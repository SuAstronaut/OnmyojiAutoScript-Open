"""
任务进度管理工具类
提供统一的任务进度保存、恢复和重置功能
可以在各个任务中复用，避免重复代码
"""
from module.logger import logger
from module.exception import TaskEnd


class PriorityTaskInterrupt(Exception):
    """高优先级任务中断异常"""
    pass


class TaskProgressManager:
    """任务进度管理器"""
    
    def __init__(self, task_instance):
        """
        初始化任务进度管理器
        :param task_instance: 任务实例（BaseTask子类）
        """
        self.task = task_instance
        self.config = task_instance.config
        self.progress_current_count = 0
        self.progress_limit_count = 0
        self.saved_count_attr_path = None  # 配置属性路径
        
    def setup(self, saved_count_attr: str, limit_count: int, saved_count: int = 0):
        """
        设置进度管理器的参数
        :param saved_count_attr: 配置属性路径，如 'hyakkiyakou.hyakkiyakou_config.hya_saved_count'
        :param limit_count: 限制次数
        :param saved_count: 当前已完成的次数（从配置恢复）
        """
        self.saved_count_attr_path = saved_count_attr
        self.progress_limit_count = limit_count
        self.progress_current_count = saved_count
        logger.info(f'恢复任务进度: 已完成 {self.progress_current_count} / {self.progress_limit_count}')
        
    def save_progress(self, count=None, reason="保存任务进度"):
        """
        保存当前进度到配置
        :param count: 要保存的计数值，None则使用self.progress_current_count
        :param reason: 保存原因（用于日志）
        """
        if count is None:
            count = self.progress_current_count
            
        self.task.save_progress_current_count(self.saved_count_attr_path, count)
        logger.info(f'{reason}: {count} / {self.progress_limit_count}')
        
    def reset_progress(self):
        """任务完成后重置进度"""
        self.task.save_progress_current_count(self.saved_count_attr_path, 0)
        logger.info('任务完成，重置保存的进度')
        
    def increment_and_save(self, reason="开始一次"):
        """
        增加计数并保存进度
        :param reason: 保存原因
        """
        self.progress_current_count += 1
        self.save_progress(reason=f'{reason}，保存任务进度')
        
    def check_limit(self) -> bool:
        """
        检查是否达到限制次数
        :return: True表示已达到限制，False表示未达到
        """
        if self.progress_current_count >= self.progress_limit_count:
            logger.warning('运行次数已达上限')
            return True
        return False
        
    def save_on_exception(self, count=None):
        """
        异常时保存进度
        :param count: 要保存的计数值，None则使用self.progress_current_count
        """
        if count is None:
            count = self.progress_current_count
        self.save_progress(count=count, reason="出现异常，保存任务进度")
        
    def save_before_priority_switch(self, count=None):
        """
        切换到高优先级任务前保存进度
        :param count: 要保存的计数值，None则使用self.progress_current_count
        """
        if count is None:
            count = self.progress_current_count
        self.save_progress(count=count, reason="切换到高优先级任务，保存任务进度")
        # 抛出高优先级中断异常
        raise PriorityTaskInterrupt()
        

def create_progress_manager(task_instance, saved_count_attr: str, limit_count: int, saved_count: int = 0) -> TaskProgressManager:
    """
    工厂函数：创建并初始化任务进度管理器
    :param task_instance: 任务实例
    :param saved_count_attr: 配置属性路径
    :param limit_count: 限制次数
    :param saved_count: 已保存的计数（从配置读取）
    :return: 初始化好的TaskProgressManager实例
    """
    manager = TaskProgressManager(task_instance)
    manager.setup(saved_count_attr, limit_count, saved_count)
    return manager


def _get_config_value(config, attr_path: str, default=0):
    """
    从配置中获取值
    :param config: 配置对象
    :param attr_path: 属性路径，如 'module.config.field'
    :param default: 默认值
    :return: 配置值或默认值
    """
    parts = attr_path.split('.')
    obj = config
    try:
        for part in parts:
            obj = getattr(obj, part)
        return obj
    except (AttributeError, TypeError):
        return default


# 使用示例装饰器
def with_progress_tracking(saved_count_attr: str, limit_count_attr: str):
    """
    装饰器：为任务方法添加进度跟踪功能
    
    使用示例:
    @with_progress_tracking('config.saved_count', 'config.limit_count')
    
    def run(self):
        while True:
            if self.progress_mgr.check_limit():
                break
            self.do_something()
            self.progress_mgr.increment_and_save()
    
    :param saved_count_attr: saved_count的配置路径，如 'module.config.saved_count'
    :param limit_count_attr: limit_count的配置路径，如 'module.config.limit_count'
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            # 从配置中获取limit_count和saved_count
            final_limit_count = _get_config_value(self.config, limit_count_attr, default=0)
            saved_count = _get_config_value(self.config, saved_count_attr, default=0)
            
            # 创建进度管理器
            progress_mgr = create_progress_manager(
                self, 
                saved_count_attr, 
                final_limit_count, 
                saved_count
            )
            
            # 将管理器绑定到self，方便在方法中使用
            self.progress_mgr = progress_mgr
            
            try:
                # 执行原函数
                func(self, *args, **kwargs)
            except TaskEnd:
                # 任务正常结束，重置进度
                progress_mgr.reset_progress()
                raise
            except PriorityTaskInterrupt:
                # 高优先级任务中断，保存进度但不重置
                raise TaskEnd  # 转换为TaskEnd，让上层框架处理
            except Exception as e:
                # 异常时保存进度
                progress_mgr.save_on_exception()
                raise
                
        return wrapper
    return decorator
