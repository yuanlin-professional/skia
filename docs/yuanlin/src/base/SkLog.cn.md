# SkLog - 日志系统接口
> 源文件: `src/base/SkLog.cpp`

## 概述
SkLog 模块提供了 Skia 的日志输出接口实现。它定义了 SkLog 函数，这是一个支持日志优先级的格式化输出函数。该函数接受优先级参数（Debug、Info、Warning、Error 等），允许日志系统根据级别进行过滤和路由。SkLog 是 SkDebugf 的底层实现基础，为整个 Skia 提供统一的日志记录能力。

## 架构位置
SkLog 位于 Skia 基础日志系统模块（src/base）中，是日志抽象层的核心。它为 SkDebugf、断言系统、错误报告等上层模块提供统一的输出接口，同时通过平台特定的 SkLogVAList 实现屏蔽平台差异。

## 公共 API 函数

### `void SkLog(SkLogPriority priority, const char format[], ...)`
- **功能**: 记录带优先级的日志消息
- **参数**:
  - priority: 日志优先级（SkLogPriority 枚举）
  - format: printf 风格的格式化字符串
  - ...: 可变参数列表
- **行为**: 将格式化的消息传递给 SkLogVAList 进行实际输出
- **条件编译**: 仅在未定义 SkLog 宏时编译此实现

## 内部实现细节

### 日志优先级（SkLogPriority）
虽然在此文件中未定义，但通常包括：
```cpp
enum class SkLogPriority {
    kDebug,    // 调试信息
    kInfo,     // 一般信息
    kWarning,  // 警告
    kError,    // 错误
    kFatal,    // 致命错误
};
```

### 实现结构
```cpp
#if !defined(SkLog)
void SkLog(SkLogPriority priority, const char format[], ...) {
    va_list args;
    va_start(args, format);
    SkLogVAList(priority, format, args);
    va_end(args);
}
#endif
```

**设计**:
1. 使用可变参数（va_list）处理格式化参数
2. 委托给 SkLogVAList 进行实际输出
3. 条件编译保护，允许平台通过宏重写

### 可变参数处理
- `va_start(args, format)`: 初始化参数列表，从 format 后的第一个参数开始
- `va_list args`: 参数列表句柄
- `va_end(args)`: 清理参数列表

### 委托给 SkLogVAList
SkLogVAList 的平台特定实现位于：
- **src/ports/SkDebug_android.cpp**: Android 平台（使用 __android_log_vprint）
- **src/ports/SkDebug_mac.cpp**: iOS/Mac 平台（使用 NSLogv）
- **src/ports/SkDebug_win.cpp**: Windows 平台（使用 OutputDebugStringA）
- **src/ports/SkDebug_stdio.cpp**: Unix/Linux 平台（使用 vfprintf(stderr, ...)）
- **src/ports/SkDebug_emscripten.cpp**: Web 平台（使用 console API）

### 条件编译保护
```cpp
#if !defined(SkLog)
```

**目的**:
- 允许平台通过宏定义 SkLog
- 启用平台特定优化
- 避免重复定义错误

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkLog.h | SkLog 和 SkLogPriority 声明 |
| <cstdarg> | va_list, va_start, va_end |

### 被依赖的模块
- src/base/SkDebug.cpp（SkDebugf 的实现）
- 断言系统（SK_ABORT、SkASSERT）
- 错误报告机制
- 测试框架
- 调试工具

## 设计模式与设计决策

### 优先级分层
支持不同优先级的日志：
- **优点**:
  - 运行时过滤（只显示 Warning 及以上）
  - 不同输出目的地（Error 发送到服务器）
  - 统计和监控（错误率追踪）
- **灵活性**: 比简单的 printf 更强大

### 两层架构
SkLog（可变参数）-> SkLogVAList（va_list）：
- **SkLog**: 方便的用户接口
- **SkLogVAList**: 平台实现接口
- **分离**: 用户代码不需要处理 va_list

