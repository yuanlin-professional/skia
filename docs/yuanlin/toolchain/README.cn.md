# toolchain/ - Bazel Hermetic 工具链配置

## 概述

`toolchain/` 目录定义了 Skia 在 Bazel 构建系统中使用的 hermetic（密封/可重复）工具链。Hermetic 工具链意味着构建所需的编译器、链接器、系统库等工具都是从已知来源下载的固定版本，而非使用主机系统上安装的工具。这确保了在不同机器上的构建结果完全一致，是可重复构建（reproducible builds）的基础。

该目录为以下目标平台提供了工具链配置：Linux x64（使用 Clang）、macOS（Intel 和 Apple Silicon）、Windows x64、iOS（真机和模拟器）、以及 Android NDK（ARM64）。每个平台有三个主要组成部分：工具链下载规则（`download_*_toolchain.bzl`）、工具链配置文件（`*_toolchain_config.bzl`）和平台特定的包装脚本（`*_trampolines/`）。

`BUILD.bazel` 文件是工具链注册的入口点，定义了 Bazel `toolchain()` 规则，将每个工具链与其适用的执行平台和目标平台关联起来。通过 Bazel 的平台约束机制（`constraint_setting` 和 `constraint_value`），可以精确控制在何种条件下使用哪个工具链。

Skia 使用自定义约束 `//bazel/platform:use_hermetic_toolchain` 来区分 hermetic 工具链和系统默认工具链。只有当目标平台包含此约束时，才会选择 Skia 的 hermetic 工具链。

## 目录结构

```
toolchain/
├── BUILD.bazel                              # 工具链注册（toolchain 规则）
├── download_toolchains.bzl                  # 工具链下载入口
├── download_linux_amd64_toolchain.bzl       # Linux x64 工具链下载
├── download_mac_toolchain.bzl               # macOS 工具链下载
├── download_windows_amd64_toolchain.bzl     # Windows x64 工具链下载
├── download_ios_toolchain.bzl               # iOS 工具链下载
├── download_ndk_linux_amd64_toolchain.bzl   # Android NDK 工具链下载
├── linux_amd64_toolchain_config.bzl         # Linux x64 工具链配置
├── mac_toolchain_config.bzl                 # macOS 工具链配置
├── windows_toolchain_config.bzl             # Windows x64 工具链配置
├── ios_toolchain_config.bzl                 # iOS 工具链配置
├── ndk_linux_arm64_toolchain_config.bzl     # Android NDK ARM64 配置
├── ndk.BUILD                                # NDK 外部仓库构建文件
├── clang_layering_check.bzl                 # Clang 层级检查功能
├── utils.bzl                                # 工具链工具函数
├── android_trampolines/                     # Android 编译器包装脚本
├── ios_trampolines/                         # iOS 编译器包装脚本
├── linux_trampolines/                       # Linux 编译器包装脚本
├── mac_trampolines/                         # macOS 编译器包装脚本
└── windows_trampolines/                     # Windows 编译器包装脚本
```

## 关键文件

### BUILD.bazel - 工具链注册

定义了以下 Bazel `toolchain()` 规则：

| 工具链名称 | 执行平台 | 目标平台 |
|-----------|---------|---------|
| `clang_linux_x64_toolchain` | Linux x86_64 | Linux x86_64 (hermetic) |
| `clang_mac_x64_toolchain` | macOS x86_64 | macOS x86_64 (hermetic) |
| `clang_mac_arm64_toolchain` | macOS ARM64 | macOS ARM64 (hermetic) |
| `clang_host_mac_x64_target_mac_arm64_toolchain` | macOS x86_64 | macOS ARM64 (交叉编译) |
| `clang_ios_arm64_toolchain` | macOS | iOS ARM64 (hermetic) |
| `clang_ios_x64_toolchain` | macOS | iOS x86_64 模拟器 |
| `clang_windows_x64_toolchain` | Windows x86_64 | Windows x86_64 (hermetic) |
| `ndk_linux_arm64_toolchain` | Linux x86_64 | Android ARM64 |

