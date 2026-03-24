# SkSVGFeDisplacementMap

> 源文件: modules/svg/src/SkSVGFeDisplacementMap.cpp

## 概述

`SkSVGFeDisplacementMap` 实现了 SVG 滤镜中的位移映射效果(feDisplacementMap),这是一种高级图像处理技术,能够根据一个输入图像的颜色通道值对另一个输入图像的像素进行空间位移。该效果常用于创建扭曲、波纹、折射等视觉效果,是实现动态图像变形的核心组件。

位移映射的基本原理是使用位移图(displacement map)的颜色值作为位移量,将源图像的像素从原始位置移动到新位置。通过选择不同的颜色通道(R/G/B/A)作为 X 和 Y 方向的位移源,可以实现各种复杂的空间扭曲效果。缩放因子(scale)控制位移的强度。

## 架构位置

`SkSVGFeDisplacementMap` 在 Skia SVG 滤镜系统中的定位:

- **继承层次**: 继承自 `SkSVGFe` 基类,是具体滤镜效果实现之一
- **双输入滤镜**: 需要两个输入源(in 和 in2),in2 作为位移图
- **坐标空间转换**: 涉及对象边界框(OBB)和用户空间坐标系统的转换
- **颜色空间特殊处理**: 重写了 `resolveColorspace()`,in 保持原始颜色空间

在 SVG 规范中,feDisplacementMap 是少数需要精确控制颜色空间处理的滤镜之一,因为位移图的颜色值直接影响几何变换,而不仅仅是颜色混合。

## 主要类与结构体

### SkSVGFeDisplacementMap
位移映射滤镜的主类,管理位移映射的所有参数和逻辑。

**关键属性**:
- `fIn2`: 第二个输入源,用作位移图(SkSVGFeInputType)
- `fXChannelSelector`: X 方向位移使用的颜色通道(ChannelSelector 枚举)
- `fYChannelSelector`: Y 方向位移使用的颜色通道(ChannelSelector 枚举)
- `fScale`: 位移缩放因子(SkSVGNumberType),控制位移强度

**核心方法**:
- `onMakeImageFilter()`: 创建 DisplacementMap ImageFilter
- `resolveColorspace()`: 特殊的颜色空间处理逻辑
- `parseAndSetAttribute()`: 解析 SVG 属性

### ChannelSelector 枚举
定义了可选择的颜色通道:

```cpp
enum class ChannelSelector {
    kR,  // 红色通道
    kG,  // 绿色通道
    kB,  // 蓝色通道
    kA   // Alpha 通道
};
```

每个通道的值范围通常是 [0, 1],经过缩放后作为像素位移量。

## 公共 API 函数

### parseAndSetAttribute()
```cpp
bool parseAndSetAttribute(const char* name, const char* value)
```
解析位移映射滤镜的 SVG 属性。

**支持的属性**:
- `in2`: 位移图输入源标识符
- `xChannelSelector`: X 方向位移的通道选择器(R/G/B/A)
- `yChannelSelector`: Y 方向位移的通道选择器(R/G/B/A)
- `scale`: 位移缩放因子

**实现**: 使用链式短路求值,先调用基类解析,再处理本类特有属性

### onMakeImageFilter()
```cpp
sk_sp<SkImageFilter> onMakeImageFilter(
    const SkSVGRenderContext& ctx,
    const SkSVGFilterContext& fctx) const override
```
创建 Skia 的 DisplacementMap ImageFilter。

**处理流程**:
1. **解析裁剪区域**: 调用 `resolveFilterSubregion()` 获取作用范围
2. **确定颜色空间**: 调用 `resolveColorspace()` 确定 in2 的颜色空间
3. **解析输入源**:
   - `in`: 保持原始颜色空间(不进行颜色空间转换)
   - `in2`: 使用解析得到的颜色空间(通常是滤镜的颜色空间)
4. **缩放因子转换**: 如果使用对象边界框单位,将缩放因子转换为绝对值
5. **创建滤镜**: 调用 `SkImageFilters::DisplacementMap()`

