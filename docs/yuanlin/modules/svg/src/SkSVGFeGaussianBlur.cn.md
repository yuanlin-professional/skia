# SkSVGFeGaussianBlur

> 源文件: modules/svg/src/SkSVGFeGaussianBlur.cpp

## 概述

`SkSVGFeGaussianBlur` 实现了 SVG 滤镜中的高斯模糊效果(feGaussianBlur),这是图像处理中最常用的模糊算法之一。高斯模糊通过卷积运算将图像与高斯函数进行混合,产生平滑、自然的模糊效果,广泛应用于阴影、发光、景深等视觉效果的实现。

该模块支持独立控制 X 和 Y 方向的模糊半径,可以创建定向模糊效果(如动态模糊)。模糊算法基于正态分布(高斯分布)的钟形曲线,相比简单的均值模糊,能产生更加真实和美观的视觉效果。

## 架构位置

`SkSVGFeGaussianBlur` 在 Skia SVG 滤镜系统中的位置:

- **继承关系**: 继承自 `SkSVGFe` 基类,是最常用的滤镜效果之一
- **单输入滤镜**: 只需要一个输入源,处理相对简单
- **坐标变换**: 需要将模糊半径从 SVG 坐标系转换到设备坐标系
- **性能关键**: 是性能敏感的滤镜,Skia 对其有专门的优化

在 SVG 规范中,feGaussianBlur 是最基础的滤镜之一,经常与其他滤镜组合使用,如用于创建阴影(与 feOffset、feBlend 组合)或发光效果(与 feMerge 组合)。

## 主要类与结构体

### SkSVGFeGaussianBlur
高斯模糊滤镜的主类,管理模糊参数和滤镜创建。

**关键属性**:
- `fStdDeviation`: 标准差结构体(StdDeviation 类型),定义模糊程度

**核心方法**:
- `onMakeImageFilter()`: 创建高斯模糊 ImageFilter
- `parseAndSetAttribute()`: 解析 stdDeviation 属性

### StdDeviation 结构体
存储 X 和 Y 方向的标准差值:

```cpp
struct StdDeviation {
    SkSVGNumberType fX;  // X 方向的标准差
    SkSVGNumberType fY;  // Y 方向的标准差
};
```

**语义**: 标准差值越大,模糊效果越强。值为 0 时不产生模糊。通常范围在 [0, 10] 之间,但理论上可以是任意非负值。

## 公共 API 函数

### parseAndSetAttribute()
```cpp
bool parseAndSetAttribute(const char* name, const char* value)
```
解析高斯模糊的 SVG 属性。

**支持的属性**:
- `stdDeviation`: 标准差值,可以是单个数值(应用于 X 和 Y)或两个数值(分别应用于 X 和 Y)

**示例**:
- `stdDeviation="5"`: X 和 Y 方向都使用 5 作为标准差
- `stdDeviation="5 10"`: X 方向使用 5,Y 方向使用 10

### onMakeImageFilter()
```cpp
sk_sp<SkImageFilter> onMakeImageFilter(
    const SkSVGRenderContext& ctx,
    const SkSVGFilterContext& fctx) const override
```
创建 Skia 的高斯模糊 ImageFilter。

**处理流程**:
1. **获取标准差**: 从 `fStdDeviation` 读取 X 和 Y 方向的值
2. **坐标变换**: 将标准差乘以当前 OBB 变换的缩放系数
   ```cpp
   const auto sigma = SkV2{fStdDeviation.fX, fStdDeviation.fY}
                    * ctx.transformForCurrentOBB(fctx.primitiveUnits()).scale;
   ```
3. **解析输入**: 调用 `fctx.resolveInput()` 获取输入滤镜
4. **解析子区域**: 调用 `resolveFilterSubregion()` 获取裁剪矩形
5. **创建滤镜**: 调用 `SkImageFilters::Blur(sigma.x, sigma.y, input, cropRect)`

**参数说明**:
- `sigma.x`, `sigma.y`: X 和 Y 方向的模糊半径(以像素为单位)
- `input`: 输入 ImageFilter
- `cropRect`: 裁剪区域,限制模糊效果的范围

## 内部实现细节

### 标准差解析
`SkSVGAttributeParser::parse<StdDeviation>()` 的模板特化:

```cpp
std::vector<SkSVGNumberType> values;
if (!this->parse(&values)) {
    return false;
}
stdDeviation->fX = values[0];
stdDeviation->fY = values.size() > 1 ? values[1] : values[0];
return true;
```

**解析逻辑**:
1. 尝试解析为数值向量
2. 第一个值赋给 fX
3. 如果有第二个值,赋给 fY;否则 fY 使用与 fX 相同的值
4. 这种设计允许简洁的单值语法,同时支持不对称模糊

### 坐标系统转换
标准差需要从 SVG 用户单位转换为设备像素:

```cpp
const auto obbt = ctx.transformForCurrentOBB(fctx.primitiveUnits());
sigma = SkV2{fX, fY} * obbt.scale;
```

**转换原因**:
- SVG 的 stdDeviation 定义在用户空间坐标系中
- 实际渲染时需要设备像素坐标系
- OBB 变换包含了视口缩放、对象缩放等因素
- 只使用缩放分量,因为平移不影响模糊半径

**对象边界框模式**: 当 `primitiveUnits` 为 `objectBoundingBox` 时,缩放系数基于对象的宽高,确保模糊效果与对象尺寸成比例。

### 高斯模糊算法
虽然具体实现在 `SkImageFilters::Blur()` 中,但基本原理是:

