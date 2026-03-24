使用 Puppeteer 和 Chrome 测量 CanvasKit 的性能。

## 初始设置

运行 `npm ci` 安装运行测试所需的依赖项。在 //modules/canvaskit 中，运行 `make release` 构建将要使用的 canvaskit。通过修改 Makefile，也可以使用其他构建方式（例如 `make profile`）。

如果需要，可以使用 sk 工具从 CIPD 下载 lottie-samples 和/或 skp 资源：
```
sk asset download lottie-samples ~/Downloads/lottie-samples
sk asset download skps ~/Downloads/skps
```

这些资源的实际下载位置并不重要——Makefile 假设它们在 Downloads 目录中，但本地用户可以修改。

## 基本性能测试

我们有一个用于运行基准测试 (Benchmark) 的测试框架。基准测试代码片段可以添加到 `canvas_perf.js` 中。测试框架本身是 `canvas_perf.html` 和 `benchmark.js`。它会在多个帧上运行代码的"测试"部分并收集数据。

要运行基准测试，请执行 `make perf_js`。默认情况下，这将使用本地最近的 canvaskit 发布构建。如果你只想运行一个或几个测试，请修改 `canvas_perf.js` 文件，将相关的 `tests.push` 改为 `onlytests.push`，然后运行 `make perf_js`。

在 CI 上，这些测试的结果会上传到 Perf。例如：
<https://perf.skia.org/e/?queries=test%3Dcanvas_drawOval>
我们包含的指标有第 90、95 和 99 百分位帧、平均帧时间、中位帧时间和标准差。有三种测量类型：without_flush_ms 是 test() 函数的测量值；with_flush_ms 是 test() 和随后的 flush() 调用的测量值；total_frame_ms 是帧到帧的时间。帧到帧的测量很重要，因为它考虑了 GPU 需要完成的所有工作，即使在 CanvasKit 刷新之后也是如此。

## Skottie 帧性能

有一个测试框架用于收集渲染 skottie 动画 600 帧的数据，以类似于向用户展示的方式循环播放（例如在 skottie.skia.org 上的方式）。

要在本地使用特定的 skottie 动画进行测试，可以随意修改 Makefile 来调整 `input_lottie` 参数，然后运行 `make frames`。测试框架本身是 `skottie-frames.html` 和 `benchmark.js`。

在 CI 上，这些测试的结果会上传到 Perf。例如：
<https://perf.skia.org/e/?queries=test%3Dlego_loader>
我们包含的指标有前 5 帧时间、平均帧时间、第 90、95 和 99 百分位帧时间。

## SKP 性能

有一个测试框架会重复绘制一个 SKP 并测量各种指标。这由 `skottie-frames.html` 和 `benchmark.js` 处理。和之前一样，可以随意修改 Makefile（`input_skp` 参数）并运行 `make skp`。

在 CI 上，这些测试的结果会上传到 Perf。例如：
<https://perf.skia.org/e/?queries=binary%3DCanvasKit%26test%3Ddesk_chalkboard.skp>
