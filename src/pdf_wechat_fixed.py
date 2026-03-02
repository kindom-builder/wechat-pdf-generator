#!/usr/bin/env python3
"""
修复版微信公众号风格PDF生成器
解决段落分行和排版问题
"""

import os
import datetime
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, KeepTogether, HRFlowable
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus.flowables import Flowable
import re
import textwrap

class FixedWeChatPDFGenerator:
    """修复版微信公众号风格PDF生成器"""
    
    def __init__(self):
        self.setup_fonts()
        self.styles = getSampleStyleSheet()
        self.create_fixed_styles()
        self.page_width, self.page_height = A4
        
    def setup_fonts(self):
        """设置字体"""
        try:
            # 注册多种字体
            font_paths = [
                "/mnt/c/Windows/Fonts/msyh.ttc",      # 微软雅黑（正文）
                "/mnt/c/Windows/Fonts/simsun.ttc",    # 宋体（标题备用）
                "/mnt/c/Windows/Fonts/simhei.ttf",    # 黑体（强调）
                "/mnt/c/Windows/Fonts/simkai.ttf",    # 楷体（引用）
            ]
            
            self.registered_fonts = {}
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font_name = os.path.basename(font_path).split('.')[0]
                    try:
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        self.registered_fonts[font_name] = font_path
                        print(f"✅ 注册字体: {font_name}")
                    except:
                        continue
            
            if 'msyh' in self.registered_fonts:
                self.main_font = 'msyh'  # 微软雅黑
                self.title_font = 'msyh'  # 标题也用微软雅黑
                self.quote_font = 'simkai' if 'simkai' in self.registered_fonts else 'msyh'  # 楷体或微软雅黑
            else:
                print("⚠️ 未找到微软雅黑字体，使用Helvetica")
                self.main_font = "Helvetica"
                self.title_font = "Helvetica-Bold"
                self.quote_font = "Helvetica-Oblique"
            
        except Exception as e:
            print(f"❌ 字体设置失败: {e}")
            self.main_font = "Helvetica"
            self.title_font = "Helvetica-Bold"
            self.quote_font = "Helvetica-Oblique"
    
    def create_fixed_styles(self):
        """创建修复版样式"""
        
        # ========== 封面页样式 ==========
        
        # 微信公众号大标题样式
        self.styles.add(ParagraphStyle(
            name='WeChatCoverTitle',
            parent=self.styles['Title'],
            fontName=self.title_font,
            fontSize=26,
            leading=34,
            spaceAfter=40,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#222222'),
            fontNameBold=self.title_font,
            bold=True
        ))
        
        # 作者信息（封面）
        self.styles.add(ParagraphStyle(
            name='WeChatCoverAuthor',
            parent=self.styles['Normal'],
            fontName=self.main_font,
            fontSize=16,
            leading=22,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#576B95'),
            fontNameBold=self.main_font,
            bold=True
        ))
        
        # ========== 正文样式 ==========
        
        # 正文段落（最终微调的紧凑排版）
        self.styles.add(ParagraphStyle(
            name='WeChatBody',
            parent=self.styles['Normal'],
            fontName=self.main_font,
            fontSize=13,  # 保持13px
            leading=17.5, # 1.35倍行距（微调，更紧凑）
            spaceAfter=8,  # 段后间距（进一步减小）
            alignment=TA_JUSTIFY,  # 两端对齐
            textColor=colors.HexColor('#222222'),
            firstLineIndent=26,  # 首行缩进2字符（13px * 2）
            wordWrap='CJK'  # 中文换行
        ))
        
        # 一级标题（文章内）
        self.styles.add(ParagraphStyle(
            name='WeChatH1',
            parent=self.styles['Heading1'],
            fontName=self.title_font,
            fontSize=19,  # 调整为19px（进一步减小）
            leading=23,   # 进一步减小行距
            spaceBefore=25,  # 标题前间距（进一步减小）
            spaceAfter=12,   # 标题后间距（进一步减小）
            alignment=TA_LEFT,
            textColor=colors.HexColor('#222222'),
            fontNameBold=self.title_font,
            bold=True,
            leftIndent=0,
            firstLineIndent=0
        ))
        
        # 二级标题
        self.styles.add(ParagraphStyle(
            name='WeChatH2',
            parent=self.styles['Heading2'],
            fontName=self.title_font,
            fontSize=17,  # 调整为17px（进一步减小）
            leading=21,   # 进一步减小行距
            spaceBefore=20,  # 标题前间距（进一步减小）
            spaceAfter=10,   # 标题后间距（进一步减小）
            alignment=TA_LEFT,
            textColor=colors.HexColor('#333333'),
            fontNameBold=self.title_font,
            bold=True
        ))
        
        # 三级标题
        self.styles.add(ParagraphStyle(
            name='WeChatH3',
            parent=self.styles['Heading3'],
            fontName=self.main_font,
            fontSize=15,  # 调整为15px（进一步减小）
            leading=19,   # 进一步减小行距
            spaceBefore=15,  # 标题前间距（进一步减小）
            spaceAfter=8,   # 标题后间距（进一步减小）
            alignment=TA_LEFT,
            textColor=colors.HexColor('#444444'),
            fontNameBold=self.main_font,
            bold=True
        ))
        
        # ========== 特殊元素样式 ==========
        
        # 引用块（微信公众号的引用样式）
        self.styles.add(ParagraphStyle(
            name='WeChatQuote',
            parent=self.styles['Normal'],
            fontName=self.quote_font,
            fontSize=12,  # 调整为12px（进一步减小）
            leading=17,   # 进一步减小行距
            leftIndent=12,  # 进一步减小缩进
            rightIndent=12, # 进一步减小缩进
            spaceBefore=12, # 进一步减小间距
            spaceAfter=12,  # 进一步减小间距
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor('#666666'),
            backColor=colors.HexColor('#F8F8F8'),
            borderColor=colors.HexColor('#E6E6E6'),
            borderWidth=1,
            borderPadding=(8, 10, 8, 10),  # 上右下左（进一步减小内边距）
            borderRadius=3  # 进一步减小圆角
        ))
        
        # 列表项
        self.styles.add(ParagraphStyle(
            name='WeChatListItem',
            parent=self.styles['Normal'],
            fontName=self.main_font,
            fontSize=13,  # 调整为13px（与正文一致）
            leading=18,   # 进一步减小行距
            spaceAfter=5,  # 进一步减小间距
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor('#222222'),
            leftIndent=18,
            firstLineIndent=-13,  # 让项目符号突出
            bulletIndent=0
        ))
        
        # 代码块
        self.styles.add(ParagraphStyle(
            name='WeChatCodeBlock',
            parent=self.styles['Code'],
            fontName='Courier',
            fontSize=11,  # 调整为11px（进一步减小）
            leading=15,   # 进一步减小行距
            spaceBefore=8,  # 进一步减小间距
            spaceAfter=8,   # 进一步减小间距
            alignment=TA_LEFT,
            textColor=colors.HexColor('#333333'),
            backColor=colors.HexColor('#F5F5F5'),
            borderColor=colors.HexColor('#DDDDDD'),
            borderWidth=1,
            borderPadding=6,  # 进一步减小内边距
            borderRadius=3
        ))
        
        # 行内代码
        self.styles.add(ParagraphStyle(
            name='WeChatInlineCode',
            parent=self.styles['Normal'],
            fontName='Courier',
            fontSize=11,  # 调整为11px（进一步减小）
            textColor=colors.HexColor('#E74C3C'),
            backColor=colors.HexColor('#FDF2F2'),
            borderPadding=2,
            borderRadius=2
        ))
        
        # ========== 页眉页脚样式 ==========
        
        # 页眉
        self.styles.add(ParagraphStyle(
            name='WeChatHeader',
            parent=self.styles['Normal'],
            fontName=self.main_font,
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#999999')
        ))
        
        # 页脚
        self.styles.add(ParagraphStyle(
            name='WeChatFooter',
            parent=self.styles['Normal'],
            fontName=self.main_font,
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#999999')
        ))
        
        # 元信息（时间等）
        self.styles.add(ParagraphStyle(
            name='WeChatMetaInfo',
            parent=self.styles['Normal'],
            fontName=self.main_font,
            fontSize=13,
            leading=18,
            spaceAfter=8,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#8C8C8C')
        ))
    
    def format_content_with_paragraphs(self, content):
        """格式化内容，确保正确的段落分隔"""
        print("📝 格式化文章内容...")
        
        # 首先清理内容
        content = content.strip()
        
        # 替换常见的段落分隔符
        content = re.sub(r'([。！？；])([^」）】])', r'\1\n\n\2', content)  # 中文句号后换行
        content = re.sub(r'([。！？；])\s*$', r'\1', content)  # 清理行尾
        
        # 处理特殊情况
        content = re.sub(r'([^.])\n([^.\n])', r'\1 \2', content)  # 合并不必要的换行
        content = re.sub(r'\n{3,}', '\n\n', content)  # 多个空行合并为一个
        
        # 确保每段都有首行缩进
        paragraphs = []
        for para in content.split('\n\n'):
            para = para.strip()
            if para:
                # 添加首行缩进标记
                paragraphs.append(para)
        
        return '\n\n'.join(paragraphs)
    
    def parse_content(self, content):
        """解析文章内容，转换为微信公众号风格的段落"""
        elements = []
        
        # 先格式化内容
        formatted_content = self.format_content_with_paragraphs(content)
        
        lines = formatted_content.split('\n')
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                # 空行表示段落结束
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    elements.append(self.create_paragraph(paragraph_text))
                    current_paragraph = []
                elements.append(Spacer(1, 6))  # 段落间距（进一步减小）
                continue
            
            # 检查标题
            if line.startswith('# '):
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    elements.append(self.create_paragraph(paragraph_text))
                    current_paragraph = []
                title = line[2:].strip()
                elements.append(Paragraph(title, self.styles['WeChatH1']))
                continue
            
            elif line.startswith('## '):
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    elements.append(self.create_paragraph(paragraph_text))
                    current_paragraph = []
                subtitle = line[3:].strip()
                elements.append(Paragraph(subtitle, self.styles['WeChatH2']))
                continue
            
            elif line.startswith('### '):
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    elements.append(self.create_paragraph(paragraph_text))
                    current_paragraph = []
                subsubtitle = line[4:].strip()
                elements.append(Paragraph(subsubtitle, self.styles['WeChatH3']))
                continue
            
            # 检查列表
            if line.startswith('- ') or line.startswith('* '):
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    elements.append(self.create_paragraph(paragraph_text))
                    current_paragraph = []
                list_item = line[2:].strip()
                list_text = f'<para leftIndent="20" firstLineIndent="-15"><b>•</b> {list_item}</para>'
                elements.append(Paragraph(list_text, self.styles['WeChatListItem']))
                continue
            
            elif re.match(r'^\d+\.\s', line):
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    elements.append(self.create_paragraph(paragraph_text))
                    current_paragraph = []
                list_item = re.sub(r'^\d+\.\s', '', line)
                list_text = f'<para leftIndent="20" firstLineIndent="-15"><b>•</b> {list_item}</para>'
                elements.append(Paragraph(list_text, self.styles['WeChatListItem']))
                continue
            
            # 检查引用
            if line.startswith('> '):
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    elements.append(self.create_paragraph(paragraph_text))
                    current_paragraph = []
                quote = line[2:].strip()
                elements.append(Paragraph(quote, self.styles['WeChatQuote']))
                continue
            
            # 普通文本行
            current_paragraph.append(line)
        
        # 处理最后一段
        if current_paragraph:
            paragraph_text = ' '.join(current_paragraph)
            elements.append(self.create_paragraph(paragraph_text))
        
        return elements
    
    def create_paragraph(self, text):
        """创建段落，处理行内格式"""
        # 处理行内代码
        text = re.sub(r'`([^`]+)`', r'<font name="Courier" color="#E74C3C" backcolor="#FDF2F2">\1</font>', text)
        
        # 处理加粗（**text**）
        text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
        
        # 处理斜体（*text*）
        text = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', text)
        
        return Paragraph(text, self.styles['WeChatBody'])
    
    def create_cover_page(self, title, author, meta_info=None):
        """创建精美的封面页"""
        cover_elements = []
        
        # 顶部留白
        cover_elements.append(Spacer(1, 6*cm))
        
        # 文章标题
        cover_elements.append(Paragraph(title, self.styles['WeChatCoverTitle']))
        cover_elements.append(Spacer(1, 3*cm))
        
        # 作者信息
        cover_elements.append(Paragraph(f"作者：{author}", self.styles['WeChatCoverAuthor']))
        cover_elements.append(Spacer(1, 2*cm))
        
        # 元信息
        if meta_info:
            for key, value in meta_info.items():
                if value:
                    cover_elements.append(Paragraph(f"{key}：{value}", self.styles['WeChatMetaInfo']))
        
        # 底部装饰性分隔线
        cover_elements.append(Spacer(1, 4*cm))
        cover_elements.append(HRFlowable(
            width="60%",
            thickness=2,
            color=colors.HexColor('#3498DB'),
            spaceBefore=20,
            spaceAfter=20
        ))
        
        # 生成信息
        generate_time = datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M')
        cover_elements.append(Spacer(1, 1.5*cm))
        cover_elements.append(Paragraph("微信公众号文章收藏", self.styles['WeChatMetaInfo']))
        cover_elements.append(Paragraph(f"生成时间：{generate_time}", self.styles['WeChatMetaInfo']))
        
        return cover_elements
    
    def create_footer(self, url, article_id):
        """创建页脚"""
        footer_elements = []
        
        # 分隔线
        footer_elements.append(HRFlowable(
            width="90%",
            thickness=1,
            color=colors.HexColor('#E6E6E6'),
            spaceBefore=30,
            spaceAfter=20
        ))
        
        # 页脚内容
        footer_text = f"""
        <b>原文链接</b>：{url}<br/>
        <b>文章ID</b>：{article_id}<br/>
        <br/>
        <font size="9">本PDF由小邹AI助手自动生成<br/>
        模仿微信公众号排版样式，优化阅读体验<br/>
        仅供个人学习使用，请尊重原作者版权</font>
        """
        
        footer_elements.append(Paragraph(footer_text, self.styles['WeChatFooter']))
        
        return footer_elements
    
    def add_header_footer(self, canvas, doc):
        """添加页眉页脚"""
        canvas.saveState()
        
        # 页眉
        header_text = f"{doc.article_author} - 微信公众号文章"
        canvas.setFont(self.main_font, 10)
        canvas.setFillColor(colors.HexColor('#999999'))
        canvas.drawCentredString(self.page_width / 2, self.page_height - 1.5*cm, header_text)
        
        # 页脚页码
        page_num = canvas.getPageNumber()
        footer_text = f"第 {page_num} 页"
        canvas.setFont(self.main_font, 9)
        canvas.setFillColor(colors.HexColor('#999999'))
        canvas.drawCentredString(self.page_width / 2, 1*cm, footer_text)
        
        # 底部装饰线
        canvas.setStrokeColor(colors.HexColor('#E6E6E6'))
        canvas.setLineWidth(0.5)
        canvas.line(2*cm, 1.5*cm, self.page_width - 2*cm, 1.5*cm)
        
        canvas.restoreState()
    
    def generate_pdf(self, article_data, output_path=None):
        """生成修复版微信公众号风格PDF"""
        # 准备数据
        title = article_data.get('title', '未命名文章')
        author = article_data.get('author', '未知作者')
        content = article_data.get('content', '')
        url = article_data.get('url', '')
        article_id = article_data.get('id', '')
        
        # 处理元信息
        meta_info = {}
        
        publish_date = article_data.get('publish_date', '')
        if publish_date:
            try:
                publish_date = datetime.datetime.fromisoformat(publish_date.replace('Z', '+00:00'))
                meta_info['发布时间'] = publish_date.strftime('%Y年%m月%d日 %H:%M')
            except:
                meta_info['发布时间'] = publish_date
        
        collect_date = article_data.get('save_date', '')
        if collect_date:
            try:
                collect_date = datetime.datetime.fromisoformat(collect_date.replace('Z', '+00:00'))
                meta_info['收录时间'] = collect_date.strftime('%Y年%m月%d日 %H:%M')
            except:
                meta_info['收录时间'] = collect_date
        
        word_count = article_data.get('word_count', 0)
        if word_count:
            meta_info['文章字数'] = f"{word_count}字"
        
        # 生成输出路径
        if output_path is None:
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_author = "".join(c for c in author if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{safe_author}_{safe_title}_{article_id}_fixed.pdf"
            # 使用相对路径
            output_path = Path(__file__).parent.parent / "data" / "wechat_articles" / "pdfs" / filename
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"📄 生成修复版微信公众号风格PDF: {output_path.name}")
        
        # 创建PDF文档
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=2.5*cm,
            leftMargin=2.5*cm,
            topMargin=3.5*cm,  # 为页眉留空间
            bottomMargin=3*cm   # 为页脚留空间
        )
        
        # 保存文章信息供页眉使用
        doc.article_author = author
        
        # 构建内容
        story = []
        
        # 封面页
        story.extend(self.create_cover_page(title, author, meta_info))
        story.append(PageBreak())
        
        # 文章内容
        print("📝 解析文章内容...")
        content_elements = self.parse_content(content)
        story.extend(content_elements)
        
        # 页脚
        story.extend(self.create_footer(url, article_id))
        
        # 生成PDF（带页眉页脚）
        try:
            doc.build(
                story,
                onFirstPage=self.add_header_footer,
                onLaterPages=self.add_header_footer
            )
            
            file_size = output_path.stat().st_size
            print(f"✅ 修复版微信公众号风格PDF生成成功: {output_path}")
            print(f"   文件大小: {file_size} 字节 ({file_size/1024:.1f} KB)")
            print(f"   使用字体: {self.main_font}")
            print(f"   样式特点:")
            print(f"     - 13px正文字体，1.38倍行距")
            print(f"     - 首行缩进2字符，两端对齐")
            print(f"     - 正确的段落分隔")
            print(f"     - 微信公众号标准配色")
            print(f"     - 带页眉页脚和页码")
            print(f"     - 精美封面页")
            
            return str(output_path)  # 转换为字符串
        except Exception as e:
            print(f"❌ PDF生成失败: {e}")
            import traceback
            traceback.print_exc()
            return None

