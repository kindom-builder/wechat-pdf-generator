#!/usr/bin/env python3
"""
稳定版微信公众号PDF生成器
集成增强版文章抓取，提供最高稳定性
"""

import os
import sys
import json
import hashlib
import datetime
from pathlib import Path
from typing import Dict, Optional, Any
import logging

from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# 导入增强版抓取器
from article_fetcher_enhanced import ArticleFetchManager
from pdf_wechat_fixed import FixedWeChatPDFGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 配置限流
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per day", "20 per hour"],
    storage_uri="memory://",
)

class StablePDFGenerator:
    """稳定版PDF生成器"""
    
    def __init__(self):
        # 配置
        self.data_dir = os.environ.get('DATA_DIR', 'data')
        self.max_file_size = int(os.environ.get('MAX_FILE_SIZE', 50 * 1024 * 1024))
        self.max_files = int(os.environ.get('MAX_FILES', 1000))
        
        # 初始化组件
        self.base_dir = Path(__file__).parent.parent / self.data_dir / "wechat_articles"
        self.setup_directories()
        
        self.fetch_manager = ArticleFetchManager()
        self.pdf_generator = FixedWeChatPDFGenerator()
        
        # 统计
        self.stats = {
            'total_generations': 0,
            'successful_generations': 0,
            'failed_generations': 0,
            'articles_fetched': 0,
            'cache_hits': 0
        }
        
        logger.info(f"稳定版PDF生成器初始化完成 - 数据目录: {self.base_dir}")
    
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
            self.base_dir / "images",
            self.base_dir / "cache"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info("系统目录结构已创建")
    
    def generate_pdf(self, url: str, custom_title: Optional[str] = None) -> Dict:
        """生成PDF（完整流程）"""
        self.stats['total_generations'] += 1
        start_time = datetime.datetime.now()
        
        try:
            logger.info(f"开始处理文章: {url}")
            
            # 1. 检查文件数量限制
            pdf_count = self.get_pdf_count()
            if pdf_count >= self.max_files:
                error_msg = f"已达到最大文件数量限制 ({self.max_files})"
                logger.warning(error_msg)
                return self._create_error_response("文件数量限制", error_msg)
            
            # 2. 抓取文章内容
            logger.info("抓取文章内容...")
            fetch_result = self.fetch_manager.fetch(url, use_cache=True)
            self.stats['articles_fetched'] += 1
            
            if fetch_result.get('from_cache'):
                self.stats['cache_hits'] += 1
            
            # 3. 准备文章数据
            article_data = self._prepare_article_data(fetch_result, url, custom_title)
            
            # 4. 生成PDF
            logger.info("生成PDF文件...")
            pdf_path = self.pdf_generator.generate_pdf(article_data)
            
            if not pdf_path:
                error_msg = "PDF生成失败"
                logger.error(error_msg)
                return self._create_error_response("PDF生成失败", error_msg)
            
            # 5. 检查文件大小
            pdf_path_obj = Path(pdf_path)
            if not pdf_path_obj.exists():
                error_msg = "PDF文件未创建"
                logger.error(error_msg)
                return self._create_error_response("文件创建失败", error_msg)
            
            file_size = pdf_path_obj.stat().st_size
            if file_size > self.max_file_size:
                pdf_path_obj.unlink()
                error_msg = f"文件过大 ({file_size}字节 > {self.max_file_size}字节限制)"
                logger.warning(error_msg)
                return self._create_error_response("文件大小限制", error_msg)
            
            # 6. 保存文章数据
            self._save_article_data(article_data)
            
            # 7. 更新统计
            processing_time = (datetime.datetime.now() - start_time).total_seconds()
            self.stats['successful_generations'] += 1
            
            logger.info(f"PDF生成成功: {pdf_path} ({file_size}字节, {processing_time:.1f}秒)")
            
            # 8. 返回成功结果
            return {
                'success': True,
                'message': 'PDF生成成功',
                'pdf_path': str(pdf_path),
                'file_name': pdf_path_obj.name,
                'file_size': file_size,
                'processing_time': round(processing_time, 2),
                'article_info': {
                    'title': article_data['title'],
                    'author': article_data['author'],
                    'word_count': article_data.get('word_count', 0),
                    'fetched_success': fetch_result['success']
                },
                'fetch_info': {
                    'from_cache': fetch_result.get('from_cache', False),
                    'fetch_time': fetch_result.get('fetch_time', 0),
                    'response_status': fetch_result.get('response_status', 0)
                }
            }
            
        except Exception as e:
            self.stats['failed_generations'] += 1
            logger.error(f"PDF生成过程异常: {e}", exc_info=True)
            return self._create_error_response("处理异常", str(e))
    
    def _prepare_article_data(self, fetch_result: Dict, url: str, custom_title: Optional[str]) -> Dict:
        """准备文章数据"""
        # 使用自定义标题或抓取的标题
        title = custom_title or fetch_result.get('title', '未命名文章')
        
        # 如果抓取失败，使用备用内容
        if not fetch_result['success']:
            content = fetch_result.get('content', '')
            if not content:
                content = self._create_fallback_content(url, fetch_result.get('error', '未知错误'))
        else:
            content = fetch_result.get('content', '')
        
        # 生成文章ID
        article_id = hashlib.md5(f"{url}_{datetime.datetime.now().timestamp()}".encode()).hexdigest()[:8]
        
        return {
            'id': article_id,
            'title': title,
            'author': fetch_result.get('author', '未知作者'),
            'content': content,
            'url': url,
            'publish_date': datetime.datetime.now().isoformat(),
            'save_date': datetime.datetime.now().isoformat(),
            'word_count': len(content),
            'fetched_success': fetch_result['success'],
            'fetch_error': fetch_result.get('error', '')
        }
    
    def _create_fallback_content(self, url: str, error: str) -> str:
        """创建备用内容"""
        return f"""# 文章抓取说明

## 文章链接
{url}

## 抓取状态
⚠️ 自动抓取遇到问题: {error}

## 稳定版解决方案
本系统使用增强版抓取器，已尝试以下优化：

### 1. 智能重试机制
- 自动重试3次
- 指数退避延迟
- 随机请求头

### 2. 多策略解析
- 微信公众号特有结构识别
- 通用文章内容提取
- 智能文本清理

### 3. 缓存优化
- 24小时本地缓存
- 减少重复请求
- 提升响应速度

### 4. 错误恢复
- 优雅降级处理
- 备用内容生成
- 详细错误报告

## 手动处理建议
如果自动抓取持续失败，建议：

1. **检查URL有效性**
2. **验证网络连接**
3. **尝试不同时间段**
4. **使用手动复制功能**

## 系统信息
- 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 系统版本: 稳定版 v1.0
- 错误代码: {hashlib.md5(error.encode()).hexdigest()[:8]}

## 示例内容
这是一个稳定版系统的示例内容，展示PDF生成效果。

**重要提示**：虽然自动抓取失败，但PDF生成功能完全正常。您可以将实际文章内容复制粘贴，系统会生成精美的PDF文档。

### 功能特点
- ✅ 稳定可靠的PDF生成
- ✅ 完美中文排版支持
- ✅ 自动错误恢复机制
- ✅ 详细的处理报告

> 稳定性是系统的核心设计目标。我们持续优化抓取算法，提供最佳用户体验。"""
    
    def _create_error_response(self, error_type: str, error_detail: str) -> Dict:
        """创建错误响应"""
        return {
            'success': False,
            'message': f'PDF生成失败: {error_type}',
            'error': error_detail,
            'error_type': error_type,
            'timestamp': datetime.datetime.now().isoformat()
        }
    
    def _save_article_data(self, article_data: Dict):
        """保存文章数据"""
        try:
            articles_dir = self.base_dir / "articles"
            articles_dir.mkdir(exist_ok=True)
            
            file_path = articles_dir / f"{article_data['id']}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"文章数据保存成功: {file_path}")
        except Exception as e:
            logger.warning(f"保存文章数据失败: {e}")
    
    def get_pdf_count(self) -> int:
        """获取PDF文件数量"""
        pdf_dir = self.base_dir / "pdfs"
        if pdf_dir.exists():
            return len([f for f in pdf_dir.iterdir() if f.is_file() and f.suffix == '.pdf'])
        return 0
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        try:
            pdf_count = self.get_pdf_count()
            pdf_dir = self.base_dir / "pdfs"
            
            # 计算总大小
            total_size = 0
            file_sizes = []
            if pdf_dir.exists():
                for f in pdf_dir.iterdir():
                    if f.is_file() and f.suffix == '.pdf':
                        size = f.stat().st_size
                        total_size += size
                        file_sizes.append(size)
            
            # 获取抓取统计
            fetch_stats = self.fetch_manager.get_stats()
            
            # 合并统计
            all_stats = {
                **self.stats,
                **fetch_stats,
                'pdf_count': pdf_count,
                'total_size': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'avg_file_size': round(sum(file_sizes) / len(file_sizes), 2) if file_sizes else 0,
                'max_files': self.max_files,
                'max_file_size_mb': round(self.max_file_size / (1024 * 1024), 2),
                'system_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'version': '稳定版 1.0',
                'data_dir': str(self.base_dir)
            }
            
            # 计算成功率
            if all_stats['total_generations'] > 0:
                all_stats['generation_success_rate'] = round(
                    (all_stats['successful_generations'] / all_stats['total_generations']) * 100, 1
                )
            else:
                all_stats['generation_success_rate'] = 0
            
            return {
                'success': True,
                'status': all_stats
            }
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {
                'success': False,
                'message': '获取系统状态失败',
                'error': str(e)
            }
    
    def list_pdfs(self, limit: int = 50) -> Dict:
        """列出PDF文件"""
        try:
            pdf_dir = self.base_dir / "pdfs"
            pdf_files = []
            
            if pdf_dir.exists():
                for f in pdf_dir.iterdir():
                    if f.is_file() and f.suffix == '.pdf':
                        stat = f.stat()
                        pdf_files.append({
                            'name': f.name,
                            'size': stat.st_size,
                            'size_mb': round(stat.st_size / (1024 * 1024), 2),
                            'created': datetime.datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                            'modified': datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                            'accessed': datetime.datetime.fromtimestamp(stat.st_atime).strftime('%Y-%m-%d %H:%M:%S')
                        })
            
            # 按修改时间倒序排序
            pdf_files.sort(key=lambda x: x['modified'], reverse=True)
            
            return {
                'success': True,
                'files': pdf_files[:limit],
                'total_count': len(pdf_files),
                'total_size_mb': round(sum(f['size'] for f in pdf_files) / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"列出PDF文件失败: {e}")
            return {
                'success': False,
                'message': '列出文件失败',
                'error': str(e)
            }
    
    def clear_cache(self, older_than_hours: int = 24):
        """清理缓存"""
        self.fetch_manager.clear_cache(older_than_hours)

# 创建实例
generator = StablePDFGenerator()

# HTML模板（简化版，专注于稳定性）
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📄 稳定版微信公众号PDF生成器</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, sans-serif; background: #f5f7fa; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header h1 { color: #2c3e50; margin-bottom: 10px; }
        .header p { color: #7f8c8d; }
        .card { background: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .card h2 { color: #3498db; margin-bottom: 15px; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: 600; color: #2c3e50; }
        .form-control { width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 5px; font-size: 16px; }
        .form-control:focus { outline: none; border-color: #3498db; }
        .btn { background: #3498db; color: white; border: none; padding: 12px 24px; border-radius: 5px; font-size: 16px; cursor: pointer; width: 100%; }
        .btn:hover { background: #2980b9; }
        .btn:disabled { background: #95a5a6; cursor: not-allowed; }
        .loading { text-align: center; padding: 20px; display: none; }
        .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .alert { padding: 15px; border-radius: 5px; margin: 15px 0; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .alert-info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 15px; }
        .stat-item { text-align: center; padding: 15px; background: #f8f9fa; border-radius: 5px; }
        .stat-value { font-size: 24px; font-weight: 700; color: #3498db; }
        .stat-label { font-size: 14px; color: #7f8c8d; margin-top: 5px; }
        .files-list { max-height: 400px; overflow-y: auto; }
        .file-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #eee; }
        .file-item:hover { background: #f8f9fa; }
        .file-info { flex: 1; }
        .file-name { font-weight: 500; margin-bottom: 4px; word-break: break-all; }
        .file-meta { font-size: 14px; color: #7f8c8d; }
        .btn-download { background: #27ae60; color: white; border: none; padding: 6px 12px; border-radius: 3px; text-decoration: none; font-size: 14px; }
        .btn-download:hover { background: #219653; }
        .footer { text-align: center; padding: 20px; color: #7f8c8d; margin-top: 30px; }
        .stability-badge { display: inline-block; background: #27ae60; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px; margin-left: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📄 稳定版微信公众号PDF生成器 <span class="stability-badge">稳定版</span></h1>
            <p>增强抓取稳定性，提供可靠的PDF生成服务</p>
        </div>
        
        <div class="card">
            <h2>📝 生成PDF</h2>
            <div class="form-group">
                <label for="articleUrl">文章URL：</label>
                <input type="url" id="articleUrl" class="form-control" 
                       placeholder="https://mp.weixin.qq.com/s/..." required>
            </div>
            
            <div class="form-group">
                <label for="customTitle">自定义标题（可选）：</label>
                <input type="text" id="customTitle" class="form-control" 
                       placeholder="留空则使用原标题">
            </div>
            
            <button id="generateBtn" class="btn">生成PDF</button>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>正在处理中，请稍候...</p>
            </div>
            
            <div id="generateResult"></div>
        </div>
        
        <div class="card">
            <h2>📊 系统状态</h2>
            <div id="systemStatus">正在加载系统状态...</div>
            
            <h2 style="margin-top: 30px;">📁 文件列表</h2>
            <div id="fileList">正在加载文件列表...</div>
        </div>
        
        <div class="card">
            <h2>🔧 稳定性特性</h2>
            <div class="alert alert-info">
                <strong>增强版抓取系统包含：</strong><br>
                • 智能重试机制（3次自动重试）<br>
                • 多策略内容解析（微信公众号+通用结构）<br>
                • 24小时本地缓存（减少重复请求）<br>
                • 优雅错误恢复（自动生成备用内容）<br>
                • 详细统计监控（成功率、响应时间等）<br>
                • 请求限流保护（防止滥用）
            </div>
        </div>
        
        <footer class="footer">
            <p>© 2026 稳定版微信公众号PDF生成器 | 版本 1.0 | 成功率监控 | 自动缓存</p>
        </footer>
    </div>
    
    <script>
        class StablePDFGeneratorApp {
            constructor() {
                this.apiBase = window.location.origin;
                this.init();
            }
            
            init() {
                this.bindEvents();
                this.loadSystemStatus();
                this.loadFileList();
                
                // 自动刷新（每30秒）
                setInterval(() => {
                    this.loadSystemStatus();
                    this.loadFileList();
                }, 30000);
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
                        this.showError('状态加载失败: ' + data.message, 'systemStatus');
                    }
                } catch (error) {
                    this.showError('状态加载失败: ' + error.message, 'systemStatus');
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
                            <div class="stat-value">${status.success_rate}%</div>
                            <div class="stat-label">抓取成功率</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${status.generation_success_rate || 0}%</div>
                            <div class="stat-label">生成成功率</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${status.cache_rate}%</div>
                            <div class="stat-label">缓存命中率</div>
                        </div>
                    </div>
                    <div style="margin-top: 15px; font-size: 14px; color: #666;">
                        <div>系统时间: ${status.system_time}</div>
                        <div>平均响应: ${status.avg_fetch_time}秒</div>
                        <div>总请求: ${status.total_requests}</div>
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
                        this.showError('文件列表加载失败: ' + data.message, 'fileList');
                    }
                } catch (error) {
                    this.showError('文件列表加载失败: ' + error.message, 'fileList');
                }
            }
            
            updateFileList(files) {
                const filesEl = document.getElementById('fileList');
                
                if (!files || files.length === 0) {
                    filesEl.innerHTML = '<div class="alert alert-info">暂无PDF文件，请先生成一个。</div>';
                    return;
                }
                
                let html = '<div class="files-list">';
                files.forEach(file => {
                    const encodedName = encodeURIComponent(file.name);
                    html += `
                        <div class="file-item">
                            <div class="file-info">
                                <div class="file-name">${file.name}</div>
                                <div class="file-meta">
                                    ${file.size_mb} MB • ${file.created}
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
                    this.showResult('请输入文章URL', 'error');
                    return;
                }
                
                if (!url.startsWith('http')) {
                    this.showResult('URL必须以http或https开头', 'error');
                    return;
                }
                
                // 禁用按钮，显示加载
                const btn = document.getElementById('generateBtn');
                const originalText = btn.textContent;
                btn.disabled = true;
                btn.textContent = '处理中...';
                
                const loadingEl = document.getElementById('loading');
                const resultEl = document.getElementById('generateResult');
                loadingEl.style.display = 'block';
                resultEl.style.display = 'none';
                
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
                    
                    loadingEl.style.display = 'none';
                    resultEl.style.display = 'block';
                    
                    if (data.success) {
                        const fileName = data.file_name;
                        const encodedName = encodeURIComponent(fileName);
                        const sizeMB = (data.file_size / 1024 / 1024).toFixed(2);
                        
                        let infoHtml = `
                            <div class="alert alert-success">
                                <strong>✅ PDF生成成功！</strong><br><br>
                                <strong>文件信息：</strong><br>
                                • 文件名：${fileName}<br>
                                • 文件大小：${sizeMB} MB<br>
                                • 处理时间：${data.processing_time}秒<br>
                        `;
                        
                        if (data.fetch_info) {
                            infoHtml += `
                                • 缓存命中：${data.fetch_info.from_cache ? '是' : '否'}<br>
                                • 抓取时间：${data.fetch_info.fetch_time}秒<br>
                            `;
                        }
                        
                        infoHtml += `
                                <br>
                                <a href="${this.apiBase}/api/download/${encodedName}" 
                                   class="btn-download" 
                                   download="${fileName}"
                                   style="display: inline-block; margin-top: 10px;">
                                    点击下载PDF
                                </a>
                            </div>
                        `;
                        
                        resultEl.innerHTML = infoHtml;
                        
                        // 刷新文件列表和状态
                        this.loadFileList();
                        this.loadSystemStatus();
                        
                        // 清空表单
                        document.getElementById('articleUrl').value = '';
                        document.getElementById('customTitle').value = '';
                    } else {
                        resultEl.innerHTML = `
                            <div class="alert alert-error">
                                <strong>❌ 生成失败：</strong><br>
                                ${data.message}<br>
                                ${data.error ? '错误详情：' + data.error : ''}
                            </div>
                        `;
                    }
                } catch (error) {
                    loadingEl.style.display = 'none';
                    resultEl.style.display = 'block';
                    resultEl.innerHTML = `
                        <div class="alert alert-error">
                            <strong>❌ 请求失败：</strong><br>
                            ${error.message}
                        </div>
                    `;
                } finally {
                    // 恢复按钮
                    btn.disabled = false;
                    btn.textContent = originalText;
                }
            }
            
            showError(message, elementId) {
                const element = document.getElementById(elementId);
                element.innerHTML = `
                    <div class="alert alert-error">
                        ${message}
                    </div>
                `;
            }
            
            showResult(message, type) {
                const resultEl = document.getElementById('generateResult');
                resultEl.innerHTML = `
                    <div class="alert alert-${type}">
                        ${message}
                    </div>
                `;
                resultEl.style.display = 'block';
                resultEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
        
        // 初始化应用
        document.addEventListener('DOMContentLoaded', () => {
            window.app = new StablePDFGeneratorApp();
        });
    </script>
</body>
</html>
'''

# API路由
@app.route('/')
def index():
    """主页"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status', methods=['GET'])
@limiter.limit("10 per minute")
def get_status():
    """获取系统状态"""
    return jsonify(generator.get_system_status())

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
        
        logger.info(f"收到生成请求 - URL: {url}")
        
        if not url:
            return jsonify({
                "success": False,
                "message": "缺少文章URL"
            }), 400
        
        # 处理文章
        result = generator.generate_pdf(url, custom_title)
        
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
        import urllib.parse
        filename = urllib.parse.unquote(filename)
        
        pdf_path = generator.base_dir / "pdfs" / filename
        
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
        limit = request.args.get('limit', 50, type=int)
        result = generator.list_pdfs(limit=limit)
        return jsonify(result)
    except Exception as e:
        logger.error(f"列出文件失败: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "列出文件失败",
            "error": str(e)
        }), 500

@app.route('/api/clear_cache', methods=['POST'])
@limiter.limit("2 per hour")
def clear_cache():
    """清理缓存"""
    try:
        older_than = request.json.get('older_than_hours', 24)
        generator.clear_cache(older_than_hours=older_than)
        
        return jsonify({
            "success": True,
            "message": f"已清理超过{older_than}小时的缓存"
        })
    except Exception as e:
        logger.error(f"清理缓存失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": "清理缓存失败",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # 从环境变量获取配置
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info("🚀 启动稳定版微信公众号PDF生成器...")
    logger.info(f"📁 工作目录: {generator.base_dir}")
    logger.info(f"🌐 服务地址: http://{host}:{port}")
    logger.info(f"⚙️  配置: PORT={port}, DEBUG={debug}, DATA_DIR={generator.data_dir}")
    logger.info(f"📊 限制: 最大文件数={generator.max_files}, 最大文件大小={generator.max_file_size}字节")
    logger.info("💪 稳定性特性: 智能重试 + 多策略解析 + 缓存优化 + 错误恢复")
    
    app.run(host=host, port=port, debug=debug)