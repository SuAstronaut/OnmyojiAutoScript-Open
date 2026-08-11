# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import argparse
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette import status
from starlette.responses import FileResponse
from starlette.responses import JSONResponse

from module.logger import logger
from module.server.home_router import home_app
from module.server.mobile_router import mobile_app
from module.server.script_router import script_app
from dev_tools.task_statistics.task_statistics_router import router as task_statistics_router


ROOT = Path(__file__).resolve().parents[2]
STATIC_DIRECTORY = ROOT / "dev_server_gui" / "static"
INDEX_FILE = STATIC_DIRECTORY / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await on_startup()
    yield
    await on_shutdown()


app = FastAPI(
    title='YYS',
    description='YYS web service',
    version='0.0.0',
    lifespan=lifespan,
)
if STATIC_DIRECTORY.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(home_app)
app.include_router(script_app)
app.include_router(mobile_app)
app.include_router(task_statistics_router)


@app.get("/")
async def read_index():
    if INDEX_FILE.is_file():
        return FileResponse(INDEX_FILE)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ok", "service": "YYS"},
    )


async def on_startup():
    logger.info('YYS web service startup done')


async def on_shutdown():
    logger.info('YYS web service shutdown done')


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Internal Server Error: {exc}", exc_info=True)

    message = ', '.join(str(arg) for arg in exc.args) if exc.args else str(exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            'message': message
        },
    )


def fastapi_app():
    parser = argparse.ArgumentParser(description="YYS web service")
    parser.add_argument(
        "-k", "--key", type=str, help="Password of YYS. No password by default"
    )
    parser.add_argument(
        "--cdn",
        action="store_true",
        help="Use jsdelivr cdn for pywebio static files (css, js). Self host cdn by default.",
    )
    parser.add_argument(
        "--run",
        nargs="+",
        type=str,
        help="Run YYS by config names on startup",
    )
    args, _ = parser.parse_known_args()

    return app
