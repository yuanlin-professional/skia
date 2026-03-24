# TimeUtils.h

> 源文件: tools/timer/TimeUtils.h

## 概述

`TimeUtils.h` 是 Skia 工具库中的时间工具集，提供了一系列用于时间转换和动画计算的实用函数。该文件定义了毫秒持续时间类型，以及用于纳秒到毫秒/秒转换、时间缩放、乒乓动画、正弦波动画等常用时间相关计算的内联函数。这些工具函数广泛应用于 Skia 的动画系统、性能测试和示例应用程序中。

核心功能包括：
- 时间单位转换（纳秒 ↔ 毫秒 ↔ 秒）
- 时间缩放和周期性循环
- 乒乓（来回）动画插值
- 正弦波动画插值

## 架构位置

在 Skia 工具库中的位置：

```
tools/
  ├── timer/
  │   ├── TimeUtils.h           # 时间工具函数（本文件）
  │   └── Timer.h               # 计时器类
  ├── viewer/
  │   └── Viewer.cpp            # 使用 TimeUtils 实现动画
  └── sk_app/
      └── Application.h         # 应用程序框架

include/core/
  └── SkTypes.h                 # 核心类型定义
```

## 主要类与结构体

### MSec 类型别名

```cpp
namespace TimeUtils {
using MSec = uint32_t;
}
```

**说明**：32 位无符号整数，用于表示毫秒持续时间。

**范围**：0 到 2^32-1 毫秒
- 最大值：约 49.7 天（INT32_MAX 毫秒）
- `MSecMax`：定义为 INT32_MAX（2147483647），约 24 天 20 小时 31 分 23.647 秒

### MSecMax 常量

```cpp
static constexpr MSec MSecMax = INT32_MAX;
```

**用途**：定义可表示的最大毫秒值，用于边界检查和断言。

## 公共 API 函数

### NanosToMSec

```cpp
static inline MSec NanosToMSec(double nanos)
```

**功能**：将纳秒转换为毫秒。

**参数**：
- `nanos`：纳秒时间（双精度浮点数）

**返回值**：毫秒时间（32 位无符号整数）

**实现**：
```cpp
const double msec = nanos * 1e-6;  // 纳秒 × 10^-6 = 毫秒
SkASSERT(MSecMax >= msec);         // 断言不溢出
return static_cast<MSec>(msec);
```

**注意**：
- 如果计时器停止，返回 0
- 如果计时器运行时间超过 MSecMax，行为未定义
- 用于性能测量和动画计时

### NanosToSeconds

```cpp
static inline double NanosToSeconds(double nanos)
```

**功能**：将纳秒转换为秒。

**参数**：
- `nanos`：纳秒时间

**返回值**：秒时间（双精度浮点数）

**实现**：
```cpp
return nanos * 1e-9;  // 纳秒 × 10^-9 = 秒
```

**用途**：用于基于秒的动画计算和物理模拟。

### Scaled

```cpp
static inline float Scaled(float time, float speed, float period = 0)
```

**功能**：将时间按速度缩放，并可选地按周期取模。

**参数**：
- `time`：输入时间
- `speed`：缩放因子（速度倍数）
- `period`：可选的周期长度，0 表示不循环（默认值）

**返回值**：缩放后的时间

**实现**：
```cpp
double value = time * speed;
if (period) {
    value = ::fmod(value, (double)(period));  // 取模实现循环
}
return (float)value;
```

**使用场景**：
- 加速或减速动画：`Scaled(time, 2.0f)` 使动画速度翻倍
- 循环动画：`Scaled(time, 1.0f, 5.0f)` 创建 5 秒循环
- 时间重映射

### PingPong

```cpp
static inline float PingPong(double time,
                             float period,
                             float phase,
                             float ends,
                             float mid)
```

**功能**：在 ends 和 mid 之间线性来回插值，创建"乒乓"效果。

**参数**：
- `time`：当前时间
- `period`：完整周期长度（从 ends → mid → ends）
- `phase`：相位偏移（时间单位）
- `ends`：两端的值
- `mid`：中点的值

**返回值**：插值结果

**实现**：
```cpp
double value = ::fmod(time + phase, period);  // 加相位，取模
double half  = period / 2.0;                  // 半周期
double diff  = ::fabs(value - half);          // 到中点的距离
return (float)(ends + (1.0 - diff / half) * (mid - ends));
```

**动画曲线**：
```
值
mid  ----
     |  /\  /\
     | /  \/  \
ends |/        \___
     0    period   2*period  (时间)
```

**使用场景**：
- 来回移动的物体
- 呼吸效果（透明度、大小）
- 摆动动画

### SineWave

