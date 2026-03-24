
---
title: "SkQP"
linkTitle: "SkQP"

---


SkQP 的开发 APK 保存在 Google 存储中。每个文件以缩写的 Git 哈希命名，指向 Skia 仓库中用于构建它的提交。

这些是通用 APK，包含 armeabi-v7a、arm64-v8a、x86 和 x86\_64 架构的原生库。最新的排在最前面。

列表可在此处找到：
[https://storage.googleapis.com/skia-skqp/apklist](https://storage.googleapis.com/skia-skqp/apklist)

如果你正在查看 Android CTS 失败，请使用 `origin/skqp/release` 分支上最新的提交。

运行测试：

    adb install -r skqp-universal-{APK_SHA_HERE}.apk
    adb logcat -c
    adb shell am instrument -w org.skia.skqp

使用以下命令监控输出：

    adb logcat TestRunner org.skia.skqp skia DEBUG "*:S"

记下设备上测试的输出路径。它看起来类似于：

    01-23 15:22:12.688 27158 27173 I org.skia.skqp:
    output written to "/storage/emulated/0/Android/data/org.skia.skqp/files/skqp_report_2019-02-28T102058"

获取并查看报告：

    OUTPUT_LOCATION="/storage/emulated/0/Android/data/org.skia.skqp/files/skqp_report_2019-02-28T102058"
    adb pull "$OUTPUT_LOCATION" /tmp/

（你的 `$OUTPUT_LOCATION` 值会与我的不同。）

打开文件 `/tmp/output/skqp_report_2019-02-28T102058/report.html`。

**将该目录压缩为 zip 文件以附加到 bug 报告中：**

    cd /tmp
    zip -r skqp_report_2019-02-28T102058.zip skqp_report_2019-02-28T102058
    ls -l skqp_report_2019-02-28T102058.zip

* * *

有关构建你自己的 APK 的更多信息，请参阅
https://skia.googlesource.com/skia/+/main/tools/skqp/README.md
