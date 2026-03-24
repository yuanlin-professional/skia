# 前置条件

需要 Node v14 或更高版本来运行测试。我们使用 npm（Node 包管理器）来安装测试依赖项。
较新的 Node 安装版本都自带 npm。
CanvasKit 没有其他外部源代码依赖。

## 使用 GN 编译
要使用 GN 构建，您需要先按照说明下载 Skia 及其依赖项
<https://skia.org/docs/user/download>。

要编译 CanvasKit，您首先需要使用 `//bin/activate-emsdk`（或同时会调用 activate-emsdk 的 `//tools/git-sync-deps`）
脚本[下载并激活 `emscripten`][1]。
这会将相关文件放置在 `//third_party/externals/emsdk` 中，GN[2] 构建脚本将默认使用这些文件。
compile.sh 脚本自动化了默认的 GN 设置；用户可以自由设置自己的配置。如果用户想使用自己版本的 emscripten，
应设置 `skia_emsdk_dir` 参数（参见 `//skia/gn/toolchain/wasm.gni`）。有关其他可用参数，
请参阅 `//modules/canvaskit/BUILD.gn`。

[1]: https://emscripten.org/
[2]: https://chromium.googlesource.com/chromium/src/tools/gn/+/48062805e19b4697c5fbd926dc649c78b6aaa138/README.md

### MacOS 特别说明
请确保已安装 Python3，否则下载 emscripten 工具链时可能会因 SSL 证书问题而失败。<https://github.com/emscripten-core/emsdk/pull/273>

另请参阅 <https://github.com/emscripten-core/emscripten/issues/9036#issuecomment-532092743>
了解 Python3 使用错误证书的解决方案。

# 编译并运行本地示例

```
# The following installs all npm dependencies and only needs to be when setting up
# or if our npm dependencies have changed (rarely).
npm ci

make release  # make debug is much faster and has better error messages
make local-example
```

这将输出一个用于查看示例的本地端点。您可以通过修改 `./npm_build/example.html` 并刷新页面来试验 CanvasKit API。
对于一些更具实验性的 API，还有 `./npm_build/extra.html`。

有关其他可用的构建目标，请参阅 `Makefile` 和 `compile.sh`。
例如，构建一个不包含文本支持或任何"附加功能"的精简版 CanvasKit，可以运行：

    ./compile.sh no_skottie no_font

这样的精简版大约是默认发布版本大小的一半。

如果 CanvasKit 构建失败，且您看到的编译错误看起来不像是 Skia 代码的问题，
您可能需要重新安装 npm 模块。您可以找到错误消息中提到的 .dts 文件，删除它，然后重新运行 `npm ci`。

如果您使用的是正确的模块加上最新支持的 TypeScript 但仍然失败，
可能需要更新 package.json 中列出的模块版本。

# 单元测试、性能测试和覆盖率

要在调试 GPU 构建上运行单元测试并计算测试覆盖率：

```
make debug
make test-continuous
```

这会读取 karma.conf.js，打开 Chrome 浏览器并开始运行 `test/` 目录中的所有测试。
它会检测该目录中测试的更改并自动重新运行，但不会自动重新构建和重新加载 CanvasKit。
关闭 Chrome 窗口只会导致其重新打开。终止 karma 进程以停止持续监控更改。

测试使用您最近构建的 CanvasKit 版本运行。请确保也使用 `release`、`debug_cpu` 和 `release_cpu` 进行测试。
使用发布版本测试将暴露闭包编译 (Closure Compilation) 中的问题以及通常被遗忘的 extern 声明。

## 覆盖率

在本地运行 test-continuous 时会自动计算覆盖率。请注意，只有在测试调试构建时结果才有意义。
打开 `coverage/<browser version>/index.html` 查看摘要和详细的逐行结果。

## 性能测量

我们使用 puppeteer 运行 Chrome 浏览器，以一致的方式收集性能数据。
更多信息请参阅 `//tools/perf-canvaskit-puppeteer`。

## 添加测试

