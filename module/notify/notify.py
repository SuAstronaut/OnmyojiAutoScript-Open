# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import aiohttp
import base64
import cv2
import hashlib
import numpy
import numpy as np
import onepush.core
import yaml
from PIL import Image, ImageDraw, ImageFont
from aiohttp_socks import ProxyConnector
from email.message import EmailMessage
from module.logger import format_chinese_time
from module.logger import logger
from module.server.i18n import I18n
from onepush import get_notifier
from onepush.core import Provider
from onepush.exceptions import OnePushException
from onepush.providers.custom import Custom
from onepush.providers.smtp import SMTP, _default_message_parser
from pathlib import Path
from requests import Response
from smtplib import SMTPResponseException
from typing import Optional

onepush.core.log = logger


class Notifier:
    def __init__(self, _config: str, _config_tg: str, enable: bool = False, enable_tg: bool = False) -> None:
        self.config_name: str = ""
        self.enable: bool = enable
        self.enable_tg: bool = enable_tg

        if self.enable:
            config = {}
            try:
                for item in yaml.safe_load_all(_config):
                    config.update(item)
            except Exception as e:
                logger.error("Fail to load onepush config, skip sending")
                return
            self.config = config
            try:
                # 获取provider
                self.provider_name: str = self.config.pop("provider", "")
                if self.provider_name == "":
                    logger.info("No provider specified, skip sending")
                    return
                # 获取notifier
                self.notifier: Provider = get_notifier(self.provider_name)
                # 获取notifier的必填参数
                self.required: list[str] = self.notifier.params["required"]
            except OnePushException:
                logger.exception("Init notifier failed")
                return
            except Exception as e:
                logger.exception(e)
                return

        if self.enable_tg:
            config_tg = {}
            try:
                for item in yaml.safe_load_all(_config_tg):
                    config_tg.update(item)
            except Exception as e:
                logger.error("Fail to load onepush config, skip sending")
                return
            self.config_tg = config_tg
            try:
                self.proxy: str = self.config_tg.pop("proxy", "")
                if self.proxy == "":
                    logger.info("No proxy specified, skip sending")
                    return
                self.token: str = self.config_tg.pop("token", "")
                if self.token == "":
                    logger.info("No token specified, skip sending")
                    return
                self.chat_id: str = self.config_tg.pop("chat_id", "")
                if self.chat_id == "":
                    logger.info("No chat_id specified, skip sending")
                    return
            except Exception as e:
                logger.error(e)
                return

    def push(self, **kwargs) -> bool:
        if not self.enable:
            return False
        # 更新配置
        kwargs["title"] = f"{self.config_name}▪{kwargs['title']}".replace(' ', '\u00A0')
        # kwargs["content"] = f'{format_chinese_time()} | {kwargs["content"]}'
        self.config.update(kwargs)
        # pre check
        for key in self.required:
            if key not in self.config:
                logger.warning(f"Notifier {self.notifier} require param '{key}' but not provided")

        if isinstance(self.notifier, Custom):
            if "method" not in self.config or self.config["method"] == "post":
                self.config["datatype"] = "json"
            if not ("data" in self.config or isinstance(self.config["data"], dict)):
                self.config["data"] = {}
            if "title" in kwargs:
                self.config["data"]["title"] = kwargs["title"]
            if "content" in kwargs:
                self.config["data"]["content"] = kwargs["content"]

        if self.provider_name.lower() == "gocqhttp":
            access_token = self.config.get("access_token")
            if access_token:
                self.config["token"] = access_token

        try:
            resp = self.notifier.notify(**self.config)
            if isinstance(resp, Response):
                if resp.status_code != 200:
                    logger.warning("Push notify failed!")
                    logger.warning(f"HTTP Code:{resp.status_code}")
                    return False
                else:
                    if self.provider_name.lower() == "gocqhttp":
                        return_data: dict = resp.json()
                        if return_data["status"] == "failed":
                            logger.warning("Push notify failed!")
                            logger.warning(
                                f"Return message:{return_data['wording']}")
                            return False
        except OnePushException:
            logger.exception("Push notify failed")
            return False
        except SMTPResponseException:
            # logger.warning("Appear SMTPResponseException")
            pass
        except Exception as e:
            logger.exception(e)
            return False
        logger.info("Push notify success")
        return True

    async def send_text_message(self, text: str, timeout: int = 10) -> bool:
        if not self.enable_tg:
            return False
        proxy = self.proxy
        token = self.token
        chat_id = str(self.chat_id)

        """发送纯文本消息"""
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}

        try:
            connector = None
            if proxy and proxy.startswith("socks"):
                connector = ProxyConnector.from_url(proxy)

            async with aiohttp.ClientSession(connector=connector) as session:
                kwargs = {"proxy": proxy} if proxy and not connector else {}

                async with session.post(
                        url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=timeout),
                        **kwargs
                ) as response:
                    result = await response.json()
                    return result.get("ok", False)

        except Exception as e:
            logger.error(f"发送文本失败: {str(e)}")
            return False

    def send_push(self, title: str, content: str, image='', log_path=''):
        try:
            provider_name = getattr(self, 'provider_name', '').lower()
            if provider_name == 'wechatworkbot':
                logger.info('企业微信机器人推送分支')

                webhook_url = self.get_wechatwork_webhook_url()
                if webhook_url:
                    log_payload = self.log_to_wechatwork_image(content, log_path)
                    if log_payload:
                        self.send_wechatwork_image_payload(webhook_url, log_payload, 'log')

                    image_payload = self.image_to_wechatwork_image(image)
                    if image_payload:
                        self.send_wechatwork_image_payload(webhook_url, image_payload, 'screenshot')
                    elif image:
                        logger.warning('企业微信机器人截图跳过: 无效图片')
                else:
                    logger.warning('企业微信机器人图片跳过: 缺少webhook地址')

                ok = self.push(
                    title=f'{I18n.trans_zh_cn(title)}',
                    content=f'{content}',
                )
                return ok

            head_text = f'<b>{content}</b><br/><br/>'

            # 读取日志文件内容
            content_text = f'<p>{log_path}</p>'
            if log_path:
                log_file = Path(log_path)
                if log_file.exists():
                    content_text = log_file.read_text(encoding='utf-8')
                    lines = content_text.splitlines()
                    # 如果超过20行，只取最后20行
                    if len(lines) > 20:
                        lines = lines[-20:]
                    content_text = ''.join(
                        f'<p style="font-size:8px;">{item}</p>'
                        for item in lines
                    )

            # 读取并处理图片
            image_b64 = f'<p>{image}</p>'
            b64_code = self.image_to_base64(image)
            if b64_code:
                image_b64 = f'<img src="data:image/jpeg;base64,{b64_code}" alt="image" /><br/><br/>'

            # 组装HTML内容
            body = head_text + image_b64 + content_text

            # 返回 HTML 内容的推送结果
            return self.push_html(title=f'{I18n.trans_zh_cn(title)}', content=body)
        except Exception as e:
            # 记录异常错误
            logger.error(f"出现异常: {e}")
            # 备用方案：发送普通消息
            return self.push(title=title, content=content)

    def get_wechatwork_webhook_url(self) -> Optional[str]:
        key = self.config.get('key')
        if not key:
            return getattr(self.notifier, 'url', None)
        if key.startswith('http://') or key.startswith('https://'):
            return key
        base_url = getattr(self.notifier, 'base_url', '')
        if base_url:
            return base_url.format(key)
        return None

    def send_wechatwork_image_payload(self, webhook_url: str, payload: dict, label: str) -> bool:
        resp = self.notifier.request('post', webhook_url, json=payload)
        if isinstance(resp, Response) and resp.status_code != 200:
            logger.warning(f'企业微信机器人 {label} 图片推送失败！')
            logger.warning(f'HTTP状态码: {resp.status_code}')
            logger.warning(f'响应内容: {getattr(resp, "text", "")}')
            return False
        logger.info(f'企业微信机器人 {label} 图片推送成功')
        return True

    def log_to_wechatwork_image(self, content: str, log_path: Optional[str | Path]):
        try:
            if not log_path:
                return None
            log_file = Path(log_path)
            if not log_file.exists():
                return None

            lines = log_file.read_text(encoding='utf-8').splitlines()
            if len(lines) > 28:
                lines = lines[-28:]

            header = [
                '=' * 100,
                f' {content} '.center(100, '-'),
                '=' * 100,
            ]
            return self.text_to_wechatwork_image(header + lines)
        except Exception as e:
            logger.error(f'企业微信机器人日志图片编码失败: {e}')
            return None

    def text_to_wechatwork_image(self, lines: list[str]):
        font_paths = [
            r'C:\Windows\Fonts\simsun.ttc',
            r'C:\Windows\Fonts\msyh.ttc',
            r'C:\Windows\Fonts\consola.ttf',
        ]
        font = None
        for font_path in font_paths:
            if Path(font_path).exists():
                font = ImageFont.truetype(font_path, 22)
                break
        if font is None:
            font = ImageFont.load_default()

        padding_x = 22
        padding_y = 18
        line_gap = 8
        measure = Image.new('RGB', (1, 1), 'white')
        draw = ImageDraw.Draw(measure)

        normalized = [line if line else ' ' for line in lines]
        widths = []
        heights = []
        for line in normalized:
            bbox = draw.textbbox((0, 0), line, font=font)
            widths.append(bbox[2] - bbox[0])
            heights.append(bbox[3] - bbox[1])

        line_height = max(heights or [24]) + line_gap
        width = max(widths or [800]) + padding_x * 2
        width = max(900, min(width, 1800))
        height = padding_y * 2 + line_height * len(normalized)

        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)
        y = padding_y
        for line in normalized:
            draw.text((padding_x, y), line, fill=(20, 20, 20), font=font)
            y += line_height

        return self.pil_image_to_wechatwork_image(img, quality=85)

    def pil_image_to_wechatwork_image(self, pil_img: Image.Image, quality: int = 85):
        image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        while quality >= 45:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            img_bytes = cv2.imencode('.jpg', image, encode_param)[1].tobytes()
            if len(img_bytes) <= 2 * 1024 * 1024:
                return {
                    'msgtype': 'image',
                    'image': {
                        'base64': base64.b64encode(img_bytes).decode(),
                        'md5': hashlib.md5(img_bytes).hexdigest(),
                    },
                }
            quality -= 10
        logger.warning('企业微信机器人图片跳过: 图片大于2MB')
        return None

    def image_to_wechatwork_image(self, image_path: Optional[str | Path | np.ndarray]):
        try:
            if isinstance(image_path, (str, Path)):
                img_path = Path(image_path)
                if not img_path.exists():
                    logger.warning('企业微信机器人图片文件不存在')
                    return None
                with Image.open(img_path) as pil_img:
                    image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            elif isinstance(image_path, numpy.ndarray):
                image = cv2.cvtColor(image_path, cv2.COLOR_RGB2BGR)
            else:
                return None

            image = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 50]
            img_bytes = cv2.imencode('.jpg', image, encode_param)[1].tobytes()
            if len(img_bytes) > 2 * 1024 * 1024:
                logger.warning('企业微信机器人图片跳过: 图片大于2MB')
                return None

            return {
                'msgtype': 'image',
                'image': {
                    'base64': base64.b64encode(img_bytes).decode(),
                    'md5': hashlib.md5(img_bytes).hexdigest(),
                },
            }
        except Exception as e:
            logger.error(f'企业微信机器人图片编码失败: {e}')
            return None

    def image_to_base64(self, image_path: Optional[str | Path | np.ndarray]):
        try:
            if isinstance(image_path, (str, Path)):
                img_path = Path(image_path)
                if not img_path.exists():
                    logger.warning("图片文件不存在")
                    return image_path
                with Image.open(img_path) as pil_img:
                    image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            elif isinstance(image_path,  numpy.ndarray):
                image = image_path
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            image = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)
            # 使用JPEG格式压缩，质量参数85平衡清晰度和文件大小
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 50]
            img_str = cv2.imencode('.jpg', image, encode_param)[1].tobytes()
            b64_code = base64.b64encode(img_str)
            b64_code = b64_code.decode()
            return b64_code
        except Exception as e:
            logger.error(f"图片处理失败: {str(e)}")
            return None

    def push_html(self, **kwargs):
        SMTP.set_message_parser(self.custom_parse)
        kwargs["type"] = "mail"
        self.push(**kwargs)
        SMTP.set_message_parser(_default_message_parser)

    def custom_parse(self, subject: str = '', title: str = '', content: str = '', From: str = None, user: str = None,
                     To: str = None, **kwargs, ):
        msg = EmailMessage()
        # Use subject if avaliable, title for compatibility with other providers
        msg["Subject"] = subject or title
        # Fallback to username if `From` address not provided
        msg["From"] = From or user
        # Send to yourself if `To` address not provided
        msg["To"] = To or user

        msg.set_content(content, subtype='html', charset='utf-8')  # 关键修改点
        return msg


if __name__ == '__main__':
    from module.config.config import Config

    config = Config('mi')
    image_path = r"D:\OnmyojiAutoScript\111\ljx\log\error\GamePageUnknownError\DemonEncounter\DU\DU 19点35分44 2026-06-25.png"
    log_path = r"D:\OnmyojiAutoScript\111\ljx\log\error\GamePageUnknownError\DemonEncounter\DU\DU 19点35分44 2026-06-25.log"
    # config.notifier.push(title='AbyssTrials', content=f"<a href='{image_path}'>image_path</a><br/><a href='{log_path}'>log_path</a>", image=image_path, log_path=log_path)
    config.notifier.send_push(title='Dokan', content='Dokan，请及时处理', image=image_path, log_path=log_path)
