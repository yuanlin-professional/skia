# SkColorMatrixFilter

> 源文件: include/effects/SkColorMatrixFilter.h, src/effects/SkColorMatrixFilter.cpp

## 概述

SkColorMatrixFilter 是 Skia 中用于创建光照效果（Lighting Effect）的颜色滤镜工厂类。该模块提供了一个已弃用的兼容接口 `MakeLightingFilter`,实际实现委托给 SkColorFilters 的 Lighting 方法。光照效果通过颜色矩阵实现,将乘法（multiply）和加法（add）颜色操作转换为矩阵运算,用于模拟光源对图像的影响。

## 架构位置

SkColorMatrixFilter 位于 Skia 的效果层颜色处理子系统:

```
include/effects/
  ├── SkColorMatrixFilter.h   # 兼容接口（本模块）
  └── SkColorMatrix.h          # 颜色矩阵定义
include/core/
  └── SkColorFilter.h          # 颜色滤镜基类
src/effects/
  └── SkColorMatrixFilter.cpp  # 实现文件（本模块）
```

该模块是遗留 API 的适配层,实际功能由 SkColorFilters 提供。

## 主要类与结构体

| 类名 | 继承关系 | 关键成员变量 | 说明 |
|------|---------|------------|------|
| `SkColorMatrixFilter` | `SkColorFilter` | 无 | 仅包含静态方法的兼容类 |

## 公共 API 函数

### 工厂方法（已弃用）

```cpp
class SK_API SkColorMatrixFilter : public SkColorFilter {
public:
    // (DEPRECATED) 使用 SkColorFilters::Lighting 代替
    static sk_sp<SkColorFilter> MakeLightingFilter(SkColor mul, SkColor add) {
        return SkColorFilters::Lighting(mul, add);
    }
};
```

### 参数说明

**MakeLightingFilter**
- `mul`: 乘法颜色（每个通道与输入相乘）
- `add`: 加法颜色（每个通道与乘法结果相加）
- 返回: `sk_sp<SkColorFilter>` 智能指针

## 内部实现细节

### 实际实现委托

模块的实际功能在 `src/effects/SkColorMatrixFilter.cpp` 中:

```cpp
sk_sp<SkColorFilter> SkColorFilters::Lighting(SkColor mul, SkColor add) {
    const SkColor opaqueAlphaMask = SK_ColorBLACK;

    // 优化: 如果没有加法操作,使用更高效的 Blend 模式
    if (0 == (add & ~opaqueAlphaMask)) {
        return SkColorFilters::Blend(mul | opaqueAlphaMask,
                                     SkBlendMode::kModulate);
    }

    // 通用路径: 使用颜色矩阵
    SkColorMatrix matrix;
    matrix.setScale(byte_to_unit_float(SkColorGetR(mul)),
                    byte_to_unit_float(SkColorGetG(mul)),
                    byte_to_unit_float(SkColorGetB(mul)),
                    1);
    matrix.postTranslate(byte_to_unit_float(SkColorGetR(add)),
                         byte_to_unit_float(SkColorGetG(add)),
                         byte_to_unit_float(SkColorGetB(add)),
                         0);
    return SkColorFilters::Matrix(matrix);
}
```

### 颜色转换辅助函数

```cpp
static SkScalar byte_to_unit_float(U8CPU byte) {
    if (0xFF == byte) {
        return 1;  // 精确返回 1.0
    } else {
        return byte * 0.00392156862745f;  // 1/255
    }
}
```

功能: 将 8 位颜色值 [0, 255] 转换为浮点数 [0.0, 1.0]

### 光照效果数学模型

**输出颜色计算**:
```
output.r = input.r * mul.r + add.r
output.g = input.g * mul.g + add.g
output.b = input.b * mul.b + add.b
output.a = input.a * 1.0   + 0.0    (alpha 不变)
```

**矩阵表示**:
```
[ R' ]   [ mul.r   0      0     0  add.r ] [ R ]
[ G' ] = [   0   mul.g    0     0  add.g ] [ G ]
[ B' ]   [   0     0    mul.b   0  add.b ] [ B ]
[ A' ]   [   0     0      0     1    0   ] [ A ]
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkColorFilter.h` | 颜色滤镜基类 |
| `include/core/SkColor.h` | 颜色定义 |
| `include/effects/SkColorMatrix.h` | 颜色矩阵结构 |
| `include/core/SkBlendMode.h` | 混合模式 |
| `include/core/SkScalar.h` | 标量类型 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| 遗留客户端代码 | 使用旧 API |
| 示例代码 | 向后兼容 |

## 设计模式与设计决策

### 适配器模式

**决策**: SkColorMatrixFilter 作为适配器,将旧 API 转发到新实现

```cpp
// 旧 API (已弃用)
SkColorMatrixFilter::MakeLightingFilter(mul, add)
  ↓
// 新 API
SkColorFilters::Lighting(mul, add)
```

**优点**:
- 保持向后兼容性
- 引导用户迁移到新 API
- 无需维护重复代码

### 性能优化策略

**快速路径检测**:
```cpp
if (0 == (add & ~opaqueAlphaMask)) {
    // add 为 (0,0,0,X) 时使用 Blend 模式（更快）
    return SkColorFilters::Blend(mul | opaqueAlphaMask,
                                 SkBlendMode::kModulate);
}
```

**优化条件**: 无加法操作时
- 避免颜色矩阵开销
- 使用 GPU 原生混合模式
- 减少内存分配

### Alpha 通道保留

**设计决策**: Alpha 通道总是保持不变

```cpp
matrix.setScale(rScale, gScale, bScale, 1);  // alpha scale = 1
matrix.postTranslate(rTrans, gTrans, bTrans, 0);  // alpha trans = 0
```

**原因**:
- 符合预期语义（光照不影响透明度）
- 简化合成操作
- 避免预乘 alpha 问题

## 性能考量

### 快速路径优化

**Blend 模式路径**:
- 条件: `add == (0, 0, 0, X)`
- 优势:
  - GPU 原生支持
  - 无矩阵计算开销
  - 更好的流水线利用

**矩阵路径**:
- 条件: 存在加法操作
- 开销:
  - 创建 SkColorMatrix 对象
  - 4x4 矩阵-向量乘法
  - 可能的 GPU 着色器编译

### 颜色转换精度

```cpp
static SkScalar byte_to_unit_float(U8CPU byte) {
    if (0xFF == byte) {
        return 1;  // 特殊处理确保精确
    }
    return byte * 0.00392156862745f;  // 预计算的 1/255
}
```

优化点:
- 特殊处理最大值（避免浮点误差）
- 使用预计算常量（避免除法）
- 单次转换（不重复计算）

### 内存分配

- 静态方法无额外堆分配
- SkColorMatrix 可能内联（取决于编译器）
- 返回智能指针管理生命周期

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkColorFilter.h` | 依赖 | 颜色滤镜基类 |
| `include/effects/SkColorMatrix.h` | 依赖 | 矩阵结构定义 |
| `include/core/SkBlendMode.h` | 依赖 | 混合模式枚举 |
| `src/core/SkColorFilter.cpp` | 相关 | 滤镜基类实现 |
| `include/core/SkPaint.h` | 使用者 | 应用颜色滤镜 |
