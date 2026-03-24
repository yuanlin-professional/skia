# SkMatrix

> 源文件: `include/core/SkMatrix.h`, `src/core/SkMatrix.cpp`

## 概述

SkMatrix 是 Skia 中用于 2D 坐标变换的 3x3 矩阵类，支持平移、缩放、旋转、倾斜和透视变换。矩阵元素按行主序（row major order）排列，默认 constexpr 构造为单位矩阵。

SkMatrix 的内存布局紧凑（用 `SK_BEGIN_REQUIRE_DENSE` 标记），包含 9 个 `SkScalar`（float）值和一个隐藏的类型掩码变量 `fTypeMask`。类型掩码对矩阵的变换类型进行分类（单位矩阵、仅平移、缩放+平移、仿射、透视），以便在映射点和其他操作中选择最优的计算路径。

该矩阵的形式为：
```
| scaleX  skewX  transX |
|  skewY scaleY  transY |
| persp0 persp1  persp2 |
```

**注意**：SkMatrix 不是线程安全的，除非先调用 `getType()` 完成类型掩码的计算。

总计约 3692 行代码（头文件约 1700 行，实现文件约 1992 行）。

## 架构位置

```
SkCanvas (绘图 API)
    │
    ├── SkMatrix (2D 变换)    ← 本文件
    ├── SkM44 (4x4 变换)
    │
    ▼
SkDevice (设备坐标映射)
    │
    ▼
SkRasterPipeline / GPU 管线 (像素级变换)
```

SkMatrix 是 Skia 坐标变换系统的基石。它被 SkCanvas 用于管理当前变换矩阵（CTM），被 SkPath 用于变换路径几何，被着色器用于纹理坐标映射，也被图像绘制用于源到目标的映射。在 Skia 的 3D 扩展中，SkM44 提供了完整的 4x4 矩阵功能，而 SkMatrix 可以通过 `SkM44::asM33()` 从 SkM44 导出。

## 主要类与结构体

### SkMatrix
核心 3x3 矩阵类，所有成员如下：

```cpp
class SK_API SkMatrix {
private:
    SkScalar fMat[9];              // 9 个矩阵元素
    mutable uint32_t fTypeMask;    // 类型掩码缓存（mutable 用于惰性计算）
};
```

### TypeMask 枚举
```cpp
enum TypeMask {
    kIdentity_Mask    = 0,     // 单位矩阵
    kTranslate_Mask   = 0x01,  // 包含平移
    kScale_Mask       = 0x02,  // 包含缩放
    kAffine_Mask      = 0x04,  // 包含倾斜或旋转
    kPerspective_Mask = 0x08,  // 包含透视
};
```
内部还有 `kUnknown_Mask` 和 `kRectStaysRect_Mask` 用于缓存管理和轴对齐检测。

### ScaleToFit 枚举
```cpp
enum ScaleToFit {
    kFill_ScaleToFit,    // 拉伸填满目标矩形（不保持宽高比）
    kStart_ScaleToFit,   // 等比缩放对齐左上
    kCenter_ScaleToFit,  // 等比缩放居中
    kEnd_ScaleToFit,     // 等比缩放对齐右下
};
```

### 矩阵元素索引常量
行主序索引：
```cpp
kMScaleX = 0, kMSkewX = 1, kMTransX = 2,
kMSkewY  = 3, kMScaleY = 4, kMTransY = 5,
kMPersp0 = 6, kMPersp1 = 7, kMPersp2 = 8
```
另有列主序仿射索引（`kAScaleX`、`kASkewY` 等），与 PDF/XPS 兼容。

## 公共 API 函数

### 静态工厂方法
| 方法 | 说明 |
|------|------|
| `Scale(sx, sy)` | 创建缩放矩阵 |
| `Translate(dx, dy)` | 创建平移矩阵 |
| `ScaleTranslate(sx, sy, tx, ty)` | 创建缩放+平移矩阵 |
| `RotateDeg(deg)` / `RotateDeg(deg, pt)` | 创建旋转矩阵 |
| `RotateRad(rad)` | 创建弧度旋转矩阵 |
| `Skew(kx, ky)` | 创建倾斜矩阵 |
| `MakeAll(scaleX, skewX, transX, ...)` | 从 9 个值创建矩阵 |
| `I()` | 返回单位矩阵 |
| `Rect2Rect(src, dst, stf)` | 创建矩形到矩形的映射矩阵 |
| `PolyToPoly(src, dst)` | 创建多边形到多边形的映射矩阵（最多 4 点） |

### 类型查询方法
| 方法 | 说明 |
|------|------|
| `getType()` | 返回 TypeMask 位域，保守估计变换类型 |
| `isIdentity()` | 是否为单位矩阵 |
| `isScaleTranslate()` | 是否仅包含缩放和平移 |
| `isTranslate()` | 是否仅包含平移 |
| `rectStaysRect()` / `preservesAxisAlignment()` | 矩形经变换后是否仍为矩形 |
| `hasPerspective()` | 是否包含透视 |
| `isSimilarity(tol)` | 是否为相似变换（等比缩放+旋转+平移） |
| `preservesRightAngles(tol)` | 是否保持直角 |
| `isFinite()` | 所有元素是否有限 |

