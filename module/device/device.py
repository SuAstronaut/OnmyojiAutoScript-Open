import time

from collections import deque
# Patch pkg_resources before importing adbutils and uiautomator2
from module.device.pkg_resources import get_distribution

# Just avoid being removed by import optimization
_ = get_distribution

from module.base.timer import Timer
from module.base.utils import get_color, image_size
from module.device.control import Control
from module.device.screenshot import Screenshot
from module.exception import (GameNotRunningError,
                              GameWaitTooLongError,
                              GameTooManyClickError,
                              RequestHumanTakeover)
from module.logger import logger
from module.device.emulator_manager import EmulatorManager
from tasks.Script.config_device import EmulatorWindow, EmulatorControl
from module.device.platform2.platform_windows import minimize_by_name,show_window_by_name,show_hide_by_name


class Device(EmulatorManager, Screenshot, Control):
    _screen_size_checked = False
    click_record = deque(maxlen=15)
    
    # 卡住检测配置：使用单个定时器 + 超时时间
    stuck_timer = Timer(60, count=60).start()  # 基础定时器
    stuck_timeout = 60  # 当前超时阈值（秒），默认60秒

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.is_emulator_running():
            self.start_emulator()
            time.sleep(5)
            start_time = time.time()
            while not self.is_emulator_running():
                if time.time() - start_time > 60:
                    raise TimeoutError("模拟器启动超时")
                time.sleep(1)

            if self.emulator_window == EmulatorWindow.front:
                show_window_by_name(self.emulator_name)
                logger.info(f'前台显示窗口: {self.emulator_name}')
            elif self.emulator_window == EmulatorWindow.min:
                minimize_by_name(self.emulator_name)
                logger.info(f'最小化窗口: {self.emulator_name}')
            elif self.emulator_window == EmulatorWindow.background:
                show_hide_by_name(self.emulator_name)
                logger.info(f'隐藏窗口: {self.emulator_name}')
            else:
                logger.info(f'默认窗口: {self.emulator_name}')

        self.screenshot_interval_set(0.3)

        # 等待模拟器"完全启动就绪"(截图通道可用)再继续,
        # 避免模拟器进程/VM 虽已启动、但截图通道(如 nemu_ipc 渲染器)尚未就绪就运行任务导致报错
        self.wait_until_ready(timeout=60)

        logger.hr('模拟器状态 True', level=1)

    def screenshot(self):
        """
        Returns:
            np.ndarray:
        """
        self.stuck_record_check()

        try:
            super().screenshot()
        except RequestHumanTakeover as e:
            raise RequestHumanTakeover("screenshot error")

        return self.image

    def release_during_wait(self):
        if self.config.script.device.screenshot_method == 'nemu_ipc':
            self.nemu_ipc_release()
        # window_win32 模式不连 adb, 跳过 adb 断开
        if self.config.script.device_2.emulator_control != EmulatorControl.win32:
            self.adb_disconnect(self.serial)

    def stuck_record_add(self, timeout=300):
        """
        设置卡住检测的超时时间。
        
        Args:
            timeout: 超时时间（秒），默认60秒。常用值：
                    - 60: 普通场景（默认）
                    - 300: 战斗场景（5分钟）
                    - 600: 超长等待（10分钟）
        Returns:
            None
        """
        if not isinstance(timeout, int):
            timeout = 300
        self.stuck_timeout = timeout
        logger.info(f'添加 {timeout}S 等待检测')

        # 长时间等待时切换到战斗截图间隔（降低CPU占用）
        self.screenshot_interval_set(1)

    def stuck_record_clear(self):
        """
        清除卡住检测记录并重置定时器。
        恢复默认超时时间和普通截图间隔。
        """
        # 恢复默认超时和截图间隔
        self.stuck_timeout = 60
        self.screenshot_interval_set(0.3)
        
        self.stuck_timer.reset()

    def stuck_record_check(self):
        """
        检查是否发生卡住情况。
        
        Raises:
            GameWaitTooLongError: 当等待时间过长且游戏仍在运行时抛出
            GameNotRunningError: 当游戏已停止运行时抛出
        """
        # 如果未达到超时时间，直接返回
        if not self.stuck_timer.reached():
            return False
        
        # 检查实际经过的时间是否超过当前超时阈值
        elapsed = self.stuck_timer.current()
        if elapsed < self.stuck_timeout:
            return False
        
        logger.warning('等待时间过长，触发卡住处理机制')
        logger.warning(f'已过时间: {elapsed:.1f}s / 超时阈值: {self.stuck_timeout}s')
        logger.warning(f'定时器状态: {self.stuck_timer}')
        
        self.stuck_record_clear()

        if self.is_app_running():
            raise GameWaitTooLongError(f'等待时间过长 ({elapsed:.1f}s > {self.stuck_timeout}s)，可能需要人工干预')
        else:
            raise GameNotRunningError('游戏已停止运行')

    def handle_control_check(self, button):
        """
        处理控制检查，清除卡住记录并添加点击记录。
        
        Args:
            button: 被点击的按钮标识
        """
        self.stuck_record_clear()
        self.click_record_add(button)
        self.click_record_check()

    def click_record_add(self, button):
        self.click_record.append(str(button))

    def click_record_clear(self):
        self.click_record.clear()

    def click_record_remove(self, button):
        """
        Remove a button from `click_record`

        Args:
            button (Button):

        Returns:
            int: Number of button removed
        """
        removed = 0
        for _ in range(self.click_record.maxlen):
            try:
                self.click_record.remove(str(button))
                removed += 1
            except ValueError:
                # Value not in queue
                break

        return removed

    def click_record_check(self):
        """
        Raises:
            GameTooManyClickError:
        """
        count = {}
        for key in self.click_record:
            count[key] = count.get(key, 0) + 1
        count = sorted(count.items(), key=lambda item: item[1])
        if count[0][1] >= 12:
            logger.warning(f'按钮点击次数过多: {count[0][0]}')
            logger.warning(f'历史点击: {[str(prev) for prev in self.click_record]}')
            self.click_record_clear()
            raise GameTooManyClickError(f'按钮点击次数过多: {count[0][0]}')
        if len(count) >= 2 and count[0][1] >= 6 and count[1][1] >= 6:
            logger.warning(f'两个按钮之间点击次数过多: {count[0][0]}, {count[1][0]}')
            logger.warning(f'历史点击: {[str(prev) for prev in self.click_record]}')
            self.click_record_clear()
            raise GameTooManyClickError(f'两个按钮之间点击次数过多: {count[0][0]}, {count[1][0]}')

    def disable_stuck_detection(self):
        """
        Disable stuck detection and its handler. Usually uses in semi auto and debugging.
        """
        logger.info('禁用卡住检测')

        def empty_function(*arg, **kwargs):
            return False

        self.click_record_check = empty_function
        self.stuck_record_check = empty_function

    def app_start(self):
        # if not self.config.script.error.handle_error:
        #     logger.critical('No app stop/start, because HandleError disabled')
        #     logger.critical('Please enable Alas.Error.HandleError or manually login to AzurLane')
        #     raise RequestHumanTakeover
        super().app_start()
        self.stuck_record_clear()
        self.click_record_clear()

    def app_stop(self):
        # if not self.config.script.error.handle_error:
        #     logger.critical('No app stop/start, because HandleError disabled')
        #     logger.critical('Please enable Alas.Error.HandleError or manually login to AzurLane')
        #     raise RequestHumanTakeover
        super().app_stop()
        self.stuck_record_clear()
        self.click_record_clear()

    def emulator_start(self):
        super().start_emulator()

    def emulator_stop(self):
        super().stop_emulator()

    def is_emulator_running(self):
        return super().is_emulator_running()

    def is_app_running(self):
        return super().is_app_running()

    def is_screenshot_ready(self) -> bool:
        """
        通过一次"真实截图"判断模拟器是否已完全启动就绪.

        仅"进程/VM 启动完成"(MuMu player_state == start_finished)并不足以保证可以截图:
        例如 nemu_ipc 的画面渲染器在启动完成后仍需片刻才能连接成功, 此时 nemu_connect 会失败.
        这里直接调用当前配置的截图方式做一次截图, 以"能否截到有效画面"作为就绪的最终判据:
            - 截图抛异常(如 nemu_ipc 连接失败) -> 未就绪
            - 截到纯黑画面(渲染器/系统尚未就绪)   -> 未就绪
            - 截到有效(非纯黑)画面                -> 已就绪

        Returns:
            bool: True 表示截图通道已就绪
        """
        try:
            method = self.screenshot_methods.get(
                self.config.script.device.screenshot_method,
                self.screenshot_adb
            )
            image = method()
        except Exception as e:
            logger.info(f'截图通道尚未就绪: {type(e).__name__}: {e}')
            return False

        if image is None:
            return False
        width, height = image_size(image)
        if width <= 0 or height <= 0:
            return False
        # 纯黑画面视为模拟器仍在启动中(与 check_screen_black 使用相同判据)
        if sum(get_color(image, area=(0, 0, width, height))) < 1:
            logger.info('收到纯黑画面，模拟器尚未完全启动')
            return False
        return True

    def wait_until_ready(self, timeout=60, retry=3):
        """
        等待模拟器"完全启动就绪"再继续, 避免尚未完全启动就运行任务导致报错.

        判定标准(两者皆满足才视为就绪):
            1. is_emulator_running(): 模拟器进程/VM 启动完成(MuMu player_state == start_finished)
            2. is_screenshot_ready(): 能成功截取到有效(非纯黑)画面(截图通道/渲染器已就绪)

        单轮超时不算失败, 会先做恢复动作再等下一轮:
            - 模拟器没在运行 -> 直接重新启动
            - 模拟器在运行但截图通道一直不就绪(卡死/黑屏) -> 先关掉再重启
        连续 retry 轮都超时才交人工处理.

        Args:
            timeout (int): 单轮等待的最长秒数
            retry (int): 最多等待几轮

        Raises:
            RequestHumanTakeover: 连续 retry 轮仍未就绪
        """
        logger.hr('等待模拟器就绪', level=2)
        self.waiting_emulator_ready = True
        try:
            for attempt in range(1, retry + 1):
                if self._wait_ready_once(timeout):
                    logger.info('模拟器已完全启动就绪')
                    return True

                logger.warning(f'等待模拟器就绪超时({timeout}s) [{attempt}/{retry}]')
                if attempt < retry:
                    self._recover_emulator()
        finally:
            self.waiting_emulator_ready = False

        logger.error(f'连续 {retry} 轮等待模拟器就绪均超时，模拟器可能未正常启动')
        raise RequestHumanTakeover('模拟器启动超时，请检查模拟器是否正常运行')

    def _recover_emulator(self):
        """
        单轮等待超时后的恢复动作: 让下一轮有机会成功, 而不是干等同样的结果.
        """
        try:
            if self.is_emulator_running():
                # 进程活着但截图通道始终不就绪, 多半是卡死/黑屏, 干等无用, 重启它
                logger.info('模拟器进程在运行但截图通道未就绪，尝试重启模拟器')
                self.stop_emulator()
                time.sleep(5)
            else:
                logger.info('模拟器未在运行，尝试重新启动')
            self.start_emulator()
        except Exception as e:
            # 恢复失败不该盖掉"启动超时"这个真正的结论, 留给下一轮/最终报错
            logger.warning(f'尝试恢复模拟器时出错: {e}')

    def _wait_ready_once(self, timeout) -> bool:
        """等待一轮, 就绪返回 True, 超时返回 False"""
        start_time = time.time()
        while True:
            if self.is_emulator_running() and self.is_screenshot_ready():
                return True

            if time.time() - start_time > timeout:
                return False

            # 释放可能的半开 nemu_ipc 连接, 下次循环重新连接
            if self.config.script.device.screenshot_method == 'nemu_ipc':
                self.nemu_ipc_release()
            time.sleep(1)


if __name__ == "__main__":
    device = Device(config="oa")
    # cv2.imshow("imgSrceen", device.screenshot())  # 显示
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
