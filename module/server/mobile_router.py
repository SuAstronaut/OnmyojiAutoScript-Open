# This Python file uses the following encoding: utf-8
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from module.server.config_manager import ConfigManager


ROOT = Path(__file__).resolve().parents[2]
MOBILE_INDEX = ROOT / "module" / "server" / "mobile" / "index.html"
LOG_DIRECTORY = ROOT / "log"

mobile_app = APIRouter(prefix="/mobile", tags=["mobile"])

@mobile_app.get("", include_in_schema=False)
@mobile_app.get("/", include_in_schema=False)
async def mobile_index():
    if not MOBILE_INDEX.is_file():
        raise HTTPException(status_code=404, detail="移动管理页面不存在")
    return FileResponse(MOBILE_INDEX)


@mobile_app.get("/api/log-tail/{script_name}")
async def mobile_log_tail(
    script_name: str,
    lines: int = Query(default=200, ge=20, le=1000),
):
    """返回指定脚本当天/最近一次日志的尾部，供手机首次打开时查看。"""
    if script_name not in ConfigManager.all_script_files():
        raise HTTPException(status_code=404, detail="脚本配置不存在")

    log_files = sorted(
        LOG_DIRECTORY.glob(f"*_{script_name}.log"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not log_files:
        return {"file": "", "lines": []}

    latest = log_files[0]
    content = latest.read_text(encoding="utf-8", errors="replace").splitlines()
    return {"file": latest.name, "lines": content[-lines:]}
