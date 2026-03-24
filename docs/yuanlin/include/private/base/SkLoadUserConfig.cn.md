# SkLoadUserConfig 用户配置加载模块

> 源文件: `include/private/base/SkLoadUserConfig.h`

## 概述
SkLoadUserConfig 是 Skia 的用户配置加载机制,负责在编译早期包含用户自定义的配置文件 (SkUserConfig.h),设置合理的默认值,并验证配置的一致性。该文件是 Skia 可配置性的核心入口。

## 架构位置
位于 Skia 基础设施层 (private/base),是整个库的配置基础。该文件通常是最早被包含的 Skia 头文件之一,影响整个编译过程。

## 核心功能

### 防止重复包含
```cpp
#ifndef SK_USER_CONFIG_WAS_LOADED
// ... 配置加载逻辑 ...
#define SK_USER_CONFIG_WAS_LOADED
#endif
```
使用包含保护宏确保配置仅加载一次。

### 包含依赖的基础头文件

#### SkFeatures.h
```cpp
#include "include/private/base/SkFeatures.h"
```
- 设置平台检测宏 (SK_BUILD_FOR_*)
- 检测 CPU 架构和字节序
- 定义 SK_RESTRICT 等编译器特性

#### SkLogPriority.h
```cpp
#include "include/private/base/SkLogPriority.h"  // IWYU pragma: keep
```
- 提供日志优先级枚举
- 允许用户在配置中引用 SkLogPriority
- `IWYU pragma: keep` 确保不被优化掉

### 辅助宏定义

#### 空宏占位符
```cpp
#define SK_NOTHING_ARG1(arg1)
#define SK_NOTHING_ARG2(arg1, arg2)
#define SK_NOTHING_ARG3(arg1, arg2, arg3)
```
- **用途**: 允许嵌入式系统禁用某些带参数的宏
- **使用方式**: 用户可定义宏为这些占位符
- **示例**:
  ```cpp
  // 在受限环境中禁用 SkDebugf
  #define SkDebugf SK_NOTHING_ARG1
  ```

### 加载用户配置文件

#### 方式一: SK_USER_CONFIG_HEADER (传统方式)
```cpp
#if defined(SK_USER_CONFIG_HEADER)
    #include SK_USER_CONFIG_HEADER
```
- 通过宏定义指定配置文件路径
- 示例: `-DSK_USER_CONFIG_HEADER="my_config.h"`
- **限制**: 不适用于 Bazel 构建系统和某些 C++ 编译器

#### 方式二: SK_USE_BAZEL_CONFIG_HEADER (Bazel 方式)
```cpp
#elif defined(SK_USE_BAZEL_CONFIG_HEADER)
    #include "SkUserConfig.h"  // NO_G3_REWRITE
```
- Bazel 特定的配置加载
- 假设配置文件在 Bazel Workspace 根目录
- `NO_G3_REWRITE` 注释防止 Google 内部工具重写

#### 方式三: 默认路径
```cpp
#else
    #include "include/config/SkUserConfig.h"
#endif
```
- 默认从 `include/config/SkUserConfig.h` 加载
- 标准 Skia 项目布局

### 配置一致性检查

#### Debug/Release 配置检查
```cpp
#if !defined(SK_DEBUG) && !defined(SK_RELEASE)
    #ifdef NDEBUG
        #define SK_RELEASE
    #else
        #define SK_DEBUG
    #endif
#endif

#if defined(SK_DEBUG) && defined(SK_RELEASE)
#  error "cannot define both SK_DEBUG and SK_RELEASE"
#elif !defined(SK_DEBUG) && !defined(SK_RELEASE)
#  error "must define either SK_DEBUG or SK_RELEASE"
#endif
```

**检查逻辑**:
1. 如果用户未定义 SK_DEBUG/SK_RELEASE,根据 NDEBUG 推断
2. 确保两者有且仅有一个被定义
3. 同时定义或都未定义会导致编译错误

#### 字节序配置检查
```cpp
#if defined(SK_CPU_LENDIAN) && defined(SK_CPU_BENDIAN)
#  error "cannot define both SK_CPU_LENDIAN and SK_CPU_BENDIAN"
#elif !defined(SK_CPU_LENDIAN) && !defined(SK_CPU_BENDIAN)
#  error "must define either SK_CPU_LENDIAN or SK_CPU_BENDIAN"
#endif
```

确保字节序配置唯一且明确。

#### 大端系统警告
```cpp
#if defined(SK_CPU_BENDIAN) && !defined(I_ACKNOWLEDGE_SKIA_DOES_NOT_SUPPORT_BIG_ENDIAN)
    #error "The Skia team is not endian-savvy enough to support big-endian CPUs."
    #error "If you still want to use Skia,"
    #error "please define I_ACKNOWLEDGE_SKIA_DOES_NOT_SUPPORT_BIG_ENDIAN."
#endif
```

- Skia 明确声明不支持大端系统
- 用户必须显式确认才能在大端系统上编译
- 用于警示潜在的兼容性问题

## 内部实现细节

### 包含顺序的重要性
```
SkLoadUserConfig.h
  ↓
SkFeatures.h (平台检测)
  ↓
SkLogPriority.h (日志级别)
  ↓
SkUserConfig.h (用户自定义)
  ↓
一致性检查
```

顺序确保用户配置可以引用平台宏和日志枚举。

### IWYU Pragma
```cpp
// IWYU pragma: begin_exports
...
// IWYU pragma: end_exports
```
- Include What You Use 工具的指令
- 标记导出的头文件,优化包含关系

