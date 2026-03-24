# SkMorphologyImageFilter

> 源文件: `src/effects/imagefilters/SkMorphologyImageFilter.cpp`

## 概述

`SkMorphologyImageFilter` 实现了形态学图像滤镜,包括膨胀(Dilate)和腐蚀(Erode)两种操作。膨胀操作在核区域内取最大值,使亮区扩张;腐蚀操作取最小值,使亮区收缩。这些操作广泛应用于图像处理中的边缘检测、降噪和形状处理。该滤镜对应 SVG 的 `feMorphology` 滤镜。

## 架构位置

```
SkImageFilter (公共接口)
  └─ SkImageFilter_Base (内部基类)
       └─ SkMorphologyImageFilter (本文件)
            ├─ MorphType: kErode / kDilate
            ├─ SkSL 线性形态学核 (kLinearMorphology StableKey)
            └─ SkSL 稀疏形态学核 (kSparseMorphology StableKey)

工厂方法:
  SkImageFilters::Dilate(radiusX, radiusY, input, cropRect)
  SkImageFilters::Erode(radiusX, radiusY, input, cropRect)
```

## 主要类与结构体

### `MorphType` 枚举
- `kErode`: 腐蚀操作(取最小值)
- `kDilate`: 膨胀操作(取最大值)

### `MorphDirection` 枚举
- `kX`: 水平方向
- `kY`: 垂直方向

### `SkMorphologyImageFilter`
- 继承自 `SkImageFilter_Base`,接收一个子滤镜输入
- **成员变量**:
  - `fType` (`MorphType`): 形态学操作类型
  - `fRadii` (`skif::ParameterSpace<SkSize>`): X/Y 方向的核半径(参数空间)

## 公共 API 函数

### `SkImageFilters::Dilate(radiusX, radiusY, input, cropRect)`
创建膨胀滤镜。半径为 0 时优化为恒等变换(仅应用裁剪)。

### `SkImageFilters::Erode(radiusX, radiusY, input, cropRect)`
创建腐蚀滤镜。同样在半径为 0 时优化为恒等变换。

## 内部实现细节

### 两级核算法
形态学操作使用分离式两级处理:先 X 方向,后 Y 方向。X pass 需要保留额外的行数据供 Y pass 使用。

### 多 Pass 形态学
`morphology_pass()` 实现了迭代式半径扩展:

1. **线性累积 Pass** (第一次迭代): 使用 `make_linear_morphology()` 着色器,半径上限 `kMaxLinearRadius = 14`(对应 DX9SM2 的 32 次纹理采样限制)。该着色器对核范围内每个像素进行采样。

2. **稀疏翻倍 Pass** (后续迭代): 使用 `make_sparse_morphology()` 着色器,每次仅需 2 次纹理采样即可将累积核大小翻倍。设前一步已累积半径 R,当前步取 radius = min(remaining, R),输出在位置 i 处为 min/max(input[i-radius], input[i+radius])。

### 半径限制
```
static constexpr int kMaxRadii = 256;
```
限制最大半径为 256 像素以避免慢速绘制调用(crbug.com/1123035)。

### 核输出边界
`kernelOutputBounds()` 根据操作类型调整边界:
- **膨胀**: 输出边界**外扩**核半径(透明像素被邻近有色像素覆盖)
- **腐蚀**: 输出边界**内缩**核半径(边缘像素被透明像素覆盖)

### 空输入处理
在 `morphology_pass()` 中,若子输出为空直接返回空结果,因为透明黑色经过腐蚀或膨胀后仍是透明黑色。

## 依赖关系

- `include/effects/SkRuntimeEffect.h` - 运行时着色器
- `src/core/SkKnownRuntimeEffects.h` - 内置 SkSL 效果
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型
- `src/core/SkImageFilter_Base.h` - 滤镜基类

## 设计模式与设计决策

### 分离式核
将 2D 形态学分解为两个 1D Pass(X+Y),将 O(w*h) 的核操作降低为 O(w+h),显著提升性能。

### 线性+稀疏双策略
- 小半径 (<=14): 使用线性核,一次 Pass 完成
- 大半径: 先用线性核处理最大 14 像素,然后用稀疏核翻倍,以 O(log n) 次 Pass 覆盖任意半径

### DX9 兼容性约束
`kMaxLinearRadius = 14` 确保线性核的纹理采样次数 (2*14+1=29) 不超过 DX9 SM2 的 32 次限制。

### 统一工厂函数
`make_morphology()` 统一处理 Dilate 和 Erode 的创建逻辑,包括零半径优化和裁剪矩形处理。

## 性能考量

- 分离式处理将 2D 核降为两个 1D Pass,核面积大时性能提升显著
- 稀疏形态学每步仅 2 次采样实现核大小翻倍,大半径时仅需 O(log R) 次额外 Pass
- 最大半径 256 限制防止过大核导致的性能退化
- 零半径优化跳过整个形态学处理
- `ShaderFlags::kSampledRepeatedly` 标记帮助后端优化重复采样
- 中间 Pass 的输出区域精确计算,避免处理不必要的像素

## 算法复杂度分析

对于半径 R 的形态学操作:

**线性累积阶段** (R <= 14):
- 纹理采样: 2R + 1 次/像素
- Pass 数: 1 次/方向 (共 2 次)
- 总采样: O(R * W * H) (W, H 为图像尺寸)

**稀疏翻倍阶段** (R > 14):
- 第一步: 线性累积 min(14, R) 像素
- 后续步: 每步翻倍已累积的半径,仅 2 次采样/像素
- Pass 数: 1 + ceil(log2(R / 14)) 次/方向
- 总采样: O((14 + 2 * log(R/14)) * W * H)

**示例**: R = 256
- 线性: 14 像素 (29 采样/像素), 累积 R = 14
- 稀疏 1: R += 14, 累积 R = 28 (2 采样/像素)
- 稀疏 2: R += 28, 累积 R = 56
- 稀疏 3: R += 56, 累积 R = 112
- 稀疏 4: R += 112, 累积 R = 224
- 稀疏 5: R += 32, 累积 R = 256
- 每方向共 6 个 Pass,总 12 个 Pass

## 膨胀与腐蚀的边界行为差异

| 操作 | 核函数 | 输入需求 | 输出效果 | 边界行为 |
|------|-------|---------|---------|---------|
| 膨胀 | max() | 外扩 R 像素 | 外扩 R 像素 | 亮区膨胀,暗区被吞噬 |
| 腐蚀 | min() | 外扩 R 像素 | 内缩 R 像素 | 暗区膨胀,亮区被侵蚀 |

注意:两种操作的**输入需求**相同(都外扩 R),但**输出边界**不同。这是因为:
- 膨胀: 边缘外的透明像素被内部有色像素的 max 值覆盖,输出扩大
- 腐蚀: 边缘处的有色像素被外部透明像素的 min 值覆盖,输出缩小

## 版本兼容性

- 旧版名称: `SkMorphologyImageFilterImpl` -> `SkMorphologyImageFilter`
- 序列化格式: 基类数据 + width(scalar) + height(scalar) + filterType(int)
- filterType 使用 `MorphType` 枚举值(0=kErode, 1=kDilate)

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `src/core/SkKnownRuntimeEffects.h` - 内置 SkSL 效果
- `src/sksl/sksl_rt_shader.sksl` - 线性和稀疏形态学着色器的 SkSL 源码
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型系统
