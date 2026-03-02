#!/bin/bash
# 稳定性测试脚本

echo "🧪 稳定性测试 - 微信公众号PDF生成器"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试服务器是否运行
check_server() {
    echo -n "🔍 检查服务器状态... "
    if curl -s http://localhost:5000/api/status > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 运行中${NC}"
        return 0
    else
        echo -e "${RED}✗ 未运行${NC}"
        return 1
    fi
}

# 启动测试服务器
start_test_server() {
    echo -e "${BLUE}🚀 启动测试服务器...${NC}"
    
    # 设置测试环境
    export DATA_DIR="test_data"
    export PORT=5999
    export DEBUG=true
    export MAX_FILES=10
    export MAX_FILE_SIZE=10485760  # 10MB
    
    # 清理旧数据
    rm -rf test_data 2>/dev/null
    mkdir -p test_data
    
    # 启动服务器（后台）
    python src/pdf_generator_stable.py > /tmp/stability_test.log 2>&1 &
    SERVER_PID=$!
    
    # 等待服务器启动
    echo -n "⏳ 等待服务器启动... "
    for i in {1..10}; do
        if curl -s http://localhost:5999/api/status > /dev/null 2>&1; then
            echo -e "${GREEN}✓ 就绪${NC}"
            return 0
        fi
        sleep 1
        echo -n "."
    done
    
    echo -e "${RED}✗ 启动失败${NC}"
    cat /tmp/stability_test.log
    return 1
}

# 测试API端点
test_api_endpoint() {
    local endpoint=$1
    local name=$2
    local expected_code=${3:-200}
    
    echo -n "🔍 测试: ${name}... "
    
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5999${endpoint}")
    
    if [ "$response_code" -eq "$expected_code" ]; then
        echo -e "${GREEN}✓ 通过 (${response_code})${NC}"
        return 0
    else
        echo -e "${RED}✗ 失败 (期望 ${expected_code}, 实际 ${response_code})${NC}"
        return 1
    fi
}

