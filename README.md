# Project Snapshot Tool

A powerful utility designed to generate comprehensive technical snapshots of Android and iOS projects. It helps developers and AI assistants quickly understand project structures, code logic, dependencies, and build configurations.

## Features

- **Multi-Platform Support**: Detailed analysis for both Android (Java, Kotlin, Gradle) and iOS (Swift, Xcode, CocoaPods, SPM).
- **Security First**: Automatically isolates sensitive data, personal file paths, and secrets using `.gitignore`, `.cursorignore`, and external configuration files.
- **Dependency Analysis**: Parses Gradle, CocoaPods, and Swift Package Manager files to list all third-party libraries.
- **Xcode Settings Analysis**: Deep dive into Xcode build configurations and target settings.
- **Directory Mapping**: Generates clean, filtered directory trees of your projects.
- **Markdown Output**: Reports are generated in clean Markdown format for easy reading or sharing.

## Prerequisites

- Python 3.x
- macOS (recommended for iOS analysis)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/hozzz9487/snapshot.git
   cd snapshot
   ```

2. **Set up a virtual environment (optional but recommended)**:
   ```bash
   python3 -m venv .
   source bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

This tool uses an external configuration file to keep your local paths private.

1. **Create your config file**:
   ```bash
   cp config.example.json config.json
   ```

2. **Edit `config.json`**:
   Add your projects and define the output directory.
   ```json
   {
       "projects": {
           "MyMobileApp": {
               "name": "My Mobile App Project",
               "android_path": "~/Developer/Android/MyApp",
               "ios_path": "~/Developer/iOS/MyApp"
           }
       },
       "output_base_dir": "~/Documents/snapshot_reports"
   }
   ```

## Usage

You can run the tool using the provided script or directly via Python:

### Using the script
```bash
./script/snapshot.command
```

### Using Python directly
```bash
python3 py/snapshot.py
```

Follow the interactive prompts to select the project and the platform you want to snapshot.

## Project Structure

- `py/`: Core Python script logic.
- `script/`: Shell scripts for easy execution.
- `config.example.json`: Template for project configuration.
- `.gitignore` / `.cursorignore`: Pre-configured to protect your privacy.

## License

[MIT License](LICENSE) (or specify your license)
