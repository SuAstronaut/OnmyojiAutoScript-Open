# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import csv
import difflib
import re
from datetime import datetime
from module.logger import logger
from pathlib import Path


def count_intersection(str1, str2):
    set1 = set(str1)
    set2 = set(str2)
    intersection = set1.intersection(set2)
    return len(intersection)

def remove_symbols(text):
    return re.sub(r'[^\w\s]', '', text)

class Answer:
    def __init__(self):
        self.data: dict[str, list] = {}
        self.data_options: dict[str, list] = {}
        file = str(Path(__file__).parent / 'data.csv')
        with open(file, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)
            for row in reader:
                # 跳过空行或长度不足的行
                if not row or len(row) < 2:
                    continue
                key = remove_symbols(row[0])
                value = remove_symbols(row[1])
                if key not in self.data:
                    self.data[key] = []
                self.data[key].append(value)
                if value not in self.data_options:
                    self.data_options[value] = []
                self.data_options[value].append(key)

    def _save_question(self, question: str, options: list[str], file_name: str):
        """
        保存未识别的题目和选项到文件
        """
        file_path = str(Path(__file__).parent / file_name)

        # 检查是否已经存在相同的记录
        if Path(file_path).exists():
            with open(file_path, 'r', newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if row and row[0] == question:  # 添加 row 检查
                        # 如果找到相同的题目和选项，不保存
                        logger.info(f'Duplicate question found, skipping: {question}')
                        return

        with open(file_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            row = [question] + options[:3]
            writer.writerow(row)

    def answer_one(self, question: str, options: list[str]) -> int|None:
        """

        每一个问题有三个选项， 返回选项的序号(1、2、3)
        :param question:
        :param options:
        :return:
        """
        def decide_by_question_foreach(ques: str, ops: list[str]):
            # 这个是最耗时的操作，遍历数据库中的所有题目，找到最相识的题目和选项
            for key, values in self.data.items():
                question_match_ratio = difflib.SequenceMatcher(None, ques, key).ratio()
                if question_match_ratio < 0.7:
                    continue
                for value in values:
                    for index, option in enumerate(ops):
                        option_match_ratio = difflib.SequenceMatcher(None, option, value).ratio()
                        if option_match_ratio >= 0.5:
                            logger.warning('The worst case: no match found for question and option')
                            logger.warning('Now traversing the entire database to find the most similar question and option')
                            logger.warning(f'Most similar question: {key} and most similar option: {value}')
                            return index + 1
            return None

        def decide_by_options(question: str, ops: list[str]):
            # 瞎猫当死耗子
            matches = {}
            for index, option in enumerate(ops):
                if option not in self.data_options.keys():
                    continue
                for ques in self.data_options[option]:
                    ques_match_ratio = difflib.SequenceMatcher(None, ques, question).ratio()
                    if ques_match_ratio > 0.8:
                        matches[index + 1] = ques_match_ratio
            if matches:
                opts = sorted(matches.items(), key=lambda x: x[1], reverse=True)
                logger.warning('未找到匹配的题目')
                logger.warning('现在正在遍历整个数据库以找到最相似的题目')
                logger.warning(f'最相似的选项: {opts[0][0]}, 相似字符数为 {opts[0][1]}')
                return opts[0][0]
            index = decide_by_question_foreach(question, ops)
            return index if index else None


        question = remove_symbols(question)
        options = [remove_symbols(option) for option in options]

        for index, option in enumerate(options):
            if option == '其余选项皆对':
                return index + 1

        question_matches: list = []
        try:
            question_matches = self.data[question]
            # self._save_question(question, options,  'known_questions.csv')
        except Exception as e:
            # 没有出现题目，从选项反入手，并保存未知题目
            logger.warning('未知题目: %s', question)
            logger.warning('选项: %s', options)
            self._save_question(question, options,  'unknown_questions.csv')
            return decide_by_options(question=question, ops=options)
        # 出现了题目，开始对答案
        for index, option in enumerate(options):
            for match in question_matches:
                if match == option:
                    return index + 1
        # 可能选项识别某一个字错误
        if all(options):
            for index, option in enumerate(options):
                for match in question_matches:
                    if len(match) != len(option):
                        continue
                    if len(match) - count_intersection(match, option) <= 1 :
                        logger.warning('Option is not match: %s, %s', match, option)
                        return index + 1
        # 最保守策略，答案匹配度最高
        opts = {}
        for index, option in enumerate(options):
            item_match_ratio = 0
            for match in question_matches:
                match_ratio = difflib.SequenceMatcher(None, match, option).ratio()
                if match_ratio >= 0.33 and match_ratio > item_match_ratio:
                    item_match_ratio = match_ratio
            if item_match_ratio > 0:
                opts[index + 1] = item_match_ratio
        if opts:
            opts = sorted(opts.items(), key=lambda x: x[1], reverse=True)
            logger.warning(f'Use SequenceMatcher and get answers: {opts[0][0]}, score: {opts[0][1]}')
            return opts[0][0]

        # 选项一个都对不上可能是，正确答案检测为空
        for index, option in enumerate(options):
            if option == '':
                logger.error('Option is empty: %s', options)
                return index + 1
        return None


if __name__ == "__main__":
    answer = Answer()
    # question = '冥界中谁拥阁魔之目一双审善度恶'
    # options = ['判官', '孟婆', '荒川之主', '阁魔']

    question = '一目连呱把谁当做妹妹来照顾'
    options = ['妖刀姬呱']

    answer._save_question(question=question, options=[options[0]], file_name='答题错误.csv')

    # question = 'ccccc'
    # options = ['aaa']
    #
    # question = '初翎山风的被动技能拥有以下哪种能力'
    # options = ['免疫控制', '反弹伤害', '增加行动条']
    # start_time = datetime.now()
    # print(answer.answer_one(question, options))
    # print(datetime.now() - start_time)