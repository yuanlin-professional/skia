# Windows 工具链资产创建脚本

> 源文件: infra/bots/assets/win_toolchain/create.py

## 概述

这是用于创建 Windows 编译工具链资产的核心脚本。它从已打包的 Visual Studio 工具链中过滤和复制必要的文件，移除不必要的组件以减小资产体积。该脚本专门设计用于处理由 `depot_tools/win_toolchain/package_from_installed.py` 生成的工具链包，通过智能过滤机制显著减小最终资产的大小和路径长度。

## 架构位置

该脚本是 Skia 基础设施资产管理系统的核心组件，位于 `infra/bots/assets/win_toolchain/`。它处理的工具链资产包含：

- **Visual C++ 编译器**: cl.exe 及相关工具
- **链接器和库管理器**: link.exe, lib.exe
- **Windows SDK**: 头文件、库文件和工具
- **运行时库**: C/C++ 运行时库和 DLL
- **构建工具**: MSBuild 相关组件

这些资产用于 Skia CI 系统在 Linux 主机上进行 Windows 交叉编译。脚本与 `create_and_upload.py` 配合工作，后者负责调用本脚本并上传生成的资产。

## 主要类与结构体

脚本使用函数式编程风格，不包含类定义。主要使用 Python 标准库模块：

- **argparse**: 命令行参数解析
- **os**: 文件系统和路径操作
- **shlex**: Shell 命令行字符串处理（导入但未使用）
- **shutil**: 高级文件操作，特别是 `copytree` 和 `rmtree`
- **subprocess**: 子进程管理（导入但未使用）
- **sys**: 系统参数，用于错误处理和平台检测

### 模块级常量

#### `ENV_VAR`
```python
ENV_VAR = 'WIN_TOOLCHAIN_SRC_DIR'
```
环境变量名，用于从 `create_and_upload.py` 接收源目录路径。

#### `IGNORE_LIST`
```python
IGNORE_LIST = [
  'WindowsMobile',
  'App Certification Kit',
  'Debuggers',
  'Extension SDKs',
  'DesignTime',
  'AccChecker',
]
```
需要过滤的目录名列表，这些目录包含不必要的组件。

## 公共 API 函数

### `getenv(key)`

安全的环境变量读取函数，带有错误处理和用户提示。

**参数**:
- `key` (str): 环境变量名

**返回**:
- 环境变量的值（字符串）

**异常**:
- 如果环境变量不存在，打印错误消息并退出（exit code 1）

**实现**:
```python
def getenv(key):
  val = os.environ.get(key)
  if not val:
    print(('Environment variable %s not set; you should run this via '
           'create_and_upload.py.' % key), file=sys.stderr)
    sys.exit(1)
  return val
```

该函数通过友好的错误消息引导用户使用正确的调用方式。

### `filter_toolchain_files(dirname, files)`

`shutil.copytree` 的 ignore 回调函数，用于过滤不需要的文件和目录。

**参数**:
- `dirname` (str): 当前正在处理的目录路径
- `files` (list): 当前目录下的文件和子目录名列表

**返回**:
- 需要忽略的文件/目录名列表，空列表表示全部保留

**功能**:
- 检查目录路径是否包含 `IGNORE_LIST` 中的任何名称
- 如果匹配，返回所有文件名（忽略整个目录）
- 如果不匹配，返回空列表（保留所有内容）
- 打印被忽略的目录路径用于日志记录

**实现细节**:
```python
def filter_toolchain_files(dirname, files):
  split = dirname.split(os.path.sep)  # 分割路径为组件
  for ign in IGNORE_LIST:
    if ign in split:  # 检查路径中是否包含忽略项
       print('Ignoring dir %s' % dirname)
       return files  # 返回所有文件表示全部忽略
  return []  # 返回空列表表示全部保留
```

### `main()`

脚本入口函数，协调整个资产创建流程。

**功能流程**:
1. 平台检测：确保运行在 Windows 平台
2. 参数解析：获取目标目录路径
3. 源目录读取：从环境变量获取源路径
4. 路径规范化：转换为绝对路径
5. 清理旧文件：删除已存在的目标目录
6. 复制过滤：使用 `copytree` 和自定义过滤函数复制文件

