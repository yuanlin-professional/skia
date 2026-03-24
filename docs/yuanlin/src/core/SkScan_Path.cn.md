# SkScan_Path

> 源文件
> - src/core/SkScan_Path.cpp

## 概述

`SkScan_Path.cpp` 实现了 Skia 中非反走样路径填充的核心扫描转换算法。该模块使用活动边表(AET, Active Edge Table)和边排序技术,将矢量路径转换为光栅像素。它支持多种填充规则(EvenOdd/Winding)、反向填充、复杂裁剪以及三角形快速路径优化,是 Skia 2D 图形渲染管道的基础组件。

## 架构位置

`SkScan_Path` 位于 Skia 扫描转换子系统的核心层:

- **SkScan 家族**: 与 `SkScan_AntiPath.cpp` 并列(非反走样版本)
- **几何到像素**: 连接矢量路径和像素填充器
- **算法层**: 实现经典的扫描线算法

## 主要类与结构体

### SkEdge (边结构)

在 `SkEdge.h` 中定义,本文件使用:

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFirstY` | `int` | 边的起始 Y 坐标 |
| `fLastY` | `int` | 边的结束 Y 坐标 |
| `fX` | `SkFixed` | 当前 X 坐标(16.16定点数) |
| `fDxDy` | `SkFixed` | X 对 Y 的增量(斜率) |
| `fWinding` | `SkEdge::WindingValue` | 边的方向(+1/-1) |
| `fNext` | `SkEdge*` | 链表指针 |
| `fPrev` | `SkEdge*` | 双向链表指针 |

### InverseBlitter (反向填充适配器)

**继承关系**: `SkBlitter` → `InverseBlitter`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBlitter` | `SkBlitter*` | 被包装的实际 blitter |
| `fFirstX` | `int` | 裁剪区域左边界 |
| `fLastX` | `int` | 裁剪区域右边界 |
| `fPrevX` | `int` | 上一个填充位置 |

**功能**: 反转水平填充区域,用于实现反向填充规则

### SkScanClipper (裁剪管理器)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBlitter` | `SkBlitter*` | 可能被包装的 blitter |
| `fClipRect` | `const SkIRect*` | 矩形裁剪区域指针 |
| `fRectBlitter` | `SkRectClipBlitter` | 矩形裁剪适配器 |
| `fRgnBlitter` | `SkRgnClipBlitter` | 区域裁剪适配器 |

## 公共 API 函数

### SkScan::FillPath (主入口)

```cpp
void SkScan::FillPath(const SkPathRaw& raw,
                      const SkRegion& origClip,
                      SkBlitter* blitter);
```

**功能**: 非反走样路径填充

**参数**:
- `raw`: 底层路径表示
- `origClip`: 裁剪区域
- `blitter`: 像素填充器

### SkScan::FillTriangle (三角形优化)

```cpp
void SkScan::FillTriangle(const SkPoint pts[],
                          const SkRasterClip& clip,
                          SkBlitter* blitter);
```

**功能**: 三角形快速路径填充

### 辅助函数

```cpp
// 反向填充辅助
void sk_blit_above(SkBlitter* blitter, const SkIRect& ir, const SkRegion& clip);
void sk_blit_below(SkBlitter* blitter, const SkIRect& ir, const SkRegion& clip);

// 路径是否需要平铺
bool SkScan::PathRequiresTiling(const SkIRect& bounds);
```

## 内部实现细节

### 扫描线算法核心

#### 1. 边表构建与排序

```cpp
static SkEdge* sort_edges(SkEdge* list[], int count, SkEdge** last) {
    SkTQSort(list, list + count, compare_edges);

    // 排序规则:
    // 1. 按 fFirstY 升序
    // 2. 相同 Y 时按 fX 升序

    // 构建双向链表
    for (int i = 1; i < count; i++) {
        list[i - 1]->fNext = list[i];
        list[i]->fPrev = list[i - 1];
    }
    return list[0];
}
```

#### 2. 活动边表遍历

