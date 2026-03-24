# SkLog 日志模块

> 源文件: `include/private/base/SkLog.h`

## 概述
SkLog 是 Skia 的日志记录系统,提供分级别的日志输出功能,支持编译期日志级别过滤。该模块定义了日志输出的核心接口和宏,允许开发者在不同的日志级别下输出调试信息、警告和错误。

## 架构位置
属于 Skia 基础设施层 (private/base),为整个 Skia 库提供统一的日志记录能力。该模块是跨平台的,由各平台实现具体的日志输出逻辑。

## 核心功能

### 日志优先级系统
通过 `SkLogPriority` 枚举定义五个日志级别:
- `kFatal`: 致命错误,会触发程序终止
- `kError`: 错误级别
- `kWarning`: 警告级别
- `kInfo`: 信息级别
- `kDebug`: 调试级别

### 编译期日志过滤
使用宏 `SKIA_LOWEST_ACTIVE_LOG_PRIORITY` 在编译期决定哪些日志会被包含到最终二进制中。默认行为:
- Debug 构建: 包含所有级别 (kDebug 及以上)
- Release 构建: 仅包含 kInfo 及以上级别

## 公共 API 函数

### `SkLog`
```cpp
void SK_SPI SkLog(SkLogPriority priority, const char format[], ...)
```
- **功能**: 输出格式化日志消息
- **参数**:
  - `priority`: 日志优先级
  - `format`: printf 风格的格式字符串
  - `...`: 可变参数列表
- **特性**: 支持 printf 风格格式化,由平台层实现具体输出

### `SkLogVAList`
```cpp
void SkLogVAList(SkLogPriority priority, const char format[], va_list args)
```
- **功能**: 使用 va_list 输出日志,供内部或高级用户使用
- **参数**:
  - `priority`: 日志优先级
  - `format`: 格式字符串
  - `args`: 可变参数列表

## 日志宏定义

### 便捷日志宏
| 宏名称 | 日志级别 | 用途 | 前缀 |
|--------|----------|------|------|
| `SKIA_LOG_F` | Fatal | 致命错误,触发终止 | "** ERROR **" |
| `SKIA_LOG_E` | Error | 错误信息 | "** ERROR **" |
| `SKIA_LOG_W` | Warning | 警告信息 | "WARNING - " |
| `SKIA_LOG_I` | Info | 一般信息 | "[skia]" |
| `SKIA_LOG_D` | Debug | 调试信息 | "[skia]" |

### 基础宏 `SKIA_LOG`
```cpp
#define SKIA_LOG(priority, fmt, ...)
```
所有便捷宏的基础实现,特性:
- 使用 `constexpr if` 进行编译期级别检查
- 仅编译满足级别要求的日志代码
- Fatal 级别调用 `SK_ABORT` 终止程序
- 其他级别调用 `SkLog` 输出

## 内部实现细节

### 编译期过滤机制
通过 `constexpr if` 语句在编译期决定是否生成日志代码:
```cpp
if constexpr (priority <= SKIA_LOWEST_ACTIVE_LOG_PRIORITY) {
    // 仅当日志级别满足要求时才编译此分支
}
```
这意味着被过滤的日志不会产生任何运行时开销。

### Graphite 兼容性支持
为保持向后兼容,支持旧的 Graphite 日志优先级定义:
- 检查 `SKGPU_GRAPHITE_LOWEST_ACTIVE_LOG_PRIORITY` 宏
- 通过 `MapGraphitePriority` 函数映射到新的优先级系统
- 这是一个过渡性方案,未来会被移除

### 平台实现要求
`SkLog` 和 `SkLogVAList` 声明为平台需要实现的函数:
- 必须在各平台的移植层实现
- 实现可以输出到不同目标 (控制台、文件、系统日志等)
- 可通过用户配置覆盖默认实现

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `SkAPI.h` | 定义 SK_SPI 导出宏 |
| `SkAttributes.h` | 提供 SK_PRINTF_LIKE 属性宏 |
| `SkLogPriority.h` | 定义日志优先级枚举 |
| `SkLoadUserConfig.h` | 加载用户配置 |
| `<cstdarg>` | va_list 支持 |

### 被依赖的模块
几乎所有 Skia 模块都会使用日志功能进行诊断和调试输出。

## 设计模式与设计决策

### 编译期日志过滤
**决策**: 使用 `constexpr if` 而非传统的预处理器条件编译
**优势**:
- 保持代码语法完整性,IDE 可正确解析所有分支
- 编译器可对未使用的分支进行死代码消除
- 保留类型检查,避免宏参数未使用时的警告

### 统一日志前缀
所有日志都添加 "[skia]" 前缀,便于在多库混合的环境中识别 Skia 的输出。

### printf 风格接口
采用 printf 风格而非流式接口 (如 C++ iostream):
- 更紧凑的语法
- 性能更优 (无临时对象构造)
- 与 C 代码兼容性好
- 通过 `SK_PRINTF_LIKE` 属性获得编译器格式检查

## 性能考量

### 零开销抽象
被过滤的日志完全不会被编译到二进制中,实现真正的零运行时开销。

### 内联优化
日志宏使用 `do-while(0)` 包裹,确保:
- 可以在任何需要单个语句的地方使用
- 不会因宏展开产生意外的作用域问题

### 格式字符串检查
使用 `SK_PRINTF_LIKE(2, 3)` 属性让编译器验证格式字符串与参数的匹配,在编译期捕获错误。

## 使用示例

### 基本用法
```cpp
// 信息日志
SKIA_LOG_I("渲染完成,耗时 %d ms", elapsed_time);

// 警告日志
SKIA_LOG_W("纹理大小 %dx%d 超过推荐值", width, height);

// 错误日志
SKIA_LOG_E("无法加载着色器: %s", shader_path);

// 调试日志 (仅 Debug 构建生效)
SKIA_LOG_D("顶点数量: %zu", vertex_count);
```

### 配置日志级别
在 `SkUserConfig.h` 中定义:
```cpp
// 仅输出警告及以上级别
#define SKIA_LOWEST_ACTIVE_LOG_PRIORITY SkLogPriority::kWarning
```

### 条件编译示例
```cpp
// Debug 构建会包含此代码
SKIA_LOG_D("详细的调试信息: %p", ptr);

// Release 构建会完全省略,无运行时开销
```

## 平台相关说明

### 平台实现差异
不同平台的 `SkLog` 实现可能输出到:
- **Android**: Android logcat 系统
- **iOS**: NSLog 或 os_log
- **Windows**: OutputDebugString 或控制台
- **Linux/Unix**: stderr 或 syslog
- **Web (Emscripten)**: console.log

### 可覆盖性
用户可以在包含此头文件前定义自己的 `SkLog`,实现自定义日志行为:
```cpp
#define SkLog MyCustomLogFunction
#include "include/private/base/SkLog.h"
```

## 相关文件
| 文件 | 关系 |
|------|------|
| `SkLogPriority.h` | 定义日志优先级枚举 |
| `SkDebug.h` | 提供 SK_ABORT 宏用于致命错误 |
| `SkLoadUserConfig.h` | 加载用户自定义配置 |
| `SkUserConfig.h` | 用户可配置日志行为的位置 |

## 历史与演进

### 版权信息
文件创建于 2026 年,归 Google LLC 所有。

### Graphite 迁移
代码中包含 TODO 注释 (b/469441457),说明正在从 `SKGPU_GRAPHITE_LOWEST_ACTIVE_LOG_PRIORITY` 迁移到统一的 `SKIA_LOWEST_ACTIVE_LOG_PRIORITY`,这是日志系统统一化的一部分工作。
