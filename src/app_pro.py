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
import shutil
import re

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
        self.fetch_browser_fallback_default = os.environ.get('FETCH_BROWSER_FALLBACK_DEFAULT', 'false').lower() == 'true'
        self.fetch_remote_fallback_default = os.environ.get('FETCH_REMOTE_FALLBACK_DEFAULT', 'true').lower() == 'true'
        
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

    def _prefs_path(self):
        cfg_dir = self.base_dir / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        return cfg_dir / "save_prefs.json"

    def load_save_prefs(self):
        p = self._prefs_path()
        if p.exists():
            try:
                return json.loads(p.read_text(encoding='utf-8'))
            except Exception:
                pass
        return {
            "save_mode": "default",  # default|author|custom
            "default_save_path": "",
            "author_base_path": "",
            "author_paths": {},
            "remember": False,
            "use_browser_print": False
        }

    def save_save_prefs(self, prefs: dict):
        p = self._prefs_path()
        p.write_text(json.dumps(prefs, ensure_ascii=False, indent=2), encoding='utf-8')

    def _sanitize_name(self, s: str):
        s = (s or '').strip()
        s = re.sub(r'[\\/:*?"<>|]+', '_', s)
        return s or '未知作者'

    def get_author_paths(self):
        prefs = self.load_save_prefs()
        return prefs.get('author_paths', {}) or {}

    def set_author_path(self, author: str, path: str):
        author = self._sanitize_name(author)
        path = str(Path(path).expanduser())
        prefs = self.load_save_prefs()
        prefs.setdefault('author_paths', {})
        prefs['author_paths'][author] = path
        self.save_save_prefs(prefs)
        return prefs['author_paths']

    def delete_author_path(self, author: str):
        author = self._sanitize_name(author)
        prefs = self.load_save_prefs()
        m = prefs.get('author_paths', {}) or {}
        if author in m:
            del m[author]
        prefs['author_paths'] = m
        self.save_save_prefs(prefs)
        return m

    def _apply_save_destination(self, src_pdf_path: str, author: str, save_mode: str, save_path: str = ""):
        """把生成好的PDF复制到目标目录，返回最终路径"""
        src = Path(src_pdf_path)
        if not src.exists():
            return src_pdf_path

        if save_mode == 'default':
            return str(src)

        prefs = self.load_save_prefs()
        author_clean = self._sanitize_name(author)

        target_dir = None
        if save_mode == 'custom':
            target_dir = Path(save_path).expanduser() if save_path else None
        elif save_mode == 'author':
            # 优先作者专属路径，其次作者基路径/本次save_path
            author_paths = prefs.get('author_paths', {}) or {}
            ap = author_paths.get(author_clean)
            if ap:
                target_dir = Path(ap).expanduser()
            else:
                base = save_path or prefs.get('author_base_path') or prefs.get('default_save_path')
                if base:
                    target_dir = Path(base).expanduser() / author_clean

        if not target_dir:
            return str(src)

        target_dir.mkdir(parents=True, exist_ok=True)
        dst = target_dir / src.name
        shutil.copy2(src, dst)
        return str(dst)

    def process_article(self, url, custom_title=None, use_browser_fallback=None, use_remote_fallback=None, save_mode='default', save_path='', remember_path=False, use_browser_print=False):
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
            
            if use_browser_fallback is None:
                use_browser_fallback = self.fetch_browser_fallback_default
            if use_remote_fallback is None:
                use_remote_fallback = self.fetch_remote_fallback_default

            # 记住用户保存偏好
            if remember_path:
                prefs = self.load_save_prefs()
                prefs['save_mode'] = save_mode or prefs.get('save_mode', 'default')
                prefs['remember'] = True
                prefs['use_browser_print'] = bool(use_browser_print)
                if save_mode == 'custom' and save_path:
                    prefs['default_save_path'] = save_path
                if save_mode == 'author' and save_path:
                    prefs['author_base_path'] = save_path
                self.save_save_prefs(prefs)

            # 可选：直接用浏览器“打印为PDF”
            if use_browser_print:
                target_tmp = self.base_dir / 'pdfs' / f"browser_print_{int(datetime.datetime.now().timestamp())}.pdf"
                print_ret = self.article_fixer.print_article_to_pdf_via_browser(url, str(target_tmp))
                if not print_ret.get('success'):
                    return {
                        "success": False,
                        "message": "浏览器打印PDF失败",
                        "error": print_ret.get('error', '未知错误')
                    }
                result = {
                    'pdf_path': print_ret['pdf_path'],
                    'author': print_ret.get('author', '未知作者'),
                    'title': custom_title or print_ret.get('title', '未命名文章'),
                    'word_count': 0,
                    'is_real_content': True
                }
                # 更新作者统计
                try:
                    self.article_fixer.update_author_stats(result['author'])
                except Exception:
                    pass
            else:
                # 使用修复版处理器
                result = self.article_fixer.process_article(
                    url,
                    custom_title,
                    use_browser_fallback=use_browser_fallback,
                    use_remote_fallback=use_remote_fallback
                )
            
            if result and "pdf_path" in result:
                pdf_path = str(result["pdf_path"])
                author = result.get('author', '未知作者')

                # 应用保存路径策略（可复制到作者目录/自定义目录）
                final_pdf_path = self._apply_save_destination(
                    pdf_path,
                    author,
                    save_mode=save_mode,
                    save_path=save_path
                )
                serve_pdf_path = pdf_path  # Web预览/下载仍走系统目录文件

                # 若记忆开启且是作者模式，保存作者映射
                if remember_path and save_mode == 'author' and save_path:
                    prefs = self.load_save_prefs()
                    author_key = self._sanitize_name(author)
                    prefs.setdefault('author_paths', {})
                    prefs['author_paths'][author_key] = str((Path(save_path).expanduser() / author_key))
                    self.save_save_prefs(prefs)

                file_size = os.path.getsize(final_pdf_path) if os.path.exists(final_pdf_path) else 0

                # 检查文件大小限制（以最终文件为准）
                if file_size > self.max_file_size:
                    try:
                        os.remove(final_pdf_path)
                    except Exception:
                        pass
                    return {
                        "success": False,
                        "message": "生成的文件过大",
                        "error": f"文件大小{file_size}字节超过限制{self.max_file_size}字节"
                    }

                return {
                    "success": True,
                    "message": "PDF生成成功",
                    "pdf_path": final_pdf_path,
                    "file_name": os.path.basename(final_pdf_path),
                    "file_size": file_size,
                    "author": author,
                    "save_mode": save_mode,
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
    
    def preview_article(self, url, use_browser_fallback=None, use_remote_fallback=None):
        """仅抓取并返回预览，不生成PDF"""
        try:
            if not url or not url.startswith('http'):
                return {"success": False, "message": "无效的URL格式"}

            if use_browser_fallback is None:
                use_browser_fallback = self.fetch_browser_fallback_default
            if use_remote_fallback is None:
                use_remote_fallback = self.fetch_remote_fallback_default

            fetched = self.article_fixer.fetch_article(
                url,
                use_browser_fallback=use_browser_fallback,
                use_remote_fallback=use_remote_fallback
            )
            if not fetched.get('success'):
                return {
                    "success": False,
                    "message": "抓取失败",
                    "error": fetched.get('error', '未知错误')
                }

            content = fetched.get('content', '') or ''
            preview_text = content[:1200]
            return {
                "success": True,
                "title": fetched.get('title', ''),
                "author": fetched.get('author', ''),
                "word_count": fetched.get('word_count', len(content)),
                "content_preview": preview_text,
            }
        except Exception as e:
            logger.error(f"预览文章失败: {str(e)}", exc_info=True)
            return {"success": False, "message": "预览失败", "error": str(e)}

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
        this.loadPrefs();
        this.loadAuthorPaths();
        this.loadSystemStatus();
        this.loadFileList();
    }
    
    async loadPrefs() {
        try {
            const res = await fetch(`${this.apiBase}/api/save-prefs`);
            const data = await res.json();
            if (data.success) {
                const p = data.prefs || {};
                document.getElementById('saveMode').value = p.save_mode || 'default';
                document.getElementById('savePath').value = p.default_save_path || p.author_base_path || '';
                document.getElementById('rememberPath').checked = !!p.remember;
                document.getElementById('useBrowserPrint').checked = !!p.use_browser_print;
            }
        } catch (_) {}
    }

    bindEvents() {
        document.getElementById('generateBtn').addEventListener('click', () => this.generatePDF());
        document.getElementById('previewBtn').addEventListener('click', () => this.previewArticle());
        document.getElementById('saveAuthorPathBtn').addEventListener('click', () => this.saveAuthorPath());
        const pickBtn = document.getElementById('pickSavePathBtn');
        if (pickBtn) pickBtn.addEventListener('click', () => this.chooseSaveFolder());
    }

    async chooseSaveFolder() {
        if (!window.showDirectoryPicker) {
            this.showError('当前浏览器不支持目录选择器，请手动输入保存路径。');
            return;
        }
        try {
            const handle = await window.showDirectoryPicker({ mode: 'readwrite' });
            // 浏览器安全限制下无法直接拿到绝对系统路径，使用name作为提示并让用户确认输入
            const savePathEl = document.getElementById('savePath');
            if (savePathEl && !savePathEl.value) {
                savePathEl.placeholder = `已选择目录: ${handle.name}（请粘贴本机绝对路径）`;
            }
            const resultEl = document.getElementById('generateResult');
            resultEl.innerHTML = `<div class="alert">已选择目录：${handle.name}。出于浏览器安全限制，请在“保存路径”中粘贴本机绝对路径后保存。</div>`;
            resultEl.className = 'alert';
        } catch (e) {
            // 用户取消不提示错误
        }
    }

    async loadAuthorPaths() {
        try {
            const res = await fetch(`${this.apiBase}/api/author-paths`);
            const data = await res.json();
            if (data.success) this.renderAuthorPaths(data.author_paths || {});
        } catch (_) {}
    }

    renderAuthorPaths(authorPaths) {
        const el = document.getElementById('authorPathList');
        const entries = Object.entries(authorPaths || {});
        if (!entries.length) {
            el.innerHTML = '<div class="alert">暂无作者路径映射</div>';
            return;
        }
        el.innerHTML = entries.map(([author, path]) => `
            <div class="file-item">
                <div class="file-info">
                    <div class="file-name">${author}</div>
                    <div class="file-meta">${path}</div>
                </div>
                <button class="btn" style="background:#ef4444;" onclick="window.app.deleteAuthorPath('${author.replace(/'/g, "\\'")}')">删除</button>
            </div>
        `).join('');
    }

    async saveAuthorPath() {
        const author = document.getElementById('authorName').value.trim();
        const path = document.getElementById('authorPath').value.trim();
        if (!author || !path) {
            this.showError('请输入作者名和路径');
            return;
        }
        try {
            const res = await fetch(`${this.apiBase}/api/author-paths`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ author, path })
            });
            const data = await res.json();
            if (data.success) {
                document.getElementById('authorName').value = '';
                this.loadAuthorPaths();
            } else {
                this.showError('保存作者路径失败: ' + (data.message || '未知错误'));
            }
        } catch (e) {
            this.showError('保存作者路径失败: ' + e.message);
        }
    }

    async deleteAuthorPath(author) {
        try {
            const res = await fetch(`${this.apiBase}/api/author-paths`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ author })
            });
            const data = await res.json();
            if (data.success) this.loadAuthorPaths();
        } catch (_) {}
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
                    <div style="display:flex; gap:8px;">
                        <a href="${this.apiBase}/api/view/${encodedName}" 
                           class="btn-download"
                           target="_blank"
                           rel="noopener noreferrer">
                            预览
                        </a>
                        <a href="${this.apiBase}/api/download/${encodedName}" 
                           class="btn-download" 
                           download="${file.name}">
                            下载
                        </a>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        filesEl.innerHTML = html;
    }
    
    async previewArticle() {
        const url = document.getElementById('articleUrl').value.trim();
        if (!url) {
            this.showError('请输入文章URL');
            return;
        }
        if (!url.startsWith('http')) {
            this.showError('URL必须以http或https开头');
            return;
        }

        const useBrowserFallback = document.getElementById('browserFallback').checked;
        const useRemoteFallback = document.getElementById('remoteFallback').checked;

        const resultEl = document.getElementById('generateResult');
        resultEl.innerHTML = '<div class="loading"><div class="spinner"></div><p>正在抓取预览，请稍候...</p></div>';
        resultEl.className = 'alert';

        try {
            const response = await fetch(`${this.apiBase}/api/preview`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    url, 
                    use_browser_fallback: useBrowserFallback,
                    use_remote_fallback: useRemoteFallback
                })
            });
            const data = await response.json();

            if (data.success) {
                const preview = (data.content_preview || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                resultEl.innerHTML = `
                    <div class="alert-success">
                        <strong>👀 预览成功</strong><br><br>
                        <strong>标题：</strong>${data.title || '未知'}<br>
                        <strong>作者：</strong>${data.author || '未知'}<br>
                        <strong>字数：</strong>${data.word_count || 0}<br><br>
                        <div style="background:#f7f7f7;padding:12px;border-radius:8px;white-space:pre-wrap;line-height:1.6;max-height:260px;overflow:auto;">
${preview}
                        </div>
                    </div>
                `;
                resultEl.className = 'alert alert-success';
            } else {
                this.showError('预览失败: ' + (data.message || '未知错误'));
            }
        } catch (error) {
            this.showError('预览请求失败: ' + error.message);
        }
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
        const useBrowserFallback = document.getElementById('browserFallback').checked;
        const useRemoteFallback = document.getElementById('remoteFallback').checked;
        const saveMode = document.getElementById('saveMode').value;
        const savePath = document.getElementById('savePath').value.trim();
        const rememberPath = document.getElementById('rememberPath').checked;
        const useBrowserPrint = document.getElementById('useBrowserPrint').checked;

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
                    custom_title: title || null,
                    use_browser_fallback: useBrowserFallback,
                    use_remote_fallback: useRemoteFallback,
                    save_mode: saveMode,
                    save_path: savePath,
                    remember_path: rememberPath,
                    use_browser_print: useBrowserPrint
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
                        • 文件大小：${sizeMB} MB<br>
                        • 保存路径：${data.pdf_path || '默认目录'}<br><br>
                        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">
                            <a href="${this.apiBase}/api/view/${encodedName}" 
                               class="btn-download"
                               target="_blank"
                               rel="noopener noreferrer">
                                打开预览
                            </a>
                            <a href="${this.apiBase}/api/download/${encodedName}" 
                               class="btn-download" 
                               download="${fileName}">
                                下载PDF
                            </a>
                        </div>
                        <iframe 
                           src="${this.apiBase}/api/view/${encodedName}#view=FitH" 
                           style="width:100%;height:520px;border:1px solid #e5e7eb;border-radius:8px;background:#fff;"
                           title="PDF预览">
                        </iframe>
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

                <div class="form-group" style="display:flex;align-items:center;gap:8px;">
                    <label for="saveMode" style="min-width:88px;">保存策略：</label>
                    <select id="saveMode" class="form-control" style="max-width:260px;">
                        <option value="default">默认目录（系统pdfs）</option>
                        <option value="author">按作者分文件夹</option>
                        <option value="custom">固定到自定义目录</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="savePath">保存路径（可选）：</label>
                    <div style="display:flex; gap:8px; flex-wrap:wrap;">
                        <input type="text" id="savePath" class="form-control" style="min-width:320px;" placeholder="如：/home/kindom/Documents/WeChatPDF">
                        <button id="pickSavePathBtn" class="btn" type="button" style="background:#4b5563;">选择文件夹</button>
                    </div>
                </div>
                <div class="form-group" style="display:flex;align-items:center;gap:8px;">
                    <input type="checkbox" id="rememberPath" checked>
                    <label for="rememberPath" style="margin:0;">记住以上保存设置（下次不再询问）</label>
                </div>

                <div class="form-group" style="display:flex;align-items:center;gap:8px;">
                    <input type="checkbox" id="useBrowserPrint">
                    <label for="useBrowserPrint" style="margin:0;">使用浏览器打印生成PDF（接近手工打印效果）</label>
                </div>
                <div class="form-group" style="display:flex;align-items:center;gap:8px;">
                    <input type="checkbox" id="remoteFallback" checked>
                    <label for="remoteFallback" style="margin:0;">启用远程兜底抓取（无sudo，推荐）</label>
                </div>
                <div class="form-group" style="display:flex;align-items:center;gap:8px;">
                    <input type="checkbox" id="browserFallback">
                    <label for="browserFallback" style="margin:0;">启用浏览器兜底抓取（需本机依赖）</label>
                </div>

                <div class="card" style="background:#fafafa;margin:10px 0;">
                    <h3 style="margin-bottom:8px;">👤 作者路径映射</h3>
                    <div class="form-group" style="display:flex;gap:8px;flex-wrap:wrap;">
                        <input type="text" id="authorName" class="form-control" style="max-width:220px;" placeholder="作者名（如 蔡垒磊）">
                        <input type="text" id="authorPath" class="form-control" placeholder="该作者固定保存目录">
                        <button id="saveAuthorPathBtn" class="btn" style="background:#2563eb;">保存映射</button>
                    </div>
                    <div id="authorPathList"></div>
                </div>
                
                <div style="display:flex; gap:10px; flex-wrap:wrap;">
                    <button id="previewBtn" class="btn" style="background:#6b7280;">先预览</button>
                    <button id="generateBtn" class="btn">生成PDF</button>
                </div>
                
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