```cpp
static void walk_edges(SkEdge* prevHead, SkPathFillType fillType,
                       SkBlitter* blitter, int start_y, int stop_y, ...) {
    int windingMask = SkPathFillType_IsEvenOdd(fillType) ? 1 : -1;

    for (int curr_y = start_y; curr_y < stop_y; curr_y++) {
        int w = 0;
        int left;

        for (SkEdge* currE = prevHead->fNext; currE->fFirstY <= curr_y; currE = currE->fNext) {
            int x = SkFixedRoundToInt(currE->fX);

            if ((w & windingMask) == 0) {
                left = x;  // 开始填充区间
            }

            w += currE->fWinding;

            if ((w & windingMask) == 0) {
                blitter->blitH(left, curr_y, x - left);  // 结束填充区间
            }

            // 更新边位置
            if (currE->fLastY == curr_y) {
                remove_edge(currE);  // 移除完成的边
            } else {
                currE->fX += currE->fDxDy;  // X += slope
                backward_insert_edge_based_on_x(currE);  // 重新排序
            }
        }
    }
}
```

**填充规则实现**:

| 规则 | windingMask | 判断条件 |
|------|-------------|---------|
| EvenOdd | 1 | `(w & 1) == 0` 时填充 |
| Winding | -1 | `w == 0` 时填充 |

#### 3. 简单边遍历(凸多边形优化)

```cpp
static void walk_simple_edges(SkEdge* prevHead, SkBlitter* blitter,
                               int start_y, int stop_y) {
    SkEdge* leftE = prevHead->fNext;
    SkEdge* riteE = leftE->fNext;

    // 假设: 只有两条活动边(凸形状)
    while (local_top < stop_y) {
        int local_bot = std::min(leftE->fLastY, riteE->fLastY);

        if (dLeft == 0 && dRite == 0) {
            // 两边都是垂直,矩形优化
            blitter->blitRect(L, local_top, R - L, count);
        } else {
            // 逐行绘制
            for (int y = local_top; y <= local_bot; y++) {
                int L = SkFixedRoundToInt(left);
                int R = SkFixedRoundToInt(rite);
                blitter->blitH(L, y, R - L);
                left += dLeft;
                rite += dRite;
            }
        }

        // 切换到下一对边
        if (!update_edge(leftE, local_bot)) leftE = currE++;
        if (!update_edge(riteE, local_bot)) riteE = currE++;
    }
}
```

### 保守光栅化边界

```cpp
static SkIRect conservative_round_to_int(const SkRect& src) {
    // 使用偏置值扩大边界,避免数值漂移导致遗漏像素
    const double kConservativeRoundBias = 0.5 + 1.5 / SK_FDot6One;

    return {
        round_down_to_int(src.fLeft),   // floor(x - bias)
        round_down_to_int(src.fTop),
        round_up_to_int(src.fRight),    // ceil(x + bias)
        round_up_to_int(src.fBottom),
    };
}
```

**原因**: 三次贝塞尔曲线的扫描转换可能产生数值误差,保守估计确保不遗漏像素

### 反向填充实现

```cpp
class InverseBlitter : public SkBlitter {
    void blitH(int x, int y, int width) override {
        // 填充 [fPrevX, x) 而不是 [x, x+width)
        int invWidth = x - fPrevX;
        if (invWidth > 0) {
            fBlitter->blitH(fPrevX, y, invWidth);
        }
        fPrevX = x + width;
    }

    void prepost(int y, bool isStart) {
        if (!isStart) {
            // 扫描线结束,填充剩余部分
            int invWidth = fLastX - fPrevX;
            if (invWidth > 0) {
                fBlitter->blitH(fPrevX, y, invWidth);
            }
        } else {
            fPrevX = fFirstX;
        }
    }
};
```

### 三角形快速路径

```cpp
static void sk_fill_triangle(const SkPoint pts[], const SkIRect* clipRect,
                             SkBlitter* blitter, const SkIRect& ir) {
    SkEdge edgeStorage[3];
    SkEdge* list[3];

    // 为三条边创建 SkEdge
    int count = build_tri_edges(edgeStorage, pts, clipRect, list);

    if (count < 2) return;  // 退化三角形

    // 直接使用 walk_simple_edges(三角形是凸的)
    walk_simple_edges(&headEdge, blitter, start_y, stop_y);
}
```

