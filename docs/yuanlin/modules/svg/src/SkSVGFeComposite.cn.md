# SkSVGFeComposite

> 源文件: modules/svg/src/SkSVGFeComposite.cpp

## 概述

`SkSVGFeComposite` 实现了 SVG 滤镜效果中的合成操作(feComposite),它允许将两个输入源通过不同的合成模式组合成一个输出结果。该滤镜支持六种合成操作符:over(覆盖)、in(内部)、out(外部)、atop(顶部)、xor(异或)和 arithmetic(算术运算),是实现复杂图像混合效果的核心组件。

合成滤镜在图像处理中扮演着重要角色,特别是在需要精确控制图层混合方式时。算术合成模式提供了基于数学公式的像素级控制,而其他模式则对应经典的 Porter-Duff 合成算法,广泛应用于图形合成和透明度处理。

## 架构位置

`SkSVGFeComposite` 在 Skia SVG 滤镜系统中的位置:

- **继承关系**: 继承自 `SkSVGFe` 基类,是具体的滤镜效果实现之一
- **同级组件**: 与 FeBlend、FeColorMatrix、FeGaussianBlur 等其他滤镜效果并列
- **依赖映射**: 将 SVG 合成操作映射到 Skia 的 `SkBlendMode` 和 `SkImageFilters`
- **输入处理**: 需要两个输入源(in 和 in2),支持滤镜链式组合

在 SVG 文档流程中:SVG DOM → SkSVGFeComposite → SkImageFilters → Skia 渲染引擎

## 主要类与结构体

### SkSVGFeComposite
合成滤镜效果的主类,管理合成操作的所有逻辑。

**关键属性**:
- `fIn2`: 第二个输入源(SkSVGFeInputType 类型)
- `fOperator`: 合成操作符(SkSVGFeCompositeOperator 枚举)
- `fK1, fK2, fK3, fK4`: 算术合成模式的四个系数(SkSVGNumberType)

**核心方法**:
- `onMakeImageFilter()`: 创建对应的 SkImageFilter
- `parseAndSetAttribute()`: 解析 SVG 属性
- `BlendModeForOperator()`: 将 SVG 操作符转换为 Skia BlendMode

### SkSVGFeCompositeOperator
合成操作符的枚举类型,定义了六种操作模式:

```cpp
enum class SkSVGFeCompositeOperator {
    kOver,        // 覆盖:前景覆盖背景
    kIn,          // 内部:保留两者重叠部分的前景
    kOut,         // 外部:保留前景的非重叠部分
    kAtop,        // 顶部:前景在背景之上,但限制在背景范围内
    kXor,         // 异或:保留非重叠部分
    kArithmetic   // 算术:基于公式的像素混合
};
```

## 公共 API 函数

### parseAndSetAttribute()
```cpp
bool parseAndSetAttribute(const char* name, const char* value)
```
解析合成滤镜的 SVG 属性。

**支持的属性**:
- `in2`: 第二个输入源标识符
- `k1`, `k2`, `k3`, `k4`: 算术合成的系数
- `operator`: 合成操作符类型

**返回值**: 成功解析返回 true,否则返回 false

**实现特点**: 使用短路求值链式调用,先尝试父类属性,再处理本类特有属性

### BlendModeForOperator() (静态方法)
```cpp
static SkBlendMode BlendModeForOperator(SkSVGFeCompositeOperator op)
```
将 SVG 合成操作符映射到 Skia 的混合模式。

**映射关系**:
- `kOver` → `SkBlendMode::kSrcOver`
- `kIn` → `SkBlendMode::kSrcIn`
- `kOut` → `SkBlendMode::kSrcOut`
- `kAtop` → `SkBlendMode::kSrcATop`
- `kXor` → `SkBlendMode::kXor`
- `kArithmetic` → 触发断言(需要特殊处理)

**注意**: 算术模式不能直接映射为 BlendMode,会触发 `SkASSERT(false)`

### onMakeImageFilter()
```cpp
sk_sp<SkImageFilter> onMakeImageFilter(
    const SkSVGRenderContext& ctx,
    const SkSVGFilterContext& fctx) const override
```
创建 Skia ImageFilter 对象实现合成效果。

**处理流程**:
1. 解析滤镜子区域(cropRect)
2. 确定颜色空间(colorspace)
3. 解析两个输入源(background 和 foreground)
4. 根据操作符类型创建对应的 ImageFilter:
   - 算术模式: 使用 `SkImageFilters::Arithmetic()`
   - 其他模式: 使用 `SkImageFilters::Blend()`

**算术公式**:
```
result = k1 * input1 * input2 + k2 * input1 + k3 * input2 + k4
```

## 内部实现细节

### 算术合成实现
当操作符为 `kArithmetic` 时,使用特殊的算术滤镜:

```cpp
constexpr bool enforcePMColor = true;
return SkImageFilters::Arithmetic(
    fK1, fK2, fK3, fK4,
    enforcePMColor,  // 强制使用预乘 alpha
    background, foreground, cropRect);
```

**参数说明**:
- `enforcePMColor`: 设为 true,确保颜色使用预乘 alpha 格式
- 系数范围: 通常在 [0, 1] 之间,但可以超出此范围产生特殊效果
- **公式应用**: 对每个像素的每个颜色通道独立计算

### 混合模式合成实现
非算术模式使用标准的 Porter-Duff 混合:

```cpp
return SkImageFilters::Blend(
    BlendModeForOperator(fOperator),
    background, foreground, cropRect);
```

