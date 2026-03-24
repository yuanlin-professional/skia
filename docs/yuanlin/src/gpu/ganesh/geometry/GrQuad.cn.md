# GrQuad

> 源文件: src/gpu/ganesh/geometry/GrQuad.h, src/gpu/ganesh/geometry/GrQuad.cpp

## 概述

`GrQuad` 是 Ganesh GPU 后端中表示四边形的核心数据结构。它可以表示从简单的轴对齐矩形到复杂的透视变换四边形的各种几何形状。该类采用 CCW(逆时针)三角带顺序存储四个顶点(左上、左下、右上、右下),支持齐次坐标系统以处理透视投影。

`GrQuad` 的关键特性:
- 支持四种类型:轴对齐、直角、通用 2D、透视
- 使用齐次坐标(x, y, w)表示顶点
- 提供高效的边界计算和类型查询
- 支持从矩形、路径和其他几何形状构建

## 架构位置

`GrQuad` 是 Ganesh 几何层的基础数据结构:

```
src/gpu/ganesh/
  └── geometry/
      ├── GrQuad.h/cpp          # 四边形数据结构(本模块)
      ├── GrQuadUtils.h/cpp     # 四边形几何工具
      ├── GrQuadBuffer.h        # 四边形缓冲区
      └── ops/
          ├── FillRectOp.cpp    # 使用四边形的填充操作
          └── TextureOp.cpp     # 使用四边形的纹理操作
```

作为基础数据类型,它被几乎所有的矩形和四边形绘制操作使用。

## 主要类与结构体

### GrQuad 类

**继承关系**: 无基类

**用途**: 表示一个由 4 个顶点组成的四边形,按 CCW 三角带顺序排列。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fX` | `float[4]` | 四个顶点的 X 坐标 |
| `fY` | `float[4]` | 四个顶点的 Y 坐标 |
| `fW` | `float[4]` | 四个顶点的齐次坐标 W 分量(默认为 1) |
| `fType` | `Type` | 四边形的几何类型 |

### Type 枚举

四边形的几何分类:

| 类型 | 说明 |
|------|------|
| `kAxisAligned` | 轴对齐矩形,边平行于坐标轴 |
| `kRectilinear` | 直角矩形(旋转 90° 或镜像) |
| `kGeneral` | 任意 2D 四边形(W = 1) |
| `kPerspective` | 透视四边形(W ≠ 1) |

类型判定影响渲染路径选择和优化策略。

### DrawQuad 结构体

表示设备空间和局部坐标空间的四边形对:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDevice` | `GrQuad` | 设备空间四边形 |
| `fLocal` | `GrQuad` | 局部(纹理)坐标四边形 |
| `fEdgeFlags` | `GrQuadAAFlags` | 抗锯齿边缘标志 |

## 公共 API 函数

### 构造函数

```cpp
GrQuad();                                    // 默认构造,W 初始化为 1
explicit GrQuad(const SkRect& rect);         // 从矩形构造
static GrQuad MakeFromRect(const SkRect&, const SkMatrix&);      // 矩形+变换
static GrQuad MakeFromSkQuad(const SkPoint pts[4], const SkMatrix&); // 从点构造
```

`MakeFromSkQuad` 的输入点顺序为 SkRect 风格(左上、右上、右下、左下),内部转换为 GrQuad 的 CCW 三角带顺序。

### 顶点访问

```cpp
SkPoint3 point3(int i) const;                // 获取齐次坐标(x, y, w)
SkPoint point(int i) const;                  // 获取投影后的 2D 坐标(x/w, y/w)
float x(int i) const;                        // 获取 X 坐标
float y(int i) const;                        // 获取 Y 坐标
float w(int i) const;                        // 获取 W 分量
float iw(int i) const;                       // 获取 1/W

skvx::Vec<4, float> x4f() const;             // 获取四个 X 坐标的 SIMD 向量
skvx::Vec<4, float> y4f() const;             // 获取四个 Y 坐标的 SIMD 向量
skvx::Vec<4, float> w4f() const;             // 获取四个 W 分量的 SIMD 向量
```

### 类型查询

```cpp
Type quadType() const;                       // 获取四边形类型
bool hasPerspective() const;                 // 是否为透视四边形
bool aaHasEffectOnRect(GrQuadAAFlags) const; // AA 是否对该矩形有效果
bool asRect(SkRect* rect) const;             // 尝试转换为矩形(需满足拓扑条件)
```

