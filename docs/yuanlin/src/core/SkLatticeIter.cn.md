# SkLatticeIter

> 源文件
> - src/core/SkLatticeIter.h
> - src/core/SkLatticeIter.cpp

## 概述

`SkLatticeIter` 是 Skia 中用于实现九宫格(Nine-Patch)绘制的迭代器类。它将一个带有可伸缩和固定区域的源图像分割成多个矩形片段,并计算每个片段应该如何映射到目标区域。这种技术广泛用于 UI 元素的绘制,如按钮、对话框背景等,可以在不失真的情况下拉伸图像。

该类的核心功能是将复杂的 Lattice(格子)结构分解为一系列简单的源矩形到目标矩形的映射对,使得绘制代码可以逐个处理这些映射,而不需要理解整个 Lattice 的复杂逻辑。

## 架构位置

`SkLatticeIter` 在 Skia 渲染管道中的位置:

```
应用层 (UI 框架)
    ↓
SkCanvas::drawImageLattice() / drawBitmapNine()
    ↓
SkLatticeIter (分解为 src/dst 矩形对)
    ↓
SkDevice::drawImageRect() (逐个绘制矩形)
    ↓
GPU/CPU 后端
```

它是连接高层 Lattice API 和底层矩形绘制的关键桥梁。

## 主要类与结构体

### SkLatticeIter

**继承关系:**
- 无继承,独立类

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fSrcX | TArray&lt;int&gt; | 源图像 X 方向的分割点 |
| fSrcY | TArray&lt;int&gt; | 源图像 Y 方向的分割点 |
| fDstX | TArray&lt;SkScalar&gt; | 目标矩形 X 方向的分割点 |
| fDstY | TArray&lt;SkScalar&gt; | 目标矩形 Y 方向的分割点 |
| fRectTypes | TArray&lt;SkCanvas::Lattice::RectType&gt; | 每个矩形的类型(普通/透明/固定颜色) |
| fColors | TArray&lt;SkColor&gt; | 固定颜色矩形的颜色值 |
| fCurrX | int | 当前迭代的 X 索引 |
| fCurrY | int | 当前迭代的 Y 索引 |
| fNumRectsInLattice | int | Lattice 中的矩形总数 |
| fNumRectsToDraw | int | 需要实际绘制的矩形数(排除透明矩形) |

## 公共 API 函数

### Valid (Lattice 版本)

```cpp
static bool Valid(int imageWidth, int imageHeight, const SkCanvas::Lattice& lattice);
```

**功能:** 验证 Lattice 定义是否有效。

**验证规则:**
1. Lattice 边界必须在图像范围内
2. 分割线必须严格递增,无重复
3. 至少有一个方向有有效的分割(X 或 Y)
4. 所有分割值必须在边界范围内

**返回值:** 验证通过返回 true,否则返回 false。

### Valid (Nine-Patch 版本)

```cpp
static bool Valid(int imageWidth, int imageHeight, const SkIRect& center);
```

**功能:** 验证九宫格中心矩形是否有效。

**验证规则:**
1. center 不能为空
2. center 必须完全包含在图像边界内

### 构造函数 (Lattice 版本)

```cpp
SkLatticeIter(const SkCanvas::Lattice& lattice, const SkRect& dst);
```

**功能:** 从 Lattice 定义创建迭代器。

**处理流程:**
1. 提取并处理 X/Y 分割线
2. 识别可伸缩和固定区域
3. 计算目标空间的分割点
4. 处理 RectTypes 和 Colors(如果存在)
5. 统计需要绘制的矩形数量

### 构造函数 (Nine-Patch 版本)

```cpp
SkLatticeIter(int imageWidth, int imageHeight, const SkIRect& center, const SkRect& dst);
```

**功能:** 从九宫格中心矩形创建迭代器。

**简化逻辑:**
- 自动创建 4x4 的分割点数组
- 中心区域是可伸缩的
- 四个角是固定的
- 四条边根据比例缩放

### next

```cpp
bool next(SkIRect* src, SkRect* dst, bool* isFixedColor = nullptr, SkColor* fixedColor = nullptr);
```

**功能:** 获取下一个要绘制的矩形对。

**返回值:**
- true: 成功获取下一个矩形对
- false: 已经遍历完所有矩形

