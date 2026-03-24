# SkCoverageMode

> 源文件: `include/core/SkCoverageMode.h`

## 概述

SkCoverageMode 定义了应用于覆盖率(coverage)字节的几何运算模式,类似于 SkRegion::Op 的布尔集合操作,但仅作用于 Alpha 通道。这些模式本质上是 Porter-Duff 混合模式的 Alpha 通道变体,主要用于遮罩(mask)的组合计算。

## 架构位置

该枚举位于 Skia 核心头文件 (`include/core`)，属于渲染管线中的遮罩处理层。它与 SkMaskFilter 紧密配合,用于两个不同遮罩的组合操作,是 Skia 遮罩系统的基础数学运算定义。

## 枚举定义

### SkCoverageMode

**职责**: 定义两个覆盖率值的几何组合运算规则。

| 枚举值 | 数学符号 | 公式 | 说明 |
|--------|---------|------|------|
| kUnion | A ∪ B | A + B - A*B | 并集运算,组合两个遮罩的覆盖区域 |
| kIntersect | A ∩ B | A * B | 交集运算,仅保留两个遮罩重叠区域 |
| kDifference | A - B | A * (1-B) | 差集运算,从 A 中减去 B 的覆盖区域 |
| kReverseDifference | B - A | B * (1-A) | 反向差集,从 B 中减去 A 的覆盖区域 |
| kXor | A ⊕ B | A + B - 2*A*B | 异或运算,保留非重叠区域 |

**枚举范围**: kLast 定义为 kXor,用于边界检查。

## 数学原理

### 覆盖率运算基础

覆盖率值通常表示为 [0, 1] 范围的浮点数或 [0, 255] 的 8 位整数:
- **0**: 完全透明(无覆盖)
- **1 或 255**: 完全不透明(全覆盖)
- **中间值**: 部分覆盖(抗锯齿边缘)

### 各模式详解

#### kUnion (并集)
```
公式: A + B - A*B
等价于: 1 - (1-A)*(1-B)
含义: 任一遮罩覆盖的区域都会在结果中出现
示例: A=0.5, B=0.3 → 0.5 + 0.3 - 0.15 = 0.65
```

#### kIntersect (交集)
```
公式: A * B
含义: 仅保留两个遮罩都覆盖的区域
示例: A=0.8, B=0.6 → 0.8 * 0.6 = 0.48
```

#### kDifference (差集)
```
公式: A * (1-B)
含义: A 覆盖但 B 不覆盖的区域
示例: A=0.7, B=0.4 → 0.7 * 0.6 = 0.42
```

#### kReverseDifference (反向差集)
```
公式: B * (1-A)
含义: B 覆盖但 A 不覆盖的区域
示例: A=0.3, B=0.6 → 0.6 * 0.7 = 0.42
```

#### kXor (异或)
```
公式: A + B - 2*A*B
等价于: |A - B| 当 A,B ∈ {0,1}
含义: 仅一个遮罩覆盖的区域
示例: A=0.4, B=0.5 → 0.4 + 0.5 - 0.4 = 0.5
```

## 使用场景

### 遮罩过滤器组合
SkMaskFilter 使用这些模式组合多个模糊或形状遮罩:
```cpp
// 伪代码示例
SkMaskFilter::CombineMasks(maskA, maskB, SkCoverageMode::kIntersect);
```

### 阴影效果
通过差集运算实现挖空阴影效果:
```cpp
// 原始形状 - 模糊形状 = 外部阴影
result = Difference(originalMask, blurredMask);
```

### 复杂形状构造
通过多次布尔运算构建复杂的抗锯齿形状:
```cpp
// 圆角矩形 = 矩形 ∪ (四个圆角)
mask = Union(rectMask, cornersMask);
```

### 文本效果
为文字添加描边或发光效果:
```cpp
// 发光 = 外扩遮罩 - 原始遮罩
glowMask = Difference(dilatedTextMask, originalTextMask);
```