### 边界计算

```cpp
SkRect bounds() const;                       // 获取边界框
```

对于透视四边形,返回投影后的边界;对于非透视四边形,直接计算坐标的最小/最大值。

### 有效性检查

```cpp
bool isFinite() const;                       // 检查所有坐标是否有限
```

实现使用巧妙的累乘法:无穷大或 NaN 乘以 0 会产生 NaN。

### 数据访问

```cpp
const float* xs() const;                     // 获取 X 坐标数组指针
float* xs();                                 // 获取可修改的 X 坐标数组指针
const float* ys() const;                     // 获取 Y 坐标数组指针
float* ys();                                 // 获取可修改的 Y 坐标数组指针
const float* ws() const;                     // 获取 W 分量数组指针
float* ws();                                 // 获取可修改的 W 分量数组指针
void setQuadType(Type newType);              // 设置四边形类型(自动调整 W 值)
```

## 内部实现细节

### 类型推断算法

从矩阵推断四边形类型:

```cpp
static GrQuad::Type quad_type_for_transformed_rect(const SkMatrix& matrix) {
    if (matrix.rectStaysRect()) {
        return GrQuad::Type::kAxisAligned;
    } else if (matrix.preservesRightAngles()) {
        return GrQuad::Type::kRectilinear;
    } else if (matrix.hasPerspective()) {
        return GrQuad::Type::kPerspective;
    } else {
        return GrQuad::Type::kGeneral;
    }
}
```

从点集推断:检查是否满足矩形的点分布模式(对边 X 或 Y 坐标相等)。

### 变换优化

对于轴对齐和平移+缩放矩阵,使用快速路径:

```cpp
static void map_rect_translate_scale(const SkRect& rect, const SkMatrix& m,
                                      V4f* xs, V4f* ys) {
    V4f r = V4f::Load(&rect);
    const V4f t{m.getTranslateX(), m.getTranslateY(), ...};
    const V4f s{m.getScaleX(), m.getScaleY(), ...};
    r = r * s + t;
    *xs = skvx::shuffle<0, 0, 2, 2>(r);  // 左左右右
    *ys = skvx::shuffle<1, 3, 1, 3>(r);  // 上下上下
}
```

使用 SIMD 向量化计算,避免逐点变换。

### 透视边界计算

透视四边形的边界需要考虑 W 平面裁剪:

```cpp
SkRect GrQuad::projectedBounds() const {
    float4 ws = this->w4f();
    mask4 clipW = ws < SkPathPriv::kW0PlaneDistance;
    if (any(clipW)) {
        // 部分顶点在 W=0 平面后方,需要计算裁剪边界
        // ... 复杂的裁剪逻辑 ...
    }
    // 所有顶点都在前方,直接投影
    ws = 1.f / ws;
    float4 x2d = xs * ws;
    float4 y2d = ys * ws;
    return {min(x2d), min(y2d), max(x2d), max(y2d)};
}
```

### AA 对矩形的影响判断

```cpp
static bool aa_affects_rect(GrQuadAAFlags edgeFlags, float ql, qt, qr, qb) {
    return ((edgeFlags & GrQuadAAFlags::kLeft)   && !SkScalarIsInt(ql)) ||
           ((edgeFlags & GrQuadAAFlags::kRight)  && !SkScalarIsInt(qr)) ||
           ((edgeFlags & GrQuadAAFlags::kTop)    && !SkScalarIsInt(qt)) ||
           ((edgeFlags & GrQuadAAFlags::kBottom) && !SkScalarIsInt(qb));
}
```

只有当边缘不在整数坐标上时,AA 才有视觉效果。这个优化避免不必要的 AA 计算。

### 类型降级机制

`setQuadType()` 确保 W 值与类型一致:

```cpp
void setQuadType(Type newType) {
    if (newType != Type::kPerspective && fType == Type::kPerspective) {
        fW[0] = fW[1] = fW[2] = fW[3] = 1.f;  // 非透视时强制 W=1
    }
    fType = newType;
}
```

