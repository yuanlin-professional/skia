# ccache macOS 资产创建脚本

> 源文件: infra/bots/assets/ccache_mac/create.py

## 概述

这是一个用于从源码编译 ccache 并创建 macOS 可执行文件资产的脚本。ccache（Compiler Cache）是一个编译器缓存工具，通过缓存先前编译的目标文件来加速重复编译过程。该脚本下载 ccache 3.7.7 源码，配置并编译，生成可在 macOS 平台使用的二进制文件和相关资源。

## 架构位置

该脚本位于 `infra/bots/assets/ccache_mac/` 目录，是 Skia 基础设施资产管理系统的一部分。ccache 资产用于加速 Skia 的 C++ 代码编译，特别是在 CI 环境中进行增量构建时，可以显著减少编译时间。该资产与构建系统集成，在编译器调用链中作为缓存层工作。

## 主要类与结构体

脚本采用函数式编程风格，依赖标准库模块和 Skia 基础设施工具：

- **argparse**: 命令行参数解析
- **os**: 文件系统操作和路径管理
- **subprocess**: 外部命令执行
- **sys**: 系统路径操作
- **utils**: Skia 基础设施工具模块，提供 `tmp_dir()` 上下文管理器

### 模块级常量

```python
URL = "https://github.com/ccache/ccache/releases/download/v3.7.7/ccache-3.7.7.tar.gz"
VERSION = "ccache-3.7.7"
```

固定使用 ccache 3.7.7 版本，这是一个稳定的长期支持版本。

## 公共 API 函数

### `create_asset(target_dir)`

核心资产创建函数，执行完整的下载、编译和安装流程。

**参数**:
- `target_dir` (str): 存放编译产物的目标目录，必须是绝对路径

**执行流程**:
1. 规范化目标路径为绝对路径（`configure --prefix` 要求）
2. 在临时目录中下载源码压缩包
3. 解压源码
4. 进入源码目录
5. 配置编译选项（禁用 man 页面，指定安装前缀）
6. 使用 make 编译
7. 使用 make install 安装到目标目录
8. 临时目录自动清理

**关键实现**:
```python
target_dir = os.path.abspath(target_dir)  # 必须是绝对路径

with utils.tmp_dir():
    subprocess.check_call(["curl", "-L", "-o", VERSION + ".tar.gz", URL])
    subprocess.check_call(["tar", "-xzf", VERSION + ".tar.gz"])
    os.chdir(VERSION)

    subprocess.check_call(["./configure", "--disable-man",
                           "--prefix=" + target_dir])
    subprocess.check_call(["make"])
    subprocess.check_call(["make", "install"])
```

### `main()`

脚本入口函数，负责参数解析和函数调用。

**命令行参数**:
- `--target_dir, -t`: 必需参数，指定资产输出目录

## 内部实现细节

### 从源码构建的原因

选择从源码构建而非下载预编译二进制的考量：
- **平台适配**: 确保与目标 macOS 环境完全兼容
- **优化**: 可以针对目标平台优化编译选项
- **定制性**: 可以选择性启用/禁用功能
- **透明性**: 构建过程完全可控和可审计

### 配置选项说明

```bash
./configure --disable-man --prefix=/absolute/path
```

**`--disable-man`**: 禁用 man 页面生成
- 减少构建依赖（不需要 asciidoc 等文档工具）
- 加快编译速度
- 减小资产体积（CI 环境不需要文档）

**`--prefix=/absolute/path`**: 指定安装路径
- 必须是绝对路径（autoconf 要求）
- 直接安装到目标目录，无需后续移动
- 二进制文件安装到 `prefix/bin`，库文件到 `prefix/lib`

### 临时目录管理

使用 `utils.tmp_dir()` 上下文管理器的优势：
- **自动清理**: 构建完成后删除所有临时文件
- **异常安全**: 即使构建失败也会清理
- **隔离性**: 不污染工作目录
- **并发安全**: 每次调用使用独立的临时目录

### 下载和解压流程

```python
subprocess.check_call(["curl", "-L", "-o", VERSION + ".tar.gz", URL])
subprocess.check_call(["tar", "-xzf", VERSION + ".tar.gz"])
```

**curl 参数**:
- `-L`: 跟随 HTTP 重定向（GitHub releases 可能重定向）
- `-o`: 指定输出文件名

