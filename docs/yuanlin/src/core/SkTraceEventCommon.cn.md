# SkTraceEventCommon

> 源文件: src/core/SkTraceEventCommon.h

## 概述

`SkTraceEventCommon.h` 是 Skia 性能追踪系统的宏定义层,提供跨平台的追踪事件 API。它支持多种追踪后端(SkEventTracer、ATrace、Perfetto),并针对 Android Framework 提供特殊支持。该文件定义了 `TRACE_EVENT` 系列宏,用于记录作用域持续时间、瞬时事件、计数器等性能数据。

## 架构位置

追踪系统位于 Skia 基础设施层,是性能分析和调试的关键工具:

- **用途**: 性能分析、调试、性能回归检测
- **后端**: SkEventTracer(默认)、ATrace(Android)、Perfetto(Android Framework)
- **集成**: Chrome 追踪、Android Systrace、独立工具

## 主要宏与功能

### 基础追踪宏

#### 作用域事件

| 宏 | 参数 | 功能 |
|----|------|------|
| `TRACE_EVENT0(category, name)` | 类别、名称 | 记录作用域持续时间 |
| `TRACE_EVENT1(category, name, arg1_name, arg1_val)` | +1 个参数 | 作用域事件带 1 个参数 |
| `TRACE_EVENT2(category, name, arg1_name, arg1_val, arg2_name, arg2_val)` | +2 个参数 | 作用域事件带 2 个参数 |

**使用示例**:
```cpp
void doSomethingCostly() {
    TRACE_EVENT0("skia", "doSomethingCostly");
    // 离开作用域时自动记录结束时间
}

void processData(int count) {
    TRACE_EVENT1("skia.gpu", "processData", "count", count);
    // ...
}
```

#### 瞬时事件

| 宏 | 功能 |
|----|------|
| `TRACE_EVENT_INSTANT0(category, name, scope)` | 记录单个时刻 |
| `TRACE_EVENT_INSTANT1/2(...)` | 带参数的瞬时事件 |

**作用域类型**:
- `TRACE_EVENT_SCOPE_GLOBAL`: 全局作用域
- `TRACE_EVENT_SCOPE_PROCESS`: 进程作用域
- `TRACE_EVENT_SCOPE_THREAD`: 线程作用域

#### 计数器

| 宏 | 功能 |
|----|------|
| `TRACE_COUNTER1(category, name, value)` | 记录单个计数器 |
| `TRACE_COUNTER2(category, name, v1_name, v1_val, v2_name, v2_val)` | 记录两个相关计数器 |

### Always 变体

```cpp
TRACE_EVENT0_ALWAYS(category, name)
TRACE_EVENT1_ALWAYS(category, name, arg1_name, arg1_val)
// ...
```

- 即使"广泛追踪"被禁用也会记录
- 用于关键事件(如帧提交)
- 在 Android Framework 中自动添加 `.always` 后缀

### Android Framework 特殊宏

```cpp
ATRACE_ANDROID_FRAMEWORK(fmt, ...)
ATRACE_ANDROID_FRAMEWORK_ALWAYS(fmt, ...)
```

- 支持 `printf` 风格格式化
- 仅在 Android Framework 构建时可用
- 多行宏,不能用于单行 if 语句

## 内部实现细节

### 追踪后端选择

```cpp
#if defined(SK_DISABLE_TRACING)
    #define TRACE_EVENT0(...) do {} while (0)
    // 所有宏变为空操作

#elif defined(SK_ANDROID_FRAMEWORK_USE_PERFETTO)
    // Android Framework + Perfetto 实现
    #define TRACE_EVENT0(category, name) \
        TRACE_EVENT_ATRACE_OR_PERFETTO(category, name)

#else
    // 标准 SkEventTracer 实现
    #define TRACE_EVENT0(category, name) \
        INTERNAL_TRACE_EVENT_ADD_SCOPED(category, name)
#endif
```

