# Android NDK Windows 资产创建脚本

> 源文件: infra/bots/assets/android_ndk_windows/create.py

## 概述

这是一个用于下载和准备 Android NDK（Native Development Kit）Windows 版本资产的脚本。Android NDK 是用于在 Android 应用中使用 C/C++ 代码的工具集，包含交叉编译器、系统头文件、库文件等。该脚本自动下载指定版本（r27d）的 NDK 压缩包，解压并整理目录结构，生成可供 Skia Windows 构建环境使用的 NDK 资产。

## 架构位置

该脚本位于 `infra/bots/assets/android_ndk_windows/` 目录，是 Skia 基础设施跨平台构建支持的重要组成部分。Android NDK 资产用于：
- 在 Windows 环境中编译 Android 平台的 Skia 库
- 支持 ARM、ARM64、x86、x86_64 等多种 Android 架构
- 为 Skia 的 Android 集成和 CanvasKit 等项目提供构建工具链

该资产使 Skia CI 能够在 Windows 主机上执行 Android 交叉编译任务。

## 主要类与结构体

脚本采用简洁的函数式编程风格，依赖 Python 标准库：

- **argparse**: 命令行参数解析
- **glob**: 文件名模式匹配，用于查找解压后的目录
- **os.path**: 路径操作
- **shutil**: 文件和目录移动操作
- **subprocess**: 外部命令执行

### 模块级常量

```python
NDK_VER = "android-ndk-r27d"
NDK_URL = "https://dl.google.com/android/repository/%s-windows.zip" % NDK_VER
```

固定使用 Android NDK r27d 版本，这是 2024 年的稳定 LTS 版本，支持最新的 Android API 级别和工具链特性。

## 公共 API 函数

### `create_asset(target_dir)`

核心资产创建函数，执行下载、解压和目录整理流程。

**参数**:
- `target_dir` (str): 存放 NDK 文件的目标目录

**执行流程**:
1. 使用 curl 从 Google 服务器下载 NDK Windows 版本的 zip 包
2. 使用 unzip 解压到目标目录
3. 使用 glob 查找解压后的版本化目录
4. 将版本化目录内的所有内容移动到目标目录根层级
5. 删除下载的 zip 文件

**实现细节**:
```python
subprocess.check_call(["curl", NDK_URL, "-o", "ndk.zip"])
subprocess.check_call(["unzip", "ndk.zip", "-d", target_dir])

# 将 android-ndk-r27d/* 移动到 target_dir/*
for f in glob.glob(os.path.join(target_dir, NDK_VER, "*")):
    shutil.move(f, target_dir)

subprocess.check_call(["rm", "ndk.zip"])
```

这种设计避免了嵌套的版本化目录，简化了后续使用。

### `main()`

脚本入口函数，负责参数解析和函数调用。

**命令行参数**:
- `--target_dir, -t`: 必需参数，指定 NDK 安装目录

## 内部实现细节

### 下载策略

使用 curl 下载而非 Python 库的原因：
- **进度显示**: curl 默认显示下载进度
- **可靠性**: 支持断点续传和重试
- **一致性**: 与其他基础设施脚本保持一致
- **外部工具**: CI 环境通常预装 curl

**URL 模式**: Google 的 Android 仓库使用规范的命名模式：
```
https://dl.google.com/android/repository/android-ndk-{version}-{platform}.zip
```

### 解压和目录扁平化

NDK zip 包的结构：
```
ndk.zip
└── android-ndk-r27d/
    ├── build/
    ├── toolchains/
    ├── platforms/
    └── ...
```

脚本将其转换为：
```
target_dir/
├── build/
├── toolchains/
├── platforms/
└── ...
```

这种扁平化通过 `glob` 和 `shutil.move` 实现：
```python
for f in glob.glob(os.path.join(target_dir, NDK_VER, "*")):
    shutil.move(f, target_dir)
```

**glob 模式**: `android-ndk-r27d/*` 匹配版本化目录下的所有顶层文件和目录。

### 清理策略

下载完成后删除 zip 文件：
```python
subprocess.check_call(["rm", "ndk.zip"])
```

这样做是为了：
- 节省磁盘空间（NDK zip 约 1 GB）
- 避免资产包包含冗余文件
- 保持工作目录整洁

### 跨平台考量

虽然脚本下载 Windows 版本 NDK，但脚本本身可能在 Linux 环境运行（CI 系统）。因此：
- 使用 Unix 风格的命令（curl, unzip, rm）
- 假设 Windows 工具可用或通过 WSL/Cygwin 等兼容层提供
- 实际部署时将资产包传输到 Windows 环境

## 依赖关系

### 外部工具依赖

