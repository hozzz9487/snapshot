# Project Snapshot Tool

<p align="left">
  <a href="README.md"><strong>English</strong></a> | 
  <a href="README.zh-TW.md"><strong>繁體中文</strong></a>
</p>

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A specialized utility designed to generate comprehensive technical snapshots of Android and iOS projects. It empowers developers and AI assistants to rapidly grasp project architectures, logic flows, dependencies, and build configurations.

---

## 🚀 Features

-   **Multi-Platform Analysis**: Full support for Android (Java/Kotlin, Gradle) and iOS (Swift, Xcode, CocoaPods, SPM).
-   **Security & Privacy**: Built-in isolation for sensitive data, paths, and secrets via `.gitignore`, `.cursorignore`, and external configs.
-   **Dependency Mapping**: Automatically parses and lists all third-party libraries from dependency managers.
-   **Xcode Settings Deep Dive**: Extracts and formats complex Xcode build settings and target configurations.
-   **Clean Visualizations**: Generates filtered directory trees and structured Markdown reports.

---

## 📦 Getting Started

### Prerequisites
-   Python 3.8+
-   macOS (Required for iOS Xcode analysis)

### Installation
1.  **Clone the project**:
    ```bash
    git clone https://github.com/hozzz9487/snapshot.git
    cd snapshot
    ```
2.  **Environment Setup**:
    ```bash
    # Setting up venv (Recommended)
    python3 -m venv .
    source bin/activate
    # Install dependencies
    pip install -r requirements.txt
    ```

---

## ⚙️ Configuration

To protect your privacy, project paths are kept in a local `config.json` file which is ignored by Git.

1.  **Initialize config**:
    ```bash
    cp config.example.json config.json
    ```
2.  **Edit your projects**:
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

## 🛠 Usage

Run the interactive tool via script or Python:

### Option 1: Using the script (Recommended)
```bash
./script/snapshot.command
```

### Option 2: Using Python directly
```bash
python3 py/snapshot.py
```

Follow the prompts to select your project and platform. The reports will be saved to your defined `output_base_dir`.

---

## 📂 Project Structure

-   `py/`: Core Python logic and analysis engines.
-   `script/`: Helper scripts for convenience.
-   `config.example.json`: Configuration template.
-   `.gitignore` / `.cursorignore`: Pre-configured security filters.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
