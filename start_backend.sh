#!/bin/bash

# 企業 AI 助理 - 後端啟動腳本
# 使用方法: ./start_backend.sh

set -e

echo "=========================================="
echo "企業 AI 助理 - 後端啟動"
echo "=========================================="
echo ""

# 檢查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 錯誤：找不到 Python 3"
    echo "請先安裝 Python 3.8 或更新版本"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python 版本: $PYTHON_VERSION"

# 進入 backend 目錄
cd "$(dirname "$0")/backend" || exit 1
echo "✅ 進入目錄: $(pwd)"

# 檢查 .env 檔案
if [ ! -f ".env" ]; then
    echo "⚠️  警告：.env 檔案不存在"
    echo "   正在複製 .env.example → .env"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ .env 已建立（請檢查並修改配置）"
    else
        echo "❌ 錯誤：找不到 .env.example"
        exit 1
    fi
fi

# 檢查虛擬環境
if [ ! -d "venv" ]; then
    echo "⚠️  虛擬環境不存在，正在建立..."
    python3 -m venv venv
    echo "✅ 虛擬環境已建立"
fi

# 啟動虛擬環境
echo "✅ 啟動虛擬環境..."
source venv/bin/activate

# 安裝依賴
if [ ! -f "requirements.txt" ]; then
    echo "❌ 錯誤：找不到 requirements.txt"
    exit 1
fi

echo "📦 檢查依賴..."
pip install -q -r requirements.txt
echo "✅ 依賴已安裝"

# 檢查 JWT_SECRET
if ! grep -q "JWT_SECRET" .env || grep "JWT_SECRET=" .env | grep -q "your-secret"; then
    echo ""
    echo "⚠️  警告：JWT_SECRET 未設定或使用預設值"
    echo "   建議：編輯 .env 檔案，設定強密鑰"
fi

# 檢查 DEFAULT_ADMIN_PASSWORD
if grep -q "DEFAULT_ADMIN_PASSWORD=admin12345" .env 2>/dev/null || ! grep -q "DEFAULT_ADMIN_PASSWORD" .env; then
    echo "⚠️  警告：使用預設 admin 密碼 (admin12345)"
    echo "   建議：編輯 .env 檔案，設定 DEFAULT_ADMIN_PASSWORD 為強密碼"
fi

echo ""
echo "=========================================="
echo "✅ 後端啟動中..."
echo "=========================================="
echo ""

# 啟動應用
python main.py
