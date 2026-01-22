#!/usr/bin/env python3
# multi_project_snapshot.py

import os
import re
import json
import pathlib
import subprocess # For calling osascript
from collections import defaultdict
import datetime
import plistlib # For Info.plist
import shutil # For copying parts of the android script logic for adaptation
import fnmatch # For gitignore pattern matching

# Imports for Xcode settings analysis
import sys # sys is used by one of the handlers in analyze_xcode_settings logging
from pbxproj import XcodeProject
# from pbxproj.pbxextensions import ProjectFiles # Not directly used in the merged logic, objects section uses get_objects_in_section
import logging
import logging.handlers

# --- Logger Setup for Xcode Settings Analysis (adapted from analyze_xcode_settings.py) ---
xcode_analyzer_logger = logging.getLogger("xcode_settings_analyzer") # Renamed logger
xcode_analyzer_logger.setLevel(logging.DEBUG)

xcode_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

log_dir = "xcode_analyzer_logs" # This will be created relative to where multi_project_snapshot.py is run
os.makedirs(log_dir, exist_ok=True)
log_filepath = os.path.join(log_dir, "xcode_analysis.log")

rotating_handler = logging.handlers.TimedRotatingFileHandler(
    filename=log_filepath,
    when="D", interval=1, backupCount=7, encoding='utf-8'
)
rotating_handler.setLevel(logging.DEBUG)
rotating_handler.setFormatter(xcode_formatter)
xcode_analyzer_logger.addHandler(rotating_handler)

stream_handler_xcode = logging.StreamHandler(sys.stdout) # Keep sys.stdout as per original
stream_handler_xcode.setLevel(logging.INFO) # Keep INFO level for console from this part
stream_handler_xcode.setFormatter(xcode_formatter)
xcode_analyzer_logger.addHandler(stream_handler_xcode)

xcode_analyzer_logger.debug("Xcode Settings Analyzer Logger initialized (DEBUG to file)")
xcode_analyzer_logger.info("Xcode 設定分析記錄器已初始化 (INFO 輸出至主控台與檔案)")
# --- End of Xcode Settings Logger Setup ---

# --- CONSTANTS ---
# Determine the absolute path to the project root (where config.json should live)
# This handles cases where the script is run from a subdirectory (like script/)
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG_FILE_PATH = PROJECT_ROOT / "config.json"

# --- 0. CONFIGURATION LOADING ---
def interactive_config_setup():
    """引導使用者建立初始設定檔的互動流程。"""
    print("\n--- 歡迎使用 Project Snapshot Tool ---")
    print(f"尚未偵測到設定檔 ({CONFIG_FILE_PATH.name})。")
    print("我們可以立即為您初始化一個專案設定，以便馬上開始使用。")
    
    try:
        confirm = input("是否立即新增專案設定？(Y/n): ").strip().lower()
    except EOFError:
        confirm = 'n' # Handle cases where input might fail or be empty

    if confirm == 'n':
        return None

    projects = {}
    
    while True:
        print("\n--- 新增專案 ---")
        name = input("請輸入專案名稱 (例如 MyAwesomeApp): ").strip()
        if not name:
            print("專案名稱不能為空。")
            continue
            
        android_path = scan_and_select_project('android')
        
        # 嘗試智慧預測 iOS 路徑
        ios_prediction = predict_related_path(android_path, 'ios')
        ios_path = None
        
        if ios_prediction:
            print(f"\n🔍 偵測到可能的 iOS 專案路徑: {ios_prediction}")
            confirm_pred = input("  是否直接使用？ (Y/n): ").strip().lower()
            if confirm_pred != 'n':
                ios_path = ios_prediction
        
        if not ios_path:
            ios_path = scan_and_select_project('ios')

        projects[name] = {
            "name": name,
            "android_path": android_path,
            "ios_path": ios_path
        }
        
        more = input("\n是否要新增另一個專案？(y/N): ").strip().lower()
        if more != 'y':
            break

    default_output = os.path.join(pathlib.Path.home(), "Documents", "snapshot_reports")
    output_dir = input(f"\n請輸入報告輸出目錄 [預設: {default_output}]: ").strip()
    if not output_dir:
        output_dir = default_output

    config_data = {
        "projects": projects,
        "output_base_dir": output_dir
    }
    
    # Save to config.json
    try:
        # Ensure we write to the project root config.json
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        print(f"\n設定已成功儲存至: {CONFIG_FILE_PATH.resolve()}")
        print("-" * 40 + "\n")
        return config_data
    except Exception as e:
        print(f"儲存設定檔時發生錯誤: {e}")
        return None

def load_config():
    default_config = {
        "projects": {},
        "output_base_dir": str(pathlib.Path.home() / "Documents" / "snapshot_reports")
    }

    if not CONFIG_FILE_PATH.exists():
        # 嘗試互動式設定
        new_config = interactive_config_setup()
        if new_config:
            return new_config
            
        print(f"Warning: {CONFIG_FILE_PATH.name} not found at {CONFIG_FILE_PATH}. Using defaults. Please copy config.example.json to config.json.")
        return default_config

    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
            return user_config
    except Exception as e:
        print(f"Error loading {CONFIG_FILE_PATH.name}: {e}")
        return default_config

CONFIG = load_config()
PROJECT_CONFIGS = CONFIG.get("projects", {})
try:
    OUTPUT_BASE_DIR = pathlib.Path(os.path.expanduser(CONFIG.get("output_base_dir", "~/Documents/snapshot_reports")))
except Exception:
     OUTPUT_BASE_DIR = pathlib.Path.home() / "Documents" / "snapshot_reports"

TREE_MAX_DEPTH = CONFIG.get("tree_max_depth", 20)
TREE_INDENT_CHAR = CONFIG.get("tree_indent_char", "    ")

# --- Android Specific Settings (adapted from your original script) ---
ANDROID_EXCLUDES = [
    '.gradle/', 'build/', '.idea/', '*.iml', 'local.properties',
    '.DS_Store', 'snapshot.py', 'snapshot.md', 'captures/',
    'release/', '*.keystore', '*.jks', '.git/',
    # Add any other Android-specific excludes
]
ANDROID_PARSE_XML_RESOURCES_DETAILS = False
ANDROID_RE_CLASS_INTERFACE = re.compile(r"^\s*(?:public|protected|private|static|\s)*\s*(class|interface)\s+([A-Za-z_][A-Za-z0-9_<>,\]]*)(?:\s+extends\s+[A-Za-z0-9_<>,\]]+)?(?:\s+implements\s+[A-Za-z0-9_<>,\]]+)?\s*\{")
ANDROID_RE_METHOD = re.compile(r"^\s*(?:@[\w\.]+\s*)*(?:public|protected)\s+(?:static\s+|final\s+|<[\w\s,]+>\s*)*([\w\.<>\[\]]+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*(?:throws\s+[\w\.,\s]+)?\s*\{?", re.MULTILINE)
ANDROID_RE_SINGLE_LINE_COMMENT = re.compile(r"^\s*//\s*(.*)")
ANDROID_RE_JAVADOC_START = re.compile(r"^\s*/\*\*\s*(.*)")
ANDROID_RE_JAVADOC_END = re.compile(r"\s*\*/")
ANDROID_RE_MANIFEST_PERMISSION = re.compile(r'<uses-permission\s+android:name="([^"]+)"\s*/>')
ANDROID_RE_MANIFEST_APPLICATION_NAME = re.compile(r'<application[^>]*android:name="([^"]+)"')
ANDROID_RE_MANIFEST_COMPONENT = re.compile(r'<(activity|service|receiver)\s+[^>]*android:name="([^"]+)"')
ANDROID_RE_XML_ID = re.compile(r'android:id="@\+id/([^"]+)"')
ANDROID_RE_XML_STRING_NAME = re.compile(r'<string\s+name="([^"]+)"[^>]*>')
ANDROID_RE_GRADLE_DEPENDENCY = re.compile(r"^\s*(implementation|api|compileOnly|runtimeOnly|testImplementation|androidTestImplementation|debugImplementation|releaseImplementation)\s*(?:\(|\s)\"([^\"]+)\"", re.MULTILINE)
ANDROID_RE_GRADLE_DEPENDENCY_LIBS = re.compile(r"^\s*(implementation|api|compileOnly|runtimeOnly|testImplementation|androidTestImplementation|debugImplementation|releaseImplementation)\s*\(\s*libs\.([\w\.-]+)\s*\)", re.MULTILINE)
ANDROID_RE_SETTINGS_GRADLE_ROOT_NAME = re.compile(r"^\s*rootProject\.name\s*=\s*\"([^\"]+)\"", re.MULTILINE)
ANDROID_RE_SETTINGS_GRADLE_INCLUDE = re.compile(r"^\s*include\s*\"\":(.*?)\"\"", re.MULTILINE)

ANDROID_RE_KOTLIN_CLASS = re.compile(r"^\s*(?:[a-z]+\s+)*(class|interface|object|enum class|sealed class|data class)\s+([A-Za-z_][A-Za-z0-9_]*)(?:.*)?\{?", re.MULTILINE)
# Match function declarations including extension functions (fun Type.functionName)
ANDROID_RE_KOTLIN_FUNCTION = re.compile(r"^\s*(?:@[\w\.]+\s+)*(?:[a-z]+\s+)*fun\s+(?:[A-Za-z_][A-Za-z0-9_<>\[\]\?]*\.)?([A-Za-z_][A-Za-z0-9_`]*)\s*\(", re.MULTILINE)
ANDROID_RE_KOTLIN_PROPERTY = re.compile(r"^\s*(?:[a-z]+\s+)*(val|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*[A-Za-z0-9_<>\[\]\?]+)?\s*=", re.MULTILINE)



