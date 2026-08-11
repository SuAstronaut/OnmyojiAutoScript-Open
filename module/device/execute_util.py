# -*- coding: utf-8 -*-

import json
import os
import subprocess
from module.logger import logger


def execute_emulator(command):
    """
    执行模拟器命令
    """
    # command_str = ' '.join(command)
    # logger.info(f'执行命令: {command_str}')
    # 隐藏CMD窗口执行命令
    startupinfo = None
    if os.name == 'nt':  # Windows系统
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=10,
        startupinfo=startupinfo,
        encoding='utf-8'  # 明确指定编码
    )
    try:
        emulators_info = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.error(f"JSON解析错误: {result}")
        return None
    except Exception as e:
        logger.error(f"执行命令时出错: {e}")
        return None
    return emulators_info


def execute_show_window(command, show_window=True):
    """
    执行命令并控制窗口显示
    """
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    if not show_window:
        startupinfo.wShowWindow = 0  # SW_MINIMIZE - 不显示窗口
    else:
        startupinfo.wShowWindow = 1  # SW_SHOWNORMAL - 正常显示
    # 添加CREATE_NO_WINDOW标志以防止创建新窗口
    creationflags = subprocess.CREATE_NO_WINDOW

    # logger.info(f'Execute: {command}')
    return subprocess.Popen(
        command,
        # close_fds=True, 会造成在python进程中出现木木模拟器
        startupinfo=startupinfo,
        creationflags=creationflags,
        # 重定向标准输出和标准错误以防止弹窗
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


if __name__ == '__main__':
    # MuMuManager.exe info -v all 返回数据
    # 单个设备格式
    # {
    #     "index": "0",
    #     "name": "DU",
    #     "is_main": true,
    #     "error_code": 0,
    #     "disk_size_bytes": 30229566070,
    #     "created_timestamp": 1767260937814013,
    #     "is_android_started": false,
    #     "is_process_started": false,
    #     "hyperv_enabled": false
    # }
    # 多个设备格式
    # {
    #     "0": {
    #         "created_timestamp": 1767260937814013,
    #         "disk_size_bytes": 30229566070,
    #         "error_code": 0,
    #         "hyperv_enabled": false,
    #         "index": "0",
    #         "is_android_started": false,
    #         "is_main": true,
    #         "is_process_started": false,
    #         "name": "DU"
    #     },
    #     "1": {
    #         "created_timestamp": 1767158053498897,
    #         "disk_size_bytes": 31298980274,
    #         "error_code": 0,
    #         "hyperv_enabled": false,
    #         "index": "1",
    #         "is_android_started": false,
    #         "is_main": false,
    #         "is_process_started": false,
    #         "name": "MI"
    #     }
    # }

    aa = '{"created_timestamp": 1767260937814013,"disk_size_bytes": 30229566070,"error_code": 0,"hyperv_enabled": false,"index": "0","is_android_started": false,"is_main": true,"is_process_started": false,"name": "DU"}'
    bb = ('{ "0":{"created_timestamp": 1767260937814013,"disk_size_bytes": 30229566070,"error_code": 0,"hyperv_enabled": false,"index": "0","is_android_started": false,"is_main": true,"is_process_started": false,"name": "DU"},'
          '"1":{"created_timestamp": 1767260937814013,"disk_size_bytes": 30229566070,"error_code": 0,"hyperv_enabled": false,"index": "0","is_android_started": false,"is_main": true,"is_process_started": false,"name": "DU"    }}')
    # 标准化返回格式
    emulators_info = json.loads(bb)
    # for key, value in emulators_info.items():
    #     print(f"Key: {key}, Value: {value}/n")
    if 'index' in emulators_info:
        print(0)
    else:
        for index, emulator in emulators_info.items():
            # 跳过非模拟器信息的条目（如版本信息等）
            if not isinstance(emulator, dict):
                continue
            name = emulator.get("name", f"模拟器{index}")
            print(index)  # 确保返回字符串类型


    # if isinstance(emulators_info, dict):
    #     if 'index' in emulators_info:  # 单设备格式
    # count = len(emulators_info)  # 统计该设备的所有属性
    #     else:  # 多设备格式
    # count = len(emulators_info)  # 统计设备数量
    # print( count)
    # elif isinstance(emulators_info, list):
    #     count = len(emulators_info)  # 数组长度

        # # 获取键值对数量
        # count = len(emulators_info)
        # if count == 1:
        #     # 单个设备格式：{"0": {...}} -> {"index":"0", "name":"DU", ...}
        #     print({"0": emulators_info})
        # else:
        #     # 已经是多设备格式：{"0": {...}, "1": {...}} 或其他格式
        #     print(emulators_info)

    # print(json.loads(aa))
    # print(json.loads(bb))
