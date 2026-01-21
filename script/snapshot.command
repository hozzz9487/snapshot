#!/bin/bash

# 切換到 Python 檔案所在的目錄
cd "$(dirname "$0")"

# 啟動虛擬環境 (並非必要，但保留以防其他環境變數有用)
source ../bin/activate

# 安裝 Python 依賴 (如果尚未安裝)，直接指定 venv 中的 pip
../bin/pip install pbxproj docopt

# 執行 Python 腳本
python3 ../py/snapshot.py

# 結束虛擬環境
deactivate