# 🚀 部署指南

本文档提供微信公众号PDF生成器的多种部署方式。

## 📋 部署选项

### 1. 🖥️ 本地部署（开发/测试）
### 2. 🐳 Docker部署（推荐）
### 3. ☁️ 云服务部署
### 4. 🖥️ VPS部署

## 1. 🖥️ 本地部署

### 环境要求
- Python 3.8+
- Git
- 支持中文字体的系统

### 步骤

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/wechat-pdf-generator.git
cd wechat-pdf-generator

# 2. 使用专业版启动脚本
./start_pro.sh

# 或者手动启动
python src/app_pro.py
```

### 配置环境变量
```bash
# 设置端口
export PORT=8080

# 设置数据目录
export DATA_DIR="/path/to/data"

# 设置文件限制
export MAX_FILES=500
export MAX_FILE_SIZE=104857600  # 100MB

# 启用调试模式
export DEBUG=true

# 然后启动
python src/app_pro.py
```

## 2. 🐳 Docker部署（推荐）

### 使用Docker Compose（最简单）

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/wechat-pdf-generator.git
cd wechat-pdf-generator

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 停止服务
docker-compose down
```

### 使用Docker直接运行

```bash
# 1. 构建镜像
docker build -t wechat-pdf-generator .

# 2. 运行容器
docker run -d \
  --name pdf-generator \
  -p 5000:8080 \
  -v pdf_data:/data \
  -e PORT=8080 \
  -e MAX_FILES=1000 \
  wechat-pdf-generator

# 3. 查看运行状态
docker logs -f pdf-generator
```

### Docker Compose配置示例

```yaml
version: '3.8'

services:
  pdf-generator:
    build: .
    ports:
      - "80:8080"  # 映射到80端口
    volumes:
      - pdf_data:/data
    environment:
      - PORT=8080
      - DATA_DIR=/data
      - MAX_FILES=2000
      - MAX_FILE_SIZE=104857600  # 100MB
      - DEBUG=false
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/status"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  pdf_data:
```

## 3. ☁️ 云服务部署

### Railway.app

1. **连接GitHub仓库**
2. **自动部署**：Railway会自动检测并部署
3. **环境变量**：在Railway控制台设置
4. **访问域名**：Railway提供免费域名

### Heroku

```bash
# 1. 安装Heroku CLI
# 2. 登录
heroku login

# 3. 创建应用
heroku create your-app-name

# 4. 设置环境变量
heroku config:set PORT=5000
heroku config:set DATA_DIR=/app/data
heroku config:set DEBUG=false

# 5. 部署
git push heroku main

# 6. 查看日志
heroku logs --tail
```

### 需要添加的Heroku文件

**Procfile**
```
web: python src/app_pro.py
```

**runtime.txt**
```
python-3.11.0
```

## 4. 🖥️ VPS部署（Ubuntu/Debian）

### 使用Systemd服务

```bash
# 1. 安装依赖
sudo apt update
sudo apt install -y python3-pip python3-venv git nginx

# 2. 克隆仓库
cd /opt
sudo git clone https://github.com/yourusername/wechat-pdf-generator.git
sudo chown -R $USER:$USER wechat-pdf-generator
cd wechat-pdf-generator

# 3. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. 创建Systemd服务
sudo tee /etc/systemd/system/pdf-generator.service << EOF
[Unit]
Description=WeChat PDF Generator
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/wechat-pdf-generator
Environment="PATH=/opt/wechat-pdf-generator/venv/bin"
Environment="PORT=5000"
Environment="DATA_DIR=/opt/wechat-pdf-generator/data"
Environment="MAX_FILES=1000"
ExecStart=/opt/wechat-pdf-generator/venv/bin/python src/app_pro.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 5. 启动服务
sudo systemctl daemon-reload
sudo systemctl enable pdf-generator
sudo systemctl start pdf-generator
sudo systemctl status pdf-generator

# 6. 配置Nginx反向代理
sudo tee /etc/nginx/sites-available/pdf-generator << EOF
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# 7. 启用站点
sudo ln -s /etc/nginx/sites-available/pdf-generator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 使用PM2（Node.js进程管理）

```bash
# 1. 安装Node.js和PM2
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2

