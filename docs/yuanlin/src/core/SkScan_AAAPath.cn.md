# SkScan_AAAPath

> 源文件: src/core/SkScan_AAAPath.cpp

## 概述

`SkScan_AAAPath` 实现了 Skia 的**解析式抗锯齿 (Analytic Anti-Aliasing, AAA)** 路径填充算法。相比传统的超采样方法,AAA 算法通过数学方式精确计算像素覆盖率,生成高质量的抗锯齿效果。

该算法的核心思想是:将路径视为线段集合,使用非等间距的扫描线,在每两条扫描线之间解析计算梯形覆盖率。这种方法比 16 倍超采样更快且质量更高,特别适合处理三角形等简单几何形状。

该文件包含约 1781 行代码,是 Skia 渲染管线中最复杂的扫描转换实现之一。

## 架构位置

```
Skia 抗锯齿渲染管线
├── SkDraw
│   └── drawPath()
├── SkScan::AntiFillPath()
├── SkScan::AAAFillPath() ← 当前模块入口
│   ├── AdditiveBlitter (累加混合)
│   │   ├── MaskAdditiveBlitter (掩码加速)
│   │   ├── RunBasedAdditiveBlitter (RLE编码)
│   │   └── SafeRLEAdditiveBlitter (安全截断)
│   ├── aaa_fill_path (算法调度)
│   ├── aaa_walk_convex_edges (凸多边形路径)
│   └── aaa_walk_edges (通用路径)
├── SkAnalyticEdge (边缘数据结构)
└── SkBlitter (最终像素输出)
```

## 主要类与结构体

### AdditiveBlitter (抽象基类)

**继承关系**: 继承自 `SkBlitter`

**关键成员变量**

| 成员 | 类型 | 说明 |
|------|------|------|
| 无直接成员 | - | 纯虚基类 |

**核心方法**

| 方法 | 功能 |
|------|------|
| getRealBlitter() | 获取真实的 Blitter |
| blitAntiH() | 累加抗锯齿像素 (多种重载) |
| getWidth() | 获取渲染宽度 |
| flush_if_y_changed() | 扫描线变化时刷新 |

### MaskAdditiveBlitter

**继承关系**: AdditiveBlitter → SkBlitter

**关键成员变量**

| 成员 | 类型 | 说明 |
|------|------|------|
| fRealBlitter | SkBlitter* | 真实输出 Blitter |
| fMask | SkMaskBuilder | Alpha 掩码存储 |
| fClipRect | SkIRect | 裁剪矩形 |
| fStorage | uint32_t[258] | 内联掩码缓冲区 (最大 1024 字节) |
| fRow | uint8_t* | 当前行指针 |
| fY | int | 当前 Y 坐标 |

**尺寸限制**

| 常量 | 值 | 说明 |
|------|-----|------|
| kMAX_WIDTH | 32 | 最大宽度 (像素) |
| kMAX_STORAGE | 1024 | 最大存储 (字节) |

### RunBasedAdditiveBlitter

**继承关系**: AdditiveBlitter → SkBlitter

**关键成员变量**

| 成员 | 类型 | 说明 |
|------|------|------|
| fRealBlitter | SkBlitter* | 真实输出 Blitter |
| fCurrY | int | 当前 Y 坐标 |
| fWidth | int | 渲染宽度 |
| fLeft | int | 左边界 |
| fTop | int | 顶边界 |
| fRunsToBuffer | int | RLE 缓冲区数量 |
| fRunsBuffer | void* | RLE 数据缓冲区 |
| fCurrentRun | int | 当前 RLE 索引 |
| fRuns | SkAlphaRuns | Alpha 游程结构 |
| fOffsetX | int | X 偏移量 |

### SafeRLEAdditiveBlitter

**继承关系**: RunBasedAdditiveBlitter → AdditiveBlitter → SkBlitter

**特殊功能**: 处理凹多边形时防止 alpha 值溢出 (>255),使用 `safely_add_alpha` 进行饱和运算。

