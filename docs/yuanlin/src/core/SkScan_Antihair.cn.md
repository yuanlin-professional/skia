# SkScan_Antihair

> 源文件
> - src/core/SkScan_Antihair.cpp

## 概述

`SkScan_Antihair.cpp` 实现了 Skia 中反走样(antialiased)细线(hairline)和矩形框的光栅化算法。该模块使用 FDot6(26.6 定点数)精度进行亚像素精确渲染,根据直线斜率选择不同的光栅化策略,并提供精确的覆盖率计算以实现高质量的反走样效果。

## 架构位置

`SkScan_Antihair` 位于 Skia 扫描转换(scan conversion)子系统中:

- **SkScan 家族**: 与 `SkScan_Path.cpp`、`SkScan_Hairline.cpp` 并列
- **渲染管道**: 位于路径几何与像素填充之间
- **反走样层**: 专注于亚像素精度的覆盖率计算

## 主要类与结构体

### SkAntiHairBlitter (抽象基类)

**继承关系**:
```
SkAntiHairBlitter (抽象)
  ├── HLine_SkAntiHairBlitter  (水平线)
  ├── Horish_SkAntiHairBlitter (近水平线)
  ├── VLine_SkAntiHairBlitter  (垂直线)
  └── Vertish_SkAntiHairBlitter (近垂直线)
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBlitter` | `SkBlitter*` | 实际像素填充器 |

**核心虚函数**:

| 函数 | 说明 |
|------|------|
| `drawCap(x, fy, slope, coverage)` | 绘制端点覆盖部分 |
| `drawLine(x, stopx, fy, slope)` | 绘制完整像素跨度 |

### HLine_SkAntiHairBlitter

用于完全水平的线(斜率为0)。

**实现特点**:
- 直线跨越两行像素,根据 Y 坐标小数部分分配覆盖率
- 无需每像素计算斜率

### Horish_SkAntiHairBlitter

用于斜率在 [-1, 1] 范围的近水平线。

**实现特点**:
- 每个 X 坐标对应至多两个 Y 坐标
- 使用 `blitAntiV2` 一次性绘制两个垂直相邻像素

### VLine_SkAntiHairBlitter

用于完全垂直的线(斜率无穷大)。

**实现特点**:
- 直线跨越两列像素
- 使用 `blitV` 高效绘制连续垂直像素

### Vertish_SkAntiHairBlitter

用于斜率 > 1 或 < -1 的近垂直线。

**实现特点**:
- 每个 Y 坐标对应至多两个 X 坐标
- 使用 `blitAntiH2` 绘制水平相邻像素对

## 公共 API 函数

### SkScan::AntiHairLineRgn

```cpp
void SkScan::AntiHairLineRgn(SkSpan<const SkPoint> src,
                             const SkRegion* clip,
                             SkBlitter* blitter);
```

**功能**: 绘制反走样细线段序列

**参数**:
- `src`: 连续点序列(每相邻两点形成一条线段)
- `clip`: 裁剪区域(可选)
- `blitter`: 像素填充器

### SkScan::AntiHairRect

```cpp
void SkScan::AntiHairRect(const SkRect& rect,
                          const SkRasterClip& clip,
                          SkBlitter* blitter);
```

**功能**: 绘制反走样矩形框(仅边框,不填充)

### SkScan::AntiFillXRect

```cpp
void SkScan::AntiFillXRect(const SkXRect& xr,
                           const SkRegion* clip,
                           SkBlitter* blitter);
```

**功能**: 填充反走样的定点矩形(SkXRect 使用 SkFixed 坐标)

### SkScan::AntiFillRect

```cpp
void SkScan::AntiFillRect(const SkRect& r,
                          const SkRegion* clip,
                          SkBlitter* blitter);
```

**功能**: 填充反走样的浮点矩形

### SkScan::AntiFrameRect

```cpp
void SkScan::AntiFrameRect(const SkRect& r,
                           const SkPoint& strokeSize,
                           const SkRegion* clip,
                           SkBlitter* blitter);
```

