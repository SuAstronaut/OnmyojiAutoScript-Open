"""
配置验证和自动修正模块
当配置参数不符合要求时，自动修改为默认值并打印日志
"""
import copy
from module.logger import logger
from pydantic import fields
from typing import Any, Type
from enum import Enum


class ConfigValidator:
    """
    配置验证和自动修正类
    """

    def __init__(self, config_model=None):
        self.config_model = config_model


def _fix_by_model_field_type(config_name, config_data: dict, model_class) -> dict:
    """
    通过模型字段类型信息来修复配置数据
    :param config_data: 配置数据
    :param model_class: 模型类
    :return: 修复后的配置数据
    """
    if not hasattr(model_class, '__fields__'):
        return config_data

    fixed_data = copy.deepcopy(config_data)
    has_changes = False

    for field_name, field_info in model_class.__fields__.items():
        if field_name in fixed_data:
            field_value = fixed_data[field_name]
            expected_type = field_info.type_

            # 如果是嵌套模型，递归处理
            if isinstance(field_value, dict) and hasattr(expected_type, '__fields__'):
                nested_fixed = _fix_by_model_field_type(config_name, field_value, expected_type)
                if nested_fixed != field_value:
                    fixed_data[field_name] = nested_fixed
                    has_changes = True
            else:
                # 尝试修复字段值
                fixed_value = _try_fix_field_value(config_name, field_value, field_info, expected_type, field_name)
                if fixed_value != field_value:
                    fixed_data[field_name] = fixed_value
                    has_changes = True
    
    if has_changes:
        logger.info(f"[{config_name}] 配置数据已修复")

    return fixed_data


def _try_fix_field_value(config_name, value: Any, field_info: fields.FieldInfo, expected_type: type, field_name: str) -> Any:
    """
    尝试修复字段值，基于模型字段类型信息
    当类型不匹配时直接使用默认值
    :param value: 当前值
    :param field_info: 字段信息
    :param expected_type: 期望类型
    :param field_name: 字段名称
    :return: 修复后的值
    """
    # 优先检查是否是枚举类型
    if _is_enum_type(expected_type):
        fixed_value = _fix_enum_value(config_name, value, expected_type, field_info, field_name)
        if fixed_value != value:
            return fixed_value

    # 检查类型是否匹配
    type_matched = False
    
    if expected_type == bool:
        type_matched = isinstance(value, bool)
    elif expected_type == int:
        type_matched = isinstance(value, int) and not isinstance(value, bool)
    elif expected_type == float:
        type_matched = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif expected_type == str:
        type_matched = isinstance(value, str)
    else:
        # 其他类型暂时认为匹配
        type_matched = True
    
    # 如果类型不匹配，使用默认值
    if not type_matched:
        default = _get_field_default(field_info)
        if default is not None:
            logger.warning(f"[{config_name}] 字段 {field_name} 期望{expected_type.__name__}类型但收到 {type(value).__name__}: '{value}'，使用默认值 {default}")
            return default
        else:
            logger.warning(f"[{config_name}] 字段 {field_name} 期望{expected_type.__name__}类型但收到 {type(value).__name__}: '{value}'，无默认值可用")

    return value


def _get_field_default(field_info: fields.FieldInfo) -> Any:
    """
    获取字段的默认值
    :param field_info: 字段信息
    :return: 默认值，如果没有则返回None
    """
    if field_info.default is not None and field_info.default != ...:
        return field_info.default
    elif field_info.default_factory is not None:
        try:
            return field_info.default_factory()
        except Exception:
            return None
    return None


def _is_enum_type(expected_type: Type) -> bool:
    """
    检查类型是否是枚举类型或枚举的子类
    """
    try:
        return issubclass(expected_type, Enum)
    except TypeError:
        return False


def _fix_enum_value(config_name, value: Any, enum_type: Type[Enum], field_info: fields.FieldInfo, field_name: str) -> Any:
    """
    修复枚举类型的值
    :param config_name: 配置名称
    :param value: 当前值
    :param enum_type: 枚举类型
    :param field_info: 字段信息
    :param field_name: 字段名称
    :return: 修复后的值
    """
    try:
        # 如果已经是正确的枚举值，直接返回
        if isinstance(value, enum_type):
            return value
        
        # 获取所有有效的枚举成员名和值
        valid_names = list(enum_type.__members__.keys())
        valid_values = [str(member.value) for member in enum_type.__members__.values()]
        all_valid = valid_names + valid_values
        
        str_value = str(value)
        
        # 精确匹配
        if str_value in all_valid:
            # 如果是枚举成员名，返回对应的枚举值
            if str_value in valid_names:
                result = enum_type[str_value].value
                logger.info(f"[{config_name}] 字段 {field_name} 使用枚举成员名 '{str_value}' -> '{result}'")
                return result
            else:
                # 如果是枚举值，直接返回
                logger.debug(f"[{config_name}] 字段 {field_name} 的值 '{str_value}' 是有效的枚举值")
                return str_value
        
        # 模糊匹配：查找相似值
        str_value_lower = str_value.lower()
        for valid_val in valid_values:
            if str_value_lower in valid_val.lower() or valid_val.lower() in str_value_lower:
                logger.warning(f"[{config_name}] 字段 {field_name} 的值 '{value}' 修正为相似值 '{valid_val}'")
                return valid_val
        
        # 尝试通过名称模糊匹配
        for valid_name in valid_names:
            if str_value_lower in valid_name.lower() or valid_name.lower() in str_value_lower:
                result = enum_type[valid_name].value
                logger.warning(f"[{config_name}] 字段 {field_name} 的值 '{value}' 通过名称匹配修正为 '{result}'")
                return result
        
        # 如果找不到匹配，使用默认值
        default_value = field_info.default
        if default_value is not None and default_value != ...:
            # 如果默认值是枚举实例，取其value
            if isinstance(default_value, enum_type):
                logger.warning(f"[{config_name}] 字段 {field_name} 的值 '{value}' 无效，使用默认值 '{default_value.value}'")
                return default_value.value
            else:
                logger.warning(f"[{config_name}] 字段 {field_name} 的值 '{value}' 无效，使用默认值 '{default_value}'")
                return default_value
        elif valid_values:
            # 使用第一个枚举值作为默认值
            first_value = valid_values[0]
            logger.warning(f"[{config_name}] 字段 {field_name} 的值 '{value}' 无效，使用第一个枚举值 '{first_value}'")
            return first_value
        
    except Exception as e:
        logger.error(f"[{config_name}] 修复枚举字段 {field_name} 时出错: {e}")
    
    return value
