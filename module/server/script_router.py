# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi import Request
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from module.config.utils import convert_to_underscore
from module.logger import logger
from module.server.main_manager import MainManager
from module.server.script_process import ScriptProcess, ScriptState
from tasks.Component.config_base import TimeDelta
script_app = APIRouter()
mm = MainManager()

# ⚡ 防抖机制：记录每个脚本的待处理定时器
_reload_signal_timers: dict[str, asyncio.TimerHandle] = {}


async def send_reload_signal(script_name: str):
    """
    ⚡ 发送配置重载信号到子进程（使用 Event）
    broadcast_state立即执行，config_reload_event延迟1秒发送（防抖）
    :param script_name: 配置名称
    """
    try:
        process = mm.script_process[script_name]

        # ⚡ 立即广播状态更新（不延迟）
        config = mm.config_cache(script_name)
        config.get_next()
        schedule_data = config.get_schedule_data()
        await process.broadcast_state({"schedule": schedule_data})

        if not process._process or not process._process.is_alive():
            logger.warning(f'⚡ 进程未运行: {script_name}')
            return

        # 取消之前的待处理定时器（如果有）
        if script_name in _reload_signal_timers:
            old_timer = _reload_signal_timers[script_name]
            if not old_timer.cancelled():
                old_timer.cancel()
                logger.debug(f'⚡ 取消之前的延迟信号 | 配置: {script_name}')

        # 创建新的1秒延迟定时器
        loop = asyncio.get_event_loop()
        timer = loop.call_later(1.0, lambda: asyncio.create_task(_do_send_reload_event(script_name)))
        _reload_signal_timers[script_name] = timer
        logger.debug(f'⚡ 设置延迟信号（1秒后发送）| 配置: {script_name}')

    except Exception as e:
        logger.error(f'⚡ 配置重载异常: {script_name} | {e}', exc_info=True)


async def _do_send_reload_event(script_name: str):
    """
    ⚡ 实际发送配置重载事件信号（延迟防抖）
    :param script_name: 配置名称
    """
    try:
        # 清理定时器记录
        _reload_signal_timers.pop(script_name, None)
        
        process = mm.script_process[script_name]
        
        logger.info(f'⚡ 准备发送配置重载信号 | 配置: {script_name}')
        process.config_reload_event.set()
        logger.info(f'⚡ 已发送配置重载信号 | 配置: {script_name}')

    except Exception as e:
        logger.error(f'⚡ 配置重载异常: {script_name} | {e}', exc_info=True)


@script_app.post('/qqbot')
async def script_qqbot(request: Request):
    data = await request.json()  # 获取事件数据
    await qqbaot.received(data)
    return 'qqbot'


@script_app.get('/test')
async def script_test():
    return 'success'


@script_app.get('/script_menu')
async def script_menu():
    return mm.config_cache('template').gui_menu_list


# ----------------------------------   配置文件管理   ----------------------------------
@script_app.get('/config_list')
async def config_list():
    return mm.all_script_files()


@script_app.get('/config_templates')
async def config_templates():
    """
    获取所有可用的模板列表（用于创建脚本时选择）
    包括 template 和 template(一条龙*) 等模板文件
    """
    return mm.all_template_files()


@script_app.post('/config_copy')
async def config_copy(file: str, template: str = 'template'):
    mm.copy(file, template)
    return mm.all_script_files()


@script_app.get('/config_new_name')
async def config_new_name():
    return mm.generate_script_name()


@script_app.get('/config_all')
async def config_all():
    return mm.all_json_file()


@script_app.put('/config')
async def config_rename(old_name: str = '', new_name: str = ''):
    """
    update config name
    :param old_name: old config name
    :param new_name: new config name
    :return: True or False
    """
    if old_name == new_name or new_name == '':
        return False
    if old_name in mm.script_process:
        if mm.script_process[old_name].state != ScriptState.INACTIVE:
            mm.script_process[old_name].stop()
        del mm.script_process[old_name]
    if not mm.rename(old_name, new_name):
        raise HTTPException(status_code=400, detail='Rename failed')
    return True


@script_app.delete('/config')
async def config_delete(name: str = ''):
    """
    delete config file
    :param name: config name
    :return: True or False
    """
    if name == '' or name == 'template':
        raise HTTPException(status_code=400, detail='Delete failed')
    if name in mm.script_process:
        if mm.script_process[name].state != ScriptState.INACTIVE:
            mm.script_process[name].stop()
        del mm.script_process[name]
    if not mm.delete(name):
        raise HTTPException(status_code=400, detail='Delete failed')
    return True


# ---------------------------------   脚本实例管理   ----------------------------------
@script_app.get('/{script_name}/start')
async def script_start(script_name: str):
    logger.info(f'[{script_name}] script process start')
    if script_name not in mm.script_process:
        mm.script_process[script_name] = ScriptProcess(script_name)
    await mm.script_process[script_name].start()
    return


@script_app.get('/{script_name}/stop')
async def script_stop(script_name: str):
    logger.info(f'[{script_name}] script process stop')
    if script_name not in mm.script_process:
        logger.warning(f'[{script_name}] script process does not exist')
        return
    await mm.script_process[script_name].stop()
    return


@script_app.get('/{script_name}/{task}/args')
async def script_task(script_name: str, task: str):
    return mm.config_cache(script_name).model.script_task(task)


