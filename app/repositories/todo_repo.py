from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.todo import Todo
from app.schemas.todo import TodoCreate

class TodoRepository:
    async def create(self, db: AsyncSession, todo_in: TodoCreate) -> Todo:
        todo = Todo(**todo_in.dict())
        db.add(todo)
        await db.commit()
        await db.refresh(todo)
        return todo

    async def list(self, db: AsyncSession):
        result = await db.execute(select(Todo))
        return result.scalars().all()

    async def get(self, db: AsyncSession, todo_id: int):
        return await db.get(Todo, todo_id)

    async def delete(self, db: AsyncSession, todo_id: int):
        todo = await self.get(db, todo_id)
        if todo:
            await db.delete(todo)
            await db.commit()
