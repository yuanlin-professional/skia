# SkDebug

> 源文件: `include/private/base/SkDebug.h`

## 概述
SkDebug 提供了 Skia 的调试输出基础设施,定义了跨平台的调试打印函数 SkDebugf 和相关的调试宏。它统一了不同平台上的调试输出接口,支持格式化输出,并在调试和发布模式下有不同的行为。

## 架构位置
该头文件位于 Skia 基础设施层的调试支持子系统,是调试输出的核心接口。几乎所有需要调试信息输出的 Skia 模块都依赖此文件,它与 SkAssert.h 一起构成了 Skia 的调试基础设施。

## 主要函数和宏

### 核心调试函数

#### `SkDebugf`
```cpp
#if !defined(SkDebugf)
    void SK_SPI SkDebugf(const char format[], ...) SK_PRINTF_LIKE(1, 2);
#endif
```

**功能**: 跨平台的调试输出函数,类似于 printf

**特点**:
- **格式化输出**: 支持 printf 风格的格式字符串
- **平台适配**: 在不同平台上输出到合适的调试输出流
- **编译时检查**: 使用 SK_PRINTF_LIKE(1, 2) 进行格式字符串检查
- **可覆盖**: 允许用户自定义实现(通过预定义宏)

**参数**:
- `format`: printf 风格的格式字符串
- `...`: 可变参数列表,对应格式字符串中的占位符

**平台行为**:
- **Windows**: 输出到 OutputDebugString (Visual Studio 调试器可见)
- **Android**: 输出到 Android logcat
- **iOS/macOS**: 输出到 NSLog 或 stderr
- **Linux/Unix**: 输出到 stderr

**示例**:
```cpp
SkDebugf("Drawing rect at (%d, %d)\n", x, y);
SkDebugf("Color: 0x%08X\n", color);
SkDebugf("Performance: %.2f ms\n", elapsed);
```

**与 printf 的区别**:
- 输出到平台特定的调试通道
- 在某些平台上可能被重定向或过滤
- 专为调试设计,不用于生产日志

## 条件编译宏

### SK_DEBUG 模式宏

#### `SkDEBUGCODE(...)`
```cpp
#if defined(SK_DEBUG)
    #define SkDEBUGCODE(...)  __VA_ARGS__
#else
    #define SkDEBUGCODE(...)
#endif
```

**功能**: 条件编译调试代码

**行为**:
- **调试模式** (SK_DEBUG 定义): 展开为传入的代码
- **发布模式**: 完全移除,不生成任何代码

**使用场景**:
- 调试专用的变量和函数
- 运行时验证和检查
- 调试辅助代码

**示例**:
```cpp
class MyClass {
    int fData;
    SkDEBUGCODE(int fDebugCounter = 0;)  // 仅在调试模式存在

public:
    void doSomething() {
        SkDEBUGCODE(++fDebugCounter;)
        // 主要逻辑
    }

    SkDEBUGCODE(
        void validate() const {
            SkASSERT(fDebugCounter >= 0);
        }
    )
};
```

**多行代码**:
```cpp
SkDEBUGCODE(
    int debug_var = 0;
    for (int i = 0; i < count; ++i) {
        debug_var += array[i];
    }
    SkDebugf("Sum: %d\n", debug_var);
)
```

#### `SkDEBUGF(...)`
```cpp
#if defined(SK_DEBUG)
    #define SkDEBUGF(...)     SkDebugf(__VA_ARGS__)
#else
    #define SkDEBUGF(...)
#endif
```

**功能**: 条件调试输出

**行为**:
- **调试模式**: 调用 SkDebugf
- **发布模式**: 完全移除

**优势**:
- 避免手动 #ifdef 包裹
- 简化代码可读性
- 零发布版本开销

**示例**:
```cpp
void processData(const Data& data) {
    SkDEBUGF("Processing data: size=%zu\n", data.size());

    // 主要逻辑
    for (size_t i = 0; i < data.size(); ++i) {
        SkDEBUGF("  [%zu] = %d\n", i, data[i]);
        process(data[i]);
    }

    SkDEBUGF("Processing complete\n");
}
```

