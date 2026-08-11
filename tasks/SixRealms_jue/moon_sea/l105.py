from module.logger import logger
from tasks.SixRealms_jue.moon_sea.skills import MoonSeaSkills


class MoonSeaL105(MoonSeaSkills):

    def run_l105(self):
        """
        绽放之屿
        @return:
        """
        logger.hr('绽放之屿')
        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_ZHAOFU, interval=1):
                break
        self.cnt_zhanfang += 1
        logger.info(f'绽放之屿: {self.cnt_zhanfang}')
        return True


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('du')
    t = MoonSeaL105(c)
    t.screenshot()

    t.run_l105()
