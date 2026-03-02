#!/bin/bash
# 部署脚本

echo "🚀 部署微信公众号PDF生成器..."

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 需要Python 3.8+"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "🔧 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "📦 安装依赖..."
pip install -r requirements.txt

# 创建数据目录
mkdir -p data

echo "✅ 部署完成！"
echo "📝 启动命令:"
echo "   source venv/bin/activate"
echo "   python src/pdf_generator_web.py"
echo "🌐 访问地址: http://localhost:5000"
