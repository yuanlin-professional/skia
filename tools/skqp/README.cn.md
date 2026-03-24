SkQP
====

SkQP（Skia 质量计划，Skia Quality Program）是 Android CTS（兼容性测试套件，Compatibility Test Suite）的一个组件，使用 Skia 现有的单元测试和渲染测试来测试 Android 设备的 GPU 以及 OpenGLES 和 Vulkan 驱动程序。

预构建 APK 请参见 https://skia.org/dev/testing/skqp。

如何构建和运行 SkQP 测试
-----------------------------------

1.  获取依赖项：

    -   你需要 Java JDK 8、`git` 和 `python`。

    -   安装 Chromium 的 [depot\_tools](http://commondatastorage.googleapis.com/chrome-infra-docs/flat/depot_tools/docs/html/depot_tools_tutorial.html)。将其添加到你的 `PATH` 中。

            git clone 'https://chromium.googlesource.com/chromium/tools/depot_tools.git'
            export PATH="${PWD}/depot_tools:${PATH}"

    -   安装 [Android NDK](https://developer.android.com/ndk/downloads/)。

            ( cd ~; unzip ~/Downloads/android-ndk-*.zip )
            ANDROID_NDK_HOME=$(ls -d ~/android-ndk-*)   # 或你安装 Android NDK 的任何位置。

    -   安装 [Android SDK](https://developer.android.com/studio/#command-tools)。
        设置 `ANDROID_HOME` 环境变量。

            mkdir ~/android-sdk
            ( cd ~/android-sdk; unzip ~/Downloads/sdk-tools-*.zip )
            yes | ~/android-sdk/tools/bin/sdkmanager --licenses
            export ANDROID_HOME=~/android-sdk  # 或你安装 Android SDK 的任何位置。

        将 `adb` 添加到你的 `PATH` 中。

            export PATH="${PATH}:${ANDROID_HOME}/platform-tools"

2.  获取正确版本的 Skia：

        git clone https://skia.googlesource.com/skia.git
        cd skia
        git checkout origin/skqp/dev  # 或你需要的任何发布标签

3.  构建 APK：

        tools/git-sync-deps
        tools/skqp/make_universal_apk

4.  构建、安装和运行。

        adb install -r out/skqp/skqp-universal-debug.apk
        adb logcat -c
        adb shell am instrument -w org.skia.skqp

5.  通过以下方式监控输出：

        adb logcat TestRunner org.skia.skqp skia "*:S"

    注意设备上测试的输出路径。它将类似于：

        01-23 15:22:12.688 27158 27173 I org.skia.skqp:
        output written to "/storage/emulated/0/Android/data/org.skia.skqp/files/output"

6.  检索并查看报告：

        OUTPUT_LOCATION="/storage/emulated/0/Android/data/org.skia.skqp/files/output"
        adb pull $OUTPUT_LOCATION /tmp/
        bin/sysopen /tmp/output/skqp_report/report.html

运行单个测试
---------------------

要运行单个测试，例如 `gles_aarectmodes`：

    adb shell am instrument -e class 'org.skia.skqp.SkQPRunner#gles_aarectmodes' -w org.skia.skqp

单元测试可以使用 `unitTest_` 前缀运行：

    adb shell am instrument -e class 'org.skia.skqp.SkQPRunner#unitTest_GrSurface -w org.skia.skqp

作为非 APK 可执行文件运行
---------------------------

1.  按照上述步骤 1-3 操作。

2.  构建 SkQP 程序，将文件加载到设备上，然后运行 skqp：

        ninja -C out/skqp/arm skqp
        python tools/skqp/run_skqp_exe out/skqp/arm
