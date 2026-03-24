# AffineMatrix

> 源文件
> - src/gpu/tessellate/AffineMatrix.h

## 概述

`AffineMatrix` 是 Skia GPU 镶嵌化系统中用于高效执行仿射 2D 变换的 SIMD 优化类。它使用向量指令同时变换多个点，并确保无论使用哪种方法调用，点都能以相同方式映射，保证结果的一致性。

核心特点：
- 使用 SIMD（单指令多数据）向量化计算
- 可同时变换 1 或 2 个点
- 存储冗余数据以优化 SIMD 操作
- 仅用作栈分配对象，在使用点进行临时计算

该类通过将变换矩阵复制到 float4 的低位和高位，实现了高效的双点变换，这在路径镶嵌化中处理贝塞尔曲线控制点时非常有用。

## 架构位置

```
skgpu::tess (镶嵌化渲染)
  ├── AffineMatrix (仿射变换 - 本类)
  ├── PatchWriter (使用 AffineMatrix 变换控制点)
  ├── PathCurveTessellator (曲线镶嵌器)
  └── StrokeTessellator (描边镶嵌器)
```

## 主要类与方法

### 构造和赋值

```cpp
AffineMatrix() = default;
AffineMatrix(const SkMatrix& m) { *this = m; }
AffineMatrix& operator=(const SkMatrix& m)
```

**功能：** 从 `SkMatrix` 构造或赋值。

**实现：**
- 断言矩阵不包含透视变换（仿射变换仅支持缩放、旋转、倾斜和平移）
- 将矩阵元素复制到 float4 的低位和高位：
  ```cpp
  fScale = float2(scaleX, scaleY).xyxy();  // [scaleX, scaleY, scaleX, scaleY]
  fSkew = float2(skewX, skewY).xyxy();     // [skewX, skewY, skewX, skewY]
  fTrans = float2(transX, transY).xyxy();  // [transX, transY, transX, transY]
  ```

### map2Points (float4 重载)

```cpp
SK_ALWAYS_INLINE skvx::float4 map2Points(skvx::float4 p0p1) const
```

**功能：** 同时变换两个点，输入为打包的 float4 [x0, y0, x1, y1]。

**实现：**
```cpp
return fScale * p0p1 + (fSkew * p0p1.yxwz() + fTrans);
```

**分解：**
- `fScale * p0p1` → [scaleX*x0, scaleY*y0, scaleX*x1, scaleY*y1]
- `p0p1.yxwz()` → [y0, x0, y1, x1] （交换 x 和 y）
- `fSkew * p0p1.yxwz()` → [skewX*y0, skewY*x0, skewX*y1, skewY*x1]
- 最终：[(scaleX*x0 + skewX*y0 + transX), (scaleY*y0 + skewY*x0 + transY), ...]

### map2Points (数组重载)

```cpp
SK_ALWAYS_INLINE skvx::float4 map2Points(const SkPoint pts[2]) const
```

**功能：** 从数组加载两个点并变换。

**实现：** 调用 `skvx::float4::Load(pts)` 加载内存中的点，然后调用上面的 float4 重载。

### map2Points (两个 SkPoint 重载)

```cpp
SK_ALWAYS_INLINE skvx::float4 map2Points(SkPoint p0, SkPoint p1) const
```

**功能：** 变换两个独立的 `SkPoint` 对象。

**实现：** 使用 `sk_bit_cast` 将 `SkPoint` 转换为 `float2`，构造 float4，然后调用主变换函数。

### mapPoint (float2 重载)

```cpp
SK_ALWAYS_INLINE skvx::float2 mapPoint(skvx::float2 p) const
```

**功能：** 变换单个点（float2 向量）。

**实现：**
```cpp
return fScale.lo * p + (fSkew.lo * p.yx() + fTrans.lo);
```

使用 `fScale.lo`、`fSkew.lo`、`fTrans.lo` 提取 float4 的低两个分量（对应单点变换的参数）。

### map1Point

```cpp
SK_ALWAYS_INLINE skvx::float2 map1Point(const SkPoint pt[1]) const
```

**功能：** 从数组加载一个点并变换。

### mapPoint (SkPoint 重载)

