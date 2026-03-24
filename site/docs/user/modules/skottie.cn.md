---
title: 'Skottie - Lottie 动画播放器'
linkTitle: 'Skottie - Lottie 动画播放器'

weight: 10
---

Skia 现在提供了一个高性能、安全的原生播放器，用于播放从 After Effects 的
Bodymovin 插件派生的 JSON 动画。它可以在你使用 Skia 的任何平台上使用，
包括 Android 和 iOS。

该播放器旨在在当今广泛用于动画的 Lottie 播放器基础上进行改进，
为我们的客户提升性能、功能集和平台一致性。我们是 Bodymovin 格式的忠实粉丝，
并在可能的情况下将改进贡献回 Bodymovin/Lottie。

<br>

## JSON 动画示例

以下是一些使用 Skia 动画播放器渲染的测试样本：

<script src="https://skottie.skia.org/static/canvaskit.js"></script>
<script src="https://skottie.skia.org/static/inline-bundle.js"></script>
<style>
    skottie-inline-sk {
        display: inline-block;
    }
</style>

<a href="https://skottie.skia.org/e6741dda67629da1f80c254dad3df865">
  <skottie-inline-sk src="https://skottie.skia.org/_/j/e6741dda67629da1f80c254dad3df865" width=200 height=200></skottie-inline-sk>
</a>
<a href="https://skottie.skia.org/ffea72cf6be48fa061671c124ed7789c">
  <skottie-inline-sk src="https://skottie.skia.org/_/j/ffea72cf6be48fa061671c124ed7789c" width=200 height=200></skottie-inline-sk>
</a>
<a href="https://skottie.skia.org/00e850cdbed7304985eaefe98a4e8a9c">
  <skottie-inline-sk src="https://skottie.skia.org/_/j/00e850cdbed7304985eaefe98a4e8a9c" width=200 height=200></skottie-inline-sk>
</a>
<a href="https://skottie.skia.org/e1aca009d5ebec9bd122b87b018bb673">
  <skottie-inline-sk src="https://skottie.skia.org/_/j/e1aca009d5ebec9bd122b87b018bb673" width=200 height=200></skottie-inline-sk>
</a>
<a href="https://skottie.skia.org/821fd79dd7437b97ba891e7a00970a06">
  <skottie-inline-sk src="https://skottie.skia.org/_/j/821fd79dd7437b97ba891e7a00970a06" width=200 height=200></skottie-inline-sk>
</a>
<a href="https://skottie.skia.org/ad63f250084685c96edd9b52ae2f436b">
  <skottie-inline-sk src="https://skottie.skia.org/_/j/ad63f250084685c96edd9b52ae2f436b" width=200 height=200></skottie-inline-sk>
</a>
<a href="https://skottie.skia.org/40f78ddc751c16348a08e1d61d3e78b1">
  <skottie-inline-sk src="https://skottie.skia.org/_/j/40f78ddc751c16348a08e1d61d3e78b1" width=200 height=200></skottie-inline-sk>
</a>
<a href="https://skottie.skia.org/fc42db7c75741437b5cb0e90b3febc65">
  <skottie-inline-sk src="https://skottie.skia.org/_/j/fc42db7c75741437b5cb0e90b3febc65" width=200 height=200></skottie-inline-sk>
</a>
<a href="https://skottie.skia.org/c16eee287f2cea44102b6670c66e60ab">
  <skottie-inline-sk src="https://skottie.skia.org/_/j/c16eee287f2cea44102b6670c66e60ab" width=200 height=200></skottie-inline-sk>
</a>

\*示例动画由 lottiefiles.com 社区提供

<br>

## 测试服务器

在 https://skottie.skia.org 我们的播放器中测试你的 Lottie 文件

<br>

## 代码

Skia 动画代码入口点可以在这里找到：
[Googlesource](https://skia.googlesource.com/skia/+/main/modules/skottie/include/Skottie.h)
和
[GitHub](https://github.com/google/skia/blob/main/modules/skottie/include/Skottie.h)。
该代码是 Skia 库的一部分，但也可以作为单独的包提供。

<br>

## 嵌入示例

使用 Skottie 原生播放器的示例 C 代码可以在
[这里](https://github.com/google/skia/blob/main/modules/skottie/src/SkottieTool.cpp)找到。

Android 应用代码可供参考，在
[这里](https://github.com/google/skia/tree/main/platform_tools/android/apps/skottie)。

将 Skottie 嵌入到我们 Viewer 应用的示例代码在
[这里](https://github.com/google/skia/blob/main/tools/viewer/SkottieSlide.cpp)。

Viewer 或 Skottie Android 应用可以按照
[这些](/docs/user/sample/viewer)说明构建。
