from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.todo_repo import TodoRepository
from app.schemas.todo import TodoCreate

class TodoService:
    def __init__(self):
        self.repo = TodoRepository()

    async def create_todo(self, db: AsyncSession, todo_in: TodoCreate):
        return await self.repo.create(db, todo_in)

    async def list_todos(self, db: AsyncSession):
        return await self.repo.list(db)

    async def get_todo(self, db: AsyncSession, todo_id: int):
        return await self.repo.get(db, todo_id)

    async def delete_todo(self, db: AsyncSession, todo_id: int):
        await self.repo.delete(db, todo_id)