**行为:**
- 自动跳过透明矩形
- 返回源矩形(整数坐标)和目标矩形(浮点坐标)
- 可选返回是否为固定颜色及其颜色值

**重载版本:**
```cpp
bool next(SkRect* src, SkRect* dst, bool* isFixedColor = nullptr, SkColor* fixedColor = nullptr);
```

将源矩形转换为浮点坐标返回。

### mapDstScaleTranslate

```cpp
void mapDstScaleTranslate(const SkMatrix& matrix);
```

**功能:** 对目标分割点应用缩放和平移变换。

**限制:** 矩阵必须是缩放+平移类型(通过 assert 检查)。

**用途:** 支持在不同坐标系中使用同一个迭代器。

### numRectsToDraw

```cpp
int numRectsToDraw() const;
```

**功能:** 返回需要实际绘制的矩形数量(排除透明矩形)。

## 内部实现细节

### 分割线处理逻辑

**处理可伸缩区域的前导零:**

```cpp
bool xIsScalable = (xCount > 0 && src.fLeft == xDivs[0]);
if (xIsScalable) {
    xDivs++;  // 跳过第一个分割线
    xCount--;
}
```

如果第一个分割线与边界重合,说明第一个区域是可伸缩的,分割线可以省略。

### 像素计数

`count_scalable_pixels()` 函数计算可伸缩像素和固定像素的数量:

```cpp
static int count_scalable_pixels(const int32_t* divs, int numDivs, bool firstIsScalable,
                                 int start, int end)
```

**逻辑:**
- 遍历所有分割区间
- 根据 `firstIsScalable` 确定每个区间是固定还是可伸缩
- 交替计数可伸缩和固定区间

### 分割点计算

`set_points()` 函数是核心算法,计算源和目标空间的分割点:

```cpp
static void set_points(float* dst, int* src, const int* divs, int divCount, int srcFixed,
                       int srcScalable, int srcStart, int srcEnd, float dstStart, float dstEnd,
                       bool isScalable)
```

**两种缩放模式:**

1. **正常模式 (srcFixed <= dstLen):**
   ```cpp
   scale = (dstLen - srcFixed) / srcScalable;
   ```
   - 固定区域保持原始大小
   - 可伸缩区域按比例缩放

2. **压缩模式 (srcFixed > dstLen):**
   ```cpp
   scale = dstLen / srcFixed;
   ```
   - 可伸缩区域被消除(设为 0)
   - 固定区域按比例缩小

**迭代计算:**
```cpp
for (int i = 0; i < divCount; i++) {
    src[i + 1] = divs[i];
    int srcDelta = src[i + 1] - src[i];
    float dstDelta = isScalable ? scale * srcDelta : srcDelta;
    dst[i + 1] = dst[i] + dstDelta;
    isScalable = !isScalable;  // 交替
}
```

### RectTypes 和 Colors 处理

如果 Lattice 包含 RectTypes:

```cpp
if (lattice.fRectTypes) {
    fRectTypes.push_back_n(fNumRectsInLattice);
    fColors.push_back_n(fNumRectsInLattice);
    // 复制并调整索引...
}
```

**处理 padding:**
- 如果第一行/列是 padding,跳过对应的 flags 和 colors
- 映射原始索引到压缩后的索引

**透明矩形统计:**
```cpp
for (int j = 0; j < fRectTypes.size(); j++) {
    if (SkCanvas::Lattice::kTransparent == fRectTypes[j]) {
        fNumRectsToDraw--;
    }
}
```

### Nine-Patch 特殊处理

Nine-Patch 构造函数创建固定的 4x4 点阵:

```cpp
fSrcX[0] = 0;
fSrcX[1] = SkIntToScalar(c.fLeft);
fSrcX[2] = SkIntToScalar(c.fRight);
fSrcX[3] = SkIntToScalar(w);
```

**重叠处理:**
如果目标太小导致中心区域重叠:

```cpp
if (fDstX[1] > fDstX[2]) {
    fDstX[1] = fDstX[0] + (fDstX[3] - fDstX[0]) * c.fLeft / (w - c.width());
    fDstX[2] = fDstX[1];
}
```

将中心区域压缩为零宽度,保持比例。

### 迭代状态管理

