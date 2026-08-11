# This Python file uses the following encoding: utf-8
# Copy from https://github.com/LmeSzinc/AzurLaneAutoScript/gui.py

import os
import subprocess
import sys
import threading
from pathlib import Path


def _run_with_console_python_if_needed() -> None:
    """Keep OASX compatible while avoiding pythonw DLL/subprocess failures.

    OASX has ``.\toolkit\pythonw.exe server.py`` compiled into app.so. On
    this Windows installation pythonw can start, but child executables and
    OpenCV DLLs fail with 0xc0000142. Keep the pythonw parent alive for OASX
    process supervision and run the real updater/server in python.exe without
    creating a console window.
    """
    if os.name != "nt" or Path(sys.executable).name.lower() != "pythonw.exe":
        return
    python_executable = Path(sys.executable).with_name("python.exe")
    script = Path(__file__).resolve()
    if not python_executable.is_file():
        raise RuntimeError(f"找不到内置 Python：{python_executable}")
    child_environment = os.environ.copy()
    # OASX decodes shell output with the active Chinese Windows code page.
    # UTF-8 here produces mojibake such as "鈺愨晲" in its log panel.
    # Replacement keeps unsupported emoji from breaking the logger.
    child_environment["PYTHONIOENCODING"] = "gbk:replace"
    child_environment["PYTHONUNBUFFERED"] = "1"
    child = subprocess.Popen(
        [str(python_executable), str(script), *sys.argv[1:]],
        cwd=str(script.parent),
        creationflags=subprocess.CREATE_NO_WINDOW,
        env=child_environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
    )
    if child.stdout is not None:
        target = getattr(sys.stdout, "buffer", None)
        try:
            for line in iter(child.stdout.readline, b""):
                if target is not None:
                    target.write(line)
                    target.flush()
        finally:
            child.stdout.close()
    raise SystemExit(child.wait())


if __name__ == "__main__":
    _run_with_console_python_if_needed()


from module.logger import logger
from module.server.setting import State


def fun(ev: threading.Event):
    import argparse
    import asyncio
    import sys
    import time

    import uvicorn

    # 不知道干啥的照着抄就行了
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    State.restart_event = ev

    parser = argparse.ArgumentParser(description="Alas web service")
    parser.add_argument(
        "--host",
        type=str,
        help="Host to listen. Default to WebuiHost in deploy setting",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        help="Port to listen. Default to WebuiPort in deploy setting",
    )
    parser.add_argument(
        "-k", "--key", type=str, help="Password of alas. No password by default"
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
        help="Run alas by config names on startup",
    )
    args, _ = parser.parse_known_args()

    host = args.host or State.deploy_config.WebuiHost or "0.0.0.0"
    port = args.port or int(State.deploy_config.WebuiPort) or 22270

    logger.hr("启动器配置")
    logger.attr("主机", host)
    logger.attr("端口", port)
    logger.attr("热重载", ev is not None)
    
    uvicorn.run("module.server.app:fastapi_app",
                host=host,
                port=port,
                factory=True)


if __name__ == "__main__":
    try:
        from deploy.installer import Installer
        installer = Installer()
        installer.kill_process_and_git_update()

        from module.ocr.rpc import ensure_ocr_server_started
        ensure_ocr_server_started()
        
        # 启动时自动更新template.json模板
        logger.info("正在更新template.json模板...")
        from module.config.config_model import ConfigModel
        template_config = ConfigModel()
        template_dict = template_config.dict()
        ConfigModel.write_json("template", template_dict)
        logger.info("template.json模板更新完成")
    except Exception as e:
        logger.error(e)
    fun(None)
