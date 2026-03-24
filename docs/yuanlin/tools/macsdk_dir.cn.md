# macsdk_dir

> 源文件
> - tools/macsdk_dir.py

## 概述

macsdk_dir 是一个 Python 3 脚本,用于确定和输出 Bazel 构建系统在当前工作空间中使用的 MacSDK 目录的完整路径。该脚本通过计算工作空间哈希值并导航 Bazel 的输出目录结构,定位到包含 XCode MacSDK 符号链接的目录。

这个工具解决了在 Bazel 构建环境中定位 MacSDK 路径的问题,MacSDK 路径由 Bazel 工具链下载器创建,包含指向 XCode MacSDK 内容的符号链接。

## 架构位置

macsdk_dir 位于工具目录,作为构建系统辅助工具的一部分:

```
skia/
├── tools/
│   ├── macsdk_dir.py          # 本脚本
│   └── 其他构建工具
├── toolchain/
│   └── download_mac_toolchain.bzl  # MacSDK 下载器
├── bazel-*                    # Bazel 符号链接
└── BUILD.bazel                # Bazel 构建文件
```

在构建流程中的位置:
1. Bazel 下载 Mac 工具链
2. 创建 MacSDK 符号链接目录
3. **macsdk_dir.py 定位该目录**
4. 其他脚本使用该路径进行编译配置

## 主要类与结构体

该脚本采用函数式设计,没有类定义,由多个独立函数组成。

### 核心函数

#### GetWorkspaceDir() -> str
返回包含此脚本的工作空间目录。

#### GetBazelWorkspaceHash() -> str
返回当前工作空间的 Bazel 哈希值(工作空间路径的 MD5)。

#### GetBazelRepositoryCacheDir() -> str
返回 Bazel 仓库缓存目录。

#### GetBazelOutputDir() -> str
返回 Bazel 输出目录。

#### GetBazelWorkspaceCacheDir() -> str
返回当前工作空间的 Bazel 输出缓存目录。

#### GetMacSDKSymlinkDir() -> str
返回 MacSDK 符号链接目录的路径。

## 公共 API 函数

### 命令行接口

```bash
python3 tools/macsdk_dir.py
```

**输出**: 打印 MacSDK 符号链接目录的完整路径到标准输出

**使用示例**:
```bash
$ python3 tools/macsdk_dir.py
/private/var/tmp/_bazel_user/a1b2c3d4e5f6/.../external/clang_mac/symlinks/xcode/MacSDK

# 在脚本中使用
MACSDK=$(python3 tools/macsdk_dir.py)
echo "MacSDK is at: $MACSDK"
```

### 函数级 API

脚本也可以作为模块导入:

```python
from tools.macsdk_dir import GetMacSDKSymlinkDir

sdk_path = GetMacSDKSymlinkDir()
print(f"Using SDK at: {sdk_path}")
```

## 内部实现细节

### 工作空间定位

```python
def GetWorkspaceDir() -> str:
    this_script_path = Path(os.path.realpath(__file__))
    return str(this_script_path.parent.parent)
```

**实现逻辑**:
1. 获取脚本的真实路径(解析符号链接)
2. 获取父目录的父目录(tools/ 的父目录)
3. 返回工作空间根目录路径

### 工作空间哈希计算

```python
def GetBazelWorkspaceHash() -> str:
    ws = GetWorkspaceDir().encode("utf-8")
    return hashlib.md5(ws).hexdigest()
```

**Bazel 哈希机制**:
- Bazel 使用工作空间完整路径的 MD5 哈希作为标识
- 这允许多个工作空间共存而不冲突
- 参考: https://bazel.build/remote/output-directories#layout-diagram

**哈希示例**:
```
工作空间路径: /Users/user/skia
UTF-8 编码: b'/Users/user/skia'
MD5 哈希: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

### 仓库缓存目录查询

```python
def GetBazelRepositoryCacheDir() -> str:
    prev_cwd = os.getcwd()
    os.chdir(GetWorkspaceDir())
    cmd = ["bazelisk", "info", "repository_cache"]
    output = subprocess.check_output(cmd)
    decoded_output = codecs.decode(output, "utf-8")
    return decoded_output.strip()
```

**实现要点**:
1. 保存当前目录
2. 切换到工作空间根目录(Bazel 命令需要在工作空间中执行)
3. 运行 `bazelisk info repository_cache` 查询缓存位置
4. 解码输出并去除空白字符
5. 返回缓存目录路径

**为什么使用 bazelisk**: bazelisk 是 Bazel 的版本管理器,确保使用正确的 Bazel 版本

### 输出目录推导

```python
def GetBazelOutputDir() -> str:
    repo_cache_dir = Path(GetBazelRepositoryCacheDir())
    output_dir = repo_cache_dir.parent.parent.parent
    return str(output_dir)
```

**目录结构**:
```
<output_base>/
├── install/
├── workspace_layout/
├── external/
│   └── <hash>/
│       └── repository_cache/  ← 从这里开始
└── execroot/
```

向上三层: `repository_cache/../../../` = `<output_base>`

### 工作空间缓存目录

```python
def GetBazelWorkspaceCacheDir() -> str:
    return os.path.join(GetBazelOutputDir(), GetBazelWorkspaceHash())
