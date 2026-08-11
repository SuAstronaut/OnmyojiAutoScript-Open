# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

import random
import re
from cached_property import cached_property
from datetime import datetime, timedelta
from module.atom.click import RuleClick
from module.atom.image_grid import ImageGrid
from module.atom.ocr import RuleOcr
from module.base.utils import point2str
from module.exception import TaskEnd, GameStuckError
from module.logger import logger
from tasks.GameUi.page import page_realm
from tasks.KekkaiActivation.assets import KekkaiActivationAssets
from tasks.KekkaiActivation.config import ActivationConfig
from tasks.KekkaiActivation.config import CardStar
from tasks.KekkaiActivation.config import CardType
from tasks.KekkaiUtilize.script_task import ScriptTask as KU
from tasks.KekkaiUtilize.utils import CardClass


class ScriptTask(KU, KekkaiActivationAssets):
    """ 结界挂卡 """
    def run(self):
        con = self.config.kekkai_activation.activation_config
        self.ui_goto_page(page_realm)

        if con.exchange_before:
            self.check_max_lv(con.shikigami_class)
        # 收取经验
        self.harvest_card()
        # 开始挂卡
        self.run_activation(con)
        self.ui_goto_page(page_realm)

        if con.exchange_max:
            self.check_max_lv(con.shikigami_class)

        raise TaskEnd('KekkaiActivation')

    @cached_property
    def dict_card_image(self) -> dict:
        match_targets = {
            CardClass.TAIKO6: self.I_CARDS_KAIKO_6,
            CardClass.TAIKO5: self.I_CARDS_KAIKO_5,
            CardClass.TAIKO4: self.I_CARDS_KAIKO_4,
            CardClass.TAIKO3: self.I_CARDS_KAIKO_3,
            CardClass.FISH6: self.I_CARDS_FISH_6,
            CardClass.FISH5: self.I_CARDS_FISH_5,
            CardClass.FISH4: self.I_CARDS_FISH_4,
            CardClass.FISH3: self.I_CARDS_FISH_3,
            CardClass.MOON6: self.I_CARDS_MOON_6,
            CardClass.MOON5: self.I_CARDS_MOON_5,
            CardClass.MOON4: self.I_CARDS_MOON_4,
            CardClass.MOON3: self.I_CARDS_MOON_3,
            CardClass.MOON2: self.I_CARDS_MOON_2,
            CardClass.MOON1: self.I_CARDS_MOON_1
        }
        return match_targets

    @cached_property
    def dict_image_card(self) -> dict:
        return {v: k for k, v in self.dict_card_image.items()}

    @cached_property
    def order_targets(self) -> ImageGrid:
        rule = self.config.kekkai_activation.activation_config.card_type
        if rule == CardType.TAIKO:
            return ImageGrid([self.I_CARDS_KAIKO_6, self.I_CARDS_KAIKO_5])
        elif rule == CardType.FISH:
            return ImageGrid([self.I_CARDS_FISH_6, self.I_CARDS_FISH_5])
        else:
            logger.error('未知的利用规则')
            raise ValueError('未知的结界利用规则')

    def run_activation(self, _config: ActivationConfig) -> bool:
        """
        执行挂卡，要求在结界的界面
        顺便把下一次执行也设置了
        :return: 挂卡成功（）返回True，失败(时间没到提前来了)返回False
        退出的时候还是在挂卡界面而不是结界界面
        """
        self.goto_cards()
        # 太诡异了 为什么有这么长的动画, 那么长的动画先休息一会
        logger.hr('开始激活')
        time.sleep(0.5)
        while 1:
            self.screenshot()
            card_status = self.check_card_status()
            card_effect = self.check_card_effect()

            # 不稳定太，等待动画结束
            if not card_status and not card_effect:
                # 黄色的 ”激活“
                if self.appear(self.I_A_ACTIVATE_YELLOW, threshold=0.95):
                    continue
                if self.appear(self.I_A_DEMOUNT):
                    # 现在在动画里面
                    logger.info('现在在动画中')
                    logger.info('现在没有结界卡')
                    continue
            # 如果这张卡生效着，在使用中
            if card_status and card_effect:
                logger.info('结界卡正在使用')
                interval = self.ocr_time()
                self.set_next_run("KekkaiActivation", success=False, finish=True, target=interval + datetime.now())
                return False
            # 如果已经选中这张卡了， 那就激活这张卡
            if card_status and not card_effect:
                logger.info('结界卡已选择但未使用')
                while 1:
                    self.screenshot()
                    if self.appear(self.I_A_INVITE, threshold=0.8):
                        logger.info('结界卡已激活')
                        break
                    if self.appear_then_click(self.I_UI_SURE, interval=0.6):
                        continue
                    if self.appear_then_click(self.I_A_ACTIVATE_YELLOW, interval=1):
                        continue
                interval = self.ocr_time(True)
                self.set_next_run("KekkaiActivation", success=True, finish=True, target=interval + datetime.now())
                return True
            # 如果是什么都没有，那就是可以开始挂卡了
            if not card_status and not card_effect:
                logger.info('结界卡未选择也未使用')
                self.screening_card(_config.card_type)

    def goto_cards(self):
        """
        寮结界,前往挂卡界面
        :return:
        """
        while 1:
            self.screenshot()

            if self.appear(self.I_A_CHECK_CARD):
                break
            if self.appear(self.I_A_AUTO_INVITE):
                break
            if self.appear_then_click(self.I_SHI_CARD, interval=1):
                continue
        logger.info('进入结界卡页面')

    def check_card_status(self, screenshot=False) -> bool:
        """
        判断使用有挂卡在上面了， 判断依据就是如果没看就可以显示背景图
        :param screenshot:
        :return: 如果有卡在上面了返回True，否则返回False
        """
        if screenshot:
            self.screenshot()
        return not self.appear(self.I_A_EMPTY)

    def check_card_effect(self, screenshot=False) -> bool:
        """
        检查这张卡是否生效了, 如果是出现的“邀请”那就是生效了， 如果是“激活”那就是还没生效
        :param screenshot:
        :return: 生效返回True
        """
        if screenshot:
            self.screenshot()
        if self.appear(self.I_A_INVITE, threshold=0.8):
            return True
        elif self.appear(self.I_A_ACTIVATE_YELLOW):
            return False
        logger.info('未知的结界卡效果')
        while 1:
            self.screenshot()
            if self.appear(self.I_A_INVITE, threshold=0.7):
                return True
            elif self.appear(self.I_A_ACTIVATE_YELLOW):
                return False
            elif self.appear(self.I_A_ACTIVATE_GRAY):
                return False

    def ocr_time(self, screenshot=False) -> timedelta or None:
        if screenshot:
            self.screenshot()
        delta = self.O_CARD_ALL_TIME.ocr_duration(self.device.image)
        if not isinstance(delta, timedelta):
            logger.warning('OCR 错误')
            return None
        if delta == timedelta(0):
            logger.error('检测到该结界卡剩余时间为0')
            logger.error('这可能是因为结界卡尚未收集')
            raise GameStuckError
        return delta

    def screening_card(self, rule: str):
        """
        开始挑选卡
        :return:
        """

        if rule == CardType.TAIKO:
            card_class = CardClass.TAIKO
            target_class = self.I_A_CARD_KAIKO
        elif rule == CardType.FISH:
            card_class = CardClass.FISH
            target_class = self.I_A_CARD_FISH
        else:
            logger.warning('未知的结界卡规则')
            self.push_notify(content='Unknown card rule')
            return

        while 1:
            self.screenshot()

            if self.appear(target_class):
                time.sleep(0.3)
                self.screenshot()
                if self.appear(target_class):
                    break
            if self.click(self.C_A_SELECT_CARD_LIST, interval=2.5):
                continue
        logger.info(f'出现结界卡类型: {card_class}')
        while 1:
            self.screenshot()
            if not self.appear(target_class):
                break
            if self.appear_then_click(target_class, interval=1):
                continue
        logger.info(f'已选择结界卡类型: {card_class}')

        # 找最优卡
        while 1:
            self.screenshot()
            target = self.check_card_num()
            if target is None:
                # 未发现卡，处理逻辑
                self._card_not_found()
            if self.appear(self.I_A_EMPTY):
                while 1:
                    self.screenshot()
                    if not self.appear(self.I_A_EMPTY):
                        def update_config():
                            self.config.kekkai_activation.activation_config.card_not_found_count = 0

                        self.config.safe_save(update_config)

                        message = f'✅ 确认挂卡: {rule}'
                        self.save_image(content=message, push_flag=False, wait_time=0)
                        return
                    if self.click(target, interval=1):
                        continue

    def check_card_num(self):
        config = self.config.kekkai_activation.activation_config
        # 挂卡类型
        rule = config.card_type
        # 挂卡星级
        star_rule = config.card_star
        # 收益筛选
        enable_filter = config.enable_yield_filter

        if rule == CardType.TAIKO:
            min_card_num = config.min_taiko_num
            check_card = "勾玉"
        elif rule == CardType.FISH:
            min_card_num = config.min_fish_num
            check_card = "体力"

        target_star_image = None
        if star_rule != CardStar.ALL:
            star_map = {
                CardType.TAIKO: {
                   CardStar.STAR_6: self.I_CARDS_KAIKO_6,
                   CardStar.STAR_5: self.I_CARDS_KAIKO_5,
                   CardStar.STAR_4: self.I_CARDS_KAIKO_4,
                   CardStar.STAR_3: self.I_CARDS_KAIKO_3,
                },
                CardType.FISH: {
                    CardStar.STAR_6: self.I_CARDS_FISH_6,
                    CardStar.STAR_5: self.I_CARDS_FISH_5,
                    CardStar.STAR_4: self.I_CARDS_FISH_4,
                    CardStar.STAR_3: self.I_CARDS_FISH_3,
                }
            }
            target_star_image = star_map.get(rule, {}).get(star_rule)

        swip_count = 0
        x = self.O_CHECK_CARD_NUMBER.roi[0]
        w = self.O_CHECK_CARD_NUMBER.roi[2]
        while 1:
            self.screenshot()

            # --- 模式 A: 用户明确指定了星级 ---
            if target_star_image:
                if self.appear(target_star_image):
                    if not enable_filter:
                        # 如果不筛选收益，看见图片就直接返回点击
                        logger.info(f"已关闭收益筛选，直接选择指定星级: [{star_rule}|{rule}]")
                        return target_star_image
                    else:
                        # 开启筛选：需要判断指定星级卡的收益是否满足最低要求
                        # 首先获取所有指定星级卡片的位置
                        grid = ImageGrid([target_star_image])
                        star_cards = grid.find_everyone(self.device.image)
                        if not star_cards:
                            logger.info(f"未找到 [{star_rule}|{rule}] 卡片位置")
                            continue

                        # 针对每个识别到的卡片，在其收益区域进行OCR识别收益
                        filtered_results = []
                        for star_item in star_cards:  # star_item格式为 (image, score, (x, y, w, h))
                            _, _, (card_x, card_y, card_w, card_h) = star_item
                            
                            # 定义OCR区域，基于识别到的指定卡片位置 （x和w是不变的）
                            ocr_roi = (x, card_y, w, card_h)
                            
                            # 创建临时OCR对象
                            temp_ocr = RuleOcr(roi=ocr_roi, area=ocr_roi, mode="Single", method="Default", keyword="", name="check_card_number")

                            # 进行OCR识别
                            card_area_results = temp_ocr.detect_and_ocr(self.device.image)
                            
                            # 筛选出包含收益关键字的结果
                            for result in card_area_results:
                                if check_card in result.ocr_text:
                                    filtered_results.append(result)
                        
                            logger.info(f"识别到指定星级卡上的收益: {[r.ocr_text for r in filtered_results]}")

                            # 检查过滤后的结果是否有满足条件的
                            for result in filtered_results:
                                numbers = [int(num) for num in re.findall(r'\d+', result.ocr_text)]
                                if numbers and numbers[0] >= min_card_num:
                                    logger.info(f"指定星级 [{star_rule}|{rule}] 的卡片收益达标，准备点击")
                                    return star_item[0]
                    logger.info(f"找到了 [{star_rule}|{rule}] 卡片，但其收益未达标，准备滑动")
                else:
                    logger.info(f"当前未发现指定的 [{star_rule}|{rule}]，准备滑动或退出")
            
            # --- 模式 B: 未指定星级（默认逻辑，优先挑收益最高的） ---
            else:
                results = self.O_CHECK_CARD_NUMBER.detect_and_ocr(self.device.image)
                filtered_results = [result for result in results if check_card in result.ocr_text]
                
                numeric_results = []
                for result in filtered_results:
                    numbers = [int(num) for num in re.findall(r'\d+', result.ocr_text)]
                    if numbers:  
                        if enable_filter and numbers[0] < min_card_num:
                            continue
                        numeric_results.append((numbers[0], result))

                if numeric_results:
                    sorted_results = [result for _, result in sorted(numeric_results, key=lambda x: x[0], reverse=True)]
                    max_result = sorted_results[0]
                    target = RuleClick(roi_front=max_result.after_box, roi_back=max_result.after_box, name="tmpclick")
                    logger.info(f"未指定星级，选择最高收益: [{max_result.ocr_text}]")
                    return target

            # --- 公共滑动逻辑 ---
            if swip_count > 3:
                logger.warning('多次未找到符合条件的结果, 退出')
                return None
            logger.warning("当前页没有符合条件的卡, 准备往下滚动寻找")
            duration = 2
            safe_pos_x = random.randint(200, 400)
            safe_pos_y = random.randint(580, 600)
            p1 = (safe_pos_x, safe_pos_y)
            p2 = (safe_pos_x, safe_pos_y - 410)
            logger.info('Swipe %s -> %s, %sS ' % (point2str(*p1), point2str(*p2), duration))
            self.device.swipe_adb(p1, p2, duration=duration)
            swip_count += 1
            time.sleep(1)
            continue

    def _card_not_found(self):

        change_card_type = self.config.kekkai_activation.activation_config.change_card_type

        if not change_card_type:
            self.push_notify(content='❌ 未发现卡，请检查挂卡')
            self.set_next_run()
            raise TaskEnd

        # 获取配置引用
        activation_config = self.config.kekkai_activation.activation_config
        # 多少分钟后重试
        retry_minutes = 180
        retry_count = 3
        # 递增未找到卡的计数器
        activation_config.card_not_found_count += 1

        if activation_config.card_not_found_count >= retry_count:
            # 达到重试上限时的处理
            log_msg = f"⚠️{activation_config.card_type}卡未检出（累计{retry_count}次），{retry_minutes}分钟后重试"
            activation_config.card_not_found_count = 0  # 重置计数器并延长下次执行时间
            next_run = datetime.now() + timedelta(minutes=retry_minutes)
        else:
            # # 未达上限切换卡类型
            new_type = (
                CardType.FISH
                if activation_config.card_type == CardType.TAIKO
                else CardType.TAIKO
            )
            log_msg = f"🔄{activation_config.card_type}卡未检出 → 切换{new_type}"
            activation_config.card_type = new_type
            next_run = datetime.now()

        # 统一记录日志和推送
        self.save_image(content=log_msg, push_flag=True)

        # 保存配置并设置下次执行
        self.config.save()
        self.set_next_run("KekkaiActivation", success=True, finish=True, target=next_run)
        raise TaskEnd

    def harvest_card(self):
        """
        收卡的经验
        :return:
        """
        harvest_items = [
            self.I_A_HARVEST_EXP,        # 如果到最后没有领的话有下面的一些图片
            self.I_A_HARVEST_KAIKO_6,    # 太鼓6
            self.I_A_HARVEST_FISH_6,     # 斗鱼6
            self.I_A_HARVEST_FISH4,      # 斗鱼4/5区别不大 斗鱼的如果一直没有领的话
            self.I_A_HARVEST_FISH_3,     # 斗鱼三
            self.I_A_HARVEST_KAIKO_4,    # 太鼓4
            self.I_A_HARVEST_KAIKO_3,    # 太鼓3
            self.I_A_HARVEST_MOON_3      # 太阴3
        ]
        
        # 遍历收获项目，有一个成功就退出
        for item in harvest_items:
            if self.appear(item):
                self.ui_click_until_disappear(item)
                break


if __name__ == "__main__":
    from module.config.config import Config

    c = Config('切换账号')

    t = ScriptTask(c)
    t.check_card_num()
    # t.run_activation(t.config.kekkai_activation.activation_config)