- **curl**: 文件下载工具
- **unzip**: zip 文件解压工具
- **rm**: 文件删除命令（Unix 工具）

### 网络依赖

- **Google 服务器**: 需要访问 `dl.google.com`
- **带宽要求**: NDK 压缩包约 1 GB，需要稳定的网络连接

### 磁盘空间

- **下载**: ~1 GB（zip 文件）
- **解压**: ~3-4 GB（解压后的 NDK）
- **峰值**: ~4-5 GB（下载和解压同时存在）
- **最终**: ~3-4 GB（删除 zip 后）

### Python 依赖

- **Python 版本**: 兼容 Python 2 和 Python 3
- **标准库**: argparse, glob, os.path, shutil, subprocess

## 设计模式与设计决策

### 版本固定策略

使用 NDK r27d 的考量：
- **稳定性**: 这是一个 LTS（长期支持）版本
- **兼容性**: 支持广泛的 Android API 级别（16-35）
- **功能完整**: 包含最新的 Clang 编译器和构建工具
- **可重现性**: 固定版本确保构建一致性

### 目录扁平化设计

将嵌套的版本化目录扁平化的原因：
- **简化路径**: 无需在配置中硬编码版本号
- **易于使用**: 用户只需知道 NDK 根目录
- **版本无关**: 更换 NDK 版本时路径不变

### 无校验和验证

与某些其他资产脚本不同，此脚本不验证下载文件的校验和。这种选择的权衡：

**风险**:
- 无法检测下载损坏
- 无法检测中间人攻击

**缓解措施**:
- Google 服务器使用 HTTPS，提供传输层安全
- curl 会检测传输错误
- 解压失败会自动报错

**改进建议**: 可以添加 SHA256 校验以提升安全性。

### 简单清理策略

使用 `rm` 而非 Python 的 `os.remove()`：
- **一致性**: 与其他命令保持风格一致
- **简单性**: 无需额外的错误处理
- **功能等价**: 两种方式效果相同

## 性能考量

### 下载时间

NDK 压缩包约 1 GB，下载时间取决于网络速度：
- **100 Mbps**: 约 80 秒
- **1 Gbps**: 约 8 秒
- **典型 CI**: 20-60 秒

这是整个流程的主要瓶颈。

### 解压时间

解压 1 GB 的 zip 文件到 3-4 GB 目录：
- **SSD**: 30-60 秒
- **HDD**: 60-120 秒

解压时间受磁盘 I/O 和 CPU 性能影响。

### 目录移动

`shutil.move()` 在同一文件系统内是重命名操作：
- **时间**: <1 秒（只修改目录表）
- **高效**: O(1) 复杂度

### 总体执行时间

典型场景：
- 下载: 20-60 秒
- 解压: 30-60 秒
- 移动: <1 秒
- 清理: <1 秒
- 总计: 50-120 秒（约 1-2 分钟）

### 优化建议

1. **并行下载**: 如果需要多个平台的 NDK，可以并行下载
2. **增量更新**: 只下载变化的部分（需要服务端支持）
3. **本地缓存**: 缓存已下载的 NDK，避免重复下载
4. **校验和**: 添加校验和验证，避免重新下载损坏的文件

## 相关文件

### 同系列脚本

- **`infra/bots/assets/android_ndk_linux/create.py`**: Linux 版本 NDK 资产脚本，几乎相同的实现
- **`infra/bots/assets/android_ndk_darwin/create.py`**: macOS 版本（如果存在）

这些脚本只在 URL 中的平台名称不同（`-windows`, `-linux`, `-darwin`）。

### 资产管理

- **`infra/bots/assets/android_ndk_windows/VERSION`**: 资产版本标识
- **`infra/bots/assets/android_ndk_windows/download.py`**: 下载脚本
- **`infra/bots/assets/android_ndk_windows/upload.py`**: 上传脚本

### Android 构建配置

- **`gn/android.gni`**: GN 构建系统的 Android 配置
- **`toolchain/linux-android/`**: Android 工具链配置
- **`BUILD.gn`**: 指定 Android NDK 路径

### CI 任务

- **`infra/bots/tasks.json`**: 定义使用 Android NDK 的构建任务
- **`infra/bots/recipes/`**: 构建配方，配置 Android 交叉编译

### Android NDK 文档

- 官方网站: https://developer.android.com/ndk
- 下载页面: https://developer.android.com/ndk/downloads
- r27 发布说明: https://github.com/android/ndk/wiki/Changelog-r27
- 构建系统文档: https://developer.android.com/ndk/guides/build

Android NDK 是 Skia 支持 Android 平台的核心依赖，使得 Skia 能够为数十亿 Android 设备提供高性能图形渲染能力。
