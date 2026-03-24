# SkAssert

> 源文件: `include/private/base/SkAssert.h`

## 概述
SkAssert 是 Skia 的断言和错误处理基础设施,提供了一套宏用于运行时检查、调试断言和不可达代码标记。它统一了 Skia 在不同平台和编译器上的断言行为,支持调试和发布模式的不同策略。

## 架构位置
该头文件位于 Skia 基础设施层的核心,是错误检测和调试支持的基石。几乎所有 Skia 模块都直接或间接依赖此文件,用于参数验证、状态检查和不变量断言。

## 主要宏定义

### 条件编译标记

#### `SK_LIKELY` / `SK_UNLIKELY`
- **功能**: 为分支预测提供编译器提示
- **实现**:
  - Clang: 使用 `[[likely]]` 和 `[[unlikely]]` 属性(C++20)
  - 其他编译器: 空定义
- **用途**: 优化热路径和错误处理路径

#### `SK_ASSUME(cond)`
- **功能**: 告诉编译器可以假设条件为真
- **实现**:
  - Clang: `__builtin_assume(cond)`
  - GCC 13+: `__attribute__((assume(cond)))`
  - GCC < 13: `(cond) ? (void)0 : __builtin_unreachable()`
  - MSVC: `__assume(cond)`
- **用途**: 优化提示,帮助编译器生成更高效的代码
- **警告**: 如果假设不成立,行为未定义

### 核心断言宏

#### `SkASSERT(cond)`
- **功能**: 调试模式断言
- **行为**:
  - 调试模式: 如果 `cond` 为假,打印错误信息并中止
  - 发布模式: 编译为空操作,`cond` 不被求值
- **使用场景**: 验证内部不变量和前提条件

#### `SkASSERTF(cond, fmt, ...)`
- **功能**: 带格式化消息的调试断言
- **参数**:
  - `cond` - 条件表达式
  - `fmt` - printf 风格的格式字符串
  - `...` - 格式参数
- **示例**: `SkASSERTF(x > 0, "x must be positive, got %d", x)`

#### `SkASSERT_RELEASE(cond)`
- **功能**: 发布模式断言,始终检查
- **行为**: 无论调试还是发布模式,条件为假时中止程序
- **使用场景**: 关键的安全检查,不能在发布版本中省略

#### `SkASSERTF_RELEASE(cond, fmt, ...)`
- **功能**: 带格式化消息的发布模式断言
- **行为**: 类似 SkASSERT_RELEASE,但提供详细错误信息

### 调试失败宏

#### `SkDEBUGFAIL(message)`
- **功能**: 无条件触发调试断言失败
- **参数**: `message` - 错误消息字符串
- **行为**:
  - 调试模式: 打印消息并中止
  - 发布模式: 空操作
- **使用场景**: 标记不应到达的代码路径

#### `SkDEBUGFAILF(fmt, ...)`
- **功能**: 带格式化消息的无条件调试失败
- **参数**: printf 风格的格式字符串和参数

#### `SkAssertResult(cond)`
- **功能**: 断言表达式结果,但在发布模式中仍求值表达式
- **行为**:
  - 调试模式: 等价于 `SkASSERT(cond)`
  - 发布模式: 求值 `cond` 但忽略结果
- **使用场景**: 检查具有副作用的函数调用结果
- **示例**: `SkAssertResult(file.open())`

### 不可达代码标记

#### `SkUNREACHABLE`
- **功能**: 标记不可达的代码路径
- **实现**:
  - MSVC: `__fastfail(FAST_FAIL_INVALID_ARG)`
  - 其他: `__builtin_trap()`
- **行为**: 触发快速失败,生成陷阱指令
- **使用场景**: switch 语句的默认分支、逻辑上不可能的路径

### 错误处理宏

#### `SK_ABORT(message, ...)`
- **功能**: 打印错误信息并中止程序
- **参数**: printf 风格的格式字符串和参数
- **行为**:
  1. 打印文件名和行号
  2. 打印格式化消息
  3. 在 Google3 环境中打印堆栈跟踪
  4. 调用 `sk_abort_no_print()` 中止程序

## 公共 API 函数

### `[[noreturn]] SK_API extern void sk_abort_no_print(void)`
- **功能**: 无消息地中止程序
- **返回值**: 不返回([[noreturn]] 属性)
- **说明**: 平台实现必须抛出异常或以其他方式退出

### 集合边界检查函数

#### `template <typename T> SK_API inline T sk_collection_check_bounds(T i, T size)`
- **功能**: 检查索引是否在有效范围内
- **参数**:
  - `i` - 索引值
  - `size` - 集合大小
- **返回值**: 有效时返回 `i`,无效时中止
- **条件**: `0 <= i && i < size`
- **优化**: 使用 `SK_LIKELY` 标记正常路径

#### `[[noreturn]] SK_API inline void sk_print_index_out_of_bounds(size_t i, size_t size)`
- **功能**: 打印索引越界错误并中止
- **参数**:
  - `i` - 越界的索引
  - `size` - 集合大小

#### `template <typename T> SK_API inline T sk_collection_check_length(T i, T size)`
- **功能**: 检查长度是否在有效范围内
- **参数**:
  - `i` - 长度值
  - `size` - 集合大小
- **返回值**: 有效时返回 `i`,无效时中止
- **条件**: `0 <= i && i <= size` (注意包含 size)

#### `[[noreturn]] SK_API inline void sk_print_length_too_big(size_t i, size_t size)`
- **功能**: 打印长度过大错误并中止

#### `SK_API inline void sk_collection_not_empty(bool empty)`
- **功能**: 检查集合非空
- **参数**: `empty` - 集合是否为空的标志
- **行为**: 如果为空则中止程序

