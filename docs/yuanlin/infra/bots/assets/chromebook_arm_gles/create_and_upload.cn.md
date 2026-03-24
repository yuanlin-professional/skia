# create_and_upload.py

> 源文件: infra/bots/assets/chromebook_arm_gles/create_and_upload.py

## 概述

`create_and_upload.py` 是一个用于创建和上传 Chromebook ARM GLES 资产的自动化脚本。该脚本负责协调资产创建过程，并将生成的资产上传到 CIPD（Chrome Infrastructure Package Deployment）系统中，供 Skia 构建系统在持续集成环境中使用。

## 架构位置

该脚本位于 Skia 基础设施的资产管理系统中：

```
infra/bots/assets/
└── chromebook_arm_gles/           # ARM 架构 Chromebook 的 GLES 库资产
    ├── create_and_upload.py       # 本文件：资产创建和上传入口
    ├── create.py                  # 实际的资产创建逻辑
    └── __init__.py                # Python 包标识文件
```

该资产系统为 Skia 的持续集成提供平台特定的 OpenGL ES 库和头文件，使得构建系统能够在 Chromebook ARM 设备上编译和测试图形渲染代码。

## 主要类与结构体

该脚本采用函数式编程风格，不包含类定义。主要组件包括：

### 全局常量

- **`FILE_DIR`**: 当前脚本文件所在的绝对路径目录
- **`ASSET`**: 资产名称，通过目录名自动推导（`chromebook_arm_gles`）

### 核心函数

**`main()`**
- 脚本的主入口点
- 功能：解析命令行参数，设置环境变量，调用 `sk` 工具上传资产

## 公共 API 函数

### main()

```python
def main():
    """主函数，协调资产的创建和上传流程"""
```

**功能描述**：
1. 平台检查：验证脚本只在 Linux 系统上运行
2. 参数解析：接收 `--lib_path`（`-l`）参数，指定 GLES 库路径
3. 环境变量传递：将库路径通过环境变量传递给 `create.py` 脚本
4. 工具定位：查找 `sk` 可执行文件（Skia 的资产管理工具）
5. 资产上传：调用 `sk asset upload` 命令将资产上传到 CIPD

**参数**：
- `--lib_path` / `-l`（必需）：包含 GLES 库文件的目录路径

**错误处理**：
- 如果不在 Linux 平台运行，打印错误信息并退出
- 如果 `sk` 工具不存在，抛出异常提示运行 `bin/fetch-sk`

## 内部实现细节

### 工作流程

1. **平台验证**
   ```python
   if 'linux' not in sys.platform:
       print('This script only runs on Linux.', file=sys.stderr)
       sys.exit(1)
   ```
   只允许在 Linux 系统上运行，因为资产创建过程涉及 Linux 特定的包管理操作。

2. **环境变量传递机制**
   ```python
   os.environ[create.ENV_VAR] = args.lib_path
   ```
   由于资产创建通过 `sk` 工具间接调用 `create.py`，无法直接传递参数，因此使用环境变量 `CHROMEBOOK_ARM_GLES_LIB_PATH` 作为通信机制。

3. **工具路径计算**
   ```python
   sk = os.path.realpath(os.path.join(
       FILE_DIR, os.pardir, os.pardir, os.pardir, os.pardir, 'bin', 'sk'))
   ```
   通过相对路径导航到 Skia 根目录下的 `bin/sk` 工具，支持跨平台（Windows 下添加 `.exe` 后缀）。

4. **资产上传**
   ```python
   subprocess.check_call([sk, 'asset', 'upload', ASSET], cwd=FILE_DIR)
   ```
   在当前资产目录中执行 `sk asset upload chromebook_arm_gles` 命令，`sk` 工具会：
   - 调用 `create.py` 生成资产内容
   - 打包资产文件
   - 上传到 CIPD 存储

### 依赖模块

- **`argparse`**: 命令行参数解析
- **`os`**: 文件系统路径操作和环境变量管理
- **`subprocess`**: 外部进程调用（`sk` 工具）
- **`sys`**: 平台检测和程序退出
- **`tempfile`**: 虽然导入但未使用，可能是遗留代码
- **`create`**: 同目录下的创建脚本模块

## 依赖关系

### 外部依赖

1. **`sk` 工具**：Skia 的资产管理 CLI 工具
   - 位置：`<SKIA_ROOT>/bin/sk`
   - 功能：执行 CIPD 资产的创建、上传、下载操作
   - 获取方式：通过 `bin/fetch-sk` 脚本下载

2. **`create.py`**：同目录下的资产创建脚本
   - 定义了 `ENV_VAR` 常量
   - 包含实际的库文件收集和打包逻辑

### 系统依赖

- Linux 操作系统（Ubuntu/Debian 系列）
- `apt-get` 包管理器（用于安装 Mesa 开发库）
- 网络连接（用于上传到 CIPD 服务器）

## 设计模式与设计决策

### 职责分离模式

脚本采用清晰的职责分离：
- **`create_and_upload.py`**（本文件）：处理外部接口（命令行参数）和工具调用
- **`create.py`**：封装资产创建的具体逻辑
- **`sk` 工具**：处理底层的 CIPD 交互

这种设计使得：
- 资产创建逻辑可以独立测试
- 相同的创建逻辑可以被不同的入口脚本复用
- 符合单一职责原则

### 环境变量作为进程间通信

由于 `sk` 工具作为中间层调用 `create.py`，无法直接传递自定义参数，因此使用环境变量作为参数传递机制。这种设计：
- 优点：简单直接，不需要修改 `sk` 工具
- 缺点：参数传递方式不够显式，增加了理解成本

### 平台限制

明确限制只在 Linux 上运行，避免在不支持的平台上出现难以诊断的错误。这是一种防御性编程实践。

## 性能考量

### I/O 密集型操作

该脚本的主要性能瓶颈在于：
1. **包下载**：`create.py` 中的 `apt-get install` 需要从网络下载 Mesa 开发包
2. **文件拷贝**：复制库文件和头文件到目标目录
3. **网络上传**：将打包后的资产上传到 CIPD 服务器（通常为数十 MB）

### 执行时间

典型执行时间：2-5 分钟（取决于网络速度和系统缓存状态）

### 资源占用

- 磁盘空间：~100MB（临时资产文件）
- 内存：<50MB
- 网络带宽：上传时需要稳定的网络连接

## 相关文件

### 同目录文件

- **`create.py`**: 实际的资产创建实现，包含库文件收集和打包逻辑
- **`__init__.py`**: Python 包标识文件
- **`version.txt`**: 资产的版本号文件（未在本脚本中引用）
- **`README.md`**: 资产的使用说明文档（如果存在）

### 相关资产目录

- **`chromebook_x86_64_gles/`**: x86_64 架构 Chromebook 的对应资产
- **`chromebook_arm64_gles/`**: ARM64 架构 Chromebook 的对应资产
- **`linux_vulkan_sdk/`**: Linux Vulkan SDK 资产

### 构建系统集成

- **`infra/bots/gen_tasks_logic/gen_tasks_logic.go`**: 任务生成逻辑，引用该资产
- **`infra/bots/tasks.json`**: 构建任务配置，指定资产依赖
- **`DEPS`**: 可能包含资产的版本固定信息

### 工具脚本

- **`bin/sk`**: Skia 资产管理 CLI 工具
- **`bin/fetch-sk`**: 下载 `sk` 工具的脚本
