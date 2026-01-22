#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Project root is one level up
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "正在檢查環境..."

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "錯誤：未安裝 Python 3。"
    echo "請從 python.org 或使用 brew 安裝 Python 3。"
    read -p "按 Enter 鍵離開..."
    exit 1
fi

# Virtual Environment Setup
VENV_DIR=".venv"
LEGACY_VENV_ACTIVATE="bin/activate"

if [ -f "$LEGACY_VENV_ACTIVATE" ]; then
    echo "使用現有的根目錄虛擬環境。"
    source "$LEGACY_VENV_ACTIVATE"
elif [ -f "$VENV_DIR/bin/activate" ]; then
    echo "使用 .venv 虛擬環境。"
    source "$VENV_DIR/bin/activate"
else
    echo "正在 .venv 建立新的虛擬環境..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "建立虛擬環境失敗。"
        read -p "按 Enter 鍵離開..."
        exit 1
    fi
    source "$VENV_DIR/bin/activate"
fi

# Upgrade pip quietly
pip install --upgrade pip > /dev/null 2>&1

# Install Dependencies
if [ -f "requirements.txt" ]; then
    echo "正在從 requirements.txt 安裝/更新依賴套件..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "安裝依賴套件失敗。"
        read -p "按 Enter 鍵離開..."
        exit 1
    fi
else
    echo "警告：找不到 requirements.txt。嘗試手動安裝核心套件..."
    pip install pbxproj docopt
fi

echo "環境準備完成。正在啟動 Snapshot 工具..."
echo "----------------------------------------"

# Run the Python script
python3 py/snapshot.py "$@"

echo "----------------------------------------"
read -p "按 Enter 鍵關閉視窗..."