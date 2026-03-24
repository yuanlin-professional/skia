# create.py

> 源文件: infra/bots/assets/clang_mac_arm/create.py

## 概述

`create.py` 用于创建 macOS ARM（Apple Silicon）平台的 Clang 编译器工具链资产。该脚本从 Chromium 项目的 GCS 下载为 Apple Silicon 预编译的通用 ARM 二进制包。

## 架构位置

该脚本为 Skia 在 Apple Silicon Mac 设备（M1/M2/M3 系列）上提供原生 ARM64 Clang 编译器支持。

## 公共 API 函数

### create_asset(target_dir)
从 Chromium GCS 下载 macOS ARM64 Clang 工具链，解压到目标目录并清理临时文件。

### main()
解析命令行参数（`--target_dir`）并调用 `create_asset()`。

## 内部实现细节

### 版本配置
```python
TAR_FILE = "clang-llvmorg-22-init-14273-gea10026b-2.tar.xz"
GS_URL = f'https://commondatastorage.googleapis.com/chromium-browser-clang/Mac_arm64/{TAR_FILE}'
```
从 Chromium 的 `Mac_arm64` 目录下载通用 ARM 二进制文件，包含 LLVM 22 开发版本。

### 架构特性
- **架构**: ARM64（Apple Silicon 原生）
- **兼容性**: 在 M1/M2/M3 Mac 上原生运行，性能优于 Rosetta 2
- **预构建库**: 不包含 libc++ 预构建库

### 下载和解压流程
1. 使用 `wget` 下载 xz 压缩的 tarball（~300 MB）
2. 使用 `tar xf` 解压（支持 xz 格式）
3. 删除临时 tarball 节省空间

## 依赖关系

### 系统依赖
- **wget**: 下载工具（需通过 `brew install wget` 安装）
- **tar**: macOS 内置，支持 xz 格式

### Python 依赖
- 标准库：`argparse`, `os`, `subprocess`, `sys`
- Skia 模块：`utils`（提供 `chdir` 上下文管理器）

## 设计模式与设计决策

### 预编译包策略
选择下载 Chromium 的预编译包而非自行编译，原因：
- 构建 LLVM 需要 30-60 分钟
- Chromium 团队已针对 Apple Silicon 优化
- 可在任何平台（包括 Linux CI）上创建资产

### 版本获取
通过运行 Chromium 的更新脚本获取最新版本：
```bash
tools/clang/scripts/update.py --output-dir /tmp/mac_clang --host-os mac-arm64
```

## 性能考量

- **下载时间**: 30-60 秒（300 MB，取决于网络速度）
- **解压时间**: 15-30 秒（xz 解压较慢但压缩率高）
- **总执行时间**: 1-2 分钟（快速网络 + SSD）
- **磁盘空间**: 下载 ~300 MB，解压后 ~700 MB

## 相关文件

- **`clang_mac_intel/create.py`**: macOS Intel 版本
- **`clang_linux/create.py`**: Linux 版本（Docker 编译）
- **`clang_win/create.py`**: Windows 版本
- **`infra/bots/utils.py`**: Skia 工具模块
- **Chromium 参考**: `tools/clang/scripts/update.py`
