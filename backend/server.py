from contextlib import asynccontextmanager
import uvicorn
import webbrowser
import threading
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import get_db
from app.core.logger import logger
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_db()
    logger.info("="*60)
    logger.info(f"{settings.PROJECT_NAME} - 服务器启动")
    logger.info("="*60)
    logger.info("已注册的路由:")
    for route in app.routes:
        if hasattr(route, "methods"):
            methods = ", ".join(sorted(route.methods))
            logger.debug(f"  {methods:<15} {route.path}")
    logger.info("="*60)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI驱动的学术研究助手",
    version="1.0.0",
    docs_url=f"{settings.API_V1_STR}/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Session-Id"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.PROJECT_NAME}


def open_browser():
    time.sleep(1.5)
    url = f"http://localhost:{settings.BACKEND_PORT}"
    webbrowser.open(url)


if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=settings.BACKEND_PORT)
