from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router
from app.config import get_settings
from app.errors import ChargeSmartError


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", description="Evidence-based EV charging recommendations")
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])
    app.include_router(router)

    @app.exception_handler(ChargeSmartError)
    async def chargesmart_error_handler(_: Request, exc: ChargeSmartError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, "warnings": exc.warnings})

    return app


app = create_app()
