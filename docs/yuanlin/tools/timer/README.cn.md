# Skia Timer 计时工具

## 概述

`tools/timer` 提供了 Skia 工具和基准测试中使用的时间相关工具函数。该模块包含时间格式化工具（`Timer`）和时间数学工具（`TimeUtils`），被广泛用于基准测试结果展示、动画时间控制和性能测量。

## 目录结构

```
tools/timer/
├── BUILD.bazel    # Bazel 构建配置
├── Timer.h        # 时间格式化函数声明
├── Timer.cpp      # 时间格式化函数实现
└── TimeUtils.h    # 时间数学工具函数（纯头文件库）
```

## 核心组件

### Timer (Timer.h / Timer.cpp)

提供毫秒时间值的人类可读格式化：

```cpp
SkString HumanizeMs(double ms);
```

将毫秒值转换为人类友好的字符串表示，例如：
- `0.5` -> `"500us"`
- `1.5` -> `"1.50ms"`
- `1500` -> `"1.50s"`

### TimeUtils (TimeUtils.h)

纯头文件的时间数学工具库，提供以下功能：

#### 类型定义

```cpp
using MSec = uint32_t;                      // 32 位毫秒类型
static constexpr MSec MSecMax = INT32_MAX;  // 最大可表示毫秒值（约 24 天 20 小时）
```

#### 时间转换

| 函数 | 说明 |
|------|------|
| `NanosToMSec(nanos)` | 纳秒转毫秒 |
| `NanosToSeconds(nanos)` | 纳秒转秒 |

#### 动画时间函数

**Scaled - 缩放时间**

```cpp
static float Scaled(float time, float speed, float period = 0);
```

按速度缩放时间值，可选按周期取模。用于控制动画播放速度和循环。

**PingPong - 往返线性动画**

```cpp
static float PingPong(double time, float period, float phase, float ends, float mid);
```

在 `ends` 和 `mid` 之间进行线性往返过渡：
- `time`: 当前时间
- `period`: 往返周期
- `phase`: 相位偏移
- `ends/mid`: 端点值和中间值

**SineWave - 正弦波动画**

```cpp
static float SineWave(double time, float periodInSecs, float phaseInSecs, float min, float max);
```

生成在 `min` 和 `max` 之间的正弦波动画值：
- 使用纳秒精度时间输入
- 周期和相位以秒为单位
- 返回 `[min, max]` 范围内的平滑波动值
- 若周期为负，返回中间值（静止状态）

## 使用示例

### 基准测试时间格式化

```cpp
#include "tools/timer/Timer.h"

double elapsed_ms = 1234.5;
SkString formatted = HumanizeMs(elapsed_ms);
// 输出类似 "1.23s"
```

### 动画时间控制

```cpp
#include "tools/timer/TimeUtils.h"

// 创建一个 2 秒周期的正弦波动画，值在 0 到 100 之间
float value = TimeUtils::SineWave(currentTimeNanos, 2.0f, 0.0f, 0.0f, 100.0f);

// 创建一个 3 秒周期的 PingPong 动画
float alpha = TimeUtils::PingPong(currentTimeNanos, 3.0f, 0.0f, 0.0f, 1.0f);
```

## 设计特点

- **TimeUtils 完全内联**: 所有函数都在头文件中定义，无运行时链接开销
- **纳秒精度**: 内部以纳秒为时间单位，确保高精度时间运算
- **溢出保护**: `NanosToMSec` 包含断言检查，防止超出 `MSecMax` 范围

## 与其他模块的关系

- **bench/**: nanobench 使用 Timer 格式化基准测试结果
- **tools/viewer/**: Viewer 应用使用 TimeUtils 控制动画回放
- **gm/**: 动画 GM 测试使用 TimeUtils 计算帧时间
- **tools/skpbench/**: SKP 基准测试使用计时功能
- **modules/skottie/**: Skottie 动画引擎使用时间工具进行帧时间计算
