# -*- coding: utf-8 -*-
"""
模拟器管理模块(门面)
支持两种启停(启动/关闭)控制方式, 通过 config.script.device_2.emulator_control 选择:
    - mumumanager: 通过 MuMuManager.exe 直接控制, 仅支持木木模拟器(默认)  -> MuMuControlMixin
    - adb:         通过 ADB/进程方式控制, 兼容多种模拟器(雷电、夜神、蓝叠、逍遥等) -> AdbControlMixin

EmulatorManager 本身只负责: 初始化分流 + 通用属性 + 6 个对外接口的分发,
具体实现分别位于:
    module.device.emulator_manager_mumu.MuMuControlMixin
    module.device.emulator_manager_adb.AdbControlMixin
对外接口(两种方式一致):
    start_emulator / stop_emulator / is_emulator_running / app_start / app_stop / is_app_running
"""
from module.device.emulator_manager_adb import AdbControlMixin
from module.device.emulator_manager_mumu import (
    MuMuControlMixin,
    find_mumu_port_in_text,  # re-export, 保持向后兼容
    get_mumu_ports,          # re-export, 保持向后兼容
)
from module.device.emulator_manager_win32 import Win32ControlMixin
from tasks.Script.config_device import EmulatorControl
from tasks.Script.config_device import PackageName


class EmulatorManager(MuMuControlMixin, AdbControlMixin, Win32ControlMixin):
    def __init__(self, config=None):
        """
        初始化模拟器管理器
        """
        self.config = config
        # 启停控制方式: mumumanager / adb / win32
        self.emulator_control = config.script.device_2.emulator_control
        # 通用: 启动后窗口显示方式 & 游戏包名
        self.emulator_window = config.script.device_2.emulator_window
        self.package_name = self.get_package_name()

        if self.emulator_control == EmulatorControl.adb:
            self._init_adb_backend()
        elif self.emulator_control == EmulatorControl.win32:
            # 截图/控制强制 window_win32 由 Script 模型的校验器保证(reload 后依然生效)
            self._init_win32_backend()
        else:
            self._init_mumu_backend()

    def get_package_name(self):
        """
        获取正确的包名(两种方式通用)
        """
        package = self.config.script.device.package_name
        if package == PackageName.AUTO:
            package = "com.netease.onmyoji.wyzymnqsd_cps"  # 默认包名
        elif isinstance(package, PackageName):
            package = package.value
        return package

    # ==================== 对外接口: 按控制方式分发 ====================
    def start_emulator(self):
        """启动模拟器"""
        if self.emulator_control == EmulatorControl.adb:
            return self._adb_start_emulator()
        if self.emulator_control == EmulatorControl.win32:
            return self._win32_start_emulator()
        return self._mumu_start_emulator()

    def stop_emulator(self):
        """关闭模拟器"""
        if self.emulator_control == EmulatorControl.adb:
            return self._adb_stop_emulator()
        if self.emulator_control == EmulatorControl.win32:
            return self._win32_stop_emulator()
        return self._mumu_stop_emulator()

    def is_emulator_running(self):
        """检查模拟器是否已启动"""
        if self.emulator_control == EmulatorControl.adb:
            return self._adb_is_emulator_running()
        if self.emulator_control == EmulatorControl.win32:
            return self._win32_is_emulator_running()
        return self._mumu_is_emulator_running()

    def app_start(self):
        """启动游戏"""
        if self.emulator_control == EmulatorControl.adb:
            return self._adb_app_start()
        if self.emulator_control == EmulatorControl.win32:
            return self._win32_app_start()
        return self._mumu_app_start()

    def app_stop(self):
        """关闭游戏"""
        if self.emulator_control == EmulatorControl.adb:
            return self._adb_app_stop()
        if self.emulator_control == EmulatorControl.win32:
            return self._win32_app_stop()
        return self._mumu_app_stop()

    def is_app_running(self):
        """检查游戏是否已启动"""
        if self.emulator_control == EmulatorControl.adb:
            return self._adb_is_app_running()
        if self.emulator_control == EmulatorControl.win32:
            return self._win32_is_app_running()
        return self._mumu_is_app_running()


if __name__ == "__main__":
    from module.config.config import Config

    config = Config('mi')
    # 创建模拟器管理器实例
    manager = EmulatorManager(config)
    manager.set_emulator_setting()

    # # 检查模拟器状态
    # if manager.is_emulator_running():
    #     print("模拟器正在运行")
    #     manager.stop_ocr_server()
    #     # manager.get_emulator_info(1)
    #     # manager.hide_window()
    # else:
    #     print("模拟器未运行")
