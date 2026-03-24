
---
title: "Skia 查看器"
linkTitle: "Skia 查看器"

---

Skia 查看器 (Viewer) 展示了一系列幻灯片，展示 Skia 的特定功能，包括 Skia GM 和允许交互的编程示例。此外，Viewer 用于调试和理解 Skia 系统的不同部分：

* 观察渲染性能 - 将 Viewer 置于统计模式可显示平均帧时间。
* 尝试不同的渲染方法 - 可以在三种渲染方法之间循环切换：光栅化 (raster)、OpenGL 和 Vulkan（在支持的平台上）。你可以将其与统计模式结合使用，查看不同渲染方法对绘图性能的影响。
* 显示和操作你自己的图片。

某些幻灯片需要存储在程序外部的资源。这些资源存储在 `<skia-path>/resources` 目录中。

Linux、Macintosh 和 Windows
----------------------------

Viewer 可以使用常规的 GN 构建流程来构建，例如

    bin/gn gen out/Release --args='is_debug=false'
    ninja -C out/Release viewer

要在桌面 Viewer 中加载资源，使用 `--resourcePath` 选项：

    <skia-path>/out/Release/viewer --resourcePath <skia-path>/resources

类似地，`--skps <skp-file-path>` 将加载该目录中的任何 `.skp` 文件
以在 Viewer 中显示。

其他有用的命令行选项：使用 `--match <pattern>` 将只加载匹配该名称的 SKP 或幻灯片；
使用 `--slide <name>` 将从该幻灯片启动；你可以使用 `--backend` 以特定渲染方法启动，
即 `--backend sw`、`--backend gl`、`--backend vk` 或 `--backend mtl`。

桌面 Viewer 使用键盘和鼠标控制：左（<-）和右（->）
箭头在幻灯片之间移动；上（^）和下（v）箭头进行
缩放；点击和拖动将进行平移。其他显示选项和幻灯片
选择器可以在工具 UI 中找到，按空格键切换。
h 键切换帮助菜单（按一次按功能分组命令，第二次按字母顺序排列，第三次隐藏）。

按键    | 操作
-------|-------------
<- ->    | 在幻灯片之间移动
^ v    | 放大 / 缩小
h      | 查看所有命令
d      | 在光栅化、OpenGL 和 Vulkan 之间切换渲染方法
s      | 显示渲染时间和图表
空格  | 切换工具 UI 的显示

Android
-------

要将 Viewer 构建为 Android 应用，首先按照
[Android 构建说明](/docs/user/build#android)设置
Android NDK 和 ninja 输出目录。此外，你需要安装
[Android SDK 命令行工具](https://developer.android.com/studio/#command-line-tools-only)
并设置 `ANDROID_HOME` 环境变量。

    mkdir ~/android-sdk
    cd ~/android-sdk
    unzip ~/Downloads/commandlinetools-*.zip
    yes | cmdline-tools/bin/sdkmanager --licenses --sdk_root=.
    export ANDROID_HOME=~/android-sdk  # Or wherever you installed the Android SDK.

如果你没有使用 Android SDK 中包含的 NDK（在此示例中为 ~/android-sdk/ndk-bundle），
你需要设置环境变量 `ANDROID_NDK_HOME`，例如

    export ANDROID_NDK_HOME=/tmp/ndk

Viewer APK 必须由 gradle 构建，可以在命令行使用以下脚本调用：

    platform_tools/android/bin/android_build_app -C <out_dir> viewer

其中 `<out_dir>` 是你创建的 ninja 输出目录（例如 `out/arm64`）。

如果你遇到似乎与 Skia 或 Viewer 无关的错误，可能是安装了不兼容版本的
各种构建工具：

* 确保安装了最新版本的 Java
* 确保 [gradle-wrapper.properties](https://crsrc.org/c/third_party/skia/platform_tools/android/apps/gradle/wrapper/gradle-wrapper.properties) 中 "distributionUrl" 指定的 Gradle 版本与你安装的 Java 版本兼容，参见 https://docs.gradle.org/current/userguide/compatibility.html
* 确保 [build.gradle](https://crsrc.org/c/third_party/skia/platform_tools/android/apps/build.gradle) 中 "com.android.tools.build:gradle:[version]" 指定的 Android Gradle 工具版本与 gradle 版本兼容，参见 https://developer.android.com/build/releases/gradle-plugin

脚本完成后，APK 可以在 `<out_dir>/viewer.apk` 找到。使用 `adb install` 安装它。

可以传递额外的命令行标志，例如

    adb shell am start -a android.intent.action.MAIN -n org.skia.viewer/org.skia.viewer.ViewerActivity --es args '"--androidndkfonts"'

如果你按照上述说明安装了 Android SDK 命令行工具，adb 应该安装在
[android-sdk]/platform-tools/adb。你可以这样过滤 Viewer 的控制台输出：

    adb logcat --pid=`adb shell pidof org.skia.viewer`

### 如何使用该应用

大多数应用功能（触摸手势和箭头按钮除外）都在**左侧抽屉**中。
点击左上角的汉堡按钮打开该抽屉。

#### 切换幻灯片

在右上角，有两个箭头：下一张幻灯片、上一张幻灯片。

在左侧抽屉中，你可以直接从列表（下拉框）中选择幻灯片。在该下拉框上方，
有一个文本过滤器适用于幻灯片列表。有数百张幻灯片，所以如果你
知道幻灯片名称，使用该过滤器可以快速定位并显示它。

#### 缩放 / 平移

我们支持在幻灯片上的触摸手势，所以你可以拖动和捏合来缩放。

#### 更改后端

在左侧抽屉中，你可以从 OpenGL、Vulkan 和 Raster 列表中选择后端。

#### 软键 / 统计

在左侧抽屉中，有一个软键列表。它们对应于桌面 Viewer 应用的键盘命令。
例如，你可以切换颜色模式或统计窗口。这些可以
像幻灯片一样进行过滤。

对于动画幻灯片，我们还显示 FPS（实际上是每帧秒数）--- 以毫秒为单位的帧
刷新率。

#### 加载资源 / SKP

资源和 SKP 会自动复制到包的 assets 中，并通过 Android
Asset Manager API 加载。

#### 在 RenderDoc 上运行

要在 RenderDoc 上运行 Android Viewer，请参考以下文档：
http://renderdoc.org/docs/how/how_android_capture.html

具体来说，你需要将 Executable Path 设置为
`org.skia.viewer/org.skia.viewer.ViewerActivity`，并可以使用
`--es args '"[args]"'` 设置命令行参数，例如 `--es args '"--backend vk"'`。

RenderDoc 本身没有捕获或显示控制台输出的机制，但你可以
随时独立于 RenderDoc 运行 `adb logcat` 来查看控制台输出。

iOS
---

iOS 上的 Viewer 使用常规 GN 流程构建，例如

    bin/gn gen out/Release --args='target_os="ios" is_debug=false'
    ninja -C out/Release viewer

与其他 iOS 应用一样，可以使用
[ios-deploy](https://github.com/ios-control/ios-deploy)
等工具部署，或者在 Xcode 中构建并通过 IDE 启动。有关
管理签名和部署的配置文件的更多信息，请参阅
[iOS 构建说明](https://skia.org/docs/user/build#ios)。

Viewer 将
自动捆绑顶级 Skia 目录中的 `resources` 目录，
如果在 Skia 目录中还放置了 `skps` 目录也会一并捆绑。

在 iOS 上，Viewer 提供基本的触摸功能：你可以查看幻灯片，
在它们之间滑动，捏合缩放以缩放，通过拖动平移。目前
尚不支持显示选项或从幻灯片列表中选择。

