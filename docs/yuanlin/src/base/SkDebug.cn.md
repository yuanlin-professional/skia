# SkDebug - 调试输出函数
> 源文件: `src/base/SkDebug.cpp`

## 概述
SkDebug 模块提供了 Skia 的调试输出功能实现。主要包含 SkDebugf 函数，这是一个类似 printf 的格式化输出函数，用于在各个平台上统一地输出调试信息。该模块还为 Google3 环境提供了特殊的堆栈跟踪输出支持。SkDebugf 是 Skia 中最常用的调试工具之一，遍布整个代码库。

## 架构位置
SkDebug 位于 Skia 基础调试工具模块（src/base）中，属于平台抽象层。它为整个 Skia 代码库提供统一的调试输出接口，屏蔽了不同平台（Android、iOS、Windows、Linux、Web）在日志输出方面的差异。

## 公共 API 函数

### `void SkDebugf(const char format[], ...)`
- **功能**: 格式化输出调试信息（类似 printf）
- **参数**:
  - format: printf 风格的格式化字符串
  - ...: 可变参数列表
- **输出目标**: 取决于平台
  - Android: logcat
  - iOS: NSLog
  - Windows: OutputDebugString
  - Linux/Mac: stderr
  - Web: console.log
- **条件编译**: 仅在未定义 SkDebugf 宏时编译此实现

### `void SkDebugfForDumpStackTrace(const char* data, void* unused)`
- **功能**: Google3 专用的堆栈跟踪输出回调
- **参数**:
  - data: 堆栈跟踪文本
  - unused: 未使用的上下文参数
- **用途**: 作为回调传递给 Google3 的堆栈跟踪工具
- **实现**: 简单调用 SkDebugf
- **条件编译**: 仅在 SK_BUILD_FOR_GOOGLE3 定义时编译

## 内部实现细节

### 委托给 SkLog
```cpp
void SkDebugf(const char format[], ...) {
    va_list args;
    va_start(args, format);
    SkLogVAList(SkLogPriority::kDebug, format, args);
    va_end(args);
}
```

**设计**:
- SkDebugf 是 SkLog 系统的便利包装
- 实际输出由 SkLogVAList 处理
- 优先级设置为 kDebug

### 可变参数处理
使用标准 C 的 va_list 机制：
1. `va_start(args, format)`: 初始化参数列表
2. 将 va_list 传递给 SkLogVAList
3. `va_end(args)`: 清理参数列表

### 条件编译保护
```cpp
#if !defined(SkDebugf)
void SkDebugf(const char format[], ...) {
    // 实现
}
#endif
```

**原因**:
- 某些平台可能通过宏定义 SkDebugf
- 避免重复定义
- 保持平台特定优化的可能性

### Google3 特殊支持
```cpp
#if defined(SK_BUILD_FOR_GOOGLE3)
void SkDebugfForDumpStackTrace(const char* data, void* unused) {
    SkDebugf("%s", data);
}
#endif
```

**用途**:
- Google3 的堆栈跟踪工具需要函数指针回调
- 回调签名：`void (*)(const char*, void*)`
- 包装 SkDebugf 以匹配该签名

### SkLogVAList 和优先级
```cpp
SkLogVAList(SkLogPriority::kDebug, format, args);
```

**SkLogPriority::kDebug**:
- 表示这是调试级别的日志
- 其他级别可能包括：kInfo, kWarning, kError
- 允许日志系统根据级别过滤

### 平台特定实现在何处
SkLogVAList 的平台特定实现位于：
- **Android**: `src/ports/SkDebug_android.cpp`
- **iOS**: `src/ports/SkDebug_mac.cpp`
- **Windows**: `src/ports/SkDebug_win.cpp`
- **Unix**: `src/ports/SkDebug_stdio.cpp`
- **Web**: `src/ports/SkDebug_emscripten.cpp`

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkDebug.h | SkDebugf 声明（IWYU pragma: keep） |
| include/private/base/SkAssert.h | 断言相关定义（IWYU pragma: keep） |
| include/private/base/SkAttributes.h | 属性宏（IWYU pragma: keep） |
| include/private/base/SkLog.h | SkLogVAList 和 SkLogPriority |
| <cstdarg> | va_list, va_start, va_end |

### 被依赖的模块
几乎整个 Skia 代码库：
- 调试跟踪
- 错误报告
- 性能分析输出
- 单元测试
- 示例程序
- 内部工具

## 设计模式与设计决策

### 委托模式
SkDebugf 委托给 SkLog 系统：
- **分离关注点**: 格式化与输出分离
- **扩展性**: 可以统一添加功能（如时间戳、线程 ID）
- **测试性**: 可以重定向 SkLog 输出到测试框架

### 条件编译的多层次
1. **宏定义检查**: `#if !defined(SkDebugf)`
2. **平台检查**: `#if defined(SK_BUILD_FOR_GOOGLE3)`
3. **IWYU pragma**: 保持包含关系

这种设计支持高度的平台定制化。

### printf 风格而非流式
选择 `SkDebugf("x=%d", x)` 而非 `SkDebug() << "x=" << x`：
- **优点**:
  - 与 C 标准库一致
  - 更紧凑的调用代码
  - 更容易国际化（格式字符串可翻译）