**平台限制**:
```python
if sys.platform != 'win32':
  print('This script only runs on Windows.', file=sys.stderr)
  sys.exit(1)
```

脚本强制要求在 Windows 平台运行，因为工具链打包和某些文件操作具有平台特定性。

## 内部实现细节

### 环境变量通信模式

脚本通过环境变量接收源目录参数，而非命令行参数。这种设计的背景：

1. `create_and_upload.py` 通过 `sk` 工具间接调用本脚本
2. `sk` 工具不支持传递自定义参数给创建脚本
3. 环境变量是简单有效的跨进程通信方式

工作流程：
```
create_and_upload.py 设置环境变量 → sk asset upload → create.py 读取环境变量
```

### 目录过滤机制

`filter_toolchain_files` 函数基于路径而非文件名进行过滤。这种设计能够：

- **递归过滤**: 一旦某个父目录匹配，其所有子目录和文件都被忽略
- **性能优化**: 避免遍历和复制不需要的大型目录树
- **灵活性**: 通过修改 `IGNORE_LIST` 轻松调整过滤规则

**示例**:
```
路径: C:\toolchain\Windows Kits\10\Debuggers\x64\...
      ↓
split: ['C:', 'toolchain', 'Windows Kits', '10', 'Debuggers', 'x64', ...]
      ↓
检查: 'Debuggers' in IGNORE_LIST → True
      ↓
结果: 整个 Debuggers 目录被忽略
```

### 忽略列表的设计考量

`IGNORE_LIST` 中的每个项目都有特定的理由：

- **WindowsMobile**: Windows Mobile 开发工具，Skia 不支持该平台
- **App Certification Kit**: 应用认证工具，CI 环境不需要
- **Debuggers**: WinDbg 等调试器，体积大且 CI 不需要
- **Extension SDKs**: 扩展 SDK，包含大量第三方库
- **DesignTime**: 设计时组件，编译时不需要
- **AccChecker**: 辅助功能检查工具，与构建无关

这些目录的共同特点：
- 占用大量磁盘空间
- 包含极长的文件路径（Windows 路径长度限制问题）
- 编译 Skia 不需要

### 路径长度问题

Windows 有 260 字符的路径长度限制（MAX_PATH）。Visual Studio 工具链包含一些路径极长的文件，例如：

```
C:\...\Extension SDKs\Microsoft.UniversalCRT.Debug\...\很长的路径\...
```

过滤这些目录不仅减小资产体积，还避免了路径长度相关的问题。

### 删除重建策略

脚本使用 `shutil.rmtree` 强制删除已存在的目标目录：

```python
shutil.rmtree(target_dir)
shutil.copytree(src_dir, target_dir, ignore=filter_toolchain_files)
```

这种策略确保：
- **幂等性**: 多次运行产生相同结果
- **清洁性**: 没有旧文件残留
- **简单性**: 无需复杂的差异比较和增量更新

**风险**: 如果 `copytree` 失败，目标目录已被删除，需要重新运行。

## 依赖关系

### 外部依赖

- **源工具链包**: 由 `depot_tools/win_toolchain/package_from_installed.py` 生成
- **Visual Studio**: 源工具链必须从完整安装的 VS 打包而来
- **Windows SDK**: 包含在 Visual Studio 安装中

### Python 依赖

- **Python 标准库**: argparse, os, shutil, sys
- **Python 版本**: 支持 Python 2 和 Python 3（使用 `__future__` 导入）

### 平台依赖

- **Windows 平台**: 脚本强制要求在 Windows 上运行
- **文件系统**: 需要支持 Windows 文件属性和权限

## 设计模式与设计决策

### 回调函数模式

使用 `filter_toolchain_files` 作为 `shutil.copytree` 的回调函数，这是一个标准的策略模式应用：

```python
shutil.copytree(src_dir, target_dir, ignore=filter_toolchain_files)
```

