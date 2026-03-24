# SkEdgeClipper

> 源文件
> - src/core/SkEdgeClipper.h
> - src/core/SkEdgeClipper.cpp

## 概述

`SkEdgeClipper` 是 Skia 光栅化管线中负责将路径边缘裁剪到指定矩形区域的核心组件。它实现了对线段、二次曲线和三次曲线的精确裁剪算法,将边缘分割为多个单调片段并裁剪到目标矩形内。该类采用迭代器模式,通过 `next()` 方法逐个返回裁剪后的边缘片段。

`SkEdgeClipper` 的设计目标是在保持数值稳定性的前提下,高效地处理复杂曲线的裁剪。它支持可选的右侧剔除优化,并能处理极端数值范围的输入数据,在必要时会将三次曲线降级为线段以避免数值不稳定。

## 架构位置

`SkEdgeClipper` 在 Skia 渲染管线中处于路径处理和边缘构建之间:

```
SkPath/SkPathRaw (矢量路径)
    ↓
SkEdgeClipper (裁剪与分割)
    ↓
SkEdgeBuilder (构建边缘列表)
    ↓
扫描线渲染器
```

该模块的位置和职责:
- **输入**: 原始路径数据和裁剪矩形
- **处理**: 在 X/Y 轴极值点分割曲线,裁剪到矩形区域
- **输出**: 裁剪后的线段、二次曲线、三次曲线序列
- **配合**: 与 `SkLineClipper` 协同处理线段裁剪

## 主要类与结构体

### SkEdgeClipper

**继承关系**
- 无继承关系,独立类

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCurrPoint` | `SkPoint*` | 当前输出点的指针 |
| `fCurrVerb` | `SkPathVerb*` | 当前输出动词的指针 |
| `fCurrVerbStop` | `SkPathVerb*` | 输出动词的结束位置 |
| `fCanCullToTheRight` | `const bool` | 是否允许剔除右侧超出裁剪区的内容 |
| `fPoints` | `SkPoint[54]` | 输出点的缓冲区,最多 54 个点 |
| `fVerbs` | `SkPathVerb[18]` | 输出动词的缓冲区,最多 18 个动词 |

**常量定义**

| 常量 | 值 | 说明 |
|-----|----|----|
| `kMaxVerbs` | 18 | 最多可存储 18 个动词(曲线在 X/Y 轴分为 9 段,每段包含线段和曲线) |
| `kMaxPoints` | 54 | 最多 54 个点(2 条线段 + 1 条三次曲线需 6 个点,乘以 9 段) |

## 公共 API 函数

### 构造函数

```cpp
explicit SkEdgeClipper(bool canCullToTheRight);
```
- **参数**: `canCullToTheRight` - 是否允许剔除右侧超出裁剪区的内容
- **说明**: 对于非凸路径,可以启用右侧剔除优化

### 裁剪函数

```cpp
bool clipLine(SkPoint p0, SkPoint p1, const SkRect& clip);
bool clipQuad(const SkPoint pts[3], const SkRect& clip);
bool clipCubic(const SkPoint pts[4], const SkRect& clip);
```
- **功能**: 对不同类型的曲线进行裁剪
- **返回值**: 如果有输出边缘返回 `true`,否则返回 `false`
- **特点**:
  - 自动处理 X/Y 轴极值点分割
  - 生成单调片段
  - 添加必要的垂直边缘

### 迭代器接口

```cpp
std::optional<SkPathVerb> next(SkPoint pts[]);
```
- **功能**: 获取下一个裁剪后的边缘片段
- **参数**: `pts` - 用于接收输出点的数组(需至少 4 个元素空间)
- **返回值**:
  - 有效时返回 `SkPathVerb` (kLine/kQuad/kCubic)
  - 无更多数据时返回空 `std::optional`
- **输出点数量**:
  - `kLine`: 2 个点
  - `kQuad`: 3 个点
  - `kCubic`: 4 个点

### 静态工具函数

```cpp
static void ClipPath(const SkPathRaw& raw, const SkRect& clip,
                     bool canCullToTheRight,
                     void (*consume)(SkEdgeClipper*, bool newCtr, void* ctx),
                     void* ctx);
