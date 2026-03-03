#!/usr/bin/env python3
"""
简化版PDF生成器服务
用于演示和测试格式增强功能
"""

import os
import sys
import json
import re
import hashlib
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import threading

class SimplePDFHandler(BaseHTTPRequestHandler):
    """简化版HTTP处理器"""

    # 避免BaseHTTPRequestHandler默认反向DNS解析导致卡顿
    def address_string(self):
        return self.client_address[0]

    def log_message(self, format, *args):
        return
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urllib.parse.urlparse(self.path)
        
        if parsed_path.path == '/':
            # 返回前端界面
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self.get_frontend_html().encode('utf-8'))
            
        elif parsed_path.path == '/api/status':
            # 返回服务状态
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'status': 'running',
                'version': '1.0.0',
                'features': ['文章抓取', 'PDF生成', '格式增强（加粗/斜体）'],
                'timestamp': datetime.datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            
        elif parsed_path.path == '/api/demo':
            # 返回演示数据
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = self.get_demo_data()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404 Not Found')
    
    def do_POST(self):
        """处理POST请求"""
        if self.path == '/api/generate':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(post_data)
                url = data.get('url', '')
                
                # 模拟处理
                result = self.process_wechat_article(url)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {'error': str(e), 'success': False}
                self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def get_frontend_html(self):
        """获取前端HTML界面"""
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>微信公众号PDF生成器 - 格式增强演示</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            color: white;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .header p {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            margin-bottom: 30px;
        }
        
        .card-title {
            font-size: 1.5rem;
            margin-bottom: 20px;
            color: #2d3748;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .card-title i {
            color: #667eea;
        }
        
        .input-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #4a5568;
        }
        
        input[type="text"] {
            width: 100%;
            padding: 15px;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 10px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .demo-btn {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            margin-left: 10px;
        }
        
        .result-section {
            margin-top: 30px;
            display: none;
        }
        
        .result-section.active {
            display: block;
            animation: fadeIn 0.5s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .result-card {
            background: #f7fafc;
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #667eea;
        }
        
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 15px;
        }
        
        .status-success {
            background: #c6f6d5;
            color: #22543d;
        }
        
        .format-demo {
            background: #f0f9ff;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            border: 1px solid #bee3f8;
        }
        
        .format-demo h4 {
            color: #2b6cb0;
            margin-bottom: 15px;
        }
        
        .format-example {
            margin: 10px 0;
            padding: 10px;
            background: white;
            border-radius: 5px;
            border-left: 3px solid #4299e1;
        }
        
        .bold-text {
            font-weight: bold;
            color: #2d3748;
        }
        
        .italic-text {
            font-style: italic;
            color: #4a5568;
        }
        
        .bold-italic-text {
            font-weight: bold;
            font-style: italic;
            color: #2d3748;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        
        .loading.active {
            display: block;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        
        .feature {
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        
        .feature:hover {
            transform: translateY(-5px);
        }
        
        .feature-icon {
            font-size: 2rem;
            margin-bottom: 15px;
            color: #667eea;
        }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            color: white;
            opacity: 0.8;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 2rem;
            }
            
            .card {
                padding: 20px;
            }
            
            .btn {
                width: 100%;
                margin-bottom: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📄 微信公众号PDF生成器</h1>
            <p>格式增强版 - 支持加粗和斜体显示</p>
        </div>
        
        <div class="card">
            <h2 class="card-title">
                <i>🔗</i> 文章转换
            </h2>
            
            <div class="input-group">
                <label for="url">微信公众号文章链接：</label>
                <input type="text" id="url" placeholder="例如：https://mp.weixin.qq.com/s/..." value="https://mp.weixin.qq.com/s/Tk7d9KKMe6aJ2QIZbJL0Vw">
            </div>
            
            <button class="btn" onclick="generatePDF()">
                <i>⚡</i> 生成PDF
            </button>
            
            <button class="btn demo-btn" onclick="showDemo()">
                <i>🎯</i> 查看演示
            </button>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>正在处理文章，请稍候...</p>
            </div>
            
            <div class="result-section" id="resultSection">
                <div class="result-card">
                    <div class="status-badge status-success">✅ 处理成功</div>
                    <h3 id="resultTitle"></h3>
                    <p id="resultContent"></p>
                    
                    <div class="format-demo">
                        <h4>🎨 格式增强演示：</h4>
                        <div class="format-example">
                            <p>这是<span class="bold-text">加粗的文字</span>，用于强调重要内容。</p>
                        </div>
                        <div class="format-example">
                            <p>这是<span class="italic-text">斜体的文字</span>，用于表示引用或特殊术语。</p>
                        </div>
                        <div class="format-example">
                            <p>这是<span class="bold-italic-text">加粗且斜体的文字</span>，用于特别强调。</p>
                        </div>
                    </div>
                    
                    <div style="margin-top: 20px;">
                        <button class="btn" onclick="downloadPDF()">
                            <i>📥</i> 下载PDF
                        </button>
                        <button class="btn demo-btn" onclick="viewDetails()">
                            <i>🔍</i> 查看详情
                        </button>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="features">
            <div class="feature">
                <div class="feature-icon">🔤</div>
                <h3>格式增强</h3>
                <p>支持加粗、斜体、组合格式显示</p>
            </div>
            <div class="feature">
                <div class="feature-icon">🎨</div>
                <h3>精美排版</h3>
                <p>模仿微信公众号样式，优化阅读体验</p>
            </div>
            <div class="feature">
                <div class="feature-icon">⚡</div>
                <h3>快速处理</h3>
                <p>智能抓取，高效生成PDF文件</p>
            </div>
            <div class="feature">
                <div class="feature-icon">🔧</div>
                <h3>智能解析</h3>
                <p>自动提取文章内容和格式信息</p>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2026 小邹AI助手 - 微信公众号PDF生成器 | 格式增强版 v1.0.0</p>
            <p>服务状态: <span id="serviceStatus">检查中...</span></p>
        </div>
    </div>
    
    <script>
        // 检查服务状态
        async function checkServiceStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                document.getElementById('serviceStatus').innerHTML = 
                    `<span style="color: #4CAF50;">✅ 运行中</span> | 版本: ${data.version}`;
            } catch (error) {
                document.getElementById('serviceStatus').innerHTML = 
                    '<span style="color: #f44336;">❌ 服务异常</span>';
            }
        }
        
        // 生成PDF
        async function generatePDF() {
            const url = document.getElementById('url').value;
            if (!url) {
                alert('请输入微信公众号文章链接');
                return;
            }
            
            // 显示加载中
            document.getElementById('loading').classList.add('active');
            document.getElementById('resultSection').classList.remove('active');
            
            try {
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url: url })
                });
                
                const data = await response.json();
                
                // 隐藏加载中
                document.getElementById('loading').classList.remove('active');
                
                if (data.success) {
                    // 显示结果
                    document.getElementById('resultTitle').textContent = data.title || '文章处理成功';
                    document.getElementById('resultContent').textContent = 
                        `作者: ${data.author || '未知'} | 文章ID: ${data.id || 'N/A'}`;
                    document.getElementById('resultSection').classList.add('active');
                    
                    // 存储结果数据
                    window.lastResult = data;
                } else {
                    alert('处理失败: ' + (data.error || '未知错误'));
                }
            } catch (error) {
                document.getElementById('loading').classList.remove('active');
                alert('请求失败: ' + error.message);
            }
        }
        
        // 显示演示
        function showDemo() {
            document.getElementById('resultTitle').textContent = '演示：为什么财富自由后，反而更忙了？';
            document.getElementById('resultContent').textContent = '作者: 蔡垒磊 | 文章ID: demo-20260303';
            document.getElementById('resultSection').classList.add('active');
            
            // 滚动到结果区域
            document.getElementById('resultSection').scrollIntoView({ behavior: 'smooth' });
        }
        
        // 下载PDF（演示）
        function downloadPDF() {
            alert('在完整版本中，这里会下载生成的PDF文件。\n\n当前为演示模式，展示了格式增强功能。');
        }
        
        // 查看详情
        function viewDetails() {
            alert('格式增强功能详情：\n\n' +
                  '✅ 加粗文字：<strong>文本</strong> 或 <b>文本</b>\n' +
                  '✅ 斜体文字：<em>文本</em> 或 <i>文本</i>\n' +
                  '✅ 组合格式：<strong><em>文本</em></strong>\n' +
                  '✅ 嵌套格式：加粗内部的斜体等\n' +
                  '✅ 整段加粗：强调段落特殊处理\n\n' +
                  '所有格式都会在PDF中正确显示！');
        }
        
        // 页面加载时检查服务状态
        window.onload = function() {
            checkServiceStatus();
            
            // 每30秒检查一次服务状态
            setInterval(checkServiceStatus, 30000);
        };
    </script>
</body>
</html>
        """
    
    def get_demo_data(self):
        """获取演示数据"""
        return {
            'success': True,
            'title': '演示：为什么财富自由后，反而更忙了？',
            'author': '蔡垒磊',
            'id': 'demo-20260303',
            'features': ['格式增强', '加粗显示', '斜体显示', '组合格式']
        }
    
    def process_wechat_article(self, url):
        """处理微信公众号文章（模拟）"""
        # 生成文章ID
        article_id = hashlib.md5(url.encode()).hexdigest()[:8]
        
        # 模拟文章数据
        return {
            'success': True,
            'title': '为什么财富自由后，反而更忙了？',
            'author': '蔡垒磊',
            'id': article_id,
            'url': url,
            'content_preview': '文章内容已成功抓取并处理...',
            'formats_detected': ['加粗', '斜体', '组合格式'],
            'timestamp': datetime.datetime.now().isoformat(),
            'message': '格式增强功能已应用：加粗和斜体将在PDF中正确显示'
        }
    
    def log_message(self, format, *args):
        """重写日志方法，减少输出"""
        pass