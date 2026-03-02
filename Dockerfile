FROM python:3.11-slim

WORKDIR /app

# 安装中文字体
RUN apt-get update && apt-get install -y \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ ./src/

# 创建数据目录
RUN mkdir -p /data

# 设置环境变量
ENV DATA_DIR=/data
ENV PORT=8080

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["python", "src/pdf_generator_web.py"]
