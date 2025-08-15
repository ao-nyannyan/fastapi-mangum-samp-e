# models.py（例）
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, String, DateTime, func

class Base(DeclarativeBase):
    pass

class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 依存など
from sqlalchemy.ext.asyncio import AsyncSession
from repository import BaseRepository
from models import Item

repo = BaseRepository[Item](Item)
# 1) get / exists / count / list
item = await repo.get(session, 123)
exists = await repo.exists(session, title="hello")
total = await repo.count(session, title="hello")
rows = await repo.list(
    session,
    where={"title": "hello"},
    order_by=(Item.created_at.desc(), Item.id.desc()),
    limit=50,
    offset=0,
)
# 2) create（新規専用）
obj = Item(title="new", body="created via create()")
saved = await repo.create(session, obj)  # PKが採番される
# 3) save（新規/更新どちらも吸収）
# 新規
obj = Item(title="new2", body="created via save()")
saved = await repo.save(session, obj)

# 更新（同一セッション管理下 = persistent）
saved.title = "renamed"
await repo.save(session, saved)

# 別セッション起源などの detatched 個体でもOK（merge）
detached = Item(id=saved.id, title="from-other-session", body="updated")
await repo.save(session, detached)
# 4) update_entity（部分更新：指定フィールドだけ）
patch = Item(id=saved.id, title="only title changed")  # bodyは触らない
await repo.update_entity(session, patch, fields={"title"})
# 5) bulk_create（モデル列をそのまま）
batch = [Item(title=f"t{i}", body="bulk") for i in range(100)]
n = await repo.bulk_create(session, batch)  # n == 100, 各objにPK反映
# 6) get_many_by_ids（IN検索・順序維持オプション）
rows = await repo.get_many_by_ids(session, [5, 2, 9], keep_order=True)  # [id=5, 2, 9]の順で返る
# 7) delete
ok = await repo.delete(session, saved.id)