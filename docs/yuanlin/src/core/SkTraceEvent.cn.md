# SkTraceEvent

> 源文件: src/core/SkTraceEvent.h

## 概述

`SkTraceEvent.h` 是 Skia 追踪系统的实现层,定义了 `SkTraceEventCommon.h` 中宏的底层实现细节。该文件包含追踪事件的辅助类、类型转换函数、以及与 `SkEventTracer` 接口的桥接代码。它提供了高效的追踪数据收集机制,支持多种参数类型和字符串处理策略。

## 架构位置

实现层位于追踪系统的底层,连接宏层和追踪器接口:

- **上层**: `SkTraceEventCommon.h` 的宏定义
- **下层**: `SkEventTracer` 接口、平台追踪器
- **角色**: 类型安全、参数打包、RAII 封装

## 主要类与结构体

### TraceID

**继承关系**:
- 无继承,值类型

**功能**: 封装追踪事件 ID,支持整数和指针类型

**构造函数重载**:

| 构造函数 | 说明 |
|---------|------|
| `TraceID(const void*, unsigned char*)` | 指针 ID,自动设置 mangle 标志 |
| `TraceID(uint64_t, unsigned char*)` | 64 位整数 ID |
| `TraceID(unsigned int, unsigned char*)` | 32 位无符号整数 |
| `TraceID(int, unsigned char*)` | 有符号整数 |
| 等等 | 支持所有整数类型 |

**关键成员**:

| 成员 | 类型 | 说明 |
|------|------|------|
| `data_` | `uint64_t` | 统一的 64 位 ID 存储 |

### TraceStringWithCopy

**功能**: 标记字符串需要复制而非引用

```cpp
class TraceStringWithCopy {
public:
    explicit TraceStringWithCopy(const char* str) : str_(str) {}
    operator const char*() const { return str_; }
private:
    const char* str_;
};
```

### ScopedTracer

**继承关系**:
- 无继承,RAII 类

**功能**: 自动管理作用域追踪事件的生命周期

**关键成员**:

| 成员 | 类型 | 说明 |
|------|------|------|
| `p_data_` | `Data*` | 指向 `data_` 或 `nullptr` |
| `data_` | `Data` | 存储追踪上下文 |

**Data 结构**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `category_group_enabled` | `const uint8_t*` | 类别启用状态指针 |
| `name` | `const char*` | 事件名称 |
| `event_handle` | `SkEventTracer::Handle` | 事件句柄 |

## 公共 API 函数

### 类型转换函数

#### SetTraceValue 模板

```cpp
template <typename T>
static inline void SetTraceValue(const T& arg,
                                 unsigned char* type,
                                 uint64_t* value)
```

**支持的类型**:

| 类型 | TRACE_VALUE_TYPE | 存储方式 |
|------|------------------|----------|
| `bool` | `TRACE_VALUE_TYPE_BOOL` | 直接存储 |
| `const char*` | `TRACE_VALUE_TYPE_STRING` | 存储指针 |
| `TraceStringWithCopy` | `TRACE_VALUE_TYPE_COPY_STRING` | 存储指针(标记复制) |
| 指针类型 | `TRACE_VALUE_TYPE_POINTER` | 转换为 `uintptr_t` |
| 无符号整数 | `TRACE_VALUE_TYPE_UINT` | 直接存储 |
| 有符号整数 | `TRACE_VALUE_TYPE_INT` | 转换为 `uint64_t` |
| 浮点数 | `TRACE_VALUE_TYPE_DOUBLE` | `sk_bit_cast` 转换 |

#### 辅助提取函数

```cpp
static inline const char* TraceValueAsString(uint64_t value);
static inline const void* TraceValueAsPointer(uint64_t value);
```

### AddTraceEvent 重载

#### 无参数版本

```cpp
static inline SkEventTracer::Handle
AddTraceEvent(char phase,
              const uint8_t* category_group_enabled,
              const char* name,
              uint64_t id,
              unsigned char flags);
```

#### 1 参数版本

```cpp
template<class ARG1_TYPE>
static inline SkEventTracer::Handle
AddTraceEvent(char phase,
              const uint8_t* category_group_enabled,
              const char* name,
              uint64_t id,
              unsigned char flags,
              const char* arg1_name,
              const ARG1_TYPE& arg1_val);
```

#### 2 参数版本

```cpp
template<class ARG1_TYPE, class ARG2_TYPE>
static inline SkEventTracer::Handle
AddTraceEvent(...,
              const char* arg1_name, const ARG1_TYPE& arg1_val,
              const char* arg2_name, const ARG2_TYPE& arg2_val);
```

### ScopedTracer 方法