**功能**: 绘制带指定线宽的反走样矩形框

## 内部实现细节

### 坐标系统与精度

使用 **SkFDot6**(26.6 定点数)提供亚像素精度:

```cpp
SkFDot6 x0 = SkScalarToFDot6(pts[0].fX);  // 26位整数 + 6位小数
SkFDot6 coverage = SK_FDot6One;           // 64 表示 100% 覆盖
```

### 覆盖率计算

```cpp
// 将 FDot6 小数部分转换为 0-255 alpha 值
static inline U8CPU fixed_to_alpha(SkFixed f) {
    return (f >> 8) & 0xFF;
}

// 根据覆盖率缩放 alpha
static inline U8CPU scale_alpha_by_coverage(U8CPU value, SkFDot6 coverage) {
    return (value * coverage) >> 6;  // 除以 64
}
```

### 斜率分类与 Blitter 选择

```cpp
void do_anti_hairline(SkFDot6 x0, SkFDot6 y0, SkFDot6 x1, SkFDot6 y1, ...) {
    if (SkAbs32(x1 - x0) > SkAbs32(y1 - y0)) {  // 近水平
        if (y0 == y1) {
            hairBlitter = &hline_blitter;   // 完全水平
        } else {
            hairBlitter = &horish_blitter;  // 近水平
            slope = fastfixdiv(y1 - y0, x1 - x0);
        }
    } else {  // 近垂直
        if (x0 == x1) {
            hairBlitter = &vline_blitter;   // 完全垂直
        } else {
            hairBlitter = &vertish_blitter; // 近垂直
            slope = fastfixdiv(x1 - x0, y1 - y0);
        }
    }
}
```

### 递归细分优化

避免超长线段溢出:

```cpp
if (SkAbs32(x1 - x0) > SkIntToFDot6(511) ||
    SkAbs32(y1 - y0) > SkIntToFDot6(511)) {
    // 递归细分为两段
    int hx = (x0 >> 1) + (x1 >> 1);
    int hy = (y0 >> 1) + (y1 >> 1);
    do_anti_hairline(x0, y0, hx, hy, clip, blitter);
    do_anti_hairline(hx, hy, x1, y1, clip, blitter);
    return;
}
```

### 端点覆盖率处理

```cpp
// 部分像素覆盖率计算
static SkFDot6 partial_pixel_coverage(SkFDot6 pos) {
    int result = fd6_frac(pos - 1) + 1;  // 如果 pos 在像素边界,返回 64
    return result;  // 范围 [1, 64]
}
```

### 裁剪优化

```cpp
// 预裁剪检查
if (clip) {
    if (istart >= clip->fRight || istop <= clip->fLeft) {
        return;  // 完全在裁剪区域外
    }

    // Y 范围检查
    if (top >= clip->fBottom || bottom <= clip->fTop) {
        return;
    }

    // 如果完全包含,禁用裁剪以加速
    if (clip->fTop <= top && clip->fBottom >= bottom) {
        clip = nullptr;
    }
}
```

### 矩形框绘制策略

`AntiFrameRect` 分三层处理:

1. **外壳层**: 外边界的反走样边缘
2. **中间层**: 实心填充区域(4条矩形)
3. **内壳层**: 内边界的反走样边缘(使用反向 alpha)

```cpp
// 外壳反走样
antifilldot8(outerL, outerT, outerR, outerB, blitter, false);

// 中间实心部分(分4条填充)
fillcheckrect(outer.fLeft, outer.fTop, outer.fRight, inner.fTop, blitter);  // 上
fillcheckrect(outer.fLeft, inner.fTop, inner.fLeft, inner.fBottom, blitter); // 左
fillcheckrect(inner.fRight, inner.fTop, outer.fRight, inner.fBottom, blitter); // 右
fillcheckrect(outer.fLeft, inner.fBottom, outer.fRight, outer.fBottom, blitter); // 下

// 内壳反走样(反向 alpha)
innerstrokedot8(innerL, innerT, innerR, innerB, blitter);
```

