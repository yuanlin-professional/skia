# android_ndk_linux - Linux 版 Android NDK

## 概述

Linux 平台的 Android NDK 资源。用于在 Linux 构建机上编译 Skia 的 Android 原生代码。这是最常用的 Android 编译环境。

## 目录结构

```
android_ndk_linux/
├── create.py   # 自动化创建脚本
└── VERSION     # 当前版本号
```

## 关键文件

- `create.py` - 从 Google 官方下载 Linux 版 Android NDK 并打包
- `VERSION` - 记录当前使用的 NDK 版本

## 依赖关系

- 被 Android 编译任务在 Linux 机器上使用
- 由 `gen_tasks_logic` 在任务生成时引用

## 相关文档与参考

- [Android NDK 官方文档](https://developer.android.com/ndk)
