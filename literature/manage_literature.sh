#!/bin/bash

# 中国食物GI值文献库管理脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/literature_manager.py"

echo "=========================================="
echo "  中国食物GI值文献库管理系统"
echo "=========================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查依赖
echo "检查Python依赖..."
python3 -c "import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "安装requests库..."
    pip3 install requests
fi

# 运行文献库管理器
cd "$SCRIPT_DIR"
python3 "$PYTHON_SCRIPT"

echo ""
echo "=========================================="
echo "  文献库结构"
echo "=========================================="
echo "文献库根目录: $SCRIPT_DIR"
echo ""
echo "目录结构:"
echo "├── literature_manager.py    # 主管理脚本"
echo "├── manage_literature.sh     # 管理脚本"
echo "├── pdfs/                    # PDF文件目录"
echo "├── summaries/               # 文献摘要目录"
echo "├── metadata/                # 文献元数据目录"
echo "└── index/                   # 索引目录"
echo ""
echo "使用方法:"
echo "1. 运行 ./manage_literature.sh 初始化文献库"
echo "2. 查看 summaries/ 目录下的文献摘要"
echo "3. 手动下载PDF文件到 pdfs/ 目录"
echo "4. 使用文献进行研究和参考"
echo ""
echo "注意: 由于版权限制，PDF文件需要手动下载"
echo "=========================================="