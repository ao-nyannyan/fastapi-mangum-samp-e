# repository.py
from __future__ import annotations
from typing import Any, Generic, Iterable, Sequence, TypeVar, Set
from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.inspection import inspect as sa_inspect

T = TypeVar("T")  # SQLAlchemy model class (Declarative)

class BaseRepository(Generic[T]):
    """
    SQLAlchemy 2.x / Async 用の共通リポジトリ（モデル専用）。
    - モデル以外（dict/Pydantic）は受け付けない設計。
    - トランザクションの commit/rollback は呼び出し側（サービス/UoW）で行う前提。
    """

    def __init__(self, model: type[T]) -> None:
        self.model = model

    # ------------------------ Read ------------------------

    async def get(self, session: AsyncSession, pk: Any) -> T | None:
        """主キー1件取得"""
        return await session.get(self.model, pk)

    async def exists(self, session: AsyncSession, **filters: Any) -> bool:
        """存在確認（等価条件のみ）"""
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        res = await session.execute(stmt)
        return int(res.scalar_one()) > 0

    async def list(
        self,
        session: AsyncSession,
        *,
        where: dict[str, Any] | None = None,
        order_by: Sequence[InstrumentedAttribute] | None = None,
        limit: int | None = 100,
        offset: int | None = 0,
    ) -> list[T]:
        """一覧（簡易版。必要ならキーセットは別途実装）"""
        stmt = select(self.model)
        if where:
            stmt = stmt.filter_by(**where)
        if order_by:
            stmt = stmt.order_by(*order_by)
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset:
            stmt = stmt.offset(offset)
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def count(self, session: AsyncSession, **filters: Any) -> int:
        """件数"""
        stmt = select(func.count()).select_from(self.model)
        if filters:
            stmt = stmt.filter_by(**filters)
        res = await session.execute(stmt)
        return int(res.scalar_one())

    async def get_many_by_ids(
        self,
        session: AsyncSession,
        ids: Sequence[Any],
        *,
        keep_order: bool = False,
        chunk_size: int = 1000,
        dedupe: bool = True,
    ) -> list[T]:
        """
        主キーのリストでまとめて取得。
        - keep_order=True: 渡したID順で返す（MySQLは ORDER BY FIELD、その他はアプリ側で整列）
        - chunk_size: IN リストを分割実行
        """
        if not ids:
            return []

        # 単一PKのみ対応
        pk_cols = sa_inspect(self.model).primary_key
        if len(pk_cols) != 1:
            raise ValueError("get_many_by_ids(): composite primary key is not supported")
        pk_col = pk_cols[0]

        # 重複除去（順序維持）
        if dedupe:
            seen = set()
            ids = [x for x in ids if not (x in seen or seen.add(x))]

        rows: list[T] = []
        dialect = session.bind.dialect.name if session.bind is not None else ""

        from sqlalchemy import func as sa_func  # for FIELD()

        for i in range(0, len(ids), chunk_size):
            chunk = ids[i : i + chunk_size]
            stmt = select(self.model).where(pk_col.in_(chunk))
            if keep_order and dialect == "mysql":
                # MySQL のみ：DB側で順序維持
                stmt = stmt.order_by(sa_func.field(pk_col, *chunk))
            res = await session.execute(stmt)
            rows.extend(res.scalars().all())

        if keep_order and dialect != "mysql":
            by_id = {getattr(r, pk_col.key): r for r in rows}
            rows = [by_id[i] for i in ids if i in by_id]
        return rows

    # ------------------------ Write ------------------------

    async def create(self, session: AsyncSession, obj: T) -> T:
        """
        新規作成。SQLAlchemyモデルのみ受け入れる。
        - transient（未管理/PKなし）: add → flush
        - detached/persistentはエラーにし、明示的に save() を使わせる設計にしても良い
        """
        state = sa_inspect(obj)
        if not state.transient:
            # 安全のため “新規専用”
            raise ValueError("create(): expected a transient (new) SQLAlchemy model instance")
        session.add(obj)
        await session.flush()
        return obj

    async def save(self, session: AsyncSession, obj: T) -> T:
        """
        SAモデルを“そのまま保存”。PK有無や状態に応じて新規/更新を吸収（簡易Upsert）。
        - transient: add → flush
        - detached: merge(load=True) → flush
        - persistent: flush（すでにセッション管理下）
        """
        state = sa_inspect(obj)
        if state.transient:
            session.add(obj)
            await session.flush()
            return obj
        if state.detached:
            merged = await session.merge(obj, load=True)
            await session.flush()
            return merged
        # persistent（同一セッション管理下）
        await session.flush()
        return obj

    async def update_entity(
        self,
        session: AsyncSession,
        entity: T,
        *,
        fields: Set[str] | None = None,
    ) -> T:
        """
        既存行を、渡したエンティティの値で部分更新。
        - PK必須
        - fields 指定でそのカラムのみ反映（Noneなら全カラム）
        """
        inst = sa_inspect(entity)
        # PK 取得
        pk_cols = inst.mapper.primary_key
        if len(pk_cols) != 1:
            raise ValueError("update_entity(): composite primary key is not supported")
        pk_name = pk_cols[0].key
        pk_val = getattr(entity, pk_name, None)
        if pk_val is None:
            raise ValueError("update_entity(): primary key value is required on entity")

        # 既存行取得
        current = await session.get(self.model, pk_val)
        if current is None:
            raise ValueError(f"update_entity(): entity not found (pk={pk_val!r})")

        # 反映対象カラム
        col_names = [c.key for c in inst.mapper.columns]
        target_fields = set(col_names) if fields is None else set(fields)
        if pk_name in target_fields:
            target_fields.remove(pk_name)

        for k in target_fields:
            setattr(current, k, getattr(entity, k))
        await session.flush()
        return current

    async def bulk_create(self, session: AsyncSession, models: Iterable[T]) -> int:
        """
        複数モデルの一括作成（全て transient を想定）。
        - add_all → flush
        - 戻り値は作成件数（IDは各モデルに反映される）
        """
        items = list(models)
        if not items:
            return 0
        # 簡易チェック
        for m in items:
            if not sa_inspect(m).transient:
                raise ValueError("bulk_create(): all models must be transient (new)")
        session.add_all(items)
        await session.flush()
        return len(items)

    async def delete(self, session: AsyncSession, pk: Any) -> bool:
        """主キー削除（行数を返す）"""
        pk_cols = sa_inspect(self.model).primary_key
        if len(pk_cols) != 1:
            raise ValueError("delete(): composite primary key is not supported")
        pk_col = pk_cols[0]
        stmt = sa_delete(self.model).where(pk_col == pk)
        res = await session.execute(stmt)
        return (res.rowcount or 0) > 0