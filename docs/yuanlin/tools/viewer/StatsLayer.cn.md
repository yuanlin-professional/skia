# StatsLayer

> 源文件: tools/viewer/StatsLayer.h, tools/viewer/StatsLayer.cpp

## 概述

`StatsLayer` 是 Skia Viewer 工具中用于实时显示性能统计信息的图层类。它继承自 `sk_app::Window::Layer`,提供 CPU 和 GPU 计时器功能,以可视化图表的形式展示渲染性能数据。该类支持多个计时器的同时追踪,并在屏幕右上角绘制性能图表,包括帧时间曲线、平均值统计和标签信息。

## 架构位置

`StatsLayer` 位于 Skia 的 `tools/viewer` 工具目录中,作为 Viewer 应用程序的性能监控组件。它实现了窗口层接口,可以叠加在其他渲染内容之上。

```
tools/viewer/
├── Viewer (主应用程序)
├── Window::Layer (窗口层基类)
└── StatsLayer (性能统计层实现)
    ├── Timer (计时器管理)
    ├── GPU Timer (GPU性能追踪)
    └── Visualization (图表绘制)
```

该类依赖于 Skia 核心绘图 API、时间工具和字体工具。

## 主要类与结构体

### StatsLayer 类

```cpp
class StatsLayer : public sk_app::Window::Layer {
public:
    StatsLayer();
    void resetMeasurements();

    typedef int Timer;
    Timer addTimer(const char* label, SkColor color, SkColor labelColor = 0);
    void beginTiming(Timer);
    void endTiming(Timer);

    void enableGpuTimer(SkColor color);
    void disableGpuTimer();
    bool isGpuTimerEnabled() const { return fGpuTimerEnabled; }
    std::function<void(uint64_t ns)> issueGpuTimer();

    void onPrePaint() override;
    void onPaint(SkSurface*) override;
    void setDisplayScale(float scale) { fDisplayScale = scale; }

private:
    static const int kMeasurementCount = 1 << 6;  // 64

    struct TimerData {
        double fTimes[kMeasurementCount];
        SkString fLabel;
        SkColor fColor;
        SkColor fLabelColor;
    };

    skia_private::TArray<TimerData> fTimers;
    double fTotalTimes[kMeasurementCount];
    TimerData fGpuTimer;
    bool fGpuTimerEnabled;
    int fCurrentMeasurement;
    double fLastTotalBegin;
    double fCumulativeMeasurementTime;
    int fCumulativeMeasurementCount;
    float fDisplayScale;
};
```

### TimerData 结构体

- `fTimes[kMeasurementCount]`: 存储最近 64 帧的时间数据
- `fLabel`: 计时器标签文本
- `fColor`: 图表中的颜色
- `fLabelColor`: 标签文本颜色

## 公共 API 函数

### 构造与初始化

**StatsLayer()**
- 初始化所有测量数据为零
- 设置默认显示缩放为 1.0
- 将当前测量索引设置为 -1

**void resetMeasurements()**
- 清零所有计时器数据
- 重置累积统计信息
- 用于重新开始性能测量

### 计时器管理

**Timer addTimer(const char* label, SkColor color, SkColor labelColor = 0)**
- 添加新的 CPU 计时器
- 参数:
  - `label`: 计时器标签
  - `color`: 图表颜色
  - `labelColor`: 标签颜色(默认使用图表颜色)
- 返回计时器 ID,用于后续的开始/结束计时调用

**void beginTiming(Timer timer)**
- 开始指定计时器的计时
- 记录当前时间戳(负值)

**void endTiming(Timer timer)**
- 结束指定计时器的计时
- 计算并存储耗时(与开始时间相加)

### GPU 计时器

**void enableGpuTimer(SkColor color)**
- 启用 GPU 计时器
- 设置 GPU 图表颜色
- 清零历史数据

**void disableGpuTimer()**
- 禁用 GPU 计时器

**bool isGpuTimerEnabled() const**
- 查询 GPU 计时器是否启用

**std::function<void(uint64_t ns)> issueGpuTimer()**
- 发起 GPU 计时器查询
- 返回回调函数,用于接收 GPU 时间结果(纳秒)
- 支持多帧延迟(GPU 查询结果可能在后续帧返回)

### 生命周期回调

**void onPrePaint() override**
- 在绘制前调用
- 计算上一帧的总时间
- 更新累积统计数据
- 推进测量索引到下一帧

**void onPaint(SkSurface* surface) override**
- 在 surface 上绘制性能统计图表
- 显示 CPU 和 GPU 时间曲线
- 显示平均值和标签

