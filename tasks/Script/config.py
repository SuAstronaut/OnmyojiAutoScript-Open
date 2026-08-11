# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from pydantic import BaseModel, Field, root_validator

from tasks.Script.config_device import ControlMethod
from tasks.Script.config_device import Device
from tasks.Script.config_device import Device2
from tasks.Script.config_device import EmulatorControl
from tasks.Script.config_device import ScreenshotMethod
from tasks.Script.config_error import Error
# from tasks.Script.config_optimization import Optimization
# from tasks.Script.config_team import Team


class Script(BaseModel):
    device: Device = Field(default_factory=Device)
    device_2: Device2 = Field(default_factory=Device2)
    error: Error = Field(default_factory=Error)
    # optimization: Optimization = Field(default_factory=Optimization)
    # team: Team = Field(default_factory=Team)

    @root_validator
    def _force_win32_methods(cls, values):
        """
        win32(桌面版)不连 adb, 截图/控制只能走 window_win32.
        必须在模型构造时强制, 否则 Config.reload() 重建 model 后会回落到磁盘里的
        nemu_ipc/minitouch, 导致任务跑到一半突然去连模拟器而崩溃.
        """
        device, device_2 = values.get('device'), values.get('device_2')
        if device is not None and device_2 is not None \
                and device_2.emulator_control == EmulatorControl.win32:
            device.screenshot_method = ScreenshotMethod.WINDOW_WIN32
            device.control_method = ControlMethod.WINDOW_WIN32
        return values
