#!/usr/bin/env python3
"""
微信公众号PDF生成器 - 完整Web版本
修复下载功能问题
"""

import os
import sys
import json
import hashlib
import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS

# 导入PDF生成器
from pdf_wechat_fixed import FixedWeChatPDFGenerator
from process_wechat_fixed import WeChatArticleFixer

app = Flask(__name__)
CORS(app)

class PDFGeneratorBackend:
    """PDF生成器后端"""
    
    def __init__(self):
        # 支持环境变量配置数据目录
        data_dir = os.environ.get('DATA_DIR', 'data')
        self.base_dir = Path(__file__).parent.parent / data_dir / "wechat_articles"
        self.setup_directories()
        self.article_fixer = WeChatArticleFixer()
        
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
        
        print("📁 系统目录结构已创建")
    
    def process_article(self, url, custom_title=None):
        """处理文章并生成PDF"""
        try:
            print(f"🔧 处理文章: {url}")
            
            # 使用修复版处理器
            result = self.article_fixer.process_article(url, custom_title)
            
            if result and "pdf_path" in result:
                # 确保返回字符串路径
                pdf_path = str(result["pdf_path"])
                return {
                    "success": True,
                    "message": "PDF生成成功",
                    "pdf_path": pdf_path,
                    "file_name": os.path.basename(pdf_path),
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
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ 处理文章时出错: {str(e)}")
            return {
                "success": False,
                "message": "处理文章时出错",
                "error": str(e)
            }
    
    def get_system_status(self):
        """获取系统状态"""
        try:
            # 检查PDF目录
            pdf_dir = self.base_dir / "pdfs"
            pdf_files = []
            if pdf_dir.exists():
                pdf_files = [f.name for f in pdf_dir.iterdir() if f.is_file() and f.suffix == '.pdf']
            
            return {
                "success": True,
                "status": {
                    "pdf_count": len(pdf_files),
                    "pdf_files": pdf_files[:10],
                    "system_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "base_dir": str(self.base_dir)
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": "获取系统状态失败",
                "error": str(e)
            }

# 创建后端实例
backend = PDFGeneratorBackend()

# HTML模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📄 微信公众号PDF生成器</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 16px;
        }
        
        .content {
            padding: 30px;
        }
        
        .section {
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        
        .section h2 {
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        
        .form-group input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 28px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
            width: 100%;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .result {
            margin-top: 20px;
            padding: 20px;
            border-radius: 10px;
            display: none;
        }
        
        .result.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .result.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .loading {
            text-align: center;
            margin: 20px 0;
            display: none;
        }
        
        .loading-spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
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
        
        .files-list {
            margin-top: 20px;
        }
        
        .file-item {
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.3s;
        }
        
        .file-item:hover {
            background: #f0f7ff;
        }
        
        .file-item:last-child {
            border-bottom: none;
        }
        
        .file-info {
            flex: 1;
        }
        
        .file-name {
            font-weight: 500;
            color: #333;
            margin-bottom: 4px;
            word-break: break-all;
        }
        
        .file-meta {
            color: #666;
            font-size: 14px;
        }
        
        .download-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            transition: background 0.3s;
        }
        
        .download-btn:hover {
            background: #5a67d8;
            text-decoration: none;
            color: white;
        }
        
        .status-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .status-item {
            background: white;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .status-label {
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }
        
        .status-value {
            font-size: 18px;
            font-weight: 600;
            color: #333;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #666;
        }
        
        .empty-state i {
            font-size: 48px;
            margin-bottom: 15px;
            opacity: 0.5;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📄 微信公众号PDF生成器</h1>
            <p>将微信公众号文章转换为精美的PDF文档</p>
        </div>
        
        <div class="content">
            <!-- 生成PDF表单 -->
            <div class="section">
                <h2>📝 生成新PDF</h2>
                <div class="form-group">
                    <label for="url">文章URL：</label>
                    <input type="url" id="url" placeholder="https://mp.weixin.qq.com/s/..." required>
                </div>
                
                <div class="form-group">
                    <label for="title">自定义标题（可选）：</label>
                    <input type="text" id="title" placeholder="留空则使用原标题">
                </div>
                
                <button class="btn" onclick="generatePDF()">生成PDF</button>
                
                <div class="loading" id="loading">
                    <div class="loading-spinner"></div>
                    <p>正在处理中，请稍候...</p>
                </div>
                
                <div class="result" id="result"></div>
            </div>
            
            <!-- 系统状态 -->
            <div class="section">
                <h2>📊 系统状态</h2>
                <div id="status">正在加载...</div>
            </div>
            
            <!-- PDF文件列表 -->
            <div class="section">
                <h2>📁 已生成的PDF文件</h2>
                <div id="files">正在加载...</div>
            </div>
        </div>
    </div>
    
    <script>
        // 页面加载时获取状态和文件列表
        document.addEventListener('DOMContentLoaded', function() {
            updateStatus();
            listFiles();
        });
        
        // 更新系统状态
        async function updateStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                if (data.success) {
                    const status = data.status;
                    document.getElementById('status').innerHTML = `
                        <div class="status-info">
                            <div class="status-item">
                                <div class="status-label">系统时间</div>
                                <div class="status-value">${status.system_time}</div>
                            </div>
                            <div class="status-item">
                                <div class="status-label">PDF文件数</div>
                                <div class="status-value">${status.pdf_count}</div>
                            </div>
                            <div class="status-item">
                                <div class="status-label">工作目录</div>
                                <div class="status-value" style="font-size: 14px;">${status.base_dir.split('/').pop()}</div>
                            </div>
                        </div>
                    `;
                } else {
                    document.getElementById('status').innerHTML = 
                        '<div class="result error">获取状态失败：' + data.message + '</div>';
                }
            } catch (error) {
                document.getElementById('status').innerHTML = 
                    '<div class="result error">获取状态失败：' + error + '</div>';
            }
        }
        
        // 列出PDF文件
        async function listFiles() {
            try {
                const response = await fetch('/api/list');
                const data = await response.json();
                
                if (data.success) {
                    if (data.files && data.files.length > 0) {
                        let filesHtml = '<div class="files-list">';
                        data.files.forEach(file => {
                            const sizeMB = (file.size / 1024 / 1024).toFixed(2);
                            const fileName = encodeURIComponent(file.name);
                            filesHtml += `
                                <div class="file-item">
                                    <div class="file-info">
                                        <div class="file-name">${file.name}</div>
                                        <div class="file-meta">${sizeMB} MB • 创建于 ${file.created}</div>
                                    </div>
                                    <a href="/api/download/${fileName}" class="download-btn" download>下载</a>
                                </div>
                            `;
                        });
                        filesHtml += '</div>';
                        document.getElementById('files').innerHTML = filesHtml;
                    } else {
                        document.getElementById('files').innerHTML = 
                            '<div class="empty-state">📭 暂无PDF文件</div>';
                    }
                } else {
                    document.getElementById('files').innerHTML = 
                        '<div class="result error">获取文件列表失败：' + data.message + '</div>';
                }
            } catch (error) {
                document.getElementById('files').innerHTML = 
                    '<div class="result error">获取文件列表失败：' + error + '</div>';
            }
        }
        
        // 生成PDF
        async function generatePDF() {
            const url = document.getElementById('url').value;
            const title = document.getElementById('title').value;
            
            if (!url) {
                showResult('请输入文章URL', 'error');
                return;
            }
            
            // 显示加载动画
            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').style.display = 'none';
            
            try {
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        url: url,
                        custom_title: title || null
                    })
                });
                
                const data = await response.json();
                
                document.getElementById('loading').style.display = 'none';
                
                if (data.success) {
                    const fileName = data.file_name || data.pdf_path.split('/').pop();
                    showResult(`
                        <strong>✅ PDF生成成功！</strong><br><br>
                        <strong>文件信息：</strong><br>
                        • 文件名：${fileName}<br>
                        • 保存路径：${data.pdf_path}<br><br>
                        <a href="/api/download/${encodeURIComponent(fileName)}" class="download-btn" download style="display: inline-block; margin-top: 10px;">
                            点击下载
                        </a>
                    `, 'success');
                    
                    // 刷新文件列表
                    listFiles();
                    updateStatus();
                } else {
                    showResult(`<strong>❌ 生成失败：</strong><br>${data.message}`, 'error');
                }
            } catch (error) {
                document.getElementById('loading').style.display = 'none';
                showResult(`<strong>❌ 请求失败：</strong><br>${error}`, 'error');
            }
        }
        
        // 显示结果
        function showResult(message, type) {
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = message;
            resultDiv.className = 'result ' + type;
            resultDiv.style.display = 'block';
            
            // 滚动到结果位置
            resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        
        // 自动刷新文件列表（每30秒）
        setInterval(listFiles, 30000);
    </script>
</body>
</html>
'''

# API路由
@app.route('/')
def index():
    """主页 - 返回完整的Web界面"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取系统状态"""
    return jsonify(backend.get_system_status())

@app.route('/api/generate', methods=['POST'])
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
        
        print(f"📨 收到生成请求 - URL: {url}, 标题: {custom_title}")
        
        if not url:
            return jsonify({
                "success": False,
                "message": "缺少文章URL"
            }), 400
        
        # 处理文章
        result = backend.process_article(url, custom_title)
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"🔥 API处理异常: {str(e)}")
        return jsonify({
            "success": False,
            "message": "处理文章失败",
            "error": str(e)
        }), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_pdf(filename):
    """下载PDF文件"""
    try:
        # 解码文件名（处理中文）
        filename = filename.encode('utf-8').decode('utf-8')
        pdf_path = backend.base_dir / "pdfs" / filename
        
        print(f"📥 下载请求: {filename}")
        print(f"📁 文件路径: {pdf_path}")
        
        if pdf_path.exists():
            # 设置正确的文件名（包含中文）
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        else:
            print(f"❌ 文件不存在: {pdf_path}")
            return jsonify({
                "success": False,
                "message": f"文件不存在: {filename}"
            }), 404
    except Exception as e:
        print(f"🔥 下载文件失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": "下载文件失败",
            "error": str(e)
        }), 500

@app.route('/api/list', methods=['GET'])
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
            "files": pdf_files
        })
    except Exception as e:
        print(f"🔥 列出文件失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": "列出文件失败",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # 从环境变量获取端口，默认5000
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    print("🚀 启动微信公众号PDF生成器Web版...")
    print("📁 工作目录:", backend.base_dir)
    print("🌐 服务地址: http://localhost:{}".format(port))
    print("📄 功能说明:")
    print("  GET  /              - 完整Web界面")
    print("  GET  /api/status    - 系统状态")
    print("  POST /api/generate  - 生成PDF")
    print("  GET  /api/list      - 列出PDF文件")
    print("  GET  /api/download/<filename> - 下载PDF")
    print("\n🛑 按 Ctrl+C 停止服务")
    print("💡 提示: 下载功能已修复，支持中文文件名")
    print("⚙️  配置: PORT={}, DEBUG={}, DATA_DIR={}".format(
        port, debug, os.environ.get('DATA_DIR', 'data')
    ))
    
    app.run(host='0.0.0.0', port=port, debug=debug)
