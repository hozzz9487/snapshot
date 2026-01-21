# Project Snapshot Tool | 專案快照分析工具

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A specialized utility designed to generate comprehensive technical snapshots of Android and iOS projects. It empowers developers and AI assistants to rapidly grasp project architectures, logic flows, dependencies, and build configurations.

這是一款專為 Android 與 iOS 專案設計的技術快照工具，能自動生成詳盡的專案報告，幫助開發者或 AI 助手快速掌握專案架構、邏輯流程、相依套件及編譯配置。

---

## 🚀 Features | 功能亮點

-   **Multi-Platform Analysis**: Full support for Android (Java/Kotlin, Gradle) and iOS (Swift, Xcode, CocoaPods, SPM).
    *   **多平台分析**：全面支援 Android (Java/Kotlin, Gradle) 與 iOS (Swift, Xcode, CocoaPods, SPM)。
-   **Security & Privacy**: Built-in isolation for sensitive data, paths, and secrets via `.gitignore`, `.cursorignore`, and external configs.
    *   **隱私安全**：內建敏感資料隔離機制，透過 `.gitignore`、`.cursorignore` 與外部設定檔保護您的路徑與金鑰。
-   **Dependency Mapping**: Automatically parses and lists all third-party libraries from dependency managers.
    *   **相依套件清單**：自動解析並列出依賴管理工具中的所有第三方套件。
-   **Xcode Settings Deep Dive**: Extracts and formats complex Xcode build settings and target configurations.
    *   **Xcode 設定深度分析**：提取並格式化複雜的 Xcode 編譯設定與 Target 配置。
-   **Clean Visualizations**: Generates filtered directory trees and structured Markdown reports.
    *   **清晰結構化報告**：生成過濾後的目錄樹狀圖與結構化的 Markdown 報告。

---

## 📦 Getting Started | 快速上手

### Prerequisites | 前置需求
-   Python 3.8+
-   macOS (Required for iOS Xcode analysis | iOS Xcode 分析需在 macOS 運行)

### Installation | 安裝步驟
1.  **Clone the project | 複製專案**:
    ```bash
    git clone https://github.com/hozzz9487/snapshot.git
    cd snapshot
    ```
2.  **Environment Setup | 環境設定**:
    ```bash
    # Setting up venv (Recommended) | 建立虛擬環境（建議）
    python3 -m venv .
    source bin/activate
    # Install dependencies | 安裝必要套件
    pip install -r requirements.txt
    ```

---

## ⚙️ Configuration | 專案配置

To protect your privacy, project paths are kept in a local `config.json` file which is ignored by Git.
為了保護隱私，專案路徑存放在本機的 `config.json` 中，此檔案不會被 Git 追蹤。

1.  **Initialize config | 初始化設定**:
    ```bash
    cp config.example.json config.json
    ```
2.  **Configure projects | 編輯設定**:
    Edit `config.json` to add your specific project paths:
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

## 🛠 Usage | 使用方法

Run the interactive tool via script or Python:
您可以透過指令腳本或直接使用 Python 運行：

### Option 1: Using the script (Recommended) | 方式一：使用腳本（建議）
```bash
./script/snapshot.command
```

### Option 2: Using Python directly | 方式二：直接運行 Python
```bash
python3 py/snapshot.py
```

Follow the prompts to select your project and platform. The reports will be saved to your defined `output_base_dir`.
依照提示選擇專案與平台，報告將存儲於您設定的 `output_base_dir` 目錄中。

---

## 📂 Project Structure | 專案架構

-   `py/`: Core Python logic and analysis engines. (核心邏輯與分析引擎)
-   `script/`: Helper scripts for convenience. (便捷運行腳本)
-   `config.example.json`: Configuration template. (設定檔範本)
-   `.gitignore` / `.cursorignore`: Pre-configured security filters. (預設的安全過濾配置)

---

## 📄 License | 授權條款

This project is licensed under the [MIT License](LICENSE).
本專案採用 [MIT 授權條款](LICENSE)。
