from fastapi import FastAPI
from mangum import Mangum
from app.routers.todo_router import router as todo_router

app = FastAPI(title="Todo Lambda")
app.include_router(todo_router, prefix="/todos")

handler = Mangum(app)
