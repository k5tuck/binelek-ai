"""
Binah.AI - FastAPI Application
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="Binah.AI",
    description="AI Server - Machine learning models and predictions",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Binah.AI"}

@app.get("/")
async def root():
    return {
        "service": "Binah.AI",
        "version": "1.0.0",
        "description": "AI Server - Machine learning models and predictions"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
