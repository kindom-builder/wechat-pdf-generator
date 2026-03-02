#!/bin/bash
# 启动稳定版微信公众号PDF生成器

echo "🚀 启动稳定版微信公众号PDF生成器..."
echo "💪 特性: 智能重试 + 多策略解析 + 缓存优化 + 错误恢复"
echo "======================================================"

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
pip install -q -r requirements.txt

# 创建数据目录
mkdir -p data

# 设置环境变量
export DATA_DIR="data"
export PORT=${PORT:-5000}
export DEBUG=${DEBUG:-false}
export MAX_FILES=${MAX_FILES:-1000}
export MAX_FILE_SIZE=${MAX_FILE_SIZE:-52428800}  # 50MB

echo ""
echo "📁 工作目录: $(pwd)"
echo "🌐 服务地址: http://localhost:${PORT}"
echo ""
echo "📊 系统配置:"
echo "  • 数据目录: ${DATA_DIR}"
echo "  • 最大文件数: ${MAX_FILES}"
echo "  • 最大文件大小: $((${MAX_FILE_SIZE}/1024/1024))MB"
echo "  • 调试模式: ${DEBUG}"
echo ""
echo "🔧 稳定性配置:"
echo "  • 智能重试: 3次自动重试"
echo "  • 请求缓存: 24小时本地缓存"
echo "  • 多策略解析: 微信公众号+通用结构"
echo "  • 错误恢复: 优雅降级处理"
echo "  • 请求限流: 防止滥用保护"
echo ""
echo "📄 可用功能:"
echo "  1. Web界面: http://localhost:${PORT}"
echo "  2. API状态: http://localhost:${PORT}/api/status"
echo "  3. 生成PDF: POST http://localhost:${PORT}/api/generate"
echo "  4. 列出文件: GET http://localhost:${PORT}/api/list"
echo "  5. 下载PDF: GET http://localhost:${PORT}/api/download/<文件名>"
echo "  6. 清理缓存: POST http://localhost:${PORT}/api/clear_cache"
echo ""
echo "📈 监控指标:"
echo "  • 抓取成功率"
echo "  • 生成成功率"
echo "  • 缓存命中率"
echo "  • 平均响应时间"
echo "  • 系统负载"
echo ""
echo "💡 使用提示:"
echo "  • 按 Ctrl+C 停止服务"
echo "  • 支持中文文件名下载"
echo "  • 自动刷新文件列表"
echo "  • 详细错误报告"
echo "  • 实时状态监控"
echo ""
echo "🛡️ 稳定性保证:"
echo "  • 即使抓取失败也会生成有用的PDF"
echo "  • 自动重试机制提高成功率"
echo "  • 缓存减少重复请求"
echo "  • 限流保护系统稳定性"
echo ""

# 启动服务
python src/pdf_generator_stable.py