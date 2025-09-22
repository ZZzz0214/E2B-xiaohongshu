# E2B Sandbox 浏览器自动化框架

> 基于E2B云平台的高级浏览器自动化框架，支持VNC远程桌面、智能混合操作和批量任务处理

## 🚀 项目简介

这是一个基于E2B云沙盒平台构建的企业级浏览器自动化框架，专为解决复杂的Web自动化场景而设计。框架集成了VNC远程桌面、智能故障检测、混合人机操作等先进功能，特别适用于需要绕过反爬虫检测的自动化任务。

### 🎯 核心特性

- **🖥️ VNC远程桌面**: 提供完整的图形化界面，支持手动登录后自动化接管
- **🔄 混合自动化**: 自动化操作 → 手动干预 → 继续自动化的无缝切换
- **🛡️ 反检测优化**: 基于真实浏览器环境，有效绕过反爬虫机制
- **📊 批量处理**: 支持大规模并发任务和持久化会话管理
- **🔧 智能故障处理**: 自动检测和恢复常见的自动化故障
- **📋 RESTful API**: 完整的HTTP API接口，易于集成

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                           E2B Sandbox 自动化框架                        │
├─────────────────────────────────────────────────────────────────────┤
│                          FastAPI HTTP Server                        │
│  ┌─────────────────┬─────────────────┬─────────────────────────────┐ │
│  │  Browser API    │   Text API      │      Sandbox API            │ │
│  │  浏览器自动化      │   文本处理       │      沙盒管理                │ │
│  └─────────────────┴─────────────────┴─────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                         Core Components                             │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                   Sandbox Manager                               │ │
│  │  • 持久化沙盒管理    • 自动清理    • 故障恢复                      │ │
│  └─────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                        E2B Cloud Platform                           │
│  ┌─────────────┬─────────────┬─────────────┬─────────────────────────┐ │
│  │   Xvfb      │   x11vnc    │ websockify  │      Playwright         │ │
│  │ 虚拟显示服务   │  VNC服务器   │  Web代理     │     浏览器驱动           │ │
│  └─────────────┴─────────────┴─────────────┴─────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    Ubuntu 20.04 Container                       │ │
│  │  • Python 3.9     • Node.js 18     • Chrome Browser            │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## 📁 项目结构

```
E2B-sandbox/
├── sandbox-server/                    # 主服务器代码
│   ├── src/                          # 源代码目录
│   │   ├── api/                      # API路由模块
│   │   │   ├── browser_routes.py     # 浏览器自动化API
│   │   │   ├── text_routes.py        # 文本处理API
│   │   │   └── sandbox_routes.py     # 沙盒管理API
│   │   ├── core/                     # 核心组件
│   │   │   └── sandbox_manager.py    # 沙盒管理器
│   │   ├── models/                   # 数据模型
│   │   │   └── request_models.py     # 请求响应模型
│   │   └── app.py                    # FastAPI应用入口
│   ├── config/                       # 配置文件
│   │   └── settings.py               # 应用配置
│   ├── templates/                    # E2B模板
│   │   └── unified-automation/       # 统一自动化模板
│   │       ├── e2b.Dockerfile        # Docker环境定义
│   │       ├── e2b.toml             # E2B配置文件
│   │       └── tools/               # 沙盒内工具
│   │           ├── browser_service.py    # 浏览器服务
│   │           ├── browser_utils.py      # 浏览器工具
│   │           ├── vnc_manager.py        # VNC管理器
│   │           ├── smart_takeover.py     # 智能接管
│   │           ├── failure_detector.py   # 故障检测
│   │           └── text_utils.py         # 文本处理
│   └── requirements.txt              # 服务器依赖
├── quick_demo.py                     # 快速演示脚本
└── README.md                         # 项目文档
```

## 🔧 技术栈

### 后端服务器
- **FastAPI**: 高性能异步Web框架
- **Python 3.9+**: 主要开发语言
- **E2B SDK**: 云沙盒平台SDK
- **Uvicorn**: ASGI服务器

### 沙盒环境 (E2B Container)
- **Ubuntu 20.04**: 基础操作系统
- **Playwright**: 现代浏览器自动化库
- **Chrome Browser**: 目标浏览器
- **Xvfb**: X虚拟帧缓冲区（虚拟显示）
- **x11vnc**: X11 VNC服务器
- **websockify**: WebSocket到TCP代理
- **noVNC**: HTML5 VNC客户端
- **Fluxbox**: 轻量级窗口管理器

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd E2B-sandbox

# 安装服务器依赖
cd sandbox-server
pip install -r requirements.txt
```

### 2. 配置设置

在 `sandbox-server/config/settings.py` 中配置你的E2B API密钥：

```python
E2B_API_KEY = "your_e2b_api_key_here"
DEFAULT_TEMPLATE_ID = "dgcanzrrlvhyju0asxth"  # 已构建的模板ID
```

### 3. 启动服务器

```bash
cd sandbox-server/src
python app.py
```

服务器将在 `http://localhost:8989` 启动

### 4. 部署E2B模板（可选）

如果需要修改沙盒环境：

```bash
# 进入模板目录
cd sandbox-server/templates/unified-automation

# 构建并部署模板
e2b template build
```

## 📚 API 使用指南

### 🖥️ VNC远程桌面 API

#### 启动VNC服务

