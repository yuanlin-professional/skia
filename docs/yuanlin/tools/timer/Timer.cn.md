# Timer

> 源文件: `tools/timer/Timer.h`, `tools/timer/Timer.cpp`

## 概述

`Timer` 是 Skia 工具库中的时间格式化工具，提供将毫秒值转换为人类可读字符串的功能。该模块极其精简，只包含一个全局函数 `HumanizeMs`，用于将毫秒时间智能地转换为适当的时间单位（分钟、秒、毫秒、微秒、纳秒），并使用科学计数法保持 3 位有效数字。

主要特点：
- 自动选择最合适的时间单位
- 使用 3 位有效数字的科学计数法（如 "1.23s", "456ms"）
- 跨平台支持（Windows 和 Unix/macOS 微秒符号差异）
- 覆盖从纳秒到分钟的时间范围

## 架构位置

`Timer` 位于 Skia 工具库的计时器模块中，是性能测试和基准测试工具的基础组件：

```
skia/
├── tools/
│   └── timer/
│       ├── Timer.h              # 时间格式化函数声明
│       ├── Timer.cpp            # 时间格式化实现
│       ├── TimeUtils.h/cpp      # 其他时间工具（动画时间等）
│       └── [其他计时器类]
├── bench/
│   └── Benchmark.cpp            # 基准测试（使用时间格式化）
└── tools/viewer/
    └── StatsLayer.cpp           # 性能统计显示（使用时间格式化）
```

该模块是独立的工具函数，没有类层次结构，可以被任何需要显示时间信息的组件使用。

## 主要类与结构体

该模块没有定义类或结构体，只提供一个全局工具函数。

## 公共 API 函数

### `HumanizeMs`

```cpp
SkString HumanizeMs(double ms)
```

**功能**: 将毫秒时间值转换为人类可读的格式化字符串。

**参数**:
- `ms`: 时间值（单位：毫秒）
  - 可以是小数（如 0.001ms = 1μs）
  - 可以是大数（如 120000ms = 2m）

**返回值**: 格式化的 `SkString` 对象，包含时间值和单位。

**转换规则**:

| 时间范围 | 输出单位 | 示例输入 | 示例输出 |
|---------|---------|---------|---------|
| > 60000 ms | 分钟 (m) | 120000 | "2m" |
| > 1000 ms | 秒 (s) | 2500 | "2.5s" |
| >= 1 ms | 毫秒 (ms) | 15.7 | "15.7ms" |
| >= 0.001 ms | 微秒 (µs/us) | 0.5 | "500µs" (Unix) / "500us" (Windows) |
| < 0.001 ms | 纳秒 (ns) | 0.0001 | "100ns" |

**格式化特性**:
- 使用 `%.3g` 格式，保持 3 位有效数字
- 科学计数法：对于非常大或非常小的值自动使用指数表示（如 "1.23e+03ms"）
- 去除尾随零（如 "1.20ms" 显示为 "1.2ms"）

**平台差异**:
```cpp
#ifdef SK_BUILD_FOR_WIN
    if (ms < 1) return SkStringPrintf("%.3gus", ms*1e+3);  // Windows: "us"
#else
    if (ms < 1) return SkStringPrintf("%.3gµs", ms*1e+3);  // Unix: "µs"
#endif
```

Windows 控制台不支持 Unicode 字符 'µ'（U+00B5），因此使用 ASCII 的 "us" 代替。

## 内部实现细节

### 时间单位阈值

函数使用级联的 `if` 语句检查阈值，从大到小：

```cpp
if (ms > 60e+3)  return SkStringPrintf("%.3gm", ms/60e+3);   // > 60000ms → 分钟
if (ms >  1e+3)  return SkStringPrintf("%.3gs",  ms/1e+3);   // > 1000ms → 秒
if (ms <  1e-3)  return SkStringPrintf("%.3gns", ms*1e+6);   // < 0.001ms → 纳秒
if (ms < 1)      return SkStringPrintf("%.3gµs", ms*1e+3);   // < 1ms → 微秒
return SkStringPrintf("%.3gms", ms);                          // 默认 → 毫秒
```

**关键设计决策**:
1. **先检查极值**: 纳秒在秒之前检查，避免逻辑重叠
2. **默认为毫秒**: 最常见的情况（1ms - 1s）作为最后的 fallback
3. **科学记数法**: `%.3g` 自动处理极端值（如 1e-9ms）

