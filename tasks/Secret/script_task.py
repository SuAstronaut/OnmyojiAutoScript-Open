# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

from cached_property import cached_property
from module.atom.ocr import RuleOcr
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralBuff.config_buff import BuffClass
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.page import page_main, page_secret_zones
from tasks.Restart.assets import RestartAssets
from tasks.Secret.assets import SecretAssets
from tasks.Secret.config import Secret
from tasks.WeeklyTrifles.assets import WeeklyTriflesAssets

""" 秘闻 """


class ScriptTask(GeneralBattle, SwitchSoul, SecretAssets):
    lay_list = ['壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖', '拾']

    @cached_property
    def match_layer(self) -> dict:
        return {
            '壹': 1, '贰': 2,
            '叁': 3, '肆': 4,
            '伍': 5, '陆': 6,
            '柒': 7, '捌': 8,
            '玖': 9, '拾': 10,
        }

    @cached_property
    def battle_config(self) -> GeneralBattleConfig:
        conf = self.config.model.secret.general_battle
        # 为了开启金币加成
        conf.lock_team_enable = False
        return conf

    def run(self):
        secret: Secret = self.config.secret
        con = secret.secret_config
        if secret.switch_soul.enable:
            self.run_switch_soul(secret.switch_soul.switch_group_team)
        if secret.switch_soul.enable_switch_by_name:
            self.run_switch_soul_by_name(secret.switch_soul.group_name, secret.switch_soul.team_name)
        self.ui_goto_page(page_secret_zones)

        # 进入
        success = True
        self.ui_click(self.I_SE_ENTER, self.I_SE_FIRE)
        time.sleep(1)  # 有一个很傻逼的动画
        self.screenshot()
        if not self.appear(self.I_SE_PLACEMENT):
            logger.warning('进入失败。您之前必须已进入秘闻副本。')
            success = False

        # 开始
        logger.info('开始秘闻副本')
        first_battle = True
        while 1:
            self.screenshot()
            if not success:
                logger.warning('秘闻副本进入失败，跳过')
                break
            if not self.appear(self.I_SE_FIRE):
                continue
            if self.appear(self.I_SE_FINISHED_1):
                logger.info('秘闻副本完成')
                break
            layer = self.find_battle()
            logger.info(f'当前层数: {layer}')
            if not layer:
                if self.appear(WeeklyTriflesAssets.I_WT_SE_SHARE):
                    logger.warning('您已完成每周琐事，跳过')
                    break
                continue
            if layer >= 6:
                first_battle = False
            if first_battle and layer <= 5:
                first_battle = False
                buff = []
                if con.secret_gold_50:
                    buff.append(BuffClass.GOLD_50)
                if con.secret_gold_100:
                    buff.append(BuffClass.GOLD_100)
                self.click_battle()
                success = self.run_general_battle(self.battle_config, buff=buff)
                continue
            if not first_battle and layer == 6:
                # 第六次关闭加成，但是发现没有这个接口。。。！！！居然没有注意到
                buff = []
                if con.secret_gold_50:
                    buff.append(BuffClass.GOLD_50_CLOSE)
                if con.secret_gold_100:
                    buff.append(BuffClass.GOLD_100_CLOSE)
                self.click_battle()
                success = self.run_general_battle(self.battle_config, buff=buff)
                continue
            elif not first_battle and layer == 9 and con.layer_9:
                self.click_battle()
                success = self.run_general_battle(self.battle_config)
                continue
            elif not first_battle and layer == 10 and con.layer_10:
                self.click_battle()
                success = self.run_general_battle(self.battle_config)
                break
            elif not first_battle:
                # 其他层
                self.click_battle()
                success = self.run_general_battle(self.battle_config)
                continue

        self.save_image()
        # 设置下一次运行时间是周一
        self.next_run_week(1)

        if con.secret_gold_50 or con.secret_gold_100:
            buff = [BuffClass.GOLD_50_CLOSE, BuffClass.GOLD_100_CLOSE]
            self.check_buff(buff)

        # self.set_next_run(task='Secret', success=True, finish=False)
        raise TaskEnd('Secret')

    def find_battle(self, screenshot: bool = False) -> int or None:
        """
        自动寻找挑战的层数并且选定 , 找不到会向下划一点
        :return: 如果找得到返回层数，找不到返回None
        """

        def set_layer_roi(ocr_target: RuleOcr, roi: tuple):
            ocr_target.roi[0] = int(roi[0]) - 225
            ocr_target.roi[1] = int(roi[1]) - 40

        def check_layer(ocr_target: RuleOcr, roi=None) -> int or None:
            #
            # 手动留了一个bug： 即使匹配到了未通关 但是在判断层数的时候还是会先判断第一个是什么的
            level = ocr_target.ocr(self.device.image)
            if not isinstance(level, str):
                logger.warning(f'OCR失败，重试 {level}')
            level = level.replace('·', '').replace(' ', '').replace('。', '').replace('武', '贰')
            if level not in self.lay_list and roi:
                print(roi)
                print(ocr_target.roi)
                set_layer_roi(ocr_target, roi)
                self.screenshot()
                level = ocr_target.ocr(self.device.image)
            if level not in self.lay_list:
                return None
            try:
                return self.match_layer[level]
            except KeyError:
                logger.warning(f'OCR失败，重试 {level}')
                return None

        def confirm_layer(ocr_target: RuleOcr, roi=None) -> int or None:
            """
            检查层数， 启用函数check_layer
            :param ocr_target:
            :param roi:
            :return:
            """
            ocr_target.roi[0] = int(roi[0]) - 118
            ocr_target.roi[1] = int(roi[1]) + 37
            logger.info(f'检测到的未通过ROI: {roi}')
            logger.info(f'检测到的勾玉数量ROI: {ocr_target.roi}')
            jade_num = ocr_target.ocr(self.device.image)
            if isinstance(jade_num, str):
                logger.warning(f'OCR失败，重试 {jade_num}')
                return None
            elif not isinstance(jade_num, int):
                logger.warning(f'OCR失败，重试 {jade_num}')
                return None
            if jade_num < 7:
                # 第一个的时候可能是没有检测到
                gold_number = self.O_SE_GOLD.ocr(self.device.image)
                if isinstance(gold_number, int) and (gold_number == 10000 or gold_number == 18000):
                    logger.info(f'未找到勾玉数量，但找到金币数量 {gold_number}')
                    return 1
                return None
            elif jade_num > 70:
                logger.warning(f'OCR失败，重试 {jade_num}')
                return None
            # 勾玉数量 = 层数 * 7
            try:
                lr = jade_num // 7
                return lr
            except TypeError:
                logger.warning(f'OCR失败，重试 {jade_num}')
                return None

        if screenshot:
            self.screenshot()
        if self.appear(self.I_CHAT_CLOSE_BUTTON):
            self.ui_click_until_disappear(self.I_CHAT_CLOSE_BUTTON, interval=2)
        text_pos = self.O_SE_NO_PASS.ocr(self.device.image)
        if text_pos != (0, 0, 0, 0):
            # 如果能找得到 未通关 ，那可以挑战
            layer = confirm_layer(self.O_SE_JADE, text_pos)
            if layer:
                self.C_SE_CLICK_LAYER.roi_front = text_pos
                self.click(self.C_SE_CLICK_LAYER, interval=1)
                return layer
            else:
                return None

        else:
            # 如果不是就向下滑动，继续找或者是判断
            last_text_pos = self.O_SE_NO_PASS_LAST.ocr(self.device.image)
            if last_text_pos != (0, 0, 0, 0):
                # 如果是后面找得到
                layer = confirm_layer(self.O_SE_JADE, last_text_pos)

                # 有个bug 十层的发现不了
                if not layer and last_text_pos[1] > 520:
                    layer = 10

                if layer:
                    self.C_SE_CLICK_LAYER.roi_front = last_text_pos
                    self.click(self.C_SE_CLICK_LAYER, interval=1)
                    return layer
                else:
                    return None

            else:
                # 如果不是就一直滑动
                self.swipe(self.S_SE_DOWN_SEIPE, interval=3)
                time.sleep(2)

    def click_battle(self):
        while 1:
            self.screenshot()
            if not self.appear(self.I_SE_FIRE):
                break
            if self.appear_then_click(self.I_SE_FIRE, interval=1):
                continue

    def battle_wait(self, random_click_swipt_enable: bool) -> bool:
        # 重写
        self.device.stuck_record_add('BATTLE_STATUS_S')
        self.device.click_record_clear()
        # 战斗过程 随机点击和滑动 防封
        while 1:
            self.screenshot()
            if self.appear(self.I_SE_BATTLE_WIN):
                logger.info('战斗胜利')
                while 1:
                    self.screenshot()
                    if self.appear_then_click(RestartAssets.I_HARVEST_CHAT_CLOSE, interval=2):
                        continue
                    if self.appear_then_click(self.I_SE_BATTLE_WIN, interval=2):
                        continue
                    if not self.appear(self.I_SE_BATTLE_WIN):
                        break
                return True
            if self.appear_then_click(self.I_WIN, interval=1):
                continue
            if self.appear(self.I_REWARD):
                logger.info('战斗胜利')
                self.ui_click_until_disappear(self.I_REWARD)
                return True

            if self.appear(self.I_FALSE):
                logger.warning('战斗失败')
                self.save_image(wait_time=0, push_flag=True, image_type=True, content="❌ 战斗失败")
                self.ui_click_until_disappear(self.I_FALSE)
                return False


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('du')
    t = ScriptTask(c)
    t.screenshot()

    t.run()
    # t.find_battle(False)
