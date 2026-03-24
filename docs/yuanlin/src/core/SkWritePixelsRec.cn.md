# SkWritePixelsRec

> 源文件: src/core/SkWritePixelsRec.h, src/core/SkWritePixelsRec.cpp

## 概述

`SkWritePixelsRec` 是一个辅助数据结构，用于打包和修剪传递给 `writePixels()` 方法的参数。它封装了像素写入操作所需的所有信息，包括像素数据指针、图像信息、行字节数以及目标位置坐标。该结构体的主要功能是确保像素写入区域在目标表面的有效边界内，并在必要时自动调整参数以适应目标尺寸。

此类提供了一个关键的 `trim()` 方法，用于验证和裁剪写入矩形，使其成为目标宽度/高度的合法子集。这种设计模式在图形 API 中很常见，用于保护底层绘制操作免受非法或越界参数的影响。

## 架构位置

`SkWritePixelsRec` 位于 Skia 核心层（`src/core`），是像素操作基础设施的一部分。它作为一个中间层，在高层像素写入 API 和底层绘制设备之间传递和验证参数。该结构体不直接被应用层使用，而是被 Skia 内部的各种设备和表面实现所使用。

在 Skia 的渲染管线中，当应用程序调用 `SkCanvas::writePixels()` 或 `SkSurface::writePixels()` 时，这些高层方法会创建一个 `SkWritePixelsRec` 实例来封装和验证参数，然后将其传递给底层的设备特定实现。

## 主要类与结构体

### SkWritePixelsRec

像素写入参数的打包和验证结构体。

**继承关系**
- 无继承（普通结构体）

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPixels` | `const void*` | 指向源像素数据的指针 |
| `fRowBytes` | `size_t` | 每行像素数据的字节数（包括可能的填充） |
| `fInfo` | `SkImageInfo` | 描述源像素格式的图像信息 |
| `fX` | `int` | 写入目标的 X 坐标 |
| `fY` | `int` | 写入目标的 Y 坐标 |

## 公共 API 函数

### 构造函数

```cpp
SkWritePixelsRec(const SkImageInfo& info, const void* pixels, size_t rowBytes, int x, int y)
```
从独立参数构造 `SkWritePixelsRec`。

**参数说明**
- `info`: 像素数据的格式信息
- `pixels`: 源像素数据指针
- `rowBytes`: 每行字节数
- `x`, `y`: 目标位置坐标

```cpp
SkWritePixelsRec(const SkPixmap& pm, int x, int y)
```
从 `SkPixmap` 构造 `SkWritePixelsRec`。这是一个便利构造函数，直接从 `SkPixmap` 提取所有必要的信息。

### trim() 方法

```cpp
bool trim(int dstWidth, int dstHeight)
```
验证和调整写入矩形，使其成为目标尺寸的合法子集。

**返回值**
- `true`: 参数有效且与目标有重叠（可能已修改成员以适应边界）
- `false`: 参数无效或与目标无重叠

**功能说明**
- 验证像素指针非空且行字节数满足最小要求
- 验证源图像尺寸为正数
- 计算源矩形与目标矩形的交集
- 如果坐标为负，调整像素指针以指向正确的起始位置
- 更新 `fInfo`、`fX`、`fY` 以反映裁剪后的区域

## 内部实现细节

### trim() 的边界裁剪逻辑

`trim()` 方法实现了复杂的边界处理逻辑：

1. **基础验证**
   - 检查像素指针非空
   - 验证 `fRowBytes >= fInfo.minRowBytes()`
   - 确保源图像宽度和高度都大于零

2. **交集计算**
   - 创建源矩形 `SkIRect::MakeXYWH(x, y, width, height)`
   - 与目标矩形 `{0, 0, dstWidth, dstHeight}` 求交集
   - 如果无交集，返回 `false`

3. **指针调整**（处理负坐标）
   ```cpp
   // 如果 x 或 y 为负，需要调整像素指针
   fPixels = ((const char*)fPixels + -y*fRowBytes + -x*fInfo.bytesPerPixel());
   ```
   这里使用了巧妙的技巧：将负值变为正值再相加，避免 UBSAN（未定义行为检测器）的指针溢出警告。

4. **更新参数**
   - 将 `fInfo` 调整为交集的尺寸
   - 更新 `fX` 和 `fY` 为裁剪后的坐标

### 内存布局考虑

结构体按照声明顺序存储成员，没有虚函数表，因此内存布局简单高效。`fPixels` 指针不拥有内存，仅用于引用外部数据。

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `SkImageInfo` | 描述像素格式、颜色空间、Alpha 类型 |
| `SkPixmap` | 提供像素数据的便捷包装 |
| `SkRect` | 用于矩形交集计算 |

**被依赖的模块**

| 模块 | 依赖原因 |
|------|----------|
| `SkCanvas` | 在 `writePixels()` 实现中使用 |
| `SkSurface` | 在 `writePixels()` 实现中使用 |
| `SkDevice` | 设备特定的像素写入实现 |
| `SkBaseDevice` | 基础设备抽象层 |

## 设计模式与设计决策

### 设计模式

1. **数据传输对象（DTO）模式**
   - `SkWritePixelsRec` 纯粹用于在不同层之间传递数据
   - 没有复杂的业务逻辑，只有验证和调整功能

2. **参数对象模式**
   - 将多个相关参数打包成单一对象
   - 简化函数签名，避免参数列表过长

3. **就地修改模式**
   - `trim()` 方法直接修改对象内部状态
   - 通过返回布尔值指示操作是否成功

### 设计决策

1. **使用结构体而非类**
   - 公开成员变量，避免不必要的封装开销
   - 适合作为内部使用的数据容器

2. **非拥有型指针**
   - `fPixels` 不拥有内存，调用者负责生命周期管理
   - 避免不必要的内存复制，提高性能

3. **immutable 输入，mutable 状态**
   - 构造后允许修改成员（通过 `trim()`）
   - 灵活性与性能的平衡

4. **行字节数保持不变**
   - 即使在 `trim()` 中调整了尺寸，`fRowBytes` 也不会改变
   - 注释明确指出"except fRowBytes"
   - 这是因为行字节数反映了源数据的内存布局，不能改变

## 性能考量

1. **栈分配友好**
   - 结构体小巧，适合在栈上分配
   - 避免堆分配开销

2. **零拷贝设计**
   - 不复制像素数据，仅传递指针
   - 对于大型图像数据尤其重要

3. **早期验证**
   - `trim()` 方法在实际写入前进行所有验证
   - 避免部分执行后失败导致的不一致状态

4. **SIMD 友好的行字节数**
   - 保留原始行字节数（可能包含对齐填充）
   - 有利于底层使用 SIMD 指令优化

5. **避免未定义行为**
   - 负坐标处理使用加法而非减法
   - 显式防止指针算术溢出

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `include/core/SkImageInfo.h` | 依赖 | 图像格式描述 |
| `include/core/SkPixmap.h` | 依赖 | 像素映射包装类 |
| `include/core/SkRect.h` | 依赖 | 矩形和交集计算 |
| `src/core/SkDevice.cpp` | 使用者 | 设备层像素写入实现 |
| `include/core/SkCanvas.h` | 使用者 | 公共 API 入口点 |
| `include/core/SkSurface.h` | 使用者 | 表面像素写入 API |