**输入顺序**:
- `background`: in2 输入(底层)
- `foreground`: in 输入(顶层)
- 顺序很重要,影响非对称操作(如 Over、Atop)的结果

### 属性解析器特化
`SkSVGAttributeParser::parse<SkSVGFeCompositeOperator>()` 的模板特化:

```cpp
static constexpr std::tuple<const char*, SkSVGFeCompositeOperator> gOpMap[] = {
    {"over", SkSVGFeCompositeOperator::kOver},
    {"in", SkSVGFeCompositeOperator::kIn},
    {"out", SkSVGFeCompositeOperator::kOut},
    {"atop", SkSVGFeCompositeOperator::kAtop},
    {"xor", SkSVGFeCompositeOperator::kXor},
    {"arithmetic", SkSVGFeCompositeOperator::kArithmetic},
};
```

使用 constexpr 数组确保编译时优化,运行时只需简单的线性查找或哈希映射。

## 依赖关系

### 外部依赖
- `include/core/SkBlendMode.h`: Skia 混合模式定义
- `include/core/SkImageFilter.h`: 图像滤镜接口
- `include/effects/SkImageFilters.h`: 图像滤镜工厂函数
- `modules/svg/include/SkSVGAttributeParser.h`: 属性解析框架
- `modules/svg/include/SkSVGFilterContext.h`: 滤镜上下文管理

### 基类依赖
- 继承自 `SkSVGFe`,复用基类的子区域解析和颜色空间处理逻辑

### 被依赖情况
- 被 `SkSVGFilter` 作为滤镜效果链中的一个节点使用
- SVG 解析器在遇到 `<feComposite>` 元素时实例化此类

## 设计模式与设计决策

### 策略模式
使用操作符枚举配合条件分支实现不同的合成策略:
- **优势**: 易于添加新的合成模式,只需扩展枚举和添加分支
- **实现**: `onMakeImageFilter()` 中的 if-else 分支

### 适配器模式
将 SVG 标准的合成操作映射到 Skia 的 BlendMode:
- **解耦**: SVG 层和 Skia 渲染层使用各自的类型系统
- **灵活性**: 如果 Skia BlendMode 改变,只需修改映射函数

### 工厂方法模式
通过 `SkImageFilters` 工厂创建具体的滤镜对象:
- **抽象**: 调用者不需要知道具体的 ImageFilter 实现类
- **一致性**: 所有滤镜效果都使用相同的创建模式

### 设计决策说明

**为何区分算术和混合模式**:
- 算术模式需要四个额外的系数参数
- 混合模式直接对应 Porter-Duff 算法,性能更优
- 分开处理使代码逻辑更清晰

**为何使用静态 BlendModeForOperator**:
- 映射逻辑是纯函数,不依赖对象状态
- 便于单独测试和复用
- 可能被编译器内联优化

**为何强制使用预乘 alpha**:
- 预乘格式在合成时数学上更正确
- 避免边缘出现意外的透明度伪影
- 与 Skia 的渲染管线一致

## 性能考量

### 滤镜创建开销
- **轻量级对象**: ImageFilter 的创建是引用计数的,开销很小
- **延迟计算**: 实际的像素处理发生在渲染时,而非创建时
- **缓存可能**: Skia 可能缓存滤镜结果,避免重复计算

### 算术模式性能
- **像素级计算**: 算术模式对每个像素执行4个乘法和3个加法
- **矢量化**: 现代 CPU 可以使用 SIMD 指令并行处理多个像素
- **复杂度**: O(width × height),与图像尺寸线性相关

### 混合模式性能
- **硬件加速**: 标准混合模式通常可以使用 GPU 加速
- **优化**: Porter-Duff 算法在图形硬件中有高度优化的实现
- **比较**: 混合模式通常比算术模式快 2-3 倍

### 内存使用
- **双输入**: 需要同时持有两个输入图像的引用
- **临时缓冲**: 可能需要临时缓冲区存储中间结果
- **裁剪优化**: cropRect 可以减少处理的像素数量

### 优化建议
1. **子区域裁剪**: 尽可能精确指定 cropRect,减少处理区域
2. **操作符选择**: 优先使用标准混合模式而非算术模式
3. **输入复用**: 如果多个合成使用相同输入,可以共享滤镜节点

## 相关文件

### 头文件
- `modules/svg/include/SkSVGFeComposite.h` - 类声明和枚举定义
- `modules/svg/include/SkSVGFe.h` - 基类定义
- `include/core/SkBlendMode.h` - Skia 混合模式
- `include/effects/SkImageFilters.h` - 图像滤镜工厂

### 相关实现
- `modules/svg/src/SkSVGFe.cpp` - 基类实现
- `modules/svg/src/SkSVGFeBlend.cpp` - 类似的混合滤镜
- `modules/svg/src/SkSVGFilterContext.cpp` - 滤镜上下文管理

### 规范文档
- W3C SVG Filters 1.1 Specification - feComposite 元素定义
- Porter-Duff Compositing Paper - 合成算法的理论基础

### 测试文件
- `modules/svg/tests/FeCompositeTest.cpp` - 单元测试
- `resources/svg/filters/feComposite*.svg` - 测试用 SVG 文件

该模块实现了 SVG 合成滤镜的完整功能,通过支持多种合成模式和算术运算,为复杂的图像混合效果提供了强大而灵活的工具。其设计充分考虑了性能和标准兼容性,是 SVG 滤镜系统中不可或缺的组成部分。