@app.route('/api/save-prefs', methods=['GET'])
@limiter.limit("20 per minute")
def get_save_prefs():
    try:
        return jsonify({"success": True, "prefs": backend.load_save_prefs()})
    except Exception as e:
        return jsonify({"success": False, "message": "读取保存偏好失败", "error": str(e)}), 500

@app.route('/api/save-prefs', methods=['POST'])
@limiter.limit("10 per minute")
def set_save_prefs():
    try:
        data = request.json or {}
        prefs = backend.load_save_prefs()
        for k in ['save_mode', 'default_save_path', 'author_base_path', 'remember', 'use_browser_print']:
            if k in data:
                prefs[k] = data[k]
        backend.save_save_prefs(prefs)
        return jsonify({"success": True, "prefs": prefs})
    except Exception as e:
        return jsonify({"success": False, "message": "写入保存偏好失败", "error": str(e)}), 500

@app.route('/api/author-paths', methods=['GET'])
@limiter.limit("20 per minute")
def get_author_paths():
    try:
        return jsonify({"success": True, "author_paths": backend.get_author_paths()})
    except Exception as e:
        return jsonify({"success": False, "message": "读取作者路径失败", "error": str(e)}), 500

@app.route('/api/author-paths', methods=['POST'])
@limiter.limit("10 per minute")
def set_author_path():
    try:
        data = request.json or {}
        author = data.get('author', '').strip()
        path = data.get('path', '').strip()
        if not author or not path:
            return jsonify({"success": False, "message": "author/path 不能为空"}), 400
        m = backend.set_author_path(author, path)
        return jsonify({"success": True, "author_paths": m})
    except Exception as e:
        return jsonify({"success": False, "message": "保存作者路径失败", "error": str(e)}), 500

