from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.app.routes.parse import router as parse_router

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="SaveTubeX API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
allowed_origins = [
    "http://localhost:3000",  # Vite dev server
    "http://127.0.0.1:3000",
    "http://localhost:5173",  # Alternative Vite port
    "https://savetubex6.web.app",  # Production frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(parse_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "SaveTubeX API - Media URL Parser"}
