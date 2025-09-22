# 基于E2B官方代码解释器镜像
FROM e2bdev/code-interpreter:latest

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:1
ENV VNC_PORT=5901
ENV NO_VNC_PORT=6080
ENV VNC_RESOLUTION=1920x1080

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    chromium \
    ca-certificates \
    fonts-liberation \
    fonts-noto-cjk \
    xvfb \
    x11vnc \
    x11-utils \
    fluxbox \
    dbus \
    psmisc \
    supervisor \
    wget \
    curl \
    net-tools \
    iproute2 \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    && rm -rf /var/lib/apt/lists/*

# 安装noVNC
RUN wget -qO- https://github.com/novnc/noVNC/archive/v1.4.0.tar.gz | tar xz -C /opt/ && \
    wget -qO- https://github.com/novnc/websockify/archive/v0.10.0.tar.gz | tar xz -C /opt/ && \
    mv /opt/noVNC-1.4.0 /opt/noVNC && \
    mv /opt/websockify-0.10.0 /opt/websockify && \
    ln -s /opt/noVNC/vnc.html /opt/noVNC/index.html && \
    chmod +x /opt/websockify/run && \
    pip install websockify

# 复制并安装Python依赖
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 安装Playwright浏览器依赖
RUN apt-get update && apt-get install -y \
    libasound2 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libfontconfig1 \
    libgtk-3-0 \
    libnspr4 \
    libpango-1.0-0 \
    libxss1 \
    libnss3 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# 安装Playwright浏览器
RUN PLAYWRIGHT_SKIP_BROWSER_DEPS=1 playwright install chromium

# 创建用户目录和权限
RUN mkdir -p /home/user/.vnc /home/user/.config/fluxbox /home/user/.cache/ms-playwright /home/user/tools

# 复制工具脚本
COPY tools/ /home/user/tools/

# 创建简化的VNC启动脚本
RUN echo '#!/bin/bash\n\
set -e\n\
export DISPLAY=:1\n\
\n\
# 清理现有进程\n\
pkill -f "Xvfb :1" || true\n\
pkill -f "x11vnc" || true\n\
pkill -f "fluxbox" || true\n\
pkill -f "websockify" || true\n\
sleep 2\n\
\n\
# 启动Xvfb\n\
echo "🖥️ 启动虚拟显示..."\n\
Xvfb :1 -screen 0 ${VNC_RESOLUTION:-1920x1080}x24 -ac +extension GLX +render -noreset &\n\
sleep 3\n\
\n\
# 启动窗口管理器\n\
echo "🪟 启动窗口管理器..."\n\
DISPLAY=:1 fluxbox &\n\
sleep 2\n\
\n\
# 启动VNC服务器\n\
echo "📡 启动VNC服务器..."\n\
DISPLAY=:1 x11vnc -display :1 -nopw -listen 0.0.0.0 -shared -forever -rfbport ${VNC_PORT:-5901} &\n\
sleep 3\n\
\n\
# 启动noVNC\n\
echo "🌐 启动noVNC..."\n\
cd /opt/websockify && ./run --web=/opt/noVNC ${NO_VNC_PORT:-6080} localhost:${VNC_PORT:-5901} &\n\
sleep 3\n\
\n\
echo "✅ VNC服务启动完成"\n\
echo "📺 VNC端口: ${VNC_PORT:-5901}"\n\
echo "🌐 noVNC端口: ${NO_VNC_PORT:-6080}"\n' > /home/user/start-vnc.sh

# 创建综合启动脚本 (VNC + 浏览器守护进程)
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "🚀 启动E2B浏览器自动化环境..."\n\
\n\
# 设置环境变量\n\
export DISPLAY=:1\n\
export PYTHONPATH="/home/user/tools"\n\
\n\
# 清理现有进程\n\
pkill -f "Xvfb :1" || true\n\
pkill -f "x11vnc" || true\n\
pkill -f "fluxbox" || true\n\
pkill -f "websockify" || true\n\
pkill -f "browser_daemon.py" || true\n\
sleep 2\n\
\n\
# 启动VNC服务\n\
echo "📺 启动VNC服务..."\n\
bash /home/user/start-vnc.sh\n\
\n\
# 等待VNC服务就绪\n\
echo "⏳ 等待VNC服务就绪..."\n\
sleep 8\n\
for i in {1..15}; do\n\
    if curl -f http://localhost:6080 >/dev/null 2>&1; then\n\
        echo "✅ VNC服务已就绪"\n\
        break\n\
    fi\n\
    echo "   检查VNC服务... ($i/15)"\n\
    sleep 3\n\
done\n\
\n\
# 启动浏览器守护进程\n\
echo "🤖 启动浏览器守护进程..."\n\
cd /home/user/tools\n\
python3 browser_daemon.py &\n\
DAEMON_PID=$!\n\
\n\
# 等待守护进程就绪\n\
echo "⏳ 等待守护进程就绪..."\n\
sleep 5\n\
for i in {1..20}; do\n\
    if curl -f http://localhost:8080/api/health >/dev/null 2>&1; then\n\
        echo "✅ 守护进程已就绪"\n\
        break\n\
    fi\n\
    echo "   检查守护进程... ($i/20)"\n\
    # 显示进程状态用于调试\n\
    if [ $i -eq 10 ]; then\n\
        echo "🔍 调试信息:"\n\
        ps aux | grep python3 || true\n\
        netstat -tulpn | grep :8080 || true\n\
    fi\n\
    sleep 3\n\
done\n\
\n\
echo "✅ 所有服务启动完成"\n\
echo "📺 VNC Web: http://localhost:6080"\n\
echo "🤖 守护进程: http://localhost:8080"\n\
echo "📚 API文档: http://localhost:8080/docs"\n\
\n\
# 清理函数\n\
cleanup() {\n\
    echo "🔄 正在关闭服务..."\n\
    kill $DAEMON_PID 2>/dev/null || true\n\
    pkill -f "browser_daemon.py" || true\n\
    exit 0\n\
}\n\
\n\
# 捕获退出信号\n\
trap cleanup SIGTERM SIGINT EXIT\n\
\n\
# 保持脚本运行，监控守护进程\n\
while true; do\n\
    if ! kill -0 $DAEMON_PID 2>/dev/null; then\n\
        echo "❌ 浏览器守护进程异常退出，重新启动..."\n\
        cd /home/user/tools\n\
        python3 browser_daemon.py &\n\
        DAEMON_PID=$!\n\
        sleep 5\n\
    fi\n\
    sleep 10\n\
done\n' > /home/user/start-all-services.sh

# 设置权限
RUN chown -R 1000:1000 /home/user && \
    chmod +x /home/user/start-vnc.sh && \
    chmod +x /home/user/start-all-services.sh

# 切换到非root用户
USER 1000
WORKDIR /home/user

# 设置环境变量
ENV PYTHONPATH="/home/user/tools"
ENV PLAYWRIGHT_BROWSERS_PATH=/home/user/.cache/ms-playwright

# 安装Playwright浏览器（用户模式）
RUN playwright install chromium

# 创建Fluxbox配置
RUN echo 'session.screen0.workspaces: 1\n\
session.screen0.toolbar.visible: false\n\
session.screen0.slit.placement: RightBottom\n\
session.screen0.window.focus.model: ClickToFocus' > /home/user/.config/fluxbox/init

# 验证安装
RUN python3 -c "import os; print('✅ E2B环境配置完成')"

# 暴露端口
EXPOSE 5901 6080 8080