# --- iOS Specific Settings ---
IOS_EXCLUDES = [
    ".DS_Store", "snapshot.py", "snapshot.md", # General self-ignores
    ".git/", "Pods/", "Carthage/", "build/", "DerivedData/",
    "*.xcodeproj/project.xcworkspace/", "*.xcodeproj/xcuserdata/",
    "*.xcworkspace/xcuserdata/", "*.xcassets/*/.json", # Exclude json inside asset catalogs
    "xcuserdata/", ".swiftpm/",
    "xcode_analyzer_logs/", # Exclude the log directory created by this script
    # Add any other iOS-specific excludes
]
# Updated Regex for Swift Types:
# 1. Supports optional modifiers (public, private, open, final, indirect, etc.)
# 2. Captures the keyword (class, struct, enum, protocol, extension, actor)
# 3. Captures the name greedily using a character class allowed in identifiers (including generics <>, dots ., etc.)
#    It stops when it hits a space (usually before :) or a char not in the class.
IOS_RE_SWIFT_TYPE = re.compile(r"^\s*(?:(?:public|internal|fileprivate|private|open|final|indirect)\s+)*(class|struct|enum|protocol|extension|actor)\s+([A-Za-z0-9_<>,\.\[\]]+)", re.MULTILINE)

IOS_RE_SWIFT_FUNC = re.compile(r"^\s*(?:@[\w\.]+\s*)*(?:(?:public|internal|fileprivate|private)\s+)?(?:(?:static|class)\s+)?(?:mutating\s+|nonmutating\s+)?\s*func\s+([`A-Za-z_][A-Za-z0-9_`<>\?\[\]!\.\(\)]*)\s*\(([^)]*)\)\s*(?:(?:async\s+)?(?:re)?throws\s+)?(?:->\s*[\w\.<>\[\]\?!\[\]\(\)]+)?\s*\{?", re.MULTILINE)
IOS_RE_SWIFT_SINGLE_LINE_COMMENT = re.compile(r"^\s*//\s*(.*)")
IOS_RE_SWIFT_DOC_COMMENT = re.compile(r"^\s*///\s*(.*)")
IOS_RE_SWIFT_MULTILINE_START = re.compile(r"^\s*/\*(?!\*).*", re.MULTILINE) # Avoid matching /** (doc comments handled by javadoc like regex)
IOS_RE_SWIFT_MULTILINE_DOC_START = re.compile(r"^\s*/\*\*\s*(.*)", re.MULTILINE)
IOS_RE_SWIFT_MULTILINE_END = re.compile(r".*\*/\s*$", re.MULTILINE)
IOS_RE_PODFILE_POD = re.compile(r"^\s*pod\s+\"([^\"]+)\"(?:,\s*\"[^\"]+\")?", re.MULTILINE) # Basic pod name
IOS_RE_PODFILE_LOCK_POD = re.compile(r"^\s*-\s+([A-Za-z0-9_/\-]+)\s+\([\w\.-]+\)", re.MULTILINE)
IOS_RE_SPM_PACKAGE_URL = re.compile(r"\.package\s*\(\s*(?:name:\s*\"([^\"]+)\"\s*,)?\s*url:\s*\"([^\"]+)\"", re.MULTILINE)
IOS_RE_SPM_PACKAGE_PATH = re.compile(r"\.package\s*\(\s*(?:name:\s*\"([^\"]+)\"\s*,)?\s*path:\s*\"([^\"]+)\"", re.MULTILINE)


# --- XCODE SETTINGS ANALYSIS FUNCTIONS (from analyze_xcode_settings.py) ---
def xcode_escape_markdown(text):
    """逸脫 Markdown 特殊字元，特別是針對表格內的內容。"""
    if not isinstance(text, str):
        text = str(text)
    # 逸脫反引號和豎線，因為它們在表格中和程式碼塊中有特殊意義
    text = text.replace('`', '\\`').replace('|', '\\|')
    return text

def xcode_format_settings_to_markdown_table(settings_dict, title="Build Settings"):
    """
    將建構設定字典格式化為 Markdown 表格。
    """
    xcode_analyzer_logger.debug(f"DEBUG: xcode_format_settings_to_markdown_table called for '{title}'")
    xcode_analyzer_logger.debug(f"DEBUG: Type of settings_dict: {type(settings_dict)}")

    is_empty = False
    actual_settings_items = {} # 用來儲存實際的建構設定

    if settings_dict and hasattr(settings_dict, '__dict__'):
        xcode_analyzer_logger.debug(f"DEBUG: Accessing settings_dict.__dict__ for '{title}'")
        for key, value in settings_dict.__dict__.items():
            if key != '_parent': # 過濾掉內部使用的 _parent 屬性
                actual_settings_items[key] = value
                
    if not actual_settings_items: # 如果過濾後為空
        if settings_dict is not None and hasattr(settings_dict, '__dict__') and len(settings_dict.__dict__) <= 1 and not actual_settings_items:
            return f"> __{title}:__ 此設定檔無定義特定設定 (空白或僅包含內部屬性)。\n\n"
        return f"> __{title}:__ 此設定檔無定義特定設定。\n\n"

    md_output = [f"> __{title}:__\n"]
    md_output.append("| 設定鍵值 (Setting Key) | 值 (Value) |")
    md_output.append("|-------------|-------|")

    try:
        sorted_keys = sorted(actual_settings_items.keys())
    except TypeError as e_sort:
        xcode_analyzer_logger.debug(f"DEBUG: Error during key sorting for '{title}' from actual_settings_items: {e_sort}")
        md_output.append(f"| 錯誤: 無法排序 {title} 的設定 (詳細資訊: {xcode_escape_markdown(str(e_sort))}) |  |")
        md_output.append("\n")
        return "\n".join(md_output)

    if not sorted_keys and not is_empty:
         return f"> __{title}:__ 找到設定物件，但在過濾後似乎為空。\n\n"

    for key in sorted_keys:
        value = actual_settings_items[key]
        
        if isinstance(value, (list, tuple)):
            value_str = ", ".join(map(str, value))
        else:
            value_str = str(value)
        
        escaped_key = f"`{xcode_escape_markdown(str(key))}`"
        escaped_value = f"`{xcode_escape_markdown(value_str)}`"
        md_output.append(f"| {escaped_key} | {escaped_value} |")
    md_output.append("\n")
    return "\n".join(md_output)

