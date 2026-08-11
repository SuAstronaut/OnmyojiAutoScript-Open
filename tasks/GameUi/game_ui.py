# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from time import sleep

import importlib
from collections import deque
from module.atom.ocr import RuleOcr
from module.base.decorator import run_once
from module.base.timer import Timer
from module.exception import (GameNotRunningError, GamePageUnknownError)
from module.logger import logger
from pathlib import Path
from tasks.Component.GeneralBattle.assets import GeneralBattleAssets
from tasks.GameUi.assets import GameUiAssets
from tasks.GameUi.page import Page, PageRegistry
from tasks.Hyakkiyakou.assets import HyakkiyakouAssets
from tasks.Restart.assets import RestartAssets
from tasks.SixRealms.assets import SixRealmsAssets
from tasks.base_task import BaseTask
from tasks.GameUi.page import win_list, false_list
from tasks.GlobalGame.assets import GlobalGameAssets


class GameUi(BaseTask, GameUiAssets, GeneralBattleAssets):
    ui_current: Page = None
    ui_close = [GlobalGameAssets.I_UI_CONFIRM, GlobalGameAssets.I_UI_SURE,
                GameUiAssets.I_CANCEL,
                win_list, false_list, GlobalGameAssets.I_REWARD,
                SixRealmsAssets.I_EXIT_SIXREALMS,
                GameUiAssets.I_BACK_RED, GameUiAssets.I_BACK_BLUE, GameUiAssets.I_BACK_YELLOW,
                GeneralBattleAssets.I_EXIT_OLD, GeneralBattleAssets.I_EXIT,
                GameUiAssets.I_SKIP_BUTTON,
                RestartAssets.I_HARVEST_CHAT_CLOSE,
                HyakkiyakouAssets.I_HEND
                ]

    def __init__(self, config):
        super().__init__(config)
        # 初始化时动态导入所有 page 模块
        self._import_all_pages()

    @staticmethod
    def _import_all_pages():
        """动态加载 tasks/**/page.py"""
        base_dir = Path(__file__).resolve().parent.parent  # tasks 目录
        for task_dir in base_dir.iterdir():
            if not task_dir.is_dir():
                continue
            page_file = task_dir / "page.py"
            if not page_file.exists():
                continue
            module_name = f"tasks.{task_dir.name}.page"
            spec = importlib.util.spec_from_file_location(module_name, page_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

    @property
    def ui_pages(self) -> list[Page]:
        return PageRegistry.all()

    def ui_page_appear(self, page: Page, skip_first_screenshot: bool = True, interval: float = None):
        """
        判断当前页面是否为page
        """
        self.maybe_screenshot(skip_first_screenshot)
        return self.appear(page.check_button, interval)

    def ui_wait_until_appear(self, page: Page, timeout: float = 5, interval: float = 0.5,
                             skip_first_screenshot: bool = True) -> bool:
        """
        等待页面出现
        :param page: 等待的页面
        :param timeout: 超时时间
        :param interval: 检查间隔时间
        :param skip_first_screenshot:
        :return: 页面出现返回True, 否则返回False
        """
        logger.attr("等待页面", page)
        timeout_timer = Timer(timeout).start()
        while not timeout_timer.reached():
            if self.ui_page_appear(page, skip_first_screenshot, interval=interval):
                return True
            skip_first_screenshot = False
        return False

    def ui_get_current_page(self, skip_first_screenshot=False) -> Page:
        """
        获取当前页面
        :param skip_first_screenshot:
        :return:
        """

        @run_once
        def app_check():
            if not self.device.is_app_running():
                raise GameNotRunningError("游戏未运行")

        @run_once
        def minicap_check():
            if self.config.script.device.control_method == "uiautomator2":
                self.device.uninstall_minicap()

        @run_once
        def rotation_check():
            self.device.get_orientation()

        timeout = Timer(15, count=20).start()
        while 1:
            self.maybe_screenshot(skip_first_screenshot)
            skip_first_screenshot = False
            # 如果10S还没有到底，那么就抛出异常
            if timeout.reached():
                break
            # Known pages
            for page in self.ui_pages:
                if not page.check_button:
                    continue
                if self.ui_page_appear(page=page, interval=None):
                    logger.attr("当前页面", page)
                    self.ui_current = page
                    return page
            # Try to close unknown page
            if self.try_close_unknown_page():
                timeout = Timer(15, count=20).start()
                sleep(0.5)
            else:
                app_check()
        # Unknown page, need manual switching
        logger.warning("未知的UI页面")
        # logger.attr("截图方式", self.config.script.device.screenshot_method)
        # logger.attr("控制方式", self.config.script.device.control_method)
        # logger.warning(f"支持的页面: {[str(page) for page in self.ui_pages]}")
        logger.critical("请在探索页面, 启动脚本")
        raise GamePageUnknownError

    def ui_goto(self, destination: Page, confirm_wait=0, skip_first_screenshot=True, timeout: int = 60) -> bool:
        """
        Args:
            destination (Page):
            confirm_wait:
            skip_first_screenshot:
        :return: find destination page or timeout reached
        """
        # 如果当前页面就是目标页面，直接返回
        if self.ui_current == destination:
            return True

        logger.attr("UI前往页面", destination)
        # 初始化
        timeout_timer = Timer(timeout).start()
        confirm_timer = Timer(confirm_wait, count=int(confirm_wait // 0.5)).start()
        close_unknown_timer = Timer(6).start()
        # 构建路径映射
        path_dict = self.build_reverse_path_dict(destination)

        found = False
        while not timeout_timer.reached():
            if found:
                confirm_timer.wait()
                return True
            confirm_timer.reset()
            path = path_dict.get(self.ui_current, None)
            # 找不到路径则重新获取页面重试
            if not path:
                self.ui_get_current_page()
                continue
            # logger.attr(f"Current page", self.ui_current)
            show_paths: str = ' -> '.join([str(p) for p in path])
            logger.attr("路径", show_paths)
            # 遍历路径
            found = self._execute_path(path, timeout_timer)
            if not found:
                if close_unknown_timer.reached_and_reset():
                    self.try_close_unknown_page(skip_screenshot=False)
                    self.ui_current = None
        else:
            logger.error(f'⚠️ 不能到达 [{destination}], 超时 [{timeout}s]')
        return False

    def ui_goto_page(self, page: Page, confirm_wait=0, skip_first_screenshot=True, timeout: int = 60) -> bool:
        """
        前往指定page，自动调用获取当前页面方法，其他参数同ui_goto
        """
        self.ui_get_current_page()
        return self.ui_goto(page, confirm_wait, skip_first_screenshot, timeout)

    def ui_button_interval_reset(self, button):
        """
        Reset interval of some button to avoid mistaken clicks

        Args:
            button (Button):
        """
        if getattr(button, 'name', None) and button.name in self.interval_timer:
            self.interval_timer[button.name].reset()

    def build_reverse_path_dict(self, destination: Page) -> dict[Page, list[Page]]:
        """
        构建从每个页面到目标页面的最短路径（反向 BFS）

        Returns:
            dict[Page, list[Page]] -> {start_page: [page1, ...destinationPage], ...}
        """
        paths = {destination: [destination]}
        queue = deque([destination])
        while queue:
            cur = queue.popleft()
            for page in self.ui_pages:
                if page not in paths and cur in page.links:
                    # page -> cur
                    paths[page] = [page] + paths[cur]
                    queue.append(page)
        return paths

    def build_reverse_paths(self, destination: Page) -> list[tuple[Page, list[Page]]]:
        """
        构建从每个页面到目标页面的最短路径（反向 BFS）
        路径从短到长排序

        Returns:
            [(start_page, [page1, ...destinationPage]), ...]
        """
        paths = self.build_reverse_path_dict(destination)
        # 转换成列表并按路径长度排序, 短到长
        sorted_paths = sorted(paths.items(), key=lambda kv: len(kv[1]))
        return sorted_paths

    def try_close_unknown_page(self, skip_screenshot: bool = True):
        """
        尝试关闭未知界面
        :return: 执行了关闭返回True, 否则False
        """
        self.maybe_screenshot(skip_screenshot)
        # timer = Timer(None).start()
        # logger.warning('⚠️ 未知页面, 尝试点击UI按钮, 切换到支持的页面')
        for close in self.ui_close:
            if self.appear_then_click(close, interval=1.5):
                # logger.info(f'⚠️ [{timer.current():.1f}s] 点击按钮 {close} 在 {self.ui_current} 页')
                return True
        # logger.warning('❌ 当前页没有可点击的UI按钮')
        return False

    def _execute_path(self, path: list, timeout_timer):
        """
        执行路径
        :param path: currentPage,page1,page2,...,destinationPage
        :param timeout_timer: 超时定时器
        :return: currentPage==destinationPage
        """
        for i, current_page in enumerate(path):
            if timeout_timer.reached():
                return False
            # 当前页不等于路径中对应页, 尝试下一页
            if self.ui_current != current_page:
                continue
            if not self.run_additional(current_page, interval=0.6, skip_first_screenshot=False):
                # 例如庭院卷轴尚未完成展开时，不得继续点击下一页面入口。
                # 结束本轮路径，交给 ui_goto 外层循环重新确认当前页面后再试。
                return False
            # 如果已经是最后一页，不再跳转
            if i == len(path) - 1:
                if len(path) == 1:
                    logger.info(f'已到达页面 {current_page}')
                break
            next_page = path[i + 1]
            logger.attr('页面切换', f'{current_page} -> {next_page}')
            # 获取页面跳转操作 - 现在返回按钮列表
            buttons = current_page.links.get(next_page, [])
            if not buttons:
                logger.error(f"❌ 从 {current_page} 到 {next_page} 无链接")
                continue

            # 尝试所有可能的按钮
            for button in buttons:
                if timeout_timer.reached():
                    return False

                # 尝试点击当前按钮
                if not self.appear_then_operate(button, interval=0.5, skip_first_screenshot=False):
                    continue

                # 等待页面跳转完成
                max_wait_timer = Timer(6).start()
                page_arrived = False

                while not max_wait_timer.reached():
                    if timeout_timer.reached():
                        return False
                    if self.ui_wait_until_appear(next_page, timeout=3, skip_first_screenshot=False):
                        logger.info(f'✅ [{max_wait_timer.current():.1f}s] 到达页面 {next_page}')
                        self.ui_current = next_page
                        page_arrived = True
                        break
                    sleep(0.2)  # 短暂等待

                if page_arrived:
                    # 成功跳转到下一页，跳出按钮循环
                    break

        return self.ui_current == path[-1]

    def run_additional(self, page: Page, interval: float = None, skip_first_screenshot: bool = True):
        """执行页面附加操作；返回 False 表示附加界面尚未稳定，不能继续跳转。"""
        if not page.additional:
            return True
        for btn in page.additional:
            if self.appear_then_operate(btn, interval=interval, skip_first_screenshot=skip_first_screenshot):
                logger.info(f'页面 {page} 附加操作 {btn} 已点击')
                skip_first_screenshot = False
                if btn is RestartAssets.I_LOGIN_SCROOLL_CLOSE:
                    if not self._wait_main_scroll_open():
                        return False
        return True

    def _wait_main_scroll_open(self, timeout: float = 3.0) -> bool:
        """等待庭院卷轴完全展开，避免动画期间把商店入口误当成阴阳寮。"""
        wait_timer = Timer(timeout).start()
        while not wait_timer.reached():
            sleep(0.2)
            self.screenshot()
            if self.appear(RestartAssets.I_LOGIN_SCROOLL_OPEN):
                # 展开标记刚出现时入口仍可能在移动，再留出少量动画稳定时间。
                sleep(0.8)
                logger.info('庭院卷轴已完全展开，可以继续页面跳转')
                return True
        logger.warning('庭院卷轴点击后未确认展开，本轮不点击阴阳寮入口')
        return False

    def appear_then_operate(self, targets, interval: float = None, skip_first_screenshot: bool = True):
        """
        出现对应目标执行操作(点击图像, 滑动列表至array第一个元素并点击, 点击OCR, 点击)
        :param targets: 目标
        :param interval: 间隔
        :param skip_first_screenshot: 是否跳过首次截图
        :return: 是否成功操作
        """
        timer = Timer(interval).start()
        targets = [targets] if not isinstance(targets, (list, tuple)) else targets
        while 1:
            if timer.reached():
                return False
            self.maybe_screenshot(skip_first_screenshot)

            match_results = []
            for item in targets:
                # 自动兼容嵌套
                if isinstance(item, RuleOcr):
                    if self.ocr_appear_click(item, interval=0.5):
                        return True
                elif item.match(self.device.image):
                    match_results.append((item, item.max_val))
                    if item.max_val > 0.9:
                        break

            if match_results:
                best = max(match_results, key=lambda x: x[1])[0]
                if self.appear_then_click(best, interval=0.5):
                    return True

    def ui_goto_active(self, active: str = ''):
        """
        跳转到指定的活动页面
        参数:
            active (str): 要跳转的目标活动名称，默认为空字符串
        返回值:
            bool: 成功点击目标活动时返回True
        """
        if active == '':
            logger.warning('❌指定的活动页面未传值!')
            return False
        self.ui_goto_page(page_all_active)
        self.O_OCR_ACTIVE.keyword = active
        while 1:
            self.screenshot()
            if self.ocr_appear_click(self.O_OCR_ACTIVE):
                return True
            else:
                sleep(1)


if __name__ == '__main__':
    from module.config.config import Config
    from tasks.GameUi.page import PageRegistry, page_all_active
    from tasks.GameUi.page import page_main, page_summon, page_exploration, page_pet, page_town, page_shikigami_records

    c = Config('切换账号')
    game = GameUi(config=c)
    # print(len(game.ui_pages))
    # for page in game.ui_pages:
    #     print(page)
    # game.ui_goto_page(page_main)
    # game.ui_goto_page(page_awake_zones)
    while 1:
        game.ui_goto_page(page_pet)

        game.ui_goto_page(page_summon)
        game.ui_goto_page(page_town)

        game.ui_goto_page(page_shikigami_records)
        game.ui_goto_page(page_exploration)
        game.ui_goto_page(page_main)

    # game.ui_goto_active('版本活动')