### 元素读写方法
| 方法 | 说明 |
|------|------|
| `operator[](index)` / `get(index)` | 按索引读取元素 |
| `rc(r, c)` | 按行列读取元素 |
| `getScaleX/Y()`, `getSkewX/Y()`, `getTranslateX/Y()`, `getPerspX/Y()` | 读取具名元素 |
| `set(index, value)` | 设置单个元素 |
| `setScaleX/Y()`, `setSkewX/Y()`, `setTranslateX/Y()`, `setPerspX/Y()` | 设置具名元素 |
| `setAll(...)` | 设置全部 9 个元素 |
| `get9(buffer)` / `set9(buffer)` | 批量读写 |

### 设置变换方法（Set Methods）
这些方法将矩阵完全替换为指定的变换：
| 方法 | 说明 |
|------|------|
| `reset()` / `setIdentity()` | 设为单位矩阵 |
| `setTranslate(dx, dy)` | 设为平移矩阵 |
| `setScale(sx, sy, px, py)` | 设为以(px,py)为中心的缩放 |
| `setRotate(degrees, px, py)` | 设为以(px,py)为中心的旋转 |
| `setSinCos(sin, cos, px, py)` | 用三角函数值设置旋转 |
| `setRSXform(rsxForm)` | 从压缩的旋转-缩放-平移形式设置 |
| `setSkew(kx, ky, px, py)` | 设为以(px,py)为中心的倾斜 |
| `setConcat(a, b)` | 设为两个矩阵的乘积 a*b |

### 预乘变换方法（Pre-multiply）
预乘变换 `Matrix = Matrix * Transform`，效果是"先应用 Transform，再应用原 Matrix"：
| 方法 | 说明 |
|------|------|
| `preTranslate(dx, dy)` | 预乘平移 |
| `preScale(sx, sy, px, py)` | 预乘缩放 |
| `preRotate(degrees, px, py)` | 预乘旋转 |
| `preSkew(kx, ky, px, py)` | 预乘倾斜 |
| `preConcat(other)` | 预乘任意矩阵 |

### 后乘变换方法（Post-multiply）
后乘变换 `Matrix = Transform * Matrix`，效果是"先应用原 Matrix，再应用 Transform"：
| 方法 | 说明 |
|------|------|
| `postTranslate(dx, dy)` | 后乘平移 |
| `postScale(sx, sy, px, py)` | 后乘缩放 |
| `postRotate(degrees, px, py)` | 后乘旋转 |
| `postSkew(kx, ky, px, py)` | 后乘倾斜 |
| `postConcat(other)` | 后乘任意矩阵 |

### 求逆
| 方法 | 说明 |
|------|------|
| `invert()` | 返回 `std::optional<SkMatrix>`，不可逆时返回空 |
| `invert(SkMatrix*)` | （已弃用）布尔返回值版本 |

### 点映射方法
| 方法 | 说明 |
|------|------|
| `mapPoints(dst, src)` | 将源点数组映射到目标数组 |
| `mapPoints(pts)` | 原地映射点数组 |
| `mapPoint(p)` | 映射单个点 |
| `mapPointAffine(p)` | 无透视的快速映射 |
| `mapOrigin()` | 映射原点 (0,0) |
| `mapHomogeneousPoints(dst, src)` | 齐次坐标映射 |
| `mapPointsToHomogeneous(dst, src)` | 2D 点映射为齐次坐标 |
| `mapVectors(dst, src)` | 映射向量（忽略平移） |
| `mapVector(dx, dy)` | 映射单个向量 |
| `mapRect(dst, src)` | 映射矩形 |
| `mapRect(rect)` | 原地映射矩形 |
| `mapRectScaleTranslate(dst, src)` | 仅缩放+平移情况下的快速矩形映射 |
| `mapRadius(radius)` | 映射半径 |

### 其他方法
| 方法 | 说明 |
|------|------|
| `normalizePerspective()` | 规范化透视行为（使 persp2 = 1） |
| `asAffine(affine)` | 导出为 6 元素列主序仿射矩阵 |
| `setAffine(affine)` | 从 6 元素列主序仿射矩阵设置 |
| `SetAffineIdentity(affine)` | 设置仿射单位矩阵 |
| `decomposeScale(scale, remaining)` | 分解缩放分量 |
| `dump()` / `toString()` | 调试输出 |
| `getMinScale()` / `getMaxScale()` | 获取最小/最大缩放因子 |
| `getMinMaxScales(scaleFactors)` | 同时获取最小和最大缩放因子 |

## 内部实现细节

