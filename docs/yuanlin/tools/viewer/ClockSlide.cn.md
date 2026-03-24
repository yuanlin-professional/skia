# ClockSlide

> 源文件: tools/viewer/ClockSlide.cpp

## 概述

`ClockSlide` 实现了一个功能完整的模拟时钟,实时显示系统时间。这是 Mozilla Canvas2D 基准测试套件中时钟测试的 C++ 实现,用于测试路径渲染和变换性能。时钟包括 12 个小时刻度、60 个分钟刻度、时针、分针、秒针以及装饰性圆圈,所有元素都使用路径绘制并应用复杂的旋转变换。

该实现展示了 Skia 在以下方面的能力:
- 复杂路径的连续渲染
- 大量变换操作的性能
- 实时动画更新
- 路径与圆形绘制的混合使用

## 架构位置

```
skia/
├── tools/viewer/
│   ├── ClockSlide.cpp    # 本文件
│   └── Slide.h            # Slide 基类
└── include/core/
    ├── SkCanvas.h         # 画布接口
    ├── SkPath.h           # 路径绘制
    └── SkPathBuilder.h    # 路径构建
```

## 主要类与结构体

### ClockSlide 类

```cpp
class ClockSlide : public Slide {
public:
    ClockSlide();
    void draw(SkCanvas* canvas) override;
    bool animate(double /*nanos*/) override;
};
```

### 时钟参数

时钟绘制使用固定的缩放和旋转:
- 画布平移到 (150, 150)
- 缩放 0.4 倍
- 初始旋转 -90 度(12 点方向朝上)

## 公共 API 函数

### draw

```cpp
void draw(SkCanvas* canvas) override;
```

完整绘制流程:
1. 保存画布状态并应用全局变换
2. 绘制 12 个小时刻度(粗线)
3. 绘制 60 个分钟刻度(细线,跳过小时位置)
4. 根据系统时间计算并绘制时针
5. 绘制分针
6. 绘制秒针(红色)
7. 绘制中心装饰圆圈
8. 绘制外圈边框
9. 恢复画布状态

### animate

```cpp
bool animate(double /*nanos*/) override;
```
始终返回 `true`,触发每帧重绘以显示实时时间。

## 内部实现细节

### 时间获取

使用 C++ 标准库获取系统时间:

```cpp
const auto time = std::chrono::system_clock::to_time_t(
    std::chrono::system_clock::now());
const auto* ltime = std::localtime(&time);
```

注意:代码注释指出 `localtime` 不是线程安全的,但对于 Slide 演示是可接受的。

### 时针角度计算

时针角度综合考虑小时、分钟和秒:

```cpp
canvas->rotate(ltime->tm_hour * (180.f / 6) +    // 小时
               ltime->tm_min  * (180.f / 360) +   // 分钟贡献
               ltime->tm_sec  * (180.f / 21600)); // 秒贡献
```

这确保时针平滑移动而非跳跃。

### 路径绘制 vs 形状绘制

代码通过 `USE_PATH` 宏支持两种实现:
- `#define USE_PATH 1`: 使用路径绘制(默认,用于基准测试)
- 未定义时使用圆角矩形绘制

路径版本性能更具挑战性,更适合基准测试。

### 刻度绘制模式

**小时刻度**(12 个):
```cpp
for (int i=0; i<12; i++) {
    canvas->rotate(180.f/6.f);  // 每次旋转 30 度
    path = SkPath::Line({200,0}, {240,0});
    canvas->drawPath(path, paintStroke);
}
```

**分钟刻度**(60 个):
```cpp
for (int i=0; i<60; i++) {
    if (i%5 == 0) {
        canvas->rotate(180.f/30.f);
        continue;  // 跳过小时位置
    }
    path = SkPath::Line({234,0}, {240,0});
    canvas->drawPath(path, paintStroke);
    canvas->rotate(180.f/30.f);  // 每次旋转 6 度
}
```

### 指针绘制

所有指针使用 `save()`/`restore()` 隔离变换:

```cpp
canvas->save();
canvas->rotate(/* 计算的角度 */);
path = SkPath::Line({起点}, {终点});
canvas->drawPath(path, paintStroke);
canvas->restore();
```

### 装饰圆圈

使用 `SkPathBuilder` 创建复杂路径:

```cpp
path = SkPathBuilder()
       .arcTo(rect, 0, 0, false)
       .addOval(rect, SkPathDirection::kCCW)
       .arcTo(rect, 360, 0, true)
       .detach();
```

虽然看起来复杂,实际效果是绘制简单的圆形。

## 依赖关系

- `include/core/SkCanvas.h`: 画布绘制和变换
- `include/core/SkPath.h`: 路径对象
- `include/core/SkPathBuilder.h`: 路径构建器
- `tools/viewer/Slide.h`: Slide 基类
- `<chrono>`, `<ctime>`: 时间获取

## 设计模式与设计决策

### 基准测试导向

该实现忠实于 Mozilla Canvas2D 基准测试,包括:
- 使用路径而非简单形状
- 每帧重新计算和绘制所有元素
- 不使用任何缓存优化

### 变换栈管理

大量使用 `save()`/`restore()` 保持变换隔离:
- 每个指针独立旋转
- 刻度循环中使用累积旋转
- 外层变换不影响内层元素

### 实时更新

每帧都查询系统时间并重绘,虽然低效但:
- 展示真实的渲染负载
- 测试持续重绘性能
- 提供实用的时钟功能

### 精确角度计算

使用浮点数角度而非整数,确保:
- 时针平滑移动
- 秒针也影响时针位置
- 视觉上更自然

## 性能考量

### 每帧开销

每帧绘制包括:
- 12 个小时刻度路径
- 48 个分钟刻度路径(60-12)
- 3 个指针路径
- 多个圆形和椭圆
- 总计约 60+ 个绘制调用

### 变换操作

每帧执行大量变换:
- 1 个全局变换
- 60+ 个旋转(刻度)
- 3 个旋转(指针)
- 多次 save/restore

### 三角函数避免

虽然处理角度和旋转,但代码巧妙地避免了显式的 sin/cos 调用:
- 使用累积旋转绘制刻度
- Canvas 的 `rotate()` 内部处理三角函数
- 角度计算仅涉及简单算术

### 路径重用

在循环中创建临时路径:

```cpp
path = SkPath::Line({200,0}, {240,0});
canvas->drawPath(path, paintStroke);
```

虽然每次都创建新路径,但路径很简单,开销可接受。

## 相关文件

### 类似的动画 Slide

- `tools/viewer/FlutterAnimateSlide.cpp`: 文本动画
- `tools/viewer/MotionMarkSlide.cpp`: 复杂动画基准测试

### 路径渲染

- `src/core/SkPath.cpp`: 路径实现
- `src/core/SkScan_Path.cpp`: 路径光栅化

### Canvas 变换

- `src/core/SkCanvas.cpp`: Canvas 实现
- `include/core/SkMatrix.h`: 变换矩阵

### 基准测试

Mozilla Canvas2D Clock Test 原始参考:
https://github.com/mozilla/arewefastyet/
