# Windows 工具链资产创建与上传脚本

> 源文件: infra/bots/assets/win_toolchain/create_and_upload.py

## 概述

这是一个简化的资产创建与上传流程编排脚本，用于自动化 Windows 工具链资产的打包和发布。该脚本作为用户和实际创建脚本（`create.py`）之间的桥梁，通过 Skia 的 `sk` 命令行工具执行资产上传操作。它使用环境变量传递参数，避免了直接调用带来的参数传递复杂性。

## 架构位置

该脚本位于 `infra/bots/assets/win_toolchain/` 目录，是 Skia 基础设施资产管理系统的一部分。Windows 工具链资产包含：
- Visual Studio 编译器和工具链
- Windows SDK
- 必要的系统库和头文件

这些资产用于在 CI 环境中进行 Windows 平台的跨平台编译。脚本与以下组件协同工作：
- **create.py**: 实际的资产创建逻辑
- **sk 工具**: Skia 的资产管理命令行工具
- **CIPD 系统**: Chrome Infrastructure Package Deployment，资产存储后端

## 主要类与结构体

脚本采用简单的函数式风格，不包含类定义。主要依赖标准库模块：

- **argparse**: 命令行参数解析
- **os**: 操作系统接口，用于环境变量和路径操作
- **subprocess**: 子进程管理，用于调用 sk 工具
- **sys**: 系统特定参数和函数
- **tempfile**: 临时文件和目录管理（导入但未使用）
- **create**: 同目录下的 create.py 模块

### 关键常量

```python
FILE_DIR = os.path.dirname(os.path.abspath(__file__))  # 脚本所在目录
ASSET = os.path.basename(FILE_DIR)  # 资产名称（win_toolchain）
```

## 公共 API 函数

### `main()`

主函数，负责整个创建和上传流程的编排。

**功能流程**:
1. 解析命令行参数，获取源目录路径
2. 将源目录路径通过环境变量传递给 create.py
3. 定位 sk 工具的可执行文件路径
4. 验证 sk 工具存在性
5. 调用 sk 工具执行资产上传

**参数**:
- `--src_dir, -s`: 必需参数，指定 Windows 工具链的源目录

**返回**: 无返回值，失败时抛出异常

## 内部实现细节

### 环境变量传递机制

脚本使用环境变量而非命令行参数传递源目录路径：

```python
os.environ[create.ENV_VAR] = args.src_dir
```

这种设计的原因：
- `sk` 工具会调用 `create.py`，但不支持传递自定义参数
- 环境变量是跨进程通信的简单方式
- `create.py` 可以通过相同的环境变量名读取值

`create.ENV_VAR` 的值是 `'WIN_TOOLCHAIN_SRC_DIR'`，定义在 `create.py` 中。

### sk 工具定位逻辑

脚本使用相对路径定位 sk 工具：

```python
sk = os.path.realpath(os.path.join(
    FILE_DIR, os.pardir, os.pardir, os.pardir, os.pardir, 'bin', 'sk'))
```

路径解析：
```
infra/bots/assets/win_toolchain/  (当前目录)
    ↓ os.pardir (infra/bots/assets/)
    ↓ os.pardir (infra/bots/)
    ↓ os.pardir (infra/)
    ↓ os.pardir (项目根目录)
    → bin/sk
```

**平台适配**: Windows 平台需要添加 `.exe` 扩展名：
```python
if os.name == 'nt':
    sk += '.exe'
```

### 工具存在性验证

脚本检查 sk 工具是否存在，如果不存在则抛出友好的错误提示：

```python
if not os.path.isfile(sk):
    raise Exception('`sk` not found at %s; maybe you need to run bin/fetch-sk?')
```

错误消息包含解决方案提示，引导用户运行 `bin/fetch-sk` 下载工具。

### 资产上传命令

最终执行的命令：

```bash
sk asset upload win_toolchain
```

