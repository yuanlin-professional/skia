# Android NDK Linux 资产创建脚本

> 源文件: infra/bots/assets/android_ndk_linux/create.py

## 概述

这是一个用于下载和准备 Android NDK（Native Development Kit）Linux 版本资产的脚本。该脚本的功能和实现与 Windows 版本几乎完全相同，只是下载的是 Linux 平台的 NDK 压缩包。Android NDK 包含完整的 C/C++ 交叉编译工具链，用于在 Linux 主机上为 Android 设备编译本地代码。这是 Skia CI 系统中最常用的 NDK 资产，因为大多数 CI 构建环境运行在 Linux 上。

## 架构位置

该脚本位于 `infra/bots/assets/android_ndk_linux/` 目录，是 Skia 基础设施中最重要的跨平台构建资产之一。Linux 版本的 NDK 资产在以下场景中使用：
- CI/CD 系统的 Android 构建任务（主要场景）
- 开发者在 Linux 工作站上进行 Android 开发
- Docker 容器中的自动化构建
- 跨平台构建和测试流水线

由于 Skia 的 CI 系统主要运行在 Linux 环境，这个资产的使用频率远高于 Windows 和 macOS 版本。

## 主要类与结构体

脚本采用简洁的函数式编程风格，依赖 Python 标准库：

- **argparse**: 命令行参数解析
- **glob**: 文件名模式匹配
- **os.path**: 路径操作
- **shutil**: 文件和目录移动
- **subprocess**: 外部命令执行

### 模块级常量

```python
NDK_VER = "android-ndk-r27d"
NDK_URL = "https://dl.google.com/android/repository/%s-linux.zip" % NDK_VER
```

唯一的区别在于 URL 中的平台标识为 `-linux` 而非 `-windows`。

## 公共 API 函数

### `create_asset(target_dir)`

核心资产创建函数，与 Windows 版本完全相同的实现逻辑。

**参数**:
- `target_dir` (str): 存放 NDK 文件的目标目录

**执行流程**:
1. 使用 curl 下载 NDK Linux 版本的 zip 包
2. 使用 unzip 解压到目标目录
3. 将版本化目录的内容移动到目标目录根层级
4. 删除下载的 zip 文件

**实现细节**:
```python
subprocess.check_call(["curl", NDK_URL, "-o", "ndk.zip"])
subprocess.check_call(["unzip", "ndk.zip", "-d", target_dir])
for f in glob.glob(os.path.join(target_dir, NDK_VER, "*")):
    shutil.move(f, target_dir)
subprocess.check_call(["rm", "ndk.zip"])
```

### `main()`

脚本入口函数，负责参数解析和函数调用。

**命令行参数**:
- `--target_dir, -t`: 必需参数，指定 NDK 安装目录

## 内部实现细节

### 平台特定差异

相比 Windows 版本，Linux 版本的 NDK 有以下特点：

**包大小**:
- Windows 版本: ~1.0 GB（包含 .exe 文件）
- Linux 版本: ~950 MB（ELF 二进制文件更紧凑）

**可执行文件格式**:
- Windows: PE 格式，.exe 扩展名
- Linux: ELF 格式，无扩展名

**权限处理**:
Linux 版本解压后会保留 Unix 权限位：
- 可执行文件自动具有执行权限
- 无需额外的 `chmod` 操作

### 工具链内容

解压后的 NDK 目录结构（Linux 和 Windows 相同）：
```
target_dir/
├── build/              # 构建系统脚本和模块
├── meta/               # 元数据和文档
├── platforms/          # Android API 级别的头文件和库
├── prebuilt/           # 预编译工具
├── python-packages/    # Python 模块
├── shader-tools/       # 着色器编译工具
├── simpleperf/         # 性能分析工具
├── sources/            # 示例代码和辅助库
├── toolchains/         # 编译器工具链
│   ├── llvm/           # Clang/LLVM 工具链
│   │   ├── prebuilt/
│   │   │   └── linux-x86_64/  # Linux 主机工具
│   │   │       ├── bin/        # 编译器可执行文件
│   │   │       ├── lib/        # 库文件
│   │   │       └── ...
│   └── ...
├── wrap.sh             # 工具包装脚本
└── ...
```

### Linux 特有的优势

在 Linux 环境中使用 NDK 的优势：
- **性能**: Linux 文件系统和进程管理效率更高
- **兼容性**: NDK 的构建系统针对 Linux 优化
- **工具链**: 许多开发工具原生为 Linux 设计
- **CI 集成**: 大多数 CI 系统基于 Linux

### 解压行为差异

unzip 在 Linux 上的行为：
- 自动保留文件权限和时间戳
- 支持符号链接（NDK 可能包含符号链接）
- 处理长文件名更可靠

## 依赖关系

### 外部工具依赖

- **curl**: 文件下载工具（Linux 通常预装）
- **unzip**: zip 文件解压工具（需要安装）
- **rm**: 文件删除命令（coreutils 的一部分）

**安装命令**:
```bash
# Debian/Ubuntu
sudo apt-get install curl unzip

# RHEL/CentOS
sudo yum install curl unzip
```

### 系统要求

- **操作系统**: Linux 内核 2.6 或更高
- **架构**: x86_64（NDK 工具是 64 位的）
- **磁盘空间**: 至少 5 GB 可用空间
- **内存**: 至少 2 GB（编译大型项目时需要更多）

