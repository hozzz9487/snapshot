# 專案快照分析工具 (Project Snapshot Tool)

<p align="left">
  <a href="README.md"><strong>English</strong></a> | 
  <a href="README.zh-TW.md"><strong>繁體中文</strong></a>
</p>

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

這是一款專為 Android 與 iOS 專案設計的技術快照工具，能自動生成詳盡的專案報告，幫助開發者或 AI 助手快速掌握專案架構、邏輯流程、相依套件及編譯配置。

---

## 🚀 功能亮點

-   **多平台分析**：全面支援 Android (Java/Kotlin, Gradle) 與 iOS (Swift, Xcode, CocoaPods, SPM)。
-   **隱私安全**：內建敏感資料隔離機制，透過 `.gitignore`、`.cursorignore` 與外部設定檔保護您的路徑與金鑰。
-   **相依套件清單**：自動解析並列出依賴管理工具中的所有第三方套件。
-   **Xcode 設定深度分析**：提取並格式化複雜的 Xcode 編譯設定與 Target 配置。
-   **清晰結構化報告**：生成過濾後的目錄樹狀圖與結構化的 Markdown 報告。

---

## 📦 快速上手

### 前置需求
-   Python 3.8+
-   macOS (iOS Xcode 分析功能需在 macOS 環境下執行)

### 安裝步驟
1.  **複製專案**:
    ```bash
    git clone https://github.com/hozzz9487/snapshot.git
    cd snapshot
    ```
2.  **環境設定**:
    ```bash
    # 建立虛擬環境（建議）
    python3 -m venv .
    source bin/activate
    # 安裝必要套件
    pip install -r requirements.txt
    ```

---

## ⚙️ 專案配置

為了保護隱私，專案路徑存放在本機的 `config.json` 中，此檔案不會被 Git 追蹤。

1.  **初始化設定**:
    ```bash
    cp config.example.json config.json
    ```
2.  **編輯設定**:
    編輯 `config.json` 加入您的專案路徑：
    ```json
    {
        "projects": {
            "MyAwesomeApp": {
                "name": "My Awesome App",
                "android_path": "~/Developer/Android/MyApp",
                "ios_path": "~/Developer/iOS/MyApp"
            }
        },
        "output_base_dir": "~/Documents/snapshot_reports"
    }
    ```

---

## 🛠 使用方法

您可以透過指令腳本或直接使用 Python 運行：

### 方式一：使用腳本（建議）
```bash
./script/snapshot.command
```

### 方式二：直接運行 Python
```bash
python3 py/snapshot.py
```

依照提示選擇專案與平台，報告將存儲於您設定的 `output_base_dir` 目錄中。

---

## 📂 專案架構

-   `py/`: 核心邏輯與分析引擎。
-   `script/`: 便捷運行腳本。
-   `config.example.json`: 設定檔範本。
-   `.gitignore` / `.cursorignore`: 預設的安全過濾配置。

---

## 📄 授權條款

本專案採用 [MIT 授權條款](LICENSE)。