| 方法 | 功能 |
|------|------|
| `ScopedTracer()` | 构造函数,成员未初始化 |
| `~ScopedTracer()` | 析构时更新事件持续时间 |
| `void Initialize(const uint8_t*, const char*, SkEventTracer::Handle)` | 延迟初始化 |

## 内部实现细节

### 静态类别缓存

```cpp
#define INTERNAL_TRACE_EVENT_GET_CATEGORY_INFO(category_group)         \
    static std::atomic<intptr_t> INTERNAL_TRACE_EVENT_UID(atomic){0};  \
    const uint8_t* INTERNAL_TRACE_EVENT_UID(category_group_enabled);   \
    INTERNAL_TRACE_EVENT_GET_CATEGORY_INFO_CUSTOM_VARIABLES(           \
        TRACE_CATEGORY_PREFIX category_group,                          \
        INTERNAL_TRACE_EVENT_UID(atomic),                              \
        INTERNAL_TRACE_EVENT_UID(category_group_enabled));
```

**工作原理**:
1. 每个追踪点有一个静态原子变量
2. 首次调用时查询类别启用状态
3. 缓存结果供后续使用
4. 使用 `memory_order_relaxed` 提高性能

### 作用域事件实现

```cpp
#define INTERNAL_TRACE_EVENT_ADD_SCOPED(category_group, name, ...)     \
    INTERNAL_TRACE_EVENT_GET_CATEGORY_INFO(category_group);            \
    skia_private::ScopedTracer INTERNAL_TRACE_EVENT_UID(tracer);       \
    do {                                                               \
        if (INTERNAL_TRACE_EVENT_CATEGORY_GROUP_ENABLED_FOR_RECORDING_MODE()) { \
          SkEventTracer::Handle h = skia_private::AddTraceEvent(       \
              TRACE_EVENT_PHASE_COMPLETE,                              \
              INTERNAL_TRACE_EVENT_UID(category_group_enabled),        \
              name, skia_private::kNoEventId,                          \
              TRACE_EVENT_FLAG_NONE, ##__VA_ARGS__);                   \
          INTERNAL_TRACE_EVENT_UID(tracer).Initialize(                 \
              INTERNAL_TRACE_EVENT_UID(category_group_enabled), name, h); \
        }                                                              \
    } while (0)
```

**流程**:
1. 获取类别信息(静态缓存)
2. 在栈上创建 `ScopedTracer` 对象
3. 如果类别启用,调用 `AddTraceEvent` 记录开始
4. 初始化 `ScopedTracer`
5. 离开作用域时析构函数更新持续时间

### 带 ID 的事件

```cpp
#define INTERNAL_TRACE_EVENT_ADD_WITH_ID(phase, category_group, name, id, flags, ...) \
    do { \
      INTERNAL_TRACE_EVENT_GET_CATEGORY_INFO(category_group);                         \
      if (INTERNAL_TRACE_EVENT_CATEGORY_GROUP_ENABLED_FOR_RECORDING_MODE()) {         \
        unsigned char trace_event_flags = flags | TRACE_EVENT_FLAG_HAS_ID;            \
        skia_private::TraceID trace_event_trace_id(id, &trace_event_flags);           \
        skia_private::AddTraceEvent(                                                  \
            phase, INTERNAL_TRACE_EVENT_UID(category_group_enabled),                  \
            name, trace_event_trace_id.data(), trace_event_flags,                     \
            ##__VA_ARGS__);                                                           \
      }                                                                               \
    } while (0)
```

用于异步事件、对象生命周期追踪等场景。

### 类型安全的参数处理

```cpp
template <typename T>
static inline void SetTraceValue(const T& arg, unsigned char* type, uint64_t* value) {
    static_assert(sizeof(T) <= sizeof(uint64_t), "Trace value is larger than uint64_t");

    if constexpr (std::is_same<bool, T>::value) {
        *type = TRACE_VALUE_TYPE_BOOL;
        *value = arg;
    } else if constexpr (std::is_same<const char*, T>::value) {
        *type = TRACE_VALUE_TYPE_STRING;
        *value = reinterpret_cast<uintptr_t>(arg);
    } else if constexpr (std::is_floating_point_v<T>) {
        *type = TRACE_VALUE_TYPE_DOUBLE;
        *value = sk_bit_cast<uint64_t>(arg);  // 避免类型双关
    }
    // ...
}
```

**编译时类型检查**:
- `static_assert` 确保类型大小
- `if constexpr` 编译时分支
- 无运行时开销

### 字符串处理策略

**引用字符串**:
```cpp
TRACE_EVENT1("skia", "func", "name", "literal");  // 不复制
```

