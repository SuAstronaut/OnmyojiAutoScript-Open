# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from datetime import time, datetime, timedelta
from time import sleep

from module.base.timer import Timer
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.GeneralBattle.config_general_battle import GreenMarkType
from tasks.Component.GreenMark.green_mark import GreenMark
from tasks.Component.SwitchOnmyoji.switch_onmyoji import SwitchOnmyoji
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.page import page_onmyodo, page_duel


class ScriptTask(SwitchSoul, SwitchOnmyoji, GreenMark):
    """ 斗技 """
    battle_win_count = 0
    battle_lose_count = 0

    def run(self):

        current_time = datetime.now().time()
        if not (time(12, 00) <= current_time < time(23, 00)):
            logger.warning('不在斗技时间段')
            self.set_next_run(task='Duel', success=True, finish=False)
            raise TaskEnd('Duel')

        con = self.config.duel
        # 切换御魂
        if con.switch_soul.enable:
            self.run_switch_soul(con.switch_soul.switch_group_team)
        if con.switch_soul.enable_switch_by_name:
            self.run_switch_soul_by_name(con.switch_soul.group_name,con.switch_soul.team_name)

        con = self.config.duel.duel_config
        celeb_con = self.config.duel.duel_celeb_config
        push_notify_enable = self.config.duel.push_notify.enable
        limit_time = con.limit_time
        self.limit_time: timedelta = timedelta(hours=limit_time.hour, minutes=limit_time.minute, seconds=limit_time.second)

        # 切换阴阳师
        if con.switch_enabled:
            self.ui_goto_page(page_onmyodo)
            self.switch_onmyoji(con.switch_onmyoji)
        self.ui_goto_page(page_duel)
        # 切换御魂
        if con.switch_all_soul:
            self.switch_all_soul()

        # 循环
        duel_week_over = False
        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_D_VICTORY, interval=0.6):
                continue
            if self.appear_then_click(self.I_WIN, interval=0.6):
                continue
            if self.appear_then_click(self.I_REWARD, interval=0.6):
                continue
            if self.appear_then_click(self.I_CANCEL, interval=0.6):
                continue
            if self.appear_then_click(self.I_BACK_RED, interval=0.6):
                continue
            if not self.appear(self.I_CHECK_DUEL):
                continue
            # if not self.duel_main():
            #     continue

            # 判断是否有更高优先级任务，去执行新任务
            self._check_first_priority_task()

            # 检查分数
            current_score = self.check_score()

            if celeb_con.avoid_celeb and current_score == 3000:
                # 3000分，退出 避免掉落名仕
                self.push_notify(f'分数: {current_score}, 本周斗技结束, 避免掉落名仕')
                duel_week_over = True
                break

            if datetime.now() - self.start_time >= self.limit_time:
                # 任务执行时间超过限制时间，退出
                logger.info('斗技任务超时')
                break

            # 不开启名仕战斗,到达名士直接退出
            if not celeb_con.celeb_battle:
                if self.appear(self.I_D_CELEB_STAR) or self.appear(self.I_D_CELEB_HONOR):
                    logger.info('你已是名仕')
                    current_score = "名仕"
                    duel_week_over = True
                    break

            # if con.honor_full_exit and self.check_honor():
            #     # 荣誉满了，退出
            #     logger.info('斗技任务荣誉点已达上限')
            #     break

            # 当前分数跟目标分数比较
            if current_score >= con.target_score:
                # 分数够了
                logger.info('斗技任务分数已达上限')
                # 是否刷满荣誉就退出
                if con.honor_full_exit:
                    if self.check_honor():
                        # 荣誉满了，退出
                        # self.save_image(content=f'分数: {current_score}, 本周斗技结束', push_flag=True)
                        logger.info('斗技任务荣誉点已达上限')
                        duel_week_over = True
                        break
                else:
                    break

            # 练习
            if self.appear(self.I_BATTLE_WITH_TRAIN) or self.appear(self.I_BATTLE_WITH_TRAIN2):
                logger.info('不在斗技时间')
                break

            # 进行一次斗技
            self.duel_one(current_score, con.green_enable, con.green_mark, celeb_con.ban_name)

        logger.info('斗技战斗结束')
        if self.current_count > 0 and push_notify_enable:
            self.push_notify(f'场次: {self.current_count} | 胜: {self.battle_win_count} 败: {self.battle_lose_count} | 分数: {current_score}')

        if duel_week_over:
            self.next_run_week(self.config.duel.switch_week.next_week_day)
        else:
            self.set_next_run(task='Duel', success=True, finish=False)

        # 调起花合战
        # self.set_next_run(task='TalismanPass', target=datetime.now())
        raise TaskEnd('Duel')

    def duel_main(self, screenshot=False) -> bool:
        """
        判断是否斗技主界面
        :return:
        """
        if screenshot:
            self.screenshot()
        return self.appear(self.I_D_HELP) or self.appear(self.I_D_CELEB_STAR) or self.appear(self.I_D_CELEB_HONOR)

    def switch_all_soul(self):
        """
        一键切换所有御魂
        :return:
        """
        click_count = 0  # 计数
        while 1:
            self.screenshot()
            if click_count >= 4:
                break

            if self.appear_then_click(self.I_D_TEAM, interval=1):
                continue
            if self.appear_then_click(self.I_UI_SURE, interval=0.6):
                continue
            if self.appear_then_click(self.I_D_TEAM_SWTICH, interval=1):
                click_count += 1
                continue
        logger.info('御魂切换完成')
        self.ui_click(self.I_BACK_YELLOW, self.I_D_TEAM)

    def check_honor(self) -> bool:
        """
        检查荣誉是否满了
        :return:
        """
        ocr_list = [self.O_D_HONOR, self.O_D_HONOR1]

        for ocr in ocr_list:
            current, remain, total = ocr.ocr(self.device.image)
            # 如果识别到有效数据，直接判断
            if total != 0:
                logger.info(f'当前荣誉: {current} / {total} 剩余: {remain}')
                return current == total

        # 如果仍无法识别，返回True作为默认值
        self.push_notify('荣誉未识别，请检查图片,默认荣誉已满')
        return True

    def check_score(self) -> int or None:
        """
        检查是否达到目标分数
        :param target: 目标分数
        :return:
        """
        while 1:
            self.screenshot()
            if self.appear(self.I_D_CELEB_STAR) or self.appear(self.I_D_CELEB_HONOR):
                current_score = self.O_D_CELEB_STAR.ocr(self.device.image)
                # score = self.O_D_CELEB_STAR.max_score
                # if score < 0.7:
                #     continue
                logger.info(f"当前分数: 名仕({current_score}星)")
                current_score = 3000 + current_score * 100
            else:
                current_score = self.O_D_SCORE.ocr(self.device.image)
                if current_score > 10000:
                    # 识别错误分数超过一万, 去掉最高位
                    logger.warning('识别错误，分数过高')
                    current_score = int(str(current_score)[1:])
            return current_score

    def duel_one(self, current_score: int, enable: bool = False,
                 mark_mode: GreenMarkType = GreenMarkType.GREEN_MAIN, ban_name: str = '') -> bool:
        """
        进行一次斗技， 返回输赢结果
        :param mark_mode:
        :param enable:
        :param current_score: 当前分数, 不同的分数有不同的战斗界面
        :return:
        """
        logger.hr('Duel battle', 2)
        self.current_count += 1
        # 是否名士
        celeb_status = False
        while 1:
            self.screenshot()
            # 如果对方直接秒退，那自己就是赢的
            if self.appear(self.I_D_VICTORY):
                self.ui_click_until_disappear(self.I_D_VICTORY)
                self.battle_win_count += 1
                return
            if self.appear(self.I_D_AUTO_ENTRY) or self.appear(self.I_D_PREPARE):
                break
            # 名士以上禁用
            if self.appear_then_click(self.I_BAN, interval=3):
                celeb_status = True
                continue
            # 战斗按钮
            if self.appear_then_click(self.I_D_BATTLE, interval=1) or self.appear_then_click(self.I_D_BATTLE2, interval=1):
                continue
            # 战斗带保护的按钮
            if self.appear_then_click(self.I_D_BATTLE_PROTECT, interval=1.6):
                continue
            # # 斗技模式（普通）
            # if self.appear_then_click(self.I_BATTLE_TYPE_COMMON, interval=1):
            #     continue
            # # 练习
            # if self.appear_then_click(self.I_BATTLE_WITH_TRAIN, interval=1) or self.appear_then_click(self.I_BATTLE_WITH_TRAIN2, interval=1):
            #     continue
            if self.appear(self.I_BATTLE_WITH_TRAIN) or self.appear(self.I_BATTLE_WITH_TRAIN2):
                return
        # 点击斗技 开始匹配对手
        logger.hr('斗技开始匹配')
        while 1:
            self.screenshot()
            # 出现自动上阵
            if self.appear(self.I_D_AUTO_ENTRY):
                ban_check_success = True
                if celeb_status:
                    # 检查禁选式神
                    name_timer = Timer(5)
                    name_timer.start()
                    duel_click_list = [self.C_DUEL_CLICK_1, self.C_DUEL_CLICK_2, self.C_DUEL_CLICK_3, self.C_DUEL_CLICK_4, self.C_DUEL_CLICK_5]
                    ban_name_list = ban_name.replace('，', ',').split(',')
                    ban_name_list = [name.strip() for name in ban_name_list if name.strip()]
                    # 填充 ban_name_list 确保至少有5个元素
                    while len(ban_name_list) < 5:
                        ban_name_list.append("")  # 添加空字符串作为默认值
                    logger.info(f'禁选式神列表: {ban_name_list}')

                    for i, click in enumerate(duel_click_list):
                        if not ban_check_success:
                            break
                        while 1:
                            if name_timer.reached():
                                logger.warning(f'斗技检测式神名称超时, 退出')
                                ban_check_success = False
                                break

                            self.click(click)
                            sleep(0.5)
                            self.screenshot()
                            # 如果对方直接秒退，那自己就是赢的
                            if self.appear(self.I_D_VICTORY):
                                self.ui_click_until_disappear(self.I_D_VICTORY)
                                self.battle_win_count += 1
                                return
                            ocr_ban_name = self.O_D_BAN_NAME.ocr(self.device.image)
                            if ocr_ban_name == '':
                                continue
                            name_timer.reset()
                            if ocr_ban_name == ban_name_list[i]:
                                logger.info(f'斗技式神未被禁选')
                                ban_check_success = True
                                break
                            else:
                                logger.warning(f'[{ocr_ban_name}] 与 [{ban_name_list[i]}] 不一致, 退出')
                                logger.warning(f'❌ 斗技式神被禁选, 退出')
                                ban_check_success = False
                                break

                # 处理检查结果
                if not ban_check_success:
                    self.exit_battle()
                    if self.appear(self.I_D_FAIL):
                        # 输了
                        self.ui_click_until_disappear(self.I_D_FAIL)
                        self.battle_lose_count += 1
                    return

                # 等待自动上阵消失
                logger.info('斗技开始自动上阵')
                self.ui_click_until_disappear(self.I_D_AUTO_ENTRY)
                self.device.stuck_record_clear()
                self.device.stuck_record_add('BATTLE_STATUS_S')
                self.wait_until_disappear(self.I_D_WORD_BATTLE)
                break
            if self.appear(self.I_D_PREPARE):
                # 低段位有的准备
                self.ui_click_until_disappear(self.I_D_PREPARE)
                self.wait_until_disappear(self.I_D_PREPARE_DONE)
                logger.info('斗技准备')
                break
            # 如果对方直接秒退，那自己就是赢的
            if self.appear(self.I_D_VICTORY):
                self.ui_click_until_disappear(self.I_D_VICTORY)
                self.battle_win_count += 1
                return
        # 正式进入战斗
        logger.info('斗技开始自动战斗')
        timer = Timer(10)
        timer.start()
        while 1:
            if timer.reached():
                break
            if self.is_in_battle():
                break
        while 1:
            self.screenshot()
            if self.ocr_appear(self.O_D_AUTO, interval=1):
                break
            if self.ocr_appear_click(self.O_D_HAND, interval=1):
                continue
            # 如果对方直接秒退，那自己就是赢的
            if self.appear(self.I_D_VICTORY):
                self.ui_click_until_disappear(self.I_D_VICTORY)
                self.battle_win_count += 1
                return
            if self.appear(self.I_D_FAIL):
                # 输了
                self.ui_click_until_disappear(self.I_D_FAIL)
                self.battle_lose_count += 1
                return
        # 绿标
        if enable:
            if not self.green_mark_ocr(mark_mode):
                self.green_mark_new(mark_mode)
        # 等待结果
        logger.info('等待斗技结果')
        self.device.stuck_record_add('BATTLE_STATUS_S')
        self.device.click_record_clear()
        battle_win = True
        swipe_count = 0
        swipe_timer = Timer(270)
        swipe_timer.start()
        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_D_BATTLE_DATA, action=self.C_D_BATTLE_DATA, interval=0.6):
                continue
            if self.appear(self.I_FALSE):
                # 打输了
                self.ui_click_until_disappear(self.I_FALSE)
                battle_win = False
                break
            if self.appear(self.I_D_FAIL):
                # 输了
                self.ui_click_until_disappear(self.I_D_FAIL)
                battle_win = False
                break
            if self.appear(self.I_WIN):
                # 打赢了
                self.ui_click_until_disappear(self.I_WIN)
                battle_win = True
                break
            if self.appear(self.I_D_VICTORY):
                # 打赢了
                self.ui_click_until_disappear(self.I_D_VICTORY)
                battle_win = True
                break

            if swipe_timer.reached():
                swipe_timer.reset()
                if swipe_count >= 2:
                    # 记三次，十五分钟没有结束也没谁了
                    logger.info('斗技战斗超时')
                    battle_win = False
                    break
                swipe_count += 1
                logger.warning('斗技战斗卡住，滑动屏幕')
                self.device.stuck_record_clear()
                self.device.stuck_record_add('BATTLE_STATUS_S')

        if battle_win:
            self.battle_win_count += 1
        else:
            self.battle_lose_count += 1

        task_run_time = datetime.now() - self.start_time
        # 格式化时间，只保留整数部分的秒
        task_run_time_seconds = timedelta(seconds=int(task_run_time.total_seconds()))

        logger.info(f'战斗结果: {battle_win}')
        logger.info(f'战斗次数: {self.current_count} | 胜利: {self.battle_win_count} 失败: {self.battle_lose_count}')
        logger.info(f'战斗用时: {task_run_time_seconds} / {self.limit_time}')
        return battle_win




if __name__ == '__main__':
    from module.config.config import Config

    c = Config('mi')
    t = ScriptTask(c)

    t.run()
