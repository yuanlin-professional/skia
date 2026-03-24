# assets - 版本化构建资源

## 概述

`assets/` 目录包含 Skia CI 机器人使用的各种工具、SDK 和测试数据资源的版本化管理。每个资源以子目录形式存在，通过 `VERSION` 文件追踪版本号，并存储在 Google Cloud Storage 中。

资源管理使用 `sk asset` 命令行工具，支持添加、上传、下载和更新操作。

## 资源分类

### 编译器与工具链
- `clang_linux`, `clang_mac_arm`, `clang_mac_intel`, `clang_win`, `clang_ubuntu_noble` - Clang 编译器
- `cast_toolchain` - Chromecast 工具链
- `binutils_linux_x64` - GNU Binutils

### Android 开发
- `android_ndk_darwin`, `android_ndk_linux`, `android_ndk_windows` - Android NDK
- `android_sdk_linux` - Android SDK

### 构建工具
- `bazel`, `bazelisk`, `bazelisk_*` - Bazel 构建系统
- `cmake_linux`, `cmake_mac`, `cmake_win` - CMake
- `win_ninja` - Windows Ninja
- `go`, `go_win` - Go 语言
- `ccache_linux`, `ccache_mac` - 编译缓存

### 测试数据
- `skp` - SKP 测试文件
- `skimage` - 测试图像
- `svg` - SVG 测试文件
- `mskp` - 多页 SKP 文件
- `skparagraph` - 段落测试数据
- `text_blob_traces` - 文本 Blob 追踪数据
- `lottie-samples` - Lottie 动画样本

### 系统交叉编译
- `arm64_sysroot`, `armhf_sysroot` - ARM 系统根
- `chromebook_arm_gles`, `chromebook_arm64_gles`, `chromebook_x86_64_gles` - Chromebook 支持

### GPU/图形驱动
- `linux_vulkan_sdk` - Vulkan SDK
- `mesa_intel_driver_linux`, `mesa_intel_driver_linux_22` - Mesa Intel 驱动
- `dwritecore` - DirectWrite 核心库

### 其他工具
- `gsutil`, `gcloud_linux` - Google Cloud 工具
- `node` - Node.js
- `protoc` - Protocol Buffers 编译器
- `jq`, `jq_mac_arm64`, `yq`, `yq_mac_arm64` - JSON/YAML 处理工具
- `kubectl`, `kubeval`, `kubeval_mac_amd64` - Kubernetes 工具
- `bloaty` - 二进制体积分析工具
- `mockery` - Mock 生成工具
- `patch_linux_amd64` - Patch 工具
- `cockroachdb` - CockroachDB

### iOS 开发
- `ios-dev-image-11.4` ~ `ios-dev-image-14.4` - iOS 开发者磁盘映像
- `xcode-11.4.1` - Xcode 版本

## 资源管理操作

### 添加新资源
```bash
sk asset add <资源名>
```

### 上传资源
```bash
sk asset upload --in <本地路径> <资源名>
# 或使用自动化创建脚本
sk asset upload <资源名>
```

### 更新后重新生成任务
```bash
make -C infra/bots train
```

## 前置要求

所有 `sk asset` 操作需要 google.com 账户并完成认证：
```bash
gcloud auth application-default login
```

## 依赖关系

- Google Cloud Storage - 资源存储后端
- `sk` CLI 工具 - 资源管理命令
- `gen_tasks.go` - 资源版本变更后需重新生成任务

## 相关文档与参考

- `scripts/` 子目录 - 资源管理的通用脚本
- 父目录 `infra/bots/README.md` 中关于资源的说明
