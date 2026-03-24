# gn_to_bp.py - Android.bp 构建文件生成器

> 源文件: `gn/gn_to_bp.py`

## 概述

`gn_to_bp.py` 是 Skia 构建系统中的核心脚本，用于从 GN（Generate Ninja）构建配置自动生成 Android 框架使用的 `Android.bp`（Blueprint）构建文件和各平台的 `SkUserConfig.h` 配置头文件。

该脚本是 Skia 与 Android 框架集成的关键桥梁。它通过运行 GN 工具获取多个目标平台（Android、Linux、macOS、Windows）的构建元数据（源文件列表、编译标志、包含目录等），然后将这些数据填充到 `Android.bp` 模板中。生成的 `Android.bp` 由 Android 的 autoroller 自动提交到 AOSP。

## 架构位置

```
Skia 与 Android 框架集成
├── gn/
│   ├── gn_to_bp.py             <-- 本文件：Android.bp 生成器
│   ├── gn_to_bp_utils.py       <-- 辅助工具函数
│   ├── skqp_gn_args.py         <-- SkQP GN 参数
│   └── opts.gni                <-- 架构特定源文件定义
├── Android.bp                  <-- 生成的构建文件（输出）
├── android/include/config/SkUserConfig.h  <-- 生成的 Android 配置
└── ...                         <-- 其他平台的 SkUserConfig.h
```

## 主要类与结构体

本文件没有定义 Python 类，但定义了重要的数据模板。

### `bp` 模板（`string.Template`）
核心 `Android.bp` 模板，包含以下主要构建目标：
- `skia_arch_defaults` - 架构特定的默认配置
- `skia_defaults` - Skia 通用默认配置（编译标志、包含目录）
- `libskia_renderengine` - RenderEngine 专用的精简 Skia 库
- `libskia_rust_ffi` - Rust FFI 静态库（Fontations 支持）
- `libskia_skcms` - skcms 颜色管理库
- `libskia` - 完整的 Skia 库
- `skia_deps` / `skia_renderengine_deps` - 依赖声明
- `skia_tool_deps` - 工具依赖
- `skia_gm_srcs` / `skia_test_minus_gm_srcs` - 测试源文件
- `skqp_jni_defaults` - SkQP JNI 默认配置

### `skqp_instance_bp` 模板
SkQP 实例模板，用于生成 `CtsSkQPTestCases` 和 `AllSkQPTestCases` 两个测试 APK 模块。

## 公共 API 函数

### `main()`
脚本入口，执行完整的生成流程：
1. 为多个平台运行 GN 获取构建元数据
2. 提取源文件列表、编译标志和包含目录
3. 计算平台特定和跨平台共享的源文件
4. 生成各平台的 `SkUserConfig.h`
5. 填充并输出 `Android.bp`

### `generate_args(target_os, enable_gpu, renderengine=False)`
生成 GN 参数字典。根据目标操作系统和 GPU 支持情况配置不同的构建选项。

### `write_android_config(config_path, defines, isNDKConfig=False)`
生成 Android 平台的 `SkUserConfig.h`，包含 `SK_BUILD_FOR_ANDROID` 验证和平台排他性检查。

### `write_config(config_path, defines, platform)`
生成非 Android 平台的 `SkUserConfig.h`，包含平台标志修正和排他性检查。

## 内部实现细节

### 多平台 GN 运行

脚本为六种配置分别运行 GN：
1. **Android（GPU 启用）** - 完整 Skia 库（`libskia`）
2. **Android（GPU 启用，RenderEngine）** - 精简版 Skia（`libskia_renderengine`）
3. **Android SkQP** - SkQP 测试库
4. **Linux（GPU 禁用）** - 主机构建
5. **macOS（GPU 禁用）** - 主机构建
6. **Windows（GPU 禁用）** - 主机构建

每次 GN 运行通过 `gn_to_bp_utils.GenerateJSONFromGN` 获取构建元数据的 JSON 输出。

### GN 参数生成

`generate_args()` 函数根据目标平台生成 GN 参数字典，核心配置包括：
- `is_official_build = true`：启用生产优化
- `target_cpu = "none"`：由 `gn_to_bp_utils` 后续处理架构特定文件
- 字体管理器配置：禁用所有内置字体管理器，Android 框架自行处理字体
- GPU 配置：根据 `enable_gpu` 参数控制 Vulkan/Ganesh/Graphite 的启用
- 编解码器配置：RenderEngine 模式禁用所有图像编解码器以缩减体积

### 跨平台源文件处理

```python
srcs = android_srcs.intersection(linux_srcs).intersection(mac_srcs).intersection(win_srcs)
android_srcs = android_srcs.difference(srcs)
linux_srcs   = linux_srcs.difference(srcs)
mac_srcs     = mac_srcs.difference(srcs)
win_srcs     = win_srcs.difference(srcs)
```

通过集合运算，将源文件分为所有平台共享的（`srcs`）和各平台特有的（`android_srcs`, `linux_srcs` 等），最小化 `Android.bp` 中的重复。

### 源文件过滤

```python
def is_src(s):
    src_extensions = ['.s', '.S', '.c', '.cpp', '.cc', '.cxx', '.mm']
    (base, ext) = os.path.splitext(s)
    (_, baseExt) = os.path.splitext(base)
    return ext in src_extensions and baseExt != ".rs"
```

Android Soong 构建系统仅接受特定的源文件扩展名，头文件和 Rust 生成的 `*.rs.*` 文件需要排除。

### 依赖收集

