# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import multiprocessing
import pickle
import socket
import time
from typing import Optional

import zerorpc

from module.logger import logger
from module.ocr.models import OcrModel

_OCR_SERVER_PROCESS: Optional[multiprocessing.Process] = None


def _normalize_address(address: str) -> str:
    if address.startswith("tcp://"):
        return address
    return f"tcp://{address}"


def _split_host_port(address: str) -> tuple[str, int]:
    addr = address.replace("tcp://", "")
    if ":" not in addr:
        return addr, 22268
    host, port = addr.rsplit(":", 1)
    return host, int(port)


def _is_port_in_use(host: str, port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(0.5)
        s.connect((host, port))
        s.shutdown(2)
        return True
    except Exception:
        return False
    finally:
        s.close()


def ensure_ocr_server_started() -> bool:
    from module.server.setting import State

    deploy_config = State.deploy_config

    if deploy_config.OcrServerPort:
        port = int(deploy_config.OcrServerPort)
    else:
        _, port = _split_host_port(str(deploy_config.OcrClientAddress))
    host = "0.0.0.0"

    if _is_port_in_use("127.0.0.1", port):
        logger.info(f"OCR server already running on port {port}")
        return True

    global _OCR_SERVER_PROCESS
    if _OCR_SERVER_PROCESS is not None and _OCR_SERVER_PROCESS.is_alive():
        logger.info("OCR server process already started")
        return True

    _OCR_SERVER_PROCESS = multiprocessing.Process(
        target=run_ocr_server,
        args=(host, port),
        name="ocr_server",
        daemon=True,
    )
    _OCR_SERVER_PROCESS.start()
    logger.info(f"Start OCR server on {host}:{port}")
    for _ in range(50):
        if _is_port_in_use("127.0.0.1", port):
            return True
        time.sleep(0.1)
    logger.error(f"OCR server is not ready on port {port}")
    return False


def get_ocr_server_process() -> Optional[multiprocessing.Process]:
    return _OCR_SERVER_PROCESS


def run_ocr_server(host: str, port: int) -> None:
    server = zerorpc.Server(OcrServer())
    server.bind(f"tcp://{host}:{port}")
    server.run()


class OcrServer(OcrModel):

    def hello(self):
        return "hello"

    def ocr(self, img_fp):
        img_fp = pickle.loads(img_fp)
        cnocr = self.__getattribute__('ch')
        return cnocr.ocr(img_fp)

    def detect_and_ocr(self, img_fp, drop_score=None):
        img_fp = pickle.loads(img_fp)
        cnocr = self.__getattribute__('ch')
        results = cnocr.detect_and_ocr(img_fp, drop_score)
        # Convert BoxedResult objects to serializable dictionaries
        if results:
            return [result.to_dict() for result in results]
        return []

    def ocr_lines(self, img_fp):
        img_fp = pickle.loads(img_fp)
        cnocr = self.__getattribute__('ch')
        return cnocr.ocr_lines(img_fp)

    def ocr_single_line(self, img_fp):
        img_fp = pickle.loads(img_fp)
        cnocr = self.__getattribute__('ch')
        return cnocr.ocr_single_line(img_fp)


if __name__ == '__main__':
    ensure_ocr_server_started()