**与 SkDEBUGCODE 的区别**:
```cpp
// 使用 SkDEBUGF
SkDEBUGF("Value: %d\n", x);

// 等价于使用 SkDEBUGCODE
SkDEBUGCODE(SkDebugf("Value: %d\n", x);)

// SkDEBUGF 更简洁,专门用于调试输出
```

## 内部实现细节

### 平台特定实现
SkDebugf 的实现在不同平台的 ports 目录中:
- `src/ports/SkDebug_win.cpp`: Windows 实现
- `src/ports/SkDebug_android.cpp`: Android 实现
- `src/ports/SkDebug_stdio.cpp`: 通用 stdio 实现

### 格式化检查
```cpp
SK_PRINTF_LIKE(1, 2)
```
- 参数 1(格式字符串)在位置 1
- 可变参数从位置 2 开始
- 编译器检查类型匹配和参数数量

### 用户自定义实现
```cpp
#if !defined(SkDebugf)
    void SK_SPI SkDebugf(const char format[], ...) SK_PRINTF_LIKE(1, 2);
#endif
```
允许用户在编译前定义自己的 SkDebugf 实现:
```cpp
// 在编译选项中或配置头文件中
#define SkDebugf my_custom_debugf
```

### SK_SPI 标记
使用 SK_SPI (Skia Private Interface) 而非 SK_API:
- 表明这是内部接口,稳定性不如公共 API
- 可能在不同版本间变化
- 主要供 Skia 内部使用

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkAPI.h | SK_SPI 宏定义 |
| include/private/base/SkAttributes.h | SK_PRINTF_LIKE 宏 |
| include/private/base/SkLoadUserConfig.h | 用户配置加载 |

### 被依赖的模块
几乎所有 Skia 模块:
- include/private/base/SkAssert.h (断言实现)
- src/ 下的所有实现文件
- 测试和示例代码
- 调试工具

## 设计模式与设计决策

### 条件编译策略
通过 SK_DEBUG 宏控制:
- 调试代码在发布版本中完全消失
- 零运行时开销
- 编译时优化,不影响性能

### 平台抽象
统一接口,平台特定实现:
- 用户代码调用 SkDebugf
- 底层根据平台输出到正确的通道
- 隔离平台差异

### 可扩展性
允许用户自定义:
- 可以重定向输出到日志文件
- 可以添加时间戳或线程 ID
- 可以集成到现有日志系统

### 宏的使用
选择宏而非函数模板:
- 在发布模式下完全移除代码
- 避免任何运行时开销(包括参数求值)
- 支持任意代码块(SkDEBUGCODE)

## 性能考量

### 发布模式零开销
```cpp
SkDEBUGF("Expensive operation: result=%d\n", expensiveFunction());
// 发布模式:expensiveFunction() 不会被调用!
```
不仅输出代码被移除,参数表达式也不求值。

### 调试模式开销
调试模式的开销:
- 格式化字符串处理
- 系统调用(输出到调试通道)
- I/O 操作
- 可接受的调试开销,不影响发布性能

### 条件编译 vs 运行时检查
```cpp
// 条件编译(推荐)
SkDEBUGF("Debug info\n");

// 运行时检查(不推荐)
if (isDebugMode()) {
    SkDebugf("Debug info\n");  // 发布版本仍有函数调用开销
}
```

## 使用场景

### 基本调试输出
```cpp
void drawRect(const SkRect& rect) {
    SkDEBUGF("drawRect: [%.2f, %.2f, %.2f, %.2f]\n",
             rect.fLeft, rect.fTop, rect.fRight, rect.fBottom);
    // ...
}
```

