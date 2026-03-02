#!/bin/bash
# GitHub仓库设置脚本

echo "🔧 设置GitHub仓库..."

# 进入项目目录
cd "$(dirname "$0")/.."

# 初始化Git仓库
if [ ! -d ".git" ]; then
    echo "📦 初始化Git仓库..."
    git init
fi

# 添加所有文件
echo "📄 添加文件到Git..."
git add .

# 提交更改
echo "💾 提交更改..."
git commit -m "feat: 初始提交 - 微信公众号PDF生成器

功能特点：
- Web界面生成PDF
- 支持微信公众号文章
- 精美排版模仿原版
- 支持中文文件名下载
- Docker部署支持"

echo ""
echo "✅ Git仓库设置完成！"
echo ""
echo "📋 下一步操作："
echo "1. 在GitHub创建新仓库：https://github.com/new"
echo "2. 仓库名：wechat-pdf-generator"
echo "3. 描述：微信公众号文章转PDF工具"
echo "4. 选择公开仓库"
echo "5. 不要初始化README（我们已经有了）"
echo ""
echo "🔗 然后运行以下命令："
echo "git remote add origin https://github.com/YOUR_USERNAME/wechat-pdf-generator.git"
echo "git branch -M main"
echo "git push -u origin main"
echo ""
echo "💡 将 YOUR_USERNAME 替换为你的GitHub用户名"