@app.route('/api/author-paths', methods=['DELETE'])
@limiter.limit("10 per minute")
def delete_author_path():
    try:
        data = request.json or {}
        author = data.get('author', '').strip()
        if not author:
            return jsonify({"success": False, "message": "author 不能为空"}), 400
        m = backend.delete_author_path(author)
        return jsonify({"success": True, "author_paths": m})
    except Exception as e:
        return jsonify({"success": False, "message": "删除作者路径失败", "error": str(e)}), 500

@app.route('/api/preview', methods=['POST'])
@limiter.limit("10 per minute")
def preview_article():
    """预览文章内容（不生成PDF）"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "请求体为空"}), 400
        url = data.get('url')
        use_browser_fallback = data.get('use_browser_fallback')
        use_remote_fallback = data.get('use_remote_fallback')
        result = backend.preview_article(
            url,
            use_browser_fallback=use_browser_fallback,
            use_remote_fallback=use_remote_fallback
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"预览API异常: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "预览失败", "error": str(e)}), 500

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
        use_browser_fallback = data.get('use_browser_fallback')
        use_remote_fallback = data.get('use_remote_fallback')
        save_mode = data.get('save_mode', 'default')
        save_path = data.get('save_path', '')
        remember_path = data.get('remember_path', False)
        use_browser_print = data.get('use_browser_print', False)
        
        logger.info(f"收到生成请求 - URL: {url}, 标题: {custom_title}, 浏览器兜底: {use_browser_fallback}, 远程兜底: {use_remote_fallback}, 保存策略: {save_mode}, 浏览器打印: {use_browser_print}")
        
        if not url:
            return jsonify({
                "success": False,
                "message": "缺少文章URL"
            }), 400
        
        # 处理文章
        result = backend.process_article(
            url,
            custom_title,
            use_browser_fallback=use_browser_fallback,
            use_remote_fallback=use_remote_fallback,
            save_mode=save_mode,
            save_path=save_path,
            remember_path=remember_path,
            use_browser_print=use_browser_print
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"API处理异常: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "处理文章失败",
            "error": str(e)
        }), 500

@app.route('/api/view/<filename>', methods=['GET'])
@limiter.limit("30 per minute")
def view_pdf(filename):
    """在线预览PDF（浏览器内打开）"""
    try:
        import urllib.parse
        filename = urllib.parse.unquote(filename)
        pdf_path = backend.base_dir / "pdfs" / filename

        if pdf_path.exists():
            return send_file(
                pdf_path,
                as_attachment=False,
                mimetype='application/pdf'
            )
        else:
            return jsonify({"success": False, "message": f"文件不存在: {filename}"}), 404
    except Exception as e:
        logger.error(f"预览文件失败: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "预览文件失败", "error": str(e)}), 500

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