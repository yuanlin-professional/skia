---
title: 'Skia 调试器 (Debugger)'
linkTitle: 'Skia 调试器 (Debugger)'
---

## 介绍

Skia 调试器是一个图形工具，用于逐步执行和分析 Skia 图片格式 (picture format) 的内容。该工具可在线使用，地址为 [https://debugger.skia.org](https://debugger.skia.org/)，也可以在本地运行。

功能：

- 绘制命令和多帧回放
- 在任意步骤显示当前裁剪区域 (clip) 和矩阵 (matrix)
- 带十字准线的缩放查看器，用于选择像素
- 当像素颜色发生变化时暂停回放的断点功能
- GPU 或 CPU 支持的执行
- GPU 操作边界 (op bounds) 可视化
- Android 离屏层 (offscreen layer) 可视化
- 共享资源查看器

<img src="../onlinedebugger.png" style="display: inline-block;" />

## 用户指南

SKP 文件可以包含单帧或多帧。单帧文件的扩展名为 .skp，多帧文件的扩展名为 .mskp。在上面链接的在线调试器中，打开一个[示例 mskp 文件](/docs/dev/tools/calendar.mskp)或使用[此处的说明](https://sites.google.com/a/google.com/skia/android/skp-from-framework)从 Android 设备捕获一个。

### 命令回放和过滤

尝试使用下方的播放按钮 <img src="../playcommands.png" style="display: inline-block;" />（不在圆圈中的那个）回放当前帧中的命令。你应该会看到图像逐个绘制命令地构建起来。

许多命令操作矩阵或裁剪区域，但运行时不会产生任何可见变化。尝试通过在命令回放控件下方的过滤文本框中粘贴 `!drawannotation save restore concat setmatrix cliprect` 来过滤这些命令。按回车应用过滤器，如果已暂停则恢复回放。这将使回放看起来快得多，因为示例文件的第一帧中只有 29 个命令通过此过滤器。

尝试暂停命令回放，并使用 `,`（逗号）和 `.`（句号）逐步前进和后退命令。

> 过滤器不区分大小写，唯一支持的逻辑运算符是 !（非），它应用于整个过滤器，且只在出现在开头时才被识别。

任何命令都可以使用 <img src="../expand.png" style="display: inline-block;" /> 图标展开，以查看随该命令记录的所有参数。

展开命令的详情视图后，可以使用复选框来禁用或启用命令。

使用 <img src="../end.png" style="display: inline-block;" /> 按钮将命令播放头跳到列表末尾。

### 帧回放

<img src="../frameplayback.png" style="display: inline-block;" />

示例文件包含多个帧。使用带圆圈的播放按钮回放帧。当前帧由滑块位置指示，滑块可以手动设置。可以使用 `w`（后退）和 `s`（前进）逐帧切换。`p` 暂停或取消暂停帧回放。

文件中并非所有帧都有相同数量的命令。当命令播放头停留在列表末尾时，调试器将播放每一帧直到其列表末尾。如果命令播放头在中间某处，比如 155，调试器将尝试播放每一帧到其第 155 个命令。

### 资源选项卡

<img src="../resources.png" style="display: inline-block;" />

文件中命令引用的所有资源都显示在此处。截至 2019 年 12 月，这仅显示图像。

可以选择并查看任何资源。如果看不到图像，你可能会发现切换亮/暗设置很有帮助。

图像名称的格式为 `7 @24205864 (99, 99)`，其中 `7` 是图像在文件中保存时的索引，`@24205864` 是它在 wasm 内存中的地址（用于与命令列表中也显示此地址的 DrawImage\* 命令进行交叉引用），`(99, 99)` 是图像的大小。

资源查看器允许用户确定图像是否未在帧或绘制命令之间有效共享。如果它在资源选项卡中出现多次，则说明在记录 SKP 的进程中存在具有不同生成 ID 的多个副本。

### Android 层

<img src="../layers.png" style="display: inline-block;" />

当在 Android 中记录 MSKP 时，会记录关于离屏硬件层的额外信息。上面链接的示例 Google 日历 mskp 包含此信息。你将在第 3 帧找到两个层。

有两种与记录的 Android 层使用相关的事件类型。

1. 绘制事件 - 离屏表面被绘制的时间点。它们可能是完整的，意味着裁剪区域等于表面大小，或者是部分的，意味着裁剪区域更小。
2. 使用事件 - 离屏表面作为 SkImage 在主表面中使用的时间点。

当查看发生层绘制事件的帧时，层显示为界面右下角的方框。每个层方框有两个按钮：`Show Use` 将循环显示该层在当前帧中的使用事件（如果有），`Inspector` 将打开绘制事件，就好像它是一个单帧 SKP。你可以回放它的命令、启用或禁用它们、检查 GPU 操作边界或任何你能用普通 SKP 做的事情。通过点击层方框上的 `Exit` 按钮退出检查器。

### 十字准线和断点

<img src="../crosshair.png" style="display: inline-block;" />

点击主视图中的任意点将切换一个红色十字准线用于选择像素。选中像素的颜色以多种格式显示在右侧面板上。选中像素的居中缩放视图显示在其下方。可以通过点击缩放视图中的相邻像素或使用 `H`（左）`L`（右）`J`（下）`K`（上）精确移动位置。

当选择"Break on change"时，命令回放将在任何改变选中像素颜色的命令处暂停。这可用于查找在查看器中绘制你看到的内容的命令。

### GPU 操作边界和其他设置

<img src="../settings.png" style="display: inline-block;" />

上面过滤后的每个命令右侧都有一个带颜色的数字 <img src="../gpuop.png" style="display: inline-block;" />。这是 GPU 操作 ID。当多个命令共享一个 GPU 操作 ID 时，表示它们在发送到 GPU 时被批量处理。在 WASM 调试器中，这通过 WebGL 进行。

界面右上方有一个"Display GPU Op Bounds"切换开关。打开它将显示一个彩色矩形，表示当前选中命令的 GPU 操作的边界。

GPU - 控制 Skia 使用哪个后端绘制到屏幕上。在线 wasm 调试器中的 GPU 意味着 WebGL。CPU 意味着 Skia 绘制到内存中的表面，然后在不使用 GPU 的情况下复制到 HTML 画布中。

亮/暗 - 此切换更改主视图和缩放视图后面的棋盘格外观，以帮助查看具有透明度的内容。

显示过度绘制可视化 (Display Overdraw Viz) - 此可视化显示一个红色叠加层，其颜色与像素上发生的过度绘制量成正比，越深越多。过度绘制意味着像素被绘制了多次。

- 截至 2019 年 12 月，此功能可能无法正常工作。

### 图像适配和下载按钮

<img src="../settings.png" style="display: inline-block;" />

这些按钮调整主视图的大小。从左到右分别是：

原始大小 - 画布在录制时的自然大小。适合页面 - 缩小到整个画布适合中心面板。适合页面宽度 - 使画布水平适合但允许垂直滚动。适合页面高度 - 使画布垂直适合但允许水平滚动。

旁边还有一个第 5 个不相关的下载按钮，用于将当前画布保存为 PNG 文件。

## 本地构建和运行

首先按照说明[下载和构建 Skia](/docs/user/build)。接下来，你需要 Skia 的基础设施仓库，可以通过以下方式下载：

<!--?prettify lang=sh?-->
    git clone https://skia.googlesource.com/buildbot

更多说明请参阅 buildbot/debugger-app/README.md。

## 捕获 SKP

### Chromium

请参阅 https://www.chromium.org/developers/how-tos/trace-event-profiling-tool/saving-skp-s-from-chromium/

### Android

请参阅[如何从 Android 框架捕获 SKP 文件](/docs/dev/tools/android-capture)。
