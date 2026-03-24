# platform_tools/android - Android 平台工具

## 概述

`android/` 包含在 Android 平台上构建、测试和调试 Skia 所需的完整工具链。
包括 Android 应用项目（Viewer、Skottie、SkQP）、命令行脚本、Vulkan 头文件
等。

## 目录结构

```
android/
├── apps/                    # Android 应用项目
│   ├── build.gradle         # 顶层 Gradle 构建文件
│   ├── settings.gradle      # Gradle 项目设置
│   ├── gradle.properties    # Gradle 属性
│   ├── gradlew              # Gradle Wrapper 脚本
│   ├── skottie/             # Skottie 动画播放器
│   ├── skqp/                # 质量保证测试套件
│   └── viewer/              # Skia Viewer 应用
├── bin/                     # 命令行工具脚本
│   ├── adb_pull_if_needed   # 按需从设备拉取文件
│   ├── adb_push_if_needed   # 按需推送文件到设备
│   ├── android_build_app    # 构建 Android 应用
│   ├── android_build_universal_viewer  # 构建通用 Viewer
│   ├── android_gdb_app      # GDB 调试 App
│   ├── android_gdb_native   # GDB 调试原生代码
│   ├── android_install_app  # 安装 App 到设备
│   ├── android_launch_app   # 启动 App
│   ├── android_perf         # 性能测试
│   ├── android_run_skia     # 运行 Skia 测试
│   ├── linux/               # Linux 特定工具
│   ├── mac/                 # macOS 特定工具
│   └── utils/               # 通用工具函数
├── gclient.config           # gclient 依赖同步配置
├── skp_gen/                 # SKP 文件生成工具
├── tradefed/                # Android Trade Federation 测试
├── vulkan/                  # Vulkan Android 头文件
│   └── Skia_Vulkan_Android.h
└── whitespace.txt           # 空白测试文件

```

## 依赖关系

- Android SDK / NDK
- ADB 工具
- Gradle 7+
- Java JDK

## 相关文档与参考

- Android NDK 文档: https://developer.android.com/ndk
- Skia Android 构建: https://skia.org/docs/dev/build/android/
