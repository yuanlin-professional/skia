# create.py

> 源文件: infra/bots/assets/clang_win/create.py

## 概述

`create.py` 是用于创建 Windows 平台 Clang 编译器工具链资产的脚本。与 Linux 版本不同，该脚本直接从 Chromium 项目的预编译二进制存储中下载已构建好的 Clang 工具链，而非从源代码编译，从而大幅缩短资产创建时间。

## 架构位置

该脚本位于 Skia 的 Windows 工具链资产目录：

```
infra/bots/assets/clang_win/
├── create.py                     # 本文件：下载并解压 Clang
└── README.md                     # 版本信息和使用说明
```

该资产为 Skia 在 Windows 平台上使用 Clang 编译器提供支持，Clang 在 Windows 上提供比 MSVC 更一致的跨平台编译体验。

## 主要类与结构体

该脚本使用函数式风格，无类定义。主要组件：

### 全局常量

```python
CLANG_REVISION = 'llvmorg-18-init-17730-gf670112a'
CLANG_SUB_REVISION = 5
PACKAGE_VERSION = '%s-%s' % (CLANG_REVISION, CLANG_SUB_REVISION)
GS_URL = ('https://commondatastorage.googleapis.com/chromium-browser-clang'
          '/Win/clang-%s.tgz' % PACKAGE_VERSION)
```

- **`CLANG_REVISION`**: LLVM 版本标识，对应 LLVM 18 的特定提交
- **`CLANG_SUB_REVISION`**: Chromium 的构建版本号
- **`PACKAGE_VERSION`**: 完整的包版本号
- **`GS_URL`**: Google Cloud Storage 下载 URL

这些版本信息直接从 Chromium 的 `tools/clang/scripts/update.py` 复制而来，确保版本一致性。

## 公共 API 函数

### create_asset(target_dir)

```python
def create_asset(target_dir):
    """从 Chromium GCS 存储下载并解压 Clang 工具链"""
```

**功能**：
1. 切换到目标目录
2. 下载预编译的 Clang tarball
3. 解压到目标目录
4. 清理临时文件

**参数**：
- `target_dir` (str): 资产解压的目标目录

**实现细节**：

```python
with utils.chdir(target_dir):
    tarball = 'clang.tgz'
    subprocess.check_call(['wget', '-O', tarball, GS_URL])
    subprocess.check_call(['tar', 'zxvf', tarball])
    os.remove(tarball)
```

- 使用 `utils.chdir` 上下文管理器临时切换工作目录
- `wget` 下载文件并保存为 `clang.tgz`
- `tar zxvf` 解压 gzip 压缩的 tar 归档
- 删除临时 tarball 节省空间

### main()

```python
def main():
    """主函数：解析参数并创建资产"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--target_dir', '-t', required=True)
    args = parser.parse_args()
    create_asset(args.target_dir)
```

标准的命令行脚本入口。

## 内部实现细节

### 版本同步机制

脚本顶部的注释明确说明版本信息的来源：

```python
# Copied from https://cs.chromium.org/chromium/src/tools/clang/scripts/update.py
CLANG_REVISION = 'llvmorg-18-init-17730-gf670112a'
CLANG_SUB_REVISION = 5
# (End copying)
```

这种设计确保：
- Skia 使用与 Chromium 相同的 Clang 版本
- 减少编译器差异导致的兼容性问题
- 简化版本更新流程（只需复制新版本号）

### 下载源选择

使用 Chromium 的预编译二进制而非自行编译的原因：
1. **构建复杂度**：Windows 上编译 LLVM 需要 Visual Studio 和复杂的依赖
2. **构建时间**：从源代码编译需要 1-2 小时
3. **构建环境**：需要 Windows 构建机器，而下载方式可在 Linux 上执行
4. **一致性**：使用 Chromium 团队测试过的构建

### 工具链结构

下载并解压后的目录结构：

```
<target_dir>/
├── bin/
│   ├── clang.exe                 # C 编译器
│   ├── clang++.exe               # C++ 编译器
│   ├── clang-cl.exe              # MSVC 兼容模式
│   ├── lld-link.exe              # LLVM 链接器（MSVC 兼容）
│   ├── clang-format.exe          # 代码格式化工具
│   └── ...
├── lib/
│   └── clang/
│       └── 18.0.0/
│           ├── include/          # 编译器内置头文件
│           └── lib/              # 运行时库
└── ...
```

## 依赖关系

### 系统依赖

1. **`wget`**：命令行下载工具
   - 在 Windows 上可能需要安装（Git for Windows 自带）
   - 替代方案：`curl -o`

2. **`tar`**：归档解压工具
   - Windows 10 1803+ 内置 tar 命令
   - 旧版本需要 Git Bash 或 MSYS2

