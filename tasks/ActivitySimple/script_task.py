from datetime import datetime, timedelta
from time import sleep

from module.base.timer import Timer
from module.exception import TaskEnd
from module.logger import logger
from tasks.ActivityCommon.challenge import Challenge
from tasks.Component.GeneralBattle.config_general_battle import GreenMarkType
from tasks.Component.GreenMark.green_mark import GreenMark


class ScriptTask(GreenMark, Challenge):
    ocr_target = False

    def run(self) -> None:
        timer = Timer(10).start()
        while 1:
            logger.warning("请在挑战界面，开始简单爬塔!!!")
            if self.get_best_fire():
                break
            else:
                if not timer.reached():
                    sleep(1)
                    continue
                logger.warning("未找到挑战按钮")
                self.set_next_run()
                raise TaskEnd

        self.start_battle(self.config.activity_simple)

        self.set_next_run()
        self.push_notify(f"✅ 简单爬塔 挑战完成")
        raise TaskEnd


    def start_battle(self, conf):
        config = conf.simple_config
        limit_time = config.limit_time
        # 限制次数
        self.limit_count = config.limit_count
        # 限制时间
        self.limit_time: timedelta = timedelta(hours=limit_time.hour, minutes=limit_time.minute,
                                               seconds=limit_time.second)

        while True:
            if self.limit_time + self.start_time < datetime.now():
                logger.info("时间已到")
                break
            if self.current_count >= self.limit_count:
                logger.info("次数已到")
                break
            entered = self.enter_battle()
            if not entered:
                break
            if self.run_general_battle(config=conf.general_battle):
                logger.info("通用战斗成功")

    def green_mark(self, enable: bool = False, mark_mode: GreenMarkType = GreenMarkType.GREEN_MAIN):
        """
        :param enable: 是否启用
        :param mark_mode: 模式
        :return:
        """
        if enable:
            if not self.green_mark_ocr(mark_mode, self.ocr_target):
                logger.info("未识别到式神（青）")
                self.ocr_target = True
                self.green_mark_ocr(mark_mode, self.ocr_target)

    def get_best_fire(self):
        challenge_templates = self._load_image_template(self.challenge_folder, roi_front=(1100, 540, 170, 170), roi_back=(819,471,457,244))
        self.screenshot()
        # 先计算所有匹配结果，再找最佳
        match_results = []
        for target in challenge_templates:
            match_result = target.match(self.device.image)
            if match_result:  # 只保留匹配成功的
                match_results.append((target, target.max_val))

        if match_results:
            best_target, max_val = max(match_results, key=lambda x: x[1])  # 按置信度取最高
            self.fire = best_target
            logger.hr("已在挑战界面", 2)
            logger.info(f"最高置信度: [{best_target} {max_val}]")
            return True
        else:
            return False


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('wy')
    t = ScriptTask(c)
    # t.screenshot()

    t.run()