def test():
    """测试函数"""
    generator = FixedWeChatPDFGenerator()
    
    test_article = {
        "id": "fixed_test",
        "title": "修复版排版测试文章",
        "author": "测试作者",
        "content": """# 修复版排版测试

这是一个测试文章，用于验证修复版的段落分隔功能。

## 段落测试

从第一个100万，到第一个1亿，不仅是数字的变化，更是思维模式、认知层次和行动方式的全面升级。财富积累需要时间和耐心，每个阶段都有其必要的积累过程。

不要急于求成，要稳扎稳打。很多人犯的错误是在只有1万的时候，就试图"赌"出第一个100万，这是非常荒谬的。

## 列表测试

- 项目一：专业技能提升
- 项目二：系统思维建立
- 项目三：资本运作学习

## 引用测试

> 财富积累需要时间和耐心，每个阶段都有其必要的积累过程。不要急于求成，要稳扎稳打。

## 总结

修复版应该确保：
1. 正确的段落分隔
2. 首行缩进2字符
3. 舒适的阅读间距
4. 完整的格式支持""",
        "url": "https://example.com/fixed_test",
        "publish_date": "2026-02-28T10:00:00",
        "save_date": "2026-02-28T21:00:00",
        "word_count": 300
    }
    
    pdf_path = generator.generate_pdf(test_article)
    if pdf_path:
        print(f"\n🎉 测试完成！")
        print(f"📄 文件位置: {pdf_path}")
        print(f"🔍 请用PDF查看器打开检查段落分隔效果")

if __name__ == "__main__":
    test()
