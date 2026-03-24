# SkEdge

> 源文件
> - src/core/SkEdge.h
> - src/core/SkEdge.cpp

## 概述

`SkEdge` 是 Skia 光栅化器中用于表示扫描线边缘的核心类。它将贝塞尔曲线（直线、二次曲线、三次曲线）近似为一系列线段，这些线段以Y坐标（而非参数t）为主轴，便于在扫描线算法中高效计算交点。该模块使用前向差分法（forward differencing）逐段更新曲线参数，在精度和性能之间取得平衡。它是 Skia CPU 光栅化路径的基础组件，直接影响填充和描边的质量与速度。

## 架构位置

`SkEdge` 位于 Skia 核心渲染层（`src/core`）中，是扫描线光栅化器的关键组成部分。它处于路径数据和像素生成之间的中间层：路径分解器将路径拆分为线段和曲线，`SkEdge` 将这些曲线转换为适合扫描线算法的表示形式，最终由 `SkScan` 模块使用这些边缘数据填充像素。

## 主要类与结构体

### SkEdge (基类)

用于表示单个线段，并提供虚接口用于曲线边缘的分段迭代。

| 类型 | 说明 |
|------|------|
| 继承关系 | 基类，被 `SkQuadraticEdge` 和 `SkCubicEdge` 继承 |
| 主要用途 | 表示当前活动的线段，支持曲线的分段更新 |

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fNext` / `fPrev` | `SkEdge*` | 双向链表指针，用于边缘列表管理 |
| `fX` | `SkFixed` | 当前线段在 `fFirstY + 0.5` 处的X坐标（16.16定点数） |
| `fDxDy` | `SkFixed` | 线段斜率（run/rise，即dx/dy，适合水平扫描） |
| `fFirstY` | `int32_t` | 线段起始Y坐标（像素行号） |
| `fLastY` | `int32_t` | 线段结束Y坐标（像素行号） |
| `fEdgeType` | `Type` | 边缘类型（kLine/kQuad/kCubic） |
| `fWinding` | `Winding` | 缠绕方向（kCW=1顺时针，kCCW=-1逆时针） |
| `fSegmentCount` | `uint8_t` | 剩余分段数（仅曲线非零） |
| `fCurveShift` | `uint8_t` | 前向差分时的移位量，用于乘以 deltaT |

### SkQuadraticEdge (二次曲线边缘)

继承自 `SkEdge`，专门处理二次贝塞尔曲线。

| 类型 | 说明 |
|------|------|
| 继承关系 | 继承 `SkEdge` |
| 主要用途 | 将二次曲线分解为 2^N 个线段，使用前向差分法迭代 |

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fQx` / `fQy` | `SkFixed` | 当前分段终点的非取整坐标 |
| `fQDxDt` / `fQDyDt` | `SkFixed` | 一阶导数（速度），存储为实际值的一半 |
| `fQD2xDt2` / `fQD2yDt2` | `SkFixed` | 二阶导数（加速度），预乘以 1/N |
| `fQLastX` / `fQLastY` | `SkFixed` | 曲线最终终点（避免累积误差） |

### SkCubicEdge (三次曲线边缘)

继承自 `SkEdge`，专门处理三次贝塞尔曲线。

| 类型 | 说明 |
|------|------|
| 继承关系 | 继承 `SkEdge` |
| 主要用途 | 将三次曲线分解为 2^N 个线段，使用三阶前向差分法 |

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCx` / `fCy` | `SkFixed` | 当前分段终点的非取整坐标 |
| `fCDxDt` / `fCDyDt` | `SkFixed` | 一阶导数 |
| `fCD2xDt2` / `fCD2yDt2` | `SkFixed` | 二阶导数 |
| `fCD3xDt3` / `fCD3yDt3` | `SkFixed` | 三阶导数，预乘以 1/N |
| `fCLastX` / `fCLastY` | `SkFixed` | 曲线最终终点 |
| `fCubicDShift` | `uint8_t` | 一阶导数的额外移位量（防止溢出） |

## 公共 API 函数

### SkEdge 类方法

```cpp
bool setLine(const SkPoint& p0, const SkPoint& p1, const SkIRect* clip)
bool setLine(const SkPoint& p0, const SkPoint& p1)
```
设置直线边缘。将浮点坐标转换为 FDot6（6位小数定点数），计算斜率和起始X坐标，确定缠绕方向。返回 `false` 如果线段高度为0或被裁剪。

```cpp
bool hasNextSegment() const
```
检查是否还有剩余分段（仅曲线返回 `true`）。

```cpp
virtual bool nextSegment()
```
更新到下一个线段。基类抛出错误（直线无分段），子类使用前向差分法计算新的 `fX`、`fDxDy`、`fFirstY`、`fLastY`。

### SkQuadraticEdge 类方法

```cpp
bool setQuadratic(const SkPoint pts[3])
```
设置二次曲线。计算曲线弯曲程度（通过中点偏离距离），确定分段数 N（2^shift），初始化前向差分参数。

```cpp
bool nextSegment() override
```
使用前向差分更新到下一段。公式：
- `x += dx >> shift`
- `dx += d2x`（二阶导数为常数）

### SkCubicEdge 类方法

```cpp
bool setCubic(const SkPoint pts[4])
```
设置三次曲线。评估曲线在 t=1/3 和 t=2/3 处的偏离距离，确定分段数，初始化三阶前向差分参数。

```cpp
bool nextSegment() override
```
使用三阶前向差分更新。公式：
- `x += dx >> dshift`
- `dx += d2x >> ddshift`
- `d2x += d3x`

## 内部实现细节

### 坐标系统与定点数

**FDot6 格式：** 整数部分在高位，小数部分占6位（精度1/64像素）。转换：
- `SkFloatToFDot6(f) = (int)(f * 64)`
- `SkFDot6ToFixed(f6) = f6 << 10`（转为16.16定点数）

**像素对齐：** `fFirstY` 和 `fLastY` 表示离散像素行，数学上视为像素中心（如6表示6.5）。起始X坐标 `fX` 对应 `fFirstY + 0.5` 这一行。

### 前向差分法原理

将贝塞尔曲线改写为多项式形式，利用导数为常数或低阶多项式的特性，每次迭代只需加法：

**二次曲线：** `B(t) = At² + Bt + C`
- 一阶导数：`B'(t) = 2At + B`
- 二阶导数：`B''(t) = 2A`（常数）
- 迭代：`pos += velocity; velocity += acceleration`

