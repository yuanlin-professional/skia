# gn/skia/ - Skia 专用 GN 编译配置

## 概述

`gn/skia/` 目录包含 Skia 项目专用的 GN 编译配置（config）。目录中唯一的文件 `BUILD.gn` 定义了大量的 `config()` 规则，这些规则控制着编译器标志（compiler flags）、预处理器定义（defines）、头文件搜索路径、链接器选项等核心构建参数。

这些配置在 `gn/BUILDCONFIG.gn` 中被引用为默认配置（`default_configs`），并自动应用于所有 Skia 构建目标。例如，`//gn/skia:default` 配置包含了针对不同平台（Windows/macOS/Linux/Android/iOS/WASM）的编译器特定标志、C++ 标准版本设置、系统头文件路径、平台定义宏等。

配置采用分层设计：基础配置（如 `default`、`no_exceptions`、`no_rtti`）适用于所有目标；条件配置（如 `optimize`、`NDEBUG`、`debug_symbols`）根据构建模式选择性启用；平台配置则在基础配置内部通过 `is_win`、`is_mac` 等条件变量进行分支处理。这种设计使得同一套构建系统能够支持多种平台和编译器组合。

`BUILD.gn` 还包含额外的编译参数声明（`extra_cflags`、`extra_ldflags` 等），允许用户在不修改构建文件的情况下，通过 GN 参数注入自定义编译标志。此外，`werror` 参数可以将编译警告升级为错误，`malloc` 参数可以指定自定义内存分配器。

## 目录结构

```
gn/skia/
└── BUILD.gn    # Skia 编译配置定义（约 500+ 行）
```

## 关键文件

### BUILD.gn - 编译配置集合

该文件定义了以下主要配置：

#### 用户可配置参数
```gn
declare_args() {
  extra_asmflags = []      # 额外的汇编标志
  extra_cflags = []        # 额外的 C/C++ 编译标志
  extra_cflags_c = []      # 额外的 C 编译标志
  extra_cflags_cc = []     # 额外的 C++ 编译标志
  extra_ldflags = []       # 额外的链接标志
  malloc = ""              # 自定义内存分配器库
  werror = false           # 是否将警告视为错误
  xcode_sysroot = ""       # Xcode sysroot 路径
}
```

#### 核心配置规则

| 配置名称 | 说明 |
|---------|------|
| `config("default")` | 默认编译配置，包含所有平台的基础编译标志 |
| `config("no_exceptions")` | 禁用 C++ 异常处理 |
| `config("no_rtti")` | 禁用运行时类型信息（RTTI） |
| `config("strict_aliasing")` | 启用严格别名规则优化 |
| `config("no_strict_aliasing")` | 禁用严格别名规则（用于 PartitionAlloc） |
| `config("optimize")` | Release 模式优化标志 |
| `config("NDEBUG")` | 定义 NDEBUG 宏，禁用断言 |
| `config("trivial_abi")` | 启用 [[clang::trivial_abi]] 属性 |
| `config("debug_symbols")` | 生成调试符号 |
| `config("warnings")` | 启用严格的编译警告 |
| `config("warnings_for_public_headers")` | 公共头文件的额外警告 |
| `config("executable")` | 可执行文件的链接配置 |
| `config("wasm")` | WebAssembly 平台特定配置 |
| `config("extra_flags")` | 用户自定义标志注入点 |

#### default 配置的平台处理逻辑

`config("default")` 是最复杂的配置，包含以下平台分支：

- **Windows (MSVC/Clang-CL)**：设置 `/bigobj`、`/utf-8`、C++20 标准（`/std:c++20`）、Windows SDK 头文件路径和库路径、定义 `_CRT_SECURE_NO_WARNINGS`、`WIN32_LEAN_AND_MEAN`、`NOMINMAX` 等宏
- **macOS**：通过 `find_xcode_sysroot.py` 自动查找 Xcode sysroot，设置 `-isysroot` 和最低部署版本
- **iOS**：配置 sysroot、最低 iOS 版本、设备/模拟器目标区分
- **Android**：配置 NDK 的头文件路径和系统库路径，设置 `-DANDROID`
- **WebAssembly**：加载 `wasm.gni` 中的特定定义
- **通用 GCC/Clang**：设置 `-std=c++20`、`-ffp-contract=off` 等标志

## 构建配置说明

### 配置的应用方式

在 `gn/BUILDCONFIG.gn` 中，配置被组合为 `default_configs` 列表：

```gn
default_configs = [
  "//gn/skia:default",
  "//gn/skia:no_exceptions",
  "//gn/skia:no_rtti",
  "//gn/skia:strict_aliasing",
]
if (!is_debug) {
  default_configs += [
    "//gn/skia:optimize",
    "//gn/skia:NDEBUG",
  ]
}
```

该列表会自动应用于所有 `executable`、`source_set`、`static_library`、`shared_library` 和 `component` 目标。

### 使用自定义编译标志

用户可以通过 GN 参数注入自定义编译标志：

```bash
# 添加自定义 C++ 编译标志
gn gen out/Debug --args='extra_cflags_cc=["-fsanitize=address"]'

# 启用警告作为错误
gn gen out/Debug --args='werror=true'

# 使用自定义内存分配器
gn gen out/Debug --args='malloc="jemalloc"'
```

### iOS/macOS sysroot 查找

对于 iOS 和 macOS 构建，`BUILD.gn` 会自动调用 `find_xcode_sysroot.py` 脚本来定位 Xcode SDK 路径。用户也可以通过 `xcode_sysroot` 参数手动指定：

```bash
gn gen out/ios --args='target_os="ios" xcode_sysroot="/path/to/sdk"'
```

## 依赖关系

- 被 `gn/BUILDCONFIG.gn` 引用，作为全局默认配置
- 导入 `gn/skia.gni` 获取 Skia 功能开关信息
- 导入 `gn/toolchain/wasm.gni` 获取 WASM 构建定义
- 调用 `gn/find_xcode_sysroot.py` 查找 Apple 平台 SDK

## 相关文档与参考

- [GN config 参考文档](https://gn.googlesource.com/gn/+/main/docs/reference.md#func_config)
- [Skia 构建参数说明](https://skia.org/docs/user/build/)
- `gn/BUILDCONFIG.gn` - 全局构建配置，定义了如何使用这些 config
- `gn/portable/BUILD.gn` - 可移植的编译配置补充
- `gn/toolchain/BUILD.gn` - 工具链定义