```
- **功能**: 对整个路径进行裁剪,通过回调函数处理每个裁剪后的片段
- **参数**:
  - `raw`: 源路径数据
  - `clip`: 裁剪矩形
  - `canCullToTheRight`: 右侧剔除标志
  - `consume`: 处理裁剪结果的回调函数
  - `ctx`: 用户上下文数据
- **特点**: 自动处理圆锥曲线到二次曲线的转换

## 内部实现细节

### 二次曲线裁剪算法

**流程**:
1. 在 Y 轴极值点分割为单调片段
2. 在 X 轴极值点进一步分割
3. 对每个单调片段调用 `clipMonoQuad()`

**单调二次曲线裁剪** (`clipMonoQuad`):
```cpp
void clipMonoQuad(const SkPoint srcPts[3], const SkRect& clip) {
    1. 按 Y 坐标排序点
    2. 检查是否完全在裁剪区外
    3. 在 Y 方向裁剪(chop_quad_in_Y)
    4. 按 X 坐标排序
    5. 处理三种情况:
       - 完全在左侧: 添加垂直边缘
       - 完全在右侧: 根据 canCullToTheRight 决定是否添加垂直边缘
       - 跨越裁剪区: 在 X 边界分割并添加适当的边缘
}
```

**数值稳定性处理**:
```cpp
// 使用求根公式计算分割参数 t
bool chopMonoQuadAt(SkScalar c0, SkScalar c1, SkScalar c2,
                    SkScalar target, SkScalar* t) {
    SkScalar A = c0 - c1 - c1 + c2;
    SkScalar B = 2*(c1 - c0);
    SkScalar C = c0 - target;
    return SkFindUnitQuadRoots(A, B, C, roots);
}
```

### 三次曲线裁剪算法

**流程**:
1. 检查边界框是否可以安全处理(避免浮点数精度问题)
2. 如果数值范围过大,降级为线段裁剪
3. 在 Y 轴极值点分割为单调片段
4. 在 X 轴极值点进一步分割
5. 对每个单调片段调用 `clipMonoCubic()`

**数值范围检查**:
```cpp
static bool too_big_for_reliable_float_math(const SkRect& r) {
    const SkScalar limit = 1 << 22;  // 约 4,194,304
    return r.fLeft < -limit || r.fTop < -limit ||
           r.fRight > limit || r.fBottom > limit;
}
```
- **原因**: 超过此范围的坐标值可能导致曲线分割和裁剪计算不精确
- **处理**: 将三次曲线替换为连接起点和终点的线段

**单调三次曲线裁剪** (`clipMonoCubic`):
```cpp
void clipMonoCubic(const SkPoint src[4], const SkRect& clip) {
    1. 按 Y 坐标排序点
    2. 在 Y 方向裁剪(chop_cubic_in_Y)
    3. 按 X 坐标排序
    4. 处理左侧/右侧/跨越裁剪区的情况
    5. 在 X 边界分割并添加适当的边缘
}
```

**三次曲线 Y 轴裁剪**:
```cpp
static void chop_cubic_in_Y(SkPoint pts[4], const SkRect& clip) {
    // 上方裁剪
    if (pts[0].fY < clip.fTop) {
        chop_mono_cubic_at_y(pts, clip.fTop, tmp);
        // 处理多次裁剪的数值误差
        if (tmp[3].fY < clip.fTop && tmp[4].fY < clip.fTop && tmp[5].fY < clip.fTop) {
            // 重新裁剪以提高精度
            chop_mono_cubic_at_y(tmp2, clip.fTop, tmp);
        }
    }
    // 下方裁剪类似处理
}
```

### 边缘输出机制

**添加不同类型的边缘**:

```cpp
void appendLine(SkPoint p0, SkPoint p1);
void appendVLine(SkScalar x, SkScalar y0, SkScalar y1, bool reverse);
void appendQuad(const SkPoint pts[3], bool reverse);
void appendCubic(const SkPoint pts[4], bool reverse);
```

**反向处理**:
- 当需要反转边缘方向时,设置 `reverse = true`
- 确保边缘的 Y 坐标按递增顺序排列
- 用于处理排序后边缘方向改变的情况

### 圆锥曲线处理

在 `ClipPath` 静态方法中:
```cpp
case SkPathEdgeIter::Edge::kConic: {
    const SkPoint* quadPts =
        quadder.computeQuads(e.fPts, iter.conicWeight(), kConicTol);
    for (int i = 0; i < quadder.countQuads(); ++i) {
        if (clipper.clipQuad(quadPts, clip)) {
            consume(&clipper, e.fIsNewContour, ctx);
        }
        quadPts += 2;
    }
}
```
- 使用 `SkAutoConicToQuads` 将圆锥曲线转换为二次曲线序列
- 容差值为 `0.25f`
- 逐个裁剪生成的二次曲线

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRect` | 定义裁剪矩形 |
| `SkGeometry` | 提供曲线分割函数(`SkChopQuadAt`, `SkChopCubicAt`等) |
| `SkLineClipper` | 处理线段裁剪 |
| `SkPathPriv` | 访问路径内部数据和迭代器 |
| `SkPathTypes` | 定义 `SkPathVerb` 枚举 |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| `SkEdgeBuilder` | 使用 `SkEdgeClipper` 对路径边缘进行裁剪 |
| `SkScan` | 间接使用(通过 `SkEdgeBuilder`) |
| `SkAAClip` | 在抗锯齿裁剪中使用 |

