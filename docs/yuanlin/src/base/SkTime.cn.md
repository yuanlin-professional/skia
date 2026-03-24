# SkTime

> 源文件: src/base/SkTime.h, src/base/SkTime.cpp

## 概述

`SkTime` 是 Skia 中提供跨平台单调时钟(monotonic clock)功能的轻量级时间工具模块。它封装了平台相关的高精度时间获取接口,提供纳秒、毫秒和秒三种时间单位的查询函数。该模块主要用于性能测量、动画计时和调试分析。

单调时钟的特点是时间值只增不减,不受系统时钟调整的影响,因此特别适合用于计算时间间隔和性能基准测试。

## 架构位置

```
src/base/
├── SkTime.h             // 时间工具接口
├── SkTime.cpp           // 平台相关实现
└── (其他基础工具)
    ↓
src/core/
├── SkCanvas.cpp         // 使用时间进行性能统计
└── SkAnimTimer.h        // 动画计时器
```

该模块位于基础设施层的底层,为动画系统、性能分析工具和基准测试提供时间服务。

## 主要类与结构体

### 命名空间 SkTime

所有功能封装在 `SkTime` 命名空间中,采用纯函数接口设计。

**无类定义,仅提供静态函数接口。**

## 公共 API 函数

### 时间获取函数

| 函数签名 | 功能说明 |
|---------|---------|
| `double GetNSecs()` | 获取当前单调时钟时间,单位为纳秒(ns) |
| `double GetSecs()` | 获取当前单调时钟时间,单位为秒(s) |
| `double GetMSecs()` | 获取当前单调时钟时间,单位为毫秒(ms) |

**返回值说明**:
- 返回的是从某个固定时间点开始的相对时间
- 不同调用返回的时间差才有实际意义
- 使用 `double` 类型保证足够的精度和范围

## 内部实现细节

### 平台相关实现

模块根据编译环境选择不同的底层实现:

**标准 C++ 实现** (默认):
```cpp
auto now = std::chrono::steady_clock::now();
std::chrono::duration<double, std::nano> ns = now.time_since_epoch();
return ns.count();
```

**Memory Sanitizer 特殊处理**:
```cpp
#if __has_feature(memory_sanitizer)
struct timespec tp;
clock_gettime(CLOCK_MONOTONIC, &tp);
return tp.tv_sec * 1e9 + tp.tv_nsec;
#endif
```

由于 Memory Sanitizer (MSan) 与 C++ `<chrono>` 库存在兼容性问题(参见 skbug.com/40037711),在 MSan 环境下回退到 POSIX 的 `clock_gettime` 实现。

### 单位转换设计

`GetSecs()` 和 `GetMSecs()` 通过内联函数实现单位转换:
```cpp
inline double GetSecs() { return GetNSecs() * 1e-9; }   // 纳秒 → 秒
inline double GetMSecs() { return GetNSecs() * 1e-6; }  // 纳秒 → 毫秒
```

这种设计的优点:
- **统一实现**: 只需维护一个平台相关的函数
- **编译器优化**: 内联函数避免函数调用开销
- **精度保证**: 从高精度向低精度转换,避免精度损失

### 时钟选择

模块使用 `std::chrono::steady_clock`,其特性:
- **单调性**: 时间只增不减
- **不可调整**: 不受系统时间修改影响
- **高精度**: 通常精度达到纳秒级(取决于平台)

在 POSIX 系统上,`CLOCK_MONOTONIC` 提供类似保证。

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| chrono (C++11) | 提供跨平台的时钟接口 |
| time.h (POSIX) | Memory Sanitizer 环境下使用 |
| ratio (C++11) | 时间单位转换 |

**被依赖的模块:**

| 模块 | 使用场景 |
|------|---------|
| tools/timer/ | 性能基准测试工具 |
| src/animator/ | 动画系统计时 |
| tests/ | 单元测试中的时间测量 |
| dm/ (Drawing Manager) | 渲染性能分析 |

## 设计模式与设计决策

### 纯函数接口

模块采用无状态的纯函数设计:
- **线程安全**: 多线程可以并发调用
- **简单直接**: 无需创建对象或管理状态
- **易于测试**: 函数行为可预测

### 单一职责原则

模块只负责获取单调时钟时间,不提供:
- 日期和时间格式化
- 时区转换
- 定时器或延迟功能
- 时间解析

这些功能由上层模块或标准库提供。

### 内联优化