def generate_xcode_settings_report_markdown(project_ios_root_path_str):
    """
    分析指定的 Xcode 專案路徑 (iOS project root)，提取建構設定並生成 Markdown 報告 string.
    """
    markdown_content = ["\n## Xcode 專案建構設定分析 (Build Settings Analysis)\n"] # Added newline for better spacing
    
    project_ios_root_path = pathlib.Path(project_ios_root_path_str)
    xcodeproj_dirs = list(project_ios_root_path.glob("*.xcodeproj"))

    if not xcodeproj_dirs:
        err_msg = f"No .xcodeproj directory found in `{project_ios_root_path_str}`"
        xcode_analyzer_logger.error(f"Error: {err_msg}") # Use the logger
        markdown_content.append(f"錯誤: 在 `{project_ios_root_path_str}` 找不到 .xcodeproj 目錄\n")
        return "\n".join(markdown_content)

    # Use the first .xcodeproj found (typically there's one at the root of an iOS project)
    xcodeproj_path_obj = xcodeproj_dirs[0]
    pbxproj_path_obj = xcodeproj_path_obj / "project.pbxproj"
    
    if not pbxproj_path_obj.exists():
        err_msg = f"Could not find project.pbxproj in `{xcodeproj_path_obj}`"
        xcode_analyzer_logger.error(f"Error: {err_msg}")
        markdown_content.append(f"錯誤: 在 `{xcodeproj_path_obj}` 找不到 project.pbxproj\n")
        return "\n".join(markdown_content)

    markdown_content.append(f"分析目標：`{pbxproj_path_obj.resolve()}`\n")

    try:
        # XcodeProject.load expects a string path
        project = XcodeProject.load(str(pbxproj_path_obj))
    except Exception as e:
        err_msg = f"Error loading project file {pbxproj_path_obj}: {e}"
        xcode_analyzer_logger.error(err_msg) # Use the logger
        markdown_content.append(f"載入專案檔 `{pbxproj_path_obj}` 時發生錯誤：{e}\n")
        return "\n".join(markdown_content)

    # --- 1. 專案級別 (Project-Level) 建構設定 ---
    markdown_content.append("### 1. 專案層級 (Project-Level) 建構設定\n") # Changed to H3 for better nesting
    markdown_content.append("> 這些設定套用於整個專案，並可能被個別 Target 繼承或覆寫。\n")

    project_object = project.get_object(project.rootObject)
    if project_object and hasattr(project_object, 'buildConfigurationList'):
        config_list_id = project_object.buildConfigurationList
        config_list = project.get_object(config_list_id)
        
        if config_list and hasattr(config_list, 'buildConfigurations') and config_list.buildConfigurations:
            for config_id in config_list.buildConfigurations:
                config = project.get_object(config_id)
                if not config:
                    markdown_content.append(f"> 警告：無法取得 ID 為 '{config_id}' 的專案層級設定物件。\n")
                    continue
                config_name = getattr(config, 'name', 'Unknown Configuration')
                markdown_content.append(f"#### Configuration: {config_name}\n") # Changed to H4
                build_settings = getattr(config, 'buildSettings', None)
                markdown_content.append(xcode_format_settings_to_markdown_table(build_settings, title=f"{config_name} 設定"))
        else:
            markdown_content.append("> 未在專案層級找到建構設定 (或列表為空/格式錯誤)。\n\n")
    else:
        markdown_content.append("> 無法取得專案層級的建構設定 (根物件或其 buildConfigurationList 遺失/無效)。\n\n")

    # --- 2. Target 級別 (Target-Level) 建構設定 ---
    markdown_content.append("### 2. 目標層級 (Target-Level) 建構設定\n") # Changed to H3
    markdown_content.append("> 這些設定專屬於個別 Target，並會覆寫專案層級的設定。\n")

    project_targets = []
    try:
        retrieved_targets = project.get_targets()
        if retrieved_targets:
            project_targets = retrieved_targets
    except AttributeError:
        try:
            if hasattr(project, 'objects') and hasattr(project.objects, 'get_targets'):
                retrieved_targets_fallback = project.objects.get_targets()
                if retrieved_targets_fallback:
                    project_targets = retrieved_targets_fallback
        except Exception as e_fallback:
            xcode_analyzer_logger.debug(f"DEBUG: Error during fallback target retrieval: {e_fallback}") 
    except Exception as e_get_targets:
        xcode_analyzer_logger.debug(f"DEBUG: An unexpected error occurred while calling `project.get_targets()`: {e_get_targets}")

    if not project_targets:
        markdown_content.append("> 專案中未找到 Targets，或讀取時發生錯誤。\n")
        # Optionally add more detailed error from above if needed
        markdown_content.append("\n")
    else:
        for target in project_targets:
            target_name = getattr(target, 'name', 'Unknown Target')
            product_type = getattr(target, 'productType', 'Unknown Type')
            markdown_content.append(f"#### Target: {target_name} (Product Type: `{product_type}`)\n") # Changed to H4
            
            build_config_list_id = getattr(target, 'buildConfigurationList', None)
            if build_config_list_id:
                config_list = project.get_object(build_config_list_id)
                if config_list and hasattr(config_list, 'buildConfigurations') and config_list.buildConfigurations:
                    for config_id in config_list.buildConfigurations:
                        config = project.get_object(config_id)
                        if not config:
                            markdown_content.append(f"> 警告：無法取得 Target '{target_name}' 中 ID 為 '{config_id}' 的設定物件。\n")
                            continue
                        config_name = getattr(config, 'name', 'Unknown Configuration')
                        markdown_content.append(f"##### Configuration: {config_name} (for Target: {target_name})\n") # Changed to H5
                        build_settings = getattr(config, 'buildSettings', None)
                        markdown_content.append(xcode_format_settings_to_markdown_table(build_settings, title=f"{target_name} 的 {config_name} 設定"))
                else:
                    # ... (simplified warning message generation for brevity)
                    markdown_content.append(f"> Target '{target_name}' 未找到建構設定。\n\n")
            else:
                markdown_content.append(f"> Target '{target_name}' 沒有 'buildConfigurationList' ID 或其無效/為空。\n\n")
            
    # --- 3. (可選) 其他 Project.pbxproj 資訊 ---
    markdown_content.append("### 3. 其他專案資訊 (檔案參照 - File References)\n") # Changed to H3
    
    try:
        files_in_project_list = []
        if not hasattr(project, 'objects') or project.objects is None:
            markdown_content.append("> 找不到 `project.objects` 屬性或其為 None。\n")
        else:
            xcode_analyzer_logger.debug(f"DEBUG: Iterating through project.objects (type: {type(project.objects)})")
            retrieved_files = project.objects.get_objects_in_section('PBXFileReference')
            
            if retrieved_files is None:
                xcode_analyzer_logger.debug(f"DEBUG: project.objects.get_objects_in_section('PBXFileReference') returned None")
                markdown_content.append("> `project.objects.get_objects_in_section('PBXFileReference')` 回傳 None。\n")
            elif not hasattr(retrieved_files, '__iter__'):
                xcode_analyzer_logger.debug(f"DEBUG: project.objects.get_objects_in_section('PBXFileReference') did not return an iterable.")
                markdown_content.append(f"> `project.objects.get_objects_in_section('PBXFileReference')` 未回傳可迭代物件 (type: {type(retrieved_files)}).\n")
            else:
                for file_obj in retrieved_files:
                    path_attr = getattr(file_obj, 'path', None)
                    if path_attr:
                        file_name_from_path = os.path.basename(str(path_attr))
                        explicit_name_attr = getattr(file_obj, 'name', None)
                        display_name = explicit_name_attr if explicit_name_attr else file_name_from_path
                        isa_attr = getattr(file_obj, 'isa', 'PBXFileReference')
                        files_in_project_list.append(f"- `{xcode_escape_markdown(str(path_attr))}` (Type: {xcode_escape_markdown(str(isa_attr))}, Name: {xcode_escape_markdown(str(display_name or 'N/A'))})")
            
            if files_in_project_list:
                markdown_content.append("\n".join(files_in_project_list[:30]))
                if len(files_in_project_list) > 30:
                    markdown_content.append("\n- ... (還有更多)")
            elif not (markdown_content[-1].startswith("> `project.objects.get_objects_in_section") and ("回傳 None" in markdown_content[-1] or "未回傳可迭代物件" in markdown_content[-1])):
                markdown_content.append("> 專案中未找到檔案參照 (PBXFileReference)。\n")
                
    except AttributeError as e_attr:
        xcode_analyzer_logger.debug(f"DEBUG: AttributeError during file listing: {e_attr}")
        markdown_content.append(f"> 存取專案物件以列出檔案時發生錯誤: {xcode_escape_markdown(str(e_attr))}.\n")
    except Exception as e_files:
        xcode_analyzer_logger.debug(f"DEBUG: Error during file listing: {e_files}")
        markdown_content.append(f"> 無法從專案物件列出檔案: {xcode_escape_markdown(str(e_files))}\n")
    markdown_content.append("\n")

    return "\n".join(markdown_content)
# --- END OF XCODE SETTINGS ANALYSIS FUNCTIONS ---


# --- 1. Generic Helper Functions ---

def select_folder_via_finder(prompt="請選擇資料夾"):
    """使用 macOS AppleScript 開啟原生的資料夾選擇視窗。"""
    try:
        # AppleScript command to choose a folder
        script = f'tell application "System Events" to activate\n' \
                 f'set p to POSIX path of (choose folder with prompt "{prompt}")'
        
        proc = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        
        if proc.returncode == 0:
            path = proc.stdout.strip()
            return path
        else:
            # User cancelled or error
            return None
    except Exception as e:
        print(f"開啟 Finder 視窗失敗: {e}")
        return None

def scan_and_select_project(platform_type):
    """
    結合 GUI 選擇與智慧掃描。
    platform_type: 'android' 或 'ios'
    回傳: 選擇的專案路徑 (str) 或 None
    """
    print(f"\n配置 {platform_type} 路徑:")
    print("  [Enter] 開啟 Finder 視窗選擇")
    print("  [文字] 直接輸入路徑")
    print("  [S] 跳過 (Skip)")
    
    choice = input("請選擇: ").strip()
    
    selected_path = None
    
    if choice.lower() == 's':
        return None
    elif not choice:
        # Launch Finder
        selected_path = select_folder_via_finder(f"選擇 {platform_type} 專案資料夾 (或其父目錄)")
        if not selected_path:
            print("  (已取消選擇)")
            return None
    else:
        # Manual input
        selected_path = os.path.expanduser(choice)

    path_obj = pathlib.Path(selected_path)
    if not path_obj.exists():
        print(f"  [錯誤] 路徑不存在: {selected_path}")
        return None

    # check markers
    android_markers = ["build.gradle", "build.gradle.kts"]
    ios_markers = ["*.xcodeproj", "*.xcworkspace", "Podfile", "Package.swift"]
    
    markers = android_markers if platform_type == 'android' else ios_markers
    
    def is_project_root(p):
        for m in markers:
            if '*' in m:
                if list(p.glob(m)): return True
            elif (p / m).exists(): return True
        return False

    # 1. Check if the selected folder is arguably the project root itself
    if is_project_root(path_obj):
        print(f"  確認為 {platform_type} 專案根目錄: {path_obj.name}")
        return str(path_obj)

    # 2. If not, scan subdirectories (Depth limited)
    print(f"  '{path_obj.name}' 看起來不像是直接的專案根目錄。正在掃描子目錄 (Max Depth: 3)...")
    candidates = []
    
    # Common directories to ignore during scan to save time
    ignore_dirs = {'.git', '.gradle', '.idea', 'build', 'captures', 'node_modules', 'Pods', 'DerivedData'}
    max_scan_depth = 3
    
    try:
        root_depth = len(path_obj.parts)
        
        for root, dirs, files in os.walk(str(path_obj)):
            # Modify dirs in-place to skip ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
            
            current_path = pathlib.Path(root)
            current_depth = len(current_path.parts) - root_depth
            
            if current_depth > max_scan_depth:
                del dirs[:] # Stop descending
                continue
            
            # Skip the root itself as we checked it in step 1
            if current_depth == 0:
                continue

            if is_project_root(current_path):
                candidates.append(current_path)
                # If found a project root, don't look inside it (avoid nested modules causing duplicates)
                del dirs[:]
                
    except Exception as e:
        print(f"掃描失敗: {e}")
    
    if not candidates:
        print("  未發現明顯的專案子目錄。將使用您選擇的目錄作為根目錄。")
        return str(path_obj)
    
    print(f"\n找到 {len(candidates)} 個可能的專案:")
    # Sort candidates by depth (shallower first) then name
    candidates.sort(key=lambda p: (len(p.parts), p.name))
    
    for i, c in enumerate(candidates):
        rel_str = str(c.relative_to(path_obj))
        print(f"  {i+1}. {rel_str}")
    print(f"  {len(candidates)+1}. 使用原本選擇的目錄 ({path_obj.name})")
    
    while True:
        try:
            sel = int(input(f"請選擇 (1-{len(candidates)+1}): "))
            if 1 <= sel <= len(candidates):
                return str(candidates[sel-1])
            elif sel == len(candidates) + 1:
                return str(path_obj)
        except ValueError:
            pass

