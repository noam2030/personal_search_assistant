import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import router as api_router
from backend.db import init_db

# Initialize Database Schema on App Startup
init_db()

app = FastAPI(
    title="Personal Search Assistant Agent API",
    description="Backend REST API for creating web monitoring tasks, executing tasks, and storing extraction results.",
    version="1.0.0",
)

# Configure CORS for Vercel deployment and local dev
allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://*.vercel.app",
]

# Allow custom CORS origins from environment variable if defined
custom_origin = os.getenv("ALLOWED_ORIGIN")
if custom_origin:
    allowed_origins.append(custom_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits requests from Vercel & local frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router)


@app.get("/")
def root():
    return {
        "message": "Personal Search Assistant Agent API is running.",
        "docs": "/docs",
        "health": "/api/health",
    }