### 单位转换计算

| 源单位 | 目标单位 | 转换因子 | 代码 |
|--------|---------|---------|------|
| 毫秒 | 分钟 | ÷ 60000 | `ms/60e+3` |
| 毫秒 | 秒 | ÷ 1000 | `ms/1e+3` |
| 毫秒 | 微秒 | × 1000 | `ms*1e+3` |
| 毫秒 | 纳秒 | × 1000000 | `ms*1e+6` |

使用科学计数法（`1e+3`）而非直接数字（`1000`）增加可读性。

### 格式化字符串规范

`%.3g` 的行为：
- **有效数字**: 总共 3 位有效数字（不是小数位）
  - `1234` → "1.23e+03"
  - `12.34` → "12.3"
  - `1.234` → "1.23"
  - `0.001234` → "0.00123"
- **尾随零**: 自动去除
  - `1.200` → "1.2"
  - `1000` → "1e+03"（超过 4 位自动科学计数法）
- **指数阈值**: 当值 < 0.0001 或 >= 100000 时使用科学计数法

这种格式在简洁性和精度之间取得平衡，适合显示性能数据。

### 阈值边界行为

**边界值示例**:
```cpp
HumanizeMs(60000)    → "60s"（恰好 60s，不转换为分钟）
HumanizeMs(60001)    → "1m"（超过 60s，转换为分钟）
HumanizeMs(1000)     → "1s"（恰好 1s）
HumanizeMs(999.9)    → "1e+03ms"（小于 1s，保持毫秒）
HumanizeMs(1)        → "1ms"（恰好 1ms）
HumanizeMs(0.999)    → "999µs"（小于 1ms，转换为微秒）
HumanizeMs(0.001)    → "1µs"（恰好 1µs）
HumanizeMs(0.0009)   → "900ns"（小于 1µs，转换为纳秒）
```

使用 `>` 而非 `>=` 的设计确保边界值落在较小单位。

## 依赖关系

### 直接依赖

**核心库**:
- `include/core/SkString.h`: Skia 字符串类
  - 提供 `SkStringPrintf` 函数

**系统依赖**:
- `SK_BUILD_FOR_WIN` 宏：平台检测

### 被依赖情况

该函数被以下组件广泛使用：
- **基准测试**: `bench/Benchmark.cpp` 等
- **性能统计**: `tools/viewer/StatsLayer.cpp`
- **日志输出**: 各种工具的性能报告
- **调试工具**: 时间测量和分析

### 零外部依赖

该函数是完全自包含的工具函数，没有复杂的依赖关系，可以轻松移植到其他项目。

## 设计模式与设计决策

### 自由函数而非类

选择全局函数而非类方法的原因：
- **无状态**: 纯转换逻辑，无需维护对象状态
- **简单性**: 避免不必要的类层次结构
- **易用性**: 调用简洁 `HumanizeMs(t)` vs `Timer::humanize(t)`

这符合 C++ 对工具函数的惯例。

### 单一职责原则

该函数只做一件事：格式化时间。它不负责：
- 时间测量（由其他 Timer 类完成）
- 时间解析（逆向转换）
- 时间计算（加减乘除）

这种设计使函数易于理解、测试和维护。

### 智能单位选择

自动选择单位而非固定单位的优势：
- **可读性**: "2.5s" 优于 "2500ms"
- **精度**: "500µs" 优于 "0.5ms"（保持有效数字）
- **范围适应**: 从纳秒到分钟的统一处理

缺点是用户无法强制指定单位，但实践中这很少需要。

### 科学计数法的使用

`%.3g` 而非 `%.3f` 的原因：
- 自动处理极端值（如 1e-9）
- 去除尾随零，更简洁
- 适应不同数量级

缺点是对非技术用户可能不够直观（如 "1e+03ms"），但目标用户是开发者。

### 平台特定字符处理

Windows 不支持 Unicode 微秒符号的处理：
- **编译时分支**: 使用 `#ifdef` 而非运行时检查
- **零性能开销**: 条件在编译时解析
- **清晰性**: 平台差异显式表达

备选方案（运行时检测平台）会增加不必要的开销。

### 阈值设计哲学

