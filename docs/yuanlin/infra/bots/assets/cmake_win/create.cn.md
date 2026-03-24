# create.py

> 源文件: infra/bots/assets/cmake_win/create.py

## 概述

`create.py` 用于创建 Windows 平台的 CMake 构建工具资产。与 Linux 版本类似，从 CMake 官方 GitHub Releases 下载预编译的 Windows 二进制包。

## 架构位置

该资产为 Windows 构建系统提供 CMake 工具，用于构建第三方依赖（如 ANGLE、Dawn）。

## 公共 API 函数

### create_asset(target_dir)
从 CMake 官方 GitHub 下载 Windows x86_64 版本并提取 `bin` 和 `share` 目录。

**实现**：
```python
VERSION = '3.31.8'
URL = ('https://github.com/Kitware/CMake/releases/download/v%s/'
       'cmake-%s-windows-x86_64.zip') % (VERSION, VERSION)

def create_asset(target_dir):
    with utils.tmp_dir():
        subprocess.check_call(['wget', URL, '--output-document=cmake.zip'])
        subprocess.check_call(['unzip', 'cmake.zip'])
        cmake_dir = 'cmake-%s-windows-x86_64' % VERSION
        for d in ['bin', 'share']:
            subprocess.check_call(['mv', os.path.join(cmake_dir, d), target_dir])
```

## 内部实现细节

### 与 Linux 版本的差异

| 特性 | Linux | Windows |
|------|-------|---------|
| URL | `.tar.gz` | `.zip` |
| 解压工具 | tar | unzip |
| 可执行文件 | `cmake` | `cmake.exe` |
| 平台标识 | `linux-x86_64` | `windows-x86_64` |

### 版本一致性
使用与 Linux 版本相同的 CMake 版本（3.31.8），确保跨平台构建行为一致。

### 选择性提取
只提取必要的 `bin/` 和 `share/` 目录：
- **bin/**: cmake.exe, ctest.exe, cpack.exe 等可执行文件
- **share/**: CMake 模块、模板和文档

忽略不必要的文档和手册页，减小资产大小。

### 目录结构优化
解压后的完整包含多个目录，但只移动必要部分：
```
cmake-3.31.8-windows-x86_64/
├── bin/          # 需要
├── share/        # 需要
├── doc/          # 忽略
└── man/          # 忽略
```

## 依赖关系

- **wget**: 下载工具
- **unzip**: ZIP 解压工具（Windows 10+ 内置）
- **`utils`**: Skia 工具模块（提供 `tmp_dir`）

## 设计模式与设计决策

### ZIP 格式
Windows 使用 ZIP 而非 tar.gz：
- 更好的 Windows 原生支持
- 官方为 Windows 提供 ZIP 包
- 工具兼容性更好

### 官方二进制
使用 Kitware 官方预编译包：
- 避免在 Windows 上编译 CMake 的复杂性
- 官方测试和优化
- 快速部署（< 1 分钟 vs. ~15 分钟编译）

## 性能考量

- **下载时间**: 20-40 秒（~50 MB）
- **解压时间**: 5-10 秒
- **目录移动**: < 1 秒
- **总时间**: 30-60 秒
- **磁盘空间**: ~50 MB（仅 bin 和 share）

## 相关文件

- **`cmake_linux/create.py`**: Linux 版本
- **`cmake_mac/create.py`**: macOS 版本
- **CMake 官网**: `https://cmake.org/`
- **GitHub Releases**: `https://github.com/Kitware/CMake/releases`
