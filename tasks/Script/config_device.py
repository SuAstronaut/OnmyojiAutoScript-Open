# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from enum import Enum
from pydantic import BaseModel, ValidationError, Field
from typing import Union
from tasks.Component.config_base import Time


class PackageName(str, Enum):
    AUTO = 'auto'
    NETEASE_ONMYOJI = 'com.netease.onmyoji.wyzymnqsd_cps'  # 网易自家的阴阳师
    NETEASE_MI = 'com.netease.onmyoji.mi'  # 小米
    NETEASE = 'com.netease.onmyoji'
    NETEASE_HUAWEI = 'com.netease.onmyoji.huawei'
    NETEASE_BILIBILI = 'com.netease.onmyoji.bili'
    NETEASE_4399 = 'com.netease.onmyoji.m4399'
    NETEASE_QQ = 'com.tencent.tmgp.yys.zqb'


class ScreenshotMethod(str, Enum):
    AUTO = 'auto'
    ADB = 'ADB'
    ADB_NC = 'ADB_nc'
    UIAUTOMATOR2 = 'uiautomator2'
    DROIDCAST = 'DroidCast'
    DROIDCAST_RAW = 'DroidCast_raw'
    SCRCPY = 'scrcpy'
    WINDOW_BACKGROUND = 'window_background'
    NEMU_IPC = 'nemu_ipc'
    WINDOW_WIN32 = 'window_win32'  # 通用 Win32 窗口 PrintWindow 截图(普通桌面软件, 不连adb)


class ControlMethod(str, Enum):
    ADB = 'adb'
    UIAUTOMATOR2 = 'uiautomator2'
    MINITOUCH = 'minitouch'
    WINDOW_MESSAGE = 'window_message'
    NEMU_IPC = "nemu_ipc"
    WINDOW_WIN32 = 'window_win32'  # 通用 Win32 窗口 PostMessage 控制(普通桌面软件, 不连adb)


class EmulatorWindow(str, Enum):
    default = '默认'
    min = '最小化'
    front = '前台显示'
    background = '隐藏'


class EmulatorControl(str, Enum):
    # 模拟器启停(启动/关闭)控制方式
    mumumanager = 'mumumanager'  # 通过 MuMuManager.exe 控制, 仅支持木木模拟器
    adb = 'adb'                  # 通过 ADB/进程方式控制, 兼容多种模拟器(雷电、夜神、蓝叠、逍遥等)
    win32 = 'win32'              # 不启停模拟器, 直接把 window_title 指定的普通Win32窗口当目标(配合截图/控制=window_win32)


class EmulatorInfoType(str, Enum):
    # module.device.platform2.emulator_base.EmulatorBase
    AUTO = 'auto'
    NoxPlayer = 'NoxPlayer'
    NoxPlayer64 = 'NoxPlayer64'
    BlueStacks4 = 'BlueStacks4'
    BlueStacks5 = 'BlueStacks5'
    BlueStacks4HyperV = 'BlueStacks4HyperV'
    BlueStacks5HyperV = 'BlueStacks5HyperV'
    LDPlayer3 = 'LDPlayer3'
    LDPlayer4 = 'LDPlayer4'
    LDPlayer9 = 'LDPlayer9'
    MuMuPlayer = 'MuMuPlayer'
    MuMuPlayerX = 'MuMuPlayerX'
    MuMuPlayer12 = 'MuMuPlayer12'
    MEmuPlayer = 'MEmuPlayer'


class Device(BaseModel):
    serial: str = Field(default="16384", title='端口')
    handle: str = Field(default='', description='对应你要启动的模拟器名称', hidden=True)
    package_name: PackageName = Field(default=PackageName.NETEASE_ONMYOJI)
    screenshot_method: ScreenshotMethod = Field(default=ScreenshotMethod.NEMU_IPC, description='screenshot_method_help')
    control_method: ControlMethod = Field(default=ControlMethod.MINITOUCH, description='control_method_help')
    adb_restart: bool = Field(default=False, description='adb_restart_help', hidden=True)
    emulatorinfo_type: Union[EmulatorInfoType, str] = Field(default=EmulatorInfoType.AUTO, description='emulatorinfo_type_help', hidden=True)
    emulatorinfo_name: str = Field(default='', description='emulatorinfo_name_help', hidden=True)
    emulatorinfo_path: str = Field(default='', description='emulatorinfo_path_help', hidden=True)


class Device2(BaseModel):
    emulator_control: EmulatorControl = Field(default=EmulatorControl.adb, description='模拟器启停方式: mumumanager 仅支持木木模拟器(默认); adb 兼容多种模拟器, 需正确填写端口/序列号; win32 桌面版)')
    emulator_window: EmulatorWindow = Field(default=EmulatorWindow.default, description='模拟器静默启动后窗口如何显示; 注意: 用 window_win32 截图时不要选"最小化"(PrintWindow 无法抓取最小化窗口会得到黑图), 后台被遮挡没问题, 选"默认"最稳')
    window_title: str = Field(default='阴阳师-MuMu模拟器专版|阴阳师-网易游戏', description='window_win32 后端目标窗口标题(普通 Win32 桌面软件, 非模拟器); 部分匹配(窗口标题包含即命中); 可用 | 分隔多个候选标题, 按先后顺序优先, 命中任意一个即可')
    window_pid: int = Field(default=0, description='多开时指定进程PID; 当 window_title 匹配到多个窗口时, 用此 PID 精确选择目标进程; 单开时保持0即可(自动使用第一个匹配窗口)')
    do_noting: bool = Field(default=False, description='不关闭模拟器，也不关闭游戏')
    close_game_time: Time = Field(default=Time(minute=5), description='超过下个任务时间, 关闭游戏, 00:00:00表示不开启功能')
    close_emulator_time: Time = Field(default=Time(minute=30), description='超过下个任务时间, 关闭模拟器, 00:00:00表示不开启功能')


if __name__ == '__main__':
    d = Device()
    print(d.json())
    print(d.schema_json())
    try:
        d.control_method = 'adb'
    except ValidationError as e:
        print(e)
