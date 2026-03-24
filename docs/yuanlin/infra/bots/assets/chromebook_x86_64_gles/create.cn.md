# create.py

> 源文件: infra/bots/assets/chromebook_x86_64_gles/create.py

## 概述

`create.py` 为 x86_64 Chromebook 创建 OpenGL ES 资产，收集和打包 GLES/EGL 库文件及头文件。与 ARM 版本类似，但针对 Intel/AMD 处理器的 Chromebook 设备。

## 架构位置

该脚本为 x86_64 架构的 Chromebook 设备提供 OpenGL ES 开发环境，支持 Skia 在这些设备上的 GPU 渲染测试。

## 公共 API 函数

### getenv(key)
安全地获取环境变量，如果未设置则终止程序并提示应通过 `create_and_upload.py` 调用。

### create_asset(target_dir, gl_path)
创建包含 GLES 库和头文件的资产包，执行以下操作：

1. **安装 Mesa 开发包**
```python
cmd = ['sudo','apt-get','install',
       'libgles2-mesa-dev', 'libegl1-mesa-dev']
subprocess.check_call(cmd)
```

2. **复制库文件**
```python
lib_dir = os.path.join(target_dir, 'lib')
os.mkdir(lib_dir)
to_copy = glob.glob(os.path.join(gl_path,'libGL*'))
to_copy.extend(glob.glob(os.path.join(gl_path,'libEGL*')))
to_copy.extend(glob.glob(os.path.join(gl_path,'libdrm*')))
for f in to_copy:
    shutil.copy(f, lib_dir)
```
收集 libGL、libEGL 和 libdrm（Direct Rendering Manager）库。

3. **复制头文件**
从系统目录复制 EGL、KHR、GLES2、GLES3 头文件目录。

### main()
解析 `--target_dir` 参数，从环境变量获取库路径，调用 `create_asset()`。

## 内部实现细节

### 与 ARM 版本的差异

**x86_64 特定**：
- 包含 `libdrm*`（Direct Rendering Manager）库
- 针对 Intel/AMD 集成 GPU（如 Intel HD Graphics）

**ARM 特定**：
- 包含 `libmali*`（ARM Mali 专有驱动）
- 针对 ARM Mali GPU

### 库文件选择
使用 glob 模式匹配确保收集所有版本和符号链接：
- `libGL*`: libGL.so, libGL.so.1, libGL.so.1.2.0
- `libEGL*`: libEGL.so, libEGL.so.1
- `libdrm*`: libdrm.so, libdrm.so.2（x86_64 专有）

### 目录结构
```
<target_dir>/
├── lib/
│   ├── libGL.so
│   ├── libGL.so.1
│   ├── libEGL.so.1
│   └── libdrm.so.2               # x86_64 特有
└── include/
    ├── EGL/
    ├── KHR/
    ├── GLES2/
    └── GLES3/
```

## 依赖关系

### 系统依赖
- Linux（Debian/Ubuntu 系列）
- sudo 权限
- APT 包管理器
- `libgles2-mesa-dev`、`libegl1-mesa-dev` 包

### Python 依赖
- 标准库：`argparse`, `glob`, `os`, `shutil`, `subprocess`, `sys`

### 外部文件
- 从 Chromebook x86_64 设备提取的 GL/EGL/DRM 库文件

## 设计模式与设计决策

### 混合库策略
结合系统 Mesa 库和设备特定驱动：
- **Mesa**: 提供标准头文件和参考实现
- **设备库**: 提供硬件加速的实际运行库
- **DRM**: 提供 Direct Rendering 支持（x86_64 特有）

### 平台检查
强制要求在 Linux 上运行，因为需要使用 `apt-get` 安装依赖包。

## 性能考量

- **包安装**: 首次 1-3 分钟，后续 10-30 秒（APT 缓存）
- **文件复制**: 10-20 秒（10-20 MB）
- **总时间**: 首次 2-5 分钟，后续 30-60 秒

## 相关文件

- **`create_and_upload.py`**: 上传入口脚本
- **`chromebook_arm_gles/create.py`**: ARM 版本（使用 libmali）
- **`chromebook_arm64_gles/create.py`**: ARM64 版本（更复杂的库收集）
- **`infra/bots/utils.py`**: 未直接使用，但是标准依赖