该命令在 `FILE_DIR`（即 `infra/bots/assets/win_toolchain/`）目录下执行。`sk` 工具会：
1. 读取当前目录的资产配置
2. 调用 `create.py` 创建资产
3. 将资产打包上传到 CIPD

## 依赖关系

### 外部依赖

- **sk 工具**: Skia 的资产管理 CLI，位于 `bin/sk`
- **CIPD 后端**: 资产上传的目标服务
- **create.py**: 实际的资产创建逻辑

### Python 依赖

- **标准库**: argparse, os, subprocess, sys, tempfile
- **本地模块**: create.py（通过 import 引用其 ENV_VAR 常量）

### 系统依赖

- **Python 解释器**: Python 2 或 3 兼容
- **网络连接**: 用于上传资产到 CIPD

## 设计模式与设计决策

### 职责分离原则

该脚本遵循单一职责原则，只负责流程编排：
- **参数获取**: 从命令行读取用户输入
- **参数传递**: 通过环境变量传递给 create.py
- **工具调用**: 执行 sk 工具完成上传

实际的资产创建逻辑完全委托给 `create.py`。

### 间接调用模式

脚本不直接调用 `create.py`，而是通过 `sk` 工具间接调用。这种设计的好处：
- **标准化**: 所有资产使用统一的上传流程
- **功能完整**: sk 工具提供版本管理、校验等额外功能
- **解耦**: 创建逻辑与上传逻辑分离

### 环境变量通信

使用环境变量而非命令行参数传递自定义参数的权衡：

**优点**:
- 简单：无需修改 sk 工具
- 灵活：可以传递任意数据
- 标准：子进程自动继承环境变量

**缺点**:
- 隐式：参数传递不如命令行直观
- 污染：修改全局环境变量状态
- 调试：错误时难以追踪参数来源

### 用户友好错误处理

脚本提供清晰的错误消息和解决方案：
```python
raise Exception('`sk` not found at %s; maybe you need to run bin/fetch-sk?')
```

这种实践提升了开发者体验，特别是对于新手。

## 性能考量

### 脚本性能

该脚本本身非常轻量：
- 无重计算逻辑
- 仅进行路径操作和一次子进程调用
- 执行时间小于 100ms

### 整体流程性能

性能瓶颈主要在：
1. **资产创建**: 由 create.py 执行，涉及大量文件复制
2. **资产打包**: sk 工具压缩资产包
3. **网络上传**: 传输数 GB 的工具链文件到 CIPD

Windows 工具链资产通常有几个 GB，上传时间取决于网络带宽。

### 优化空间

脚本本身已经足够简洁，优化空间有限。潜在改进：
- **并行化**: 目前是串行流程，但资产上传通常需要按顺序进行
- **缓存**: 可以缓存未变化的资产，避免重复上传（sk 工具可能已实现）
- **增量更新**: 只上传变化的部分（依赖 CIPD 功能）

## 相关文件

- **`infra/bots/assets/win_toolchain/create.py`**: 资产创建的实际实现，包含文件过滤和复制逻辑
- **`infra/bots/assets/win_toolchain/__init__.py`**: Python 包标识文件
- **`infra/bots/assets/win_toolchain/download.py`**: 从 CIPD 下载资产的脚本
- **`infra/bots/assets/win_toolchain/VERSION`**: 资产版本标识
- **`bin/sk`**: Skia 资产管理工具的可执行文件
- **`bin/fetch-sk`**: 下载或更新 sk 工具的脚本
- **`depot_tools/win_toolchain/package_from_installed.py`**: 从本地安装的 Visual Studio 打包工具链

### 使用流程

完整的 Windows 工具链资产更新流程：
1. 在 Windows 机器上安装完整的 Visual Studio
2. 运行 `depot_tools/win_toolchain/package_from_installed.py` 打包工具链
3. 解压生成的 zip 文件
4. 运行本脚本 `create_and_upload.py --src_dir <解压目录>`
5. 资产被上传到 CIPD，供 CI 使用

该脚本简化了步骤 4，自动化了创建和上传的流程。
