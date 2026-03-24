# create.py

> 源文件: infra/bots/assets/chromebook_arm64_gles/create.py

## 概述

`create.py` 为 ARM64 Chromebook 创建 OpenGL ES 资产，这是三个 Chromebook GLES 资产脚本中最复杂的一个，需要处理多个库路径和创建符号链接。

## 架构位置

该脚本为 64位 ARM 架构的 Chromebook（使用 ARM Mali GPU）提供 OpenGL ES 支持。

## 主要类与结构体

函数式编程风格，无类定义。

## 公共 API 函数

### getenv(key)
获取环境变量 `CHROMEBOOK_ARM64_GLES_LIB_PATH`，如果未设置则终止。

### create_asset(target_dir, gl_path)
创建 ARM64 GLES 资产，包括：

1. **安装依赖包**（添加 `-y` 自动确认）
```python
cmd = ['sudo','apt-get','install','-y',
       'libgles2-mesa-dev', 'libegl1-mesa-dev']
subprocess.check_call(cmd)
```

2. **复制标准库文件**（从 `/usr/lib64`）
```python
to_copy = glob.glob(os.path.join(gl_path,'usr/lib64/libGLES*'))
to_copy.extend(glob.glob(os.path.join(gl_path,'usr/lib64/libEGL*')))
for f in to_copy:
    shutil.copy(f, lib_dir)
```

3. **复制 apitrace 包装器**（从 `/usr/local/lib64`）
```python
prefix = 'apitrace/wrappers'
to_copy = glob.glob(os.path.join(gl_path,'usr/local/lib64', prefix, '*'))
dest = os.path.join(lib_dir, prefix)
os.makedirs(dest)
for f in to_copy:
    shutil.copy(f, dest)
```

4. **创建符号链接**
```python
subprocess.check_call(['ln', '-s', prefix+'/libGL.so', 'libGL.so'], cwd=lib_dir)
```
创建 `lib/libGL.so` -> `apitrace/wrappers/libGL.so` 的符号链接。

5. **复制头文件**
从系统 `/usr/include/` 复制 EGL、KHR、GLES2、GLES3 目录。

### main()
解析参数并调用 `create_asset()`。

## 内部实现细节

### 复杂的库路径结构

ARM64 Chromebook 使用 64位库路径 (`lib64` 而非 `lib`)：
- **`/usr/lib64/`**: 标准系统库
- **`/usr/local/lib64/`**: 本地安装的库（如 apitrace）

### apitrace 集成

**apitrace** 是 OpenGL 调试工具，提供：
- API 调用跟踪
- 性能分析
- 回放功能

包装器库的作用：
- 拦截 OpenGL 函数调用
- 记录调用序列
- 透明代理到实际驱动

### 符号链接策略

```bash
ln -s apitrace/wrappers/libGL.so libGL.so
```

这样应用程序链接 `-lGL` 时：
1. 链接器找到 `lib/libGL.so`（符号链接）
2. 实际加载 `lib/apitrace/wrappers/libGL.so`
3. apitrace 包装器代理到真实的 Mali 驱动

### 与其他版本的区别

| 版本 | 库路径 | 特殊处理 | 复杂度 |
|------|--------|---------|--------|
| ARM | 单路径 | 无 | 低 |
| x86_64 | 单路径 | libdrm | 中 |
| ARM64 | 双路径 | apitrace + symlink | 高 |

## 依赖关系

### 系统依赖
- Linux 系统（Debian/Ubuntu）
- sudo 权限
- APT 包：`libgles2-mesa-dev`, `libegl1-mesa-dev`

### Python 依赖
- 标准库：`argparse`, `glob`, `os`, `shutil`, `subprocess`, `sys`

### 外部文件
从 ARM64 Chromebook 设备提取的库文件，包含：
- `/usr/lib64/` 下的 GLES/EGL 库
- `/usr/local/lib64/apitrace/wrappers/` 下的包装器

## 设计模式与设计决策

### 分层库架构
```
应用程序
    ↓ 链接 -lGL
lib/libGL.so (符号链接)
    ↓
lib/apitrace/wrappers/libGL.so (包装器)
    ↓ dlopen
真实的 Mali 驱动库
```

这种设计允许：
- 透明的 API 跟踪（用于调试）
- 可选启用/禁用 apitrace
- 不修改应用程序代码

### 多路径库收集
从不同路径收集库文件：
- **系统路径**（`/usr/lib64/`）：标准 GLES/EGL 库
- **本地路径**（`/usr/local/lib64/`）：apitrace 包装器
- **设备路径**（通过参数传递）：可能包含额外的专有库

## 性能考量

- **文件复制**: 20-40 秒（更多文件和目录）
- **符号链接创建**: < 1 秒
- **总时间**: 首次 2-5 分钟，后续 1-2 分钟

## 相关文件

- **`create_and_upload.py`**: 上传入口
- **`__init__.py`**: 包标识
- **`chromebook_arm_gles/create.py`**: 简化版本（32位 ARM）
- **`chromebook_x86_64_gles/create.py`**: x86_64 版本
