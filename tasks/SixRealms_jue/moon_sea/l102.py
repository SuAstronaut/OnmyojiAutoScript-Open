
from module.logger import logger
from tasks.SixRealms_jue.moon_sea.skills import MoonSeaSkills


class MoonSeaL102(MoonSeaSkills):
    def run_l102(self):
        logger.hr('开始神秘之屿')
        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_BACK_EXIT, interval=1):
                break

    def imitate(self):
        # 仿造
        logger.info('仿造')
        cnt_imitate = 0
        while 1:
            self.screenshot()
            if self.in_main():
                break
            if self.cnt_skill101 >= 5:
                if self.appear_then_click(self.I_BACK_EXIT, interval=2):
                    continue
            if self.appear_then_click(self.I_IMITATE_1, interval=2.5):
                continue
            if self.appear_then_click(self.I_UI_CONFIRM, interval=1):
                continue
            if self.appear_then_click(self.I_UI_SURE, interval=1):
                continue
            if cnt_imitate >= 3:
                logger.info('仿造失败，可能技能已满级')
                while 1:
                    self.screenshot()
                    if self.in_main():
                        break
                    if self.appear_then_click(self.I_BACK_EXIT, interval=2):
                        continue
                break
            if self.appear_then_click(self.I_IMITATE, interval=1):
                cnt_imitate += 1
                continue
        self.cnt_skill101 += 1
        logger.info(f'轰雷等级: {self.cnt_skill101}')
        logger.info('完成仿造')


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('du')
    t = MoonSeaL102(c)
    t.screenshot()

    t.run_l102()
