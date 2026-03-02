#!/bin/bash
# 启动微信公众号PDF生成器专业版

echo "🚀 启动微信公众号PDF生成器专业版..."

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
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📦 安装依赖..."
pip install -r requirements.txt

# 创建数据目录
mkdir -p data

# 设置环境变量
export DATA_DIR="data"
export PORT=${PORT:-5000}
export DEBUG=${DEBUG:-false}
export MAX_FILES=${MAX_FILES:-1000}
export MAX_FILE_SIZE=${MAX_FILE_SIZE:-52428800}  # 50MB

echo "📁 工作目录: $(pwd)"
echo "🌐 服务地址: http://localhost:${PORT}"
echo "📊 系统配置:"
echo "  • 数据目录: ${DATA_DIR}"
echo "  • 最大文件数: ${MAX_FILES}"
echo "  • 最大文件大小: $((${MAX_FILE_SIZE}/1024/1024))MB"
echo "  • 调试模式: ${DEBUG}"
echo ""
echo "📄 可用功能:"
echo "  1. Web界面: http://localhost:${PORT}"
echo "  2. API状态: http://localhost:${PORT}/api/status"
echo "  3. 生成PDF: POST http://localhost:${PORT}/api/generate"
echo "  4. 列出文件: GET http://localhost:${PORT}/api/list"
echo "  5. 下载PDF: GET http://localhost:${PORT}/api/download/<文件名>"
echo ""
echo "💡 提示:"
echo "  • 按 Ctrl+C 停止服务"
echo "  • 支持中文文件名下载"
echo "  • 自动刷新文件列表"
echo "  • 有限流保护"
echo ""

# 启动服务
python src/app_pro.py