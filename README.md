# AstrBot Grok 图像生成与编辑插件

[![AstrBot](https://img.shields.io/badge/AstrBot->=v4.5.7-blue)](https://github.com/Soulter/AstrBot)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

基于 Grok API (`grok-imagine-image-pro`) 的图像生成与编辑插件，支持 aiocqhttp 平台（OneBot v11 / QQ）。

## 🌟 功能特性

- 🎨 **图像生成** - 根据文本描述生成高质量图像
- ✏️ **图像编辑** - 基于原图和提示词智能编辑图像
- 🤖 **AI Tool 集成** - 注册 LLM Tool，让 AI 自动调用图像功能
- 🖼️ **图片消息处理** - 自动提取用户发送的图片 URL 或本地路径
- 💾 **自动保存图片** - API 返回的图片自动下载并保存到本地目录
- 📁 **本地文件支持** - 支持将本地图片文件转为 base64 发送给 API
- 🌐 **HTTP 代理支持** - 支持通过代理连接 Grok API
- 🔄 **自动重试** - 内置请求重试机制，提高稳定性
- 🛠️ **可视化配置** - 在 AstrBot WebUI 中轻松配置插件参数

## 📦 安装方法

### 方法一：手动安装

1. 克隆或下载本插件到 AstrBot 插件目录：
   ```bash
   cd AstrBot/data/plugins/
   git clone https://github.com/AstrBotDevs/astrbot_plugin_grok_image
   ```

2. 重启 AstrBot 或重载插件

3. 在 WebUI 中配置 Grok API Key

### 方法二：通过插件市场（如果可用）

在 AstrBot WebUI 的插件市场中搜索 `astrbot_plugin_grok_image` 并安装。

## ⚙️ 配置说明

在 AstrBot WebUI 的插件配置页面中设置以下参数：

### 基础配置

| 配置项 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `grok_api_key` | string | ✅ | - | Grok API Key，从 [xAI Console](https://console.x.ai/) 获取 |
| `grok_default_aspect_ratio` | string | ❌ | `1:1` | 默认图像宽高比 |
| `grok_default_resolution` | string | ❌ | `1k` | 默认图像分辨率 |

### 网络设置

| 配置项 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `network_settings.http_proxy` | string | ❌ | - | HTTP 代理地址，格式: `http://host:port` 或 `http://user:pass@host:port` |
| `network_settings.https_proxy` | string | ❌ | - | HTTPS 代理地址，留空则使用 HTTP 代理设置 |

### 存储设置

| 配置项 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `storage_settings.save_directory` | string | ❌ | `/AstrBot/data/plugin_data/grok_image/` | 图片保存目录的绝对路径 |
| `storage_settings.filename_prefix` | string | ❌ | `grok_` | 保存的图片文件名前缀 |

### 高级设置

| 配置项 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `advanced_settings.request_timeout` | int | ❌ | `120` | API 请求超时时间（秒） |
| `advanced_settings.max_retries` | int | ❌ | `3` | 请求失败时的最大重试次数 |

### 支持的宽高比

`1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `2:1`, `1:2`, `19.5:9`, `9:19.5`, `20:9`, `9:20`, `auto`

### 支持的分辨率

- `1k` - 标准清晰度
- `2k` - 高清晰度

## 🚀 使用方法

### 命令方式

#### 生成图像

```
/grok_gen <提示词> [宽高比] [分辨率]
```

**示例：**
```
/grok_gen 一只可爱的猫咪 1:1 1k
/grok_gen 科幻城市夜景 16:9 2k
/grok_gen 油画风格的山水画 4:3 1k
```

**返回结果：**
```
✅ 图像生成成功！
📁 文件路径: /AstrBot/data/plugin_data/grok_image/grok_20250225_143052_a1b2c3d4.jpg
🌐 原始链接: https://api.x.ai/image/...
```

#### 编辑图像（支持三种方式）

**方式一：使用图片 URL**
```
/grok_edit <图片URL> <提示词>
```

**方式二：直接发送图片**
```
[发送图片] /grok_edit <提示词>
```

**方式三：使用本地文件路径（自动转 base64）**
```
/grok_edit <文件路径> <提示词>
```

**示例：**
```
# 使用网络图片
/grok_edit https://example.com/image.jpg 将背景改为蓝色

# 直接发送图片并附带命令
[图片] /grok_edit 添加一些花朵装饰

# 使用本地文件路径（支持绝对路径）
/grok_edit /AstrBot/data/temp/xxxxx.jpg 换成动漫风格
/grok_edit /home/user/images/photo.png 添加滤镜效果
```

**返回结果：**
```
✅ 图像编辑成功！
📁 文件路径: /AstrBot/data/plugin_data/grok_image/grok_20250225_143150_e5f6g7h8.png
🌐 原始链接: https://api.x.ai/image/...
```

#### 查看帮助

```
/grok_help
```

### LLM Tool 方式（推荐）

插件自动注册了两个 LLM Tool，AI 可以根据对话上下文自动调用：

- `grok_generate_image` - 生成图像
- `grok_edit_image` - 编辑图像（支持 URL 和本地文件路径自动识别）

**使用示例：**
```
用户：帮我画一只在月球上的宇航员
AI：[自动调用 grok_generate_image] 正在为您生成图像...
AI：图像生成成功！文件路径: /AstrBot/data/plugin_data/grok_image/grok_20250225_143052_a1b2c3d4.jpg
```

```
用户：[发送一张猫的图片] 把这只猫换成狗
AI：[自动调用 grok_edit_image，从消息中提取图片 URL] 正在编辑图像...
AI：图像编辑成功！文件路径: /AstrBot/data/plugin_data/grok_image/grok_20250225_143150_e5f6g7h8.png
```

```
用户：编辑这张图片 /AstrBot/data/temp/mypic.jpg 改成油画风格
AI：[自动调用 grok_edit_image，识别为本地文件并转 base64] 正在编辑图像...
AI：图像编辑成功！文件路径: /AstrBot/data/plugin_data/grok_image/grok_20250225_143230_i9j0k1l2.jpg
```

## 💾 图片自动保存说明

API 返回的图片会自动下载并保存到本地目录：

### 保存路径
- **默认路径**: `/AstrBot/data/plugin_data/grok_image/`
- **可配置**: 在 `storage_settings.save_directory` 中设置自定义路径

### 文件名格式
```
{前缀}_{时间戳}_{UUID}.{扩展名}
```
示例：`grok_20250225_143052_a1b2c3d4.jpg`

### 文件格式自动识别
根据 API 返回的 Content-Type 自动识别格式：
- `image/jpeg` → `.jpg`
- `image/png` → `.png`
- `image/gif` → `.gif`
- `image/webp` → `.webp`
- 其他 → `.jpg`（默认）

### 输出内容
插件会返回：
```
✅ 图像生成/编辑成功！
📁 文件路径: {绝对路径}
🌐 原始链接: {临时URL}
```

## 📁 本地文件处理说明

当使用本地文件路径时，插件会自动：

1. **检测文件类型** - 判断是本地文件还是 URL
2. **读取文件** - 从磁盘读取图片文件
3. **转码 base64** - 将文件转为 base64 编码
4. **添加 MIME 类型** - 根据文件扩展名自动识别格式
5. **发送 API** - 使用 `image_base64` 类型发送给 Grok API

**支持的图片格式：**
- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- GIF (`.gif`)
- WebP (`.webp`)
- BMP (`.bmp`)

## 🌐 HTTP 代理配置

如果服务器无法直接访问 Grok API，可以配置 HTTP 代理：

### 配置示例

```json
{
  "network_settings": {
    "http_proxy": "http://127.0.0.1:7890",
    "https_proxy": "http://127.0.0.1:7890"
  }
}
```

### 带认证的代理

```json
{
  "network_settings": {
    "http_proxy": "http://username:password@proxy.example.com:8080"
  }
}
```

## 📁 文件结构

```
astrbot_plugin_grok_image/
├── metadata.yaml          # 插件元数据
├── _conf_schema.json      # 配置模式定义
├── main.py               # 主插件代码
├── requirements.txt      # 依赖列表
└── README.md             # 本文件
```

保存的图片将存放在：
```
/AstrBot/data/plugin_data/grok_image/
├── grok_20250225_143052_a1b2c3d4.jpg
├── grok_20250225_143150_e5f6g7h8.png
└── ...
```

## 🔧 技术细节

- **模型**: `grok-imagine-image`（Grok图像生成模型）
- **API 端点**: `https://api.x.ai/v1`
- **支持平台**: aiocqhttp（OneBot v11 / QQ）
- **最低 AstrBot 版本**: v4.5.7
- **依赖**: `aiohttp>=3.8.0`

## ⚠️ 注意事项

1. **API Key 安全**: 请勿将您的 Grok API Key 泄露给他人
2. **网络环境**: 确保服务器能够访问 `api.x.ai`，或使用 HTTP 代理
3. **磁盘空间**: 保存的图片会占用磁盘空间，请定期清理
4. **内容审核**: 生成的图像会经过内容审核，违规内容会被过滤
5. **速率限制**: 请注意 Grok API 的速率限制，详见 [xAI 文档](https://docs.x.ai/)
6. **代理设置**: 如果使用代理，请确保代理服务器稳定可用
7. **本地文件权限**: 使用本地文件时，确保 AstrBot 有读取权限
8. **保存目录权限**: 确保插件有写入保存目录的权限

## 📝 更新日志

### v1.0.3
- ✨ 初始版本发布
- 🎨 支持图像生成和编辑
- 🤖 集成 LLM Tool 功能
- 🖼️ 支持图片消息自动提取
- 💾 支持 API 返回图片自动保存到本地
- 📁 支持本地文件转 base64 发送
- 🌐 支持 HTTP 代理
- ⚙️ 支持可视化配置
### 已知BUG
- 🥺 下载图片完成后，控制台输出完成消息。LLM需要再使用send_message_to_user工具发送给用户。
- 😋 图片默认保存地址仿佛有些问题。
- 🥺 尽量不要使用pro模型或编辑过大文件，会导致任务超时。如有其他异常，请使用/stop命令进行中断。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 [MIT](LICENSE) 许可证。

## 🔗 相关链接

- [AstrBot 官方文档](https://docs.astrbot.app/)
- [AstrBot GitHub](https://github.com/Soulter/AstrBot)
- [xAI 开发者文档](https://docs.x.ai/)

- [Grok API 定价](https://console.x.ai/)

