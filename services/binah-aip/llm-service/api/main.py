"""
Binah.LLM - FastAPI Application
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="Binah.LLM",
    description="LLM Server - Natural language processing and reasoning",
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
    return {"status": "healthy", "service": "Binah.LLM"}

@app.get("/")
async def root():
    return {
        "service": "Binah.LLM",
        "version": "1.0.0",
        "description": "LLM Server - Natural language processing and reasoning"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
