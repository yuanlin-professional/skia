# create.py

> 源文件: infra/bots/assets/clang_mac_intel/create.py

## 概述

`create.py` 是用于创建 macOS Intel 平台 Clang 编译器工具链资产的脚本。该脚本从 Chromium 项目的 Google Cloud Storage 下载为 macOS Intel（x86_64）架构预编译的 Clang 工具链二进制包。

## 架构位置

```
infra/bots/assets/clang_mac_intel/
├── create.py                     # 本文件：下载 macOS Intel Clang
└── README.md                     # 资产说明
```

该资产为 Skia 在 macOS Intel 设备上使用 Clang 编译器提供支持。

## 主要类与结构体

函数式编程风格，无类定义。

## 公共 API 函数

### create_asset(target_dir)

```python
def create_asset(target_dir):
    """从 Chromium GCS 下载 macOS Intel Clang 工具链"""
    with utils.chdir(target_dir):
        tarball = 'clang.tar.xz'
        subprocess.check_call(['wget', '-O', tarball, GS_URL])
        subprocess.check_call(['tar', 'xf', tarball])
        os.remove(tarball)
```

**功能**：
1. 下载 Chromium 的预编译 Clang tarball（.tar.xz 格式）
2. 解压到目标目录
3. 删除临时 tarball

**参数**：
- `target_dir` (str): 输出目录

### main()

标准的命令行入口点。

## 内部实现细节

### 版本配置

```python
TAR_FILE = "clang-llvmorg-22-init-14273-gea10026b-2.tar.xz"
GS_URL = f'https://commondatastorage.googleapis.com/chromium-browser-clang/Mac/{TAR_FILE}'
```

- **LLVM 版本**：`llvmorg-22-init-14273-gea10026b`（LLVM 22 的开发版本）
- **构建版本**：`-2`（Chromium 的第 2 次构建）
- **存储位置**：Chromium 的 GCS Mac 目录

### 版本获取方法

脚本顶部的注释说明了如何找到正确的版本：

```python
# From a Chromium checkout, run the following script and look for the file that it downloads.
# $ tools/clang/scripts/update.py --output-dir /tmp/mac_clang --host-os mac
# Downloading https://commondatastorage.googleapis.com/chromium-browser-clang/Mac/$TAR_FILE
```

更新流程：
1. 在 Chromium 代码库中运行 `update.py`
2. 观察下载的文件名
3. 更新本脚本中的 `TAR_FILE` 变量

### 压缩格式

使用 `tar.xz`（LZMA2 压缩）而非 `tar.gz`（gzip）：
- **优点**：更高的压缩率（节省 20-30% 存储和带宽）
- **缺点**：解压速度稍慢
- **选择原因**：macOS 和 Chromium 都支持 xz，优先考虑存储效率

### Intel 二进制特性

该包包含 Intel x86_64 二进制文件：
- **架构**：x86_64
- **兼容性**：原生运行在 Intel Mac 上
- **Apple Silicon**：可通过 Rosetta 2 运行（但有性能损失）
- **预构建库**：不包含 libc++ 预构建库（注释中说明）

## 依赖关系

### 系统依赖

1. **wget**：下载工具（macOS 需要安装，如 `brew install wget`）
2. **tar**：解压工具（macOS 内置，支持 xz）
3. **网络连接**：访问 Google Cloud Storage

### Python 依赖

- **`argparse`、`os`、`subprocess`、`sys`**（标准库）
- **`utils`**：Skia 的工具模块（提供 `chdir` 上下文管理器）

### 外部文件依赖

- Chromium GCS 上的预编译 Clang 包（~300 MB）

## 设计模式与设计决策

### 下载预编译包策略

选择下载而非编译的原因：
1. **构建复杂度**：macOS 上编译 LLVM 需要 Xcode
2. **构建时间**：从源代码编译需要 30-60 分钟
3. **一致性**：使用 Chromium 测试过的构建
4. **跨平台创建**：可在 Linux CI 机器上创建 Mac 资产

### 版本跟随策略

紧密跟随 Chromium 的 Clang 版本：
- **优点**：与 Chromium 保持一致，减少兼容性问题
- **更新机制**：手动检查 Chromium 的 `update.py` 并更新
- **测试**：Chromium 团队已对该版本进行广泛测试

### 路径导航模式

```python
FILE_DIR = os.path.dirname(os.path.abspath(__file__))
INFRA_BOTS_DIR = os.path.realpath(os.path.join(FILE_DIR, os.pardir, os.pardir))
sys.path.insert(0, INFRA_BOTS_DIR)
import utils
```

使用相对路径导入 `utils` 模块，确保脚本可在任何位置运行。

## 性能考量

### 下载时间

- **文件大小**：约 300 MB（压缩后）
- **网络速度影响**：
  - 100 Mbps：25-30 秒
  - 10 Mbps：4-5 分钟

### 解压时间

- **xz 解压**：15-30 秒（取决于 CPU 和磁盘速度）
- **解压后大小**：约 700 MB

### 总执行时间

- **最佳情况**：1-2 分钟（快速网络 + SSD）
- **典型情况**：3-5 分钟
- **最差情况**：10 分钟（慢速网络 + HDD）

### 磁盘空间

- 下载的 tarball：~300 MB
- 解压后的工具链：~700 MB
- 峰值占用：~1 GB（下载和解压同时存在）
- tarball 删除后：~700 MB

## 相关文件

### 同目录文件

- **`README.md`**: 版本信息和使用说明

### 相似资产

- **`clang_mac_arm/create.py`**: macOS ARM（Apple Silicon）版本
- **`clang_win/create.py`**: Windows 版本
- **`clang_linux/create.py`**: Linux 版本（使用 Docker 编译）

### 工具模块

- **`infra/bots/utils.py`**: Skia 通用工具模块

### Chromium 参考

- **`tools/clang/scripts/update.py`**: Chromium 的 Clang 更新脚本
- **GCS 存储**：`gs://chromium-browser-clang/Mac/`

### 构建系统

- **`gn/BUILD.gn`**: Skia GN 构建配置
- **`gn/toolchain/mac_toolchain.gni`**: macOS 工具链定义
- **`infra/bots/gen_tasks_logic/gen_tasks_logic.go`**: CI 任务定义