```cpp
static inline float SineWave(double time,
                             float periodInSecs,
                             float phaseInSecs,
                             float min,
                             float max)
```

**功能**：生成在 min 和 max 之间振荡的正弦波。

**参数**：
- `time`：当前时间（纳秒）
- `periodInSecs`：周期长度（秒），< 0 时返回中值
- `phaseInSecs`：相位偏移（秒）
- `min`：最小值
- `max`：最大值

**返回值**：正弦波插值结果

**实现**：
```cpp
if (periodInSecs < 0.f) {
    return (min + max) / 2.f;  // 静态模式
}
double t = NanosToSeconds(time) + phaseInSecs;
t *= 2 * SK_FloatPI / periodInSecs;  // 转换为弧度
float halfAmplitude = (max - min) / 2.f;
return halfAmplitude * std::sin(t) + halfAmplitude + min;
```

**数学公式**：
```
y = A * sin(2π * t / T + φ) + offset
其中：
  A = (max - min) / 2（振幅）
  T = periodInSecs（周期）
  φ = 2π * phaseInSecs / T（相位）
  offset = (max + min) / 2（中心值）
```

**使用场景**：
- 平滑的周期性动画
- 波动效果
- 呼吸灯效果

## 内部实现细节

### 内联函数优化

所有函数声明为 `static inline`：
- 避免函数调用开销
- 编译器可直接内联到调用点
- 适合频繁调用的工具函数

### 数值精度选择

- **输入时间**：double（双精度），适合纳秒级精度
- **返回值**：float（单精度），对于图形应用足够精确
- **中间计算**：double，避免累积误差

### 周期性函数的实现

使用 `fmod` 实现周期性：
```cpp
value = ::fmod(time + phase, period);
```

**特点**：
- 处理任意大的时间值
- 避免溢出
- 保持精度

## 依赖关系

**标准库依赖**：
- `<climits>`：INT32_MAX 常量
- `<cmath>`：fmod、fabs、sin 函数

**Skia 内部依赖**：
- `include/core/SkTypes.h`：基本类型定义、SkASSERT 宏
- `include/private/base/SkFloatingPoint.h`：SK_FloatPI 常量

**被依赖者**：
- `tools/viewer/AnimTimer.h`：动画计时器
- `tools/viewer/*Slide.cpp`：各种演示幻灯片
- `tools/sk_app/Application.cpp`：应用程序主循环

## 设计模式与设计决策

### 命名空间隔离

```cpp
namespace TimeUtils { ... }
```

将工具函数组织在独立命名空间中，避免命名冲突。

### 仅头文件库

所有函数定义在头文件中，无需单独的 .cpp 文件：
- 简化构建
- 支持内联优化
- 易于使用

### 通用性与简洁性

提供常用的时间操作，而非完整的时间库：
- Scaled：基本时间变换
- PingPong：往复插值
- SineWave：平滑周期插值

覆盖大多数动画需求，保持接口简单。

### 参数灵活性

- `Scaled` 的 `period` 参数默认为 0（不循环）
- `SineWave` 支持负周期（返回中值）
- 相位偏移允许多个动画同步但错开

## 性能考量

### 内联优化

所有函数标记为 `inline`，在调用点展开，消除函数调用开销。

### 数学函数性能

- `fmod`：相对较慢，但对于每帧一次的调用可接受
- `sin`：现代 CPU 有硬件优化，性能良好
- `fabs`：通常编译为单条指令

### 精度与性能权衡

使用 float 返回值而非 double：
- 更快的算术运算
- 更小的内存占用
- 对于图形应用精度足够（约 6-7 位有效数字）

### 避免分支

`Scaled` 和 `PingPong` 中的条件分支很少，现代 CPU 的分支预测器可有效处理。

## 相关文件

**同模块文件**：
- `tools/timer/Timer.h`：高精度计时器类

**使用者**：
- `tools/viewer/AnimTimer.h`：封装动画计时逻辑
- `tools/viewer/Slide.h`：演示幻灯片基类
- `tools/viewer/Viewer.cpp`：Viewer 应用程序
- `tools/viewer/*Slide.cpp`：各种动画示例

**典型使用模式**：
```cpp
// 在 Slide 的 animate 方法中
void MySlide::animate(double nanos) {
    fTime = TimeUtils::Scaled(TimeUtils::NanosToSeconds(nanos), fSpeed);
    fAlpha = TimeUtils::SineWave(nanos, 2.0f, 0.0f, 0.2f, 1.0f);
    fPosition = TimeUtils::PingPong(nanos, 5.0f, 0.0f, 0.0f, 200.0f);
}
```

该工具库是 Skia 动画系统的基础，提供了简洁而强大的时间操作接口。
