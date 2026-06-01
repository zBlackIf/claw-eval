"""FastAPI application entry point."""
from fastapi import FastAPI
from app.api.routers import chat

app = FastAPI(title="Novel Platform API")
app.include_router(chat.router)
