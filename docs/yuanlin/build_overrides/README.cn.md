# build_overrides/ - 构建参数覆盖

## 概述

`build_overrides/` 目录包含 Skia 用于覆盖第三方依赖默认构建参数的 GN 配置文件。当 Skia 集成来自 Chromium 生态系统的第三方库（如 Dawn、ANGLE、SPIRV-Tools、PartitionAlloc 等）时，这些库的构建文件通常会引用 Chromium 特有的构建参数。由于 Skia 是一个独立项目，并非在 Chromium 构建环境中编译，因此需要提供这些参数的覆盖值。

GN 的 `build_overrides` 机制允许项目为导入的模块提供自定义的构建参数值。当第三方库的 `.gni` 文件执行 `import("//build_overrides/xxx.gni")` 时，GN 会在此目录中查找对应文件。通过这种方式，Skia 能够在不修改第三方库源代码的情况下，调整其构建行为以适应 Skia 的构建环境。

该目录中的每个文件对应一个第三方依赖或构建子系统，设置了诸如 `build_with_chromium = false`、库路径、特性开关等变量。这些覆盖确保第三方库在 Skia 的 GN 构建中能够正确编译，同时不会引入 Chromium 特有的依赖或行为。

## 目录结构

```
build_overrides/
├── angle.gni              # ANGLE 图形库构建参数覆盖
├── build.gni              # 通用 Chromium 构建参数覆盖
├── partition_alloc.gni    # PartitionAlloc 内存分配器覆盖
├── spirv_tools.gni        # SPIRV-Tools 构建参数覆盖
├── vulkan_headers.gni     # Vulkan Headers 构建参数覆盖
└── vulkan_tools.gni       # Vulkan Tools 构建参数覆盖
```

## 关键文件

### build.gni - 通用 Chromium 构建参数

```gn
build_with_chromium = false
build_with_angle = false
```

这是最基础的覆盖文件，设置 `build_with_chromium = false` 告知所有第三方依赖当前不在 Chromium 构建环境中。许多第三方库会根据此标志启用或禁用 Chromium 特有的功能。`build_with_angle = false` 类似地禁用了 ANGLE 特定的构建路径。

### angle.gni - ANGLE 图形抽象层

```gn
angle_root = "//third_party/externals/angle2"
angle_zlib_compression_utils_dir = "//third_party/zlib"
angle_spirv_headers_dir = "//third_party/externals/spirv-headers"
angle_spirv_tools_dir = "//third_party/externals/spirv-tools"
angle_has_build = false
is_cfi = false
is_chromeos = false
```

ANGLE（Almost Native Graphics Layer Engine）是一个跨平台的 OpenGL ES 实现。该文件：
- 设置 ANGLE 及其依赖的源码路径
- `angle_has_build = false` 表示不使用 Chromium 的 `build/` 目录
- 设置 `is_cfi = false`、`is_chromeos = false` 等 Chromium 特有的构建标志

### partition_alloc.gni - Chrome 内存分配器

这是最复杂的覆盖文件（约 78 行），为 PartitionAlloc 内存分配器提供完整的配置：

```gn
is_asan = sanitize == "ASAN"
is_hwasan = sanitize == "HWASAN"
is_cast_android = false
is_castos = false
is_cronet_build = false
is_nacl = false
is_posix = !is_win
build_with_chromium = false
```

关键配置包括：
- **Sanitizer 检测**：将 Skia 的 `sanitize` 参数映射到 PartitionAlloc 期望的 `is_asan`/`is_hwasan` 变量
- **严格别名规则处理**：`partition_alloc_remove_configs` 和 `partition_alloc_add_configs` 用于处理 GCC 严格别名优化与 PartitionAlloc 的不兼容性
- **平台支持**：只在 Android、ChromeOS、Linux、Windows 上启用
- **默认配置**：`use_partition_alloc_as_malloc_default`、`enable_backup_ref_ptr_support_default` 等安全特性配置
- **性能优先**：即使在 Debug 模式下也为 PartitionAlloc 启用优化

### spirv_tools.gni - SPIR-V 工具集

```gn
spirv_tools_standalone = false
spirv_tools_googletest_dir = "//third_party/googletest/src"
spirv_tools_spirv_headers_dir = "//third_party/externals/spirv-headers"
```

设置 SPIR-V 工具不以独立模式构建，并指定测试框架和 SPIR-V Headers 的位置。SPIR-V 是 Vulkan 和 OpenCL 使用的着色器中间表示格式。

### vulkan_headers.gni - Vulkan 头文件

```gn
# （空文件，仅包含版权声明）
```

目前此文件为空，说明 Vulkan Headers 不需要特殊的参数覆盖。

### vulkan_tools.gni - Vulkan 工具

```gn
vulkan_data_subdir = "vulkandata"
vulkan_headers_dir = "//third_party/externals/vulkan-headers"
```

设置 Vulkan 数据子目录和头文件位置。

## 构建配置说明

### 覆盖机制的工作原理

GN 的 `build_overrides` 目录位于项目根目录下。当第三方库的 `.gni` 文件包含如下导入语句时：

```gn
import("//build_overrides/build.gni")
```

GN 会解析到 `<project_root>/build_overrides/build.gni` 文件，读取其中定义的变量。这些变量会覆盖第三方库中声明的默认值。

### 添加新的覆盖

当引入新的第三方依赖时，如果该依赖引用了 `//build_overrides/` 中的文件，需要：

1. 确认第三方库期望的变量名和类型
2. 在 `build_overrides/` 中创建对应的 `.gni` 文件
3. 设置适合 Skia 独立构建的变量值
4. 测试确保第三方库能正确编译

### PartitionAlloc 集成注意事项

PartitionAlloc 的集成较为复杂，需要注意：
- 仅在特定平台上支持（Linux、Android、ChromeOS、Windows）
- 使用 Sanitizer 时会自动禁用（因为 Sanitizer 会替换内存分配器）
- MSVC（非 Clang-CL）编译器不支持
- Windows Debug + Component Build 组合不支持

## 依赖关系

- 被 `third_party/` 下各第三方依赖的 `.gni` 文件导入
- 依赖 `gn/BUILDCONFIG.gn` 中定义的平台检测变量（`is_win`、`is_linux` 等）
- 依赖 `gn/BUILDCONFIG.gn` 中的 `sanitize` 参数
- 引用 `gn/skia/BUILD.gn` 中的配置（如 `//gn/skia:strict_aliasing`）

## 相关文档与参考

- [GN build_overrides 机制](https://gn.googlesource.com/gn/+/main/docs/reference.md)
- [PartitionAlloc 文档](https://chromium.googlesource.com/chromium/src/+/HEAD/base/allocator/partition_allocator/PartitionAlloc.md)
- [ANGLE 项目](https://chromium.googlesource.com/angle/angle)
- [SPIRV-Tools](https://github.com/KhronosGroup/SPIRV-Tools)
- `gn/BUILDCONFIG.gn` - 全局构建配置
- `third_party/` - 第三方依赖的构建规则
