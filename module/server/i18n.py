from pathlib import Path

import json5


class I18n:
    file_zh_cn = Path.cwd() / 'module' / 'zh-CN.json'
    file_zh_cn_web = Path.cwd() / 'module' / 'zh-CN-Web.json'

    @classmethod
    def trans_zh_cn(cls, text) -> str:
        cn_zh_data = cls.load_zh_cn(I18n.file_zh_cn)
        return cn_zh_data[text] if text in cn_zh_data else text

    @classmethod
    def trans_zh_cn_web(cls, text) -> str:
        cn_zh_data = cls.load_zh_cn(I18n.file_zh_cn_web)
        return cn_zh_data[text] if text in cn_zh_data else ''

    @classmethod
    def save_zh_cn(cls, data) -> None:
        I18n.file_zh_cn.parent.mkdir(parents=True, exist_ok=True)
        with open(str(I18n.file_zh_cn), 'w', encoding='utf-8') as f:
            s = json5.dumps(data, indent=2, ensure_ascii=False, sort_keys=False, default=str)
            f.write(s)

    @classmethod
    def load_zh_cn(cls, file_path=None) -> dict:
        try:
            if not file_path.exists():
                return {}
            with open(str(file_path), 'r', encoding='utf-8') as f:
                return json5.load(f)
        except Exception as e:
            from module.logger import logger
            logger.error(f"加载中文翻译文件时出错: {e}")
            return {}

    @classmethod
    def load_additions(cls, file_path=None) -> dict:
        result = {'en-US': {}, 'zh-CN': {}}  # 默认 'en-US' 为空字典
        try:
            if file_path.exists():
                with open(str(file_path), 'r', encoding='utf-8') as f:
                    result['zh-CN'] = json5.load(f)
            return result
        except Exception as e:
            from module.logger import logger
            logger.error(f"加载翻译文件时出错: {e}")
            return result


if __name__ == '__main__':
    print(I18n.load_zh_cn())
    print(I18n.load_additions())
