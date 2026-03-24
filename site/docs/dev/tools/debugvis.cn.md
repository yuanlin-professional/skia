
---
title: "调试可视化 (Debug Visualization)"
linkTitle: "调试可视化 (Debug Visualization)"

---


Skia 使用自定义容器类型，如 `SkString` 和 `SkTArray<>`，在调试器中查看这些类型可能不太方便。

如果你经常调试使用 Skia 类型的代码，可以考虑安装调试可视化工具。Skia 为以下平台提供调试器可视化支持：

-   [Visual Studio 和 VS Code](https://skia.googlesource.com/skia/+/refs/heads/main/platform_tools/debugging/vs/Skia.natvis)
-   [LLDB 和 Xcode](https://skia.googlesource.com/skia/+/refs/heads/main/platform_tools/debugging/lldb/skia.py)