## 公共 API 函数

### 入口函数

```cpp
void SkScan::AAAFillPath(
    const SkPathRaw& path,
    SkBlitter* blitter,
    const SkIRect& ir,              // 路径边界矩形
    const SkIRect& clipBounds,       // 裁剪边界
    bool forceRLE                    // 强制使用 RLE Blitter
);
```

**调用流程**:
1. 判断是否为反向填充
2. 选择 Blitter 类型 (Mask / RLE / SafeRLE)
3. 调用 `aaa_fill_path` 执行填充
4. 析构时自动刷新掩码到真实 Blitter

## 内部实现细节

### 1. 解析式抗锯齿算法原理

**扫描线选择策略**:
- 整数 Y 坐标: `y = 0, 1, 2, ..., H`
- 线段端点的 Y 坐标
- 线段交点的 Y 坐标

**覆盖率计算**:

对于两条扫描线 `y = c_i` 和 `y = c_{i+1}` 之间的梯形,计算每个像素的覆盖面积:

```
+-----------\----+
|            \  C|
|             \  |
\              \ |
|\      A       \|
| \              \
|  \             |
| B \            |
+----\-----------+
```

- 区域 A: 目标交集 (难以直接计算)
- 区域 B, C: 排除三角形 (易于计算)
- 策略: 计算 `全矩形 - B - C` 得到 A

### 2. 梯形光栅化

**核心函数**:
```cpp
static void blit_trapezoid_row(
    AdditiveBlitter* blitter,
    int y,
    SkFixed ul, SkFixed ur,  // 上边左右端点
    SkFixed ll, SkFixed lr,  // 下边左右端点
    SkFixed lDY, SkFixed rDY, // 左右斜率
    SkAlpha fullAlpha,
    SkAlpha* maskRow,
    bool noRealBlitter
);
```

**优化策略**:
1. **单像素情况**: 直接计算梯形面积,调用 `blit_single_alpha`
2. **双像素情况**: 计算两个三角形,调用 `blit_two_alphas`
3. **多像素情况**:
   - 计算左右边缘的部分覆盖
   - 中间矩形部分使用 `blit_full_alpha`
   - 复杂区域调用 `blit_aaa_trapezoid_row`

### 3. Alpha 计算公式

**梯形 Alpha**:
```cpp
static SkAlpha trapezoid_to_alpha(SkFixed l1, SkFixed l2) {
    SkFixed area = (l1 + l2) / 2;  // 梯形面积
    return SkTo<SkAlpha>(area >> 8);
}
```

**三角形 Alpha**:
```cpp
static SkAlpha partial_triangle_to_alpha(SkFixed a, SkFixed b) {
    // 近似计算: area = a * a * b / 2
    SkFixed area = (a >> 11) * (a >> 11) * (b >> 11);
    return SkTo<SkAlpha>((area >> 8) & 0xFF);
}
```

### 4. 边缘遍历算法

**凸多边形优化路径** (`aaa_walk_convex_edges`):
- 假设只有左右两条边
- 简化相交判断
- 使用 `is_smooth_enough` 跳过中间扫描线

**通用路径** (`aaa_walk_edges`):
- 维护边缘链表 (按 X 坐标排序)
- 使用 Winding 规则或 Even-Odd 规则
- 处理边缘相交和动态插入

### 5. 定点数与 Snapping

使用 16.16 定点数 (SkFixed) 进行精确计算:

```cpp
const SkFixed kSnapDigit = SK_Fixed1 >> 4;  // 1/16 像素
const SkFixed kSnapHalf = kSnapDigit >> 1;
const SkFixed kSnapMask = (-1 ^ (kSnapDigit - 1));

left += kSnapHalf;  // 快速四舍五入
left &= kSnapMask;  // 对齐到 1/16 像素网格
```

**目的**:
- 避免极小三角形带来的性能损失
- 防止精度误差导致的边缘情况

### 6. 平滑跳跃优化

检测边缘斜率变化是否足够平缓:

