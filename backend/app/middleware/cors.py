from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


DEV_ORIGINS = ["http://localhost:5173"]
PROD_ORIGINS = ["https://your-frontend.vercel.app"]
origins = PROD_ORIGINS if settings.is_production else DEV_ORIGINS


def setup_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