### 平台抽象
通过平台特定的 SkLogVAList 实现：
- 统一的 API
- 平台优化的输出
- 易于添加新平台

### 条件编译灵活性
允许通过宏替换：
```cpp
// 某些平台可能定义
#define SkLog(priority, format, ...) platform_specific_log(priority, format, ##__VA_ARGS__)
```

## 与 SkDebugf 的关系

### SkDebugf 是 SkLog 的便利包装
```cpp
// SkDebug.cpp
void SkDebugf(const char format[], ...) {
    va_list args;
    va_start(args, format);
    SkLogVAList(SkLogPriority::kDebug, format, args);
    va_end(args);
}
```

**区别**:
- SkDebugf: 固定优先级（Debug），更简单
- SkLog: 可指定优先级，更灵活

### 调用链
```
用户代码
  |
  v
SkDebugf("x=%d", x) 或 SkLog(kError, "Failed: %s", msg)
  |
  v
SkLogVAList(priority, format, va_list)
  |
  v
平台特定实现（Android logcat, stderr, OutputDebugString, 等）
```

## 优先级使用指南

### kDebug
- **用途**: 详细的调试信息
- **场景**: 临时调试、开发期间
- **生产**: 通常禁用或过滤
- **示例**: `SkLog(kDebug, "Entering function %s", __FUNCTION__);`

### kInfo
- **用途**: 一般性信息消息
- **场景**: 初始化成功、配置信息
- **生产**: 可选显示
- **示例**: `SkLog(kInfo, "Loaded %d fonts", count);`

### kWarning
- **用途**: 警告信息，非致命问题
- **场景**: 降级功能、性能问题
- **生产**: 应该记录和监控
- **示例**: `SkLog(kWarning, "Falling back to software rendering");`

### kError
- **用途**: 错误信息，功能失败
- **场景**: 文件打开失败、解码错误
- **生产**: 必须记录，可能需要报告
- **示例**: `SkLog(kError, "Failed to load image: %s", path);`

### kFatal
- **用途**: 致命错误，程序无法继续
- **场景**: 严重的逻辑错误、资源耗尽
- **生产**: 记录后通常终止程序
- **示例**: `SkLog(kFatal, "Out of memory"); abort();`

## 性能考量

### 可变参数开销
可变参数函数略慢于固定参数：
- va_list 操作需要栈遍历
- 类型信息在运行时解析
- 但对于日志输出（I/O 密集），影响可忽略

### 条件日志
避免不必要的格式化：
```cpp
// 不好：即使日志被禁用，expensiveToString() 仍被调用
SkLog(kDebug, "Value: %s", expensiveToString(obj));

// 好：先检查是否启用
#if SK_LOG_LEVEL >= SK_LOG_DEBUG
    SkLog(kDebug, "Value: %s", expensiveToString(obj));
#endif
```

### 平台输出速度
不同平台的日志输出速度差异很大：
- **stderr**: 微秒级（如果不是终端）
- **Android logcat**: 毫秒级（进程间通信）
- **Windows OutputDebugString**: 毫秒级（特别是有调试器时）
- **建议**: 不要在紧密循环中大量日志

### 格式化开销
printf 风格格式化相对昂贵：
- 解析格式字符串
- 类型转换和格式化
- 字符串构建
- 对于性能关键代码，考虑条件编译

## 使用示例

### 基本用法
```cpp
SkLog(SkLogPriority::kInfo, "Application started");
SkLog(SkLogPriority::kDebug, "x=%d, y=%d", x, y);
SkLog(SkLogPriority::kWarning, "Resource limit reached: %d/%d", used, max);
SkLog(SkLogPriority::kError, "Failed to open file: %s", filename);
```

### 条件日志
```cpp
#ifdef SK_DEBUG
    SkLog(kDebug, "Debug build, extra checks enabled");
#endif
```

