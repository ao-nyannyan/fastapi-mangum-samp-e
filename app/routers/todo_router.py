from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.todo import TodoCreate, TodoOut
from app.services.todo_service import TodoService
from app.database import get_db

router = APIRouter()
service = TodoService()

@router.post("/", response_model=TodoOut, status_code=201)
async def create_todo(todo_in: TodoCreate, db: AsyncSession = Depends(get_db)):
    return await service.create_todo(db, todo_in)

@router.get("/", response_model=list[TodoOut])
async def list_todos(db: AsyncSession = Depends(get_db)):
    return await service.list_todos(db)

@router.get("/{todo_id}", response_model=TodoOut)
async def get_todo(todo_id: int, db: AsyncSession = Depends(get_db)):
    todo = await service.get_todo(db, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo

@router.delete("/{todo_id}", status_code=204)
async def delete_todo(todo_id: int, db: AsyncSession = Depends(get_db)):
    await service.delete_todo(db, todo_id)
