"""AstrBot Grok 图像生成与编辑插件

基于 Grok API 的图像生成与编辑插件，支持 aiocqhttp 平台。
支持 HTTP 代理、图片消息自动处理、自动保存图片到本地。
"""

import asyncio
import base64
import json
import os
import socket
import uuid
from datetime import datetime
from typing import Optional, List, Dict

import aiohttp
from aiohttp import TCPConnector
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger
from astrbot.api import AstrBotConfig
from astrbot.api.message_components import Image

# Grok API 配置
GROK_API_BASE = "https://api.x.ai/v1"
GROK_IMAGE_MODEL = "grok-imagine-image"

# 支持的宽高比
VALID_ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4", "2:1", "1:2", "19.5:9", "9:19.5", "20:9", "9:20", "auto"]
# 支持的分辨率
VALID_RESOLUTIONS = ["1k", "2k"]

# TCP 连接设置
TCP_CONNECT_TIMEOUT = 30
TCP_TOTAL_TIMEOUT = 300


class GrokImagePlugin(Star):
    """Grok 图像生成与编辑插件"""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.context = context
        self.config = config
        
        # 从配置中读取 API Key
        self.api_key = config.get("grok_api_key", "")
        self.default_aspect_ratio = config.get("grok_default_aspect_ratio", "1:1")
        self.default_resolution = config.get("grok_default_resolution", "1k")
        
        # 网络设置
        network_settings = config.get("network_settings", {})
        self.http_proxy = network_settings.get("http_proxy", "")
        self.https_proxy = network_settings.get("https_proxy", "") or self.http_proxy
        
        # 存储设置
        storage_settings = config.get("storage_settings", {})
        self.save_directory = storage_settings.get("save_directory", "")
        self.filename_prefix = storage_settings.get("filename_prefix", "grok_")
        
        # 如果没有配置保存目录，使用默认路径
        if not self.save_directory:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
            self.save_directory = os.path.join(data_dir, "plugin_data", "grok_image")
        
        # 确保保存目录存在
        os.makedirs(self.save_directory, exist_ok=True)
        logger.info(f"图片保存目录: {self.save_directory}")
        
        # 高级设置
        advanced_settings = config.get("advanced_settings", {})
        self.request_timeout = advanced_settings.get("request_timeout", 180)
        self.max_retries = advanced_settings.get("max_retries", 3)
        
        # aiohttp session（复用连接池）
        self._session: Optional[aiohttp.ClientSession] = None
        
        if not self.api_key:
            logger.warning("GrokImagePlugin: 未配置 grok_api_key，插件将无法正常工作")
        else:
            logger.info(f"GrokImagePlugin: 插件已加载 (代理: {self.http_proxy if self.http_proxy else '无'})")

    def _get_proxy(self) -> Optional[str]:
        """获取代理设置"""
        if self.https_proxy:
            return self.https_proxy
        if self.http_proxy:
            return self.http_proxy
        return None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 aiohttp session（带连接池和代理）"""
        if self._session is None or self._session.closed:
            connector = TCPConnector(
                limit=10,
                limit_per_host=5,
                enable_cleanup_closed=True,
                force_close=False,
                ttl_dns_cache=300,
                use_dns_cache=True,
                family=socket.AF_INET,
            )
            
            timeout = aiohttp.ClientTimeout(
                connect=TCP_CONNECT_TIMEOUT,
                total=TCP_TOTAL_TIMEOUT
            )
            
            trust_env = False
            proxy = self._get_proxy()
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    "User-Agent": "AstrBot-GrokImagePlugin/1.0.0"
                },
                trust_env=trust_env
            )
            
            self._session._grok_proxy = proxy
            
        return self._session

    def _is_local_file(self, path: str) -> bool:
        """检查是否是本地文件路径"""
        return path.startswith('/') or path.startswith('\\') or (len(path) > 1 and path[1] == ':')

    async def _file_to_base64(self, file_path: str) -> Optional[str]:
        """将本地文件转换为 base64 字符串"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None
            
            ext = os.path.splitext(file_path)[1].lower()
            mime_type = "image/jpeg"
            if ext == '.png':
                mime_type = "image/png"
            elif ext == '.gif':
                mime_type = "image/gif"
            elif ext == '.webp':
                mime_type = "image/webp"
            elif ext == '.bmp':
                mime_type = "image/bmp"
            
            with open(file_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            data_uri = f"data:{mime_type};base64,{image_data}"
            logger.info(f"文件转base64成功: {file_path}")
            return data_uri
            
        except Exception as e:
            logger.error(f"文件转base64失败: {file_path}, 错误: {str(e)}")
            return None

    async def _prepare_image_for_api(self, image_source: str) -> Optional[Dict]:
        """准备图片数据用于API调用（支持URL和本地文件）"""
        if self._is_local_file(image_source):
            base64_data = await self._file_to_base64(image_source)
            if base64_data:
                return {
                    "image": {
                        "url": base64_data,
                        "type": "image_url"
                    }
                }
            else:
                return None
        else:
            return {
                "image": {
                    "url": image_source,
                    "type": "image_url"
                }
            }

    async def _download_and_save_image(self, image_url: str) -> Optional[str]:
        """下载图片并保存到本地目录"""
        try:
            session = await self._get_session()
            proxy = getattr(session, '_grok_proxy', None)
            
            logger.info(f"正在下载图片...")
            
            async with session.get(image_url, proxy=proxy, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status != 200:
                    logger.error(f"图片下载失败: HTTP {response.status}")
                    return None
                
                image_data = await response.read()
                
                content_type = response.headers.get('Content-Type', '')
                if 'image/jpeg' in content_type or 'image/jpg' in content_type:
                    ext = '.jpg'
                elif 'image/png' in content_type:
                    ext = '.png'
                elif 'image/gif' in content_type:
                    ext = '.gif'
                elif 'image/webp' in content_type:
                    ext = '.webp'
                else:
                    ext = '.jpg'
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_id = str(uuid.uuid4())[:8]
                filename = f"{self.filename_prefix}{timestamp}_{unique_id}{ext}"
                
                file_path = os.path.join(self.save_directory, filename)
                
                with open(file_path, "wb") as f:
                    f.write(image_data)
                
                abs_path = os.path.abspath(file_path)
                logger.info(f"图片保存成功: {abs_path}")
                
                return abs_path
                
        except Exception as e:
            logger.error(f"图片下载或保存失败: {str(e)}")
            return None

    async def _call_grok_api(self, endpoint: str, payload: dict) -> dict:
        """调用 Grok API（带重试和代理支持）"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        url = f"{GROK_API_BASE}{endpoint}"
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                session = await self._get_session()
                proxy = getattr(session, '_grok_proxy', None)
                
                logger.info(f"Grok API 请求: {endpoint} (尝试 {attempt + 1}/{self.max_retries})")
                
                async with session.post(
                    url, 
                    headers=headers, 
                    json=payload,
                    ssl=True,
                    proxy=proxy
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Grok API HTTP 错误: {response.status}")
                        raise Exception(f"Grok API 错误 (HTTP {response.status}): {error_text}")
                    
                    result = await response.json()
                    logger.info(f"Grok API 请求成功")
                    return result
                    
            except asyncio.TimeoutError as e:
                last_error = f"请求超时"
                logger.warning(f"Grok API 请求超时 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                    
            except aiohttp.ClientProxyConnectionError as e:
                last_error = f"代理连接错误: {str(e)}"
                logger.error(f"代理连接失败: {last_error}")
                raise Exception(f"代理连接失败，请检查代理设置: {last_error}")
                    
            except aiohttp.ClientConnectorError as e:
                last_error = f"连接错误: {str(e)}"
                logger.warning(f"Grok API 连接失败 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    if self._session and not self._session.closed:
                        await self._session.close()
                    self._session = None
                    continue
                    
            except aiohttp.ClientError as e:
                last_error = f"客户端错误: {str(e)}"
                logger.warning(f"Grok API 客户端错误 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                    
            except Exception as e:
                last_error = f"未知错误: {str(e)}"
                logger.error(f"Grok API 调用异常: {last_error}")
                raise
        
        raise Exception(f"API 调用失败，已重试 {self.max_retries} 次: {last_error}")

    def _get_image_sources_from_event(self, event: AstrMessageEvent) -> List[str]:
        """从消息事件中提取图片源（URL或本地路径）"""
        image_sources = []
        for comp in event.message_obj.message:
            if isinstance(comp, Image):
                url = comp.url if hasattr(comp, 'url') and comp.url else None
                path = comp.path if hasattr(comp, 'path') and comp.path else None
                
                source = url or path
                if source:
                    image_sources.append(source)
                    logger.info(f"从消息中提取到图片源")
        return image_sources

    def _validate_aspect_ratio(self, aspect_ratio: str) -> str:
        """验证并返回有效的宽高比"""
        if aspect_ratio in VALID_ASPECT_RATIOS:
            return aspect_ratio
        logger.warning(f"无效的宽高比: {aspect_ratio}，使用默认值")
        return self.default_aspect_ratio

    def _validate_resolution(self, resolution: str) -> str:
        """验证并返回有效的分辨率"""
        if resolution in VALID_RESOLUTIONS:
            return resolution
        logger.warning(f"无效的分辨率: {resolution}，使用默认值")
        return self.default_resolution

    # ==================== LLM Tools ====================

    @filter.llm_tool(name="grok_generate_image")
    async def tool_generate_image(self, event: AstrMessageEvent, **kwargs) -> str:
        '''使用 Grok API 根据文本提示生成图像
        
        Args:
            prompt(string)[Required]: 图像生成提示词
            aspect_ratio(string): 宽高比，可选值: 1:1, 16:9, 9:16, 4:3, 3:4, 2:1, 1:2, 19.5:9, 9:19.5, 20:9, 9:20, auto。默认: 1:1
            resolution(string): 分辨率，可选值: 1k, 2k。默认: 1k
        '''
        if not self.api_key:
            return "错误：未配置 Grok API Key"
        
        prompt = kwargs.get("prompt", "")
        aspect_ratio = kwargs.get("aspect_ratio", self.default_aspect_ratio)
        resolution = kwargs.get("resolution", self.default_resolution)
        
        if not prompt or not prompt.strip():
            return "错误：提示词不能为空"
        
        aspect_ratio = self._validate_aspect_ratio(aspect_ratio)
        resolution = self._validate_resolution(resolution)
        
        payload = {
            "model": GROK_IMAGE_MODEL,
            "prompt": prompt.strip(),
            "aspect_ratio": aspect_ratio,
            "resolution": resolution
        }
        
        try:
            result = await asyncio.wait_for(
                self._call_grok_api("/images/generations", payload),
                timeout=self.request_timeout
            )
            
            if "data" in result and len(result["data"]) > 0:
                image_url = result["data"][0].get("url", "")
                if image_url:
                    saved_path = await self._download_and_save_image(image_url)
                    if saved_path:
                        return f"图像生成成功！文件路径: {saved_path}"
                    else:
                        return f"图像生成成功，但保存失败。URL: {image_url}"
                else:
                    return "错误：API 返回数据中没有图像 URL"
            else:
                return f"错误：API 返回数据格式异常"
                
        except asyncio.TimeoutError:
            logger.error("生成图像超时")
            return f"错误：生成图像超时（>{self.request_timeout}秒）。Grok API 处理时间较长，请使用命令方式重试"
        except Exception as e:
            logger.error(f"生成图像失败: {str(e)}")
            return f"生成图像失败: {str(e)}"

    @filter.llm_tool(name="grok_edit_image")
    async def tool_edit_image(self, event: AstrMessageEvent, **kwargs) -> str:
        '''使用 Grok API 根据原图和提示词编辑/修改图像
        
        Args:
            prompt(string)[Required]: 编辑提示词，描述你想要如何修改图像
            image_url(string): 原图 URL 地址或本地文件路径（单张图片）
            image_urls(array[string]): 原图 URL 列表（支持多张图片，取第一张）
        '''
        if not self.api_key:
            return "错误：未配置 Grok API Key"
        
        prompt = kwargs.get("prompt", "")
        image_url = kwargs.get("image_url", "")
        image_urls = kwargs.get("image_urls", None)
        
        # 优先使用 image_urls，其次使用 image_url
        image_source = ""
        if image_urls and len(image_urls) > 0:
            image_source = image_urls[0]
        elif image_url:
            image_source = image_url
        
        if not image_source or not image_source.strip():
            image_sources = self._get_image_sources_from_event(event)
            if image_sources:
                image_source = image_sources[0]
                logger.info(f"从消息中自动提取图片源")
            else:
                return "错误：原图不能为空，且未在消息中检测到图片"
        
        if not prompt or not prompt.strip():
            return "错误：编辑提示词不能为空"
        
        image_data = await self._prepare_image_for_api(image_source.strip())
        if not image_data:
            return f"错误：无法处理图片源: {image_source}"
        
        payload = {
            "model": GROK_IMAGE_MODEL,
            "prompt": prompt.strip(),
            **image_data
        }
        
        try:
            result = await asyncio.wait_for(
                self._call_grok_api("/images/edits", payload),
                timeout=self.request_timeout
            )
            
            if "data" in result and len(result["data"]) > 0:
                new_image_url = result["data"][0].get("url", "")
                if new_image_url:
                    saved_path = await self._download_and_save_image(new_image_url)
                    if saved_path:
                        return f"图像编辑成功！文件路径: {saved_path}"
                    else:
                        return f"图像编辑成功，但保存失败。URL: {new_image_url}"
                else:
                    return "错误：API 返回数据中没有图像 URL"
            else:
                return f"错误：API 返回数据格式异常"
                
        except asyncio.TimeoutError:
            logger.error("编辑图像超时")
            return f"错误：编辑图像超时（>{self.request_timeout}秒）。Grok API 处理时间较长，请使用命令方式重试"
        except Exception as e:
            logger.error(f"编辑图像失败: {str(e)}")
            return f"编辑图像失败: {str(e)}"

    # ==================== Commands ====================

    @filter.command("grok_gen")
    async def cmd_generate_image(self, event: AstrMessageEvent):
        """生成图像命令"""
        if not self.api_key:
            yield event.plain_result("❌ 错误：未配置 Grok API Key")
            return
        
        message = event.message_str.strip()
        parts = message.split(maxsplit=3)
        
        if len(parts) < 2:
            yield event.plain_result("❌ 用法: /grok_gen <提示词> [宽高比] [分辨率]")
            return
        
        prompt = parts[1]
        aspect_ratio = parts[2] if len(parts) > 2 else self.default_aspect_ratio
        resolution = parts[3] if len(parts) > 3 else self.default_resolution
        
        aspect_ratio = self._validate_aspect_ratio(aspect_ratio)
        resolution = self._validate_resolution(resolution)
        
        yield event.plain_result(f"🎨 正在生成图像，请稍候...（预计30-60秒）")
        
        payload = {
            "model": GROK_IMAGE_MODEL,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution
        }
        
        try:
            result = await asyncio.wait_for(
                self._call_grok_api("/images/generations", payload),
                timeout=self.request_timeout
            )
            
            if "data" in result and len(result["data"]) > 0:
                image_url = result["data"][0].get("url", "")
                if image_url:
                    saved_path = await self._download_and_save_image(image_url)
                    if saved_path:
                        yield event.plain_result(f"✅ 图像生成成功！\n📁 文件路径: {saved_path}")
                    else:
                        yield event.plain_result(f"⚠️ 保存失败\n🌐 {image_url}")
                else:
                    yield event.plain_result("❌ API 返回数据中没有图像 URL")
            else:
                yield event.plain_result("❌ API 返回数据格式异常")
                
        except asyncio.TimeoutError:
            yield event.plain_result(f"❌ 超时（>{self.request_timeout}秒），请稍后重试")
        except Exception as e:
            logger.error(f"生成图像失败: {str(e)}")
            yield event.plain_result(f"❌ 失败: {str(e)}")

    @filter.command("grok_edit")
    async def cmd_edit_image(self, event: AstrMessageEvent):
        """编辑图像命令"""
        if not self.api_key:
            yield event.plain_result("❌ 错误：未配置 Grok API Key")
            return
        
        message = event.message_str.strip()
        parts = message.split(maxsplit=2)
        
        image_sources = self._get_image_sources_from_event(event)
        
        image_source = None
        prompt = None
        
        if len(parts) >= 3:
            image_source = parts[1]
            prompt = parts[2]
        elif image_sources and len(parts) >= 2:
            image_source = image_sources[0]
            prompt = parts[1] if len(parts) > 1 else "美化"
        else:
            yield event.plain_result("❌ 用法: /grok_edit <图片> <提示词>")
            return
        
        is_local = self._is_local_file(image_source)
        yield event.plain_result(f"🎨 正在编辑...（预计30-60秒）")
        
        image_data = await self._prepare_image_for_api(image_source)
        if not image_data:
            yield event.plain_result(f"❌ 无法处理图片源")
            return
        
        payload = {
            "model": GROK_IMAGE_MODEL,
            "prompt": prompt,
            **image_data
        }
        
        try:
            result = await asyncio.wait_for(
                self._call_grok_api("/images/edits", payload),
                timeout=self.request_timeout
            )
            
            if "data" in result and len(result["data"]) > 0:
                new_image_url = result["data"][0].get("url", "")
                if new_image_url:
                    saved_path = await self._download_and_save_image(new_image_url)
                    if saved_path:
                        yield event.plain_result(f"✅ 编辑成功！\n📁 {saved_path}")
                    else:
                        yield event.plain_result(f"⚠️ 保存失败\n🌐 {new_image_url}")
                else:
                    yield event.plain_result("❌ API 返回数据中没有图像 URL")
            else:
                yield event.plain_result("❌ API 返回数据格式异常")
                
        except asyncio.TimeoutError:
            yield event.plain_result(f"❌ 超时（>{self.request_timeout}秒），请稍后重试")
        except Exception as e:
            logger.error(f"编辑图像失败: {str(e)}")
            yield event.plain_result(f"❌ 失败: {str(e)}")

    @filter.command("grok_help")
    async def cmd_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        proxy_status = "✅" if self.http_proxy else "❌"
        
        help_text = f"""🎨 Grok 图像插件

📌 命令:
• /grok_gen <提示词> [宽高比] [分辨率]
• /grok_edit <图片URL/路径> <提示词>
• /grok_help

⚙️ 设置:
• 代理: {proxy_status}
• 超时: {self.request_timeout}秒
• 保存目录: {self.save_directory}

⚠️ Grok API 处理时间较长（30-60秒），请耐心等待"""
        yield event.plain_result(help_text)

    async def terminate(self):
        """插件卸载时调用"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("GrokImagePlugin: session 已关闭")
        logger.info("GrokImagePlugin: 插件已卸载")