**复制字符串**:
```cpp
std::string temp = "temp";
TRACE_EVENT1("skia", "func", "name", TRACE_STR_COPY(temp.c_str()));  // 复制
```

**Perfetto 字符串**:
```cpp
#ifdef SK_ANDROID_FRAMEWORK_USE_PERFETTO
    #define TRACE_STR_COPY(str) (::perfetto::DynamicString{str})
#else
    #define TRACE_STR_COPY(str) (::skia_private::TraceStringWithCopy(str))
#endif
```

### ScopedTracer 实现

```cpp
~ScopedTracer() {
    if (p_data_ && *data_.category_group_enabled)
      TRACE_EVENT_API_UPDATE_TRACE_EVENT_DURATION(
          data_.category_group_enabled, data_.name, data_.event_handle);
}
```

**优化点**:
- `p_data_` 为 `nullptr` 时跳过(未初始化)
- 再次检查类别启用状态(可能被运行时禁用)
- 仅在启用时调用更新函数

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkEventTracer` | 追踪器接口 |
| `SkTraceEventCommon.h` | 宏定义层 |
| `SkUtils.h` | `sk_bit_cast` 等工具 |
| `<atomic>` | 类别缓存 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| 所有追踪宏展开代码 | 使用此文件的函数和类 |
| 自定义追踪器实现 | 可参考类型定义 |

## 设计模式与设计决策

### 设计模式

1. **RAII 模式**: `ScopedTracer` 自动管理生命周期
2. **模板元编程**: 编译时类型分派
3. **单例缓存**: 静态类别状态缓存

### 设计决策

**为什么 ScopedTracer 成员未初始化?**

```cpp
// Note: members of data_ intentionally left uninitialized. See Initialize.
ScopedTracer() : p_data_(nullptr) {}
```

- `ScopedTracer` 总是在栈上创建
- 如果追踪禁用,永远不会初始化
- 避免不必要的零初始化开销

**为什么使用 Data 结构体?**

```cpp
struct Data {
    const uint8_t* category_group_enabled;
    const char* name;
    SkEventTracer::Handle event_handle;
};
Data* p_data_;
Data data_;
```

- 避免构造时初始化所有成员
- 通过 `p_data_` 判断是否已初始化
- 减少编译器警告

**参数数量限制**

仅支持 0-2 个参数:
- 平衡功能和实现复杂度
- 过多参数影响追踪性能
- 可使用格式化字符串传递更多信息

**TraceID 的指针 mangling**

```cpp
TraceID(const void* id, unsigned char* flags)
        : data_(static_cast<uint64_t>(reinterpret_cast<uintptr_t>(id))) {
    *flags |= TRACE_EVENT_FLAG_MANGLE_ID;
}
```

- 避免跨进程 ID 冲突
- 混合进程 ID 到指针值
- 追踪器后端处理 mangling

**浮点数编码**

```cpp
*value = sk_bit_cast<uint64_t>(arg);  // 而非 reinterpret_cast
```

- 避免类型双关未定义行为
- `sk_bit_cast` 是 `std::bit_cast` 的兼容实现
- 保留所有浮点位(包括 NaN 模式)

## 性能考量

### 优化策略

1. **静态缓存**: 类别启用状态缓存在静态变量
2. **延迟初始化**: `ScopedTracer` 仅在需要时初始化
3. **编译时分派**: `if constexpr` 消除分支
4. **无拷贝**: 默认引用字符串

### 内存布局

**ScopedTracer**:
```
sizeof(ScopedTracer) = sizeof(Data*) + sizeof(Data)
                     = 8 + (8 + 8 + 8)
                     = 32 字节 (64位系统)
```

- 栈分配,无堆开销
- 未使用时仅 8 字节有效(`p_data_ = nullptr`)

### 性能测试

**宏展开开销** (类别禁用):
```cpp
TRACE_EVENT0("skia", "func");
// 展开为:
static std::atomic<intptr_t> atomic{0};
const uint8_t* enabled = atomic.load(std::memory_order_relaxed);
if (!enabled) {
    enabled = GetCategoryGroupEnabled("disabled-by-default-skia");
    atomic.store(...);
}
if (*enabled & kEnabledForRecording) {  // 通常为 false
    // 不执行
}
```

- 原子加载: ~1 周期
- 分支预测: 几乎总是不追踪
- 总开销: ~2-3 周期

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/core/SkTraceEventCommon.h` | 宏定义层 |
| `include/utils/SkEventTracer.h` | 追踪器接口 |
| `include/utils/SkTraceEventPhase.h` | 事件阶段常量 |
| `src/base/SkUtils.h` | `sk_bit_cast` 等工具 |
