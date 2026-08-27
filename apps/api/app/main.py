"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.csrf import csrf_middleware

# Instantiating Settings validates the configuration; a production deployment without
# CSRF_SECRET fails here rather than serving requests with weak CSRF protection.
settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(csrf_middleware)

app.include_router(api_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "env": settings.app_env}