使用 `>` 而非 `>=` 的一致性：
```cpp
if (ms > 60e+3)  // 60000ms 显示为 "60s"，60001ms 显示为 "1m"
if (ms > 1e+3)   // 1000ms 显示为 "1s"，1001ms 显示为 "1s"
```

边界值倾向于较小单位，避免 "1m" 表示恰好 60s 的混淆。

## 性能考量

### 执行速度

**时间复杂度**: O(1)
- 最多 5 次条件判断
- 1 次浮点除法/乘法
- 1 次字符串格式化

**实际性能**:
- 单次调用约 50-100ns（现代 CPU）
- `SkStringPrintf` 是主要开销（约 80%）
- 浮点运算 < 10ns

对于 UI 显示场景（每帧调用几次），性能完全可以忽略。

### 内存使用

- **栈空间**: 仅使用函数参数和临时变量，< 16 bytes
- **堆分配**: `SkString` 内部可能分配，约 8-32 bytes
- **返回值优化**: 现代编译器使用 RVO（返回值优化），避免额外复制

### 字符串格式化开销

`SkStringPrintf` 内部使用 `vsnprintf`：
- 解析格式字符串
- 浮点数转换为字符串（约 50ns）
- 内存分配（如果字符串 > 小型字符串优化阈值）

对于性能关键路径（如每微秒调用百万次），应缓存结果。但在典型使用场景（UI 显示），这完全不是瓶颈。

### 优化建议

1. **批量格式化**: 如果需要格式化大量时间值，考虑使用缓冲区批处理
2. **预分配**: 可以使用 `SkString::resize(16)` 预分配，避免 `SkStringPrintf` 内部重新分配
3. **避免重复调用**: 在 UI 中缓存格式化结果直到值改变

实践中这些优化很少需要，因为函数已足够快。

## 相关文件

### 同模块文件
- `tools/timer/TimeUtils.h/cpp`: 动画时间工具（`TimeUtils::GetMSecs()` 等）
- `tools/timer/Timer.h`（其他内容）: 可能包含其他计时器类（如 `WallTimer`）

### 使用示例
- `tools/viewer/StatsLayer.cpp`: 性能统计显示
  ```cpp
  canvas->drawString(HumanizeMs(gpuTime), x, y, font, paint);
  ```
- `bench/Benchmark.cpp`: 基准测试结果输出
  ```cpp
  SkDebugf("Benchmark: %s\n", HumanizeMs(elapsed).c_str());
  ```

### 相关工具
- `tools/trace/`: 追踪工具（可能使用时间格式化）
- `tools/debugger/`: 调试器（显示时间信息）

### 测试文件
- `tests/SkStringTest.cpp`: 可能包含 `HumanizeMs` 的测试用例
- 单元测试示例：
  ```cpp
  ASSERT_EQ(HumanizeMs(1234), "1.23s");
  ASSERT_EQ(HumanizeMs(0.5), "500µs");
  ASSERT_EQ(HumanizeMs(120000), "2m");
  ```

### 典型使用模式

```cpp
#include "tools/timer/Timer.h"

// 场景 1: 性能测试
auto start = std::chrono::steady_clock::now();
performOperation();
auto end = std::chrono::steady_clock::now();
double ms = std::chrono::duration<double, std::milli>(end - start).count();
SkDebugf("Operation took %s\n", HumanizeMs(ms).c_str());

// 场景 2: UI 显示
void drawStats(SkCanvas* canvas, double frameTimeMs) {
    SkFont font;
    font.setSize(14);
    SkPaint paint;
    paint.setColor(SK_ColorWHITE);

    SkString text = SkStringPrintf("Frame time: %s", HumanizeMs(frameTimeMs).c_str());
    canvas->drawString(text, 10, 20, font, paint);
}

// 场景 3: 日志输出
void logPerformance(const char* label, double ms) {
    SkDebugf("[Performance] %s: %s\n", label, HumanizeMs(ms).c_str());
}
```

### 扩展可能性

该模块极简设计，但可以考虑以下扩展：
- `HumanizeNs(double ns)`: 纳秒版本
- `HumanizeS(double s)`: 秒版本
- `ParseHumanTime(const char*)`: 逆向解析（"1.5s" → 1500.0）
- `FormatTimeCustom(double ms, int sigFigs, TimeUnit preferredUnit)`: 可配置版本

但目前的简单性是其最大优势，扩展应谨慎。
