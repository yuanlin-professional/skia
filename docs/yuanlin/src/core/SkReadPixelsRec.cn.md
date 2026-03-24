# SkReadPixelsRec

> 源文件: src/core/SkReadPixelsRec.h, src/core/SkReadPixelsRec.cpp

## 概述

`SkReadPixelsRec` 是一个辅助结构体,用于打包和裁剪 `readPixels()` 操作的参数。它封装了像素数据指针、行字节数、图像信息和读取位置,并提供 `trim` 方法来确保读取区域在源图像范围内。该结构体简化了像素读取操作的参数传递和验证逻辑。

## 架构位置

`SkReadPixelsRec` 位于 Skia 核心绘图引擎的像素访问层:
- 被 `SkCanvas::readPixels` 和 `SkSurface::readPixels` 内部使用
- 与 `SkPixmap` 紧密关联
- 处理像素读取操作的参数规范化
- 确保跨边界读取的正确性

## 主要类与结构体

### SkReadPixelsRec

**继承关系:** 独立结构体(非继承)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPixels` | `void*` | 目标像素缓冲区指针 |
| `fRowBytes` | `size_t` | 每行的字节数(stride) |
| `fInfo` | `SkImageInfo` | 目标图像信息(格式、尺寸、色彩空间) |
| `fX` | `int` | 源图像中的 X 坐标 |
| `fY` | `int` | 源图像中的 Y 坐标 |

## 公共 API 函数

### 构造函数

```cpp
SkReadPixelsRec(const SkImageInfo& info, void* pixels, size_t rowBytes, int x, int y)
```

**参数:**
- `info`: 目标像素格式和尺寸
- `pixels`: 目标缓冲区指针
- `rowBytes`: 每行字节数
- `x, y`: 在源图像中的读取起始位置

**用途:** 直接构造读取记录。

```cpp
SkReadPixelsRec(const SkPixmap& pm, int x, int y)
```

**参数:**
- `pm`: 提供目标缓冲区信息的 SkPixmap
- `x, y`: 在源图像中的读取起始位置

**用途:** 从 SkPixmap 构造,更便捷的接口。

### trim 方法

```cpp
bool trim(int srcWidth, int srcHeight)
```

**功能:** 裁剪读取区域以确保在源图像边界内。

**返回值:**
- `true`: 存在有效的重叠区域,参数已调整
- `false`: 无重叠或参数无效,结构体未修改

**调整逻辑:**
1. 验证基本有效性(非空指针、合理的 rowBytes、正尺寸)
2. 计算请求区域与源图像的交集
3. 调整 `fPixels` 指向实际读取的起始位置
4. 更新 `fInfo` 尺寸为实际读取大小
5. 更新 `fX` 和 `fY` 为裁剪后的源坐标

## 内部实现细节

### trim 实现分析

#### 1. 基本验证

```cpp
if (nullptr == fPixels || fRowBytes < fInfo.minRowBytes()) {
    return false;
}
if (0 >= fInfo.width() || 0 >= fInfo.height()) {
    return false;
}
```

检查:
- 像素指针非空
- rowBytes 至少满足最小要求
- 请求的宽高为正数

#### 2. 交集计算

```cpp
SkIRect srcR = SkIRect::MakeXYWH(x, y, fInfo.width(), fInfo.height());
if (!srcR.intersect({0, 0, srcWidth, srcHeight})) {
    return false;
}
```

使用 `SkIRect` 计算请求区域与源图像 `[0, 0, srcWidth, srcHeight)` 的交集。

#### 3. 指针调整

```cpp
if (x > 0) {
    x = 0;
}
if (y > 0) {
    y = 0;
}
// x, y 现在是 0 或负数
fPixels = ((char*)fPixels + -y*fRowBytes + -x*fInfo.bytesPerPixel());
```

**关键点:**
- 如果 `x` 或 `y` 为负(请求区域在源图像左上方开始),需要调整目标指针
- 将 `x` 和 `y` 转换为偏移量(负值)
- 使用 `-y*fRowBytes` 和 `-x*fInfo.bytesPerPixel()` 避免 UBSAN 的指针溢出警告
- 实际上是 `fPixels += abs(y)*fRowBytes + abs(x)*fInfo.bytesPerPixel()`

#### 4. 参数更新

```cpp
fInfo = fInfo.makeDimensions(srcR.size());
fX = srcR.x();
fY = srcR.y();
```

- 更新 `fInfo` 的尺寸为实际读取大小
- 更新 `fX` 和 `fY` 为裁剪后的源坐标

### 指针算术技巧

代码使用 `-y*fRowBytes + -x*fInfo.bytesPerPixel()` 而非 `abs(y)*fRowBytes + abs(x)*fInfo.bytesPerPixel()` 的原因:

1. **UBSAN 兼容:** 避免触发指针溢出检查
2. **统一处理:** 当 `x` 和 `y` 为 0 或正数时,计算结果为 0
3. **性能:** 避免条件分支和 abs 函数调用

### 边界情况处理

- **完全不重叠:** `srcR.intersect` 返回 false
- **部分重叠:** 调整所有参数以反映实际可读区域
- **完全包含:** 参数保持不变(除非 x/y 为负)
- **负坐标:** 通过指针偏移正确处理

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkImageInfo` | 描述像素格式和尺寸 |
| `SkPixmap` | 提供便捷的构造接口 |
| `SkRect` | 计算区域交集 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkCanvas` | readPixels 内部使用 |
| `SkSurface` | readPixels 内部使用 |
| `SkBitmap` | readPixels 内部使用 |
| `SkImage` | readPixels 内部使用 |

## 设计模式与设计决策

### 1. 参数对象(Parameter Object)
将多个相关参数打包到单个结构体,简化函数签名。

### 2. 就地修改(In-Place Modification)
`trim` 方法直接修改成员变量,避免创建新对象。

### 3. 早期返回(Early Return)
验证失败时立即返回 false,避免不必要的计算。

### 4. 防御性编程
验证所有输入参数,防止崩溃和未定义行为。

### 5. 值语义(Value Semantics)
作为简单结构体,支持拷贝和按值传递。

### 6. 辅助工具类(Utility Class)
不是核心抽象,而是简化参数处理的工具。

## 性能考量

### 1. 结构体紧凑性
成员变量精简,结构体大小约 32-40 字节,适合栈分配。

### 2. 避免分配
所有操作就地进行,无需动态内存分配。

### 3. 分支预测
验证逻辑简单,分支预测友好。

### 4. 指针算术优化
使用加法和乘法代替条件分支,提高效率。

### 5. 内联友好
所有方法体积小,适合内联优化。

### 6. 缓存友好
结构体小且数据相关,提高缓存命中率。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkImageInfo.h` | 图像信息定义 |
| `include/core/SkPixmap.h` | 像素映射 |
| `include/core/SkRect.h` | 矩形和交集计算 |
| `include/core/SkCanvas.h` | readPixels 使用者 |
| `include/core/SkSurface.h` | readPixels 使用者 |
| `include/core/SkBitmap.h` | readPixels 使用者 |
| `include/core/SkImage.h` | readPixels 使用者 |