- **缺点**:
  - 类型不安全（需要匹配 % 说明符）
  - 不支持自定义类型的流式输出

### 为何不是宏
SkDebugf 是函数而非宏：
- **优点**:
  - 类型检查
  - 调试器友好
  - 可以取地址（如作为函数指针）
- **缺点**:
  - 发布版仍然编译参数表达式（即使不输出）
  - 某些平台通过宏包装以优化

### Google3 的特殊处理
Google3 需要特殊回调适配器：
- Google3 有自己的堆栈跟踪基础设施
- 需要桥接到 Skia 的输出系统
- 通过专用函数提供桥接

## 性能考量

### 调试构建 vs 发布构建
- **调试构建**: SkDebugf 输出到平台日志
- **发布构建**: 通常被优化掉或禁用
- **控制**: 通过 SK_DEBUG 或平台特定宏

### 格式化开销
printf 风格的格式化相对昂贵：
- 字符串解析
- 类型转换
- 可变参数处理
- 建议：不要在性能关键循环中调用

### 条件调用
常见模式：
```cpp
#ifdef SK_DEBUG
    SkDebugf("Debug info: %d\n", value);
#endif
```
避免在发布版中计算参数和格式化。

### 平台输出速度
不同平台的输出速度差异很大：
- **最快**: 直接 stderr（微秒级）
- **中等**: OutputDebugString（毫秒级）
- **较慢**: Android logcat（可能阻塞）

### 缓冲行为
- 某些平台缓冲输出（需要换行符刷新）
- Android logcat 按行输出
- 建议：总是在调试消息末尾加 `\n`

## 使用模式

### 基本输出
```cpp
SkDebugf("Value: %d\n", value);
SkDebugf("Point: (%f, %f)\n", x, y);
SkDebugf("String: %s\n", str);
```

### 条件调试
```cpp
#ifdef SK_DEBUG
    SkDebugf("This only in debug builds\n");
#endif
```

### 详细级别控制
```cpp
#if SK_DEBUG_LEVEL > 1
    SkDebugf("Verbose debug info\n");
#endif
```

### 与断言结合
```cpp
if (badCondition) {
    SkDebugf("Error: bad condition detected\n");
    SkASSERT(false);
}
```

### 临时调试
```cpp
// TODO: remove debug print
SkDebugf("Reached line %d\n", __LINE__);
```

## 常见问题

### 输出不显示
可能原因：
1. 发布版构建（SkDebugf 被禁用）
2. 平台日志查看器未正确配置
3. 输出被缓冲（缺少换行符）
4. 平台特定实现未链接

### 格式化错误
```cpp
// 错误：类型不匹配
int64_t big = 123456789012345;
SkDebugf("%d\n", big);  // 未定义行为

// 正确
SkDebugf("%lld\n", big);
```

### 性能影响
即使输出被禁用，参数计算仍然执行：
```cpp
// 不好：即使不输出，expensiveComputation() 仍被调用
SkDebugf("Result: %d\n", expensiveComputation());

// 更好
#ifdef SK_DEBUG
    int result = expensiveComputation();
    SkDebugf("Result: %d\n", result);
#endif
```

## 替代方案

### SK_ABORT
对于致命错误：
```cpp
SK_ABORT("Fatal error: %s", reason);
```

### SkASSERT
用于断言检查（仅调试版）：
```cpp
SkASSERT(ptr != nullptr);
```

### SkLog 系列
更细粒度的日志控制：
```cpp
SkLog(SkLogPriority::kWarning, "Warning: %s", msg);
```

### 平台原生 API
有时直接使用更合适：
```cpp
#ifdef SK_BUILD_FOR_ANDROID
    __android_log_print(ANDROID_LOG_DEBUG, "Skia", "msg");
#endif
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkDebug.h | SkDebugf 声明 |
| include/private/base/SkLog.h | SkLog 系统接口 |
| src/base/SkLog.cpp | SkLog 实现 |
| src/ports/SkDebug_android.cpp | Android 平台实现 |
| src/ports/SkDebug_mac.cpp | iOS/Mac 平台实现 |
| src/ports/SkDebug_win.cpp | Windows 平台实现 |
| src/ports/SkDebug_stdio.cpp | Unix/Linux 平台实现 |
| include/private/base/SkAssert.h | 断言系统（使用 SkDebugf） |

## 最佳实践

### 总是包含换行符
```cpp
SkDebugf("Message\n");  // 好
SkDebugf("Message");    // 可能不会立即显示
```

### 使用前缀区分模块
```cpp
SkDebugf("[Path] Computing bounds\n");
SkDebugf("[GPU] Uploading texture\n");
```

### 避免敏感信息
```cpp
// 不要输出密码、密钥、个人信息
SkDebugf("API key: %s\n", key);  // 危险！
```

### 临时调试代码加注释
```cpp
// TEMP DEBUG - remove before commit
SkDebugf("x=%d y=%d\n", x, y);
```

### 发布前搜索并移除
```bash
git grep "SkDebugf" | grep -v "test"
```
