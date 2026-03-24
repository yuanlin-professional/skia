# gn/toolchain/ - GN 工具链配置

## 概述

`gn/toolchain/` 目录定义了 Skia GN 构建系统使用的所有工具链（toolchain）。工具链是 GN 中的核心概念，它定义了编译器、链接器、归档器等工具的调用方式和参数格式。Skia 支持三大类工具链：GCC/Clang 类工具链（用于 Linux、macOS、Android、iOS）、MSVC 工具链（用于 Windows）和 WebAssembly 工具链（用于 WASM 目标）。

`BUILD.gn` 是该目录的核心文件，体量较大（约 400+ 行），包含了 `msvc_toolchain` 模板和 `gcc_like` 工具链模板的完整定义。这些模板定义了如何调用编译器（`cc`、`cxx`）、链接器（`link`）、归档器（`ar`/`lib`）以及辅助工具（如 `stamp`、`copy`）来处理源文件。每个工具链还包含并发控制（如 `dsymutil_pool`、`link_pool`）和编译器包装器（`cc_wrapper`，用于分布式编译如 Goma/Sccache）的支持。

工具链的选择在 `gn/BUILDCONFIG.gn` 中通过 `set_default_toolchain()` 完成。Windows 平台使用 `//gn/toolchain:msvc`，WebAssembly 平台使用 `//gn/toolchain:wasm`，其他平台（Linux、macOS、Android、iOS）使用 `//gn/toolchain:gcc_like`。每种工具链还有对应的 host 版本（`msvc_host`、`gcc_like_host`），用于构建需要在主机上运行的工具。

辅助文件 `wasm.gni` 定义了 WebAssembly 构建的特殊配置，包括 WASM 库模板（`skia_wasm_lib`）和 WASM 特定的预处理器定义。`num_cpus.py` 脚本用于动态确定可用的 CPU 核心数，以控制并发编译任务数量。

## 目录结构

```
gn/toolchain/
├── BUILD.gn        # 工具链定义主文件
├── wasm.gni        # WebAssembly 构建配置
├── num_cpus.py     # CPU 核心数检测脚本
└── emsdk/          # Emscripten SDK 激活子目录
    └── BUILD.gn    # EMSDK 激活 action
```

## 关键文件

### BUILD.gn - 工具链定义

#### 用户可配置参数

```gn
declare_args() {
  host_ar = ar               # 主机归档工具
  host_cc = cc               # 主机 C 编译器
  host_cxx = cxx             # 主机 C++ 编译器
  target_ar = ar             # 目标归档工具
  target_cc = cc             # 目标 C 编译器
  target_cxx = cxx           # 目标 C++ 编译器
  cc_wrapper = ""            # 编译器包装器（如 ccache、sccache）
  dlsymutil_pool_depth = N   # dsymutil 并发数（默认为 CPU 核心数）
  link_pool_depth = -1       # 链接并发数（-1 为无限制）
}
```

#### MSVC 工具链（`msvc_toolchain` 模板）

该模板为 Windows 平台定义了完整的 MSVC 构建工具链：

- **tool("cc") / tool("cxx")**：调用 `cl.exe` 或 `clang-cl.exe` 编译 C/C++ 源文件
- **tool("asm")**：调用 `ml64.exe` 处理汇编文件
- **tool("alink")**：调用 `lib.exe` 或 `lld-link /lib` 创建静态库
- **tool("solink") / tool("link")**：调用 `link.exe` 或 `lld-link` 进行链接
- 支持 `clang_win` 参数切换到 Clang-CL 编译器
- 使用 `/showIncludes` 生成依赖信息

定义了两个工具链实例：
- `toolchain("msvc")` - 目标平台工具链（`target_cpu`）
- `toolchain("msvc_host")` - 主机工具链（`host_cpu`）

#### GCC/Clang 类工具链（`gcc_like` 模板）

该模板为类 Unix 平台定义了构建工具链：

- **tool("cc") / tool("cxx") / tool("objc") / tool("objcxx")**：调用 gcc/clang 编译源文件
- **tool("asm")**：汇编文件处理
- **tool("alink")**：调用 `ar` 创建静态库
- **tool("solink")**：创建共享库（`.so`/`.dylib`）
- **tool("link")**：链接可执行文件
- 使用 `-MMD -MF` 生成依赖文件
- 支持 `cc_wrapper` 进行分布式编译

定义了两个工具链实例：
- `toolchain("gcc_like")` - 使用 `target_cc`/`target_cxx`
- `toolchain("gcc_like_host")` - 使用 `host_cc`/`host_cxx`

#### WebAssembly 工具链

定义了 `toolchain("wasm")`，使用 Emscripten 的 `emcc`/`em++` 编译器：
- 编译器路径从 `skia_emsdk_dir` 参数获取
- 使用 `emar` 创建归档文件
- 链接器输出 `.js` 文件（通过 Emscripten 的链接步骤）

### wasm.gni - WebAssembly 构建配置

```gn
declare_args() {
  skia_emsdk_dir = rebase_path("../../third_party/externals/emsdk")
}
```

定义了 `skia_wasm_lib` 模板和 `wasm_defines` 变量：
- `skia_wasm_lib` 模板创建 WASM 可执行目标（输出 `.js` 文件）
- `wasm_defines` 包含 WASM 特定定义：`SKVX_DISABLE_SIMD`、`SK_FORCE_8_BYTE_ALIGNMENT`

### num_cpus.py - CPU 核心数检测

简单的 Python 脚本，使用 `multiprocessing.cpu_count()` 返回可用 CPU 核心数。用于设置 `dsymutil_pool` 和 `link_pool` 的默认深度。

## 构建配置说明

### Android 交叉编译

当 `ndk` 参数被设置时，工具链自动配置 NDK 工具路径：

```bash
gn gen out/android --args='ndk="/path/to/android-ndk" target_cpu="arm64"'
```

工具链会自动设置 `target_cc`、`target_cxx`、`target_ar` 为 NDK 中的 clang/llvm-ar。

### 使用编译器缓存

通过 `cc_wrapper` 参数可以启用编译器缓存：

```bash
gn gen out/Debug --args='cc_wrapper="ccache"'
```

### 控制链接并发

对于内存受限的构建环境，可以限制并发链接任务：

```bash
gn gen out/Debug --args='link_pool_depth=4'
```

## 依赖关系

- 被 `gn/BUILDCONFIG.gn` 通过 `set_default_toolchain()` 引用
- 引用 `gn/skia.gni` 获取功能开关信息
- Android 构建依赖 `BUILDCONFIG.gn` 中计算的 `ndk_host` 和 `ndk_target` 变量
- WASM 构建依赖 `third_party/externals/emsdk` 提供的 Emscripten 工具链
- `emsdk/BUILD.gn` 依赖 `bin/activate-emsdk` 脚本

## 相关文档与参考

- [GN toolchain 参考文档](https://gn.googlesource.com/gn/+/main/docs/reference.md#func_toolchain)
- [Ninja 构建系统手册](https://ninja-build.org/manual.html)
- [Emscripten SDK 文档](https://emscripten.org/docs/tools_reference/emsdk.html)
- `gn/BUILDCONFIG.gn` - 工具链选择逻辑
- `gn/toolchain/emsdk/README.md` - Emscripten SDK 激活说明
