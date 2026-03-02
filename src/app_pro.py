#!/usr/bin/env python3
"""
微信公众号PDF生成器 - 专业版
适合公开部署的Web应用
"""

import os
import sys
import json
import hashlib
import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging

# 导入PDF生成器
from pdf_wechat_fixed import FixedWeChatPDFGenerator
from process_wechat_fixed import WeChatArticleFixer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
           static_folder='../static',
           template_folder='../templates')
CORS(app)

# 配置限流
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

class ProPDFGenerator:
    """专业版PDF生成器"""
    
    def __init__(self):
        # 支持环境变量配置
        self.data_dir = os.environ.get('DATA_DIR', 'data')
        self.max_file_size = int(os.environ.get('MAX_FILE_SIZE', 50 * 1024 * 1024))  # 50MB
        self.max_files = int(os.environ.get('MAX_FILES', 1000))
        
        self.base_dir = Path(__file__).parent.parent / self.data_dir / "wechat_articles"
        self.setup_directories()
        self.article_fixer = WeChatArticleFixer()
        
        logger.info(f"初始化PDF生成器 - 数据目录: {self.base_dir}")
        
    def setup_directories(self):
        """创建目录结构"""
        directories = [
            self.base_dir,
            self.base_dir / "authors",
            self.base_dir / "articles",
            self.base_dir / "pdfs",
            self.base_dir / "database",
            self.base_dir / "logs",
            self.base_dir / "templates",
            self.base_dir / "images"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info("系统目录结构已创建")
    
    def process_article(self, url, custom_title=None):
        """处理文章并生成PDF"""
        try:
            logger.info(f"处理文章请求 - URL: {url}")
            
            # 验证URL格式
            if not url.startswith('http'):
                return {
                    "success": False,
                    "message": "无效的URL格式",
                    "error": "URL必须以http或https开头"
                }
            
            # 检查文件数量限制
            pdf_count = self.get_pdf_count()
            if pdf_count >= self.max_files:
                return {
                    "success": False,
                    "message": "已达到最大文件数量限制",
                    "error": f"最多支持{self.max_files}个文件"
                }
            
            # 使用修复版处理器
            result = self.article_fixer.process_article(url, custom_title)
            
            if result and "pdf_path" in result:
                pdf_path = str(result["pdf_path"])
                file_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
                
                # 检查文件大小限制
                if file_size > self.max_file_size:
                    os.remove(pdf_path)
                    return {
                        "success": False,
                        "message": "生成的文件过大",
                        "error": f"文件大小{file_size}字节超过限制{self.max_file_size}字节"
                    }
                
                return {
                    "success": True,
                    "message": "PDF生成成功",
                    "pdf_path": pdf_path,
                    "file_name": os.path.basename(pdf_path),
                    "file_size": file_size,
                    "article_info": result.get("article_info", {})
                }
            else:
                error_msg = "无法生成PDF文件"
                if result and "error" in result:
                    error_msg = result["error"]
                return {
                    "success": False,
                    "message": "PDF生成失败",
                    "error": error_msg
                }
                
        except Exception as e:
            logger.error(f"处理文章时出错: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "处理文章时出错",
                "error": str(e)
            }
    
    def get_pdf_count(self):
        """获取PDF文件数量"""
        pdf_dir = self.base_dir / "pdfs"
        if pdf_dir.exists():
            return len([f for f in pdf_dir.iterdir() if f.is_file() and f.suffix == '.pdf'])
        return 0
    
    def get_system_status(self):
        """获取系统状态"""
        try:
            pdf_count = self.get_pdf_count()
            pdf_dir = self.base_dir / "pdfs"
            
            # 计算总大小
            total_size = 0
            if pdf_dir.exists():
                for f in pdf_dir.iterdir():
                    if f.is_file() and f.suffix == '.pdf':
                        total_size += f.stat().st_size
            
            return {
                "success": True,
                "status": {
                    "pdf_count": pdf_count,
                    "total_size": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "max_files": self.max_files,
                    "max_file_size_mb": round(self.max_file_size / (1024 * 1024), 2),
                    "system_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "version": "1.0.0"
                }
            }
        except Exception as e:
            logger.error(f"获取系统状态失败: {str(e)}")
            return {
                "success": False,
                "message": "获取系统状态失败",
                "error": str(e)
            }

# 创建后端实例
backend = ProPDFGenerator()

# 创建静态文件和模板目录
static_dir = Path(__file__).parent.parent / "static"
templates_dir = Path(__file__).parent.parent / "templates"
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

# 创建静态文件
css_content = '''
/* 专业版样式 */
:root {
    --primary-color: #4361ee;
    --secondary-color: #3a0ca3;
    --success-color: #4cc9f0;
    --danger-color: #f72585;
    --light-color: #f8f9fa;
    --dark-color: #212529;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    color: var(--dark-color);
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.header {
    background: white;
    border-radius: 20px;
    padding: 40px;
    margin-bottom: 30px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.1);
    text-align: center;
}

.header h1 {
    font-size: 2.5rem;
    color: var(--primary-color);
    margin-bottom: 10px;
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.header p {
    color: #666;
    font-size: 1.1rem;
    max-width: 600px;
    margin: 0 auto;
}

.main-content {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 30px;
    margin-bottom: 30px;
}

@media (max-width: 768px) {
    .main-content {
        grid-template-columns: 1fr;
    }
}

.card {
    background: white;
    border-radius: 15px;
    padding: 30px;
    box-shadow: 0 5px 20px rgba(0,0,0,0.08);
}

.card h2 {
    color: var(--primary-color);
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 2px solid #f0f0f0;
}

.form-group {
    margin-bottom: 20px;
}

.form-group label {
    display: block;
    margin-bottom: 8px;
    font-weight: 600;
    color: #444;
}

.form-control {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    font-size: 16px;
    transition: all 0.3s;
}

.form-control:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.1);
}

.btn {
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    color: white;
    border: none;
    padding: 14px 28px;
    border-radius: 10px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
    width: 100%;
}

.btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 20px rgba(67, 97, 238, 0.3);
}

.btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.loading {
    text-align: center;
    padding: 20px;
}

.spinner {
    border: 4px solid #f3f3f3;
    border-top: 4px solid var(--primary-color);
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
    margin: 0 auto 10px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.alert {
    padding: 15px;
    border-radius: 10px;
    margin: 15px 0;
}

.alert-success {
    background: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}

.alert-error {
    background: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}

.files-list {
    max-height: 400px;
    overflow-y: auto;
}

.file-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    border-bottom: 1px solid #eee;
    transition: background 0.3s;
}

.file-item:hover {
    background: #f8f9fa;
}

.file-info {
    flex: 1;
}

.file-name {
    font-weight: 500;
    margin-bottom: 4px;
    word-break: break-all;
}

.file-meta {
    font-size: 14px;
    color: #666;
}

.btn-download {
    background: var(--success-color);
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    text-decoration: none;
    font-size: 14px;
    transition: background 0.3s;
}

.btn-download:hover {
    background: #3ab8d9;
    color: white;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 15px;
    margin-top: 20px;
}

.stat-item {
    text-align: center;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 10px;
}

.stat-value {
    font-size: 24px;
    font-weight: 700;
    color: var(--primary-color);
}

.stat-label {
    font-size: 14px;
    color: #666;
    margin-top: 5px;
}

.footer {
    text-align: center;
    padding: 20px;
    color: white;
    margin-top: 30px;
}

.footer a {
    color: white;
    text-decoration: none;
}

.footer a:hover {
    text-decoration: underline;
}
'''

js_content = '''
// 专业版JavaScript
class PDFGeneratorApp {
    constructor() {
        this.apiBase = window.location.origin;
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadSystemStatus();
        this.loadFileList();
    }
    
    bindEvents() {
        document.getElementById('generateBtn').addEventListener('click', () => this.generatePDF());
    }
    
    async loadSystemStatus() {
        try {
            const response = await fetch(`${this.apiBase}/api/status`);
            const data = await response.json();
            
            if (data.success) {
                this.updateStatusDisplay(data.status);
            } else {
                this.showError('状态加载失败: ' + data.message);
            }
        } catch (error) {
            this.showError('状态加载失败: ' + error.message);
        }
    }
    
    updateStatusDisplay(status) {
        const statusEl = document.getElementById('systemStatus');
        statusEl.innerHTML = `
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">${status.pdf_count}</div>
                    <div class="stat-label">PDF文件</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${status.total_size_mb} MB</div>
                    <div class="stat-label">总大小</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${status.max_files}</div>
                    <div class="stat-label">最大文件数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">v${status.version}</div>
                    <div class="stat-label">版本</div>
                </div>
            </div>
            <div style="margin-top: 15px; color: #666; font-size: 14px;">
                系统时间: ${status.system_time}
            </div>
        `;
    }
    
    async loadFileList() {
        try {
            const response = await fetch(`${this.apiBase}/api/list`);
            const data = await response.json();
            
            if (data.success) {
                this.updateFileList(data.files);
            } else {
                this.showError('文件列表加载失败: ' + data.message);
            }
        } catch (error) {
            this.showError('文件列表加载失败: ' + error.message);
        }
    }
    
    updateFileList(files) {
        const filesEl = document.getElementById('fileList');
        
        if (!files || files.length === 0) {
            filesEl.innerHTML = '<div class="alert">暂无PDF文件，请先生成一个。</div>';
            return;
        }
        
        let html = '<div class="files-list">';
        files.forEach(file => {
            const sizeMB = (file.size / 1024 / 1024).toFixed(2);
            const encodedName = encodeURIComponent(file.name);
            html += `
                <div class="file-item">
                    <div class="file-info">
                        <div class="file-name">${file.name}</div>
                        <div class="file-meta">
                            ${sizeMB} MB • 创建于 ${file.created}
                        </div>
                    </div>
                    <a href="${this.apiBase}/api/download/${encodedName}" 
                       class="btn-download" 
                       download="${file.name}">
                        下载
                    </a>
                </div>
            `;
        });
        html += '</div>';
        filesEl.innerHTML = html;
    }
    
    async generatePDF() {
        const url = document.getElementById('articleUrl').value.trim();
        const title = document.getElementById('customTitle').value.trim();
        
        if (!url) {
            this.showError('请输入文章URL');
            return;
        }
        
        // 验证URL格式
        if (!url.startsWith('http')) {
            this.showError('URL必须以http或https开头');
            return;
        }
        
        // 禁用按钮，显示加载
        const btn = document.getElementById('generateBtn');
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = '处理中...';
        
        const resultEl = document.getElementById('generateResult');
        resultEl.innerHTML = '<div class="loading"><div class="spinner"></div><p>正在处理，请稍候...</p></div>';
        resultEl.className = 'alert';
        
        try {
            const response = await fetch(`${this.apiBase}/api/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: url,
                    custom_title: title || null
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                const fileName = data.file_name || data.pdf_path.split('/').pop();
                const encodedName = encodeURIComponent(fileName);
                const sizeMB = data.file_size ? (data.file_size / 1024 / 1024).toFixed(2) : '未知';
                
                resultEl.innerHTML = `
                    <div class="alert-success">
                        <strong>✅ PDF生成成功！</strong><br><br>
                        <strong>文件信息：</strong><br>
                        • 文件名：${fileName}<br>
                        • 文件大小：${sizeMB} MB<br><br>
                        <a href="${this.apiBase}/api/download/${encodedName}" 
                           class="btn-download" 
                           download="${fileName}"
                           style="display: inline-block; margin-top: 10px;">
                            点击下载PDF
                        </a>
                    </div>
                `;
                resultEl.className = 'alert alert-success';
                
                // 刷新文件列表和状态
                this.loadFileList();
                this.loadSystemStatus();
                
                // 清空表单
                document.getElementById('articleUrl').value = '';
                document.getElementById('customTitle').value = '';
            } else {
                resultEl.innerHTML = `
                    <div class="alert-error">
                        <strong>❌ 生成失败：</strong><br>
                        ${data.message}<br>
                        ${data.error ? '错误详情：' + data.error : ''}
                    </div>
                `;
                resultEl.className = 'alert alert-error';
            }
        } catch (error) {
            resultEl.innerHTML = `
                <div class="alert-error">
                    <strong>❌ 请求失败：</strong><br>
                    ${error.message}
                </div>
            `;
            resultEl.className = 'alert alert-error';
        } finally {
            // 恢复按钮
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
    
    showError(message) {
        const resultEl = document.getElementById('generateResult');
        resultEl.innerHTML = `
            <div class="alert-error">
                ${message}
            </div>
        `;
        resultEl.className = 'alert alert-error';
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new PDFGeneratorApp();
    
    // 自动刷新文件列表（每60秒）
    setInterval(() => window.app.loadFileList(), 60000);
});
'''

# 创建HTML模板
html_template = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📄 微信公众号PDF生成器 - 专业版</title>
    <link rel="stylesheet" href="/static/style.css">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📄</text></svg>">
    <meta name="description" content="将微信公众号文章转换为精美的PDF文档">
    <meta name="keywords" content="微信公众号,PDF,转换,文章,阅读">
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>📄 微信公众号PDF生成器</h1>
            <p>将微信公众号文章转换为精美的PDF文档，支持中文文件名，完美模仿原版排版</p>
        </header>
        
        <main class="main-content">
            <div class="card">
                <h2>📝 生成新PDF</h2>
                <div class="form-group">
                    <label for="articleUrl">文章URL：</label>
                    <input type="url" id="articleUrl" class="form-control" 
                           placeholder="https://mp.weixin.qq.com/s/..." 
                           required>
                </div>
                
                <div class="form-group">
                    <label for="customTitle">自定义标题（可选）：</label>
                    <input type="text" id="customTitle" class="form-control" 
                           placeholder="留空则使用原标题">
                </div>
                
                <button id="generateBtn" class="btn">生成PDF</button>
                
                <div id="generateResult"></div>
            </div>
            
            <div class="card">
                <h2>📊 系统状态</h2>
                <div id="systemStatus">正在加载系统状态...</div>
                
                <h2 style="margin-top: 30px;">📁 文件列表</h2>
                <div id="fileList">正在加载文件列表...</div>
            </div>
        </main>
        
        <footer class="footer">
            <p>© 2026 微信公众号PDF生成器 | 
                <a href="https://github.com/yourusername/wechat-pdf-generator" target="_blank">GitHub</a> | 
                <a href="/api/status">API状态</a>
            </p>
            <p style="font-size: 14px; opacity: 0.8; margin-top: 10px;">
                版本 1.0.0 | 支持中文文件名 | 自动刷新
            </p>
        </footer>
    </div>
    
    <script src="/static/app.js"></script>
</body>
</html>
'''

# 写入静态文件
(static_dir / "style.css").write_text(css_content)
(static_dir / "app.js").write_text(js_content)
(templates_dir / "index.html").write_text(html_template)

# API路由
@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
@limiter.limit("10 per minute")
def get_status():
    """获取系统状态"""
    return jsonify(backend.get_system_status())

@app.route('/api/generate', methods=['POST'])
@limiter.limit("5 per minute")
def generate_pdf():
    """生成PDF"""
    try:
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "message": "请求体为空"
            }), 400
            
        url = data.get('url')
        custom_title = data.get('custom_title')
        
        logger.info(f"收到生成请求 - URL: {url}, 标题: {custom_title}")
        
        if not url:
            return jsonify({
                "success": False,
                "message": "缺少文章URL"
            }), 400
        
        # 处理文章
        result = backend.process_article(url, custom_title)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"API处理异常: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "处理文章失败",
            "error": str(e)
        }), 500

@app.route('/api/download/<filename>', methods=['GET'])
@limiter.limit("20 per minute")
def download_pdf(filename):
    """下载PDF文件"""
    try:
        # 解码文件名
        import urllib.parse
        filename = urllib.parse.unquote(filename)
        
        pdf_path = backend.base_dir / "pdfs" / filename
        
        logger.info(f"下载请求 - 文件名: {filename}")
        
        if pdf_path.exists():
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        else:
            logger.warning(f"文件不存在: {pdf_path}")
            return jsonify({
                "success": False,
                "message": f"文件不存在: {filename}"
            }), 404
    except Exception as e:
        logger.error(f"下载文件失败: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "下载文件失败",
            "error": str(e)
        }), 500

@app.route('/api/list', methods=['GET'])
@limiter.limit("10 per minute")
def list_pdfs():
    """列出所有PDF文件"""
    try:
        pdf_dir = backend.base_dir / "pdfs"
        pdf_files = []
        if pdf_dir.exists():
            for f in pdf_dir.iterdir():
                if f.is_file() and f.suffix == '.pdf':
                    stat = f.stat()
                    pdf_files.append({
                        "name": f.name,
                        "size": stat.st_size,
                        "created": datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                        "modified": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })
        
        # 按修改时间倒序排序
        pdf_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            "success": True,
            "files": pdf_files[:50]  # 限制返回50个文件
        })
    except Exception as e:
        logger.error(f"列出文件失败: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "列出文件失败",
            "error": str(e)
        }), 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    return send_from_directory(static_dir, filename)

if __name__ == '__main__':
    # 从环境变量获取配置
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info("🚀 启动微信公众号PDF生成器专业版...")
    logger.info(f"📁 工作目录: {backend.base_dir}")
    logger.info(f"🌐 服务地址: http://{host}:{port}")
    logger.info(f"⚙️  配置: PORT={port}, DEBUG={debug}, DATA_DIR={backend.data_dir}")
    logger.info(f"📊 限制: 最大文件数={backend.max_files}, 最大文件大小={backend.max_file_size}字节")
    
    app.run(host=host, port=port, debug=debug)