**tar 参数**:
- `-x`: 解压
- `-z`: 使用 gzip 解压缩
- `-f`: 指定文件

### 编译流程

典型的 autotools 构建流程：
```
./configure → make → make install
```

1. **configure**: 检测系统环境，生成 Makefile
2. **make**: 编译源码生成二进制文件
3. **make install**: 安装到指定目录

ccache 使用标准的 autotools 构建系统，确保跨平台兼容性。

## 依赖关系

### 构建依赖

- **curl**: 下载源码
- **tar**: 解压源码包
- **C/C++ 编译器**: GCC 或 Clang（macOS 通常使用 Xcode Command Line Tools）
- **autotools**: autoconf, automake（ccache 源码包含预生成的 configure 脚本）
- **make**: GNU Make 或兼容实现

### 运行时依赖

编译生成的 ccache 可能动态链接到：
- **libc/libSystem**: macOS 系统库
- **zlib**: 压缩库（用于缓存压缩）
- **C++ 标准库**: libc++ 或 libstdc++

### Python 依赖

- **Python 标准库**: argparse, os, subprocess, sys
- **Skia utils**: `infra/bots/utils.py`

## 设计模式与设计决策

### 版本固定策略

使用 ccache 3.7.7 而非最新版本（4.x）的原因：
- **稳定性**: 3.7.x 是成熟的稳定版本
- **兼容性**: 避免 4.x 的破坏性变更
- **测试成本**: 版本升级需要充分测试

### 最小化安装

通过 `--disable-man` 减少不必要的文件：
- 减小资产体积（节省 ~1 MB）
- 减少构建时间（节省 ~10-20%）
- 简化依赖（无需文档生成工具）

### 原地安装策略

直接使用 `--prefix=target_dir` 安装到最终位置，而非先安装到临时位置再复制。这种设计：
- **高效**: 避免额外的文件复制
- **简单**: 无需处理复杂的目录结构
- **可靠**: 减少出错可能

### 绝对路径要求

```python
target_dir = os.path.abspath(target_dir)
```

强制转换为绝对路径是因为：
- autoconf 的 `--prefix` 必须是绝对路径
- 避免相对路径在 `chdir` 后失效
- 提升脚本的健壮性

## 性能考量

### 编译时间

ccache 是一个 C++ 项目，编译时间取决于：
- **CPU 性能**: 现代多核 CPU 约 30-60 秒
- **磁盘 I/O**: SSD 比 HDD 快 2-3 倍
- **并行度**: 脚本使用单线程 make，未启用 `-j`

### 优化机会

可以通过并行编译加速：
```python
subprocess.check_call(["make", "-j"])  # 自动检测 CPU 核心数
```

但 ccache 项目规模较小，并行收益有限（约节省 30-40%）。

### 下载时间

源码压缩包约 400-500 KB，下载时间通常小于 1 秒。

### 整体性能

典型执行时间：
- 下载: 1-5 秒
- 解压: 1-2 秒
- configure: 5-10 秒
- 编译: 30-60 秒
- 安装: 1-2 秒
- 总计: ~40-80 秒

## 相关文件

### 同类资产

- **`infra/bots/assets/ccache_linux/create.py`**: Linux 版本
- **`infra/bots/assets/ccache_win/create.py`**: Windows 版本（如果存在）

### 资产管理

- **`infra/bots/assets/ccache_mac/VERSION`**: 资产版本标识
- **`infra/bots/assets/ccache_mac/download.py`**: 下载脚本
- **`infra/bots/assets/ccache_mac/upload.py`**: 上传脚本

### 构建集成

- **`infra/bots/recipe_modules/flavor/`**: 构建配方模块，配置 ccache 使用
- **`infra/bots/recipes/`**: CI 配方，在编译任务中启用 ccache

### ccache 配置

- **`.ccache/ccache.conf`**: ccache 配置文件（如果存在）
- **环境变量**: `CCACHE_DIR`, `CCACHE_MAXSIZE` 等

### 上游项目

- GitHub: https://github.com/ccache/ccache
- 文档: https://ccache.dev/
- 版本 3.7.7 发布说明: https://github.com/ccache/ccache/releases/tag/v3.7.7

ccache 通过缓存编译结果可以将重复编译时间减少 50-90%，是提升 CI 效率的重要工具。
