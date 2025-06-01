from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.schemas.user import UserCreate

class UserRepository:
    async def create(self, db: AsyncSession, user_in: UserCreate) -> User:
        user = User(**user_in.dict())
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def list(self, db: AsyncSession):
        result = await db.execute(select(User))
        return result.scalars().all()

    async def get(self, db: AsyncSession, user_id: int):
        return await db.get(User, user_id)

    async def delete(self, db: AsyncSession, user_id: int):
        user = await self.get(db, user_id)
        if user:
            await db.delete(user)
            await db.commit()