### 默认值推断
```cpp
#ifdef NDEBUG
    #define SK_RELEASE
#else
    #define SK_DEBUG
#endif
```
如果用户未配置,从标准 C++ 宏 `NDEBUG` 推断。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `SkFeatures.h` | 平台和特性检测 |
| `SkLogPriority.h` | 日志优先级定义 |
| `SkUserConfig.h` | 用户自定义配置 (可选) |

### 被依赖的模块
几乎所有 Skia 头文件间接依赖此文件的配置结果。

## 设计模式与设计决策

### 多种配置加载方式
支持三种方式适应不同构建系统:
- 传统 Makefile: 宏定义指定
- Bazel: 特定路径
- CMake/默认: 标准路径

### 防御性编程
通过编译错误强制配置一致性,避免运行时问题。

### 惰性求值
配置文件仅在首次需要时加载,避免多次包含。

### 明确的不支持声明
对于大端系统,通过编译错误明确告知不支持,而非静默失败。

## 可配置项示例

### 在 SkUserConfig.h 中可配置的内容
```cpp
// SkUserConfig.h 示例

// 1. 构建模式 (可选,会自动推断)
#define SK_DEBUG

// 2. 日志级别
#define SKIA_LOWEST_ACTIVE_LOG_PRIORITY SkLogPriority::kWarning

// 3. 禁用某些功能
#define SK_SUPPORT_GPU 0

// 4. 自定义内存分配器
#define sk_malloc_throw my_malloc
#define sk_free my_free

// 5. 图像格式支持
#define SK_CODEC_DECODES_PNG
#define SK_CODEC_DECODES_JPEG

// 6. 数学优化
#define SK_USE_LEGACY_COMPUTE_INVERSE_MATRIX

// 7. 调试辅助
#define SK_DEBUG_TRACE_FUNC SkDebugf("Entering %s\n", __func__)
```

## 性能考量

### 编译期配置
所有配置在编译期决定,无运行时检查开销。

### 条件编译
根据配置,不需要的代码完全不会被编译,减小二进制大小。

### 包含保护
防止重复包含和重复处理。

## 平台相关说明

### Bazel 构建
- 需要在 Workspace 根目录放置 SkUserConfig.h
- 定义 `SK_USE_BAZEL_CONFIG_HEADER`

### CMake 构建
- 可通过 `-DSK_USER_CONFIG_HEADER` 指定自定义配置
- 或使用默认路径 `include/config/SkUserConfig.h`

### Google 内部构建
- `NO_G3_REWRITE` 注释防止内部工具修改包含路径

## 使用示例

### 创建自定义配置
```cpp
// my_skia_config.h
#ifndef MY_SKIA_CONFIG_H
#define MY_SKIA_CONFIG_H

// 强制 Release 模式
#define SK_RELEASE

// 仅记录错误
#define SKIA_LOWEST_ACTIVE_LOG_PRIORITY SkLogPriority::kError

// 禁用 GPU 支持
#define SK_SUPPORT_GPU 0

#endif
```

编译时指定:
```bash
g++ -DSK_USER_CONFIG_HEADER="my_skia_config.h" ...
```

### 使用默认配置
如果不需要自定义:
```cpp
// include/config/SkUserConfig.h
// 可以为空,或包含项目标准配置
```

### 嵌入式系统配置
```cpp
// embedded_config.h

// 禁用日志
#define SkDebugf SK_NOTHING_ARG1
#define SKIA_LOG_D SK_NOTHING_ARG3

// 最小内存配置
#define SK_SUPPORT_PDF 0
#define SK_SUPPORT_GPU 0
#define SK_CODEC_DECODES_PNG 0  // 仅支持必需格式
```

### 调试构建配置
```cpp
// debug_config.h
#define SK_DEBUG

// 启用所有日志
#define SKIA_LOWEST_ACTIVE_LOG_PRIORITY SkLogPriority::kDebug

// 启用额外的断言
#define SK_DEBUG_CANVAS_STATE_CHECK
```

## 故障排查

### 错误: cannot define both SK_DEBUG and SK_RELEASE
**原因**: 配置文件中同时定义了两者
**解决**: 移除其中一个定义

### 错误: must define either SK_DEBUG or SK_RELEASE
**原因**: 没有定义构建模式,且 NDEBUG 也未定义
**解决**: 定义 SK_DEBUG 或 SK_RELEASE,或设置 NDEBUG

### 错误: must define either SK_CPU_LENDIAN or SK_CPU_BENDIAN
**原因**: SkFeatures.h 未能自动检测字节序
**解决**: 在配置文件中显式定义字节序

### 大端系统编译错误
**原因**: Skia 不支持大端系统
**解决**: 定义 `I_ACKNOWLEDGE_SKIA_DOES_NOT_SUPPORT_BIG_ENDIAN`(风险自负)

## 相关文件
| 文件 | 关系 |
|------|------|
| `SkFeatures.h` | 首先包含,提供平台检测 |
| `SkLogPriority.h` | 提供日志级别枚举 |
| `SkUserConfig.h` | 用户自定义配置文件 |
| 所有 Skia 头文件 | 间接依赖配置结果 |

## 历史与演进
- 2022 年统一配置加载机制
- 添加 Bazel 构建支持
- 引入空宏占位符支持嵌入式系统
- 改进配置一致性检查
- 明确大端系统不支持声明

## 总结
SkLoadUserConfig 是 Skia 配置系统的核心,通过多种方式加载用户配置,设置合理默认值,并严格验证配置一致性。它确保了 Skia 的可配置性和跨平台兼容性,同时通过编译期检查防止配置错误。