```cpp
static bool is_smooth_enough(SkAnalyticEdge* thisEdge, SkAnalyticEdge* nextEdge, int stop_y) {
    // 对于二次曲线
    if (thisEdge->fCurveCount > 0) {
        auto qEdge = static_cast<SkAnalyticQuadraticEdge*>(thisEdge);
        return SkAbs32(qEdge->fQDx) >> 1 >= SkAbs32(qEdge->fQDDx) &&
               SkAbs32(qEdge->fQDy) >> 1 >= SkAbs32(qEdge->fQDDy) &&
               (qEdge->fQDy - qEdge->fQDDy) >> qEdge->fCurveShift >= SK_Fixed1;
    }
    // 对于直线
    return SkAbs32(nextEdge->fDX - thisEdge->fDX) <= SK_Fixed1 &&
           nextEdge->fLowerY - nextEdge->fUpperY >= SK_Fixed1;
}
```

当边缘足够平滑时,跳过分数扫描线,直接前进到整数 Y 坐标。

### 7. 矩形快速路径

针对轴对齐矩形的特殊优化:

```cpp
static inline bool try_blit_fat_anti_rect(SkBlitter* blitter, const SkPathRaw& raw, const SkIRect& clip) {
    std::optional<SkRect> rect = raw.isRect();
    if (!rect) return false;
    if (!rect->intersect(SkRect::Make(clip))) return true;
    SkIRect bounds = rect->roundOut();
    if (bounds.width() < 3) return false;  // 矩形太窄
    blitter->blitFatAntiRect(*rect);
    return true;
}
```

避免通用算法开销,直接调用 Blitter 的矩形函数。

## 依赖关系

### 依赖的模块

| 模块 | 用途 | 头文件 |
|------|------|--------|
| SkAnalyticEdge | 边缘数据结构 | src/core/SkAnalyticEdge.h |
| SkEdgeBuilder | 边缘构建器 | src/core/SkEdgeBuilder.h |
| SkBlitter | 像素输出 | src/core/SkBlitter.h |
| SkAlphaRuns | RLE 编码 | src/core/SkAlphaRuns.h |
| SkPathRaw | 路径数据 | src/core/SkPathRaw.h |
| SkMask | 掩码结构 | src/core/SkMask.h |
| SkFixed | 定点数运算 | include/private/base/SkFixed.h |
| SkTSort | 排序算法 | src/base/SkTSort.h |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| SkScan | 通过 `SkScan::AAAFillPath` 调用 |
| SkDraw | 路径绘制时选择 AAA 算法 |
| SkAAClip | 抗锯齿裁剪生成时使用 (forceRLE=true) |

## 设计模式与设计决策

### 1. 策略模式

通过三种 `AdditiveBlitter` 实现不同的渲染策略:

| Blitter | 适用场景 | 特性 |
|---------|----------|------|
| MaskAdditiveBlitter | 小区域 (≤32x32) | 内存掩码,最快 |
| RunBasedAdditiveBlitter | 凸多边形 | RLE 编码,中等速度 |
| SafeRLEAdditiveBlitter | 凹多边形 | 饱和运算,最安全 |

### 2. 模板方法模式

`AdditiveBlitter` 定义抽象流程:
1. 初始化 (构造函数)
2. 累加像素 (`blitAntiH`)
3. 刷新输出 (析构函数)

具体实现由子类完成。

### 3. RAII (Resource Acquisition Is Initialization)

Blitter 的生命周期管理:
```cpp
{
    MaskAdditiveBlitter additiveBlitter(blitter, ir, clipBounds, isInverse);
    aaa_fill_path(path, ...);
    // 析构时自动调用 blitter->blitMask()
}
```

### 4. 编译时优化

使用内联缓冲区避免小对象的动态内存分配:
```cpp
const int kQuickLen = 31;
alignas(2) char quickMemory[(sizeof(SkAlpha) * 2 + sizeof(int16_t)) * (kQuickLen + 1)];
SkAlpha* alphas;
if (len <= kQuickLen) {
    alphas = (SkAlpha*)quickMemory;  // 栈上分配
} else {
    alphas = new SkAlpha[...];       // 堆上分配
}
```

