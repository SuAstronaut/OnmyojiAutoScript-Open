# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from fastapi import APIRouter, Body
from module.logger import logger
from module.server.i18n import I18n
from module.server.main_manager import MainManager
from module.server.updater import Updater

home_app = APIRouter(
    prefix="/home",
    tags=["home"],
)

# 全局缓存：配置标题映射
_config_titles_cache = None


@home_app.get('/test')
async def home_test():
    return {'message': 'test'}


#  gcc -Wall -pedantic -shared -fPIC -o group_work.so group_work.c -lwiringPi
@home_app.get('/home_menu')
async def home_menu():
    return {'Home': [], 'Updater': [], 'Tool': []}


@home_app.post('/notify_test')
async def notify_test(setting: str, title: str, content: str):
    from module.notify.notify import Notifier
    try:
        notifier = Notifier(setting, setting, True, False)
        if notifier.push(title=title, content=content):
            del notifier
            return True
        else:
            del notifier
            return False
    except Exception as e:
        logger.exception(e)
        return str(e)


@home_app.get('/kill_server')
async def kill_server():
    MainManager.signal_kill_server = True
    return 'success'


@home_app.get('/update_info')
async def update_info():
    try:
        updater = Updater()
        result = {'is_update': updater.check_update(),
                  'branch': updater.current_branch(),
                  'current_commit': updater.current_commit(),
                  'latest_commit': updater.latest_commit(),
                  'commit': updater.get_commit(n=15),
                  }
        return result
    except Exception as e:
        logger.error(e)
        return None


@home_app.get('/version_info')
async def version_info():
    """
    获取版本信息，用于前端展示
    """
    try:
        updater = Updater()
        
        # 获取当前提交信息
        current_commit = updater.current_commit()  # (sha1, author, isotime, message)
        latest_commit = updater.latest_commit()    # (sha1, author, isotime, message)
        
        # 判断是否需要更新
        is_latest = False
        if current_commit and latest_commit:
            is_latest = current_commit[0] == latest_commit[0]
        
        result = {
            'is_latest': is_latest
        }
        
        return result
    except Exception as e:
        logger.error(f'获取版本信息失败: {e}')
        return None


@home_app.get('/execute_update')
async def execute_update():
    # 下拉仓库 -> 关闭所有脚本进程 -> 最后重启
    try:
        updater = Updater()
        updater.execute_pull()
    except Exception as e:
        logger.error(e)
    return '手动更新将会立即结束运行中的脚本服务, 最后你还需重启'


# @home_app.put('/chinese_translate')
# async def chinese_translate(data: dict = Body(...)):
#     try:
#         I18n.save_zh_cn(data)
#     except Exception as e:
#         logger.error(e)
#     return True