**优点**:
- 与标准库集成良好
- 过滤逻辑与复制逻辑分离
- 高效：在遍历过程中过滤，避免二次遍历

### 平台检测模式

脚本显式检查平台并拒绝在非 Windows 系统运行：

```python
if sys.platform != 'win32':
  print('This script only runs on Windows.', file=sys.stderr)
  sys.exit(1)
```

这种防御性编程避免了：
- 跨平台路径问题
- 文件权限和属性问题
- 用户在错误环境运行时产生的混淆

### 列表驱动配置

使用 `IGNORE_LIST` 列表驱动过滤逻辑，而非硬编码条件判断：

**优点**:
- 配置集中管理
- 易于维护和扩展
- 代码逻辑简洁

**扩展性**: 添加新的过滤规则只需修改列表，无需改动逻辑代码。

### 错误优先的设计

`getenv` 函数优先处理错误情况，提供清晰的错误消息和解决方案：

```python
if not val:
  print('...you should run this via create_and_upload.py.', file=sys.stderr)
  sys.exit(1)
```

这种设计提升了用户体验，特别是对于不熟悉系统的开发者。

## 性能考量

### 文件复制性能

复制大型工具链（几 GB）是性能瓶颈：

- **I/O 密集**: 受磁盘速度限制
- **CPU 轻量**: 过滤逻辑很简单
- **内存占用**: 低，只在内存中保持当前目录的文件列表

典型性能：
- SSD: 200-500 MB/s
- HDD: 50-150 MB/s
- 总时间: 1-5 分钟（取决于磁盘和工具链大小）

### 过滤优化

通过过滤减少复制量的效果：
- **原始大小**: 约 10-15 GB（完整工具链）
- **过滤后**: 约 3-5 GB
- **节省**: 60-70% 的数据量

过滤带来的性能提升：
1. 减少复制时间
2. 减少打包压缩时间
3. 减少上传时间
4. 减少下载和部署时间

### 内存使用

`shutil.copytree` 不会一次性加载所有文件到内存：
- 逐目录遍历和复制
- 回调函数只接收当前目录的文件列表
- 内存占用与单个目录的文件数成正比，通常小于 1 MB

### 优化建议

潜在的优化方向：

1. **并行复制**: 可以并行复制多个顶级目录，但收益有限（I/O 瓶颈）
2. **增量更新**: 检测变化的文件，只复制修改的部分（复杂度高）
3. **符号链接**: 对于未变化的文件使用硬链接（需要文件系统支持）
4. **流式压缩**: 边复制边压缩，减少总时间（需要重构）

## 相关文件

- **`infra/bots/assets/win_toolchain/create_and_upload.py`**: 上层编排脚本，调用本脚本并上传资产
- **`infra/bots/assets/win_toolchain/__init__.py`**: Python 包标识文件
- **`infra/bots/assets/win_toolchain/VERSION`**: 资产版本号文件
- **`infra/bots/assets/win_toolchain/download.py`**: 从 CIPD 下载资产的脚本
- **`depot_tools/win_toolchain/package_from_installed.py`**: 从本地 Visual Studio 安装打包工具链的源脚本
- **`bin/sk`**: Skia 资产管理工具，调用本脚本进行资产创建

### 完整工作流

```
1. 在 Windows 机器上安装 Visual Studio（包含所需组件）
   ↓
2. 运行 depot_tools/win_toolchain/package_from_installed.py
   输出: <SHA256>.zip
   ↓
3. 解压 zip 文件到某个目录
   ↓
4. 运行 create_and_upload.py --src_dir <解压目录>
   ├─ 设置环境变量 WIN_TOOLCHAIN_SRC_DIR
   ├─ 调用 sk asset upload
   │   └─ sk 调用本脚本 create.py
   │       ├─ 读取环境变量获取源目录
   │       ├─ 过滤和复制文件
   │       └─ 生成精简的工具链
   └─ sk 打包并上传到 CIPD
   ↓
5. CI 系统从 CIPD 下载资产用于构建
```

该脚本是整个流程中的核心过滤和复制步骤，确保最终资产既包含所有必需文件，又尽可能精简。
