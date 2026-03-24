# bazel/ - Bazel 构建系统

## 概述

`bazel/` 目录是 Skia 项目 Bazel 构建系统的核心目录。Bazel 是 Google 开发的大规模构建工具，Skia 使用它作为 GN 之外的另一套构建系统，特别用于与 Google 内部构建系统（Blaze/G3）保持兼容、支持远程构建执行（RBE）、以及作为源文件列表的"真实来源"（source of truth）。Bazel 中定义的源文件列表会通过 `exporter_tool` 自动导出为 GN 的 `.gni` 文件。

该目录包含了 Bazel 构建所需的规则（rules）、宏（macros）、构建标志（flags）、外部依赖管理、工具链配置、CI 构建配置等。Skia 的 Bazel 构建支持 Linux x64、macOS (Intel/ARM)、Windows x64、iOS、Android (NDK) 等多个目标平台，并支持通过 hermetic 工具链确保构建的可重复性。

`buildrc` 文件定义了大量的预设构建配置（如 `for_linux_x64_debug`、`for_mac_arm64_release` 等），方便 CI 系统和开发者快速切换不同的目标平台和构建模式。`deps.json` 文件管理所有外部依赖的版本信息，`external/` 子目录为每个第三方依赖提供 Bazel 构建文件。

此外，Bazel 构建系统还集成了 Rust (通过 `cxx` bridge)、Go (用于内部工具)、WebAssembly (通过 Emscripten) 等多语言支持，以及代码生成、GCS 资源镜像、Karma 测试等高级功能。

## 目录结构

```
bazel/
├── BUILD.bazel                         # Bazel 包定义
├── buildrc                             # CI 构建配置集合
├── Makefile                            # 便捷构建命令
├── deps.json                           # 外部依赖版本清单
├── skia_rules.bzl                      # Skia 自定义 Bazel 规则
├── macros.bzl                          # 通用 Bazel 宏（含第三方依赖）
├── flags.bzl                           # 构建标志和选项定义
├── cipd_deps.bzl                       # CIPD 依赖管理
├── cipd_install.bzl                    # CIPD 包下载安装规则
├── cpp_modules.bzl                     # C++ 模块化编译支持
├── devicesrc                           # 设备测试配置
├── download_config_files.bzl           # 配置文件下载规则
├── gcs_mirror.bzl                      # GCS 镜像 URL 生成
├── gen_compile_flags_txt_linux_amd64.bzl  # Linux 编译标志生成
├── generate_cpp_files_for_headers.bzl  # 头文件对应的 cpp 文件生成
├── go_googleapis_compatibility_hack.bzl # googleapis Go 兼容性处理
├── remove_indentation.bzl              # 缩进处理工具
├── run_cxxbridge_cmd.bzl               # Rust CXX Bridge 运行规则
├── rust_cxx_bridge.bzl                 # Rust CXX Bridge 集成
├── common_config_settings/             # 通用构建配置设置
│   └── BUILD.bazel
├── deps_parser/                        # DEPS 文件解析工具
│   ├── BUILD.bazel
│   └── deps_parser.go
├── device_specific_configs/            # 设备特定配置
│   ├── BUILD.bazel
│   ├── device_specific_configs.go
│   ├── device_specific_configs_test.go
│   └── generate/
├── exporter/                           # GNI 和 CMake 导出器
│   ├── BUILD.bazel
│   ├── gni_exporter.go
│   ├── cmake_exporter.go
│   └── ...（其他导出器源文件）
├── exporter_tool/                      # 导出工具可执行程序
│   ├── BUILD.bazel
│   ├── main.go
│   └── README.md
├── external/                           # 第三方依赖的 Bazel 构建文件
│   ├── dawn/
│   ├── freetype/
│   ├── harfbuzz/
│   ├── icu/
│   ├── libpng/
│   ├── vulkan_headers/
│   └── ...（35+ 个外部依赖）
├── gcs_mirror/                         # GCS 资源镜像工具
│   └── gcs_mirror.go
├── karma/                              # Karma 浏览器测试集成
│   ├── BUILD.bazel.old
│   └── karma_test.bzl
├── platform/                           # 平台定义
│   └── BUILD.bazel
├── rbe/                                # 远程构建执行配置
│   ├── gce_linux/
│   ├── gce_linux_container/
│   ├── Makefile
│   └── README.md
└── user/                               # 用户自定义配置
    └── README.md
```

