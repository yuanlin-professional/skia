# gn/toolchain/emsdk/ - Emscripten SDK 激活配置

## 概述

`gn/toolchain/emsdk/` 目录包含 Emscripten SDK (EMSDK) 的 GN 构建集成配置。Emscripten 是一个将 C/C++ 代码编译为 WebAssembly (WASM) 的工具链，Skia 使用它来构建 CanvasKit ------ 一个在 Web 浏览器中运行的高性能 2D 图形引擎。

该目录中的 `BUILD.gn` 文件定义了一个 action 目标 `activate`，用于在构建前确保 Emscripten SDK 已经被正确安装和激活。这个 action 调用 `bin/activate-emsdk` 脚本，该脚本会下载并激活指定版本的 EMSDK（当前为 4.0.7 版本）。

该 action 仅在 host 工具链下执行，因为 SDK 的安装是在主机上进行的操作，而非 WASM 目标平台上的操作。激活完成后会在 `$target_gen_dir` 中创建一个 `emsdk_done.stamp` 标记文件，以避免重复激活。Ninja 构建系统会检查该标记文件的存在与时间戳，来决定是否需要重新运行激活流程。

Emscripten 工具链是 Skia WASM 构建的基础。它将 Skia 的 C++ 代码编译为 WebAssembly 字节码，通过 JavaScript 胶水代码在浏览器中运行。CanvasKit 模块是此工具链的主要消费者，它将 Skia 的完整功能暴露为 JavaScript API，供 Web 应用（如 Flutter Web）使用。

## 目录结构

```
gn/toolchain/emsdk/
└── BUILD.gn    # EMSDK 激活 action 定义
```

## 关键文件

### BUILD.gn - EMSDK 激活 Action

文件完整内容如下：

```gn
if (current_toolchain == "//gn/toolchain:$host_toolchain") {
  action("activate") {
    script = "//bin/activate-emsdk"
    args = []
    outputs = [ "$target_gen_dir/emsdk_done.stamp" ]
  }
}
```

**关键设计点：**

1. **条件执行**：`current_toolchain == "//gn/toolchain:$host_toolchain"` 条件确保此 action 仅在 host 工具链下定义。这是因为 EMSDK 的安装是一个本地主机操作，只需要在主机平台上执行一次，而不是在每个工具链实例中都执行。

2. **脚本路径**：`script = "//bin/activate-emsdk"` 指向项目根目录的 `bin/activate-emsdk` Python 脚本。GN 中的 `//` 前缀表示项目源码根目录。

3. **输出标记**：`outputs = [ "$target_gen_dir/emsdk_done.stamp" ]` 声明一个标记文件作为输出。Ninja 构建系统利用此文件判断 action 是否需要重新执行。如果该文件已存在且 `bin/activate-emsdk` 脚本未被修改，则跳过激活步骤。

4. **无输入文件**：该 action 没有声明 `inputs`，这意味着它的重新执行仅取决于输出文件是否存在以及脚本本身是否被修改。

### bin/activate-emsdk - 关联的激活脚本

虽然此脚本位于 `bin/` 目录，但它是本 `BUILD.gn` 直接调用的核心依赖。脚本的主要逻辑包括：

```python
EMSDK_ROOT = os.path.join(SRC_ROOT_DIR, 'third_party', 'externals', 'emsdk')
EMSDK_VERSION = '4.0.7'

# 安装指定版本
subprocess.check_call([sys.executable, EMSDK_PATH, 'install', "--permanent", EMSDK_VERSION])
# 激活指定版本
subprocess.check_call([sys.executable, EMSDK_PATH, 'activate', "--permanent", EMSDK_VERSION])
```

该脚本使用 `--permanent` 标志进行安装和激活，确保 EMSDK 配置持久化，后续编译步骤可以直接使用。

## 构建配置说明

### EMSDK 激活流程

完整的 WASM 构建流程中，EMSDK 激活发生在以下步骤中：