**构建配置**:
1. `SK_DISABLE_TRACING`: 完全禁用追踪
2. `SK_ANDROID_FRAMEWORK_USE_PERFETTO`: Android Framework 混合模式
3. 默认: 使用 `SkEventTracer` 接口

### Android Framework 混合追踪

Android Framework 支持运行时在 ATrace 和 Perfetto 之间切换:

```cpp
class SkAndroidFrameworkTraceUtil {
public:
    // 控制是否启用广泛追踪
    static void setEnableTracing(bool enableAndroidTracing);

    // 切换追踪后端 (ATrace <-> Perfetto)
    static bool setUsePerfettoTrackEvents(bool usePerfettoTrackEvents);

    static bool getEnableTracing();
    static bool getUsePerfettoTrackEvents();
};
```

**使用模式**:
```cpp
// 启动时
SkAndroidFrameworkTraceUtil::setEnableTracing(true);
SkAndroidFrameworkTraceUtil::setUsePerfettoTrackEvents(false);  // 默认 ATrace

// 运行时切换
SkAndroidFrameworkTraceUtil::setUsePerfettoTrackEvents(true);  // 切换到 Perfetto
```

### Perfetto 类别定义

```cpp
#ifdef SK_ANDROID_FRAMEWORK_USE_PERFETTO
PERFETTO_DEFINE_CATEGORIES(
    perfetto::Category("skia"),
    perfetto::Category("skia.gpu"),
    perfetto::Category("skia.gpu.cache"),
    perfetto::Category("skia.shaders"),
    // ".always" 变体用于关键事件
    perfetto::Category("skia.always").SetTags("skia.always"),
    perfetto::Category("skia.gpu.always").SetTags("skia.always"),
    // ...
);
#endif
```

**类别系统**:
- 静态类别列表(编译时定义)
- `.always` 变体支持过滤关键事件
- 与 ATrace 动态类别不同

### ATrace 参数模拟

ATrace 原生不支持事件参数,Skia 通过嵌套切片模拟:

```cpp
#define SK_INTERNAL_ATRACE_ARGS_BEGIN_DANGEROUS_1(name, arg1_name, arg1_val) \
    char skTraceStrBuf1[SK_ANDROID_FRAMEWORK_ATRACE_BUFFER_SIZE];            \
    snprintf(skTraceStrBuf1, ..., "^(%s: %s)", arg1_name, arg1_val);         \
    atrace_begin_body(name);                                                 \
    atrace_begin_body(skTraceStrBuf1);  // 嵌套切片
```

**实现细节**:
- 主事件一个切片
- 每个参数一个嵌套切片
- 参数切片以 `^(` 开头标记
- 需要匹配的 `atrace_end_body()` 调用

### 字符串复制宏

```cpp
#ifdef SK_ANDROID_FRAMEWORK_USE_PERFETTO
    #define TRACE_STR_COPY(str) (::perfetto::DynamicString{str})
    #define TRACE_STR_STATIC(str) (::perfetto::StaticString{str})
#else
    #define TRACE_STR_COPY(str) (::skia_private::TraceStringWithCopy(str))
    #define TRACE_STR_STATIC(str) (str)
#endif
```

**使用场景**:
- `TRACE_STR_COPY`: 短生命周期字符串(如 `std::string::c_str()`)
- `TRACE_STR_STATIC`: 静态字符串(进程生命周期)
- 字面量无需包装

### 追踪标志

```cpp
#define TRACE_EVENT_FLAG_NONE              (0)
#define TRACE_EVENT_FLAG_COPY              (1 << 0)
#define TRACE_EVENT_FLAG_HAS_ID            (1 << 1)
#define TRACE_EVENT_FLAG_MANGLE_ID         (1 << 2)
#define TRACE_EVENT_FLAG_SCOPE_OFFSET      (1 << 3)
#define TRACE_EVENT_FLAG_SCOPE_EXTRA       (1 << 4)
// ...
```