**优化点**:
- 只有3条边,避免复杂排序
- 始终是凸形状,使用简化算法
- 跳过 `SkEdgeBuilder` 的开销

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkEdge` / `SkEdgeBuilder` | 边表构建 |
| `SkBlitter` | 像素填充 |
| `SkRegion` | 裁剪区域 |
| `SkTSort` | 边排序算法 |
| `SkPathPriv` | 路径属性查询(凸性等) |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SkDraw` | 调用 `FillPath` 填充路径 |
| `SkCanvas` | 通过 `SkDraw` 间接调用 |
| `SkDevice` | 设备相关绘制调度 |

## 设计模式与设计决策

### 1. 策略模式

不同形状使用不同遍历策略:
- **凸路径**: `walk_simple_edges`(假设两条活动边)
- **复杂路径**: `walk_edges`(完整 AET 算法)
- **三角形**: 特化的 `sk_fill_triangle`

### 2. 适配器模式

多种 blitter 适配器:
- `InverseBlitter`: 反向填充
- `SkRectClipBlitter`: 矩形裁剪
- `SkRgnClipBlitter`: 复杂区域裁剪

### 3. 模板方法模式

```cpp
void sk_fill_path(...) {
    // 模板骨架
    SkEdge** list = builder.buildEdges(...);
    SkEdge* edge = sort_edges(list, count, &last);

    if (isConvex && count >= 2) {
        walk_simple_edges(...);  // 变体1
    } else {
        walk_edges(...);         // 变体2
    }
}
```

### 4. 设计权衡

**为什么不使用反走样?**
- **性能**: 非反走样快约3-5倍
- **精确性**: 某些 UI 场景需要精确像素控制
- **兼容性**: 低端设备或特定平台需求

**为什么需要保守边界?**
- **安全性**: 防止数值误差导致像素遗漏
- **视觉质量**: 宁可多填充也不留空隙

## 性能考量

### 1. 凸路径快速路径

```cpp
if (raw.isKnownToBeConvex() && count >= 2) {
    walk_simple_edges(...);  // 跳过复杂的边排序
}
```

**性能提升**: ~2x(简单形状)

### 2. 三角形特化

```cpp
void FillTriangle(...) {
    // 直接构建3条边,跳过 SkEdgeBuilder
    int count = build_tri_edges(edgeStorage, pts, clipRect, list);
    walk_simple_edges(...);
}
```

**性能提升**: ~1.5x(相比通用路径)

### 3. 矩形优化

```cpp
if (dLeft == 0 && dRite == 0) {
    // 垂直边优化: 一次性填充矩形
    blitter->blitRect(L, local_top, R - L, count + 1);
}
```

### 4. 裁剪快速路径

```cpp
if (!irPreClipped && fClipRect->contains(ir)) {
    fClipRect = nullptr;  // 禁用逐像素裁剪
}
```

### 5. 边表内存管理

```cpp
SkBasicEdgeBuilder builder;
int count = builder.buildEdges(raw, pathContainedInClip ? nullptr : &clipRect);
// SkBasicEdgeBuilder 使用栈分配的内存池
```

### 6. 边更新优化

```cpp
// 使用安全算术避免断言失败
left = Sk32_can_overflow_add(left, dLeft);  // 允许溢出(未使用的值)
```

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkScan_Path.cpp` | 本文件(非反走样路径填充) |
| `src/core/SkScan_AntiPath.cpp` | 反走样路径填充 |
| `src/core/SkEdge.h` | 边结构定义 |
| `src/core/SkEdgeBuilder.h` | 边表构建器 |
| `src/core/SkBlitter.h` | 像素填充接口 |
| `src/core/SkScanPriv.h` | 扫描转换内部辅助 |
| `src/core/SkPathRawShapes.h` | 路径底层表示 |
| `src/core/SkDraw.cpp` | 主要调用者 |
