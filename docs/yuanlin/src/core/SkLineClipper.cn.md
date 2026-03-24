# SkLineClipper

> 源文件
> - src/core/SkLineClipper.h
> - src/core/SkLineClipper.cpp

## 概述

`SkLineClipper` 是 Skia 中用于线段裁剪的工具类,实现了 Cohen-Sutherland 算法的变体。它能够将线段裁剪到矩形区域内,并针对扫描转换(scan conversion)进行了特殊优化,为超出裁剪区域的部分添加垂直线段,从而保证反锯齿边缘的正确渲染。

该类提供两种裁剪模式:
1. **ClipLine:** 用于扫描转换,会在左右边界外添加垂直线段
2. **IntersectLine:** 纯粹的几何裁剪,只返回在裁剪区域内的线段部分

## 架构位置

`SkLineClipper` 在 Skia 渲染管道中的位置:

```
SkCanvas::drawLine()
    ↓
SkDraw::drawLine()
    ↓
SkLineClipper (裁剪到裁剪区域)
    ↓
SkScan::HairLine() / AntiHairLine()
    ↓
CPU 光栅化器
```

它是连接高层绘制 API 和底层扫描转换的关键组件。

## 主要类与结构体

### SkLineClipper

**类型:** 工具类(所有方法都是静态的)

**常量定义:**

| 常量 | 值 | 说明 |
|------|-----|------|
| kMaxPoints | 4 | ClipLine 可能返回的最大点数 |
| kMaxClippedLineSegments | 3 | ClipLine 可能返回的最大线段数 |

这些常量定义了输出数组的最大尺寸。

## 公共 API 函数

### ClipLine

```cpp
static int ClipLine(const SkPoint pts[2], const SkRect& clip,
                    SkPoint lines[kMaxPoints], bool canCullToTheRight);
```

**功能:** 将线段裁剪到矩形内,并为扫描转换添加垂直线段。

**参数:**
- `pts[2]`: 输入线段的两个端点
- `clip`: 裁剪矩形
- `lines[kMaxPoints]`: 输出点数组(最多 4 个点)
- `canCullToTheRight`: 是否可以剔除完全在右侧的线段

**返回值:** 返回裁剪后的线段数量(0-3)

**输出格式:**
- 返回 1: lines[0]-lines[1] 是一条线段
- 返回 2: lines[0]-lines[1] 和 lines[1]-lines[2] 是两条线段(共享端点)
- 返回 3: lines[0]-lines[1], lines[1]-lines[2], lines[2]-lines[3] 是三条线段

**特殊处理:**
- 完全在上方或下方的线段被剔除(返回 0)
- 在左侧外的部分添加垂直线段(X 坐标设为 clip.fLeft)
- 在右侧外的部分可选添加垂直线段或剔除(根据 canCullToTheRight)

### IntersectLine

```cpp
static bool IntersectLine(const SkPoint src[2], const SkRect& clip, SkPoint dst[2]);
```

**功能:** 计算线段与矩形的交集。

**参数:**
- `src[2]`: 输入线段的两个端点
- `clip`: 裁剪矩形
- `dst[2]`: 输出线段的两个端点

**返回值:**
- true: 线段与矩形有交集,dst 包含裁剪后的线段
- false: 线段与矩形无交集,dst 内容未定义

**与 ClipLine 的区别:**
- 不添加垂直线段
- 只返回在裁剪区域内的部分
- 更适合纯几何计算

## 内部实现细节

### 辅助函数

#### pin_unsorted

```cpp
template <typename T> T pin_unsorted(T value, T limit0, T limit1)
```

**功能:** 将 value 限制在 [min(limit0, limit1), max(limit0, limit1)] 范围内。

**用途:** 处理浮点数精度问题,确保计算出的交点在合法范围内。

#### sect_with_horizontal

```cpp
static SkScalar sect_with_horizontal(const SkPoint src[2], SkScalar Y)
```

**功能:** 计算线段与水平线 y=Y 的交点的 X 坐标。

**实现:**
```cpp
SkScalar dy = src[1].fY - src[0].fY;
if (SkScalarNearlyZero(dy)) {
    return sk_float_midpoint(src[0].fX, src[1].fX);  // 几乎水平,返回中点
} else {
    double result = X0 + ((double)Y - Y0) * (X1 - X0) / (Y1 - Y0);
    return (float)pin_unsorted(result, X0, X1);  // 钳制结果
}
```

