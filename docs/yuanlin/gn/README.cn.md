# gn/ - GN 构建系统根目录

## 概述

`gn/` 目录是 Skia 项目中 GN (Generate Ninja) 构建系统的核心目录。GN 是 Chromium 项目开发的元构建系统，能够生成 Ninja 构建文件，用于高效地编译 Skia 图形库。该目录包含了所有平台（Windows、macOS、Linux、Android、iOS、WebAssembly）的构建配置、源文件列表、编译选项和辅助脚本。

Skia 使用 GN 作为其主要的独立构建系统（standalone build system）。`BUILDCONFIG.gn` 文件是整个 GN 构建的入口点，负责检测目标平台、设置默认编译器参数、定义工具链选择逻辑。所有的 `.gni` 文件（GN Import 文件）定义了 Skia 各模块的源文件列表，这些列表大多由 Bazel 导出工具自动生成，确保 GN 和 Bazel 两套构建系统的一致性。

该目录还包含多个 Python 辅助脚本，用于自动检测编译器类型、查找 Windows SDK、生成 Android.bp 文件（用于 Android 框架集成）、以及将 GN 配置转换为 CMake 格式。这些工具使得 Skia 能够灵活地集成到不同的构建环境中。

GN 构建的整体流程为：首先通过 `BUILDCONFIG.gn` 确定平台和工具链，然后加载 `skia.gni` 中的功能开关，接着根据各 `.gni` 文件确定源文件列表，最后由 `gn/skia/BUILD.gn` 和 `gn/toolchain/BUILD.gn` 提供编译配置和工具链定义。

## 目录结构

```
gn/
├── BUILDCONFIG.gn              # GN 构建全局配置入口
├── BUILD.bazel                 # Bazel 构建兼容文件
├── __init__.py                 # Python 模块初始化
├── skia.gni                    # Skia 功能开关与构建选项
├── core.gni                    # 核心模块源文件列表（自动生成）
├── gpu.gni                     # GPU 模块源文件列表（自动生成）
├── graphite.gni                # Graphite 后端源文件列表（自动生成）
├── sksl.gni                    # SkSL 着色语言源文件列表
├── sksl_tests.gni              # SkSL 测试文件列表
├── effects.gni                 # 效果模块源文件列表
├── effects_imagefilters.gni    # 图像滤镜源文件列表
├── codec.gni                   # 图像编解码器源文件列表
├── pdf.gni                     # PDF 模块源文件列表
├── svg.gni                     # SVG 模块源文件列表
├── xml.gni                     # XML 模块源文件列表
├── xps.gni                     # XPS 模块源文件列表
├── ports.gni                   # 平台适配层源文件列表
├── opts.gni                    # CPU 优化源文件列表
├── pathops.gni                 # 路径操作源文件列表
├── utils.gni                   # 工具类源文件列表
├── shared_sources.gni          # 共享源文件列表
├── bench.gni                   # 基准测试源文件列表
├── tests.gni                   # 测试源文件列表
├── gm.gni                      # Golden Master 测试源文件列表
├── fuzz.gni                    # 模糊测试源文件列表
├── ios.gni                     # iOS 平台构建模板
├── rust.gni                    # Rust FFI 源文件列表（自动生成）
├── gn_to_bp.py                 # GN 转 Android.bp 工具
├── gn_to_bp_utils.py           # Android.bp 转换辅助工具
├── gn_to_cmake.py              # GN 转 CMake 工具
├── gn_meta_sln.py              # Visual Studio 解决方案生成器
├── skqp_gn_args.py             # SkQP GN 参数定义
├── bazel_build.py              # Bazel 构建辅助脚本
├── find_msvc.py                # 自动查找 MSVC 编译器
├── find_headers.py             # 头文件搜索工具
├── find_xcode_sysroot.py       # Xcode sysroot 查找工具
├── highest_version_dir.py      # 最高版本目录查找
├── is_clang.py                 # Clang 编译器检测
├── compile_sksl_tests.py       # SkSL 测试编译脚本
├── minify_sksl.py              # SkSL 代码压缩工具
├── minify_sksl_tests.py        # SkSL 测试压缩脚本
├── run_sksllex.py              # SkSL 词法分析器运行脚本
├── make_gm_gni.py              # GM 测试列表生成器
├── codesign_ios.py             # iOS 代码签名工具
├── compile_ib_files.py         # iOS Interface Builder 文件编译
├── copy_git_directory.py       # Git 目录复制工具
├── push_to_android.py          # Android 设备推送工具
├── call.py                     # 通用命令调用工具
├── checkdir.py                 # 目录检查工具
├── cp.py                       # 跨平台文件复制
├── rm.py                       # 跨平台文件删除
├── skia/                       # Skia 特定的 GN 编译配置
├── portable/                   # 可移植的 GN 配置
└── toolchain/                  # 工具链定义
```