`tests/` 中的测试按主题分组到不同文件中。
每个文件中有 `describe` 代码块进一步组织测试，其中的 `it()` 函数测试特定行为。
`describe` 和 `it` 是 jasmine 的方法，都可以临时重命名为 `fdescribe` 和 `fit`，
这将导致 jasmine 只运行这些测试。

我们还定义了 `gm`，这是一种定义测试的方法，该测试会在画布上绘制内容，
然后截图并报告到 gold.skia.org，您可以在那里将其与 HEAD 版本的截图进行比较。

## 从 Gerrit 进行测试

在 Gerrit 中提交 CL 时，点击"choose tryjobs"并输入 CanvasKit 进行过滤。
选择所有任务，在编写本文时共有四个任务，分别对应 perf/test 和 gpu/cpu 的每种组合。

性能结果报告到 [perf.skia.org]，正确性结果报告到 [gold.skia.org]。

以这种方式运行测试时不会测量覆盖率。

# 检查输出的 WASM

[WebAssembly 二进制工具包](https://github.com/WebAssembly/wabt) 中的 `wasm2wat` 工具
可用于生成 `.wasm` 文件的人类可读文本版本。

`wasm2wat --version` 的输出应为 `1.0.13 (1.0.17)`。此版本已验证可与 `wasm_tools/SIMD/` 中的工具配合使用。
这些工具以编程方式检查 CanvasKit 构建的 `.wasm` 输出，以检测是否存在 [WASM SIMD](https://github.com/WebAssembly/simd) 操作。

# 基础设施操作手册 (Infrastructure Playbook)

在 CI 中处理 CanvasKit 时，我们使用 Docker。请查看
$SKIA_ROOT/infra/wasm-common/docker/README.md 了解更多关于构建/编辑用于构建和测试的镜像的信息。

## 更新我们构建/测试所用的 Emscripten 版本

前提是您已在本地将 emscripten 更新到较新版本的 SDK，并已验证/修复了出现的所有构建问题。

  1. 编辑 `//bin/activate-emsdk` 以安装和激活所需版本的 Emscripten。
  2. 上传包含所有更改的 CL。运行所有 .+CanvasKit 任务以确保新的构建通过。
  3. 发送 CL 进行审查。您可以将审查者指向这些步骤。

## 针对 wasm+WebGL 运行 Skia 的 GM 和单元测试 ##

一般提示：
 - 利用 run-wasm-gm-tests.html 中的跳过列表和起始索引来聚焦有问题的测试。
 - `Uncaught (in promise) RuntimeError: function signature mismatch` 通常意味着某处发生了空指针解引用。
   添加 SkASSERT 来验证。

### 调试部分 GM / 单元测试
为了加快迭代速度，建议聚焦于特定的 GM 而不是重新编译所有 GM。
可以通过修改 `compile_gm.sh` 脚本（但不要提交此更改）来设置 `GMS_TO_BUILD` 和/或 `TESTS_TO_BUILD`
为最小的文件集。其中有一个 `if false` 可以取消注释来辅助实现。

从此文件夹运行 `make gm_tests` 或 `make_gm_tests_debug`。这将在（未纳入版本控制的）`build` 子文件夹中
生成 .js 和 .wasm 文件。

运行 `make single-gm` 并导航到 <http://localhost:8000/wasm_tools/gms.html>。这将加载该 HTML 文件和
刚构建的 wasm_gm_tests 二进制文件，并运行编译进来的单个 GM 和单元测试。
您可以自由修改 //modules/canvaskit/wasm_tools/gms.html 来运行您关心的特定 GM/单元测试。

### 测试所有 GM / 单元测试
使用当前的 GN 构建，编译和重新编译可能需要相当长的时间（即将推出的 Bazel 构建应该能缓解这个问题）。

从此文件夹运行 `make gm_tests` 或 `make_gm_tests_debug`。这将在（未纳入版本控制的）`build` 子文件夹中
生成 .js 和 .wasm 文件。

切换到 `//tools/run-wasm-gm-tests` 目录。运行 `make run_local`，这将把 GM 生成的所有 PNG 文件
放入 `/tmp/wasm-gmtests` 并运行所有单元测试。
