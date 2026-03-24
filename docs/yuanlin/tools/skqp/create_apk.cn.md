# create_apk.py - SkQP Android APK 构建脚本

> 源文件: `tools/skqp/create_apk.py`

## 概述

`create_apk.py` 是一个 Python 构建脚本，用于自动化构建 SkQP（Skia Quality Program）的 Android APK 包。SkQP 是 Skia 的合规性测试套件，用于验证 Android 设备上 GPU 渲染行为是否符合预期。

该脚本自动化了从 GN 配置生成、Ninja 编译、原生库打包到 Gradle APK 构建的完整流程。它支持同时为多种 CPU 架构（arm, arm64, x86, x64）编译原生库，并将它们打包到一个通用（universal）APK 中。

## 架构位置

```
Skia 工具链
├── tools/
│   ├── skqp/
│   │   ├── create_apk.py          <-- 本文件：APK 构建入口脚本
│   │   ├── download_model.py      <-- 模型下载脚本
│   │   └── src/
│   │       ├── skqp.h             <-- SkQP 核心头文件
│   │       ├── jni_skqp.cpp       <-- JNI 桥接层
│   │       └── skqp_main.cpp      <-- 命令行版本入口
├── gn/
│   └── skqp_gn_args.py            <-- GN 参数配置（被本脚本导入）
└── platform_tools/android/apps/skqp/  <-- Android 应用目录
```

## 主要类与结构体

### `SkQP_Build_Options`
构建选项管理类，负责从环境变量和命令行参数中收集构建配置。

```python
class SkQP_Build_Options(object):
    android_ndk     # Android NDK 路径（来自 ANDROID_NDK_HOME）
    android_home    # Android SDK 路径（来自 ANDROID_HOME）
    architectures   # 目标架构列表，默认 ['arm', 'arm64', 'x86', 'x64']
    build_dir       # 构建中间目录（来自 SKQP_BUILD_DIR 或默认 out/skqp）
    final_output_dir # APK 输出目录（来自 SKQP_OUTPUT_DIR）
    debug           # 是否使用 debug 模式编译（来自 SKQP_DEBUG）
```

关键方法：
- `gn_args(arch)`: 返回指定架构的 GN 编译参数字典
- `write(o)`: 将当前配置输出到流

### `RemoveFiles`
上下文管理器，在退出时自动删除指定的文件和目录，用于清理构建临时文件。

### `ChDir`
上下文管理器，在进入时切换工作目录，在退出时恢复原目录。

## 公共 API 函数

### `create_apk(opts)`
APK 构建的顶层入口函数，切换到 Skia 根目录后调用 `create_apk_impl`。

### `create_apk_impl(opts)`
APK 构建的核心实现，执行以下流程：
1. 为每个目标架构执行 `gn gen` 和 `ninja` 编译
2. 将编译好的 `.so` 文件复制到 Android 应用的 `libs` 目录
3. 调用 `gradlew` 执行 Android 构建
4. 将生成的 APK 复制到最终输出目录

### `check_ninja()`
检查 `ninja` 构建工具是否在系统 PATH 中可用。

### `accept_android_license(android_home)`
自动接受 Android SDK 许可协议，通过向 `sdkmanager` 的 stdin 持续写入 `y` 实现。

### `print_cmd(cmd, o)`
将命令行参数格式化输出，对包含特殊字符的参数使用 `repr()` 进行转义。

## 内部实现细节

### 架构名称映射

```python
skia_to_android_arch_name_map = {
    'arm'  : 'armeabi-v7a',
    'arm64': 'arm64-v8a',
    'x86'  : 'x86',
    'x64'  : 'x86_64'
}
```

Skia 使用简短的架构名称，而 Android 使用不同的命名约定，此映射在打包 JNI 库时使用。

### 构建路径管理

脚本通过符号链接将 Gradle 需要的不受版本控制的目录（`.gradle`、`build`、`libs`）重定向到构建目录下，从而保持源码树的清洁。构建完成后通过 `RemoveFiles` 上下文管理器自动清理这些符号链接。

### 编译重试机制

```python
try:
    check_call(['ninja', '-C', build, lib])
except subprocess.CalledProcessError:
    check_call(['ninja', '-C', build, '-t', 'clean'])
    check_call(['ninja', '-C', build, lib])
```

如果首次 Ninja 编译失败，脚本会通过 `ninja -t clean` 清理所有构建产物后重试一次。这处理了增量构建可能遇到的缓存不一致问题。

### 输出文件命名

生成两个 APK 副本：
- `skqp-universal-debug.apk`：标准命名
- `skqp-{arch1}_{arch2}_...-debug.apk`：带架构标识的命名

## 依赖关系

- **Python 标准库**：`os`, `re`, `subprocess`, `sys`, `shutil`, `time`
- **Skia 内部模块**：`skqp_gn_args`（GN 参数生成）
- **外部工具**：
  - `ninja` 构建系统
  - `bin/gn`（GN 元构建系统，需先运行 `tools/git-sync-deps`）
  - `gradlew`（Gradle 包装器）
  - Android SDK（`ANDROID_HOME`）
  - Android NDK（`ANDROID_NDK_HOME`）

## 设计模式与设计决策

1. **上下文管理器模式**：`RemoveFiles` 和 `ChDir` 使用 Python 的上下文管理器协议（`__enter__`/`__exit__`），确保资源清理即使在异常情况下也能执行。

2. **环境变量驱动配置**：构建选项主要通过环境变量（`ANDROID_NDK_HOME`、`ANDROID_HOME`、`SKQP_BUILD_DIR` 等）配置，符合 CI/CD 环境的使用习惯。

3. **符号链接隔离**：通过符号链接将构建产物重定向到单独的构建目录，既满足了 Gradle 对特定目录结构的要求，又保持了源码树的清洁。

4. **失败提前退出**：`SkQP_Build_Options.__init__` 在初始化阶段就验证所有前提条件（ninja 可用性、环境变量设置、架构参数有效性），收集所有错误信息后一次性报告。

## 性能考量

- **多架构并行**：脚本按顺序编译各架构（非并行），因为每个架构的 Ninja 编译本身已经是多线程的，串行执行避免了资源竞争。
- **编译重试**：通过 `ninja -t clean` 后重试的策略处理可能的增量编译不一致问题，牺牲了一次编译时间换取构建可靠性。
- **APK 复制而非移动**：最终 APK 既被 `move` 到输出目录，又被 `copyfile` 为带架构名的副本，确保两种命名都可用。
- **符号链接优化**：使用符号链接将构建产物指向外部目录，避免在源码树内产生大量临时文件，同时利用外部存储（可能是 tmpfs 或 SSD）的速度优势。
- **GN 参数缓存**：`gn gen` 的参数通过 `skqp_gn_args.GetGNArgs` 统一管理，确保各架构使用一致的编译配置。

## 相关文件

- `tools/skqp/src/skqp.h` - SkQP 核心测试框架头文件
- `tools/skqp/src/jni_skqp.cpp` - JNI 桥接层实现
- `gn/skqp_gn_args.py` - GN 参数生成辅助模块（`GetGNArgs` 函数）
- `platform_tools/android/apps/skqp/` - Android 应用工程目录
- `platform_tools/android/apps/skqp/src/main/java/org/skia/skqp/SkQP.java` - Java 端 SkQP 类
- `platform_tools/android/apps/skqp/src/main/AndroidManifest.xml` - Android 清单文件
- `tools/skqp/download_model` - 模型下载脚本（需在构建前运行）
- `bin/gn` - GN 元构建工具（需通过 `tools/git-sync-deps` 获取）
