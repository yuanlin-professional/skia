# third_party/native_app_glue - Android Native Activity 粘合层

## 概述

`third_party/native_app_glue/` 包含 Android NDK 的 NativeActivity 粘合代码的
Skia 构建配置。该库提供了将 Android NativeActivity 生命周期事件转发给 C/C++
代码的桥接层，使 Skia 的 Android 原生应用能够正确响应系统事件。

## 目录结构

```
native_app_glue/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 native_app_glue 的编译选项

## 依赖关系

- Android NDK（native_app_glue 是 NDK 的一部分）

## 相关文档与参考

- Android NativeActivity: https://developer.android.com/ndk/guides/concepts
- Android 平台工具: `platform_tools/android/`
