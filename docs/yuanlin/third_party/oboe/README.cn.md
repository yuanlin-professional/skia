# third_party/oboe - Android 音频库

## 概述

`third_party/oboe/` 包含 Google Oboe 音频库的 Skia 构建配置。Oboe 提供了
统一的高性能 Android 音频 API，在 Skia 的某些演示和测试工具中可能用于音频
同步功能。

## 目录结构

```
oboe/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 Oboe 的编译选项

## 依赖关系

- Oboe 源码（通过 DEPS 拉取）
- Android NDK

## 相关文档与参考

- Oboe: https://github.com/google/oboe
- Android 音频: https://developer.android.com/ndk/guides/audio
