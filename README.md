# 📄 微信公众号文章PDF生成器

一个将微信公众号文章转换为精美PDF的Web应用。

## ✨ 功能特点

### 🎯 稳定版（推荐）
- 💪 **智能重试机制**：3次自动重试，提高成功率
- 🔄 **多策略解析**：微信公众号+通用结构识别
- 💾 **本地缓存**：24小时缓存，减少重复请求
- 🛡️ **错误恢复**：优雅降级，自动生成备用内容
- 📊 **详细监控**：成功率、响应时间等实时统计
- ⚡ **请求限流**：防止滥用，保护系统稳定性

### 🌐 Web界面
- 🎨 **现代化设计**：响应式布局，美观实用
- 📱 **移动端适配**：完美支持手机、平板、电脑
- ⚡ **实时更新**：自动刷新文件列表和状态
- 🎯 **易于使用**：简洁直观的操作流程

### 📄 PDF生成
- 🖋️ **高质量排版**：模仿微信公众号原版样式
- 📏 **标准字体**：16px正文字体，1.75倍行距
- 📐 **专业格式**：首行缩进2字符，两端对齐
- 🎨 **精美设计**：封面页、页眉页脚、标准配色

### 🔄 文章处理
- 🤖 **自动抓取**：智能获取文章内容
- 🔍 **内容解析**：多策略HTML解析
- 🧹 **智能清理**：移除广告、脚本等无关内容
- 📝 **格式优化**：自动整理段落和格式

### 📥 文件管理
- 📁 **中文支持**：完美处理中文文件名
- ⬇️ **一键下载**：方便的文件下载功能
- 📊 **文件统计**：大小、时间等信息展示
- 🔄 **自动排序**：按时间倒序排列文件

## 🚀 快速开始

### 环境要求
- Python 3.8+
- 支持中文字体的系统

### 安装步骤

#### 选项1：使用稳定版（推荐）
```bash
# 克隆仓库
git clone https://github.com/yourusername/wechat-pdf-generator.git
cd wechat-pdf-generator

# 启动稳定版
./start_stable.sh

# 或者手动启动
python src/pdf_generator_stable.py
```

#### 选项2：使用专业版
```bash
# 克隆仓库
git clone https://github.com/yourusername/wechat-pdf-generator.git
cd wechat-pdf-generator

# 启动专业版
./start_pro.sh

# 或者手动启动
python src/app_pro.py
```

#### 选项3：使用基础版
```bash
# 克隆仓库
git clone https://github.com/yourusername/wechat-pdf-generator.git
cd wechat-pdf-generator

# 启动基础版
python src/pdf_generator_web.py
```

4. **访问应用**
打开浏览器访问：http://localhost:5000

## 📖 使用方法

### 1. 通过Web界面
1. 访问 http://localhost:5000
2. 输入微信公众号文章URL
3. （可选）输入自定义标题
4. 点击"生成PDF"按钮
5. 下载生成的PDF文件

### 2. 通过API
```bash
# 生成PDF
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"url": "文章URL"}'

# 列出文件
curl http://localhost:5000/api/list

# 下载文件
curl -O http://localhost:5000/api/download/文件名.pdf
```

## 🏗️ 项目结构

```
wechat-pdf-generator/
├── src/                    # 源代码
│   ├── pdf_generator_web.py    # Web应用主文件
│   ├── pdf_wechat_fixed.py     # PDF生成器核心
│   └── process_wechat_fixed.py # 文章处理器
├── static/                 # 静态文件
├── templates/              # 模板文件
├── data/                   # 数据文件
├── scripts/                # 脚本文件
├── docs/                   # 文档
├── requirements.txt        # Python依赖
├── README.md              # 项目说明
└── LICENSE                # 许可证
```

## 🔧 配置选项

### 修改端口
编辑 `src/pdf_generator_web.py`：
```python
app.run(host='0.0.0.0', port=8080, debug=False)  # 修改端口
```

### 修改数据目录
编辑 `src/pdf_generator_web.py`：
```python
self.base_dir = Path(__file__).parent.parent / "data"  # 修改数据目录
```

## 🌐 部署选项

### 1. 本地部署
```bash
python src/pdf_generator_web.py
```

### 2. Docker部署
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "src/pdf_generator_web.py"]
```

### 3. 云服务器部署
- **VPS**：使用systemd服务
- **Heroku**：添加Procfile
- **Railway**：直接部署

## 📝 注意事项

1. **字体要求**：需要系统中安装中文字体（微软雅黑、宋体等）
2. **网络要求**：需要网络连接来抓取文章
3. **存储空间**：PDF文件会保存在本地
4. **微信公众号限制**：部分文章需要登录才能访问

## 🤝 贡献指南

1. Fork本仓库
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- ReportLab：PDF生成库
- Flask：Web框架
- 微信公众号：文章来源

## 📞 支持

如有问题，请：
1. 查看 [Issues](https://github.com/yourusername/wechat-pdf-generator/issues)
2. 提交新的Issue
3. 发送邮件到 your.email@example.com
