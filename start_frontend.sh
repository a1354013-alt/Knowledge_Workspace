#!/bin/bash
echo "🚀 啟動企業 AI 助理前端..."
cd frontend-vue

# 【重要】檢查 package-lock.json 是否變更
DEPS_HASH_FILE=".npm_deps_hash"
CURRENT_HASH=""

if [ -f "package-lock.json" ]; then
    CURRENT_HASH=$(md5sum package-lock.json | awk '{print $1}')
fi

# 比較 hash，只在變更時重裝
if [ ! -f "$DEPS_HASH_FILE" ] || [ "$CURRENT_HASH" != "$(cat $DEPS_HASH_FILE 2>/dev/null)" ]; then
    echo "📦 依賴有變更，執行 npm install..."
    npm install
    echo "$CURRENT_HASH" > "$DEPS_HASH_FILE"
else
    echo "✅ 依賴無變更，跳過 npm install"
fi

npm run dev
