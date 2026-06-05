from fastapi import FastAPI
from app.routes import auth, notes, ai
from app.middleware.cors import setup_cors

app = FastAPI(title="SmartNotes AI", version="1.0.0")

setup_cors(app)
app.include_router(auth.router)
app.include_router(notes.router)
app.include_router(ai.router)

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