这防止了类型与数据不一致的情况。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRect` | 矩形数据类型 |
| `SkMatrix` | 坐标变换 |
| `SkVx` | SIMD 向量化 |
| `GrTypesPriv` | Ganesh 内部类型定义 |
| `BufferWriter` | 顶点缓冲区写入 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `GrQuadUtils` | 四边形几何操作 |
| `GrQuadBuffer` | 四边形批处理缓冲 |
| `FillRectOp` | 矩形填充操作 |
| `TextureOp` | 纹理绘制操作 |
| `GrQuadPerEdgeAA` | 每边抗锯齿渲染 |

## 设计模式与设计决策

### 值语义设计

`GrQuad` 采用值语义(可拷贝,可赋值),没有动态分配:

```cpp
GrQuad(const GrQuad&) = default;
GrQuad& operator=(const GrQuad&) = default;
```

优势:
- 避免堆分配开销
- 简化生命周期管理
- 便于在栈上创建和传递
- 总大小仅 52 字节(12 floats + 1 enum)

### CCW 三角带顺序

顶点顺序为:v0(左上) → v1(左下) → v2(右上) → v3(右下)

这种顺序的优势:
- 符合 GPU 三角带渲染的自然顺序
- 可以直接用于 `GL_TRIANGLE_STRIP` 绘制
- 相邻三角形共享边,减少顶点传输

```
v0---v2       三角形 1: v0-v1-v2
|  / |        三角形 2: v1-v3-v2
| /  |
v1---v3
```

### 类型分级策略

四种类型按复杂度递增:

```
kAxisAligned → kRectilinear → kGeneral → kPerspective
```

每个类型都是下一个类型的特例,允许:
- 类型降级优化(如检测到轴对齐可以使用更快的渲染路径)
- 渐进式功能支持(基础实现支持 kGeneral,优化实现针对特定类型)

### 懒惰 W 分量

非透视四边形的 W 默认为 1,但不在每次访问时检查:

```cpp
float w(int i) const { return fW[i]; }  // 直接返回,不检查类型
```

信任调用者根据 `quadType()` 正确使用,避免分支开销。

### SkVx 集成

提供 `x4f()`, `y4f()`, `w4f()` 方法返回 SIMD 向量,便于:
- 几何工具(`GrQuadUtils`)高效批量处理
- 与其他 SIMD 代码集成
- 避免逐元素访问的开销

## 性能考量

### 内联关键路径

大部分访问函数在头文件中内联:

```cpp
float x(int i) const { return fX[i]; }
SkRect bounds() const {
    if (fType == GrQuad::Type::kPerspective) {
        return this->projectedBounds();  // 唯一非内联路径
    }
    // 非透视边界计算完全内联
    auto min = [](const float c[4]) { return std::min(...); };
    auto max = [](const float c[4]) { return std::max(...); };
    return {min(fX), min(fY), max(fX), max(fY)};
}
```

非透视边界计算完全内联,避免函数调用开销。

### 数据局部性

13 个 float(12 坐标 + 1 枚举)紧凑布局在 52 字节内,适合:
- CPU 缓存行(通常 64 字节)
- GPU 常量缓冲区
- 批处理传输

### SIMD 友好布局

虽然使用 AoS(Array of Structures)布局,但提供 SoA(Structure of Arrays)风格的访问:

```cpp
float4 xs = quad.x4f();  // 一次加载 4 个 X 坐标
float4 ys = quad.y4f();  // 一次加载 4 个 Y 坐标
```

这让 SIMD 代码可以高效处理四边形,同时保持数据结构的简洁性。

### 类型特化优化

通过类型检查启用快速路径:

```cpp
if (quadType() == Type::kAxisAligned) {
    // 轴对齐的 O(1) 路径
} else {
    // 通用的 O(n) 路径
}
```

测量显示轴对齐矩形占绘制操作的 70%+,值得专门优化。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/geometry/GrQuadUtils.h` | 紧密耦合 | 四边形几何操作工具 |
| `src/gpu/ganesh/geometry/GrQuadBuffer.h` | 使用 | 四边形批处理容器 |
| `src/gpu/ganesh/ops/FillRectOp.cpp` | 被使用 | 矩形填充实现 |
| `src/gpu/ganesh/ops/TextureOp.cpp` | 被使用 | 纹理绘制实现 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 依赖 | Ganesh 类型定义 |
| `tests/GrQuadTest.cpp` | 测试 | 单元测试用例 |