def predict_related_path(known_path_str, target_platform):
    """
    根據已知的路徑 (known_path_str) 猜測另一個平台 (target_platform) 的路徑。
    例如：
    1. .../project/android -> .../project/ios (Sibling)
    2. .../project (Root) -> .../project/ios (Child)
    3. .../project/Android/app -> .../project/iOS/app (Parallel/Cousin)
    """
    if not known_path_str:
        return None
        
    known_path = pathlib.Path(known_path_str)
    target_names = []
    
    if target_platform == 'ios':
        target_names = ['ios', 'iOS', 'iosApp', 'Runner'] # Runner is for Flutter
    elif target_platform == 'android':
        target_names = ['android', 'Android', 'androidApp']
        
    # 策略 1: 檢查兄弟目錄 (Sibling)
    # 適用於 .../project/android -> .../project/ios
    parent = known_path.parent
    for name in target_names:
        candidate = parent / name
        if candidate.exists() and candidate.is_dir():
            return str(candidate)
            
    # 策略 2: 檢查子目錄 (Child)
    # 適用於 .../project (Root) -> .../project/ios
    for name in target_names:
        candidate = known_path / name
        if candidate.exists() and candidate.is_dir():
            return str(candidate)

    # 策略 3: 平行結構/堂兄弟 (Parallel/Cousin) - 針對您的案例
    # 適用於 .../root/Android/myapp -> .../root/iOS/myapp
    # 邏輯：往上找兩層 (Grandparent)，找目標平台資料夾，再找同名子資料夾
    grandparent = parent.parent
    current_folder_name = known_path.name # e.g., 'myapp'
    
    for name in target_names:
        parallel_platform_folder = grandparent / name # e.g., .../root/iOS
        if parallel_platform_folder.exists() and parallel_platform_folder.is_dir():
            # 3a. 檢查是否包含同名資料夾 (.../root/iOS/myapp)
            same_name_candidate = parallel_platform_folder / current_folder_name
            if same_name_candidate.exists() and same_name_candidate.is_dir():
                return str(same_name_candidate)
            
            # 3b. 也許平行資料夾本身就是專案根目錄 (.../root/iOS)
            # 這裡可以簡單檢查一下裡面是否有特徵檔案，避免誤判
            if target_platform == 'ios':
                if list(parallel_platform_folder.glob("*.xcodeproj")) or (parallel_platform_folder / "Podfile").exists():
                    return str(parallel_platform_folder)
            elif target_platform == 'android':
                if (parallel_platform_folder / "build.gradle").exists() or (parallel_platform_folder / "build.gradle.kts").exists():
                    return str(parallel_platform_folder)

    return None

def parse_ignore_patterns(ignore_file_path):
    """Parses a .gitignore or .cursorignore file and returns a list of patterns."""
    patterns = []
    try:
        with open(ignore_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    patterns.append(line)
    except Exception:
        pass  # If file doesn't exist or can't be read, return empty list
    return patterns

def is_excluded(path_str, project_root_str, current_excludes_list):
    """Checks if a file/directory should be excluded based on the provided exclude list.
    
    Supports gitignore-style patterns using fnmatch.
    """
    try:
        path_obj_absolute = pathlib.Path(path_str)
        project_root_path_obj = pathlib.Path(project_root_str)

        try:
            relative_path_obj = path_obj_absolute.relative_to(project_root_path_obj)
            relative_path_str = str(relative_path_obj)
        except ValueError: 
            relative_path_obj = path_obj_absolute.name
            relative_path_str = str(relative_path_obj)

        for exclude_pattern in current_excludes_list:
            # Handle directory patterns (ending with /)
            if exclude_pattern.endswith('/'):
                normalized_exclude_dir = exclude_pattern.strip('/')
                if relative_path_obj == normalized_exclude_dir or \
                   normalized_exclude_dir in pathlib.Path(relative_path_obj).parts or \
                   str(relative_path_obj).startswith(normalized_exclude_dir + os.sep):
                    return True
            # Use fnmatch for glob patterns (supports *, ?, [seq], etc.)
            elif '*' in exclude_pattern or '?' in exclude_pattern or '[' in exclude_pattern:
                # Match against relative path
                if fnmatch.fnmatch(relative_path_str, exclude_pattern):
                    return True
                # Also match against just the filename
                if fnmatch.fnmatch(path_obj_absolute.name, exclude_pattern):
                    return True
            # Exact match
            else:
                if path_obj_absolute.name == exclude_pattern or \
                   (isinstance(relative_path_obj, pathlib.Path) and relative_path_obj.name == exclude_pattern) or \
                   exclude_pattern in str(relative_path_obj):
                    return True
    except Exception:
        return False
    return False

def generate_directory_tree(project_root_path, max_depth, indent_char, current_excludes_list, platform_name="Project"):
    """Generates a project directory tree as a list of strings."""
    tree_lines = [f"## {platform_name} 目錄結構 ({project_root_path.name})\n```"]
    
    project_root_path = pathlib.Path(project_root_path)

    def add_to_tree(current_path, prefix="", level=0):
        if level > max_depth:
            tree_lines.append(f"{prefix}└─ ... (達到最大深度)")
            return

        items = []
        try:
            sorted_iter = sorted(
                current_path.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower())
            )
            for item in sorted_iter:
                if not is_excluded(str(item), str(project_root_path), current_excludes_list):
                    items.append(item)
        except PermissionError:
            tree_lines.append(f"{prefix}└─ [權限不足: {current_path.name}]")
            return
        except FileNotFoundError:
            tree_lines.append(f"{prefix}└─ [找不到檔案: {current_path.name}]")
            return

        for i, item in enumerate(items):
            connector = "└─ " if i == len(items) - 1 else "├─ "
            tree_lines.append(f"{prefix}{connector}{item.name}")
            if item.is_dir():
                new_prefix = prefix + (indent_char if i == len(items) - 1 else "│" + indent_char[1:])
                add_to_tree(item, new_prefix, level + 1)
    
    if project_root_path.exists() and project_root_path.is_dir():
        tree_lines.append(f"{project_root_path.name}")
        add_to_tree(project_root_path, level=0)
    else:
        tree_lines.append(f"[錯誤: 找不到專案根目錄 '{project_root_path}' 或它不是一個目錄]")
        
    tree_lines.append("```\n")
    return "\n".join(tree_lines)

# --- 2. Android Snapshot Logic (Adapted from your original script) ---

