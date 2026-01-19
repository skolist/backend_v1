"""
Exposes the function to create the FastAPI application instance. To be used by main.py
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize logging configuration (must be imported before other modules)
from config.logger import setup_logging
setup_logging()

from config.settings import DEPLOYMENT_ENV
from api.v1.router import router as v1_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    The function to create the FastAPI application instance. To be used by main.py
    """
    app = FastAPI(title="My FastAPI Application")

    app.include_router(v1_router)

    if DEPLOYMENT_ENV == "PRODUCTION":
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"https://.*\.skolist\.com",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info(
            "CORS configured",
            extra={
                "deployment_env": DEPLOYMENT_ENV,
                "allow_origin_pattern": r"https://.*\.skolist\.com",
            },
        )
    elif DEPLOYMENT_ENV == "STAGE":
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"https://.*\.vercel\.app",  # Vercel Preview mode
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info(
            "CORS configured",
            extra={
                "deployment_env": DEPLOYMENT_ENV,
                "allow_origin_pattern": r"https://.*\.vercel\.app",
            },
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Local mode
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info(
            "CORS configured",
            extra={
                "deployment_env": DEPLOYMENT_ENV,
                "allow_origins": "*",
            },
        )

    @app.get("/")
    async def read_root():
        return {"message": "Welcome to My FastAPI Application!"}

    return app
