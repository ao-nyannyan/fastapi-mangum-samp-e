from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import UserCreate, UserOut
from app.services.user_service import UserService
from app.database import get_db

router = APIRouter()
service = UserService()

@router.post("/", response_model=UserOut, status_code=201)
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    return await service.create_user(db, user_in)

@router.get("/", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db)):
    return await service.list_users(db)

@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    await service.delete_user(db, user_id)
