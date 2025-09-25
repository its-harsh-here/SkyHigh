from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime  # ✅ ADDED MISSING IMPORT
import uvicorn  # ✅ ADDED MISSING IMPORT
from weather_routes import router as weather_router
from config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Aviation Weather Briefing System API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(weather_router)

@app.get("/")
async def root():
    return {
        "message": "Aviation Weather Briefing System API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "✅ Ready"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat()  # ✅ FIXED
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