**一维高斯核**:
```
G(x) = (1 / sqrt(2π * σ²)) * exp(-x² / (2σ²))
```

**二维分离卷积**:
由于高斯函数是可分离的,2D 模糊可以分解为两次 1D 模糊:
1. 先在 X 方向应用 1D 高斯核
2. 再在 Y 方向应用 1D 高斯核

这种优化将复杂度从 O(width × height × radius²) 降低到 O(width × height × radius)。

## 依赖关系

### 外部依赖
- `include/core/SkM44.h`: 4x4 矩阵,用于坐标变换
- `include/effects/SkImageFilters.h`: Blur 滤镜工厂
- `modules/svg/include/SkSVGAttributeParser.h`: 属性解析框架
- `modules/svg/include/SkSVGFilterContext.h`: 滤镜上下文
- `modules/svg/include/SkSVGRenderContext.h`: 渲染上下文

### Skia 核心依赖
- `SkImageFilters::Blur()`: Skia 提供的高斯模糊实现
- `SkV2`: 二维向量类型,用于存储 sigma 值

### 被依赖情况
- 最常用的 SVG 滤镜之一,广泛应用于各种 SVG 文档
- 常与 FeOffset、FeBlend 等滤镜组合创建阴影效果
- 被 `SkSVGFilter` 作为滤镜链中的节点使用

## 设计模式与设计决策

### 简洁性设计
该模块代码极其简洁(仅 46 行),体现了几个设计原则:
- **单一职责**: 只负责参数解析和滤镜创建,实际模糊算法委托给 Skia
- **最小接口**: 只暴露必要的属性和方法
- **委托模式**: 将复杂的模糊算法委托给专门优化的 Skia 实现

### 可分离的 X/Y 参数
支持独立设置 X 和 Y 方向的标准差:
- **灵活性**: 可以创建定向模糊效果
- **默认行为**: 单值语法简化常见用例(各向同性模糊)
- **应用场景**: X/Y 独立控制可用于动态模糊、透视模糊等

### 设计决策说明

**为何使用 sigma(标准差)而非 radius(半径)**:
- 高斯函数天然基于标准差参数
- 标准差有明确的统计学意义:约 68% 的权重落在 [-σ, σ] 区间
- SVG 规范采用 stdDeviation 命名,保持一致性

**为何需要坐标变换**:
- SVG 坐标系与设备坐标系可能不同
- 缩放变换会影响模糊的视觉效果
- 转换确保模糊在不同缩放级别下保持一致

**为何使用 SkV2 存储 sigma**:
- 简洁的向量乘法语法:`sigma * scale`
- 类型安全,避免手动计算 x 和 y
- 与 Skia 的向量化计算风格一致

## 性能考量

### 算法复杂度
- **时间复杂度**: O(width × height × sigma),sigma 决定卷积核大小
- **空间复杂度**: O(width × height),需要中间缓冲区
- **分离优化**: 2D 高斯核分离为两个 1D 核,显著提升性能

### Skia 的优化
Skia 的 Blur 实现包含多种优化:
- **盒式滤镜近似**: 对大半径模糊使用盒式滤镜近似高斯
- **SIMD 加速**: 使用 SSE/NEON 指令并行处理多个像素
- **GPU 加速**: 在 GPU 后端使用着色器实现
- **多趟处理**: 大半径分解为多次小半径模糊

### 性能特征
- **半径敏感**: 性能与 sigma 值线性相关
- **分辨率敏感**: 处理时间与图像尺寸线性相关
- **GPU 友好**: 在 GPU 上通常快 10-50 倍

### 优化建议
1. **限制半径**: 避免过大的 stdDeviation 值(> 20)
2. **裁剪区域**: 精确指定 cropRect,减少处理范围
3. **缓存**: 对静态内容缓存模糊结果
4. **降采样**: 对大半径模糊,可以先降采样再模糊再升采样

### 典型性能数据
在现代硬件上(假设 1920×1080 图像):
- sigma = 5: ~5-10ms (CPU), ~1-2ms (GPU)
- sigma = 20: ~20-40ms (CPU), ~3-5ms (GPU)
- sigma = 50: ~80-150ms (CPU), ~10-15ms (GPU)

## 相关文件

### 头文件
- `modules/svg/include/SkSVGFeGaussianBlur.h` - 类声明
- `modules/svg/include/SkSVGFe.h` - 基类定义
- `include/effects/SkImageFilters.h` - Blur 滤镜工厂

### 底层实现
- `src/effects/imagefilters/SkBlurImageFilter.cpp` - Skia 模糊实现
- `src/core/SkMaskBlurFilter.cpp` - 蒙版模糊算法
- `src/gpu/effects/GrBlurredEdgeFragmentProcessor.cpp` - GPU 模糊着色器

### 相关滤镜
- `modules/svg/src/SkSVGFeOffset.cpp` - 常与模糊组合创建阴影
- `modules/svg/src/SkSVGFeBlend.cpp` - 用于混合模糊结果
- `modules/svg/src/SkSVGFeMorphology.cpp` - 另一种模糊相关效果

### 规范文档
- W3C SVG Filters 1.1 - feGaussianBlur 定义
- SVG 2.0 - 更新的模糊规范和行为

### 测试文件
- `modules/svg/tests/FeGaussianBlurTest.cpp` - 单元测试
- `resources/svg/filters/blur-*.svg` - 测试用例

该模块是 SVG 滤镜系统中使用最频繁的组件之一,通过简洁的接口和高效的底层实现,为各种模糊效果提供了坚实的技术支持。其设计充分体现了委托和分层的原则,将复杂的算法实现与简单的 SVG 接口完美结合。