3. **网络连接**
   - 需要访问 `commondatastorage.googleapis.com`
   - 下载大小：约 300-500 MB

### Python 模块依赖

- **`argparse`**: 命令行参数解析（标准库）
- **`os`**: 文件系统操作（标准库）
- **`subprocess`**: 外部命令执行（标准库）
- **`sys`**: 系统路径操作（标准库）

### Skia 内部依赖

- **`utils.py`**：Skia 的通用工具模块
  - `utils.chdir`: 目录切换上下文管理器

```python
FILE_DIR = os.path.dirname(os.path.abspath(__file__))
INFRA_BOTS_DIR = os.path.realpath(os.path.join(FILE_DIR, os.pardir, os.pardir))
sys.path.insert(0, INFRA_BOTS_DIR)
import utils
```

## 设计模式与设计决策

### 下载而非编译策略

对比 Linux 版本使用 Docker 编译，Windows 版本选择下载预编译二进制：

| 方面 | 编译方式 | 下载方式 |
|------|---------|---------|
| 执行时间 | 30-60 分钟 | 2-5 分钟 |
| 环境要求 | Visual Studio, CMake | wget, tar |
| 可重复性 | 高（Dockerfile） | 高（固定 URL） |
| 自定义能力 | 可修改构建选项 | 无法修改 |
| 跨平台创建 | 需要 Windows | 可在 Linux 执行 |

选择下载方式的关键原因：
- Windows 构建环境设置复杂
- Chromium 团队已提供高质量的构建
- 资产创建可在 Linux CI 机器上执行

### 版本跟随策略

通过复制 Chromium 的版本号实现版本跟随：
- **优点**：确保与 Chromium 一致，减少兼容性问题
- **更新流程**：
  1. 检查 Chromium 的 `update.py` 文件
  2. 复制新的 `CLANG_REVISION` 和 `CLANG_SUB_REVISION`
  3. 测试新版本
  4. 上传新资产

### 路径处理模式

使用相对路径导航到 `utils.py`：

```python
INFRA_BOTS_DIR = os.path.realpath(os.path.join(FILE_DIR, os.pardir, os.pardir))
sys.path.insert(0, INFRA_BOTS_DIR)
```

这种模式：
- 不依赖环境变量
- 不需要安装 Skia Python 包
- 适用于脚本式工具

## 性能考量

### 下载时间

影响因素：
- 网络速度（主要瓶颈）
- Google Cloud Storage 的地理位置
- 文件大小：约 400 MB

典型时间：
- 100 Mbps 网络：30-60 秒
- 10 Mbps 网络：5-10 分钟

### 解压时间

- `tar` 解压：10-30 秒
- 主要取决于磁盘 I/O 速度
- SSD 显著快于 HDD

### 总执行时间

- 最佳情况：2 分钟（快速网络 + SSD）
- 典型情况：5 分钟
- 最差情况：15 分钟（慢速网络 + HDD）

对比从源代码编译（30-60 分钟），性能提升约 10 倍。

### 磁盘空间

- 下载的 tarball：~400 MB
- 解压后的工具链：~800 MB
- 临时空间需求：~1.2 GB（同时存储 tarball 和解压后的文件）
- tarball 删除后：~800 MB

## 相关文件

### 同目录文件

- **`README.md`**: 资产说明和版本历史

### 相似资产脚本

- **`infra/bots/assets/clang_linux/create.py`**: Linux 版本（使用 Docker 编译）
- **`infra/bots/assets/clang_mac_intel/create.py`**: macOS Intel 版本（下载方式）
- **`infra/bots/assets/clang_mac_arm/create.py`**: macOS ARM 版本（下载方式）
- **`infra/bots/assets/clang_ubuntu_noble/create.py`**: Ubuntu Noble 版本（Docker 编译）

### 工具模块

- **`infra/bots/utils.py`**: 通用工具函数库
  - `chdir`: 目录切换上下文管理器
  - `tmp_dir`: 临时目录创建

### Chromium 源文件

- **`tools/clang/scripts/update.py`**: Chromium 的 Clang 更新脚本（版本信息来源）
- 链接：`https://chromium.googlesource.com/chromium/src/+/main/tools/clang/scripts/update.py`

### 构建集成

- **`gn/BUILD.gn`**: Skia 的 GN 构建配置
- **`gn/toolchain/win_toolchain.gni`**: Windows 工具链定义
- **`infra/bots/gen_tasks_logic/gen_tasks_logic.go`**: CI 任务定义

### GCS 存储

- **下载 URL**：`https://commondatastorage.googleapis.com/chromium-browser-clang/Win/`
- **浏览器访问**：可通过浏览器查看可用版本
