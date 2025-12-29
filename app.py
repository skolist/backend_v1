"""
Exposes the function to create the FastAPI application instance. To be used by main.py
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from config.settings import PRODUCTION
from api.v1.router import router as v1_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    The function to create the FastAPI application instance. To be used by main.py
    """
    app = FastAPI(title="My FastAPI Application")

    app.include_router(v1_router)

    if PRODUCTION:
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"https://.*\.skolist\.com",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info("🌐 Configuring CORS for production")
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Development mode
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/")
    async def read_root():
        return {"message": "Welcome to My FastAPI Application!"}

    return app
