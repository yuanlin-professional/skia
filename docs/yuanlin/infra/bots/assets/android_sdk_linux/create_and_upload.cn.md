# Android SDK Linux 资产创建与上传脚本

> 源文件: infra/bots/assets/android_sdk_linux/create_and_upload.py

## 概述

Android SDK Linux 版本的资产创建和上传编排脚本。该脚本从本地已安装的 Android SDK 目录创建资产包并上传到 CIPD，支持通过命令行参数或环境变量指定 SDK 路径。

## 架构位置

位于 `infra/bots/assets/android_sdk_linux/`，为 Skia Android 开发和 CI 系统提供完整的 Android SDK 工具集，包括构建工具、平台文件和系统镜像。

## 主要类与结构体

函数式风格，依赖标准库和本地 create 模块。

## 公共 API 函数

### `main()`

执行流程：
1. 解析 `--android_sdk_root` 参数或读取环境变量
2. 验证 SDK 路径有效性
3. 通过环境变量传递路径给 create.py
4. 定位 sk 工具
5. 调用 sk asset upload 执行上传

**Android SDK 路径解析**:
```python
android_sdk_root = args.android_sdk_root
if not android_sdk_root:
    android_sdk_root = (os.environ.get('ANDROID_HOME') or
                        os.environ.get('ANDROID_SDK_ROOT'))
if not android_sdk_root:
    raise Exception('No --android_sdk_root provided and no ANDROID_HOME or '
                    'ANDROID_SDK_ROOT environment variables.')
```

支持三种方式指定 SDK 路径：
1. `--android_sdk_root` 命令行参数
2. `ANDROID_HOME` 环境变量（传统）
3. `ANDROID_SDK_ROOT` 环境变量（新标准）

## 内部实现细节

### 环境变量优先级

优先使用命令行参数，然后尝试环境变量。这种设计：
- 提供灵活性
- 支持不同开发环境
- 兼容新旧标准

### 环境变量通信

与 Windows 工具链类似，使用环境变量传递参数给 create.py：
```python
os.environ[create.ENV_VAR] = android_sdk_root
```

### sk 工具路径

使用相对路径定位 sk 工具，从当前目录上溯到项目根目录的 bin/sk。

## 依赖关系

- **sk 工具**: Skia 资产管理 CLI
- **create.py**: 实际的资产创建逻辑
- **本地 Android SDK**: 需要预先安装完整的 SDK

## 设计模式与设计决策

### 多路径支持

支持 ANDROID_HOME 和 ANDROID_SDK_ROOT 是为了兼容：
- 旧版本 Android 工具使用 ANDROID_HOME
- 新版本推荐使用 ANDROID_SDK_ROOT
- 不同 IDE 和构建系统的约定

### 从本地复制

Android SDK 体积巨大（10-50 GB），从本地复制而非下载确保：
- 开发者可以选择需要的组件
- 避免重复下载大文件
- 支持自定义配置

## 性能考量

Android SDK 包含大量文件，复制和上传时间可能需要：
- 复制: 5-30 分钟（取决于 SDK 大小和磁盘速度）
- 压缩: 10-20 分钟
- 上传: 10-60 分钟（取决于网络带宽）

## 相关文件

- `create.py`: 复制 SDK 目录的实际逻辑
- `__init__.py`: Python 包标识
- Android Studio 或 sdkmanager 安装的本地 SDK