单位转换函数使用 `inline` 关键字:
- 避免函数调用开销
- 编译器可以进一步优化乘法运算
- 生成的代码与直接调用 `GetNSecs()` 并转换的代码相同

### 平台抽象

通过条件编译隔离平台差异:
```cpp
#if __has_feature(memory_sanitizer)
    // 使用 POSIX 实现
#else
    // 使用 C++11 标准库
#endif
```

这种设计使得代码在不同平台和编译配置下都能正常工作。

## 性能考量

### 时钟精度

不同平台的精度差异:
- **Linux**: `CLOCK_MONOTONIC` 通常提供纳秒级精度
- **macOS**: `mach_absolute_time()` 包装在 `steady_clock` 中,纳秒级
- **Windows**: `QueryPerformanceCounter()` 包装在 `steady_clock` 中,高精度

### 性能开销

**调用开销**:
- `GetNSecs()`: 通常对应一次系统调用或特殊指令(如 x86 的 RDTSC)
- `GetSecs()` / `GetMSecs()`: 额外一次浮点乘法,可内联优化

**典型调用时间**:
- 现代 x86/ARM 处理器: 20-100 纳秒
- 系统调用路径(如 `clock_gettime`): 可能达到几百纳秒

### 使用建议

1. **避免高频调用**: 不要在紧密循环中频繁调用
2. **批量测量**: 测量较大的时间间隔以提高精度
3. **缓存结果**: 同一帧内可以缓存时间值

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| include/private/base/SkThreadID.h | 线程标识,常与时间配合用于并发分析 |
| tools/timer/Timer.h | 基于 SkTime 的计时器工具 |
| src/utils/SkAnimCodecPlayer.h | 动画播放器,使用时间控制帧率 |
| bench/Benchmark.cpp | 基准测试框架,依赖时间测量 |

## 使用示例

```cpp
// 示例 1: 测量代码执行时间(纳秒)
double start = SkTime::GetNSecs();
performHeavyComputation();
double end = SkTime::GetNSecs();
double elapsedNs = end - start;
SkDebugf("Elapsed: %.2f ns\n", elapsedNs);

// 示例 2: 测量代码执行时间(毫秒)
double startMs = SkTime::GetMSecs();
renderFrame();
double endMs = SkTime::GetMSecs();
double elapsedMs = endMs - startMs;
SkDebugf("Frame time: %.2f ms\n", elapsedMs);

// 示例 3: 计算帧率
double frameStart = SkTime::GetSecs();
while (running) {
    double currentTime = SkTime::GetSecs();
    double deltaTime = currentTime - frameStart;

    if (deltaTime >= targetFrameTime) {
        updateAndRender(deltaTime);
        frameStart = currentTime;
    }
}

// 示例 4: 性能基准测试
constexpr int iterations = 1000;
double start = SkTime::GetNSecs();
for (int i = 0; i < iterations; ++i) {
    functionUnderTest();
}
double end = SkTime::GetNSecs();
double avgTimeNs = (end - start) / iterations;
SkDebugf("Average time per iteration: %.2f ns\n", avgTimeNs);

// 示例 5: 超时检测
double timeout = SkTime::GetMSecs() + 5000;  // 5 秒超时
while (condition && SkTime::GetMSecs() < timeout) {
    doWork();
}
if (SkTime::GetMSecs() >= timeout) {
    SkDebugf("Operation timed out\n");
}
```

## 注意事项

1. **相对时间**: 返回值的绝对值无意义,只有时间差才有意义
2. **不保证起始点**: 不同进程或程序运行的起始时间点可能不同
3. **精度限制**: 虽然返回纳秒级数值,但实际精度取决于硬件和操作系统
4. **浮点误差**: 使用 `double` 存储纳秒值,超大值可能损失精度
5. **不适合日期时间**: 此模块只用于计时,不用于获取当前日期时间
6. **Memory Sanitizer 行为**: 在 MSan 环境下使用不同实现,可能有细微差异
7. **时间回退**: 虽然是单调时钟,但系统休眠可能影响时间计数

## 扩展阅读

- C++11 `<chrono>` 库文档
- POSIX `clock_gettime` 函数规范
- 关于 skbug.com/40037711 的 Memory Sanitizer 兼容性问题

## 设计哲学

`SkTime` 模块体现了 Skia 的设计哲学:
- **最小化**: 仅提供必需的功能
- **跨平台**: 统一接口,平台差异由内部处理
- **高性能**: 轻量级实现,低开销
- **实用主义**: 针对常见用例(性能测量)优化
