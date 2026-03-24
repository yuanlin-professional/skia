# create.py

> 源文件: infra/bots/assets/chromebook_arm_gles/create.py

## 概述

`create.py` 是用于创建 Chromebook ARM 架构 OpenGL ES 资产的核心脚本。该脚本负责收集和打包在 ARM Chromebook 设备上进行 OpenGL ES 开发所需的库文件和头文件，包括 libGL、libEGL、libmali 等图形库，以及相关的开发头文件。

## 架构位置

该脚本是 Skia 资产管理系统中特定平台资产创建流程的一部分：

```
infra/bots/assets/chromebook_arm_gles/
├── create_and_upload.py          # 上传入口脚本
├── create.py                     # 本文件：资产创建实现
└── __init__.py                   # 包标识
```

在 Skia 的持续集成流程中，该脚本生成的资产被用于：
- 在 ARM Chromebook 设备上编译 Skia 的 OpenGL ES 后端
- 运行 GPU 相关的测试和基准测试
- 确保跨平台图形 API 的兼容性

## 主要类与结构体

该脚本采用纯函数式设计，无类定义。主要组件包括：

### 全局常量

- **`ENV_VAR = 'CHROMEBOOK_ARM_GLES_LIB_PATH'`**
  - 环境变量名称，用于接收从 `create_and_upload.py` 传递的库路径
  - 指向包含 ARM Mali 图形驱动库的目录

### 核心函数

1. **`getenv(key)`**: 安全地获取环境变量
2. **`create_asset(target_dir, gl_path)`**: 执行资产创建的主要逻辑
3. **`main()`**: 脚本入口点，参数解析和流程协调

## 公共 API 函数

### getenv(key)

```python
def getenv(key):
    """安全地获取环境变量，如果不存在则退出"""
    val = os.environ.get(key)
    if not val:
        print(('Environment variable %s not set; you should run this via '
               'create_and_upload.py.' % key), file=sys.stderr)
        sys.exit(1)
    return val
```

**功能**：获取指定环境变量的值，如果未设置则打印错误信息并终止程序。

**参数**：
- `key` (str): 环境变量名称

**返回值**：环境变量的字符串值

**设计决策**：强制要求通过 `create_and_upload.py` 调用，避免缺少必要参数导致的运行时错误。

### create_asset(target_dir, gl_path)

```python
def create_asset(target_dir, gl_path):
    """创建包含 GLES 库和头文件的资产"""
```

**功能**：执行以下操作：
1. 安装系统级的 Mesa OpenGL ES 开发包
2. 从指定路径复制 ARM Mali 图形驱动库
3. 复制 OpenGL ES 头文件到资产目录

**参数**：
- `target_dir` (str): 资产文件的输出目录
- `gl_path` (str): ARM Mali 库文件的源目录路径

**执行步骤**：

#### 1. 安装依赖包

```python
cmd = [
    'sudo','apt-get','install',
    'libgles2-mesa-dev',
    'libegl1-mesa-dev'
]
subprocess.check_call(cmd)
```

安装 Mesa 的 OpenGL ES 2.0 和 EGL 开发包，提供标准的 OpenGL ES 头文件。

#### 2. 复制库文件

```python
lib_dir = os.path.join(target_dir, 'lib')
os.mkdir(lib_dir)

to_copy = glob.glob(os.path.join(gl_path,'libGL*'))
to_copy.extend(glob.glob(os.path.join(gl_path,'libEGL*')))
to_copy.extend(glob.glob(os.path.join(gl_path,'libmali*')))
for f in to_copy:
    shutil.copy(f, lib_dir)
```

收集并复制以下库文件：
- **`libGL*`**: OpenGL 库（通常为 libGL.so 及其符号链接）
- **`libEGL*`**: EGL 库（窗口系统接口）
- **`libmali*`**: ARM Mali 专有图形驱动库

#### 3. 复制头文件

```python
include_dir = os.path.join(target_dir, 'include')
os.mkdir(include_dir)
shutil.copytree('/usr/include/EGL', os.path.join(include_dir, 'EGL'))
shutil.copytree('/usr/include/KHR', os.path.join(include_dir, 'KHR'))
shutil.copytree('/usr/include/GLES2', os.path.join(include_dir, 'GLES2'))
shutil.copytree('/usr/include/GLES3', os.path.join(include_dir, 'GLES3'))
```

从系统目录复制 OpenGL ES 标准头文件目录：
- **`EGL/`**: EGL API 头文件（egl.h, eglplatform.h 等）
- **`KHR/`**: Khronos 通用定义（khrplatform.h）
- **`GLES2/`**: OpenGL ES 2.0 API 头文件
- **`GLES3/`**: OpenGL ES 3.0+ API 头文件

### main()

```python
def main():
    """主函数，解析参数并调用资产创建"""
```

**功能**：
1. 验证运行平台为 Linux
2. 解析 `--target_dir` 命令行参数
3. 从环境变量获取库路径
4. 调用 `create_asset()` 执行资产创建