**缩放因子处理**:
```cpp
if (primitiveUnits == objectBoundingBox) {
    scale = lengthContext.resolve(
        SkSVGLength(scale, Unit::kPercentage),
        LengthType::kOther
    );
}
```

### resolveColorspace()
```cpp
SkSVGColorspace resolveColorspace(
    const SkSVGRenderContext& ctx,
    const SkSVGFilterContext& fctx) const override
```
确定滤镜的颜色空间,特殊处理确保 in 输入保持原始颜色空间。

**规范要求**: 根据 SVG 规范,feDisplacementMap 的 in 输入必须保持其当前颜色空间不变,因为位移是几何操作而非颜色操作。返回的颜色空间实际上是 in 输入的颜色空间。

## 内部实现细节

### 位移映射原理
DisplacementMap 的核心算法:

```
对于输出图像的每个像素 (x, y):
1. 从位移图(in2)的 (x, y) 位置读取颜色值
2. 提取选定的通道值:
   dx = in2[x,y][xChannelSelector] - 0.5  // 中心化到 [-0.5, 0.5]
   dy = in2[x,y][yChannelSelector] - 0.5
3. 计算位移后的源坐标:
   srcX = x + dx * scale
   srcY = y + dy * scale
4. 从源图像(in)的 (srcX, srcY) 位置采样像素值
5. 将采样值写入输出图像的 (x, y) 位置
```

### 对象边界框单位处理
当 `primitiveUnits` 为 `objectBoundingBox` 时:

```cpp
const auto obbt = ctx.transformForCurrentOBB(fctx.primitiveUnits());
scale = SkSVGLengthContext({obbt.scale.x, obbt.scale.y})
            .resolve(SkSVGLength(scale, SkSVGLength::Unit::kPercentage),
                     SkSVGLengthContext::LengthType::kOther);
```

**转换步骤**:
1. 获取 OBB 变换(包含缩放和偏移)
2. 将缩放因子视为百分比值
3. 使用 OBB 的缩放系数解析为绝对像素值

这确保了位移量在不同坐标系统下保持一致的视觉效果。

### 颜色空间的特殊处理
```cpp
sk_sp<SkImageFilter> in = fctx.resolveInput(ctx, this->getIn());
sk_sp<SkImageFilter> in2 = fctx.resolveInput(ctx, this->getIn2(), colorspace);
```

关键差异:
- `in` 调用时**不传递**颜色空间参数,保持原始颜色空间
- `in2` 调用时传递 `colorspace` 参数,可能进行颜色空间转换

这符合 SVG 规范的要求,确保位移计算的正确性。

### 通道选择器解析
`SkSVGAttributeParser::parse<ChannelSelector>()` 模板特化:

```cpp
static constexpr std::tuple<const char*, ChannelSelector> gMap[] = {
    { "R", ChannelSelector::kR },
    { "G", ChannelSelector::kG },
    { "B", ChannelSelector::kB },
    { "A", ChannelSelector::kA },
};
```

解析器直接将字符串 "R", "G", "B", "A" 映射到对应的枚举值,使用 constexpr 确保编译时优化。

## 依赖关系

### 外部依赖
- `include/core/SkImageFilter.h`: ImageFilter 接口
- `include/core/SkM44.h`: 4x4 矩阵,用于坐标变换
- `include/effects/SkImageFilters.h`: DisplacementMap 滤镜工厂
- `modules/svg/include/SkSVGFilterContext.h`: 滤镜上下文管理
- `modules/svg/include/SkSVGRenderContext.h`: 渲染上下文

### 核心依赖
- `SkImageFilters::DisplacementMap()`: Skia 提供的位移映射实现
- `SkSVGLengthContext`: 长度单位解析器

### 被依赖情况
- 被 SVG 解析器在遇到 `<feDisplacementMap>` 元素时实例化
- 被 `SkSVGFilter` 作为滤镜链中的节点使用

