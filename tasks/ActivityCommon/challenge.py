# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from time import sleep

import os
import random
from cached_property import cached_property
from datetime import datetime, timedelta
from module.atom.ocr import RuleOcr
from module.base.timer import Timer
from module.exception import TaskEnd
from module.logger import logger
from tasks.ActivityCommon.config import NumberType, ModeType
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.page import page_main, page_all_active
from tasks.Restart.assets import RestartAssets
from tasks.ActivityCommon.assets import ActivityCommonAssets
from tasks.ActivityCommon.config import ActiveType
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig


class Challenge(SwitchSoul, GeneralBattle, ActivityCommonAssets):
    """ 战斗 """
    SoulsFUll = False
    fire = None
    each_limit_second = 0
    challenge_folder = "./tasks/ActivityCommon/挑战"
    temp_folder = "./tasks/ActivityCommon/临时"
    temp_challenge_templates = []
    active_type = ActiveType.battle

    def run_config(self, config):
        battle_active_type = config.activity_common_config.active_type
        self.active_type = battle_active_type
        goto_challenge_folder = f"./tasks/ActivityCommon/{battle_active_type}"

        # 加载进入挑战界面图片列表
        goto_challenge_templates = self._load_image_template(goto_challenge_folder, threshold=0.84)
        # 加载挑战图片列表
        challenge_templates = self._load_image_template(self.challenge_folder, roi_front=(1100, 540, 170, 170), roi_back=(819,471,457,244))

        self.temp_challenge_templates = self._load_image_template(self.temp_folder, threshold=0.8)

        logger.hr(f"开始 {battle_active_type} 任务", 2)

        # 切换御魂
        if config.switch_soul_config.enable:
            self.run_switch_soul(config.switch_soul_config.switch_group_team)
        if config.switch_soul_config.enable_switch_by_name:
            self.run_switch_soul_by_name(config.switch_soul_config.group_name, config.switch_soul_config.team_name)

        # 跳转到活动挑战页面
        self.goto_challenge(config, goto_challenge_templates, challenge_templates)

        # 开始战斗流程
        self.start_battle(config)

        if config.activity_common_config.active_souls_clean:
            self.set_next_run(task='SoulsTidy', success=False, finish=False, target=datetime.now())

        self.push_notify(f"✅ {battle_active_type} 挑战完成")
        self.set_next_run()
        raise TaskEnd

    def enter_battle(self) -> bool | None:
        """进入战斗
        :return: True:进入成功 False:进入失败
        """
        click_cnt, max_click = 0, random.randint(4, 6)
        while True:
            self.screenshot()
            if self.is_in_battle(False):
                return True  # 成功进入战斗
            if click_cnt >= max_click:  # 异常情况,怎么都无法进入
                return False
            if self.appear_then_click(self.fire, interval=1):  # 挑战按钮
                self.device.stuck_record_clear()
                click_cnt += 1
                continue
            for template in self.temp_challenge_templates:
                if self.appear_then_click(template, interval=1):
                    continue
            # if self.appear_then_click(self.I_BACK_RED, interval=1):  # ❌号
            #     continue

    def start_battle(self, config):

        limit_time = config.activity_common_config.limit_time
        enable = config.activity_common_config.enable
        if enable:
            # 限制次数
            self.limit_count = config.activity_common_config.limit_count
            # 限制时间
            self.limit_time: timedelta = timedelta(hours=limit_time.hour, minutes=limit_time.minute,
                                                   seconds=limit_time.second)
        # 每场战斗限制秒数
        self.each_limit_second = config.activity_common_config.each_limit_second

        # 切换预设的队伍上阵， 要求是在不锁定队伍时的情况下
        preset_enable = config.switch_soul_config.preset_enable
        switch_group_team = config.switch_soul_config.switch_group_team
        preset_group, preset_team = self.switch_parser(switch_group_team)

        general_battle_config = GeneralBattleConfig(
            lock_team_enable=not preset_enable,
            preset_enable=preset_enable,
            preset_group=preset_group,
            preset_team=preset_team
        )

        while True:
            if enable:
                if datetime.now() - self.start_time > self.limit_time:
                    self.push_notify(f"{self.limit_time} 时间限制已到，结束任务", image_type=False)
                    break
                if self.current_count >= self.limit_count:
                    self.push_notify(f"{self.limit_count} 次数限制已到，结束任务", image_type=False)
                    break
            # 判断是否有更高优先级任务，去执行新任务
            if config.activity_common_config.enable_check_first_priority_task:
                self._check_first_priority_task()
            # 是否判断门票次数 OCR识别
            if config.check_battle_config.enable:
                if self.check_battle(config):
                    break
            # 进入战斗
            if not self.enter_battle():
                break
            # 开始战斗
            self.run_general_battle(general_battle_config)

    def battle_wait(self, random_click_swipt_enable: bool):
        self.device.stuck_record_add(650)
        self.device.click_record_clear()
        click_list = [self.I_WIN, self.I_FALSE, self.I_UI_REWARD, self.I_REWARD, self.I_REWARD_GOLD, self.I_GREED_GHOST,
                      self.I_REWARD_STATISTICS, self.I_REWARD_PURPLE_SNAKE_SKIN,
                      self.I_SOUL_JADE]
        run_timer = Timer(self.each_limit_second)
        if self.each_limit_second > 0:
            run_timer.start()
        while 1:
            self.screenshot()

            if self.appear(self.fire):
                logger.info('战斗完成,退出')
                break

            if self.appear(self.temp_challenge_templates):
                logger.info('检测到临时,退出')
                break

            if run_timer.started() and run_timer.reached():
                logger.info(f'已到本场战斗时间{self.each_limit_second}秒, 退出')
                self.exit_battle()
                run_timer.reset()
                continue

            # 处理战斗类元素
            action_click = self.get_random_reward_action([self.C_REWARD_LEFT])
            if any(self.appear_then_click(item, action=action_click, interval=1) for item in click_list):
                continue
            if self.active_type != ActiveType.huanjing:
                if self.appear_then_click(self.I_BACK_RED):
                    continue
            # 误点聊天频道会自动关闭
            if self.appear_then_click(RestartAssets.I_HARVEST_CHAT_CLOSE):
                self.device.stuck_record_add('BATTLE_STATUS_S')
                continue
            if self.appear_then_click(self.I_SOUL_FULL_ENSURE):
                if not self.SoulsFUll:
                    self.push_notify("御魂溢出")
                    self.SoulsFUll = True
                    self.set_next_run(task='SoulsTidy', target=datetime.now())
                continue

            # 如果开启战斗过程随机滑动
            if random_click_swipt_enable:
                self.random_click_swipt()

    def check_battle(self, config):

        # 使用实例属性缓存，基于config生成唯一标识
        cache_key = id(config.check_battle_config)

        if not hasattr(self, '_battle_cache'):
            self._battle_cache = {}

        if cache_key not in self._battle_cache:
            con = config.check_battle_config
            roi = tuple(map(int, con.ocr_number_roi.split(',')))
            mode = con.ocr_number_mode
            limit_ocr_number = con.limit_ocr_number
            number_type = con.number_type
            O_NUMBER = RuleOcr(roi=roi, area=roi, mode=mode, method="Default", keyword="", name="number")

            self._battle_cache[cache_key] = {
                'roi': roi,
                'mode': mode,
                'limit_ocr_number': limit_ocr_number,
                'number_type': number_type,
                'O_NUMBER': O_NUMBER
            }

        # 使用缓存的数据
        cached = self._battle_cache[cache_key]
        roi = cached['roi']
        mode = cached['mode']
        limit_ocr_number = cached['limit_ocr_number']
        number_type = cached['number_type']
        O_NUMBER = cached['O_NUMBER']

        logger.info(f"RuleOcr(roi={roi}, area={roi}, mode=f'{mode}', method=\"Default\", keyword=\"\", name=\"number\")")
        self.wait_until_stable(
            self.fire,
            timer=Timer(limit=0.5, count=2),
            timeout=Timer(2, count=10)
        )

        if mode == ModeType.DigitCounter:
            cu, res, total = self.ocr_result(O_NUMBER)
            if 0 < total == cu + res:
                should_notify = False
                if number_type == NumberType.Ticket:
                    if cu <= limit_ocr_number:
                        should_notify = True
                elif number_type == NumberType.Battle:
                    if cu >= limit_ocr_number:
                        should_notify = True

                if should_notify:
                    self.push_notify(content=f"限制{limit_ocr_number}次已完成: {cu}/{total}", image_type=False)
                    return True
        return False

    def goto_challenge(self, config, goto_challenge_templates, challenge_templates):
        """
        跳转到活动挑战页面
        """
        # goto_challenge = config.activity_common_config.goto_challenge_path
        # active_type = config.activity_common_config.active_type
        # goto_challenge_list = goto_challenge.split(',')
        ocr_goto_challenge_list = []

        # # 加载第一个ocr文字描述（活动名称）
        # if goto_challenge and goto_challenge_list and ActiveType.battle == active_type:
        #     self.O_OCR_ACTIVE.keyword = goto_challenge_list[0]
        #
        #     # 加载剩余ocr文字描述（进入挑战名称）
        #     if len(goto_challenge_list) > 1:
        #         roi = self.O_OCR_ACTIVE_BATTLE.roi
        #         ocr_goto_challenge_list = [
        #             RuleOcr(roi=roi, area=roi, mode="FULL", method="Default",keyword=f"{goto_challenge_str}", name=f"{goto_challenge_str}")
        #             for goto_challenge_str in goto_challenge_list[1:]
        #         ]
        #
        #     # 开始执行跳转逻辑
        #     self.ui_goto_page(page_all_active)
        #     while 1:
        #         self.screenshot()
        #         if self.appear(self.I_GOTO_ACTIVE) and self.appear(self.I_ACTIVE_STORE):
        #             break
        #         if self.ocr_appear_click(self.O_OCR_ACTIVE):
        #             logger.info(f'点击前往活动')
        #
        #     # 前往活动按钮消失
        #     self.ui_click_until_disappear(self.I_GOTO_ACTIVE)
        # else:
        self.ui_goto_page(page_main)

        while 1:
            self.screenshot()

            # 获得奖励
            if self.ui_reward_appear_click():
                continue
            # 误点聊天频道会自动关闭
            if self.appear_then_click(RestartAssets.I_HARVEST_CHAT_CLOSE):
                continue

            # 两种点击方式 进入挑战页面
            if any(self.appear_then_click(target, interval=1.5)
                   for target in goto_challenge_templates + ocr_goto_challenge_list):
                sleep(1)
                continue

            # 先计算所有匹配结果，再找最佳
            match_results = []
            for target in challenge_templates:
                match_result = target.match(self.device.image)
                if match_result:  # 只保留匹配成功的
                    match_results.append((target, target.max_val))

            if match_results:
                best_target, max_val = max(match_results, key=lambda x: x[1])  # 按置信度取最高
                logger.hr("已在挑战界面", 2)
                logger.info(f"最高置信度: [{best_target} {max_val}]")
                self.fire = best_target
                return



if __name__ == '__main__':
    from module.config.config import Config

    c = Config('16448-切换')
    t = Challenge(c)
    # t.screenshot()

    config = c.activity_common
    # config = c.activity_common_2

    t.run_config(config)
    # t.check_battle(config)