**精度处理:**
- 使用 double 精度计算避免中间溢出
- 使用 pin_unsorted 处理量子涨落(quantum flux)导致的越界

#### sect_with_vertical

```cpp
static SkScalar sect_with_vertical(const SkPoint src[2], SkScalar X)
```

**功能:** 计算线段与垂直线 x=X 的交点的 Y 坐标。

**类似于 sect_with_horizontal,但不需要 pin_unsorted(注释中提到的 bug)。**

#### sect_clamp_with_vertical

```cpp
static SkScalar sect_clamp_with_vertical(const SkPoint src[2], SkScalar x)
```

**功能:** 计算线段与垂直线的交点,并强制钳制结果。

**用途:** 修复 skbug.com/40038736,确保结果在 src[0].fY 和 src[1].fY 之间。

### IntersectLine 实现细节

**快速路径:**
```cpp
SkRect bounds;
bounds.set(src[0], src[1]);
if (containsNoEmptyCheck(clip, bounds)) {
    // 线段完全在裁剪区域内
    if (src != dst) {
        memcpy(dst, src, 2 * sizeof(SkPoint));
    }
    return true;
}
```

**边界检查:**
使用 `nestedLT` 函数处理边界重合情况:
```cpp
static inline bool nestedLT(SkScalar a, SkScalar b, SkScalar dim) {
    return a <= b && (a < b || dim > 0);
}
```

只有当线段和边缘共线时(dim > 0),才允许边界重合。

**两阶段裁剪:**

1. **Y 方向裁剪:**
   ```cpp
   if (tmp[index0].fY < clip.fTop) {
       tmp[index0].set(sect_with_horizontal(src, clip.fTop), clip.fTop);
   }
   if (tmp[index1].fY > clip.fBottom) {
       tmp[index1].set(sect_with_horizontal(src, clip.fBottom), clip.fBottom);
   }
   ```

2. **X 方向裁剪:**
   ```cpp
   if (tmp[index0].fX < clip.fLeft) {
       tmp[index0].set(clip.fLeft, sect_with_vertical(tmp, clip.fLeft));
   }
   if (tmp[index1].fX > clip.fRight) {
       tmp[index1].set(clip.fRight, sect_with_vertical(tmp, clip.fRight));
   }
   ```

**特殊情况:** 垂直线与边界重合的处理。

### ClipLine 实现细节

**Y 方向快速剔除:**
```cpp
if (pts[index1].fY <= clip.fTop) {  // 完全在上方
    return 0;
}
if (pts[index0].fY >= clip.fBottom) {  // 完全在下方
    return 0;
}
```

**Y 方向裁剪:**
与 IntersectLine 类似,但结果存储在 tmp 中。

**X 方向处理 (核心差异):**

1. **完全在左侧:**
   ```cpp
   if (tmp[index1].fX <= clip.fLeft) {
       tmp[0].fX = tmp[1].fX = clip.fLeft;  // 创建垂直线段
       result = tmp;
       reverse = false;
   }
   ```

2. **完全在右侧:**
   ```cpp
   else if (tmp[index0].fX >= clip.fRight) {
       if (canCullToTheRight) {
           return 0;  // 剔除
       }
       tmp[0].fX = tmp[1].fX = clip.fRight;  // 创建垂直线段
       result = tmp;
       reverse = false;
   }
   ```

3. **部分在内部 (核心算法):**
   ```cpp
   else {
       result = resultStorage;
       SkPoint* r = result;

       // 左侧外 -> 添加垂直线段
       if (tmp[index0].fX < clip.fLeft) {
           r->set(clip.fLeft, tmp[index0].fY);
           r += 1;
           r->set(clip.fLeft, sect_clamp_with_vertical(tmp, clip.fLeft));
           SkASSERT(is_between_unsorted(r->fY, tmp[0].fY, tmp[1].fY));
       } else {
           *r = tmp[index0];
       }
       r += 1;

       // 右侧外 -> 添加垂直线段
       if (tmp[index1].fX > clip.fRight) {
           r->set(clip.fRight, sect_clamp_with_vertical(tmp, clip.fRight));
           SkASSERT(is_between_unsorted(r->fY, tmp[0].fY, tmp[1].fY));
           r += 1;
           r->set(clip.fRight, tmp[index1].fY);
       } else {
           *r = tmp[index1];
       }

       lineCount = SkToInt(r - result);
   }
   ```

