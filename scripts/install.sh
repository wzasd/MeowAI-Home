#!/bin/bash
# MeowAI Home 一键安装脚本
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🐱 MeowAI Home 安装程序"
echo "========================"
echo ""

ERRORS=0

# --- Check Python ---
echo "🔍 检查依赖..."

# Find a suitable Python
PYTHON=""
for py in python3.12 python3.11 python3.10 python3; do
    if command -v $py &>/dev/null; then
        if $py -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
            PYTHON=$py
            break
        fi
    fi
done

if [ -n "$PYTHON" ]; then
    PY_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
    echo -e "  ${GREEN}✓${NC} Python $PY_VERSION ($PYTHON)"
else
    echo -e "  ${RED}✗${NC} Python >= 3.10 not found"
    echo "    → brew install python@3.11"
    ERRORS=$((ERRORS + 1))
fi

# --- Check Node.js ---
HAS_NODE=false
if command -v node &>/dev/null; then
    NODE_VERSION=$(node -v)
    echo -e "  ${GREEN}✓${NC} Node.js $NODE_VERSION"
    HAS_NODE=true
else
    echo -e "  ${YELLOW}⚠${NC} Node.js not found (Web UI 不可用)"
    echo "    → brew install node"
fi

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo -e "${RED}请先安装上述必须依赖后重新运行${NC}"
    exit 1
fi

# --- Install Python deps ---
echo ""
echo "📦 安装 Python 依赖..."
$PYTHON -m pip install -e ".[dev]" --quiet 2>/dev/null
echo -e "  ${GREEN}✓${NC} Python 依赖已安装"

# --- Install frontend deps ---
if [ "$HAS_NODE" = true ] && [ -d "web" ]; then
    echo "📦 安装前端依赖..."
    cd web && npm install --silent 2>/dev/null && cd ..
    echo -e "  ${GREEN}✓${NC} 前端依赖已安装"
fi

# --- Setup environment ---
mkdir -p data
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "  ${GREEN}✓${NC} 已创建 .env"
fi

# --- Check CLI tools ---
echo ""
echo "🔍 检查 AI CLI 工具:"
for tool in claude codex gemini opencode; do
    if command -v $tool &>/dev/null; then
        VER=$($tool --version 2>/dev/null | head -1)
        echo -e "  ${GREEN}✓${NC} $tool: ${VER:-installed}"
    else
        echo -e "  ${YELLOW}-${NC} $tool: 未安装"
    fi
done

# --- Done ---
echo ""
echo -e "${GREEN}✅ 安装完成！${NC}"
echo ""
echo "  启动服务:  meowai start"
echo "  环境检查:  meowai check"
echo "  CLI 对话:  meowai chat"
echo ""
