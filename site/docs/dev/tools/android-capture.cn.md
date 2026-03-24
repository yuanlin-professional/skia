---
title: '如何从 Android 框架捕获 SKP 文件'
linkTitle: '如何从 Android 框架捕获 SKP 文件'
---

## 前提条件

要设置新刷入的设备进行捕获，请运行以下命令以使录制进程能够写入文件：

```
adb root
adb remount
```

MSKP 文件可以捕获 Skia 画布 (canvas) 的任何使用，Android 中有两种用途已被检测以进行捕获。HWUI 会显示单个应用程序的内容，而 RenderEngine 会显示来自多个应用程序的交错缓冲区以及横竖屏切换等过渡效果。

## 从 HWUI 捕获

设置 capture_skp 属性以启用（但不启动）HWUI 捕获功能。这只会影响设置 capture_skp 属性后启动的应用程序，因此你可能需要重新启动你希望捕获的应用程序。

```
adb root
adb shell setprop debug.hwui.capture_skp_enabled true
```

然后，每次你想捕获文件时：

首先，打开你要捕获的应用程序。然后，从你的 Android 源码树根目录使用以下脚本触发捕获。（参见 https://source.android.com/docs/setup/download。）

```
frameworks/base/libs/hwui/tests/scripts/skp-capture.sh -p PACKAGE_NAME -n FRAMES
```

`PACKAGE_NAME` 是你要捕获的组件或应用程序的名称，例如：**com.google.android.apps.nexuslauncher**。如果未指定，脚本将尝试推断当前打开的应用程序的包名。

`FRAMES` 是要捕获的帧数。这是可选的，默认为 1。

## 从 RenderEngine 捕获

在捕获之前，从 Android 根目录运行以下命令一次。

```
frameworks/native/libs/renderengine/skia/debug/record.sh rootandsetup
```

录制 RenderEngine 在 2 秒内处理的所有帧。

```
frameworks/native/libs/renderengine/skia/debug/record.sh 2000
```

当设备完成序列化后，输出文件会被复制到你当前的工作目录。这可能需要长达 30 秒。

捕获脚本有小概率会过早检测到文件完成，并从设备复制一个截断的文件。在调试器中它将无法读取。如果你怀疑发生了这种情况，你很可能仍然可以从设备的 `/data/user/re_skiacapture_*.mskp` 路径检索到完整文件。

## 读取文件

在 [Skia 调试器][Skia Debugger] 中打开生成的文件。对于单帧 SKP，你也可以使用 [Skia Viewer][Skia Viewer] 查看，或使用 `dm` 进行栅格化（参见 [Skia 构建说明][Skia Build Instructions] 了解如何构建 `dm`）：

```
out/Release/dm --src skp --skps FILENAME.skp -w /tmp --config 8888 gpu pdf --verbose
ls -l /tmp/*/skp/FILENAME.skp.*
```

[Skia Build Instructions]: /docs/user/build
[Skia Debugger]: https://debugger.skia.org
[Skia Viewer]: /docs/user/sample/viewer/