## 设计模式与设计决策

### 迭代器模式

`SkEdgeClipper` 实现了标准的迭代器模式:

```cpp
SkEdgeClipper clipper(canCullToTheRight);
if (clipper.clipQuad(pts, clip)) {
    SkPoint outputPts[4];
    while (auto verb = clipper.next(outputPts)) {
        // 处理输出的边缘片段
    }
}
```

**优势**:
- 避免预先分配大型输出缓冲区
- 支持流式处理
- 简化调用者代码

### 缓冲区复用

使用固定大小的内部缓冲区:
```cpp
SkPoint     fPoints[kMaxPoints];   // 54 个点
SkPathVerb  fVerbs[kMaxVerbs];     // 18 个动词
```

**原因**:
- 避免动态内存分配
- 缓冲区大小足以处理任何单条曲线的裁剪结果
- 提高性能和缓存局部性

### 降级策略

当遇到极端数值时,三次曲线降级为线段:
```cpp
if (too_big_for_reliable_float_math(bounds)) {
    return this->clipLine(srcPts[0], srcPts[3], clip);
}
```

**设计理由**:
- **正确性优先**: 避免数值不稳定导致的渲染错误
- **实用主义**: 极端坐标下的精确曲线裁剪意义不大
- **性能权衡**: 使用 double 精度会显著降低性能

### 数值鲁棒性处理

**多重保护机制**:
1. **精确求根**: 使用二次方程求解计算分割参数
2. **备用方法**: 求根失败时使用迭代逼近(`mono_cubic_closestT`)
3. **强制箝位**: 在分割后强制箝位坐标到裁剪边界
4. **多次裁剪**: 对数值误差较大的情况重新裁剪

```cpp
// 强制箝位以清理数值误差
tmp[3].fY = clip.fTop;
clamp_ge(tmp[4].fY, clip.fTop);
```

## 性能考量

### 内存优化

1. **栈分配**: 所有缓冲区都在栈上,避免堆分配开销
2. **固定大小**: 编译时确定缓冲区大小,无需动态增长
3. **就地修改**: `chop_quad_in_Y` 和 `chop_cubic_in_Y` 直接修改输入点数组

### 计算优化

1. **提前拒绝**:
   ```cpp
   if (quick_reject(bounds, clip)) {
       return;  // 完全在裁剪区外,直接返回
   }
   ```

2. **右侧剔除**:
   ```cpp
   if (pts[0].fX >= clip.fRight) {
       if (!this->canCullToTheRight()) {
           this->appendVLine(clip.fRight, pts[0].fY, pts[3].fY, reverse);
       }
       return;  // 无需进一步处理
   }
   ```

3. **单调性假设**: 通过在极值点分割,简化裁剪算法
4. **避免重复计算**: 使用 `sort_increasing_Y` 一次性确定点的顺序

### 数值稳定性权衡

```cpp
const SkScalar limit = 1 << 22;  // 选择此值的原因:
// 1. 足够大以覆盖大多数实际场景
// 2. 足够小以避免 float32 精度问题
// 3. 实验确定的最佳平衡点
```

### 调试支持

```cpp
#ifdef SK_DEBUG
    void sk_assert_monotonic_x(const SkPoint pts[], int count);
    void sk_assert_monotonic_y(const SkPoint pts[], int count);
#else
    #define sk_assert_monotonic_x(pts, count)
    #define sk_assert_monotonic_y(pts, count)
#endif
```
- Debug 模式下验证单调性假设
- Release 模式下编译为空操作,零开销

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkLineClipper.h` | 依赖 | 线段裁剪实现 |
| `src/core/SkGeometry.h` | 依赖 | 曲线几何计算函数 |
| `src/core/SkPathPriv.h` | 依赖 | 路径内部辅助函数和迭代器 |
| `src/core/SkEdgeBuilder.cpp` | 使用者 | 在边缘构建过程中使用裁剪器 |
| `include/core/SkRect.h` | 数据结构 | 裁剪矩形定义 |
| `include/core/SkPathTypes.h` | 数据结构 | 路径动词类型 |