@script_app.put('/{script_name}/{task}/{group}/{argument}/value')
async def script_task(script_name: str, task: str, group: str, argument: str, types: str, value):
    try:
        logger.info(f'/{script_name}/{task}/{group}/{argument}/{value}')
        match types:
            case 'integer':
                value = int(value)
            case 'number':
                value = float(value)
            case 'boolean':
                if isinstance(value, str):
                    logger.warning(
                        f'[{script_name}] script argument {argument} value is string, try to convert to bool')
                    if value.lower() in ['true', '1']:
                        value = True
                    elif value.lower() in ['false', '0']:
                        value = False
                value = bool(value)
            case 'string':
                pass
            case 'date_time':
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            case 'time_delta':
                # strptime 是个好东西，但是不能解析00的天数
                day = int(value[1])
                date_time = datetime.strptime(value[3:], '%H:%M:%S')
                value = TimeDelta(days=day, hours=date_time.hour, minutes=date_time.minute, seconds=date_time.second)
            case 'time':
                value = datetime.strptime(value, '%H:%M:%S').time()
            case _:
                pass
    except Exception as e:
        # 类型不正确
        raise HTTPException(status_code=400, detail=f'Argument type error: {e}')
    result = mm.config_cache(script_name).model.script_set_arg(task, group, argument, value)
    # ⚡ 配置重载信号改为后台任务，任何异常都不阻塞主进程
    await send_reload_signal(script_name)
    return result


@script_app.put('/{script_name}/{task}/sync_next_run')
async def sync_next_run(script_name: str, task: str, target_dt: str):
    if script_name not in mm.script_process:
        return False
    config = mm.config_cache(script_name)
    target = datetime.strptime(target_dt, '%Y-%m-%d %H:%M:%S') if target_dt else None
    config.task_delay(task=task, success=True, target=target)
    # ⚡ 配置重载信号改为后台任务，任何异常都不阻塞主进程
    await send_reload_signal(script_name)
    return True


@script_app.put('/config/task/copy')
async def task_copy(task_name: str, dest_config_name: str, source_config_name: str):
    if dest_config_name not in mm.script_process or source_config_name not in mm.script_process:
        return False
    source_task = getattr(mm.config_cache(source_config_name).model, convert_to_underscore(task_name), None)
    if source_task is None:
        return False
    result = mm.config_cache(dest_config_name).model.copy_script_task(task_name, source_task)
    # ⚡ 配置重载信号改为后台任务，任何异常都不阻塞主进程
    await send_reload_signal(dest_config_name)
    return result


@script_app.put('/config/task/group/copy')
async def task_group_copy(task_name: str, group_name: str, dest_config_name: str, source_config_name: str):
    if dest_config_name not in mm.script_process or source_config_name not in mm.script_process:
        return False
    source_task = getattr(mm.config_cache(source_config_name).model, convert_to_underscore(task_name), None)
    if source_task is None:
        return False
    result = mm.config_cache(dest_config_name).model.copy_task_group(task_name, group_name, source_task)
    # ⚡ 配置重载信号改为后台任务，任何异常都不阻塞主进程
    await send_reload_signal(dest_config_name)
    return result


# --------------------------------------  SSE  --------------------------------------


@script_app.get('/{script_name}/state')
async def script_task_state(script_name: str):
    async def state_generate_events():
        while True:
            # 生成 SSE 事件数据
            event_data = "data: Hello, SSE!\n\n"
            yield event_data

            # 模拟异步操作，可以替换为您的实际处理逻辑
            await asyncio.sleep(1)

    response = StreamingResponse(state_generate_events(), media_type="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    return response


@script_app.get('/{script_name}/log')
async def script_task_log(script_name: str):
    async def log_generate_events():
        while True:
            # 生成 SSE 事件数据
            event_data = "data: log\n"
            yield event_data

            # 模拟异步操作，可以替换为您的实际处理逻辑
            await asyncio.sleep(1)

    response = StreamingResponse(log_generate_events(), media_type="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    return response


# -------------------------------------- websocket --------------------------------------
@script_app.websocket("/ws/{script_name}")
async def websocket_endpoint(websocket: WebSocket, script_name: str):
    if script_name not in mm.script_process:
        mm.script_process[script_name] = ScriptProcess(script_name)
    script_process = mm.script_process[script_name]
    await script_process.connect(websocket)

    try:
        await script_process.broadcast_state({"state": script_process.state})
        config = mm.config_cache(script_name)
        config.get_next()
        await script_process.broadcast_state({"schedule": config.get_schedule_data()})

        while True:
            # 初次进入，广播state schedule
            data = await websocket.receive_text()
            # logger.info(f'[{script_name}] websocket receive: {data}')
            if data == 'get_state':
                await script_process.broadcast_state({"state": script_process.state})
            elif data == 'get_schedule':
                config = mm.config_cache(script_name)
                config.get_next()
                await script_process.broadcast_state({"schedule": config.get_schedule_data()})
            elif data == 'start':
                await script_process.start()
            elif data == 'stop':
                await script_process.stop()

    except WebSocketDisconnect:
        logger.warning(f'[{script_name}] websocket disconnect')
        await script_process.disconnect(websocket)
    except Exception as e:
        logger.exception(f'[{script_name}] websocket error: {e}')
        await script_process.disconnect(websocket)
