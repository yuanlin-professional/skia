# platform_tools/ - 平台特定工具

## 概述

`platform_tools/` 包含 Skia 在各平台上构建、调试和部署所需的工具和脚本。
主要覆盖 Android、iOS 和调试工具等平台相关功能。这些工具简化了跨平台开发
和测试的工作流程。

## 目录结构

```
platform_tools/
├── android/                 # Android 平台工具
│   ├── apps/                # Android 应用项目
│   │   ├── skottie/         # Skottie 动画播放器 App
│   │   ├── skqp/            # Skia 质量保证测试 App
│   │   ├── viewer/          # Skia Viewer App
│   │   ├── build.gradle     # Gradle 构建配置
│   │   └── settings.gradle  # Gradle 设置
│   ├── bin/                 # Android 命令行工具脚本
│   │   ├── adb_pull_if_needed  # ADB 文件拉取
│   │   ├── adb_push_if_needed  # ADB 文件推送
│   │   ├── android_build_app   # Android 应用构建
│   │   ├── android_gdb_app     # Android GDB 调试
│   │   ├── android_perf        # Android 性能测试
│   │   └── android_run_skia    # 运行 Skia 测试
│   ├── gclient.config       # gclient 同步配置
│   ├── skp_gen/             # SKP 文件生成工具
│   ├── tradefed/            # Trade Federation 测试框架
│   └── vulkan/              # Android Vulkan 头文件
├── debugging/               # 调试辅助工具
│   ├── lldb/                # LLDB 调试器扩展
│   └── vs/                  # Visual Studio 调试工具
├── ios/                     # iOS 平台工具
│   ├── app/                 # iOS 应用模板
│   └── bin/                 # iOS 命令行工具
└── libraries/               # 平台特定库
    └── include/             # 平台头文件
```

## 关键文件

- **android/bin/android_run_skia**: 在 Android 设备上运行 Skia 测试的脚本
- **android/bin/android_gdb_app**: 用于在 Android 设备上调试 Skia 应用
- **android/apps/build.gradle**: 所有 Android 应用的 Gradle 构建入口
- **debugging/lldb/**: LLDB 调试器的 Skia 数据类型可视化扩展

## 依赖关系

- Android SDK 和 NDK
- ADB（Android Debug Bridge）
- Gradle 构建系统
- iOS SDK（Xcode）
- LLDB / Visual Studio 调试器

## 相关文档与参考

- Android Viewer 应用: `platform_tools/android/apps/viewer/`
- SkQP 质量保证: `platform_tools/android/apps/skqp/`
- Skia 构建文档: https://skia.org/docs/dev/
