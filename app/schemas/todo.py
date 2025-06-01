from pydantic import BaseModel
from typing import Optional

class TodoBase(BaseModel):
    title: str

class TodoCreate(TodoBase):
    owner_id: int

class TodoOut(TodoBase):
    id: int
    owner_id: int
    class Config:
        orm_mode = True
