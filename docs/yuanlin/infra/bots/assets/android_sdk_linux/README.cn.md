# android_sdk_linux - Linux 版 Android SDK

## 概述

Linux 平台的 Android SDK 资源。包含 Android 应用构建和测试所需的平台工具、构建工具和系统镜像。

## 目录结构

```
android_sdk_linux/
├── __init__.py              # Python 包标识
├── create.py                # 自动化创建脚本
├── create_and_upload.py     # 创建并上传的便捷脚本
└── VERSION                  # 当前版本号
```

## 关键文件

- `create.py` - 下载并配置 Android SDK 组件
- `create_and_upload.py` - 一键创建和上传新版本

## 依赖关系

- 被 Android 构建和测试任务使用
- 与 `android_ndk_linux` 配合使用

## 相关文档与参考

- [Android SDK 官方文档](https://developer.android.com/studio/command-line)
