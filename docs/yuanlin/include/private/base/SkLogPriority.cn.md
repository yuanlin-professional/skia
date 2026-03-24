# SkLogPriority 日志优先级定义模块

> 源文件: `include/private/base/SkLogPriority.h`

## 概述
SkLogPriority 定义了 Skia 日志系统的优先级枚举,用于控制日志输出的级别。该文件设计为可被用户配置文件 (SkUserConfig.h) 包含,因此避免引入其他头文件依赖,保持最小化。

## 架构位置
位于 Skia 基础设施层 (private/base),是日志系统 (SkLog.h) 的基础类型定义。该文件可在用户配置阶段被包含,早于大部分 Skia 头文件。

## 枚举定义

### SkLogPriority
```cpp
enum class SkLogPriority : int {
    kFatal = 0,
    kError = 1,
    kWarning = 2,
    kInfo = 3,
    kDebug = 4,
};
```

**日志级别说明**:
| 级别 | 值 | 说明 | 使用场景 |
|------|-----|------|----------|
| `kFatal` | 0 | 致命错误 | 不可恢复的错误,程序将终止 |
| `kError` | 1 | 错误 | 严重问题,但程序可继续运行 |
| `kWarning` | 2 | 警告 | 潜在问题,应该注意 |
| `kInfo` | 3 | 信息 | 一般运行时信息 |
| `kDebug` | 4 | 调试 | 调试信息,仅开发时使用 |

### 设计特点

#### 整数基础类型
```cpp
enum class SkLogPriority : int
```
- 使用 `int` 作为底层类型
- 便于比较和排序
- 级别数值越小优先级越高

#### 强类型枚举 (enum class)
- 类型安全,不会隐式转换为整数
- 需要显式作用域 `SkLogPriority::kError`
- 避免命名冲突

#### 连续的整数值
- 值从 0 到 4 连续
- 便于数组索引和范围检查
- 易于扩展新级别

## 配置使用

### 在 SkUserConfig.h 中配置
该枚举的主要用途是允许用户配置日志级别:

```cpp
// SkUserConfig.h
#define SKIA_LOWEST_ACTIVE_LOG_PRIORITY SkLogPriority::kWarning
```

配置后,仅 `kWarning` 及以上级别 (kFatal, kError, kWarning) 的日志会被编译进代码。

### 级别过滤示例
```cpp
// 仅记录错误和致命错误
#define SKIA_LOWEST_ACTIVE_LOG_PRIORITY SkLogPriority::kError

// 记录所有日志 (包括调试信息)
#define SKIA_LOWEST_ACTIVE_LOG_PRIORITY SkLogPriority::kDebug

// 仅记录致命错误
#define SKIA_LOWEST_ACTIVE_LOG_PRIORITY SkLogPriority::kFatal
```

## 内部实现细节

### 最小依赖设计
文件开头的注释明确说明:
```cpp
/**
 * Note: this file may be included in clients' SkUserConfig.h files, so including any other headers
 * in this file should be avoided.
 */
```

**设计原因**:
- SkUserConfig.h 在编译早期被包含
- 避免循环依赖
- 保持配置文件的轻量级

### 级别排序
优先级从高到低:
```
kFatal (0) → kError (1) → kWarning (2) → kInfo (3) → kDebug (4)
```

比较运算符语义:
```cpp
if (priority <= SkLogPriority::kWarning) {
    // 包括 kFatal, kError, kWarning
}
```

### 与整数的转换
虽然是 `enum class`,但可显式转换:
```cpp
int priorityValue = static_cast<int>(SkLogPriority::kError);  // 1
SkLogPriority priority = static_cast<SkLogPriority>(2);       // kWarning
```

## 依赖关系

### 依赖的模块
无 - 该文件完全独立,不包含任何其他头文件。

### 被依赖的模块
| 模块 | 关系 |
|------|------|
| `SkLog.h` | 使用此枚举作为参数类型 |
| `SkLoadUserConfig.h` | 包含此文件供用户配置 |
| `SkUserConfig.h` | 用户配置文件可引用此枚举 |

## 设计模式与设计决策

### 单一职责
文件仅定义一个枚举,职责明确,便于维护和理解。

### 前向兼容性
预留足够的数值空间,未来可在中间插入新级别:
```cpp
// 假设未来需要在 Info 和 Debug 之间插入 Verbose 级别
kInfo = 3,
kVerbose = 4,  // 新增
kDebug = 5,    // 调整
```

### 与标准日志系统的对应
级别设计参考常见日志系统:
- Android Logcat: VERBOSE, DEBUG, INFO, WARN, ERROR, FATAL
- syslog: DEBUG, INFO, NOTICE, WARNING, ERR, CRIT, ALERT, EMERG

