
---
title: "跟踪 Skia 执行 (Tracing)"
linkTitle: "跟踪 Skia 执行 (Tracing)"

---


介绍
------------

Skia 被检测为以多种方式提供执行跟踪 (execution traces)。在 Chrome 中，Skia 与 Chromium 的其余部分一起使用标准的[跟踪接口](chrome://tracing)进行跟踪。在 Android 框架中，Skia 的跟踪集成到 [atrace](https://source.android.com/devices/tech/debug/ftrace) 中。

对于独立构建，Skia 的工具（DM、nanobench 和 Viewer）能够以三种方式跟踪执行，由 `--trace` 命令行参数控制。

独立跟踪
------------------

`--trace` 的大多数参数将被解释为文件名（下面描述的两个例外情况除外），跟踪事件将以 JSON 格式写入该文件，适合使用 [chrome://tracing](chrome://tracing) 查看。

<!--?prettify lang=sh?-->

    # 在几个 GM 上运行 DM 以获取跟踪数据
    out/Release/dm --config gl --match bleed --trace gl_bleed_gms.json

这将在当前目录中创建一个文件 `gl_bleed_gms.json`。Chrome 的跟踪工具有限制，无法加载大于 256 MB 的文件。为了保持在该限制以下（并避免界面中的杂乱和卡顿），最好在跟踪时运行少量测试/基准测试。以这种方式生成文件后，转到 [chrome://tracing](chrome://tracing)，点击"Load"：

![Load Button](../tracing_load.png)

... 然后选择 JSON 文件。数据将被加载，并可使用跟踪工具进行导航/检查。提示：按 '?' 可获取解释可用键盘和鼠标控制的帮助屏幕。

![Tracing interface](../tracing.png)

Android ATrace
--------------

在 Android 设备上使用 `--trace atrace` 运行任何工具将使应用程序将跟踪信息转发到 [atrace](https://source.android.com/devices/tech/debug/ftrace)。在其他平台上，这没有效果。

如果你从主机命令行运行 `systrace`，你需要提供 `-a <app_name>`，并且 `<app_name>` 参数需要与目标设备上使用的命令行完全匹配。例如，如果你使用 `adb shell "cd /data/local/tmp; ./nanobench --trace atrace ..."`，你必须传递 `-a ./nanobench`，否则 systrace 将忽略来自应用程序的事件。

控制台日志
---------------

对于简单情况，所有跟踪事件可以使用 `--trace debugf` 定向到控制台：

<!--?prettify lang=sh?-->

    # 在单个 GM 上使用 SkDebugf 跟踪运行 DM
    out/Release/dm --config gl --match ^gamma$ --trace debugf

~~~
[ 0] <skia.gpu> GrDrawingManager::internalFlush id=1 #0 {
[ 0] } GrDrawingManager::internalFlush
[ 0] <skia.gpu> GrGpu::createTexture id=1 #1 {
[ 0] } GrGpu::createTexture
[ 0] <skia.gpu> GrRenderTargetContext::discard id=1 #2 {
[ 0] } GrRenderTargetContext::discard
[ 0] <skia.gpu> SkGpuDevice::clearAll id=1 #3 {
[ 1]  <skia.gpu> GrRenderTargetContext::clear id=1 #4 {
[ 1]  } GrRenderTargetContext::clear
[ 0] } SkGpuDevice::clearAll
[ 0] <skia> SkCanvas::drawRect() #5 {
[ 1]  <skia.gpu> SkGpuDevice::drawRect id=1 #6 {
[ 2]   <skia.gpu> GrRenderTargetContext::drawRect id=1 #7 {
[ 3]    <skia.gpu> GrRenderTargetContext::addDrawOp id=1 #8 {
[ 3]    } GrRenderTargetContext::addDrawOp
[ 2]   } GrRenderTargetContext::drawRect
[ 1]  } SkGpuDevice::drawRect
[ 0] } SkCanvas::drawRect()
...
~~~

使用 Perfetto 进行跟踪
--------------
使用 `--trace perfetto` 运行任何工具将使应用程序将跟踪信息转发到 [Perfetto](https://perfetto.dev/docs/instrumentation/track-events)。Perfetto 仅支持 Linux、Mac 和 Android，不会在其他平台上运行。

默认情况下，Skia 中的 Perfetto 跟踪已配置为处理相对较短（约 10 秒或更短）的跟踪事件和会话（例如，测试的子集而不是整个测试套件）。对于任何超过约 10 秒的跟踪会话，建议使用 `--longPerfettoTrace` 运行时选项，它将更改 Skia 的 Perfetto 配置以适应更长的跟踪。在没有此运行时选项的情况下进行长时间跟踪可能会覆盖事件，导致数据丢失。

跟踪输出文件路径可以通过运行时参数更改。`--perfettoOutputDir` 设置输出目录，`--perfettoOutputFileName` 设置输出文件名（不带文件扩展名），`--perfettoOutputFileExtension` 设置输出文件扩展名。默认情况下，跟踪文件将作为 `trace.perfetto-trace` 放置在构建输出目录中。

你还可以选择为每个 nanobench 基准测试生成不同的跟踪文件。为此，请使用 `--splitPerfettoTracesByBenchmark` 选项。请注意，这将导致输出文件以不同的基准测试命名。

这些跟踪文件可以使用 [Perfetto 的 Web 可视化工具](https://ui.perfetto.dev/)进行可视化。要可视化较大的跟踪文件（任何大于约 2 GB 的文件），请参阅[这些说明](https://perfetto.dev/docs/visualization/large-traces)。

如果你遇到任何问题或意外结果，Perfetto 有一些资源可能会有所帮助。要识别潜在的根本原因，请检查 Web 可视化工具上的"Info and stats"页面，或通过对跟踪文件运行 SQL 查询（在线或使用 [trace processor 应用程序](https://perfetto.dev/docs/analysis/trace-processor)）。要诊断这些问题，请参阅关于调试数据丢失的[这一部分](https://perfetto.dev/docs/concepts/buffers#debugging-data-losses)和关于可能出现意外长时间的乱序事件的[这一部分](https://perfetto.dev/docs/concepts/buffers#flushes-and-windowed-trace-importing)。


添加更多跟踪事件
------------------------

添加更多跟踪事件涉及使用一组 `TRACE_` 宏。最简单的例子是记录函数或其他作用域中花费的时间：

~~~
#include "SkTraceEvent.h"
...
void doSomething() {
  // 为当前函数（或其他作用域）的持续时间添加事件
  // "skia" 是类别名称，用于在录制时过滤事件
  // TRACE_FUNC 是事件名称，展开为当前函数的名称
  TRACE_EVENT0("skia", TRACE_FUNC);

  if (doExtraWork) {
    TRACE_EVENT0("skia", "ExtraWorkBeingDone");
    ...
  }
}
~~~

有关更多示例，包括其他类型的跟踪事件和将参数附加到事件，请参阅 [SkTraceEventCommon.h](https://cs.chromium.org/chromium/src/third_party/skia/src/core/SkTraceEventCommon.h) 中的注释。