## 依赖关系

### 依赖的模块
该文件是独立的枚举定义,无外部依赖(仅依赖标准 C++ 枚举语法)。

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| SkMaskFilter | 使用覆盖率模式组合遮罩滤镜 |
| SkBlurMaskFilter | 模糊遮罩与原始遮罩的组合 |
| SkRegion | 区域运算的 Alpha 通道类比 |
| 内部遮罩生成器 | 光栅化时的覆盖率计算 |

## 设计决策

### 为何独立定义
虽然功能类似 SkRegion::Op,但覆盖率运算:
1. **连续值**: 处理 [0,1] 浮点数而非布尔值
2. **抗锯齿**: 保持子像素精度
3. **Alpha 通道特化**: 不涉及颜色混合

### 数学公式选择
公式设计确保:
- **交换律**: Union 和 Intersect 满足 A⊕B = B⊕A
- **边界行为**: 输入 0 或 1 时退化为经典布尔运算
- **数值稳定性**: 避免浮点溢出

### 枚举而非函数
使用枚举而非函数指针:
- **类型安全**: 编译时检查有效性
- **性能**: 避免虚函数或函数指针开销
- **可序列化**: 易于状态保存和传输

## 性能考量

### 整数优化
对于 8 位覆盖率值(0-255):
```cpp
// 快速整数乘法(使用 255*255 = 65025 可放入 16 位)
uint8_t Multiply(uint8_t a, uint8_t b) {
    return (a * b + 127) / 255; // +127 实现四舍五入
}
```

### SIMD 向量化
现代实现使用 SIMD 指令并行处理多个像素:
```cpp
// SSE/NEON 示例(伪代码)
__m128i Union(__m128i a, __m128i b) {
    __m128i product = _mm_mullo_epi16(a, b);
    return _mm_sub_epi16(_mm_add_epi16(a, b), product);
}
```

### 查找表
对于固定 8 位输入,可预计算所有组合:
```cpp
// 256x256 查找表(64KB)
uint8_t UnionLUT[256][256];
```

## 与 Porter-Duff 的关系

Porter-Duff 混合模式作用于完整的 RGBA 像素,而 SkCoverageMode 仅处理 Alpha:

| SkCoverageMode | 对应 Porter-Duff 模式 |
|----------------|----------------------|
| kUnion | Plus(饱和加法的 Alpha 部分) |
| kIntersect | SrcIn/DstIn (Alpha 部分) |
| kDifference | SrcOut (Alpha 部分) |
| kXor | Xor (Alpha 部分) |

关键区别:
- **SkCoverageMode**: `result.alpha = Op(A, B)`
- **Porter-Duff**: `result.rgba = Op(src, dst)` (含颜色混合)

## 实际应用示例

### 内发光效果
```cpp
// 1. 获取形状遮罩
SkMask shapeMask = RasterizeShape();

// 2. 创建内收缩版本
SkMask erodedMask = Erode(shapeMask);

// 3. 计算内发光区域
SkMask glowRegion = Difference(shapeMask, erodedMask);

// 4. 应用颜色
ApplyColor(glowRegion, glowColor);
```

### 双层阴影
```cpp
// 外阴影(大模糊)
SkMask outerShadow = Blur(shapeMask, largeRadius);

// 内阴影(小模糊)
SkMask innerShadow = Blur(shapeMask, smallRadius);

// 组合阴影环
SkMask shadowRing = Difference(outerShadow, innerShadow);
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkMaskFilter.h` | 主要使用者,遮罩滤镜组合 |
| `include/core/SkBlendMode.h` | 完整 RGBA 混合模式(更高层) |
| `include/core/SkRegion.h` | 区域布尔运算(几何层面) |
| `src/core/SkMask.h` | 遮罩数据结构定义 |
| `src/core/SkDraw.cpp` | 光栅化时的覆盖率计算 |
| `include/effects/SkBlurMaskFilter.h` | 模糊遮罩实现 |