### Python 依赖

- **Python 版本**: 兼容 Python 2.7 和 Python 3.x
- **标准库**: argparse, glob, os, shutil, subprocess

## 设计模式与设计决策

### 代码共享机会

Linux 和 Windows 版本的脚本几乎完全相同，只有 URL 不同。这种重复可以通过以下方式优化：

**方案 1: 参数化平台**
```python
def create_asset(target_dir, platform='linux'):
    NDK_URL = f"https://dl.google.com/android/repository/{NDK_VER}-{platform}.zip"
    # 其余逻辑相同
```

**方案 2: 共享模块**
```python
# common.py
def download_ndk(platform, target_dir):
    # 通用实现
```

目前的设计选择独立脚本，优点是：
- **简单性**: 每个脚本自包含
- **独立性**: 修改一个平台不影响其他
- **清晰性**: 无需理解抽象层

### 版本管理策略

NDK r27d 是一个重要的版本里程碑：
- **Clang 版本**: 18.x
- **C++ 标准**: 支持 C++20
- **API 级别**: 支持 API 16-35
- **工具改进**: 改进的诊断和性能

选择 r27d 而非更新版本的原因：
- **稳定性**: 经过充分测试
- **兼容性**: 与 Skia 的构建系统完全兼容
- **LTS 支持**: 长期支持版本

### 无版本检查

脚本不检查系统是否已安装 NDK 或安装的版本。这种设计：
- **简单**: 无需版本比较逻辑
- **可重现**: 每次都创建全新的资产
- **安全**: 避免使用可能损坏的已有安装

## 性能考量

### Linux 特有的性能优势

相比 Windows，Linux 环境中的性能特点：

**文件系统性能**:
- **ext4/xfs**: 比 NTFS 更高效的小文件处理
- **缓存**: Linux 文件系统缓存更积极
- **并发**: 更好的并发 I/O 性能

**进程创建**:
- **fork/exec**: 比 Windows CreateProcess 快
- **影响**: 编译过程涉及大量进程创建

### 典型执行时间

在标准 CI 环境（如 Google Cloud 虚拟机）：
- 下载: 15-30 秒（取决于网络）
- 解压: 20-40 秒（取决于磁盘）
- 移动: <1 秒
- 清理: <1 秒
- 总计: 35-70 秒

### CI 环境优化

在 CI 环境中的常见优化：
1. **本地缓存**: 使用 CIPD 缓存避免重复下载
2. **预热镜像**: Docker 镜像预安装 NDK
3. **网络代理**: 使用地理位置接近的镜像
4. **并行准备**: 在构建开始前异步下载

### 磁盘空间管理

NDK 是大型资产，CI 系统需要注意：
- **清理策略**: 构建后删除未使用的 NDK
- **共享存储**: 多个构建共享同一 NDK 实例
- **增量更新**: 只在 NDK 版本变化时更新

## 相关文件

### 同系列脚本

- **`infra/bots/assets/android_ndk_windows/create.py`**: Windows 版本，几乎相同的代码
- **`infra/bots/assets/android_ndk_darwin/create.py`**: macOS 版本（如果存在）

### 资产管理

- **`infra/bots/assets/android_ndk_linux/VERSION`**: 资产版本标识
- **`infra/bots/assets/android_ndk_linux/download.py`**: 从 CIPD 下载资产
- **`infra/bots/assets/android_ndk_linux/upload.py`**: 上传资产到 CIPD
- **`infra/bots/assets/android_ndk_linux/__init__.py`**: Python 包标识

### 构建系统集成

- **`gn/toolchain/linux_android.gni`**: GN 工具链定义
- **`gn/android.gni`**: Android 构建配置
- **`.gn`**: GN 根配置，指定 NDK 路径
- **`BUILD.gn`**: 根构建文件

### CI 配置

- **`infra/bots/tasks.json`**: 定义 Android 构建任务
- **`infra/bots/recipes/build.py`**: 构建配方脚本
- **`infra/bots/recipe_modules/flavor/android.py`**: Android 特定的构建逻辑

### Docker 集成

如果使用 Docker 容器化构建：
```dockerfile
# 示例 Dockerfile
FROM debian:bullseye
RUN apt-get update && apt-get install -y curl unzip python3
COPY create.py /tmp/
RUN python3 /tmp/create.py -t /opt/android-ndk
ENV ANDROID_NDK_ROOT=/opt/android-ndk
```

### 环境变量

使用 NDK 时常用的环境变量：
- `ANDROID_NDK_ROOT` 或 `ANDROID_NDK_HOME`: NDK 根目录
- `ANDROID_SDK_ROOT`: Android SDK 路径
- `ANDROID_API_LEVEL`: 目标 API 级别

### 使用示例

在 GN 构建中使用 NDK：
```gn
# args.gn
target_os = "android"
target_cpu = "arm64"
ndk = "/path/to/android-ndk"
ndk_api = 21
```

在命令行中使用：
```bash
gn gen out/android --args='target_os="android" target_cpu="arm64"'
ninja -C out/android
```

Android NDK Linux 版本是 Skia 支持 Android 平台的核心基础设施，使得 Skia 能够为全球数十亿 Android 设备提供高性能 2D 图形渲染能力。