def _collect_config_titles() -> dict:
    """
    收集所有任务配置中的字段名和 title
    只收集有 title 的字段，没有 title 的跳过
    返回格式: {"field_name": "title"}
    """
    from module.config.config_model import ConfigModel
    from pydantic import BaseModel
    import inflection
    import re
    result = {}
    
    try:
        # 获取 ConfigModel 的所有字段
        config_model = ConfigModel()
        
        def extract_titles_from_task(task_obj):
            """从任务对象中提取所有 title（参考 script_task 的实现）"""
            if not isinstance(task_obj, BaseModel):
                return
            
            try:
                schema = task_obj.schema()
                definitions = schema.get('definitions', {})
                
                # 提取 groups（嵌套的 Config）
                def properties_groups(sch) -> dict:
                    properties = {}
                    for key, value in sch["properties"].items():
                        if value.get("hidden") is True:
                            continue
                        # 处理有 $ref 的字段（嵌套的 Config）
                        if '$ref' in value:
                            properties[key] = re.search(r"/([^/]+)$", value['$ref']).group(1)
                        elif 'allOf' in value and len(value['allOf']) > 0 and '$ref' in value['allOf'][0]:
                            # 处理 allOf 形式的引用
                            properties[key] = re.search(r"/([^/]+)$", value['allOf'][0]['$ref']).group(1)
                    return properties
                
                def extract_groups(sch):
                    properties = properties_groups(sch)
                    result_groups = {}
                    for key, value in properties.items():
                        if value in sch["definitions"]:
                            definition = sch["definitions"][value]
                            if "properties" in definition:
                                visible_properties = {}
                                for prop_key, prop_value in definition["properties"].items():
                                    if prop_value.get("hidden") is not True:
                                        visible_properties[prop_key] = prop_value
                                if visible_properties:
                                    result_groups[key] = {**definition, "properties": visible_properties}
                            else:
                                result_groups[key] = definition
                    return result_groups
                
                groups = extract_groups(schema)
                
                # 遍历所有 group，收集分组本身的 title 和内部字段的 title
                for group_name, group_info in groups.items():
                    # 1. 收集分组本身的 title（从 schema 的 properties 中获取）
                    if group_name in schema['properties']:
                        group_field_info = schema['properties'][group_name]
                        underscore_key = inflection.underscore(group_name)
                        auto_generated_title = inflection.titleize(underscore_key)
                        group_title = group_field_info.get('title', auto_generated_title)
                        
                        # 如果分组有自定义 title，收集
                        if group_title != auto_generated_title:
                            result[group_name] = group_title
                    
                    # 2. 收集分组内部字段的 title
                    if "properties" not in group_info:
                        continue
                    
                    for field_name, field_info in group_info["properties"].items():
                        # 检查 title 是否是 Pydantic 自动生成的
                        underscore_key = inflection.underscore(field_name)
                        auto_generated_title = inflection.titleize(underscore_key)
                        field_title = field_info.get('title', auto_generated_title)
                        
                        # 调试
                        if 'memory' in group_name.lower() and 'close' in field_name:
                            logger.info(f"调试: {group_name}.{field_name} -> title='{field_title}', auto='{auto_generated_title}'")
                        
                        # 如果是自定义 title，收集
                        if field_title != auto_generated_title:
                            result[field_name] = field_title
                
            except Exception as e:
                logger.warning(f"提取任务 {type(task_obj).__name__} 的标题时出错: {e}")
        
        # 遍历 ConfigModel 的所有任务字段
        task_count = 0
        for field_name in dir(config_model):
            if field_name.startswith('_'):
                continue
            
            field_value = getattr(config_model, field_name, None)
            if isinstance(field_value, BaseModel):
                task_count += 1
                # 调试：打印所有任务名称
                if 'memory' in field_name.lower():
                    logger.info(f"调试: 找到任务 {field_name}, 类型: {type(field_value).__name__}")
                extract_titles_from_task(field_value)
        
        logger.info(f"✅ 共遍历 {task_count} 个任务，成功收集 {len(result)} 个配置字段的标题")
        # if result:
        #     logger.info(f"示例: {list(result.items())[:5]}")
        return result
        
    except Exception as e:
        logger.error("❌ 收集配置标题时出错")
        logger.error(e, exc_info=True)
        return {}


@home_app.get('/additional_translate')
async def additional_translate() -> dict:
    global _config_titles_cache
    
    try:
        # 加载两个翻译文件并合并
        data_backend = I18n.load_additions(I18n.file_zh_cn)
        data_web = I18n.load_additions(I18n.file_zh_cn_web)
        
        # 先合并 web 和 backend 翻译（backend 覆盖 web）
        merged_zh_cn = {**data_web['zh-CN'], **data_backend['zh-CN']}
        
        # 如果缓存为空，则收集配置标题
        if _config_titles_cache is None:
            logger.info("🔄 正在收集配置标题...")
            _config_titles_cache = _collect_config_titles()
        
        # 配置标题优先级最高，最后合并覆盖
        if _config_titles_cache:
            for key, value in _config_titles_cache.items():
                merged_zh_cn[key] = value
            # logger.info(f"📝 已覆盖合并 {len(_config_titles_cache)} 个配置标题到翻译数据")
        
        return {'en-US': {}, 'zh-CN': merged_zh_cn}
    except Exception as e:
        logger.error("❌ 获取后端翻译报错")
        logger.error(e, exc_info=True)
    return {'en-US': {}, 'zh-CN': {}}


@home_app.get('/additional_translate_web')
async def additional_translate_web() -> dict:
    try:
        # 加载两个翻译文件并合并
        data_backend = I18n.load_additions(I18n.file_zh_cn)
        data_web = I18n.load_additions(I18n.file_zh_cn_web)

        # 合并 zh-CN 部分（backend 覆盖 web 的同名键）
        merged_zh_cn = {**data_web['zh-CN'], **data_backend['zh-CN']}

        return {'en-US': {}, 'zh-CN': merged_zh_cn}
    except Exception as e:
        logger.error("❌ 获取后端翻译报错")
        logger.error(e, exc_info=True)
    return {'en-US': {}, 'zh-CN': {}}