def android_parse_code_file(file_path):
    content = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return [f"  - 讀取檔案 {file_path.name} 時發生錯誤: {e}"]

    current_comment_lines = []
    in_javadoc = False
    
    is_kotlin = file_path.suffix == '.kt'

    for line in lines:
        stripped_line = line.strip()
        
        # --- Comment Handling (Shared) ---
        if in_javadoc:
            if ANDROID_RE_JAVADOC_END.search(stripped_line):
                in_javadoc = False
                if not current_comment_lines:
                    javadoc_match = ANDROID_RE_JAVADOC_START.search(stripped_line)
                    if javadoc_match and javadoc_match.group(1) and not ANDROID_RE_JAVADOC_END.search(javadoc_match.group(1)):
                         current_comment_lines.append(javadoc_match.group(1).replace('*/', '').strip())
                    elif javadoc_match and javadoc_match.group(1): 
                        current_comment_lines.append(javadoc_match.group(1).replace('*/','').strip())
            elif stripped_line.startswith("* "):
                current_comment_lines.append(stripped_line[2:].strip())
            elif stripped_line == "*":
                pass
            else: 
                processed_line = stripped_line.replace('*/', '').strip()
                if processed_line:
                    current_comment_lines.append(processed_line)
            continue 

        javadoc_match = ANDROID_RE_JAVADOC_START.search(stripped_line)
        if javadoc_match:
            in_javadoc = True
            comment_text = javadoc_match.group(1).strip()
            if comment_text and not ANDROID_RE_JAVADOC_END.search(comment_text): 
                current_comment_lines.append(comment_text)
            elif comment_text: 
                current_comment_lines.append(comment_text.replace('*/','').strip())
                in_javadoc = False 
            continue

        single_comment_match = ANDROID_RE_SINGLE_LINE_COMMENT.search(stripped_line)
        if single_comment_match:
            current_comment_lines.append(single_comment_match.group(1).strip())
            continue

        # --- Parsing Logic ---
        
        if is_kotlin:
             class_match = ANDROID_RE_KOTLIN_CLASS.search(line)
             if class_match:
                entity_type = class_match.group(1)
                entity_name = class_match.group(2).strip()
                if current_comment_lines:
                    content.append(f"  - **{entity_type.capitalize()} {entity_name}**")
                    for comment_line in current_comment_lines:
                        if comment_line: content.append(f"    - _{comment_line}_")
                else:
                    content.append(f"  - **{entity_type.capitalize()} {entity_name}**")
                current_comment_lines = []
                continue
                
             func_match = ANDROID_RE_KOTLIN_FUNCTION.search(line)
             if func_match:
                func_name = func_match.group(1)
                # Since we simplified the regex, we just show the function name
                signature = f"{func_name}(...)"
                if current_comment_lines:
                    content.append(f"    - `Func: {signature}`")
                    for comment_line in current_comment_lines:
                         if comment_line: content.append(f"      - _{comment_line}_")
                else:
                    content.append(f"    - `Func: {signature}`")
                current_comment_lines = []
                continue
             
             # Match Kotlin properties (val/var)
             property_match = ANDROID_RE_KOTLIN_PROPERTY.search(line)
             if property_match:
                property_type = property_match.group(1)  # val or var
                property_name = property_match.group(2)
                if current_comment_lines:
                    content.append(f"    - `{property_type.capitalize()}: {property_name}`")
                    for comment_line in current_comment_lines:
                         if comment_line: content.append(f"      - _{comment_line}_")
                else:
                    content.append(f"    - `{property_type.capitalize()}: {property_name}`")
                current_comment_lines = []
                continue

        else: # Java / Groovy
            class_match = ANDROID_RE_CLASS_INTERFACE.search(line)
            if class_match:
                entity_type = class_match.group(1)
                entity_name = class_match.group(2).strip() 
                if current_comment_lines:
                    content.append(f"  - **{entity_type.capitalize()} {entity_name}**")
                    for comment_line in current_comment_lines:
                        if comment_line: content.append(f"    - _{comment_line}_")
                else:
                    content.append(f"  - **{entity_type.capitalize()} {entity_name}**")
                current_comment_lines = []
                continue

            method_match = ANDROID_RE_METHOD.search(line)
            if method_match:
                method_name = method_match.group(2)
                params = method_match.group(3)
                return_type = method_match.group(1)
                signature = f"{return_type} {method_name}({params})" if return_type else f"{method_name}({params})"
                if current_comment_lines:
                    content.append(f"    - `Method: {signature}`")
                    for comment_line in current_comment_lines:
                         if comment_line: content.append(f"      - _{comment_line}_")
                else:
                    content.append(f"    - `Method: {signature}`")
                current_comment_lines = []
                continue
        
        if stripped_line:
            current_comment_lines = []
            
    return content

def android_parse_manifest(file_path):
    manifest_data = {"permissions": set(), "application_name": None, "components": []}
    try:
        with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
    except Exception as e:
        return {"error": f"讀取 AndroidManifest.xml 時發生錯誤: {e}"}

    for match in ANDROID_RE_MANIFEST_PERMISSION.finditer(content):
        manifest_data["permissions"].add(match.group(1))
    app_name_match = ANDROID_RE_MANIFEST_APPLICATION_NAME.search(content)
    if app_name_match: manifest_data["application_name"] = app_name_match.group(1)
    for match in ANDROID_RE_MANIFEST_COMPONENT.finditer(content):
        manifest_data["components"].append(f"{match.group(1).capitalize()}: {match.group(2)}")
    
    md = ["### AndroidManifest 元件"]
    if manifest_data.get("error"): md.append(f"- {manifest_data['error']}"); return "\n".join(md)
    md.append(f"- **Application Name:** `{manifest_data['application_name'] or '(未指定)'}`")
    if manifest_data["permissions"]:
        md.append("- **權限 (Permissions):**")
        for p in sorted(list(manifest_data["permissions"])): md.append(f"  - `{p}`")
    if manifest_data["components"]:
        md.append("- **主要元件 (Main Components):**")
        for c in sorted(manifest_data["components"]): md.append(f"  - `{c}`")
    md.append("\n")
    return "\n".join(md)

def android_parse_xml_resource_file(file_path):
    if not ANDROID_PARSE_XML_RESOURCES_DETAILS:
        return [f"  - {file_path.name} (詳細解析已關閉)"]
    details = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f: xml_content = f.read()
    except Exception as e: return [f"  - 讀取 {file_path.name} 時發生錯誤: {e}"]

    is_layout = 'layout' in file_path.parent.name.lower()
    is_values = 'values' in file_path.parent.name.lower()

    if is_layout:
        ids = set(ANDROID_RE_XML_ID.findall(xml_content))
        if ids:
            details.append(f"  - **{file_path.name} (Layout IDs):**")
            for xml_id in sorted(list(ids)): details.append(f"""  - `android:id="@+id/{xml_id}"`""")
    elif is_values and file_path.name == "strings.xml":
        names = set(ANDROID_RE_XML_STRING_NAME.findall(xml_content))
        if names:
            details.append(f"  - **{file_path.name} (String Names):**")
            for name in sorted(list(names)): details.append(f"    - `<string name=\"{name}\">`")
    else:
        details.append(f"  - {file_path.name}")
    return details if details else [f"  - {file_path.name} (未擷取到特定內容)"]

def android_parse_gradle_dependencies(project_root_path):
    deps_by_module = defaultdict(lambda: defaultdict(list))
    gradle_files = list(project_root_path.rglob("build.gradle")) + list(project_root_path.rglob("build.gradle.kts"))
    root_project_name_from_settings = project_root_path.name
    module_paths_from_settings = {}

    settings_gradle = project_root_path / "settings.gradle"
    if settings_gradle.exists():
        try:
            with open(settings_gradle, 'r', encoding='utf-8') as f:
                for line in f:
                    root_match = ANDROID_RE_SETTINGS_GRADLE_ROOT_NAME.search(line)
                    if root_match: root_project_name_from_settings = root_match.group(1)
                    inc_match = ANDROID_RE_SETTINGS_GRADLE_INCLUDE.search(line)
                    if inc_match:
                        m_path_str = inc_match.group(1).replace(':', '/')
                        module_paths_from_settings[str(pathlib.Path(m_path_str))] = m_path_str.split('/')[-1]
        except Exception: pass 

    for gf in gradle_files:
        if is_excluded(str(gf), str(project_root_path), ANDROID_EXCLUDES): continue
        
        module_name = None
        try:
            rel_module_dir = gf.parent.relative_to(project_root_path)
            if str(rel_module_dir) in module_paths_from_settings:
                module_name = module_paths_from_settings[str(rel_module_dir)]
            elif not rel_module_dir.parts: 
                 module_name = f"{root_project_name_from_settings} (Root Project)"
            else:
                module_name = rel_module_dir.name 
        except ValueError: 
             module_name = gf.parent.name
        
        if not module_name: module_name = gf.parent.name or "Unknown Module"

        try:
            with open(gf, 'r', encoding='utf-8') as f:
                in_deps_block = False
                for line in f:
                    s_line = line.strip()
                    if s_line.startswith("dependencies {"): in_deps_block = True; continue
                    if in_deps_block and s_line == "}": in_deps_block = False; break 
                    if in_deps_block:
                        dep_m = ANDROID_RE_GRADLE_DEPENDENCY.search(s_line)
                        if dep_m: deps_by_module[module_name][dep_m.group(1)].append(f'\"{dep_m.group(2)}\"')
                        else:
                            dep_libs_m = ANDROID_RE_GRADLE_DEPENDENCY_LIBS.search(s_line)
                            if dep_libs_m: deps_by_module[module_name][dep_libs_m.group(1)].append(f'\"libs.{dep_libs_m.group(2)}\" (alias)')
        except Exception as e: deps_by_module[module_name]["error"].append(f"讀取 {gf.name} 時發生錯誤: {e}")

    md = ["## Gradle 相依性 (Dependencies)"]
    if not deps_by_module: md.append("未找到 build.gradle 檔案或相依性。\n"); return "\n".join(md)
    
    sorted_modules = sorted(deps_by_module.keys(), key=lambda m: (not m.endswith("(Root Project)"), m))

    for mod in sorted_modules:
        md.append(f"### 模組: {mod}")
        if "error" in deps_by_module[mod]:
            for err in deps_by_module[mod]["error"]: md.append(f"- _{err}_")
            continue
        configs = deps_by_module[mod]
        if not configs: md.append("    (此模組未找到或未解析出相依性)\n"); continue
        for cfg_type in sorted(configs.keys()):
            md.append(f"#### {cfg_type}")
            if configs[cfg_type]:
                for dep in sorted(configs[cfg_type]): md.append(f"  - {dep}")
            else: md.append("    (無)") 
            md.append("") 
        md.append("") 
    md.append("\n")
    return "\n".join(md)