```python
gn_to_bp_utils.GrabDependentValues(js, '//:skia', 'sources', android_srcs, VMA_DEP)
```

`GrabDependentValues` 递归遍历 GN 目标的依赖树，收集传递依赖中的源文件。某些依赖（如 VMA）可以被排除以避免引入不需要的文件。

### SkQP 双模块生成

生成两个 SkQP 测试模块：
- `CtsSkQPTestCases`（JNI 库 `libskqp_jni`）- CTS 合规性测试，尊重设备 API 级别
- `AllSkQPTestCases`（JNI 库 `libskqp_jni_alltests`）- 全覆盖测试，忽略 API 级别，添加 `-DSKQP_ENFORCE_ALL_INCLUDED_TESTS`

### SkUserConfig.h 生成

为每个平台生成特定的 `SkUserConfig.h`：
- `android/include/config/SkUserConfig.h` - Android 框架
- `renderengine/include/config/SkUserConfig.h` - RenderEngine（含 `SK_IN_RENDERENGINE` 定义）
- `skqp/include/config/SkUserConfig.h` - SkQP（NDK 配置）
- `linux/include/config/SkUserConfig.h` - Linux 主机
- `mac/include/config/SkUserConfig.h` - macOS 主机
- `win/include/config/SkUserConfig.h` - Windows 主机

### 平台排他性检查

```python
def disallow_platforms(config, desired):
    PLATFORMS = { 'IOS', 'MAC', 'WIN', 'ANDROID', 'UNIX' }
    # 生成 #if 检查，确保只有目标平台的 SK_BUILD_FOR_* 被定义
```

这防止了错误的平台检测导致的编译问题。

### VMA 和 Rust FFI 依赖处理

- **Vulkan Memory Allocator (VMA)**：作为特殊依赖处理，其源文件（`VulkanMemoryAllocatorWrapper.cpp`）和包含路径（`vma_android/include`）仅在 Android 目标中包含。脚本还负责将 VMA 头文件和许可证复制到输出目录。
- **Rust FFI（Fontations）**：通过 `rust_ffi_static`、`gensrcs` 生成 Rust 和 C++ 之间的桥接代码。`libskia_rust_ffi` 编译 Rust 代码，`libskia_cxx_bridge_code` 和 `libskia_cxx_bridge_header` 生成 C++ 绑定。

### bpfmt 格式化

```python
def bpfmt(indent, lst, sort=True):
    lst = sorted(lst)
    return ('\n' + ' '*indent).join('"%s",' % v for v in lst)
```

将字符串列表格式化为 Android.bp 的缩进和引用格式，默认排序以确保输出稳定性。

## 依赖关系

- **Python 标准库**：`argparse`, `os`, `shutil`, `string`
- **Skia 构建辅助**：`gn_to_bp_utils`（GN 运行、依赖收集、配置写入）, `skqp_gn_args`（SkQP 参数）
- **外部工具**：`gn`（GN 构建系统工具，默认在 PATH 中）

## 设计模式与设计决策

1. **模板替换模式**：使用 Python `string.Template` 定义 `Android.bp` 骨架，用构建元数据填充占位符。

2. **数据驱动生成**：所有构建配置从 GN 工具动态获取，避免手动维护源文件列表。

3. **集合运算优化**：使用集合的交集和差集操作将源文件分为共享和平台特定两类，消除 `Android.bp` 中的重复。

4. **多配置 GN 运行**：为每个目标平台单独运行 GN，确保每个平台的源文件和配置完全正确。

5. **自动化流水线集成**：设计为 autoroller 的一部分，无需人工介入即可在 Skia 代码变更后自动更新 Android 构建配置。

## 性能考量

- **多次 GN 调用**：脚本需要运行 6 次以上的 GN 进程（每个平台一次 + RenderEngine + SkQP），总耗时可达数十秒，但只在构建配置变更时执行。
- **集合运算**：使用 Python 集合的内置操作（交集、差集）处理源文件列表，效率高于手动循环比较。
- **文件排序**：`bpfmt` 函数默认对列表进行排序，确保输出稳定性并便于 diff 审查。
- **依赖收集**：`GrabDependentValues` 递归收集传递依赖的源文件，确保不遗漏间接依赖。
- **输出目录管理**：使用 `os.makedirs(exist_ok=True)` 确保输出目录结构存在，避免重复创建检查。

## 相关文件

- `gn/gn_to_bp_utils.py` - 辅助工具函数（`GenerateJSONFromGN`, `GrabDependentValues`, `CleanupCFlags`, `WriteUserConfig`）
- `gn/skqp_gn_args.py` - SkQP GN 参数配置（`GetGNArgs`）
- `gn/opts.gni` - 架构特定源文件定义（HSW/SKX SIMD 优化等）
- `Android.bp` - 生成的 Android Blueprint 构建文件
- `android/include/config/SkUserConfig.h` - 生成的 Android 配置头文件
- `renderengine/include/config/SkUserConfig.h` - 生成的 RenderEngine 配置头文件
- `skqp/include/config/SkUserConfig.h` - 生成的 SkQP 配置头文件
- `linux/include/config/SkUserConfig.h` - 生成的 Linux 配置头文件
- `mac/include/config/SkUserConfig.h` - 生成的 macOS 配置头文件
- `win/include/config/SkUserConfig.h` - 生成的 Windows 配置头文件
- `vma_android/include/vk_mem_alloc.h` - 复制的 VMA 头文件
- `platform_tools/android/apps/skqp/` - SkQP Android 应用目录