## 关键文件

### BUILDCONFIG.gn - 全局构建配置
这是 GN 构建系统的顶层配置文件，负责：
- 声明全局构建参数（`is_official_build`、`is_component_build`、`sanitize`、`ndk` 等）
- 检测目标平台（`is_android`、`is_ios`、`is_linux`、`is_mac`、`is_wasm`、`is_win`）
- 检测目标 CPU 架构（`target_cpu`、`current_cpu`）
- 判断是否使用 Clang 编译器（`is_clang`）
- 配置 Android NDK 工具链路径
- 查找 Windows MSVC 和 SDK 路径
- 定义 `component()` 模板（静态库或共享库）
- 设置默认编译配置（`default_configs`）
- 选择默认工具链（msvc / wasm / gcc_like）

### skia.gni - Skia 功能开关
定义 Skia 的所有构建选项和功能开关，包括：
- 图形后端选择：`skia_enable_ganesh`、`skia_enable_graphite`、`skia_use_gl`、`skia_use_vulkan`、`skia_use_metal`、`skia_use_dawn`、`skia_use_direct3d`
- 图像编解码器：`skia_use_libjpeg_turbo_decode`、`skia_use_libpng_decode`、`skia_use_libwebp_decode`、`skia_use_wuffs`
- 字体管理器：`skia_use_freetype`、`skia_use_harfbuzz`、`skia_use_fontconfig`、`skia_use_fonthost_mac`
- 模块开关：`skia_enable_pdf`、`skia_enable_skottie`、`skia_enable_svg`
- 自定义目标模板：`skia_source_set`、`skia_static_library`、`skia_shared_library`、`skia_executable`

### 自动生成的 .gni 文件
以下文件由 `bazel/exporter_tool` 自动生成，不应手动编辑：
- `core.gni` - 核心源文件列表，定义 `skia_core_public`、`skia_core_sources` 等变量
- `gpu.gni` - GPU 相关源文件列表
- `graphite.gni` - Graphite 渲染后端源文件列表
- `rust.gni` - Rust FFI 绑定文件列表

## 构建配置说明

### 基本构建流程
```bash
# 获取 GN 工具
python3 bin/fetch-gn

# 生成构建文件（Debug 模式）
bin/gn gen out/Debug

# 生成构建文件（Release 模式）
bin/gn gen out/Release --args='is_official_build=true'

# 使用 Ninja 编译
ninja -C out/Debug
```

### 常用构建参数
```
is_official_build=true       # Release 构建
is_component_build=true      # 构建为共享库
is_debug=false               # 禁用调试信息
skia_enable_ganesh=true      # 启用 Ganesh GPU 后端
skia_enable_graphite=true    # 启用 Graphite 后端
skia_use_vulkan=true         # 启用 Vulkan 支持
skia_use_metal=true          # 启用 Metal 支持（macOS/iOS）
ndk="/path/to/ndk"           # Android NDK 路径
target_cpu="arm64"           # 目标 CPU 架构
```

## 依赖关系

- `gn/skia/BUILD.gn` - 提供编译器标志和警告配置
- `gn/portable/BUILD.gn` - 提供可移植的异常处理和 RTTI 配置
- `gn/toolchain/BUILD.gn` - 提供工具链定义（gcc_like、msvc、wasm）
- `gn/toolchain/wasm.gni` - WebAssembly 构建配置
- `//BUILD.gn` - 项目根目录的主构建文件，引用本目录中的 `.gni` 文件
- `third_party/` - 第三方依赖的构建规则

## 相关文档与参考

- [GN 官方文档](https://gn.googlesource.com/gn/+/main/docs/)
- [Skia 构建指南](https://skia.org/docs/user/build/)
- `gn/skia/README.md` - Skia 编译配置详细说明
- `gn/toolchain/README.md` - 工具链配置详细说明
- `bazel/exporter_tool/README.md` - .gni 文件自动生成说明