def snapshot_android_project(project_path_str, project_display_name, output_dir_path):
    """Generates a snapshot report for a given Android project."""
    project_root = pathlib.Path(project_path_str)
    if not project_root.is_dir():
        print(f"錯誤：找不到 Android 專案路徑或該路徑不是目錄：{project_root}")
        return

    print(f"\n--- 正在產生 Android 快照報告：{project_display_name} ---")
    print(f"專案根目錄：{project_root}")

    # Load dynamic ignore patterns from target project
    active_excludes = list(ANDROID_EXCLUDES)  # Start with defaults
    gitignore_path = project_root / ".gitignore"
    cursorignore_path = project_root / ".cursorignore"
    
    if gitignore_path.exists():
        gitignore_patterns = parse_ignore_patterns(gitignore_path)
        active_excludes.extend(gitignore_patterns)
        print(f"  已載入 {len(gitignore_patterns)} 個 .gitignore 規則")
    
    if cursorignore_path.exists():
        cursorignore_patterns = parse_ignore_patterns(cursorignore_path)
        active_excludes.extend(cursorignore_patterns)
        print(f"  已載入 {len(cursorignore_patterns)} 個 .cursorignore 規則")

    markdown_parts = []
    
    print("  正在產生目錄結構...")
    markdown_parts.append(generate_directory_tree(project_root, TREE_MAX_DEPTH, TREE_INDENT_CHAR, active_excludes, "Android Project"))

    code_summary = ["## 主要 Java/Groovy/Kotlin 類別與方法"]
    xml_summary = ["## XML 資源摘要"]
    if not ANDROID_PARSE_XML_RESOURCES_DETAILS:
        xml_summary.append("_詳細 XML 資源解析已關閉。僅列出檔名。_\n")
    
    manifest_content = ""
    counts = {"code": 0, "manifest": 0, "xml": 0}
    
    print("  正在掃描並解析檔案...")
    for item in project_root.rglob("*"):
        if is_excluded(str(item), str(project_root), active_excludes): continue
        if item.is_file():
            rel_path = str(item.relative_to(project_root))
            if item.suffix in ['.java', '.groovy', '.kt']: 
                counts["code"] += 1
                code_summary.append(f"### 檔案: `{rel_path}`")
                parsed = android_parse_code_file(item) 
                code_summary.extend(parsed if parsed else ["  - (無可擷取的內容)"])
                code_summary.append("\n")
            elif item.name == "AndroidManifest.xml":
                counts["manifest"] += 1
                manifest_content = android_parse_manifest(item)
            elif item.suffix == '.xml' and any(p.lower() == 'res' for p in item.relative_to(project_root).parts):
                counts["xml"] += 1
                if ANDROID_PARSE_XML_RESOURCES_DETAILS:
                    xml_summary.extend(android_parse_xml_resource_file(item))
                else:
                    xml_summary.append(f"- `{rel_path}`")

    if counts["code"] == 0: code_summary.append("_未找到或未解析出 Java/Groovy/Kotlin 檔案。_\n")
    markdown_parts.append("\n".join(code_summary))

    if manifest_content: markdown_parts.append(manifest_content)
    elif counts["manifest"] > 0: markdown_parts.append("### AndroidManifest Components\n_找到 Manifest，但未提取出具體內容。_\n")
    else: markdown_parts.append("### AndroidManifest Components\n_找不到 AndroidManifest.xml。_\n")

    print("  正在解析 Gradle 相依性...")
    markdown_parts.append(android_parse_gradle_dependencies(project_root))
    
    if counts["xml"] == 0: xml_summary.append("_未找到 XML 資源檔案。_\n")
    markdown_parts.append("\n".join(xml_summary))

    output_filename = f"{project_display_name.replace(' ', '_')}_Android_Snapshot.md"
    output_path = output_dir_path / output_filename
    
    print(f"  正在將 Android 報告寫入至：{output_path}")
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Android 專案快照：{project_display_name}\n\n")
            f.write(f"_報告產生時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n")
            f.write("\n---\n\n".join(markdown_parts))
        print(f"  成功產生 Android 快照：{output_path}")
    except Exception as e:
        print(f"  錯誤：無法將 Android 報告寫入至 {output_path}: {e}")

# --- 3. iOS Snapshot Logic ---

def ios_parse_swift_file(file_path):
    """Parses a Swift file for classes, structs, funcs, and comments."""
    content = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return [f"  - 讀取檔案 {file_path.name} 時發生錯誤: {e}"]

    current_comment_lines = []
    in_multiline_comment = False
    in_multiline_doc_comment = False

    for line_num, line_content in enumerate(lines):
        stripped_line = line_content.strip()

        if in_multiline_doc_comment:
            if IOS_RE_SWIFT_MULTILINE_END.search(stripped_line):
                in_multiline_doc_comment = False
                comment_part = stripped_line.split('*/', 1)[0]
                if comment_part.startswith("* "): comment_part = comment_part[2:]
                elif comment_part.startswith("*"): comment_part = comment_part[1:]
                if comment_part.strip(): current_comment_lines.append(comment_part.strip())
            else: 
                comment_part = stripped_line
                if comment_part.startswith("* "): comment_part = comment_part[2:]
                elif comment_part.startswith("*"): comment_part = comment_part[1:]
                if comment_part.strip(): current_comment_lines.append(comment_part.strip())
            continue
        
        if in_multiline_comment:
            if IOS_RE_SWIFT_MULTILINE_END.search(stripped_line):
                in_multiline_comment = False
            continue

        doc_start_match = IOS_RE_SWIFT_MULTILINE_DOC_START.search(stripped_line)
        if doc_start_match:
            in_multiline_doc_comment = True
            comment_text = doc_start_match.group(1).strip()
            if comment_text: current_comment_lines.append(comment_text)
            if IOS_RE_SWIFT_MULTILINE_END.search(stripped_line) and not stripped_line.endswith("/**/"):
                 in_multiline_doc_comment = False 
            continue
        
        multiline_start_match = IOS_RE_SWIFT_MULTILINE_START.search(stripped_line)
        if multiline_start_match:
            in_multiline_comment = True
            if IOS_RE_SWIFT_MULTILINE_END.search(stripped_line): 
                in_multiline_comment = False
            continue 

        doc_comment_match = IOS_RE_SWIFT_DOC_COMMENT.search(stripped_line)
        if doc_comment_match:
            current_comment_lines.append(doc_comment_match.group(1).strip())
            continue
        
        single_comment_match = IOS_RE_SWIFT_SINGLE_LINE_COMMENT.search(stripped_line)
        if single_comment_match:
            pass 
            continue

        type_match = IOS_RE_SWIFT_TYPE.search(line_content) 
        if type_match:
            entity_type = type_match.group(1)
            
            # Safely handle potential None for group(2)
            raw_name_group = type_match.group(2)
            if raw_name_group:
                entity_name = raw_name_group.strip().replace('`', '')
            else:
                entity_name = "(Unknown)"

            if current_comment_lines:
                content.append(f"  - **{entity_type.capitalize()} {entity_name}**")
                for comment_line in current_comment_lines:
                    if comment_line: content.append(f"    - _{comment_line}_")
            else:
                content.append(f"  - **{entity_type.capitalize()} {entity_name}**")
            current_comment_lines = []
            continue

        func_match = IOS_RE_SWIFT_FUNC.search(line_content)
        if func_match:
            func_name = func_match.group(1).strip().replace('`', '')
            params = func_match.group(2).strip()
            signature = f"{func_name}({params})"
            if current_comment_lines:
                content.append(f"    - `Func: {signature}`")
                for comment_line in current_comment_lines:
                    if comment_line: content.append(f"      - _{comment_line}_")
            else:
                content.append(f"    - `Func: {signature}`")
            current_comment_lines = []
            continue
        
        if stripped_line: 
            current_comment_lines = [] 

    return content

def ios_parse_info_plist(file_path):
    """Parses Info.plist for key information."""
    plist_data = {}
    try:
        with open(file_path, 'rb') as fp:
            plist_content = plistlib.load(fp)
        
        plist_data['BundleIdentifier'] = plist_content.get('CFBundleIdentifier', 'N/A')
        plist_data['DisplayName'] = plist_content.get('CFBundleDisplayName', plist_content.get('CFBundleName', 'N/A'))
        plist_data['Version'] = plist_content.get('CFBundleShortVersionString', 'N/A')
        plist_data['Build'] = plist_content.get('CFBundleVersion', 'N/A')
        
        permissions = []
        for key, value in plist_content.items():
            if key.endswith("UsageDescription"):
                permissions.append(f"{key}: {value}")
        plist_data['Permissions'] = sorted(permissions)

    except Exception as e:
        return {"error": f"解析 {file_path.name} 時發生錯誤: {e}"}

    md = ["### Info.plist 摘要"]
    if plist_data.get("error"): md.append(f"- {plist_data['error']}"); return "\n".join(md)

    md.append(f"- **Bundle Identifier:** `{plist_data.get('BundleIdentifier')}`")
    md.append(f"- **顯示名稱 (Display Name):** `{plist_data.get('DisplayName')}`")
    md.append(f"- **版本 (Version):** `{plist_data.get('Version')}`")
    md.append(f"- **建置版本 (Build):** `{plist_data.get('Build')}`")

    # Extract values that might contain build settings variables
    bundle_info_values = [
        plist_data.get('BundleIdentifier'),
        plist_data.get('DisplayName'),
        plist_data.get('Version'),
        plist_data.get('Build')
    ]
    if any("$(" in str(val) for val in bundle_info_values):
        md.append("  - _注意：類似 `$(VARIABLE_NAME)` 的值是 Xcode 建構設定變數。實際值會在建構過程中解析。_")
    
    if plist_data.get('Permissions'):
        md.append("- **權限使用說明 (Permission Usage Descriptions):**")
        for perm in plist_data['Permissions']:
            md.append(f"  - `{perm}`")
    md.append("\n")
    return "\n".join(md)