```

**路径构成**:
```
<output_base>/<workspace_hash>/
```

**多工作空间支持**: 不同的工作空间有不同的哈希,输出互不干扰

### MacSDK 符号链接定位

```python
def GetMacSDKSymlinkDir() -> str:
    return os.path.join(
        GetBazelWorkspaceCacheDir(),
        "external",
        "clang_mac",
        "symlinks",
        "xcode",
        "MacSDK"
    )
```

**完整路径**:
```
<output_base>/<workspace_hash>/external/clang_mac/symlinks/xcode/MacSDK
```

**路径来源**: 这个结构由 `//toolchain/download_mac_toolchain.bzl` 创建

## 依赖关系

### Python 标准库
- `codecs`: 字符编码转换
- `hashlib`: MD5 哈希计算
- `os`: 文件系统操作
- `subprocess`: 执行外部命令
- `sys`: 系统交互
- `pathlib.Path`: 路径对象操作

### 外部工具依赖
- **bazelisk**: Bazel 版本管理器,用于查询 Bazel 信息
- **Bazel**: 构建系统(通过 bazelisk 调用)

### 构建系统依赖
- `//toolchain/download_mac_toolchain.bzl`: 创建 MacSDK 符号链接

### 数据流

```
Bazel 工具链下载器
    ↓
创建 MacSDK 符号链接
    ↓
macsdk_dir.py 定位路径
    ↓
构建脚本使用 SDK 路径
    ↓
编译器查找头文件和库
```

## 设计模式与设计决策

### 函数式设计

脚本采用纯函数式设计:
- 每个函数职责单一
- 函数之间通过返回值传递数据
- 易于测试和理解

### 类型注解

使用 Python 3 类型注解:
```python
def GetWorkspaceDir() -> str:
```

**优点**:
- 提高代码可读性
- 支持静态类型检查
- 更好的 IDE 支持

### 分层抽象

函数调用层次清晰:
```
GetMacSDKSymlinkDir()
    ↓
GetBazelWorkspaceCacheDir()
    ↓
GetBazelOutputDir() + GetBazelWorkspaceHash()
    ↓
GetBazelRepositoryCacheDir() + GetWorkspaceDir()
```

每一层解决一个子问题,最终组合成完整解决方案。

### 文档驱动设计

脚本开头的 docstring 清楚说明了:
- 脚本的目的
- MacSDK 目录的创建机制
- 目录内容(XCode MacSDK 符号链接)

### 避免硬编码

使用 Bazel 命令查询路径而非硬编码:
- **优点**: 适应 Bazel 配置变化
- **缺点**: 需要执行外部命令,略慢
- **权衡**: 正确性比性能更重要

## 性能考量

### subprocess 调用开销

调用 `bazelisk info` 是主要性能瓶颈:
- 启动 Java 进程(Bazel 运行在 JVM 上)
- 加载 Bazel 配置
- 查询信息

**典型耗时**: 500ms - 2s(首次调用),后续调用有缓存

### 优化策略

对于频繁调用场景,可以缓存结果:
```python
_cached_sdk_path = None

def GetMacSDKSymlinkDir() -> str:
    global _cached_sdk_path
    if _cached_sdk_path is None:
        _cached_sdk_path = os.path.join(...)
    return _cached_sdk_path
```

### 实际使用场景

脚本通常在构建配置阶段调用一次:
- 不在构建热路径上
- 性能影响可接受
- 正确性比速度重要

## 相关文件

### 工具链文件
- `toolchain/download_mac_toolchain.bzl`: 下载和配置 Mac 工具链

### 构建配置
- `BUILD.bazel`: Bazel 构建规则
- `.bazelrc`: Bazel 配置选项

### Bazel 输出目录结构

```
$HOME/.cache/bazel/_bazel_$USER/<hash>/
├── external/
│   └── clang_mac/
│       └── symlinks/
│           └── xcode/
│               └── MacSDK/          ← 目标目录
│                   ├── System/
│                   ├── usr/
│                   └── ...
```

### 使用此脚本的工具

可能的使用者:
- 编译器配置脚本
- IDE 集成脚本
- 测试环境设置脚本

### Bazel 文档参考

- [Bazel 输出目录布局](https://bazel.build/remote/output-directories)
- [Bazel 工作空间规则](https://bazel.build/concepts/build-ref)

### 使用示例

**在 shell 脚本中使用**:
```bash
#!/bin/bash
MACSDK_PATH=$(python3 tools/macsdk_dir.py)
export SDKROOT="$MACSDK_PATH"
clang++ -isysroot "$SDKROOT" main.cpp
```

**在 Python 构建脚本中使用**:
```python
import subprocess
from tools.macsdk_dir import GetMacSDKSymlinkDir

sdk_path = GetMacSDKSymlinkDir()
compiler_args = ['-isysroot', sdk_path]
subprocess.run(['clang++'] + compiler_args + ['main.cpp'])
```

macsdk_dir 脚本虽然专注于一个特定任务,但在 Bazel 构建的 macOS 环境中发挥着重要作用。它的设计展示了如何通过组合简单函数来解决复杂的路径定位问题,同时保持代码的清晰和可维护性。