## 设计模式与设计决策

### 策略模式 - 通道选择
通过枚举类型实现不同通道选择策略:
- **灵活性**: 可以独立选择 X 和 Y 方向的位移源通道
- **类型安全**: 使用枚举而非整数,避免无效值
- **可扩展**: 如需添加新通道(如自定义通道),只需扩展枚举

### 模板方法模式
继承自 `SkSVGFe`,重写关键方法:
- `onMakeImageFilter()`: 提供具体的滤镜创建逻辑
- `resolveColorspace()`: 提供特殊的颜色空间处理

### 设计决策说明

**为何 in 和 in2 使用不同的颜色空间处理**:
- **in**: 作为源图像,位移操作是几何变换,不应改变颜色
- **in2**: 作为位移图,其颜色值被解释为位移量,需要在正确的颜色空间中解释
- **规范要求**: SVG 1.1 规范明确要求这种区别对待

**为何需要缩放因子的单位转换**:
- 对象边界框单位下,缩放因子是相对值
- 绝对像素值才能正确控制位移距离
- 转换确保了不同坐标系统下的视觉一致性

**为何使用通道选择器而非直接指定 X/Y 值**:
- 提供了更大的灵活性,可以使用同一张位移图的不同通道
- 节省内存,无需为 X 和 Y 方向准备独立的位移图
- 符合 SVG 规范的设计

## 性能考量

### 计算复杂度
- **像素级操作**: 对输出的每个像素都需要查询位移图和采样源图像
- **时间复杂度**: O(width × height),与图像尺寸线性相关
- **采样成本**: 每个像素可能需要双线性插值,增加了计算量

### 内存占用
- **双输入**: 需要同时持有两个输入图像
- **中间缓冲**: 可能需要临时缓冲区存储位移后的结果
- **缓存友好性**: 位移操作可能导致非顺序访问,降低缓存效率

### GPU 加速
- **着色器实现**: 现代 GPU 可以高效执行位移映射
- **并行化**: 每个像素的计算相互独立,适合并行处理
- **纹理采样**: GPU 硬件纹理采样器可以高效处理插值

### 优化建议
1. **缩放因子控制**: 较小的缩放因子减少位移范围,提高缓存命中率
2. **裁剪区域**: 精确指定 cropRect,减少处理的像素数量
3. **位移图分辨率**: 使用较低分辨率的位移图可以减少内存访问
4. **通道选择**: 使用相同通道(如都用 R)可能允许编译器优化

### 性能特点
- **相对较慢**: 相比简单的颜色滤镜,位移映射计算量大
- **适合 GPU**: 这类操作在 GPU 上通常比 CPU 快 10-100 倍
- **分辨率敏感**: 性能与图像分辨率的平方成正比

## 相关文件

### 头文件
- `modules/svg/include/SkSVGFeDisplacementMap.h` - 类声明
- `modules/svg/include/SkSVGFe.h` - 基类定义
- `include/effects/SkImageFilters.h` - DisplacementMap 滤镜

### 相关实现
- `modules/svg/src/SkSVGFe.cpp` - 基类实现
- `modules/svg/src/SkSVGFilterContext.cpp` - 滤镜上下文
- `src/effects/imagefilters/SkDisplacementMapEffect.cpp` - Skia 底层实现

### 规范文档
- W3C SVG Filters 1.1 - feDisplacementMap 元素定义
- SVG 2.0 Draft - 更新的位移映射规范

### 应用示例
位移映射常用于:
- **水波纹效果**: 使用径向渐变作为位移图
- **文字扭曲**: 使用噪声图案创建手写效果
- **折射模拟**: 模拟透过不平整玻璃观看的效果
- **热浪效果**: 创建空气扭曲的视觉效果

该模块实现了 SVG 中最强大的图像变形工具之一,通过灵活的通道选择和精确的坐标系统转换,为创建各种动态视觉效果提供了坚实的技术基础。