**void setDisplayScale(float scale)**
- 设置显示缩放因子
- 用于适配不同 DPI 的屏幕

## 内部实现细节

### 时间测量机制

1. **环形缓冲区**: 使用固定大小 64 的数组存储历史数据,通过索引取模实现环形缓冲
2. **差分计时**: `beginTiming` 存储负时间戳,`endTiming` 加上正时间戳,得到耗时
3. **多计时器累加**: 每帧可以有多个计时器,它们的时间会累加显示

### 图表绘制

**绘制区域**:
- 宽度: 195 像素 (64 次测量 × 3 像素间距 + 1 个额外间距)
- CPU 图表高度: 100 像素
- GPU 图表高度: 100 像素(如果启用)
- 文本区域高度: 60 像素
- 位置: 屏幕右上角,有 10 像素边距

**可视化元素**:
- 黑色背景矩形
- 16ms 基准线(60 FPS 对应的帧时间)
- 垂直条形图,每条代表一帧
- 不同颜色代表不同计时器
- 白色部分表示未被计时器覆盖的时间

**缩放处理**:
- Android 平台固定 1.5 倍缩放
- 其他平台使用 `fDisplayScale`
- 使用矩阵变换保持右边缘对齐

### GPU 计时器特殊处理

- GPU 查询可能有多帧延迟
- 使用 -1 标记等待中的查询结果
- 绘制等待中的查询时使用反色,提醒用户结果未返回
- 回调函数通过 lambda 捕获索引和 layer 指针,将纳秒转换为毫秒

### 数据统计

- **瞬时平均**: 计算最近 64 帧中非零帧的平均时间
- **累积平均**: 自上次重置以来所有帧的平均时间
- 文本显示格式: "C: 瞬时平均 ms -> 累积平均 ms"

## 依赖关系

### 直接依赖

- **Skia 核心**: `SkCanvas`, `SkPaint`, `SkFont`, `SkSurface`, `SkRect`, `SkString`
- **时间工具**: `SkTime::GetMSecs()` (毫秒时间戳)
- **字体工具**: `ToolUtils::CreatePortableTypeface()`
- **窗口系统**: `sk_app::Window::Layer`
- **容器**: `skia_private::TArray`

### 模块依赖

```
StatsLayer
├── src/base/SkTime (时间测量)
├── tools/fonts/FontToolUtils (字体)
└── tools/sk_app/Window (窗口层接口)
```

## 设计模式与设计决策

### 设计模式

1. **Observer 模式**: 实现 `Window::Layer` 接口,响应绘制事件
2. **Strategy 模式**: GPU 计时器使用回调函数策略,解耦查询和结果处理
3. **Circular Buffer**: 环形缓冲区模式,固定内存开销追踪历史数据

### 设计决策

1. **固定大小缓冲**: 64 帧历史记录,平衡内存使用和数据可视性
2. **2 的幂次大小**: `kMeasurementCount = 1 << 6`,使用位运算实现快速取模
3. **多计时器支持**: 动态数组存储计时器,支持任意数量的性能追踪点
4. **GPU 异步查询**: 使用回调处理延迟结果,避免阻塞渲染
5. **视觉反馈**: 等待中的 GPU 查询用反色显示,提供清晰的状态指示
6. **平台适配**: Android 特殊缩放处理,提升小屏幕可读性

## 性能考量

1. **固定内存**: 64 × 8 字节 × (计时器数量 + 2) 的内存开销,每帧恒定
2. **轻量级绘制**: 使用简单的线条和矩形,绘制开销极小
3. **时间戳开销**: 每帧调用 `SkTime::GetMSecs()` 一次,开销可忽略
4. **环形缓冲**: O(1) 时间复杂度的数据更新和访问
5. **GPU 查询**: 异步机制避免阻塞,但增加了少量回调开销
6. **文本渲染**: 每帧重新格式化和渲染文本,有一定开销但可接受
7. **缩放变换**: 矩阵计算和画布变换有轻微开销

## 相关文件

- **tools/sk_app/Window.h**: 定义 `Window::Layer` 基类接口
- **src/base/SkTime.h**: 提供时间戳函数
- **tools/fonts/FontToolUtils.h**: 字体工具函数
- **tools/viewer/Viewer.cpp**: Viewer 主程序,创建和使用 `StatsLayer`
- **include/core/SkCanvas.h**: 画布绘图 API
- **include/core/SkSurface.h**: Surface 接口