每个工具链通过 `target_compatible_with` 包含 `//bazel/platform:use_hermetic_toolchain` 约束，确保只有显式请求 hermetic 工具链时才会使用。

### download_toolchains.bzl - 工具链下载入口

```python
name_toolchain = {
    "clang_linux_amd64": download_linux_amd64_toolchain,
    "clang_mac": download_mac_toolchain,
    "clang_windows_amd64": download_windows_amd64_toolchain,
    "ndk_linux_amd64": download_ndk_linux_amd64_toolchain,
    "clang_ios": download_ios_toolchain,
}
```

提供 `download_toolchains_for_skia()` 函数，在 `MODULE.bazel` 中调用以注册所有工具链的下载规则。

### linux_amd64_toolchain_config.bzl - Linux 工具链配置（示例）

定义了 Clang 编译器的完整配置，包括：
- 编译器路径和系统头文件搜索路径
- 链接器配置（使用 LLD）
- 默认编译标志（`-std=c++20`、`-fPIC` 等）
- 功能开关（如 supports_pic、layering_check 等）
- sysroot 配置

### clang_layering_check.bzl - 层级检查

实现了 Clang 模块映射（module maps）的层级检查功能，能够检测：
1. `cc_library` 使用了另一个 `cc_library` 的私有头文件
2. `cc_library` 通过传递依赖而非直接依赖使用了公共头文件

### utils.bzl - GCS 镜像工具

提供 `gcs_mirror_url()` 函数，为外部资源的下载 URL 生成 GCS 镜像地址。Skia 在 `cdn.skia.org` 维护了所有外部依赖的镜像备份，确保构建不会因上游资源不可用而失败。

### *_trampolines/ - 编译器包装脚本

每个平台目录包含 shell 脚本或 batch 脚本，用作编译器的包装器（trampoline）。这些脚本在实际编译器调用前设置必要的环境变量，如 `PATH`、SDK 路径等，确保 hermetic 工具链能正确找到所有依赖的工具。

## 构建配置说明

### 使用 hermetic 工具链构建

```bash
# 使用 hermetic Linux 工具链构建
bazelisk build //:skia_core --config=for_linux_x64

# 使用 hermetic macOS ARM64 工具链构建
bazelisk build //:skia_core --config=for_mac_arm64
```

`--config` 标志在 `bazel/buildrc` 中定义，会设置 `--platforms` 指向包含 `use_hermetic_toolchain` 约束的平台定义。

### 交叉编译

```bash
# 在 Intel Mac 上为 Apple Silicon 构建
bazelisk build //:skia_core --config=for_mac_arm64

# 在 Linux 上为 Android ARM64 构建
bazelisk build //:skia_core --config=for_android_arm64
```

### 工具链版本管理

工具链版本在各 `download_*_toolchain.bzl` 文件中固定。更新工具链时需要：
1. 更新下载 URL 和 SHA256 校验值
2. 测试所有平台的构建
3. 提交更改

## 依赖关系

- `MODULE.bazel` (项目根目录) - 注册工具链仓库
- `bazel/platform/BUILD.bazel` - 定义 `use_hermetic_toolchain` 约束
- `bazel/buildrc` - 引用工具链平台进行构建配置
- 各 `download_*_toolchain.bzl` 从 CIPD 或 GCS 下载预构建的编译器

## 相关文档与参考

- [Bazel 工具链文档](https://bazel.build/extending/toolchains)
- [Bazel 平台文档](https://bazel.build/extending/platforms)
- [Hermetic 构建概念](https://bazel.build/basics/hermeticity)
- `bazel/buildrc` - CI 构建配置
- `bazel/platform/BUILD.bazel` - 平台约束定义
- `bazel/cipd_install.bzl` - CIPD 包下载规则
