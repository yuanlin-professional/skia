# gen_trampolines.go - Android NDK 工具链跳板脚本生成器

> 源文件: `toolchain/android_trampolines/gen_trampolines/gen_trampolines.go`

## 概述

本文件是一个 Go 语言辅助工具程序，用于生成 Android NDK 工具链的跳板（trampoline）脚本。这些跳板脚本是 Bazel 构建系统与 Android NDK 工具链集成的必要组件。由于 Bazel 的 `cc_common.create_cc_toolchain_config_info` 要求工具路径指向调用目录下的文件，而 NDK 工具实际位于 `external/ndk_linux_amd64` 目录中，因此需要跳板脚本作为间接层，将命令行参数透传给实际的 NDK 二进制文件。

## 架构位置

该文件位于 `toolchain/android_trampolines/gen_trampolines/` 目录下，属于 Skia 项目的构建工具链层。它不参与 Skia 的编译或运行时逻辑，而是在构建系统配置变更时（如升级 NDK 版本）手动运行。生成的跳板脚本存放在 `toolchain/android_trampolines/` 目录中，被 Bazel 的 C++ 工具链配置引用。

## 主要类与结构体

### 全局变量

- **`bazelNdkPath`**: Bazel 工作空间中 NDK 的路径常量：`"external/+download_ndk_linux_amd64_toolchain+ndk_linux_amd64"`
- **`tools`**: 需要生成跳板脚本的 NDK 工具列表，包含：
  - ARM 32 位工具链（`arm-linux-androideabi-*`）: ar、dwp、ld、nm、objcopy、objdump、strip
  - ARM 64 位工具链（`aarch64-linux-android-*`）: 同上
  - LLVM clang 编译器

### 模板

- **`trampolineScriptTemplate`**: Bash 跳板脚本模板，包含路径解析和工具调用逻辑

## 公共 API 函数

- **`main()`**: 程序入口，解析命令行参数并生成跳板脚本
  - `--ndk-dir`: 本地 NDK 副本的路径（用于验证工具路径有效性）
  - `--out-dir`: 跳板脚本输出目录

## 内部实现细节

### 跳板脚本生成流程

1. 解析 `--ndk-dir` 和 `--out-dir` 命令行参数
2. 遍历 `tools` 列表中的每个工具路径
3. 使用 `os.Stat` 验证工具在本地 NDK 中确实存在
4. 使用 `trampolineScriptTemplate` 生成 Bash 脚本
5. 将脚本写入 `out-dir`，文件名为工具的基本名称加 `.sh` 后缀

### 跳板脚本工作原理

生成的 Bash 脚本执行以下步骤：
1. 通过 `BASH_SOURCE[0]` 确定自身位置
2. 向上导航两级目录找到 `external/` 目录
3. 使用相对路径定位 NDK 工具链目录
4. 将所有命令行参数（`$@`）透传给实际的 NDK 工具

### 路径间接寻址

使用 `cd` 切换到 `external/` 的父目录而非使用绝对路径调用 clang。这是因为用绝对路径调用 clang 会干扰 `#include` 检测机制（clang 期望系统路径也使用绝对路径）。

### 支持的工具链

- **ARM 32 位** (`arm-linux-androideabi-4.9`): 面向 32 位 Android ARM 设备
- **ARM 64 位** (`aarch64-linux-android-4.9`): 面向 64 位 Android ARM 设备
- **LLVM clang**: 统一的 C/C++ 编译器前端

## 依赖关系

- **Go 标准库**: `errors`、`flag`、`fmt`、`os`、`path/filepath`
- **Android NDK**: 用于验证工具路径的本地 NDK 副本
- **Bazel 构建系统**: 生成的跳板脚本被 Bazel 的 CC 工具链配置引用

## 设计模式与设计决策

- **代码生成**: 使用 Go 程序生成 Bash 脚本，而非手动维护，确保工具列表的一致性
- **验证优先**: 在生成脚本前验证 NDK 中工具的存在性，提前发现路径错误
- **模板化**: 使用字符串模板生成统一格式的跳板脚本，易于理解和维护
- **手动触发**: 该工具仅在工具链配置变更时手动运行，不作为构建过程的一部分
- **相对路径策略**: 跳板脚本使用相对路径避免绝对路径带来的 `#include` 检测问题
- **文件权限**: 生成的脚本权限为 0750（所有者和组可读写执行）

## 性能考量

- 代码生成是一次性操作，性能不是关键考量
- 跳板脚本在每次编译器调用时引入极小的 shell 启动开销
- `realpath` 和 `dirname` 的路径解析在首次调用时完成，后续编译无额外开销
- 参数透传（`$@`）不涉及参数解析，开销可忽略

## 相关文件

- `toolchain/android_trampolines/` - 生成的跳板脚本存放目录
- `toolchain/download_toolchains.bzl` - NDK 下载配置
- `toolchain/BUILD.bazel` - 工具链构建配置
- `WORKSPACE` 或 `MODULE.bazel` - Bazel 工作空间配置