### 子像素线宽对齐

对于 < 1 像素的线宽,确保边缘对齐避免重复绘制:

```cpp
static inline void align_thin_stroke(FDot8& edge1, FDot8& edge2) {
    if (FDot8Floor(edge1) == FDot8Floor(edge2)) {
        // 两边在同一像素内,对齐到像素边界
        edge2 -= (edge1 & 0xFF);
        edge1 &= ~0xFF;
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkBlitter` | 像素级绘制接口 |
| `SkFDot6` | 26.6 定点数运算 |
| `SkLineClipper` | 直线裁剪算法 |
| `SkRasterClip` | 光栅裁剪区域 |
| `SkRegion` | 复杂裁剪区域 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SkScan` | 公共扫描转换接口 |
| `SkDraw` | 高层绘制命令调度 |
| `SkCanvas` | 用户绘图 API |

## 设计模式与设计决策

### 1. 策略模式

不同斜率使用不同的 `SkAntiHairBlitter` 子类:
- **水平/垂直**: 特化实现,无斜率计算
- **近水平/近垂直**: 每像素更新一个坐标

### 2. 模板方法模式

基类定义绘制流程,子类实现具体策略:

```cpp
class SkAntiHairBlitter {
    // 模板方法
    void draw_full_line() {
        drawCap(...);        // 起点
        drawLine(...);       // 主体
        drawCap(...);        // 终点
    }

    // 子类实现
    virtual SkFixed drawCap(...) = 0;
    virtual SkFixed drawLine(...) = 0;
};
```

### 3. 亚像素精度权衡

**为什么用 FDot6?**
- **精度**: 1/64 像素精度足够反走样
- **性能**: 整数运算比浮点快
- **范围**: 26 位整数可表示 [-2^25, 2^25] 像素

**为什么用 FDot8(24.8) 填充矩形?**
- 更高精度用于边缘混合
- 8 位小数直接映射到 256 级 alpha

## 性能考量

### 1. 批量绘制优化

`call_hline_blitter` 使用栈缓冲区批量处理:

```cpp
#define HLINE_STACK_BUFFER 100

void call_hline_blitter(..., int count, U8CPU alpha) {
    int16_t runs[HLINE_STACK_BUFFER + 1];
    uint8_t aa[HLINE_STACK_BUFFER];

    do {
        int n = std::min(count, HLINE_STACK_BUFFER);
        runs[0] = n;
        runs[n] = 0;
        aa[0] = alpha;
        blitter->blitAntiH(x, y, aa, runs);
        count -= n;
        x += n;
    } while (count > 0);
}
```

### 2. 快速定点除法

```cpp
static inline SkFixed fastfixdiv(SkFDot6 a, SkFDot6 b) {
    SkASSERT((SkLeftShift(a, 16) >> 16) == a);  // 无溢出
    return SkLeftShift(a, 16) / b;              // (a << 16) / b
}
```

### 3. 裁剪快速路径

- **完全包含**: 跳过逐像素裁剪检查
- **快速拒绝**: 边界检查避免绘制空白区域

### 4. 特化优化

水平/垂直线避免斜率计算:

```cpp
if (y0 == y1) {  // 完全水平
    slope = 0;
    fstart = SkFDot6ToFixed(y0);
    hairBlitter = &hline_blitter;  // 无需每像素计算 Y
}
```

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkScan_Antihair.cpp` | 本文件(反走样细线实现) |
| `src/core/SkScan_Hairline.cpp` | 非反走样细线实现 |
| `src/core/SkScan_Path.cpp` | 路径填充扫描转换 |
| `src/core/SkBlitter.h` | 像素填充接口 |
| `src/core/SkFDot6.h` | 定点数定义和运算 |
| `src/core/SkLineClipper.h` | 直线裁剪工具 |
| `src/core/SkRasterClip.h` | 光栅裁剪管理 |
