#!/usr/bin/env python3
"""
修复版微信公众号文章处理器
解决段落分隔和排版问题
"""

import os
import sys
import json
import hashlib
import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import re

# 导入修复版PDF生成器
from pdf_wechat_fixed import FixedWeChatPDFGenerator

class WeChatArticleFixer:
    """修复版微信公众号文章处理器"""
    
    def __init__(self):
        # 支持环境变量配置数据目录
        data_dir = os.environ.get('DATA_DIR', 'data')
        self.base_dir = Path(__file__).parent.parent / data_dir / "wechat_articles"
        self.setup_directories()
        
        self.pdf_generator = FixedWeChatPDFGenerator()
        
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
    
    def fetch_article(self, url, use_browser_fallback=False, use_remote_fallback=False):
        """抓取文章内容并正确格式化（增强成功率：重试/多UA/URL规范化）"""
        print(f"🌐 抓取文章: {url}")
        print(f"   浏览器兜底: {'开启' if use_browser_fallback else '关闭'}")
        print(f"   远程兜底: {'开启' if use_remote_fallback else '关闭'}")

        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

        def normalize_url(raw_url: str):
            raw_url = (raw_url or '').strip().replace('&amp;', '&')
            if not raw_url.startswith('http'):
                raw_url = 'https://' + raw_url.lstrip('/')

            u = urlparse(raw_url)
            # 只处理微信域名
            if 'mp.weixin.qq.com' not in (u.netloc or ''):
                return [raw_url]

            # 尽量保留关键参数，减少无关参数干扰
            q = parse_qs(u.query, keep_blank_values=True)
            keep_keys = ['__biz', 'mid', 'idx', 'sn', 'chksm', 'scene', 'srcid']
            clean_q = {k: v for k, v in q.items() if k in keep_keys and v}
            query = urlencode(clean_q, doseq=True)

            canonical = urlunparse((u.scheme or 'https', u.netloc, u.path, '', query, ''))
            # 候选URL：原始 + 规范化（去fragment）
            no_frag = urlunparse((u.scheme or 'https', u.netloc, u.path, '', u.query, ''))
            return list(dict.fromkeys([raw_url, no_frag, canonical]))

        url_candidates = normalize_url(url)

        request_profiles = [
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://mp.weixin.qq.com/',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            },
            {
                # 手机UA有时更容易拿到正文
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://mp.weixin.qq.com/',
            },
        ]

        # 记录最后一次错误，便于前端展示
        last_error = None

        for candidate in url_candidates:
            for headers in request_profiles:
                try:
                    response = requests.get(candidate, headers=headers, timeout=(8, 20), allow_redirects=True)
                    response.raise_for_status()

                    # 编码兜底
                    if not response.encoding:
                        response.encoding = response.apparent_encoding or 'utf-8'

                    html_text = response.text
                    soup = BeautifulSoup(html_text, 'html.parser')

                    # 常见被拦截页面特征
                    text_sample = soup.get_text(' ', strip=True)[:1200]
                    blocked_markers = ['环境异常', '访问过于频繁', '请在微信客户端打开链接', '该内容因违规无法查看']
                    if any(m in text_sample for m in blocked_markers):
                        last_error = f'微信侧限制访问（{candidate}）'
                        continue

                    # 提取信息
                    title = self._extract_title(soup)
                    author = self._extract_author(soup)
                    content = self._extract_and_format_content(soup)

                    if content and len(content) > 100:
                        return {
                            'success': True,
                            'title': title or '未获取到标题',
                            'author': author or '未知作者',
                            'content': content,
                            'raw_html': str(soup),
                            'source_url': candidate,
                        }

                    # 内容过短，也算失败并继续尝试下一个配置
                    last_error = f'内容提取不足（len={len(content) if content else 0}）'

                except Exception as e:
                    last_error = str(e)
                    continue

        # requests路径失败后，先走远程兜底（无sudo）
        if use_remote_fallback:
            remote_result = self._fetch_article_via_remote(url)
            if remote_result.get('success'):
                return remote_result
            last_error = f"{last_error or 'requests失败'}; 远程兜底失败: {remote_result.get('error', '未知错误')}"

        # 再按开关决定是否启用浏览器兜底
        if use_browser_fallback:
            browser_result = self._fetch_article_via_browser(url)
            if browser_result.get('success'):
                return browser_result
            last_error = f"{last_error or 'requests失败'}; 浏览器兜底失败: {browser_result.get('error', '未知错误')}"

        print(f"❌ 抓取失败: {last_error}")
        return {'success': False, 'error': last_error or '未知错误'}
    
    def _fetch_article_via_remote(self, url):
        """远程渲染兜底（无sudo）：默认使用 r.jina.ai 可读代理"""
        try:
            from urllib.parse import quote
            # 可通过环境变量覆盖
            remote_prefix = os.environ.get('REMOTE_FETCH_PREFIX', 'https://r.jina.ai/http://')
            target = url
            if target.startswith('https://'):
                target = target[len('https://'):]
            elif target.startswith('http://'):
                target = target[len('http://'):]
            remote_url = remote_prefix + target

            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'text/plain,text/markdown,*/*'
            }
            r = requests.get(remote_url, headers=headers, timeout=(8, 25))
            r.raise_for_status()
            text = r.text.strip()
            if len(text) < 120:
                return {'success': False, 'error': f'远程返回内容过短(len={len(text)})'}

            # 从可读文本里猜标题
            title = None
            for line in text.splitlines()[:20]:
                s = line.strip('# ').strip()
                if len(s) >= 6 and 'http' not in s.lower():
                    title = s
                    break

            # 直接作为正文（markdown风格）
            return {
                'success': True,
                'title': title or '未获取到标题',
                'author': '未知作者',
                'content': text,
                'raw_html': '',
                'source_url': url,
                'fetched_by': 'remote_fallback'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _fetch_article_via_browser(self, url):
        """浏览器兜底抓取（Playwright，可选依赖）"""
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            return {'success': False, 'error': f'Playwright不可用: {e}'}

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    locale='zh-CN'
                )
                page = context.new_page()
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(1500)
                html = page.content()
                browser.close()

            soup = BeautifulSoup(html, 'html.parser')
            title = self._extract_title(soup)
            author = self._extract_author(soup)
            content = self._extract_and_format_content(soup)
            if content and len(content) > 100:
                return {
                    'success': True,
                    'title': title or '未获取到标题',
                    'author': author or '未知作者',
                    'content': content,
                    'raw_html': html,
                    'source_url': url,
                    'fetched_by': 'browser_fallback'
                }
            return {'success': False, 'error': f'浏览器抓取内容不足(len={len(content) if content else 0})'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def print_article_to_pdf_via_browser(self, url, output_path):
        """使用浏览器打印（page.pdf）直接生成PDF"""
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            return {'success': False, 'error': f'Playwright不可用: {e}'}

        try:
            output_path = str(output_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
                context = browser.new_context(locale='zh-CN')
                page = context.new_page()
                page.goto(url, wait_until='domcontentloaded', timeout=45000)
                page.wait_for_timeout(2000)

                # 尝试提取标题/作者
                title = page.title() or '未命名文章'
                author = '未知作者'
                for sel in ['#js_name', '.account_nickname_inner', '.profile_nickname', '.rich_media_meta_text']:
                    try:
                        t = page.locator(sel).first.inner_text(timeout=800)
                        if t and t.strip():
                            author = t.strip()
                            break
                    except Exception:
                        pass

                page.pdf(
                    path=output_path,
                    format='A4',
                    print_background=True,
                    margin={'top': '15mm', 'right': '12mm', 'bottom': '15mm', 'left': '12mm'}
                )
                browser.close()

            if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                return {
                    'success': True,
                    'pdf_path': output_path,
                    'title': title,
                    'author': author
                }
            return {'success': False, 'error': '浏览器打印生成文件为空'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _extract_title(self, soup):
        """提取标题"""
        selectors = [
            'meta[property="og:title"]',
            'title',
            '.rich_media_title',
            '#activity-name',
            'h1',
            '.article-title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get('content') or element.text.strip()
                if title and len(title) > 5:
                    # 清理标题
                    title = re.sub(r'\s+', ' ', title)
                    return title
        
        return None
    
    def _extract_author(self, soup):
        """提取作者"""
        selectors = [
            'meta[name="author"]',
            'meta[property="og:article:author"]',
            '.rich_media_meta_list .rich_media_meta_text',
            '#js_name',
            '.account_name',
            '.profile_nickname'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                author = element.get('content') or element.text.strip()
                if author:
                    return author
        
        return None
    
    def _extract_and_format_content(self, soup):
        """提取文章内容并正确格式化"""
        # 微信公众号内容容器
        content_selectors = [
            '#js_content',
            '.rich_media_content',
            '.article-content',
            '.content',
            'article'
        ]
        
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                return self._format_content_properly(content_element)
        
        return None
    
    def _format_content_properly(self, element):
        """正确格式化内容，保留加粗和斜体格式"""
        # 创建副本以避免修改原始元素
        element = BeautifulSoup(str(element), 'html.parser')
        
        # 移除不需要的元素
        for tag in element.find_all(['script', 'style', 'iframe', 'noscript', 'ins', 'ads', 'img']):
            tag.decompose()
        
        # 转换标题
        for h in element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            level = int(h.name[1])
            h_text = h.get_text().strip()
            if h_text:
                h.string = f"{'#' * level} {h_text}\n\n"
        
        # 转换段落 - 保留格式标记（含 style/class 的粗体斜体）
        paragraphs = []
        for p in element.find_all('p'):
            p_text = self._extract_formatted_text(p)
            if p_text:
                paragraphs.append(p_text)
        
        # 转换列表
        for ul in element.find_all('ul'):
            for li in ul.find_all('li', recursive=False):
                li_text = self._extract_formatted_text(li)
                if li_text:
                    paragraphs.append(f"- {li_text}")
        
        for ol in element.find_all('ol'):
            for i, li in enumerate(ol.find_all('li', recursive=False), 1):
                li_text = self._extract_formatted_text(li)
                if li_text:
                    paragraphs.append(f"{i}. {li_text}")
        
        # 转换引用
        for blockquote in element.find_all('blockquote'):
            quote_text = self._extract_formatted_text(blockquote)
            if quote_text:
                paragraphs.append(f"> {quote_text}")
        
        # 构建最终文本
        formatted_text = []
        for para in paragraphs:
            if para.startswith('#') or para.startswith('-') or para.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '0.')) or para.startswith('>'):
                formatted_text.append(para)
            else:
                # 普通段落，确保有正确的句子分隔
                para = self._add_paragraph_breaks(para)
                formatted_text.append(para)
        
        return '\n\n'.join(formatted_text)

    def _extract_formatted_text(self, node):
        """递归提取文本，并保留粗体/斜体（标签与样式）为 Markdown 标记"""
        if not node:
            return ""

        if isinstance(node, NavigableString):
            text = str(node)
            text = re.sub(r'\s+', ' ', text)
            return text

        if not isinstance(node, Tag):
            return ""

        parts = [self._extract_formatted_text(child) for child in node.children]
        text = ''.join(parts)
        text = re.sub(r'\s+', ' ', text).strip()

        if not text:
            return ""

        is_bold = self._is_bold_like(node)
        is_italic = self._is_italic_like(node)

        if is_bold and is_italic:
            return f"***{text}***"
        if is_bold:
            return f"**{text}**"
        if is_italic:
            return f"*{text}*"

        return text

    def _is_bold_like(self, tag):
        """判断节点是否应视为粗体（标签、style、class）"""
        if not isinstance(tag, Tag):
            return False

        if tag.name in ['strong', 'b']:
            return True

        style = (tag.get('style') or '').lower()
        classes = ' '.join(tag.get('class', [])).lower()

        if 'font-weight' in style:
            if 'bold' in style or re.search(r'font-weight\s*:\s*([6-9]00|[1-9]\d{2,})', style):
                return True

        if any(k in classes for k in ['bold', 'font-weight', 'fw-bold']):
            return True

        return False

    def _is_italic_like(self, tag):
        """判断节点是否应视为斜体（标签、style、class）"""
        if not isinstance(tag, Tag):
            return False

        if tag.name in ['em', 'i']:
            return True

        style = (tag.get('style') or '').lower()
        classes = ' '.join(tag.get('class', [])).lower()

        if 'font-style' in style and 'italic' in style:
            return True

        if any(k in classes for k in ['italic', 'oblique']):
            return True

        return False
    
    def _add_paragraph_breaks(self, text):
        """为长文本添加段落分隔"""
        # 在中文句号、问号、感叹号后添加换行
        text = re.sub(r'([。！？；])([^」）】])', r'\1\n\2', text)
        
        # 如果文本太长，在适当位置分割
        if len(text) > 500:
            sentences = re.split(r'([。！？；])', text)
            result = []
            current_chunk = ""
            
            for i in range(0, len(sentences), 2):
                if i + 1 < len(sentences):
                    sentence = sentences[i] + sentences[i+1]
                else:
                    sentence = sentences[i]
                
                if len(current_chunk) + len(sentence) > 300:
                    if current_chunk:
                        result.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += sentence
            
            if current_chunk:
                result.append(current_chunk.strip())
            
            return '\n\n'.join(result)
        
        return text
    
    def generate_article_id(self, url):
        """生成文章ID"""
        return hashlib.md5(url.encode()).hexdigest()[:8]
    
    def save_article(self, article_data):
        """保存文章"""
        article_id = article_data['id']
        article_dir = self.base_dir / "articles" / article_id
        article_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存内容
        content_path = article_dir / "content.md"
        with open(content_path, "w", encoding="utf-8") as f:
            f.write(article_data['content'])
        
        # 保存元数据
        metadata_path = article_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(article_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 文章保存成功，ID: {article_id}")
        return article_id
    
    def update_author_stats(self, author_name):
        """更新作者统计"""
        author_file = self.base_dir / "authors" / f"{author_name}.json"
        
        if author_file.exists():
            with open(author_file, "r", encoding="utf-8") as f:
                author_data = json.load(f)
            author_data['total_articles'] = author_data.get('total_articles', 0) + 1
            author_data['last_article_date'] = datetime.datetime.now().isoformat()
        else:
            author_data = {
                "name": author_name,
                "added_date": datetime.datetime.now().isoformat(),
                "last_check": None,
                "last_article_date": datetime.datetime.now().isoformat(),
                "total_articles": 1,
                "info": {
                    "description": "微信公众号作者",
                    "category": "未分类",
                    "priority": "medium",
                    "notes": "自动添加的作者"
                }
            }
        
        with open(author_file, "w", encoding="utf-8") as f:
            json.dump(author_data, f, ensure_ascii=False, indent=2)
        
        print(f"📊 作者统计更新: {author_name} ({author_data['total_articles']}篇文章)")
        return author_data
    
    def process_article(self, url, custom_title=None, use_browser_fallback=False, use_remote_fallback=False):
        """处理文章"""
        print("=" * 70)
        print("🤖 修复版微信公众号文章处理系统")
        print("=" * 70)
        print(f"📄 目标文章: {url}")
        
        # 生成文章ID
        article_id = self.generate_article_id(url)
        
        # 抓取文章
        print("\n🔄 抓取并格式化文章内容...")
        fetched_data = self.fetch_article(
            url,
            use_browser_fallback=use_browser_fallback,
            use_remote_fallback=use_remote_fallback
        )
        
        if fetched_data['success']:
            print("✅ 成功抓取并格式化文章内容")
            title = custom_title or fetched_data['title']
            author = fetched_data['author']
            content = fetched_data['content']
            word_count = len(content)
            
            print(f"   标题: {title}")
            print(f"   作者: {author}")
            print(f"   字数: {word_count}字")
            print(f"   段落数: {content.count('\\n\\n') + 1}")
        else:
            print("❌ 无法抓取文章内容")
            print("   将使用格式化后的模拟内容生成PDF")
            
            title = custom_title or f"文章_{article_id}"
            author = "未知作者"
            content = f"""# {title}

## 文章链接
{url}

## 抓取状态
⚠️ 自动抓取失败，以下是格式化后的模拟内容。

## 可能的原因
1. 微信公众号文章需要登录才能访问完整内容
2. 文章链接可能已过期或需要特定权限
3. 反爬虫机制阻止了自动抓取

## 解决方案
1. **手动复制粘贴**：在浏览器中打开文章，复制全文内容
2. **使用微信客户端**：在微信中打开文章，分享到文件传输助手
3. **截图转文字**：使用OCR工具提取文章内容

## 模拟内容
这是一个测试段落，用于验证修复版的段落分隔功能。

从第一个100万，到第一个1亿，不仅是数字的变化，更是思维模式、认知层次和行动方式的全面升级。

财富积累需要时间和耐心，每个阶段都有其必要的积累过程。不要急于求成，要稳扎稳打。

### 测试要点
- 中文字符显示
- 段落分隔效果
- 格式排版效果
- PDF兼容性

> 这是一段引用文字，用于测试引用格式。

## 后续步骤
请将实际文章内容复制粘贴到系统中，系统将为您生成格式良好的PDF文件。"""
            word_count = 300
        
        # 准备文章数据
        article_data = {
            "id": article_id,
            "title": title,
            "author": author,
            "content": content,
            "url": url,
            "publish_date": datetime.datetime.now().isoformat(),
            "save_date": datetime.datetime.now().isoformat(),
            "word_count": word_count,
            "fetched_success": fetched_data['success']
        }
        
        # 保存文章
        print("\n💾 保存文章数据...")
        self.save_article(article_data)
        
        # 生成PDF
        print("\n📄 生成修复版微信公众号风格PDF...")
        pdf_path = self.pdf_generator.generate_pdf(article_data)
        
        if not pdf_path:
            print("❌ PDF生成失败")
            return None
        
        # 更新作者统计
        self.update_author_stats(author)
        
        # 显示结果
        print("\n🎉 文章处理完成！")
        print("=" * 50)
        print(f"📝 标题: {title}")
        print(f"👤 作者: {author}")
        print(f"🆔 文章ID: {article_id}")
        print(f"📄 PDF文件: {pdf_path}")
        print(f"📊 字数: {word_count}字")
        
        if not fetched_data['success']:
            print("\n⚠️ 注意：这是模拟内容PDF")
            print("   请手动复制实际文章内容，然后重新生成PDF")
        
        return {
            "article_id": article_id,
            "pdf_path": pdf_path,
            "author": author,
            "title": title,
            "word_count": word_count,
            "is_real_content": fetched_data['success']
        }
    
    def get_system_status(self):
        """获取系统状态"""
        authors_dir = self.base_dir / "authors"
        articles_dir = self.base_dir / "articles"
        pdfs_dir = self.base_dir / "pdfs"
        
        author_count = len(list(authors_dir.glob("*.json"))) if authors_dir.exists() else 0
        article_count = len(list(articles_dir.iterdir())) if articles_dir.exists() else 0
        pdf_count = len(list(pdfs_dir.glob("*.pdf"))) if pdfs_dir.exists() else 0
        
        print("\n📊 系统状态报告")
        print("=" * 40)
        print(f"监控作者: {author_count} 位")
        print(f"总文章数: {article_count} 篇")
        print(f"PDF文件: {pdf_count} 个")
        
        # 显示作者详情
        if author_count > 0:
            print("\n📝 作者文章统计:")
            total_articles = 0
            for author_file in sorted(authors_dir.glob("*.json")):
                with open(author_file, "r", encoding="utf-8") as f:
                    author_data = json.load(f)
                count = author_data.get('total_articles', 0)
                total_articles += count
                print(f"  {author_data['name']}: {count} 篇")
            
            print(f"\n📈 总计: {total_articles} 篇文章")
        
        return {
            "authors": author_count,
            "articles": article_count,
            "pdfs": pdf_count
        }

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python process_wechat_fixed.py <文章URL> [自定义标题]")
        print("示例: python process_wechat_fixed.py https://mp.weixin.qq.com/s/example")
        print("       python process_wechat_fixed.py https://mp.weixin.qq.com/s/example '自定义标题'")
        print("\n📝 修复版特点:")
        print("  - 解决段落分隔问题")
        print("  - 正确的首行缩进和段落间距")
        print("  - 16px正文字体，1.75倍行距")
        print("  - 两端对齐，微信公众号标准排版")
        print("  - 带页眉页脚和精美封面")
        return
    
    url = sys.argv[1]
    custom_title = sys.argv[2] if len(sys.argv) > 2 else None
    
    fixer = WeChatArticleFixer()
    
    # 处理文章
    result = fixer.process_article(url, custom_title)
    
    if result:
        # 显示系统状态
        fixer.get_system_status()
        
        print("\n✅ 处理完成！")
        print("=" * 40)
        print("你现在可以:")
        print(f"  1. 查看PDF文件: {result['pdf_path'].name}")
        print(f"  2. 检查段落分隔效果")
        print(f"  3. 验证排版质量")
        
        if not result['is_real_content']:
            print("\n⚠️ 重要提示:")
            print("  由于无法自动抓取文章内容，生成了模拟PDF")
            print("  请手动复制实际文章内容，然后重新处理")
        
        print("\n🔄 继续处理更多文章:")
        print("  python process_wechat_fixed.py <文章URL>")

if __name__ == "__main__":
    main()