# 测试PDF生成
test_pdf_generation() {
    echo -e "${BLUE}📄 测试PDF生成稳定性...${NC}"
    
    # 测试不同类型的URL
    test_urls=(
        "https://mp.weixin.qq.com/s/stable-test-1"  # 正常URL
        "invalid-url"                               # 无效URL
        "https://nonexistent-domain-12345.com/test" # 不存在的域名
        "https://mp.weixin.qq.com/s/stable-test-2"  # 另一个正常URL（测试缓存）
    )
    
    success_count=0
    total_count=${#test_urls[@]}
    
    for url in "${test_urls[@]}"; do
        echo -n "🔗 测试URL: ${url:0:40}... "
        
        response=$(curl -s -X POST http://localhost:5999/api/generate \
            -H "Content-Type: application/json" \
            -d "{\"url\": \"$url\", \"custom_title\": \"稳定性测试 $(date +%s)\"}")
        
        if echo "$response" | grep -q '"success":true'; then
            echo -e "${GREEN}✓ 成功${NC}"
            success_count=$((success_count + 1))
            
            # 提取文件名并测试下载
            file_name=$(echo "$response" | grep -o '"file_name":"[^"]*"' | cut -d'"' -f4)
            if [ -n "$file_name" ]; then
                encoded_name=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$file_name'))")
                test_api_endpoint "/api/download/$encoded_name" "下载生成的文件" 200
            fi
        elif echo "$response" | grep -q '"success":false'; then
            echo -e "${YELLOW}⚠ 失败（预期内）${NC}"
            # 检查是否有合理的错误信息
            error_msg=$(echo "$response" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
            if [ -n "$error_msg" ]; then
                echo "   错误信息: ${error_msg:0:60}..."
            fi
        else
            echo -e "${RED}✗ 无效响应${NC}"
        fi
        
        # 短暂延迟
        sleep 1
    done
    
    success_rate=$((success_count * 100 / total_count))
    echo -e "${BLUE}📊 生成成功率: ${success_count}/${total_count} (${success_rate}%)${NC}"
    
    if [ $success_count -gt 0 ]; then
        return 0
    else
        return 1
    fi
}

# 测试缓存功能
test_cache_function() {
    echo -e "${BLUE}💾 测试缓存功能...${NC}"
    
    test_url="https://mp.weixin.qq.com/s/cache-test-$(date +%s)"
    
    echo -n "🔍 第一次请求（应该未命中缓存）... "
    response1=$(curl -s -X POST http://localhost:5999/api/generate \
        -H "Content-Type: application/json" \
        -d "{\"url\": \"$test_url\"}")
    
    cache_info1=$(echo "$response1" | grep -o '"from_cache":[^,]*' | cut -d':' -f2)
    if [ "$cache_info1" = "false" ]; then
        echo -e "${GREEN}✓ 未命中缓存${NC}"
    else
        echo -e "${RED}✗ 预期未命中缓存${NC}"
    fi
    
    sleep 1
    
    echo -n "🔍 第二次请求（应该命中缓存）... "
    response2=$(curl -s -X POST http://localhost:5999/api/generate \
        -H "Content-Type: application/json" \
        -d "{\"url\": \"$test_url\"}")
    
    cache_info2=$(echo "$response2" | grep -o '"from_cache":[^,]*' | cut -d':' -f2)
    if [ "$cache_info2" = "true" ]; then
        echo -e "${GREEN}✓ 命中缓存${NC}"
        return 0
    else
        echo -e "${RED}✗ 预期命中缓存${NC}"
        return 1
    fi
}

# 测试错误恢复
test_error_recovery() {
    echo -e "${BLUE}🛡️ 测试错误恢复...${NC}"
    
    # 测试无效URL
    echo -n "🔍 测试无效URL处理... "
    response=$(curl -s -X POST http://localhost:5999/api/generate \
        -H "Content-Type: application/json" \
        -d "{\"url\": \"not-a-valid-url\"}")
    
    if echo "$response" | grep -q '"success":false'; then
        echo -e "${GREEN}✓ 正确处理无效URL${NC}"
        
        # 检查是否有错误信息
        error_msg=$(echo "$response" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
        if [ -n "$error_msg" ]; then
            echo "   错误信息: ${error_msg}"
        fi
        return 0
    else
        echo -e "${RED}✗ 未正确处理无效URL${NC}"
        return 1
    fi
}

# 测试系统状态监控
test_system_monitoring() {
    echo -e "${BLUE}📈 测试系统监控...${NC}"
    
    echo -n "🔍 获取系统状态... "
    response=$(curl -s http://localhost:5999/api/status)
    
    if echo "$response" | grep -q '"success":true'; then
        echo -e "${GREEN}✓ 状态API正常${NC}"
        
        # 提取关键指标
        metrics=("success_rate" "cache_rate" "total_requests" "pdf_count")
        for metric in "${metrics[@]}"; do
            value=$(echo "$response" | grep -o "\"$metric\":[^,]*" | cut -d':' -f2)
            echo "   ${metric}: ${value}"
        done
        return 0
    else
        echo -e "${RED}✗ 状态API异常${NC}"
        return 1
    fi
}

# 主测试流程
main() {
    echo -e "${BLUE}=== 稳定性测试开始 ===${NC}"
    
    # 启动测试服务器
    if ! start_test_server; then
        echo -e "${RED}❌ 测试服务器启动失败${NC}"
        exit 1
    fi
    
    # 测试基本API
    echo -e "${BLUE}🔧 测试基本API端点...${NC}"
    test_api_endpoint "/" "Web界面" 200
    test_api_endpoint "/api/status" "状态API" 200
    test_api_endpoint "/api/list" "文件列表API" 200
    
    # 运行各项测试
    test_pdf_generation
    test_cache_function
    test_error_recovery
    test_system_monitoring
    
    # 清理
    echo -e "${BLUE}🧹 清理测试环境...${NC}"
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
    rm -rf test_data 2>/dev/null
    
    echo -e "${BLUE}=== 稳定性测试完成 ===${NC}"
    
    # 显示测试日志摘要
    if [ -f "/tmp/stability_test.log" ]; then
        echo -e "${YELLOW}📋 测试日志摘要:${NC}"
        grep -E "(ERROR|WARNING|INFO.*成功|INFO.*失败)" /tmp/stability_test.log | tail -10
    fi
    
    echo -e "${GREEN}✅ 稳定性测试执行完毕${NC}"
}

# 运行测试
main "$@"