#### `template <typename T> SK_ALWAYS_INLINE size_t check_size_bytes_too_big(size_t size)`
- **功能**: 检查元素数量是否导致字节数溢出
- **参数**: `size` - 元素数量
- **返回值**: 有效时返回 `size`,溢出时中止
- **最大值**: `std::numeric_limits<size_t>::max() / sizeof(T)`

## 内部实现细节

### 断言实现策略
```cpp
#if defined(__clang__)
#define SkASSERT_RELEASE(cond) \
    static_cast<void>( __builtin_expect(static_cast<bool>(cond), 1) \
        ? static_cast<void>(0) \
        : []{ SK_ABORT("check(%s)", #cond); }() )
#else
#define SkASSERT_RELEASE(cond) \
    static_cast<void>( (cond) ? static_cast<void>(0) : []{ SK_ABORT("check(%s)", #cond); }() )
#endif
```

**关键点**:
- 使用 lambda 表达式延迟错误处理
- `__builtin_expect` 提供分支预测提示
- `static_cast<void>` 使其可作为表达式使用
- 支持 constexpr 上下文

### 平台特定行为

**Windows (MSVC)**:
```cpp
#define SK_DUMP_LINE_FORMAT "%s(%d)"  // 兼容 Visual Studio 错误导航
```

**其他平台**:
```cpp
#define SK_DUMP_LINE_FORMAT "%s:%d"  // 标准格式
```

**Google3 环境**:
- 自动打印堆栈跟踪
- 使用 `base::DumpStackTrace`

### constexpr 兼容性
断言宏设计为可在 constexpr 函数中使用:
```cpp
constexpr int foo(int x) {
    return SkASSERT(x > 0), x - 1;  // 逗号表达式
}
```

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkAPI.h | SK_API 宏 |
| include/private/base/SkAttributes.h | SK_ALWAYS_INLINE 等属性宏 |
| include/private/base/SkDebug.h | SkDebugf 调试输出 |
| <cstddef> | size_t 类型 |
| <limits> | std::numeric_limits |

### 被依赖的模块
几乎所有 Skia 模块:
- 核心绘图 API
- 图像编解码器
- GPU 后端
- 文本渲染
- 路径操作

## 设计模式与设计决策

### 零开销调试断言
- 调试模式: 完整检查
- 发布模式: 完全优化掉
- 通过条件编译实现

### 分支预测优化
使用 `SK_LIKELY` 和 `__builtin_expect`:
- 优化正常执行路径
- 将错误处理代码移到冷路径
- 提高指令缓存效率

### 表达式友好
断言可以作为表达式使用:
```cpp
return SkASSERT(ptr), *ptr;  // 断言后使用
```

### 编译器假设
`SK_ASSUME` 允许编译器进行激进优化:
```cpp
SK_ASSUME(ptr != nullptr);
// 编译器可以省略后续的空指针检查
```

## 性能考量

### 调试模式开销
- 每个断言增加一次条件检查
- 失败路径包含格式化和输出
- 可接受的调试开销

### 发布模式零开销
```cpp
#define SkASSERT(cond) static_cast<void>(0)
```
- 编译器完全移除代码
- 不求值条件表达式
- 不影响发布性能

### 分支预测
```cpp
if (0 <= i && i < size) SK_LIKELY {
    return i;
}
SK_UNLIKELY {
    // 错误处理
}
```
- 帮助 CPU 分支预测器
- 减少分支误预测惩罚
- 提高热路径性能

### 内联优化
- `SK_ALWAYS_INLINE` 强制内联关键检查函数
- 减少函数调用开销
- 允许编译器优化

## 使用场景

### 前提条件检查
```cpp
void drawRect(const SkRect& rect) {
    SkASSERT(!rect.isEmpty());
    SkASSERT(rect.isFinite());
    // ...
}
```

### 不变量验证
```cpp
class Buffer {
    void checkInvariants() {
        SkASSERT(fSize <= fCapacity);
        SkASSERT(fData != nullptr || fCapacity == 0);
    }
};
```

### 索引边界检查
```cpp
T& operator[](int i) {
    return fArray[sk_collection_check_bounds(i, fCount)];
}
```

### 不可达路径
```cpp
switch (type) {
    case Type::kA: /* ... */ break;
    case Type::kB: /* ... */ break;
    default: SkUNREACHABLE;
}
```

### 副作用函数检查
```cpp
SkAssertResult(pthread_mutex_init(&mutex, nullptr) == 0);
// 发布模式仍会调用 pthread_mutex_init
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkDebug.h | 提供 SkDebugf |
| include/private/base/SkAttributes.h | 提供属性宏 |
| src/ports/SkDebug_*.cpp | 平台特定的 sk_abort_no_print 实现 |

## 注意事项

### 副作用
调试断言的条件在发布模式中不求值:
```cpp
// 错误!发布模式不会调用 foo()
SkASSERT(foo() > 0);

// 正确:使用 SkAssertResult
SkAssertResult(foo() > 0);
```

### 线程安全
- 断言本身是线程安全的
- 但错误输出可能交错
- 不依赖断言顺序进行同步

### 异常与断言
- Skia 不使用 C++ 异常
- 断言失败通过 abort 终止程序
- 不会抛出异常

### 性能关键路径
发布模式断言有开销:
```cpp
// 热路径避免使用
SkASSERT_RELEASE(expensive_check());

// 使用条件编译或假设
#ifdef SK_DEBUG
    SkASSERT(cheap_check());
#else
    SK_ASSUME(cheap_check());
#endif
```