### 类型掩码缓存
`fTypeMask` 是一个 `mutable` 成员，使用惰性计算策略。初始值和修改后设为 `kUnknown_Mask`，首次通过 `getType()` 访问时调用 `computeTypeMask()` 进行计算并缓存。后续读取直接返回缓存值，直到矩阵被修改。

`computeTypeMask()` 检查每个矩阵元素：
- 透视行（persp0、persp1 是否非零，persp2 是否非 1）
- 仿射元素（skewX、skewY 是否非零）
- 缩放元素（scaleX、scaleY 是否非 1）
- 平移元素（transX、transY 是否非零）
- 轴对齐性（`kRectStaysRect_Mask`）

### 矩阵乘法优化
`setConcat()` 根据两个输入矩阵的 TypeMask 选择不同的乘法路径：
- 若其中一个是单位矩阵，直接复制另一个
- 若都仅含缩放+平移，使用简化的 4 次乘法
- 否则执行完整的 3x3 矩阵乘法

### 点映射的分发机制
`mapPoints()` 根据 TypeMask 分发到不同的映射函数：
- `kIdentity_Mask` → 直接复制
- `kTranslate_Mask` → 加上偏移量
- `kScale_Mask | kTranslate_Mask` → 乘缩放再加偏移
- `kAffine_Mask` → 完整仿射变换
- `kPerspective_Mask` → 包含齐次坐标除法的透视变换

### 矩阵求逆
求逆算法根据类型掩码优化：
- 仅平移：取反平移分量
- 缩放+平移：取倒数
- 仿射：使用 2x2 子矩阵的行列式
- 透视：使用完整 3x3 辅因子矩阵

检测到行列式为零（不可逆）时返回 `std::nullopt`。

## 依赖关系

- `SkPoint` / `SkPoint3` — 点类型，mapPoints 的输入输出
- `SkRect` — 矩形类型，mapRect 的输入输出
- `SkScalar` — 浮点标量类型（即 `float`）
- `SkRSXform` — 压缩的旋转-缩放-平移变换
- `SkSize` — 尺寸类型
- `include/private/base/SkFloatingPoint.h` — 浮点工具函数

## 设计模式与设计决策

### 惰性类型缓存
使用 `mutable fTypeMask` 实现惰性计算，在不修改矩阵的逻辑不变性前提下缓存类型信息。这是一种常见的 const-correct 缓存模式。

### 构建者模式（Builder Pattern）
设置方法（如 `setScale`）返回 `SkMatrix&` 引用，支持链式调用：
```cpp
SkMatrix m;
m.setScale(2, 2).preRotate(45).postTranslate(10, 20);
```

### 紧凑内存布局
使用 `SK_BEGIN_REQUIRE_DENSE` 确保无填充字节，使矩阵可以安全地用于 `memcmp` 比较和网络传输。

### 预乘 vs 后乘的命名约定
Skia 遵循"变换管线"的思维模型：
- `preXxx` 表示"在现有变换之前应用"（预乘，右乘）
- `postXxx` 表示"在现有变换之后应用"（后乘，左乘）

这与 OpenGL 的右乘约定一致，但与某些数学教材的左乘约定相反。

## 性能考量

1. **类型掩码分发**：根据矩阵类型选择最优计算路径，避免单位矩阵和仅平移情况下的不必要乘法
2. **constexpr 默认构造**：单位矩阵的构造在编译期完成，零运行时开销
3. **mapRectScaleTranslate**：专门针对缩放+平移（最常见情况）优化的矩形映射，避免通用 `mapPoints` 的开销
4. **批量映射**：`mapPoints` 的 Span 版本支持对多个点进行批量变换，内部可利用 SIMD 指令加速
5. **`[[nodiscard]]` 标注**：静态工厂方法标记为 `[[nodiscard]]`，防止忽略返回值导致的性能浪费和逻辑错误
6. **isFinite 快速检查**：利用浮点特性，将 9 个值相乘后检查是否为 0/NaN，单次比较即可判断所有元素是否有限

## 相关文件

- `/Users/yuanlin/workspace/skia/include/core/SkMatrix.h` — 公共头文件
- `/Users/yuanlin/workspace/skia/src/core/SkMatrix.cpp` — 实现文件
- `/Users/yuanlin/workspace/skia/include/core/SkM44.h` — 4x4 矩阵类
- `/Users/yuanlin/workspace/skia/src/core/SkMatrixPriv.h` — 私有辅助函数
- `/Users/yuanlin/workspace/skia/include/core/SkPoint.h` — 点类型
- `/Users/yuanlin/workspace/skia/include/core/SkRect.h` — 矩形类型
- `/Users/yuanlin/workspace/skia/include/core/SkRSXform.h` — 旋转-缩放-平移压缩形式
- `/Users/yuanlin/workspace/skia/include/core/SkCanvas.h` — 使用 SkMatrix 管理变换状态