1. 用户配置 WASM 构建：`gn gen out/wasm --args='target_cpu="wasm"'`
2. GN 在 `BUILDCONFIG.gn` 中检测到 `target_cpu == "wasm"`，自动设置 `target_os = "wasm"`
3. `is_wasm` 变量被设置为 `true`
4. 默认工具链被设置为 `//gn/toolchain:wasm`
5. WASM 工具链需要 Emscripten 编译器（`emcc`/`em++`），路径由 `skia_emsdk_dir` 参数指定
6. 当构建目标依赖 EMSDK 时，`activate` action 被触发
7. `bin/activate-emsdk` 脚本执行，下载并激活 EMSDK 4.0.7
8. 标记文件 `emsdk_done.stamp` 被创建

### EMSDK 版本管理

EMSDK 版本在 `bin/activate-emsdk` 脚本中硬编码为 `EMSDK_VERSION = '4.0.7'`。该版本需要与 `MODULE.bazel` 中定义的版本保持一致。EMSDK 的源代码本身位于 `third_party/externals/emsdk/` 目录，通过 Skia 的 `DEPS` 文件进行版本管理和同步。

更新 EMSDK 版本时需要：
1. 更新 `bin/activate-emsdk` 中的 `EMSDK_VERSION` 常量
2. 更新 `MODULE.bazel` 中对应的版本号
3. 运行 `bin/sync` 同步 EMSDK 源码
4. 重新运行 `bin/activate-emsdk` 安装新版本
5. 测试 CanvasKit 构建确保兼容性

### 平台限制

`bin/activate-emsdk` 脚本会检测运行平台：
- **linux-aarch64 / linux-arm64**：这些平台可能不支持指定版本的 EMSDK，在此情况下脚本会静默跳过安装，不会返回错误
- **其他平台**（macOS、Linux x64、Windows）：正常执行安装和激活

### 与 wasm.gni 的关系

`gn/toolchain/wasm.gni` 中定义了 EMSDK 路径和 WASM 构建模板：

```gn
declare_args() {
  skia_emsdk_dir = rebase_path("../../third_party/externals/emsdk")
}

template("skia_wasm_lib") { ... }

wasm_defines = [
  "SKVX_DISABLE_SIMD",
  "SK_FORCE_8_BYTE_ALIGNMENT",
]
```

`skia_emsdk_dir` 默认指向 `third_party/externals/emsdk`，即 `activate-emsdk` 安装的位置。用户也可以通过 GN 参数覆盖此路径，指向自定义的 EMSDK 安装位置。

## 依赖关系

- 依赖 `bin/activate-emsdk` Python 脚本执行实际的 SDK 激活
- 依赖 `third_party/externals/emsdk/` 目录中的 EMSDK 源代码和工具
- 被 `gn/toolchain/BUILD.gn` 中的 WASM 工具链间接使用
- 与 `gn/toolchain/wasm.gni` 中的 `skia_emsdk_dir` 参数配合使用
- CanvasKit 模块（`modules/canvaskit/`）是 WASM 构建的主要消费者
- `DEPS` 文件管理 EMSDK 源码的版本同步

## 相关文档与参考

- [Emscripten 官方文档](https://emscripten.org/docs/getting_started/)
- [CanvasKit 构建说明](https://skia.org/docs/user/modules/canvaskit/)
- [WebAssembly 规范](https://webassembly.org/)
- `gn/toolchain/BUILD.gn` - WASM 工具链定义，包含 `emcc`/`em++` 调用配置
- `gn/toolchain/wasm.gni` - WASM 构建配置，定义 `skia_wasm_lib` 模板和 `wasm_defines`
- `gn/BUILDCONFIG.gn` - 全局构建配置，包含 WASM 平台检测和工具链选择逻辑
- `bin/activate-emsdk` - EMSDK 安装和激活的实际执行脚本
- `modules/canvaskit/` - CanvasKit 模块，Skia 的 WASM 绑定层
