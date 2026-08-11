from module.base.timer import Timer
from module.logger import logger
from tasks.Component.GeneralBattle.config_general_battle import GreenMarkType
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Duel.assets import DuelAssets


class GreenMark(GeneralBattle, DuelAssets):

    def green_mark_ocr(self, mark_mode: GreenMarkType = GreenMarkType.GREEN_MAIN, ocr_target: bool = None) -> bool:
        """
        使用须知： 把你想要绿标的式神改为 '青'，然后正确选择式神绿标站位

        绿标， 如果不使能就直接返回
        :param mark_mode:
        :param ocr_target:
        :return:
        """
        # 定义「位置枚举」与「图片变量」的映射关系
        MARK_POSITION_MAP = {
            GreenMarkType.GREEN_LEFT1: self.I_GREEN_MARK_IMG1,
            GreenMarkType.GREEN_LEFT2: self.I_GREEN_MARK_IMG2,
            GreenMarkType.GREEN_LEFT3: self.I_GREEN_MARK_IMG3,
            GreenMarkType.GREEN_LEFT4: self.I_GREEN_MARK_IMG4,
            GreenMarkType.GREEN_LEFT5: self.I_GREEN_MARK_IMG5,
        }

        if not ocr_target:
            logger.info(f'------（青）进行{mark_mode}位置图片识别------')

            # 处理主位置：直接返回
            if mark_mode == GreenMarkType.GREEN_MAIN:
                logger.info('阴阳师位置不支持，返回')
                return False

            # 处理左侧位置：从映射表取值（移除位置日志打印）
            if mark_mode in MARK_POSITION_MAP:
                target = MARK_POSITION_MAP[mark_mode]  # 仅赋值，不打印具体位置
        else:
            logger.info(f'------（青）进行全位置图片识别------')
            target = self.I_GREEN_MARK_IMG_ALL

        # 点击绿标
        mark_timer = Timer(5)
        mark_timer.start()
        while 1:
            if mark_timer.reached():
                # self.save_image(task_name='未识别到式神名称', wait_time=0, push_flag=True, content='未识别到式神名称',image_type=True)
                return False
            self.screenshot()
            if self.appear(target, interval=0.5):
                new_roi_front = (target.roi_front[0],
                                 target.roi_front[1] + 60,
                                 10,
                                 100)
                self.C_DUEL_GREEN_LEFT_FULL.roi_front = new_roi_front
                break
        # 点击绿标
        mark_timer = Timer(5)
        mark_timer.start()
        while 1:
            if mark_timer.reached():
                # logger.info(f'old Image roi {target.roi_front}')
                # logger.info(f'new Image roi {self.C_DUEL_GREEN_LEFT_FULL.roi_front}')
                # self.save_image(task_name='斗技绿标超时', wait_time=0, push_flag=True, content='超时未识别到绿标',image_type=True)
                return False
            self.screenshot()
            if self.appear(self.I_WIN) and self.appear(self.I_D_VICTORY):
                logger.info('对面直接退了,识别到赢，返回')
                return True
            if self.wait_until_appear(self.I_GREEN_MARK_AUTO, wait_time=1):
                # self.save_image(wait_time=0, push_flag=True, content='识别到绿标',image_type=True)
                logger.info('识别到绿标,返回')
                return True
            self.click(self.C_DUEL_GREEN_LEFT_FULL)


    def green_mark_new(self, mark_mode: GreenMarkType = GreenMarkType.GREEN_MAIN):
        """
        绿标， 如果不使能就直接返回
        :param mark_mode:
        :return:
        """
        logger.info('------进行区域点击识别绿标位置------')
        if self.wait_until_appear(self.I_GREEN_MARK, wait_time=1):
            # logger.info("识别到绿标，返回")
            return
        # logger.info("Green is enable")
        x, y = None, None
        match mark_mode:
            case GreenMarkType.GREEN_LEFT1:
                x, y = self.C_DUEL_GREEN_LEFT_1.coord()
                logger.info("Green left 1")
            case GreenMarkType.GREEN_LEFT2:
                x, y = self.C_GREEN_LEFT_2.coord()
                logger.info("Green left 2")
            case GreenMarkType.GREEN_LEFT3:
                x, y = self.C_GREEN_LEFT_3.coord()
                logger.info("Green left 3")
            case GreenMarkType.GREEN_LEFT4:
                x, y = self.C_GREEN_LEFT_4.coord()
                logger.info("Green left 4")
            case GreenMarkType.GREEN_LEFT5:
                x, y = self.C_DUEL_GREEN_LEFT_5.coord()
                logger.info("Green left 5")
            case GreenMarkType.GREEN_MAIN:
                x, y = self.C_GREEN_MAIN.coord()
                logger.info("Green main")

        # 等待那个准备的消失
        while 1:
            self.screenshot()
            if not self.appear(self.I_PREPARE_HIGHLIGHT):
                break

        # 点击绿标
        mark_timer = Timer(5)
        mark_timer.start()
        while 1:
            self.screenshot()
            if self.wait_until_appear(self.I_GREEN_MARK, wait_time=1):
                # logger.info("识别到绿标,返回")
                break
            if mark_timer.reached():
                # logger.warning("识别绿标超时,返回")
                break
            # 点击绿标
            self.device.click(x, y)
