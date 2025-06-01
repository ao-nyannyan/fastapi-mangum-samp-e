from fastapi import FastAPI
from mangum import Mangum
from app.routers.user_router import router as user_router

app = FastAPI(title="User Lambda")
app.include_router(user_router, prefix="/users")

handler = Mangum(app)