### 调试专用代码
```cpp
class ResourceCache {
    SkDEBUGCODE(
        int fAllocCount = 0;
        int fFreeCount = 0;
    )

public:
    void* allocate(size_t size) {
        void* ptr = malloc(size);
        SkDEBUGCODE(++fAllocCount;)
        SkDEBUGF("Allocated %zu bytes, total allocations: %d\n",
                 size, SkDEBUGCODE(fAllocCount));
        return ptr;
    }

    SkDEBUGCODE(
        void checkLeaks() const {
            if (fAllocCount != fFreeCount) {
                SkDebugf("LEAK: %d allocations, %d frees\n",
                         fAllocCount, fFreeCount);
            }
        }
    )
};
```

### 性能追踪
```cpp
void expensiveOperation() {
    SkDEBUGCODE(auto start = std::chrono::steady_clock::now();)

    // 执行操作
    performWork();

    SkDEBUGCODE(
        auto end = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
        SkDebugf("expensiveOperation took %lld ms\n", elapsed.count());
    )
}
```

### 状态转储
```cpp
class StateMachine {
public:
    SkDEBUGCODE(
        void dumpState() const {
            SkDebugf("State: %d\n", fState);
            SkDebugf("Queue size: %zu\n", fQueue.size());
            for (size_t i = 0; i < fQueue.size(); ++i) {
                SkDebugf("  [%zu] = %d\n", i, fQueue[i]);
            }
        }
    )
};
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkAssert.h | 使用 SkDebugf 输出断言信息 |
| src/ports/SkDebug_*.cpp | 平台特定的 SkDebugf 实现 |
| include/private/base/SkAttributes.h | 提供 SK_PRINTF_LIKE 宏 |

## 注意事项

### 参数求值
```cpp
// 错误:发布模式下 getIndex() 不会被调用
SkDEBUGF("Index: %d\n", getIndex());

// 正确:如果 getIndex() 有副作用,应该分离
int index = getIndex();
SkDEBUGF("Index: %d\n", index);
```

### 字符串生命周期
```cpp
// 错误:临时字符串在输出前可能被销毁
SkDEBUGF("Name: %s\n", getName().c_str());

// 正确:保持字符串生命周期
std::string name = getName();
SkDEBUGF("Name: %s\n", name.c_str());
```

### 格式字符串安全
```cpp
// 错误:用户输入作为格式字符串
SkDebugf(userInput);  // 安全漏洞!

// 正确:使用字面量格式字符串
SkDebugf("%s\n", userInput);
```

### 宏参数多重求值
```cpp
// 错误:参数可能被多次求值(虽然 SkDEBUGF 不会)
#define MY_DEBUG(x) SkDEBUGF("Value: %d\n", x)
MY_DEBUG(++counter);  // 安全,SkDEBUGF 是函数

// 但自定义宏要小心
#define BAD_DEBUG(x) if (debug) { SkDebugf("%d\n", x); SkDebugf("%d\n", x); }
BAD_DEBUG(++counter);  // counter 可能递增两次!
```

### 线程安全
- SkDebugf 通常是线程安全的(平台实现保证)
- 但输出可能交错,不要依赖顺序
- 多线程调试时考虑添加线程 ID

### 性能分析
在进行性能基准测试时:
- 使用发布构建,SkDEBUGF 会被移除
- 或显式禁用 SK_DEBUG,避免调试代码影响测量

## 最佳实践

### 适度使用
```cpp
// 好:关键操作的调试输出
SkDEBUGF("Initializing GPU context\n");

// 不好:过度的调试输出
for (int i = 0; i < 1000000; ++i) {
    SkDEBUGF("Processing item %d\n", i);  // 太多输出!
}
```

### 有意义的信息
```cpp
// 不好:信息不足
SkDEBUGF("Error\n");

// 好:提供上下文
SkDEBUGF("Failed to load texture: %s, error code: %d\n", filename, error);
```

### 层次化输出
```cpp
void complexOperation() {
    SkDEBUGF("Starting complex operation\n");

    step1();
    SkDEBUGF("  Step 1 complete\n");

    step2();
    SkDEBUGF("  Step 2 complete\n");

    SkDEBUGF("Complex operation finished\n");
}
```