```http
POST /api/browser/vnc/start
Content-Type: application/json

{
  "vnc_port": 5901,
  "no_vnc_port": 6080,
  "with_browser": true
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "VNC服务启动成功",
  "data": {
    "persistent_id": "persistent_xxx",
    "e2b_sandbox_id": "xxxxxx",
    "access_info": {
      "external_web_url": "https://6080-xxxxxx.e2b.app/",
      "web_browser": "https://6080-xxxxxx.e2b.app/",
      "internal_web_url": "http://localhost:6080",
      "instructions": "使用external_web_url在浏览器中打开VNC界面"
    }
  }
}
```

### 🤖 浏览器自动化 API

#### 批量自动化操作

```http
POST /api/browser/automation
Content-Type: application/json

{
  "actions": [
    {
      "method": "start",
      "params": {"headless": false},
      "description": "启动浏览器"
    },
    {
      "method": "visit",
      "params": {"url": "https://xiaohongshu.com"},
      "description": "访问小红书"
    },
    {
      "method": "find",
      "params": {
        "selector": "input[placeholder*='搜索']",
        "action": "fill",
        "value": "美食推荐"
      },
      "description": "搜索美食推荐"
    }
  ],
  "persistent": true,
  "auto_cleanup": false
}
```

### 🔄 混合自动化流程

1. **启动VNC服务**: 获取可视化界面
2. **执行自动化脚本**: 自动打开网站、填充表单
3. **手动干预**: 在VNC界面中手动登录
4. **继续自动化**: 登录后自动继续执行任务

**完整示例：**

```python
import requests
import time

# 1. 启动VNC + 浏览器
vnc_response = requests.post("http://localhost:8989/api/browser/vnc/start", json={
    "with_browser": True
})

vnc_url = vnc_response.json()["data"]["access_info"]["external_web_url"]
print(f"VNC访问地址: {vnc_url}")

# 2. 执行自动化操作
automation_response = requests.post("http://localhost:8989/api/browser/automation", json={
    "actions": [
        {
            "method": "visit",
            "params": {"url": "https://xiaohongshu.com"},
            "description": "访问小红书"
        },
        {
            "method": "find",
            "params": {
                "selector": "a[href*='login']",
                "action": "click"
            },
            "description": "点击登录按钮"
        }
    ],
    "persistent": True
})

print("请在VNC界面中手动完成登录...")
input("登录完成后按Enter继续...")

# 3. 继续自动化
continue_response = requests.post("http://localhost:8989/api/browser/automation", json={
    "actions": [
        {
            "method": "find",
            "params": {
                "selector": "input[placeholder*='搜索']",
                "action": "fill",
                "value": "美食推荐"
            },
            "description": "搜索美食推荐"
        },
        {
            "method": "find",
            "params": {
                "selector": "button[type='submit'], .search-btn",
                "action": "click"
            },
            "description": "点击搜索"
        }
    ],
    "persistent": True
})
```

## 🎨 高级特性

### 1. 智能故障检测与恢复

框架内置智能故障检测机制，可自动识别和处理：
- 页面加载超时
- 元素定位失败
- 网络连接问题
- 反爬虫验证码

### 2. 持久化会话管理

支持长时间运行的自动化任务：
- 浏览器实例保活
- 登录状态保持
- 自动资源清理
- 并发任务隔离

### 3. 可视化调试

通过VNC远程桌面提供：
- 实时操作观察
- 手动干预能力
- 调试信息查看
- 截图和录屏

### 4. 扩展性设计

框架支持自定义扩展：
- 自定义操作方法
- 插件化故障处理
- 多浏览器支持
- 第三方工具集成

## 🔒 安全与最佳实践

### 安全配置

- **API密钥管理**: 使用环境变量存储敏感信息
- **CORS设置**: 配置允许的源域名
- **速率限制**: 防止API滥用
- **沙盒隔离**: 每个任务在独立环境中运行

### 性能优化

- **资源池管理**: 复用浏览器实例
- **并发控制**: 限制同时运行的任务数
- **内存监控**: 自动清理过期资源
- **缓存策略**: 减少重复操作开销

## 🛠️ 开发与调试

### 本地开发

```bash
# 启动开发服务器
cd sandbox-server/src
python app.py

# 运行测试
python quick_demo.py
```

### 调试技巧

1. **使用VNC界面**: 实时观察浏览器操作
2. **查看日志**: 检查详细的执行日志
3. **API测试**: 使用FastAPI自动生成的文档 (`/docs`)
4. **分步执行**: 将复杂任务分解为小步骤

### 常见问题

**Q: VNC界面无法访问？**
A: 检查E2B沙盒ID是否正确，确保使用外部访问地址

**Q: 浏览器启动失败？**
A: 检查E2B模板是否正确构建，查看沙盒日志

**Q: 自动化操作不稳定？**
A: 增加等待时间，使用更精确的选择器

## 📈 监控与运维

### 健康检查

```http
GET /health
```

### 系统状态

```http
GET /api/browser/status
```

### 沙盒管理

```http
GET /api/sandbox/list
POST /api/sandbox/cleanup
```

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交代码变更
4. 创建Pull Request

## 📄 许可证

[MIT License](LICENSE)

---

**🎯 这个框架特别适用于：**
- 电商平台数据采集
- 社交媒体内容爬取
- 表单自动填写
- 登录流程自动化
- 复杂的人机交互场景