**三次曲线：** `B(t) = At³ + Bt² + Ct + D`
- 需跟踪三阶导数 `6A`（常数）
- 迭代：`pos += vel; vel += acc; acc += jerk`

### 自适应分段策略

**二次曲线：**
1. 计算中点 `B(1/2) = (p0 + 2p1 + p2)/4`
2. 计算基线中点 `M = (p0 + p2)/2`
3. 距离 `d = |B(1/2) - M| = |(-p0 + 2p1 - p2)/4|`
4. 分段数 `N = 2^shift`，其中 `shift = log2(d/threshold)`

**三次曲线：**
使用更精确的距离函数 `cubic_delta_from_line`，评估 t=1/3 和 t=2/3 处的最大偏离。

**限制：** `MAX_COEFF_SHIFT = 6`，最多64个分段（存储在8位 `fSegmentCount` 中）。

### 溢出防护

**二次曲线：** 导数存储为实际值的一半，应用时使用 `2/N` 而非 `1/N`，避免 `2(p1-p0)` 溢出16.16定点数。

**三次曲线：** 使用 `upShift` 和 `downShift` 机制：
- 先左移6位增加精度（`upShift=6`）
- 计算后右移（`downShift = shift + 6 - 10`）
- 确保中间结果不超过32位

### 裁剪处理

`chopLineWithClip` 方法将线段裁剪到矩形区域：
- 如果 `fFirstY < clip.fTop`，调整 `fX += fDxDy * (clip.fTop - fFirstY)`
- 假设线段至少部分在裁剪区域内（由调用者保证）

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkFDot6` | 6位定点数类型和转换函数 |
| `SkFixed` | 16.16定点数类型 |
| `SkPoint` | 浮点坐标输入 |
| `SkIRect` | 裁剪矩形 |
| `SkMathPriv` | 数学工具（如 `SkCLZ` 计算前导零） |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SkScan` | 扫描线填充器，消费边缘数据 |
| `SkAAClip` | 抗锯齿裁剪，使用边缘列表 |
| `SkBlitter` | 像素填充器，由 `SkScan` 调用 |

## 设计模式与设计决策

**继承与多态：** 虽然使用虚函数 `nextSegment()`，但大多数情况下类型在编译期已知，编译器可以去虚化调用。这种设计在灵活性和性能间取得平衡。

**Y主导设计：** 与传统图形学中按参数 t 遍历曲线不同，`SkEdge` 按Y坐标（扫描线）组织数据。斜率存储为 `dx/dy` 而非 `dy/dx`，这使得在固定Y值时计算X值变得简单高效。

**防御式终点处理：** 最后一段不使用前向差分结果，而是直接使用存储的终点 `fLastX/fLastY`，避免累积误差导致曲线端点偏移。

**双向链表：** `fNext` 和 `fPrev` 指针用于活动边列表（AET）的维护。在扫描线算法中，边缘需要按X坐标排序并动态插入/删除。

**缠绕规则支持：** `fWinding` 字段（1或-1）支持非零缠绕填充规则。扫描线算法通过累加缠绕值判断内外。

## 性能考量

**定点数算术：** 所有计算使用16.16或6.26定点数，避免浮点运算的开销和精度问题。在2000年代的硬件上，定点数比浮点数快得多；即使在现代硬件上，定点数的可预测性也有助于优化。

**前向差分优势：** 每个分段只需2-3次加法（二次曲线）或4-5次加法（三次曲线），无需乘法或除法。相比直接求值贝塞尔曲线（需多次乘法），性能提升显著。

**跳过零高度段：** `nextSegment()` 内部循环跳过所有零高度线段（`top == bot`），避免无效绘制。这在曲线接近水平时很常见。

**缓存局部性：** 边缘对象紧凑（基类约40字节，子类约80-100字节），活动边列表的遍历对缓存友好。

**自适应精度：** 根据曲线弯曲程度动态调整分段数。平缓曲线用更少分段（如4段），急剧弯曲曲线用更多分段（如64段），在质量和性能间自动平衡。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/core/SkScan.h` | 扫描线填充器，主要消费者 |
| `src/core/SkScan_Path.cpp` | 路径扫描，创建和管理边缘列表 |
| `src/core/SkFDot6.h` | 定点数类型定义 |
| `src/core/SkEdgeBuilder.cpp` | 从路径构建边缘 |
| `src/core/SkEdgeClipper.cpp` | 边缘裁剪辅助 |
| `include/core/SkPath.h` | 路径定义，边缘的输入来源 |
