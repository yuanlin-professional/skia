# include/config - Skia 构建配置头文件

## 概述

`include/config` 目录包含 Skia 的用户可自定义构建配置文件。该目录的核心是 `SkUserConfig.h`，这是 Skia 提供给嵌入者的配置入口点，允许通过定义预处理器宏来调整 Skia 的行为、性能特征和功能开关。此文件被 `include/private/base/SkLoadUserConfig.h` 在构建早期阶段包含，确保配置在整个 Skia 代码库中生效。

Skia 的配置系统采用分层设计。首先，`include/private/base/SkFeatures.h` 自动检测编译平台和 CPU 特征。然后，`SkUserConfig.h` 允许用户覆盖或补充这些自动检测的结果。最后，`SkLoadUserConfig.h` 验证配置的一致性（例如不能同时定义 `SK_DEBUG` 和 `SK_RELEASE`）。这种设计使得 Skia 可以在不修改核心代码的情况下适配各种嵌入环境。

除了 `SkUserConfig.h`，该目录还包含 Bazel 构建系统所需的配置文件。`MODULE.bazel` 和 `WORKSPACE.bazel` 定义了该目录作为独立 Bazel 工作区的配置，这使得 Bazel 构建可以通过工作区嵌套机制正确地定位 `SkUserConfig.h`。`copts.bzl` 和 `linkopts.bzl` 提供了 Bazel 构建中使用的编译器和链接器选项。

该目录中的所有宏定义默认处于注释状态，这意味着包含默认的 `SkUserConfig.h` 不会改变 Skia 的任何行为。嵌入者可以根据需要取消注释或通过命令行 `-D` 参数来启用特定配置。

## 目录结构

```
include/config/
├── SkUserConfig.h    # 用户自定义构建配置（核心配置文件）
├── BUILD.bazel       # Bazel 构建目标定义
├── copts.bzl         # Bazel 编译器选项
├── linkopts.bzl      # Bazel 链接器选项
├── MODULE.bazel      # Bazel 模块定义
├── WORKSPACE.bazel   # Bazel 工作区定义
└── OWNERS            # 代码审查所有者
```

## 关键类与函数

### SkUserConfig.h - 可配置宏定义

#### 调试与发布模式
- **`SK_DEBUG`**: 启用调试模式，开启断言、参数检查和详细的调试输出。
- **`SK_RELEASE`**: 启用发布模式，禁用调试代码以获得最佳性能。
- 如果两者都未定义，Skia 根据 `NDEBUG` 宏自动选择。

#### 调试输出与错误处理
- **`SkDebugf(...)`**: 可重定义调试消息输出函数，默认使用 `printf` 格式。
- **`SK_ABORT(message, ...)`**: 可重定义不可恢复错误的处理函数，默认调用 `SkDebugf` 后终止。

#### 缓存配置
- **`SK_DEFAULT_FONT_CACHE_LIMIT`**: 字体命中缓存的内存上限（字节），默认使用内置值。
- **`SK_DEFAULT_FONT_CACHE_COUNT_LIMIT`**: 字体缓存条目数上限，示例值为 2048。
- **`SK_DEFAULT_IMAGE_CACHE_LIMIT`**: 图像缓存大小上限（字节），可通过 `SkGraphics.h` 运行时 API 调整。

#### 文本渲染
- **`SK_MAX_SIZE_FOR_LCDTEXT`**: LCD 子像素文本渲染的最大字号阈值，超过此值的文本不使用 LCD 渲染。增大此值会增加字体缓存开销。默认约 48。

#### 颜色格式
- **`SK_R32_SHIFT`**: 设置为 16 可将 `kN32_SkColorType` 的通道顺序从 RGBA 改为 BGRA，用于适配 X Window System 等使用 BGRA 格式的环境。

#### 画布配置
- **`SK_CANVAS_SAVE_RESTORE_PREALLOC_COUNT`**: 控制 SkCanvas 中用于保存/恢复操作（`save()`/`restore()`）的预分配栈空间大小。

#### 直方图与监控
- **`SK_HISTOGRAM_BOOLEAN(name, sample)`**: 布尔值直方图记录宏。
- **`SK_HISTOGRAM_ENUMERATION(name, sampleEnum, enumSize)`**: 枚举值直方图。
- **`SK_HISTOGRAM_EXACT_LINEAR(name, sample, valueMax)`**: 精确线性直方图。
- **`SK_HISTOGRAM_MEMORY_KB(name, sample)`**: 内存使用直方图（KB）。
- **`SK_HISTOGRAM_CUSTOM_COUNTS(...)`**: 自定义计数直方图。
- 默认这些宏为空操作，嵌入者可提供自己的实现以集成其监控系统。

#### 管线调试
- **`SK_PIPELINE_LIFETIME_LOGGING`**: 启用 Graphite 管线生命周期的详细日志。

### Bazel 构建配置
- **`copts.bzl`**: 定义 Bazel 构建中的编译器标志，如优化级别、警告设置和平台特定选项。
- **`linkopts.bzl`**: 定义链接器标志，如库搜索路径和系统库链接。
- **`MODULE.bazel`/`WORKSPACE.bazel`**: 将 `include/config` 声明为独立的 Bazel 工作区，使得 `SkUserConfig.h` 可以通过 `#include "SkUserConfig.h"` 被直接引用（而非使用完整的仓库路径）。

### 配置加载流程详解
Skia 的配置加载遵循严格的顺序，确保所有宏在使用前已正确定义：

```
1. SkFeatures.h      - 自动检测 OS、CPU 架构、字节序
2. SkLogPriority.h   - 定义日志优先级枚举
3. SkUserConfig.h    - 用户自定义覆盖（本文件）
4. SkLoadUserConfig.h - 验证配置一致性（SK_DEBUG/SK_RELEASE 互斥等）
5. SkAPI.h           - 定义 SK_API/SK_SPI 导出宏
6. SkTypes.h         - 公共类型入口（暴露给所有用户）
```

### 自定义配置的三种方式
1. **直接编辑 `SkUserConfig.h`**: 取消注释相应宏定义。简单直接但不利于 Skia 版本升级。
2. **命令行定义**: 通过编译器参数 `-DSK_DEBUG` 等方式定义宏，无需修改源文件。
3. **自定义头文件**: 定义 `SK_USER_CONFIG_HEADER` 宏指向自定义头文件路径，Skia 会包含该文件替代默认的 `SkUserConfig.h`。此方式最灵活但不兼容 Bazel 构建。

## 依赖关系

- **上游依赖**: 无（这是 Skia 配置层次结构的最顶层）
- **被包含于**: `include/private/base/SkLoadUserConfig.h` -> `include/private/base/SkAPI.h` -> `include/core/SkTypes.h`（整个 Skia 代码库的入口）
- **加载链**: `SkFeatures.h`（平台检测） -> `SkLoadUserConfig.h`（加载用户配置） -> `SkUserConfig.h`（本文件）
- **下游影响**: 整个 Skia 代码库的行为都受此配置影响

## 相关文档与参考

- [Skia 构建指南](https://skia.org/docs/user/build/) - 如何自定义 Skia 构建
- [Skia Bazel 构建](https://skia.org/docs/dev/build/bazel/) - Bazel 构建系统使用说明
- [SkGraphics API](https://api.skia.org/classSkGraphics.html) - 运行时配置 API（缓存大小等）
- `include/private/base/SkLoadUserConfig.h` - 配置加载和验证逻辑
- `include/private/base/SkFeatures.h` - 自动平台特性检测
- `include/private/base/SkDebug.h` - 调试输出实现
- `include/core/SkTypes.h` - 包含配置的公共类型入口