## 内部实现细节

### 库文件选择策略

使用 `glob.glob()` 进行模式匹配，确保收集所有版本和符号链接：
- `libGL*` 可能匹配：`libGL.so`, `libGL.so.1`, `libGL.so.1.2.0`
- `libEGL*` 可能匹配：`libEGL.so`, `libEGL.so.1`
- `libmali*` 可能匹配：ARM 专有驱动的各种版本

这种策略确保了动态链接器能够正确解析库依赖。

### 权限管理

使用 `sudo apt-get install` 安装系统包，需要管理员权限。这是必需的，因为：
- 需要修改系统包数据库
- 需要在 `/usr` 目录下安装文件

### 目录结构设计

生成的资产目录结构：
```
<target_dir>/
├── lib/                          # 动态链接库
│   ├── libGL.so
│   ├── libEGL.so.1
│   └── libmali.so
└── include/                      # 开发头文件
    ├── EGL/
    │   ├── egl.h
    │   └── eglplatform.h
    ├── KHR/
    │   └── khrplatform.h
    ├── GLES2/
    │   ├── gl2.h
    │   └── gl2ext.h
    └── GLES3/
        ├── gl3.h
        └── gl3ext.h
```

这种结构符合标准的 Unix 库和头文件布局，便于编译器和链接器查找。

## 依赖关系

### 系统依赖

1. **Linux 操作系统**（必需）
   - 需要 Debian/Ubuntu 系列发行版（使用 `apt-get`）
   - 需要 sudo 权限

2. **APT 包管理器**
   - 用于安装 Mesa 开发包

3. **已安装的包**
   - `libgles2-mesa-dev`: Mesa OpenGL ES 2.0 开发文件
   - `libegl1-mesa-dev`: Mesa EGL 1.x 开发文件

### Python 模块依赖

- **`argparse`**: 命令行参数解析（Python 标准库）
- **`glob`**: 文件名模式匹配（Python 标准库）
- **`os`**: 操作系统接口（Python 标准库）
- **`shutil`**: 高级文件操作（Python 标准库）
- **`subprocess`**: 子进程管理（Python 标准库）
- **`sys`**: 系统特定参数和函数（Python 标准库）

### 外部文件依赖

- **ARM Mali 库目录**：需要通过 `--lib_path` 参数指定
  - 通常从 Chromebook 设备提取
  - 包含特定硬件的专有驱动库

## 设计模式与设计决策

### 防御性编程

1. **平台检查**
   ```python
   if 'linux' not in sys.platform:
       print('This script only runs on Linux.', file=sys.stderr)
       sys.exit(1)
   ```
   明确限制运行平台，避免在不支持的系统上产生误导性错误。

2. **环境变量验证**
   通过 `getenv()` 函数确保必要的环境变量已设置，并提供清晰的错误消息。

### 模块化设计

将资产创建逻辑封装在 `create_asset()` 函数中，与参数解析和环境设置分离，提高了代码的可测试性和可维护性。

### 混合库策略

同时使用系统 Mesa 库（开源参考实现）和 ARM Mali 专有驱动：
- Mesa 提供标准的头文件和备用实现
- Mali 提供硬件加速的实际运行库
- 这种策略确保了编译时和运行时的兼容性

## 性能考量

### I/O 密集型操作

1. **包安装**
   - `apt-get install` 可能需要下载数十 MB 的包
   - 使用包管理器缓存可以显著提速

2. **文件复制**
   - 使用 `shutil.copy()` 和 `shutil.copytree()` 复制库文件和头文件
   - 总数据量：约 10-20 MB
   - 性能瓶颈在磁盘 I/O，而非 CPU

### 执行时间

- **首次运行**：1-3 分钟（需要下载包）
- **后续运行**：10-30 秒（使用 APT 缓存）

### 磁盘空间

- 输出资产大小：约 15-30 MB
- 临时空间需求：~100 MB（APT 包下载和解压）

## 相关文件

### 同目录文件

- **`create_and_upload.py`**: 上传入口脚本，调用本脚本并上传到 CIPD
- **`__init__.py`**: Python 包标识文件

### 相似资产脚本

- **`chromebook_x86_64_gles/create.py`**: x86_64 架构的对应实现
- **`chromebook_arm64_gles/create.py`**: ARM64 架构的对应实现（收集更多库）
- **`linux_vulkan_sdk/create.py`**: Linux Vulkan SDK 资产创建脚本

### 构建系统集成

- **`infra/bots/gen_tasks_logic/gen_tasks_logic.go`**: 定义使用该资产的构建任务
- **`infra/bots/recipes/`**: Recipe 脚本，在构建时解包和使用该资产

### 相关文档

- **`include/gpu/gl/GrGLInterface.h`**: Skia 的 OpenGL 接口抽象层
- **`src/gpu/ganesh/gl/`**: Skia 的 OpenGL 后端实现
