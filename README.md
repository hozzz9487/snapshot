# Project Snapshot Tool

<p align="left">
  <a href="README.md"><strong>English</strong></a> | 
  <a href="README.zh-TW.md"><strong>繁體中文</strong></a>
</p>

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A specialized utility designed to "de-noise" and condense Android/iOS projects into optimized technical snapshots. It empowers developers and AI assistants to rapidly grasp project DNA—architectures, logic flows, and configurations—within a single, context-efficient report.

---

## 🎯 Why Snapshot?

Modern AI models have context limits. Feeding raw source code often introduces "noise" (boilerplate, build artifacts, comments) that wastes tokens and confuses reasoning. 

**Snapshot Tool** acts as a digital lens:
- **Noise Reduction**: Strips away non-essential code while preserving structural logic.
- **Context Optimization**: Merges hundreds of files into a single, structured Markdown report.
- **AI-Ready**: Designed specifically for prompts in assistants like Claude, ChatGPT, and Cursor.


---

## 🚀 Features

-   **Multi-Platform Analysis**: Full support for Android (Java/Kotlin, Gradle) and iOS (Swift, Xcode, CocoaPods, SPM).
-   **Interactive Management**: Built-in CLI menu to add, remove, or edit projects. Supports selecting paths via macOS native Finder dialog.
-   **Smart Path Detection**: Automatically scans subdirectories for project roots and intelligently predicts iOS paths from Android paths (supports sibling/cousin structures).
-   **Security & Privacy**: Built-in isolation for sensitive data via `.gitignore` and `.cursorignore`.
-   **Xcode Settings Deep Dive**: Formats complex build settings into human/AI-readable tables.
-   **Structured Documentation**: Generates filtered directory trees and condensed code summaries.


---

## 📦 Getting Started

### Prerequisites
-   Python 3.8+
-   macOS (Required for iOS Xcode analysis and Finder integration)

### Installation
1.  **Clone the project**:
    ```bash
    git clone https://github.com/hozzz9487/snapshot.git
    cd snapshot
    ```

---

## ⚙️ Configuration (Zero Config)

**No need to manually edit config files!**

When you run the tool for the first time, if `config.json` is missing, it will automatically launch an **Interactive Setup Mode** to guide you through adding your first project.

You can still manage configuration manually if you prefer:
-   Config location: `config.json` (at project root, auto-generated).
-   Privacy: This file is ignored by Git by default.

---

## 🛠 Usage

Run the interactive tool via script or Python:

### Option 1: Using the script (Recommended)
This script automatically creates a virtual environment (`.venv`) and installs dependencies for you.

```bash
./script/snapshot.command
```

### Option 2: Manual Python Execution
If you prefer to manage the environment manually:

```bash
# 1. Create and activate venv
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the tool
python3 py/snapshot.py
```

### Operations
Once in the main menu, you can:
1.  **Enter a number**: Run snapshot analysis for a specific project.
2.  **Enter `A`**: Run analysis for **All** configured projects.
3.  **Enter `M`**: Enter **Management Mode** to add, remove, or edit projects.

Reports will be saved to your defined `output_base_dir` (default: `~/Documents/snapshot_reports`).

---

## 📂 Project Structure

-   `py/`: Core Python logic and analysis engines.
-   `script/`: Helper scripts for convenience.
-   `config.example.json`: Configuration template.
-   `.gitignore` / `.cursorignore`: Pre-configured security filters.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
