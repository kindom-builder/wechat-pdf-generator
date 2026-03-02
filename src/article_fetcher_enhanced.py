#!/usr/bin/env python3
"""
增强版微信公众号文章抓取器
提供稳定、可靠的文章内容获取
"""

import os
import re
import json
import time
import random
import hashlib
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import urllib3
from fake_useragent import UserAgent

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedArticleFetcher:
    """增强版文章抓取器"""
    
    def __init__(self, cache_dir: str = "cache"):
        """
        初始化抓取器
        
        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 初始化User-Agent生成器
        self.ua = UserAgent()
        
        # 请求配置
        self.session = requests.Session()
        self.session.verify = False  # 禁用SSL验证（某些环境需要）
        
        # 配置请求头
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        
        # 重试配置
        self.max_retries = 3
        self.retry_delay = 2  # 秒
        
        # 超时配置
        self.timeout = 30
        
        # 缓存配置（小时）
        self.cache_expiry = 24
        
        logger.info("增强版文章抓取器初始化完成")
    
    def get_cache_key(self, url: str) -> str:
        """生成缓存键"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"article_{url_hash}.json"
    
    def is_cache_valid(self, cache_file: Path) -> bool:
        """检查缓存是否有效"""
        if not cache_file.exists():
            return False
        
        # 检查缓存时间
        cache_age = time.time() - cache_file.stat().st_mtime
        return cache_age < (self.cache_expiry * 3600)
    
    def load_from_cache(self, cache_file: Path) -> Optional[Dict]:
        """从缓存加载"""
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载缓存失败: {e}")
            return None
    
    def save_to_cache(self, cache_file: Path, data: Dict):
        """保存到缓存"""
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")
    
    def generate_random_headers(self) -> Dict:
        """生成随机请求头"""
        headers = self.headers.copy()
        headers['User-Agent'] = self.ua.random
        
        # 添加更多随机化
        headers['Accept-Language'] = random.choice([
            'zh-CN,zh;q=0.9',
            'zh-CN,zh;q=0.8,en;q=0.7',
            'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'
        ])
        
        return headers
    
    def fetch_with_retry(self, url: str) -> Optional[requests.Response]:
        """带重试的请求"""
        for attempt in range(self.max_retries):
            try:
                # 随机延迟（避免请求过于频繁）
                if attempt > 0:
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"第{attempt + 1}次重试，等待{delay:.1f}秒...")
                    time.sleep(delay)
                
                # 生成随机请求头
                headers = self.generate_random_headers()
                
                logger.info(f"尝试抓取: {url} (尝试 {attempt + 1}/{self.max_retries})")
                
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                    stream=False
                )
                
                # 检查响应状态
                response.raise_for_status()
                
                # 检查内容类型
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type and 'application/json' not in content_type:
                    logger.warning(f"非HTML/JSON响应: {content_type}")
                    continue
                
                logger.info(f"抓取成功: 状态码 {response.status_code}, 大小 {len(response.content)} 字节")
                return response
                
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{self.max_retries})")
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"连接错误: {e} (尝试 {attempt + 1}/{self.max_retries})")
            except requests.exceptions.HTTPError as e:
                logger.warning(f"HTTP错误: {e} (尝试 {attempt + 1}/{self.max_retries})")
                if response.status_code == 403:
                    logger.error("访问被拒绝 (403)，可能需要处理反爬虫")
                elif response.status_code == 404:
                    logger.error("页面不存在 (404)")
                    return None  # 404不需要重试
            except Exception as e:
                logger.warning(f"请求异常: {e} (尝试 {attempt + 1}/{self.max_retries})")
        
        logger.error(f"所有{self.max_retries}次尝试都失败")
        return None
    
    def extract_wechat_article(self, html: str, url: str) -> Dict:
        """提取微信公众号文章内容"""
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 方法1：尝试提取公众号文章结构
            article_data = self._extract_wechat_structure(soup)
            if article_data['success']:
                return article_data
            
            # 方法2：尝试提取通用文章结构
            article_data = self._extract_general_article(soup)
            if article_data['success']:
                return article_data
            
            # 方法3：提取所有文本内容
            article_data = self._extract_all_text(soup)
            return article_data
            
        except Exception as e:
            logger.error(f"提取文章内容失败: {e}")
            return {
                'success': False,
                'error': f'提取失败: {str(e)}',
                'title': '提取失败',
                'author': '未知',
                'content': f'无法提取文章内容。错误: {str(e)}\n\n原文URL: {url}'
            }
    
    def _extract_wechat_structure(self, soup: BeautifulSoup) -> Dict:
        """提取微信公众号特有结构"""
        result = {
            'success': False,
            'title': '',
            'author': '',
            'content': ''
        }
        
        try:
            # 尝试查找微信公众号文章标题
            title_selectors = [
                '#activity-name',
                '.rich_media_title',
                'h1#title',
                'h1.title',
                'h1',
                'title'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem and title_elem.text.strip():
                    result['title'] = title_elem.text.strip()
                    break
            
            # 尝试查找作者
            author_selectors = [
                '#js_name',
                '.rich_media_meta_text',
                '.profile_nickname',
                'meta[name="author"]',
                '.author'
            ]
            
            for selector in author_selectors:
                author_elem = soup.select_one(selector)
                if author_elem and author_elem.text.strip():
                    result['author'] = author_elem.text.strip()
                    break
            
            # 尝试查找文章内容
            content_selectors = [
                '#js_content',
                '.rich_media_content',
                '.article-content',
                '.content',
                'article',
                'main'
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # 清理内容
                    content = self._clean_content(content_elem)
                    if content:
                        result['content'] = content
                        result['success'] = True
                        break
            
            # 如果找到标题和内容，就算成功
            if result['title'] and result['content']:
                result['success'] = True
                
        except Exception as e:
            logger.warning(f"提取微信公众号结构失败: {e}")
        
        return result
    
    def _extract_general_article(self, soup: BeautifulSoup) -> Dict:
        """提取通用文章结构"""
        result = {
            'success': False,
            'title': '',
            'author': '',
            'content': ''
        }
        
        try:
            # 提取标题（从多个可能的位置）
            title = soup.find('title')
            if title:
                result['title'] = title.text.strip()
            
            # 提取作者（从meta标签或特定class）
            author_meta = soup.find('meta', attrs={'name': 'author'})
            if author_meta and author_meta.get('content'):
                result['author'] = author_meta['content']
            
            # 尝试提取主要文章内容
            # 策略：找到包含最多文本的容器
            candidates = []
            
            # 检查常见的文章容器
            article_tags = soup.find_all(['article', 'main', 'div', 'section'])
            for tag in article_tags:
                # 计算文本长度
                text_length = len(tag.get_text(strip=True))
                if text_length > 100:  # 至少100字符
                    candidates.append((tag, text_length))
            
            # 选择文本最多的候选
            if candidates:
                candidates.sort(key=lambda x: x[1], reverse=True)
                best_candidate = candidates[0][0]
                
                # 清理内容
                content = self._clean_content(best_candidate)
                if content:
                    result['content'] = content
                    result['success'] = True
                    
                    # 如果没有找到标题，尝试从h1-h3中提取
                    if not result['title']:
                        for heading in best_candidate.find_all(['h1', 'h2', 'h3']):
                            if heading.text.strip():
                                result['title'] = heading.text.strip()
                                break
            
        except Exception as e:
            logger.warning(f"提取通用文章结构失败: {e}")
        
        return result
    
    def _extract_all_text(self, soup: BeautifulSoup) -> Dict:
        """提取所有文本内容（最后的手段）"""
        result = {
            'success': True,  # 总是返回一些内容
            'title': '网页内容',
            'author': '未知',
            'content': ''
        }
        
        try:
            # 移除脚本、样式等不需要的元素
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
            
            # 获取所有文本
            all_text = soup.get_text(separator='\n', strip=True)
            
            # 清理空白行
            lines = [line.strip() for line in all_text.split('\n') if line.strip()]
            result['content'] = '\n\n'.join(lines[:100])  # 限制行数
            
            # 尝试从前面几行提取标题
            if lines:
                for line in lines[:10]:
                    if len(line) > 10 and len(line) < 100:  # 合理的标题长度
                        result['title'] = line
                        break
            
        except Exception as e:
            logger.warning(f"提取所有文本失败: {e}")
            result['content'] = f"无法提取文章内容。错误: {str(e)}"
        
        return result
    
    def _clean_content(self, element) -> str:
        """清理文章内容"""
        try:
            # 创建副本以避免修改原始元素
            cleaned = element.copy()
            
            # 移除不需要的元素
            for tag in cleaned(['script', 'style', 'iframe', 'noscript', 'button', 'form', 'input']):
                tag.decompose()
            
            # 处理图片
            for img in cleaned.find_all('img'):
                alt = img.get('alt', '')
                src = img.get('src', '')
                if alt:
                    img.replace_with(f'\n[图片: {alt}]\n')
                elif src:
                    img.replace_with(f'\n[图片]\n')
                else:
                    img.decompose()
            
            # 处理链接
            for a in cleaned.find_all('a'):
                href = a.get('href', '')
                text = a.get_text(strip=True)
                if href and text:
                    a.replace_with(f'{text} ({href})')
                else:
                    a.unwrap()
            
            # 处理标题
            for h in cleaned.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                level = int(h.name[1])
                text = h.get_text(strip=True)
                h.replace_with(f'\n{"#" * level} {text}\n')
            
            # 处理列表
            for ul in cleaned.find_all('ul'):
                items = []
                for li in ul.find_all('li'):
                    item_text = li.get_text(strip=True)
                    if item_text:
                        items.append(f'• {item_text}')
                if items:
                    ul.replace_with('\n' + '\n'.join(items) + '\n')
                else:
                    ul.decompose()
            
            for ol in cleaned.find_all('ol'):
                items = []
                for i, li in enumerate(ol.find_all('li'), 1):
                    item_text = li.get_text(strip=True)
                    if item_text:
                        items.append(f'{i}. {item_text}')
                if items:
                    ol.replace_with('\n' + '\n'.join(items) + '\n')
                else:
                    ol.decompose()
            
            # 处理引用
            for blockquote in cleaned.find_all('blockquote'):
                text = blockquote.get_text(strip=True)
                if text:
                    blockquote.replace_with(f'\n> {text}\n')
                else:
                    blockquote.decompose()
            
            # 获取文本并清理
            text = cleaned.get_text(separator='\n', strip=True)
            
            # 清理空白行和多余空行
            lines = []
            for line in text.split('\n'):
                line = line.strip()
                if line:
                    # 合并短行
                    if lines and len(lines[-1]) < 50 and len(line) < 50:
                        lines[-1] = lines[-1] + ' ' + line
                    else:
                        lines.append(line)
            
            # 添加段落分隔
            content = '\n\n'.join(lines)
            
            # 限制最大长度
            if len(content) > 100000:
                content = content[:100000] + '\n\n[内容过长，已截断]'
            
            return content
            
        except Exception as e:
            logger.warning(f"清理内容失败: {e}")
            return element.get_text(separator='\n', strip=True)
    
    def fetch_article(self, url: str, use_cache: bool = True) -> Dict:
        """
        抓取文章内容
        
        Args:
            url: 文章URL
            use_cache: 是否使用缓存
            
        Returns:
            文章数据字典
        """
        start_time = time.time()
        
        # 检查缓存
        cache_file = self.cache_dir / self.get_cache_key(url)
        if use_cache and self.is_cache_valid(cache_file):
            cached_data = self.load_from_cache(cache_file)
            if cached_data:
                logger.info(f"使用缓存数据: {url}")
                cached_data['from_cache'] = True
                return cached_data
        
        # 初始化结果
        result = {
            'success': False,
            'url': url,
            'title': '',
            'author': '未知作者',
            'content': '',
            'error': '',
            'from_cache': False,
            'fetch_time': 0,
            'response_status': 0
        }
        
        try:
            # 验证URL
            if not url.startswith('http'):
                result['error'] = '无效的URL格式'
                return result
            
            # 抓取网页
            response = self.fetch_with_retry(url)
            if response is None:
                result['error'] = '抓取失败，请检查URL和网络连接'
                return result
            
            result['response_status'] = response.status_code
            
            # 检查重定向
            if response.history:
                result['redirected'] = True
                result['final_url'] = response.url
                logger.info(f"发生重定向: {url} -> {response.url}")
            
            # 提取文章内容
            html = response.text
            article_data = self.extract_wechat_article(html, url)
            
            if article_data['success']:
                result.update(article_data)
                result['success'] = True
                result['word_count'] = len(result['content'])
                
                logger.info(f"文章提取成功: {result['title']} ({result['word_count']}字)")
            else:
                result['error'] = article_data.get('error', '无法提取文章内容')
                result['title'] = article_data.get('title', '提取失败')
                result['content'] = article_data.get('content', '')
                
                # 即使提取失败，也返回一些内容
                if not result['content']:
                    result['content'] = self._create_fallback_content(url, result['error'])
                
                logger.warning(f"文章提取部分成功: {result['error']}")
            
            # 计算抓取时间
            result['fetch_time'] = round(time.time() - start_time, 2)
            
            # 保存到缓存
            if result['success'] or result['content']:
                self.save_to_cache(cache_file, result)
            
            return result
            
        except Exception as e:
            logger.error(f"抓取过程异常: {e}", exc_info=True)
            result['error'] = f'抓取异常: {str(e)}'
            result['fetch_time'] = round(time.time() - start_time, 2)
            return result
    
    def _create_fallback_content(self, url: str, error: str) -> str:
        """创建备用内容"""
        return f"""# 文章抓取说明

## 文章链接
{url}

## 抓取状态
⚠️ 自动抓取遇到问题: {error}

## 可能的原因
1. **微信公众号限制**：文章需要登录或特定权限才能访问
2. **反爬虫机制**：网站阻止了自动抓取
3. **网络问题**：连接不稳定或超时
4. **页面结构变化**：网站更新了页面布局

## 解决方案
1. **手动复制粘贴**：
   - 在浏览器中打开文章
   - 复制全文内容（Ctrl+A, Ctrl+C）
   - 使用其他工具生成PDF

2. **使用微信客户端**：
   - 在微信中打开文章
   - 分享到文件传输助手
   - 从手机复制内容

3. **截图转文字**：
   - 使用OCR工具（如百度OCR、腾讯OCR）
   - 截图后识别文字
   - 整理识别结果

4. **联系支持**：
   - 检查URL是否正确
   - 尝试不同的网络环境
   - 等待一段时间后重试

## 技术详情
- 抓取时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 错误类型: {error}

## 备用内容示例
这是一个示例段落，用于展示PDF生成器的排版效果。

从第一个100万，到第一个1亿，不仅是数字的变化，更是思维模式、认知层次和行动方式的全面升级。

财富积累需要时间和耐心，每个阶段都有其必要的积累过程。不要急于求成，要稳扎稳打。

### 测试要点
- 中文字符显示测试
- 段落分隔效果验证
- 格式排版兼容性检查
- PDF文件生成测试

> 这是一段引用文字，用于测试引用格式的显示效果。

## 后续步骤
请将实际文章内容提供给系统，系统将为您生成格式良好的PDF文件。"""

class ArticleFetchManager:
    """文章抓取管理器"""
    
    def __init__(self):
        self.fetcher = EnhancedArticleFetcher()
        self.stats = {
            'total_requests': 0,
            'successful_fetches': 0,
            'failed_fetches': 0,
            'cache_hits': 0,
            'total_fetch_time': 0
        }
    
    def fetch(self, url: str, use_cache: bool = True) -> Dict:
        """抓取文章（带统计）"""
        self.stats['total_requests'] += 1
        
        result = self.fetcher.fetch_article(url, use_cache)
        
        if result['from_cache']:
            self.stats['cache_hits'] += 1
        
        if result['success']:
            self.stats['successful_fetches'] += 1
        else:
            self.stats['failed_fetches'] += 1
        
        if 'fetch_time' in result:
            self.stats['total_fetch_time'] += result['fetch_time']
        
        return result
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        avg_time = 0
        if self.stats['total_requests'] > 0:
            avg_time = self.stats['total_fetch_time'] / self.stats['total_requests']
        
        success_rate = 0
        if self.stats['total_requests'] > 0:
            success_rate = (self.stats['successful_fetches'] / self.stats['total_requests']) * 100
        
        cache_rate = 0
        if self.stats['total_requests'] > 0:
            cache_rate = (self.stats['cache_hits'] / self.stats['total_requests']) * 100
        
        return {
            **self.stats,
            'avg_fetch_time': round(avg_time, 2),
            'success_rate': round(success_rate, 1),
            'cache_rate': round(cache_rate, 1),
            'timestamp': datetime.datetime.now().isoformat()
        }
    
    def clear_cache(self, older_than_hours: int = 24):
        """清理过期缓存"""
        cache_dir = self.fetcher.cache_dir
        if not cache_dir.exists():
            return
        
        current_time = time.time()
        expiry_seconds = older_than_hours * 3600
        
        deleted_count = 0
        for cache_file in cache_dir.glob("*.json"):
            file_age = current_time - cache_file.stat().st_mtime
            if file_age > expiry_seconds:
                try:
                    cache_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"删除缓存文件失败 {cache_file}: {e}")
        
        logger.info(f"清理了 {deleted_count} 个过期缓存文件")

# 测试函数
def test_fetcher():
    """测试抓取器"""
    print("🧪 测试增强版文章抓取器...")
    
    # 测试URL（使用示例URL）
    test_urls = [
        "https://mp.weixin.qq.com/s/example1",
        "https://mp.weixin.qq.com/s/example2",
        "https://blog.example.com/test-article"
    ]
    
    manager = ArticleFetchManager()
    
    for url in test_urls:
        print(f"\n🔗 测试URL: {url}")
        print("-" * 50)
        
        result = manager.fetch(url, use_cache=False)
        
        if result['success']:
            print(f"✅ 抓取成功")
            print(f"   标题: {result['title']}")
            print(f"   作者: {result['author']}")
            print(f"   字数: {result.get('word_count', 0)}")
            print(f"   时间: {result['fetch_time']}秒")
        else:
            print(f"❌ 抓取失败")
            print(f"   错误: {result['error']}")
            print(f"   内容长度: {len(result['content'])}字符")
        
        # 显示内容预览
        if result['content']:
            preview = result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
            print(f"   内容预览: {preview}")
    
    # 显示统计
    stats = manager.get_stats()
    print(f"\n📊 抓取统计:")
    print(f"   总请求: {stats['total_requests']}")
    print(f"   成功: {stats['successful_fetches']}")
    print(f"   失败: {stats['failed_fetches']}")
    print(f"   成功率: {stats['success_rate']}%")
    print(f"   平均时间: {stats['avg_fetch_time']}秒")
    
    # 清理缓存
    manager.clear_cache(older_than_hours=1)
    
    print("\n✅ 测试完成")

if __name__ == "__main__":
    test_fetcher()