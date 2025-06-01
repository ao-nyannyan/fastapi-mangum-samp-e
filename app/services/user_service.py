from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate

class UserService:
    def __init__(self):
        self.repo = UserRepository()

    async def create_user(self, db: AsyncSession, user_in: UserCreate):
        return await self.repo.create(db, user_in)

    async def list_users(self, db: AsyncSession):
        return await self.repo.list(db)

    async def get_user(self, db: AsyncSession, user_id: int):
        return await self.repo.get(db, user_id)

    async def delete_user(self, db: AsyncSession, user_id: int):
        await self.repo.delete(db, user_id)