## 关键文件

### skia_rules.bzl - Skia 自定义 Bazel 规则

定义了 Skia 项目专用的 Bazel 规则和宏：
- `skia_cc_library` - Skia C++ 库目标，自动应用默认编译选项和链接选项
- `skia_cc_binary` - Skia C++ 可执行目标
- `skia_objc_library` - Skia Objective-C 库（用于 Apple 平台）
- `skia_filegroup` - 源文件分组
- `split_srcs_and_hdrs` - 自动将源文件分为 `.cpp` 和 `.h` 文件组
- `select_multi` - 增强版 `select()`，允许多个条件同时匹配

### flags.bzl - 构建标志系统

定义了 Skia 的构建标志框架：
- `string_flag_with_values` - 创建带合法值列表的字符串标志和对应的 `config_setting`
- `multi_string_flag` - 可在命令行多次设置的字符串标志
- `bool_flag` - 布尔标志

这些标志控制着 Skia 的功能开关，例如选择 GPU 后端、编解码器支持等。

### macros.bzl - 通用宏

重新导出常用的 Bazel 规则和宏，包括：
- Bazel Skylib 的 `selects`
- Emscripten 的 `wasm_cc_binary`
- Go 和 Python 构建规则
- Skia 自定义规则

### buildrc - CI 构建配置

定义了大量预设的构建配置组合，例如：
- `for_linux_x64_debug` / `for_linux_x64_release` - Linux x64 构建
- `for_mac_arm64_debug` / `for_mac_arm64_release` - macOS ARM64 构建
- `for_linux_x64_with_rbe` - 启用远程构建执行的 Linux 构建
- 各种 GPU 后端配置（Ganesh GL、Ganesh Vulkan、Graphite Dawn/Vulkan/Metal 等）

### deps.json - 外部依赖清单

以 JSON 格式记录所有外部依赖的信息：
- `name` - 依赖名称
- `remote` - Git 仓库 URL
- `commit` - 固定的 Git 提交哈希
- `build_file` - 对应的 Bazel BUILD 文件路径
- `patches` - 需要应用的补丁文件

### Makefile - 便捷命令

提供快捷的 Make 目标：
- `make generate_gni` - 从 Bazel 规则导出 GN `.gni` 文件
- `make generate_gni_rbe` - 使用 RBE 加速导出
- `make generate_cmake` - 导出 CMake 配置
- `make generate_go` / `make gazelle` - 更新 Go 构建文件

## 构建配置说明

### 基本 Bazel 构建

```bash
# 构建 Skia 核心库（Linux x64 Debug）
bazelisk build //:skia_core --config=for_linux_x64_debug

# 构建 CanvasKit（WASM）
bazelisk build //modules/canvaskit:canvaskit --config=ck_full

# 运行测试
bazelisk test //tests:... --config=for_linux_x64_debug
```

### 从 Bazel 导出 GN 文件

```bash
# 构建导出工具并生成 .gni 文件
cd bazel && make generate_gni
```

此命令首先编译 `exporter_tool`，然后扫描 Bazel 规则并生成对应的 `.gni` 文件（如 `gn/core.gni`、`gn/gpu.gni` 等）。

### 远程构建执行 (RBE)

```bash
bazelisk build //:skia_core --config=for_linux_x64_release_with_rbe --jobs=100
```

RBE 允许将编译任务分发到远程构建集群，大幅加速构建过程。

## 依赖关系

- `MODULE.bazel` (项目根目录) - 定义 Bazel 模块和外部依赖
- `toolchain/` - 提供 hermetic 工具链定义
- `third_party/externals/` - 存放第三方源代码
- `gn/*.gni` - 由 `exporter_tool` 从 Bazel 规则自动生成
- 各 `src/`、`include/`、`modules/` 目录中的 `BUILD.bazel` 文件

## 相关文档与参考

- [Bazel 官方文档](https://bazel.build/docs)
- [Skia Bazel 构建指南](https://skia.org/docs/dev/contrib/bazel/)
- `bazel/exporter_tool/README.md` - 导出工具使用说明
- `bazel/rbe/README.md` - 远程构建执行配置说明
- `bazel/user/README.md` - 用户自定义配置说明
- `toolchain/` - Bazel hermetic 工具链定义