def ios_parse_dependency_files(project_root_path):
    """
    Looks for iOS dependency files (Podfile.lock, Package.resolved, and fallbacks)
    and extracts dependency information.
    """
    deps_summary = ["## iOS 相依性總覽 (Dependency Overview)"]
    found_deps = False
    processed_spm_resolved = False 

    podfile_lock_path = project_root_path / "Podfile.lock"
    podfile_path = project_root_path / "Podfile"

    if podfile_lock_path.exists():
        found_deps = True
        deps_summary.append("### CocoaPods (來自 Podfile.lock)")
        pods_from_lock = []
        try:
            with open(podfile_lock_path, 'r', encoding='utf-8') as f:
                in_pods_section = False
                for line in f:
                    if line.strip() == "PODS:":
                        in_pods_section = True
                        continue
                    if line.strip() == "DEPENDENCIES:" or not line.startswith("  "):
                        in_pods_section = False
                    
                    if in_pods_section:
                        match = IOS_RE_PODFILE_LOCK_POD.search(line)
                        if match:
                            pod_name = match.group(1)
                            pod_version = match.group(2)
                            pods_from_lock.append(f"{pod_name}: {pod_version}")
            
            if pods_from_lock:
                for pod_info in sorted(list(set(pods_from_lock))): 
                    deps_summary.append(f"- `{pod_info}`")
            else:
                deps_summary.append("- _未從 Podfile.lock 提取出特定 pod (或格式不符)。_")
        except Exception as e:
            deps_summary.append(f"- _讀取 Podfile.lock 時發生錯誤: {e}_")
        deps_summary.append("")  
    
    elif podfile_path.exists(): 
        found_deps = True
        deps_summary.append("### CocoaPods (來自 Podfile - 僅宣告)")
        pods_declared = []
        try:
            with open(podfile_path, 'r', encoding='utf-8') as f:
                for line in f:
                    match = IOS_RE_PODFILE_POD.search(line)
                    if match:
                        pods_declared.append(match.group(1))
            if pods_declared:
                for pod in sorted(list(set(pods_declared))):
                    deps_summary.append(f"- `{pod}` (版本未在 Podfile 或 regex 中指定)")
            else:
                deps_summary.append("- _未透過 regex 提取出特定 pod (或 Podfile 內容較複雜)。_")
        except Exception as e:
            deps_summary.append(f"- _讀取 Podfile 時發生錯誤: {e}_")
        deps_summary.append("")

    package_resolved_candidates = []
    for xcodeproj_dir in project_root_path.glob("*.xcodeproj"):
        package_resolved_candidates.append(xcodeproj_dir / "project.xcworkspace/xcshareddata/swiftpm/Package.resolved")
        package_resolved_candidates.append(xcodeproj_dir / "xcshareddata/swiftpm/Package.resolved")
    for xcworkspace_dir in project_root_path.glob("*.xcworkspace"):
        package_resolved_candidates.append(xcworkspace_dir / "xcshareddata/swiftpm/Package.resolved")
    package_resolved_candidates.append(project_root_path / ".swiftpm/Package.resolved")
    package_resolved_candidates.append(project_root_path / "Package.resolved") 

    actual_package_resolved_path = None
    for p_path in package_resolved_candidates:
        if p_path.exists():
            actual_package_resolved_path = p_path
            break
            
    if actual_package_resolved_path:
        found_deps = True
        processed_spm_resolved = True
        deps_summary.append(f"### Swift Package Manager (來自 {actual_package_resolved_path.name})")
        spm_packages = []
        try:
            with open(actual_package_resolved_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                pins = []
                if 'object' in data and 'pins' in data['object']: 
                    pins = data['object']['pins']
                elif 'pins' in data: 
                    pins = data['pins']

                for pin in pins:
                    pkg_identity = pin.get('identity', pin.get('package', 'Unknown Identity'))
                    pkg_location = pin.get('location', pin.get('repositoryURL', 'Unknown URL'))
                    pkg_version = pin.get('state', {}).get('version', 'Unknown Version')
                    branch = pin.get('state', {}).get('branch')
                    revision = pin.get('state', {}).get('revision')

                    version_detail = pkg_version
                    if version_detail == 'Unknown Version':
                        if branch:
                            version_detail = f"branch: {branch}"
                        elif revision:
                            version_detail = f"revision: {revision[:7]}"

                    spm_packages.append(f"{pkg_identity} ({pkg_location}): {version_detail}")

            if spm_packages:
                for pkg_info in sorted(list(set(spm_packages))):
                    deps_summary.append(f"- `{pkg_info}`")
            else:
                deps_summary.append("- _未從 Package.resolved 找到或解析出特定套件。_")
        except Exception as e:
            deps_summary.append(f"- _讀取或解析 {actual_package_resolved_path.name} 時發生錯誤: {e}_")
        deps_summary.append("")

    package_swift_path = project_root_path / "Package.swift"
    if package_swift_path.exists() and not processed_spm_resolved : 
        found_deps = True
        if not processed_spm_resolved:
             deps_summary.append("### Swift Package Manager (來自 Package.swift - 僅宣告)")
        else:
             deps_summary.append("### Swift Package Manager (來自 Package.swift - 補充宣告)")

        packages_url = []
        packages_path = []
        try:
            with open(package_swift_path, 'r', encoding='utf-8') as f:
                content = f.read() 
                for match in IOS_RE_SPM_PACKAGE_URL.finditer(content):
                    name = match.group(1)
                    url = match.group(2)
                    packages_url.append(f"{name} (from {url})" if name else url)
                for match in IOS_RE_SPM_PACKAGE_PATH.finditer(content):
                    name = match.group(1)
                    path_val = match.group(2) 
                    packages_path.append(f"{name} (local path: {path_val})" if name else f"Local path: {path_val}")

            if packages_url:
                deps_summary.append("#### 宣告的遠端套件 (Remote Packages):")
                for pkg in sorted(list(set(packages_url))): deps_summary.append(f"- `{pkg}`")
            if packages_path:
                deps_summary.append("#### 宣告的本機套件 (Local Packages):")
                for pkg in sorted(list(set(packages_path))): deps_summary.append(f"- `{pkg}`")
            
            if not packages_url and not packages_path:
                deps_summary.append("- _未透過 regex 從 Package.swift 提取出特定套件 (或檔案內容較複雜)。_")
        except Exception as e:
            deps_summary.append(f"- _讀取 Package.swift 時發生錯誤: {e}_")
        deps_summary.append("")

    if not found_deps:
        deps_summary.append("_未在專案根目錄找到或解析出常見的 iOS 相依性檔案 (Podfile.lock, Podfile, Package.resolved, Package.swift)。_")
    
    deps_summary.append("\n") 
    return "\n".join(deps_summary)

def snapshot_ios_project(project_path_str, project_display_name, output_dir_path):
    """Generates a snapshot report for a given iOS project."""
    project_root = pathlib.Path(project_path_str)
    if not project_root.is_dir():
        print(f"錯誤：找不到 iOS 專案路徑或該路徑不是目錄：{project_root}")
        return

    print(f"\n--- 正在產生 iOS 快照報告：{project_display_name} ---")
    print(f"專案根目錄：{project_root}")
    
    # Load dynamic ignore patterns from target project
    active_excludes = list(IOS_EXCLUDES)  # Start with defaults
    gitignore_path = project_root / ".gitignore"
    cursorignore_path = project_root / ".cursorignore"
    
    if gitignore_path.exists():
        gitignore_patterns = parse_ignore_patterns(gitignore_path)
        active_excludes.extend(gitignore_patterns)
        print(f"  已載入 {len(gitignore_patterns)} 個 .gitignore 規則")
    
    if cursorignore_path.exists():
        cursorignore_patterns = parse_ignore_patterns(cursorignore_path)
        active_excludes.extend(cursorignore_patterns)
        print(f"  已載入 {len(cursorignore_patterns)} 個 .cursorignore 規則")
    
    markdown_parts = []

    print("  正在產生目錄結構...")
    markdown_parts.append(generate_directory_tree(project_root, TREE_MAX_DEPTH, TREE_INDENT_CHAR, active_excludes, "iOS Project"))

    swift_summary = ["## 主要 Swift 類型與函式"]
    plist_content_md = "" # Changed name to avoid conflict
    counts = {"swift": 0, "plist": 0}

    print("  正在掃描並解析檔案...")
    found_plist_path = None
    possible_plist_locations = [p for p in project_root.rglob("Info.plist") if not is_excluded(str(p), str(project_root), active_excludes)]
    if possible_plist_locations:
        possible_plist_locations.sort(key=lambda p: (project_root.name not in str(p.parent), len(p.parts)))
        found_plist_path = possible_plist_locations[0]
        
    if found_plist_path:
        print(f"    在以下位置找到 Info.plist：{found_plist_path.relative_to(project_root)}")
        counts["plist"] += 1
        plist_content_md = ios_parse_info_plist(found_plist_path)
    else:
        print("    找不到 Info.plist 或已被排除。")


    for item in project_root.rglob("*"):
        if is_excluded(str(item), str(project_root), active_excludes): continue
        if item.is_file():
            rel_path = str(item.relative_to(project_root))
            if item.suffix == '.swift':
                counts["swift"] += 1
                swift_summary.append(f"### 檔案: `{rel_path}`")
                parsed = ios_parse_swift_file(item)
                swift_summary.extend(parsed if parsed else ["  - (無可擷取的內容)"])
                swift_summary.append("\n")

    if counts["swift"] == 0: swift_summary.append("_未找到或未解析出 Swift 檔案。_\n")
    markdown_parts.append("\n".join(swift_summary))

    if plist_content_md: markdown_parts.append(plist_content_md)
    elif counts["plist"] > 0 : markdown_parts.append("### Info.plist 摘要\n_找到 Info.plist，但未提取出具體內容。_\n")
    else: markdown_parts.append("### Info.plist 摘要\n_找不到 Info.plist。_\n")
    
    # --- Xcode Project Settings Analysis ---
    print("  正在分析 Xcode 專案設定...")
    # Pass project_root as a string, as expected by generate_xcode_settings_report_markdown
    xcode_settings_md = generate_xcode_settings_report_markdown(str(project_root))
    markdown_parts.append(xcode_settings_md)
    # --- End of Xcode Project Settings Analysis ---

    print("  正在解析相依性檔案...")
    markdown_parts.append(ios_parse_dependency_files(project_root))
    
    markdown_parts.append("## 其他 iOS 檔案 (Other iOS Artifacts)\n_可在此處新增針對 Storyboards, XIBs, Asset Catalogs 的進一步分析。_\n")

    output_filename = f"{project_display_name.replace(' ', '_')}_iOS_Snapshot.md"
    output_path = output_dir_path / output_filename
    
    print(f"  正在將 iOS 報告寫入至：{output_path}")
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# iOS 專案快照：{project_display_name}\n\n")
            f.write(f"_報告產生時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n")
            f.write("\n---\n\n".join(markdown_parts))
        print(f"  成功產生 iOS 快照：{output_path}")
    except Exception as e:
        print(f"  錯誤：無法將 iOS 報告寫入至 {output_path}: {e}")


# --- 4. Main Orchestration ---
def save_config_file():
    """儲存目前的 CONFIG 全域變數至 config.json"""
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(CONFIG, f, indent=4, ensure_ascii=False)
        print(f"  [系統] 設定檔已更新: {CONFIG_FILE_PATH.resolve()}")
        return True
    except Exception as e:
        print(f"  [錯誤] 儲存設定檔時發生問題: {e}")
        return False

def manage_projects():
    """專案管理選單 (新增/修改/刪除)"""
    while True:
        projects = CONFIG.get("projects", {})
        print("\n--- 專案管理模式 ---")
        print("1. 新增專案 (Add Project)")
        print("2. 移除專案 (Remove Project)")
        print("3. 編輯專案路徑 (Edit Project Paths)")
        print("4. 返回主選單 (Back)")
        
        choice = input("請選擇操作 (1-4): ").strip()
        
        if choice == '1': # Add
            name = input("輸入新專案名稱 (例如 MyNewApp): ").strip()
            if not name:
                print("名稱不能為空。")
                continue
            if name in projects:
                print(f"專案 '{name}' 已存在。")
                continue
                
            android_path = scan_and_select_project('android')
            
            # 嘗試智慧預測 iOS 路徑
            ios_prediction = predict_related_path(android_path, 'ios')
            ios_path = None
            
            if ios_prediction:
                print(f"\n🔍 偵測到可能的 iOS 專案路徑: {ios_prediction}")
                confirm_pred = input("  是否直接使用？ (Y/n): ").strip().lower()
                if confirm_pred != 'n':
                    ios_path = ios_prediction
            
            if not ios_path:
                ios_path = scan_and_select_project('ios')
            
            projects[name] = {
                "name": name,
                "android_path": android_path,
                "ios_path": ios_path
            }
            save_config_file()
            print(f"專案 '{name}' 已新增。")

        elif choice == '2': # Remove
            if not projects:
                print("目前沒有專案。")
                continue
            
            keys = list(projects.keys())
            for i, k in enumerate(keys):
                print(f"  {i+1}. {projects[k].get('name', k)}")
            
            try:
                idx = int(input(f"選擇要移除的專案 (1-{len(keys)}), 或 0 取消: "))
                if 1 <= idx <= len(keys):
                    key_to_remove = keys[idx-1]
                    confirm = input(f"確定要移除 '{key_to_remove}' 嗎? (y/N): ").lower()
                    if confirm == 'y':
                        del projects[key_to_remove]
                        save_config_file()
                        print(f"專案 '{key_to_remove}' 已移除。")
                elif idx == 0:
                    continue
            except ValueError:
                print("輸入無效。")

        elif choice == '3': # Edit
            if not projects:
                print("目前沒有專案。")
                continue
            
            keys = list(projects.keys())
            for i, k in enumerate(keys):
                print(f"  {i+1}. {projects[k].get('name', k)}")
                
            try:
                idx = int(input(f"選擇要編輯的專案 (1-{len(keys)}), 或 0 取消: "))
                if 1 <= idx <= len(keys):
                    key_to_edit = keys[idx-1]
                    proj = projects[key_to_edit]
                    print(f"\n編輯專案: {proj.get('name', key_to_edit)}")
                    print(f"目前 Android 路徑: {proj.get('android_path', '(未設定)')}")
                    print(f"目前 iOS 路徑: {proj.get('ios_path', '(未設定)')}")
                    
                    if input("是否修改 Android 路徑? (y/N): ").lower() == 'y':
                        new_android = scan_and_select_project('android')
                        if new_android: proj['android_path'] = new_android

                    if input("是否修改 iOS 路徑? (y/N): ").lower() == 'y':
                        new_ios = scan_and_select_project('ios')
                        if new_ios: proj['ios_path'] = new_ios
                    
                    save_config_file()
                    print("專案已更新。")
            except ValueError:
                print("輸入無效。")

        elif choice == '4': # Back
            break
        else:
            print("無效的選擇。")

def get_user_choices():
    """Gets project and platform choices from the user."""
    while True:
        # Reload projects from global CONFIG every time we show the menu
        # because manage_projects() might have modified it.
        current_projects = CONFIG.get("projects", {})
        project_options = list(current_projects.keys())
        
        print("\n=== Snapshot Tool 主選單 ===")
        
        if not project_options:
             print("目前無專案 (No projects available)")
             print("請輸入 'M' 進入管理模式新增專案。")
        else:
            print("[執行特定專案] (輸入數字):")
            for i, name in enumerate(project_options):
                p_name = current_projects[name].get('name', name)
                print(f"  {i+1}. 執行: {p_name}")
            
        print("\n[其他操作]:")
        if project_options:
            print(f"  A. 🚀 執行所有專案 (Run All)")
        print(f"  M. 🔧 專案管理 (新增/移除/編輯)")
        print(f"  Q. 離開 (Quit)")

        choice_raw = input(f"\n請輸入專案編號 (例如 1) 或操作代碼 (A/M/Q): ").strip().lower()
        
        if choice_raw == 'q':
            print("再見！")
            exit(0)
            
        if choice_raw == 'm':
            manage_projects()
            continue # Loop back to redraw menu
            
        if choice_raw == 'a' and project_options:
            selected_projects = project_options
        else:
            try:
                choice = int(choice_raw)
                if 1 <= choice <= len(project_options):
                    selected_projects = [project_options[choice-1]]
                else:
                    print(f"無效的數字選擇: {choice}。請輸入 1 到 {len(project_options)} 之間的數字。")
                    continue
            except ValueError:
                print("無效的輸入。請輸入專案編號數字，或 M/A/Q。")
                continue

        # Platform Selection (Only happens if a project was selected)
        print("\n可用平台 (Available Platforms):")
        print("  1. Android")
        print("  2. iOS")
        print("  3. 雙平台 (Both)")

        while True:
            try:
                p_choice = input(f"選擇平台 (1-3) [預設 3]: ").strip()
                if not p_choice: # Default to both
                     selected_platforms = ['android', 'ios']
                     break
                if p_choice == '1':
                    selected_platforms = ['android']
                    break
                elif p_choice == '2':
                    selected_platforms = ['ios']
                    break
                elif p_choice == '3':
                    selected_platforms = ['android', 'ios']
                    break
                else:
                    print("無效的選擇。")
            except ValueError:
                pass
                
        return selected_projects, selected_platforms

def main():
    """Main execution function."""
    # check = True logic removed or moved inside loop as it was static check based on initial load
    
    selected_project_keys, selected_platforms = get_user_choices()
    
    # Reload project configs in case they were changed in the menu
    current_project_configs = CONFIG.get("projects", {})

    OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n報告將儲存至：{OUTPUT_BASE_DIR}")

    for project_key in selected_project_keys:
        project_config = current_project_configs.get(project_key)
        if not project_config:
             print(f"錯誤：找不到專案設定 '{project_key}'")
             continue
             
        project_display_name = project_config.get("name", project_key)

        if "android" in selected_platforms:
            android_path_str = project_config.get("android_path")
            if android_path_str and android_path_str != "/path/to/your/...": 
                 android_path_str = os.path.expanduser(android_path_str) 
                 if os.path.isdir(android_path_str):
                    snapshot_android_project(android_path_str, project_display_name, OUTPUT_BASE_DIR)
                 else:
                    print(f"略過 {project_display_name} 的 Android 部分：路徑 '{android_path_str}' 不是一個有效的目錄。")
            else:
                print(f"略過 {project_display_name} 的 Android 部分：路徑未設定。")

        if "ios" in selected_platforms:
            ios_path_str = project_config.get("ios_path")
            if ios_path_str and ios_path_str != "/path/to/your/...": 
                ios_path_str = os.path.expanduser(ios_path_str) 
                if os.path.isdir(ios_path_str):
                    snapshot_ios_project(ios_path_str, project_display_name, OUTPUT_BASE_DIR)
                else:
                    print(f"略過 {project_display_name} 的 iOS 部分：路徑 '{ios_path_str}' 不是一個有效的目錄。")
            else:
                print(f"略過 {project_display_name} 的 iOS 部分：路徑未設定。")
    
    print("\n--- 已完成所有選定的快照報告。 ---")

if __name__ == "__main__":
    main()
