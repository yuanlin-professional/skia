# CMake macOS 资产创建脚本

> 源文件: infra/bots/assets/cmake_mac/create.py

## 概述

从官方发布下载并准备 CMake macOS 版本的资产创建脚本。CMake 是跨平台的构建系统生成器，Skia 的某些依赖项使用 CMake 构建。该脚本下载 CMake 3.31.8 macOS universal 二进制包，解压并提取必要的文件。

## 架构位置

位于 `infra/bots/assets/cmake_mac/`，为 Skia macOS 构建环境提供 CMake 工具，用于编译第三方依赖如 zlib、libpng 等使用 CMake 的库。

## 主要类与结构体

函数式风格，使用标准库和 Skia utils 模块。

### 模块级常量

```python
VERSION = '3.31.8'
URL = 'https://github.com/Kitware/CMake/releases/download/v%s/cmake-%s-macos-universal.tar.gz' % (VERSION, VERSION)
```

universal 二进制同时支持 Intel 和 Apple Silicon Mac。

## 公共 API 函数

### `create_asset(target_dir)`
执行流程：
1. 在临时目录下载 CMake tar.gz
2. 解压文件
3. 从 CMake.app bundle 提取 bin 和 share 目录
4. 移动到目标目录

**实现**:
```python
with utils.tmp_dir():
    subprocess.check_call(['wget', URL, '--output-document=cmake.tar.gz'])
    subprocess.check_call(['tar', '--extract', '--gunzip', '--file', 'cmake.tar.gz'])
    cmake_dir = os.path.join(f'cmake-{VERSION}-macos-universal', 'CMake.app', 'Contents')
    for d in ['bin', 'share']:
        subprocess.check_call(['mv', os.path.join(cmake_dir, d), target_dir])
```

### `main()`
解析参数并执行资产创建。

## 内部实现细节

### macOS App Bundle 结构

CMake macOS 发布采用 App Bundle 格式：
```
cmake-3.31.8-macos-universal/
└── CMake.app/
    └── Contents/
        ├── bin/        # 可执行文件
        ├── share/      # 模块和文档
        ├── MacOS/      # GUI 应用
        └── Resources/  # 资源文件
```

脚本只提取 `bin/` 和 `share/`，这是命令行使用所需的全部内容。

### Universal 二进制

macOS universal 二进制包含两种架构：
- x86_64 (Intel)
- arm64 (Apple Silicon)

这使得同一资产可在所有 Mac 上使用。

## 依赖关系

- **wget**: 下载工具
- **tar**: 解压工具
- **Skia utils**: `tmp_dir()` 上下文管理器

## 设计模式与设计决策

### 最小化提取

只提取 bin 和 share，不包括：
- GUI 应用（MacOS/ 目录）
- 开发文档（Resources/ 目录）

减小资产体积约 50%。

### 版本选择

CMake 3.31.8 是 2024 年的最新稳定版本，支持：
- C++20/23
- 最新的 Apple SDK
- M系列芯片优化

## 性能考量

- 下载大小: 约 50 MB
- 解压后: 约 120 MB
- 最小化后: 约 60 MB
- 总时间: 10-30 秒

## 相关文件

- `infra/bots/assets/cmake_linux/create.py`: Linux 版本
- 第三方库的 CMakeLists.txt 使用该 CMake