**结果反转处理:**
如果 reverse 为 true,将结果点逆序复制:
```cpp
if (reverse) {
    for (int i = 0; i <= lineCount; i++) {
        lines[lineCount - i] = result[i];
    }
} else {
    memcpy(lines, result, (lineCount + 1) * sizeof(SkPoint));
}
```

保证线段方向与原始输入一致。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkPoint | 点表示 |
| SkRect | 矩形表示 |
| SkScalar | 标量类型 |
| SkFloatingPoint | 浮点辅助函数 |
| SkTo | 类型转换 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkScan | 扫描转换前的线段裁剪 |
| SkDraw | 高层绘制逻辑 |
| SkPath | 路径光栅化 |

## 设计模式与设计决策

### 静态工具类设计

`SkLineClipper` 不维护状态,所有方法都是静态的:
- **优势:** 不需要构造对象,调用开销小
- **线程安全:** 无共享状态,天然线程安全
- **简单性:** 接口清晰,易于理解和使用

### 两种裁剪模式

提供 ClipLine 和 IntersectLine 两种方法:

**设计原因:**
- **ClipLine:** 为扫描转换优化,添加垂直线段确保边缘反锯齿正确
- **IntersectLine:** 纯几何计算,用于边界检测和其他场景

**权衡:** 分离两种用途,避免单一方法承担过多职责。

### 两阶段裁剪算法

先裁剪 Y 方向,再裁剪 X 方向:

**原因:**
1. Y 方向可以快速剔除(完全在上方或下方)
2. X 方向需要复杂的垂直线段处理
3. 分阶段简化了每个阶段的逻辑

### 精度保护机制

使用多层精度保护:
1. **Double 精度计算:** 避免中间结果溢出
2. **pin_unsorted:** 钳制结果到合法范围
3. **sect_clamp_with_vertical:** 特殊钳制处理
4. **SkScalarNearlyZero:** 处理几乎水平/垂直的线段

**设计理由:** 浮点运算不精确,需要多层保护确保结果合法。

## 性能考量

### 快速路径优化

IntersectLine 包含快速路径:
```cpp
if (containsNoEmptyCheck(clip, bounds)) {
    // 快速路径:完全包含
    if (src != dst) {
        memcpy(dst, src, 2 * sizeof(SkPoint));
    }
    return true;
}
```

对于完全在裁剪区域内的线段,直接返回,避免昂贵的交点计算。

### 早期剔除

ClipLine 在处理 X 方向前先剔除 Y 方向外的线段:
```cpp
if (pts[index1].fY <= clip.fTop) {
    return 0;  // 早期返回
}
```

减少不必要的计算。

### 栈上分配

所有临时数据都在栈上分配:
```cpp
SkPoint tmp[2];
SkPoint resultStorage[kMaxPoints];
```

避免堆分配的开销。

### 内存布局

输出数组的点是连续存储的,方便后续处理:
```cpp
SkPoint lines[kMaxPoints];  // [p0, p1, p2, p3]
// 线段1: lines[0]-lines[1]
// 线段2: lines[1]-lines[2]
// 线段3: lines[2]-lines[3]
```

**优势:** 缓存友好,共享端点节省内存。

### 分支预测

使用 index0/index1 预先排序,减少后续分支:
```cpp
if (src[0].fY < src[1].fY) {
    index0 = 0;
    index1 = 1;
} else {
    index0 = 1;
    index1 = 0;
}
```

让后续代码可以假设 tmp[index0].fY <= tmp[index1].fY。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkPoint.h | 依赖 | 点类型定义 |
| include/core/SkRect.h | 依赖 | 矩形类型定义 |
| src/core/SkScan.h | 使用者 | 扫描转换 |
| src/core/SkDraw.cpp | 使用者 | 高层绘制实现 |
| include/private/base/SkFloatingPoint.h | 依赖 | 浮点辅助函数 |