### 5. 双路径架构

针对凸/凹多边形使用不同算法:
- **凸多边形**: `aaa_walk_convex_edges` (简化逻辑)
- **凹多边形**: `aaa_walk_edges` (完整逻辑)

### 6. 延迟计算

扫描线交点只在必要时计算:
```cpp
bool skipIntersect = path.points().size() > SkToSizeT((stop_y - start_y) * 2);
```

当路径点数多时,跳过相交计算以换取性能。

## 性能考量

### 1. 掩码缓存策略

**限制条件**:
- 宽度 ≤ 32 像素
- 总面积 ≤ 1024 字节

**优势**:
- 避免逐行调用 Blitter (虚函数开销)
- 利用 CPU 缓存局部性
- 减少 Alpha 组合计算

### 2. RLE 编码优化

`RunBasedAdditiveBlitter` 使用游程长度编码压缩 Alpha 值:
```
[255, 255, 255, 128, 0, 0, 0]
→ [runs: 3, 1, 3] [alpha: 255, 128, 0]
```

节省内存并提高 Blitter 效率。

### 3. Alpha 快照 (Snapping)

```cpp
SkAlpha snapAlpha(SkAlpha alpha) {
    return alpha > 247 ? 0xFF : alpha < 8 ? 0x00 : alpha;
}
```

将接近 0 和 255 的 Alpha 值快速路径化,因为 Blitter 处理完全透明/不透明更快。

### 4. 浮点避免

全程使用 16.16 定点数,避免浮点运算延迟和不确定性。

### 5. 扫描线跳跃

通过 `is_smooth_enough` 判断,跳过不必要的分数扫描线:
- 传统算法: 每像素 4 条扫描线 (1/4 像素间隔)
- AAA 算法: 只在关键点设置扫描线
- 三角形例子: 传统 4H 条 → AAA 约 3+H 条

### 6. 边缘交叉检测优化

```cpp
static bool edges_too_close(SkAnalyticEdge* prev, SkAnalyticEdge* next, SkFixed lowerY) {
    constexpr SkFixed SLACK = SK_Fixed1;
    return next && prev && next->fUpperY < lowerY &&
           prev->fX + SLACK >= next->fX - SkAbs32(next->fDX);
}
```

提前检测潜在的边缘交叉,强制使用 RLE 路径避免 SkAAClip 的左到右顺序要求被破坏。

### 7. 循环展开

在关键路径中手动优化循环:
```cpp
if (uL + 2 == lL) {  // 只需计算两个三角形,加速这种特殊情况
    SkFixed first = SkIntToFixed(uL) + SK_Fixed1 - ul;
    SkFixed second = ll - ul - first;
    SkAlpha a1 = fullAlpha - partial_triangle_to_alpha(first, lDY);
    SkAlpha a2 = partial_triangle_to_alpha(second, lDY);
    alphas[0] = alphas[0] > a1 ? alphas[0] - a1 : 0;
    alphas[1] = alphas[1] > a2 ? alphas[1] - a2 : 0;
}
```

避免通用算法的循环开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkScan.h | 接口定义 | 声明 `AAAFillPath` 入口 |
| src/core/SkScanPriv.h | 内部工具 | 边缘操作模板函数 |
| src/core/SkAnalyticEdge.h | 数据结构 | 解析式边缘定义 |
| src/core/SkEdgeBuilder.cpp | 边缘构建 | 从路径生成边缘 |
| src/core/SkBlitter.h | 输出接口 | 像素渲染 |
| src/core/SkAlphaRuns.h | RLE 编码 | 游程数据结构 |
| src/core/SkAAClip.cpp | 使用者 | 生成抗锯齿裁剪 |
| src/core/SkDraw.cpp | 调度者 | 选择渲染算法 |
