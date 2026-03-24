# android_ndk_windows - Windows 版 Android NDK

## 概述

Windows 平台的 Android NDK 资源。用于在 Windows 构建机上编译 Skia 的 Android 原生代码。

## 目录结构

```
android_ndk_windows/
├── create.py   # 自动化创建脚本
└── VERSION     # 当前版本号
```

## 关键文件

- `create.py` - 下载 Windows 版 Android NDK 并打包
- `VERSION` - 记录当前使用的 NDK 版本

## 依赖关系

- 被 Android 编译任务在 Windows 机器上使用

## 相关文档与参考

- [Android NDK 官方文档](https://developer.android.com/ndk)