### 错误处理
```cpp
if (!loadFont(path)) {
    SkLog(kError, "Failed to load font: %s", path);
    return false;
}
```

### 性能追踪
```cpp
SkLog(kInfo, "Rendering frame took %lld ms", elapsedTime);
```

## 扩展日志系统

### 自定义日志处理器
某些平台可能重定向日志：
```cpp
// 自定义 SkLogVAList 实现
void SkLogVAList(SkLogPriority priority, const char format[], va_list args) {
    if (priority >= kWarning) {
        // 发送到远程日志服务器
        sendToServer(priority, format, args);
    }
    // 同时输出到本地
    vfprintf(stderr, format, args);
}
```

### 日志过滤
```cpp
void SkLogVAList(SkLogPriority priority, const char format[], va_list args) {
    if (priority < gMinLogLevel) {
        return;  // 过滤低优先级日志
    }
    // 输出
}
```

### 格式化增强
```cpp
void SkLogVAList(SkLogPriority priority, const char format[], va_list args) {
    // 添加时间戳
    fprintf(stderr, "[%s] ", getCurrentTime());
    // 添加优先级标签
    fprintf(stderr, "[%s] ", priorityToString(priority));
    // 原始消息
    vfprintf(stderr, format, args);
    fprintf(stderr, "\n");
}
```

## 平台差异

### Android
```cpp
// SkDebug_android.cpp
#include <android/log.h>
void SkLogVAList(SkLogPriority priority, const char format[], va_list args) {
    __android_log_vprint(priorityToAndroid(priority), "Skia", format, args);
}
```

### iOS/Mac
```cpp
// SkDebug_mac.cpp
void SkLogVAList(SkLogPriority priority, const char format[], va_list args) {
    NSLogv([NSString stringWithUTF8String:format], args);
}
```

### Windows
```cpp
// SkDebug_win.cpp
void SkLogVAList(SkLogPriority priority, const char format[], va_list args) {
    char buffer[4096];
    vsnprintf(buffer, sizeof(buffer), format, args);
    OutputDebugStringA(buffer);
}
```

### Unix/Linux
```cpp
// SkDebug_stdio.cpp
void SkLogVAList(SkLogPriority priority, const char format[], va_list args) {
    vfprintf(stderr, format, args);
}
```

## 最佳实践

### 选择合适的优先级
```cpp
// 调试信息
SkLog(kDebug, "Entering loop iteration %d", i);

// 配置信息
SkLog(kInfo, "Using GPU backend: %s", gpuName);

// 可恢复的错误
SkLog(kWarning, "Font not found, using fallback");

// 功能失败
SkLog(kError, "Texture upload failed");

// 程序无法继续
SkLog(kFatal, "Assertion failed: %s", condition);
```

### 包含上下文信息
```cpp
// 好：提供足够的上下文
SkLog(kError, "Failed to decode image %s: %s", filename, errorMsg);

// 不好：缺少上下文
SkLog(kError, "Decode failed");
```

### 避免敏感信息
```cpp
// 危险：可能泄露敏感信息
SkLog(kDebug, "API key: %s", apiKey);

// 安全：不记录敏感数据
SkLog(kDebug, "API authentication successful");
```

### 国际化友好
```cpp
// 可考虑
SkLog(kError, GetLocalizedString(kErrorFileNotFound), filename);
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkLog.h | SkLog 和 SkLogPriority 声明 |
| src/base/SkDebug.cpp | SkDebugf 实现（使用 SkLog） |
| src/ports/SkDebug_android.cpp | Android 平台实现 |
| src/ports/SkDebug_mac.cpp | iOS/Mac 平台实现 |
| src/ports/SkDebug_win.cpp | Windows 平台实现 |
| src/ports/SkDebug_stdio.cpp | Unix/Linux 平台实现 |
| include/private/base/SkAssert.h | 断言系统（使用 SkLog） |