```cpp
SK_ALWAYS_INLINE SkPoint mapPoint(SkPoint p) const
```

**功能：** 变换单个 `SkPoint` 对象，返回 `SkPoint`。

**实现：** 使用 `sk_bit_cast` 在 `SkPoint` 和 `float2` 之间转换。

## 内部实现细节

### 数据成员

```cpp
private:
    skvx::float4 fScale;  // [scaleX, scaleY, scaleX, scaleY]
    skvx::float4 fSkew;   // [skewX, skewY, skewX, skewY]
    skvx::float4 fTrans;  // [transX, transY, transX, transY]
```

**存储策略：**
- 使用 float4 存储，虽然每个参数只有两个独特值
- 低两个分量用于单点变换
- 完整的四个分量用于双点变换
- 这种冗余存储换取了 SIMD 性能

### 仿射变换公式

标准仿射变换：
```
x' = scaleX * x + skewX * y + transX
y' = skewY * x + scaleY * y + transY
```

SIMD 向量化实现：
```cpp
result = fScale * input + (fSkew * input.yx() + fTrans);
```

通过交换 x 和 y 分量（`.yx()`），一次 SIMD 操作完成所有乘加运算。

### SK_ALWAYS_INLINE

所有方法都标记为 `SK_ALWAYS_INLINE`，确保编译器内联这些小函数，减少函数调用开销，充分发挥 SIMD 性能。

## 依赖关系

### 依赖的头文件

| 头文件 | 用途 |
|--------|------|
| `include/core/SkMatrix.h` | `SkMatrix` 类型 |
| `include/core/SkPoint.h` | `SkPoint` 类型 |
| `src/base/SkVx.h` | SIMD 向量类型（float2、float4） |
| `src/base/SkUtils.h` | `sk_bit_cast` 位转换函数 |

### 被依赖关系

- **PatchWriter** - 变换曲线控制点
- **PathCurveTessellator** - 变换路径顶点
- **StrokeTessellator** - 变换描边控制点

## 设计模式与决策

### 栈分配设计

类注释明确说明"最好仅用作栈分配对象"，因为：
- 存储冗余数据（12 个 float，实际只需 6 个）
- 不适合长期存储
- 作为临时对象在使用点创建和销毁

### SIMD 优化

通过冗余存储和 SIMD 指令：
- 单点变换：4 次 float 乘法 + 4 次加法（向量化为 2-3 条指令）
- 双点变换：8 次 float 乘法 + 8 次加法（向量化为 3-4 条指令）
- 与标量代码相比，性能提升 2-4 倍

### 一致性保证

类注释强调"无论使用哪种方法，都以相同方式映射点"，这对于：
- 避免浮点精度差异导致的视觉瑕疵
- 确保镶嵌化结果的确定性
- 简化测试和调试

### 位转换模式

使用 `sk_bit_cast` 在 `SkPoint` 和 `skvx::float2` 之间转换：
- 零开销（编译时消除）
- 类型安全
- 避免拷贝构造

## 性能考量

### SIMD 加速

现代 CPU 的 SIMD 指令集（SSE、AVX、NEON）可以在单周期内执行 4-8 个浮点操作，使得双点变换几乎与单点变换一样快。

### 内存局部性

将两个点打包在 float4 中，提高缓存命中率和内存带宽利用率。

### 编译器优化

- `SK_ALWAYS_INLINE` 确保内联
- SIMD 向量化自动利用 CPU 指令集
- 编译器可以进一步优化向量操作流水线

### 使用场景

最适合：
- 循环中变换大量点
- 处理贝塞尔曲线（通常有 2-4 个控制点）
- 需要高吞吐量的路径处理

不适合：
- 偶尔变换单个点
- 需要长期存储变换矩阵

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/tessellate/PatchWriter.h` | 使用者 | 使用 AffineMatrix 变换补丁控制点 |
| `src/gpu/tessellate/PathCurveTessellator.h` | 使用者 | 曲线镶嵌器 |
| `src/gpu/tessellate/StrokeTessellator.h` | 使用者 | 描边镶嵌器 |
| `src/base/SkVx.h` | 基础设施 | SIMD 向量类型 |
| `include/core/SkMatrix.h` | 输入类型 | 标准 Skia 矩阵 |