```cpp
bool SkLatticeIter::next(SkIRect* src, SkRect* dst, ...) {
    int currRect = fCurrX + fCurrY * (fSrcX.size() - 1);
    if (currRect == fNumRectsInLattice) {
        return false;  // 迭代结束
    }

    const int x = fCurrX;
    const int y = fCurrY;

    // 更新索引
    if (fSrcX.size() - 1 == ++fCurrX) {
        fCurrX = 0;
        fCurrY += 1;
    }

    // 跳过透明矩形
    if (fRectTypes[currRect] == kTransparent) {
        return this->next(src, dst, ...);  // 递归跳过
    }

    // 设置输出
    src->setLTRB(fSrcX[x], fSrcY[y], fSrcX[x + 1], fSrcY[y + 1]);
    dst->setLTRB(fDstX[x], fDstY[y], fDstX[x + 1], fDstY[y + 1]);
    ...
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkCanvas::Lattice | Lattice 定义结构 |
| SkRect / SkIRect | 矩形表示 |
| SkMatrix | 坐标变换 |
| SkColor | 颜色定义 |
| skia_private::TArray | 动态数组 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkCanvas | drawImageLattice(), drawBitmapNine() |
| SkDevice | 设备层 Lattice 实现 |
| SkBitmapDevice | CPU 渲染路径 |
| SkGpuDevice | GPU 渲染路径 |

## 设计模式与设计决策

### 迭代器模式

`SkLatticeIter` 是标准迭代器模式的实现:
- **封装遍历逻辑:** 隐藏复杂的 Lattice 分解算法
- **统一接口:** `next()` 方法提供简单一致的访问方式
- **无需知道内部结构:** 使用者不需要理解 fSrcX, fDstX 等内部细节

### 预计算优化

在构造函数中预计算所有分割点:
- **优势:** `next()` 调用非常快,只是简单的数组索引
- **劣势:** 初始化时间较长,占用更多内存

**权衡决策:** 绘制 Lattice 通常涉及多个矩形,预计算的一次性开销远小于每次 `next()` 时重新计算的累积开销。

### 两阶段验证

分离验证和构造:
```cpp
if (!SkLatticeIter::Valid(...)) {
    return;  // 早期拒绝
}
SkLatticeIter iter(lattice, dst);  // 假设已验证
```

**优势:**
- 允许早期失败,避免构造无效对象
- 构造函数可以使用 SkASSERT 而不是运行时检查

### Nine-Patch 作为 Lattice 的特例

Nine-Patch 可以视为特殊的 Lattice:
- 固定 2 个 X 分割和 2 个 Y 分割
- 中心区域可伸缩,四角固定

**设计决策:** 提供专门的 Nine-Patch 构造函数,而不是要求用户手动构造等价的 Lattice。

## 性能考量

### 内存预分配

使用 `TArray` 的 `reset()` 方法预分配内存:

```cpp
fSrcX.reset(xCount + 2);
fDstX.reset(xCount + 2);
```

避免了动态扩容的开销。

### 透明矩形跳过

通过递归跳过透明矩形:
```cpp
if (SkCanvas::Lattice::kTransparent == fRectTypes[currRect]) {
    return this->next(src, dst, isFixedColor, fixedColor);
}
```

**优势:** 调用者不需要知道透明矩形的存在
**劣势:** 可能导致深度递归(如果有连续大量透明矩形)

### 浮点精度考虑

分割点计算使用浮点数:
```cpp
float dstDelta = isScalable ? scale * srcDelta : srcDelta;
```

即使固定区域也使用浮点计算,可能导致微小的累积误差。但对于典型的 UI 绘制,这种误差可以忽略。

### 缓存友好的内存布局

分割点存储在连续数组中:
```cpp
skia_private::TArray<int> fSrcX;
skia_private::TArray<SkScalar> fDstX;
```

迭代访问时,缓存局部性良好。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkCanvas.h | 依赖 | Lattice 结构定义 |
| include/core/SkRect.h | 依赖 | 矩形类型 |
| include/core/SkMatrix.h | 依赖 | 矩阵变换 |
| src/core/SkDevice.h | 使用者 | 设备层绘制 |
| src/core/SkBitmapDevice.cpp | 使用者 | CPU 渲染实现 |
| src/gpu/ganesh/SkGpuDevice.cpp | 使用者 | GPU 渲染实现 |