### 编译期级别过滤
通过用户配置,不需要的日志代码根本不会被编译,实现零运行时开销。

## 性能考量

### 零运行时开销
配置后的日志级别过滤在编译期完成:
```cpp
#if constexpr (priority <= SKIA_LOWEST_ACTIVE_LOG_PRIORITY) {
    // 仅当满足条件时编译此分支
}
```

### 整数类型的比较
使用 `int` 作为底层类型,比较操作非常高效。

### 无虚函数
枚举类型无运行时多态开销。

## 使用示例

### 在 SkLog.h 中使用
```cpp
void SkLog(SkLogPriority priority, const char format[], ...);

// 调用
SkLog(SkLogPriority::kError, "Failed to load texture: %s", filename);
```

### 在用户配置中设置
```cpp
// SkUserConfig.h

// 生产环境:仅记录错误和致命错误
#define SKIA_LOWEST_ACTIVE_LOG_PRIORITY SkLogPriority::kError

// 开发环境:记录所有信息
#define SKIA_LOWEST_ACTIVE_LOG_PRIORITY SkLogPriority::kDebug

// 性能测试:禁用所有日志
// (没有比 kFatal 更高的级别,所以实际上只有 kFatal 会输出)
#define SKIA_LOWEST_ACTIVE_LOG_PRIORITY SkLogPriority::kFatal
```

### 条件日志记录
```cpp
#if defined(SK_DEBUG)
    constexpr SkLogPriority kDefaultPriority = SkLogPriority::kDebug;
#else
    constexpr SkLogPriority kDefaultPriority = SkLogPriority::kInfo;
#endif
```

### 日志级别字符串映射
```cpp
const char* LogPriorityToString(SkLogPriority priority) {
    switch (priority) {
        case SkLogPriority::kFatal:   return "FATAL";
        case SkLogPriority::kError:   return "ERROR";
        case SkLogPriority::kWarning: return "WARNING";
        case SkLogPriority::kInfo:    return "INFO";
        case SkLogPriority::kDebug:   return "DEBUG";
        default:                      return "UNKNOWN";
    }
}
```

### 动态级别控制 (不推荐)
虽然可以实现运行时级别控制,但这与编译期过滤的设计目标冲突:
```cpp
// 不推荐:破坏了编译期优化
SkLogPriority g_minLogLevel = SkLogPriority::kInfo;

void Log(SkLogPriority priority, const char* msg) {
    if (priority <= g_minLogLevel) {
        // 输出日志
    }
}
```

推荐的做法是通过编译标志控制:
```bash
# Debug 构建
cmake -DSK_DEBUG=1 ...

# Release 构建 (自动设置更高的日志阈值)
cmake -DCMAKE_BUILD_TYPE=Release ...
```

## 扩展性

### 添加新级别
如果需要添加新的日志级别,应:
1. 在适当位置插入新枚举值
2. 更新所有使用 switch 的代码
3. 更新文档和注释

### 平台特定级别映射
不同平台可映射到自己的日志系统:
```cpp
#if defined(SK_BUILD_FOR_ANDROID)
    android_LogPriority ToAndroidPriority(SkLogPriority priority) {
        switch (priority) {
            case SkLogPriority::kFatal:   return ANDROID_LOG_FATAL;
            case SkLogPriority::kError:   return ANDROID_LOG_ERROR;
            case SkLogPriority::kWarning: return ANDROID_LOG_WARN;
            case SkLogPriority::kInfo:    return ANDROID_LOG_INFO;
            case SkLogPriority::kDebug:   return ANDROID_LOG_DEBUG;
        }
    }
#endif
```

## 注意事项

### 不要在运行时频繁比较
虽然可以比较日志级别,但主要用途是编译期过滤,而非运行时判断。

### 避免循环依赖
该文件必须保持独立,不能包含其他 Skia 头文件。

### 用户配置的时机
日志级别配置必须在包含 SkLog.h 之前定义,通常在 SkUserConfig.h 中。

## 相关文件
| 文件 | 关系 |
|------|------|
| `SkLog.h` | 使用此枚举定义日志 API |
| `SkLoadUserConfig.h` | 包含此文件以供用户配置 |
| `SkUserConfig.h` | 用户定义日志级别的位置 |
| 平台特定日志实现 | 映射到平台日志系统 |

## 历史与演进
- 2026 年引入,统一 Skia 的日志优先级定义
- 替代之前各模块独立的日志级别定义
- 设计为可被用户配置文件安全包含
- 为 Skia 的日志系统标准化提供基础

## 总结
SkLogPriority 是一个设计精简的枚举定义,为 Skia 的日志系统提供了统一的优先级标准。其最小依赖的设计使其可以在编译早期被安全引用,支持用户在配置文件中灵活控制日志输出级别,实现编译期的零开销日志过滤。
