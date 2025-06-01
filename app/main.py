from fastapi import FastAPI
from app.routers import user_router, todo_router

app = FastAPI(title="Lambda FastAPI Example")

app.include_router(user_router.router, prefix="/users", tags=["Users"])
app.include_router(todo_router.router, prefix="/todos", tags=["Todos"])

# Root health
@app.get("/")
async def read_root():
    return {"status": "ok"}