# 2. 创建PM2配置文件
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [{
    name: 'pdf-generator',
    script: 'src/app_pro.py',
    interpreter: 'venv/bin/python',
    cwd: '/opt/wechat-pdf-generator',
    env: {
      PORT: 5000,
      DATA_DIR: 'data',
      MAX_FILES: 1000,
      DEBUG: false
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    log_date_format: 'YYYY-MM-DD HH:mm:ss'
  }]
}
EOF

# 3. 启动应用
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

## 🔧 高级配置

### 数据库持久化

```bash
# 使用外部数据库目录
export DATA_DIR="/mnt/data/wechat-pdf"

# 确保目录存在并有正确权限
mkdir -p /mnt/data/wechat-pdf
chmod 755 /mnt/data/wechat-pdf
```

### SSL证书（HTTPS）

```nginx
# Nginx SSL配置
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:5000;
        # ... 其他代理设置
    }
}

# 使用Certbot获取免费证书
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 监控和日志

```bash
# 查看应用日志
journalctl -u pdf-generator -f

# 查看Nginx访问日志
tail -f /var/log/nginx/access.log

# 查看错误日志
tail -f /var/log/nginx/error.log
```

## 📊 性能优化

### 调整限制
```bash
# 增加最大文件数
export MAX_FILES=5000

# 增加最大文件大小（单位：字节）
export MAX_FILE_SIZE=209715200  # 200MB

# 调整Flask配置
export FLASK_THREADS=4
export FLASK_WORKERS=2
```

### 使用Gunicorn（生产环境）

```bash
# 安装Gunicorn
pip install gunicorn

# 创建Gunicorn配置文件
cat > gunicorn_config.py << EOF
bind = "0.0.0.0:5000"
workers = 4
threads = 2
worker_class = "sync"
timeout = 120
keepalive = 5
EOF

# 使用Gunicorn启动
gunicorn "src.app_pro:app" -c gunicorn_config.py
```

## 🔒 安全建议

1. **使用HTTPS**：始终启用SSL
2. **设置防火墙**：只开放必要端口
3. **定期备份**：备份data目录
4. **监控日志**：定期检查访问日志
5. **更新依赖**：定期更新Python包
6. **使用强密码**：如果添加认证功能

## 🚨 故障排除

### 常见问题

1. **端口被占用**
```bash
# 查看占用端口的进程
sudo lsof -i :5000

# 杀死进程
sudo kill -9 <PID>
```

2. **权限问题**
```bash
# 修复数据目录权限
sudo chown -R $USER:$USER /opt/wechat-pdf-generator/data
sudo chmod 755 /opt/wechat-pdf-generator/data
```

3. **内存不足**
```bash
# 查看内存使用
free -h

# 调整限制
export MAX_FILES=500
export MAX_FILE_SIZE=52428800  # 50MB
```

4. **字体问题**
```bash
# 安装中文字体（Ubuntu/Debian）
sudo apt install -y fonts-wqy-zenhei fonts-wqy-microhei

# 检查字体
fc-list | grep -i chinese
```

### 获取帮助

1. 查看日志：`journalctl -u pdf-generator -f`
2. 检查状态：`systemctl status pdf-generator`
3. 重启服务：`systemctl restart pdf-generator`
4. 查看文档：README.md
5. 提交Issue：GitHub Issues

## 📈 扩展功能

### 添加用户认证
```python
# 使用Flask-Login添加登录功能
from flask_login import LoginManager, UserMixin, login_required

login_manager = LoginManager()
login_manager.init_app(app)
```

### 添加邮件通知
```python
# 使用Flask-Mail发送通知
from flask_mail import Mail, Message

mail = Mail(app)
```

### 添加API密钥验证
```python
# 验证API密钥
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key and api_key == os.environ.get('API_KEY'):
            return f(*args, **kwargs)
        return jsonify({'error': 'Invalid API key'}), 401
    return decorated
```

## 🎯 总结

选择最适合你需求的部署方式：
- **开发测试**：本地部署
- **快速上线**：Docker Compose
- **生产环境**：VPS + Systemd + Nginx
- **无服务器**：Railway/Heroku

记得定期备份数据和更新应用！