控制追踪事件的行为(复制字符串、ID 处理等)。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkTraceEventPhase.h` | 事件阶段常量 |
| `<perfetto/tracing.h>` | Perfetto 集成(可选) |
| `<cutils/trace.h>` | ATrace 集成(Android) |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| Skia 核心代码 | 所有性能关键路径 |
| GPU 后端 | 渲染管线追踪 |
| 图像编解码 | 编解码性能分析 |
| 字体系统 | 字形缓存追踪 |

## 设计模式与设计决策

### 设计模式

1. **宏抽象层**: 隔离不同追踪后端
2. **RAII 模式**: 作用域事件自动记录开始/结束
3. **策略模式**: 运行时切换追踪后端(Android)

### 设计决策

**为什么使用宏而不是函数?**
- 零开销(禁用时完全消除)
- 捕获源文件位置信息
- 支持复杂的参数处理

**为什么限制参数数量为 2?**
- 平衡功能和性能
- 过多参数影响追踪开销
- 大多数场景 2 个参数足够

**Android Framework 的混合架构**
```cpp
if (SkAndroidFrameworkTraceUtil::getUsePerfettoTrackEvents()) {
    TRACE_EVENT_BEGIN(category, name, ##__VA_ARGS__);
} else {
    SK_INTERNAL_ATRACE_ARGS_BEGIN(name, ##__VA_ARGS__);
}
```
- 支持平滑迁移到 Perfetto
- 运行时切换后端
- 单一代码库支持两种系统

**类别前缀**
```cpp
#define TRACE_CATEGORY_PREFIX "disabled-by-default-"
```
- Skia 追踪在 Chrome 中默认禁用
- 避免干扰 Chrome 自身追踪
- 用户需显式启用

**线程安全性**
- `setEnableTracing()` 不是线程安全的
- 应在启动时配置,避免运行时切换
- 追踪事件本身是线程安全的

## 性能考量

### 优化策略

1. **条件编译**: `SK_DISABLE_TRACING` 完全消除
2. **延迟求值**: 参数仅在启用时评估
3. **静态缓存**: 类别启用状态缓存
4. **批量操作**: Perfetto 支持批量提交

### 开销分析

**禁用追踪** (`SK_DISABLE_TRACING`):
```cpp
#define TRACE_EVENT0(...) do {} while (0)
```
- 编译器完全优化掉
- 零运行时开销

**启用但未激活追踪**:
```cpp
INTERNAL_TRACE_EVENT_GET_CATEGORY_INFO(category_group);
if (INTERNAL_TRACE_EVENT_CATEGORY_GROUP_ENABLED_FOR_RECORDING_MODE()) {
    // ...
}
```
- 原子加载 + 位测试(~2-3 个周期)
- 分支预测友好(通常不追踪)

**活跃追踪**:
- 时间戳获取: ~10-30 ns
- 数据缓冲: ~50-100 ns
- 总开销: ~100-200 ns per event

### 使用建议

**适合追踪的场景**:
- 函数耗时 > 1 微秒
- 性能关键路径
- GPU 操作
- 文件 I/O

**不适合追踪**:
- 内联函数
- 紧密循环内部
- 耗时 < 100 纳秒的操作

**宏选择**:
```cpp
// 常规代码 - 可通过 setEnableTracing() 控制
TRACE_EVENT0("skia", "function");

// 关键路径 - 总是追踪
TRACE_EVENT0_ALWAYS("skia", "criticalFunction");

// Android Framework - 格式化字符串
ATRACE_ANDROID_FRAMEWORK("Processing %d items", count);
```

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/core/SkTraceEvent.h` | 实现细节和辅助类 |
| `include/utils/SkEventTracer.h` | 标准追踪器接口 |
| `include/utils/SkTraceEventPhase.h` | 事件阶段定义 |
| `src/utils/SkEventTracer.cpp` | 默认追踪器实现 |
| `tools/sk_app/CommandSet.cpp` | 工具中的追踪配置 |
