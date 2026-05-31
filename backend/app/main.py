from fastapi import FastAPI
from app.routes import auth
from app.middleware.cors import setup_cors

app = FastAPI(title="SmartNotes AI", version="1.0.0")

setup_cors(app)
app.include_router(auth.router)

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
