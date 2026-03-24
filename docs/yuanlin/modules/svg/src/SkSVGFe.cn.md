# SkSVGFe

> 源文件: modules/svg/src/SkSVGFe.cpp

## 概述

`SkSVGFe` 是 Skia SVG 模块中所有滤镜效果(Filter Effects)的抽象基类实现。该模块定义了 SVG 滤镜元素的核心行为,包括滤镜子区域解析、输入源管理、颜色空间处理等通用功能。作为滤镜系统的基础架构,它为所有具体的滤镜效果(如 feBlend、feGaussianBlur 等)提供了统一的接口和公共实现。

该模块实现了 W3C SVG 滤镜规范中定义的基础属性处理逻辑,特别是滤镜原语子区域(filter primitive subregion)的计算规则,这是滤镜效果链式组合的关键机制。通过标准化的输入输出管理,不同滤镜效果可以无缝连接形成复杂的图像处理管道。

## 架构位置

`SkSVGFe` 在 Skia 的 SVG 模块中处于核心基类位置:

- **层次结构**: 作为抽象基类,被所有具体滤镜效果类继承
- **子类包括**: FeBlend、FeColorMatrix、FeComposite、FeGaussianBlur、FeMorphology 等 15+ 个滤镜效果
- **上层交互**: 由 `SkSVGFilter` 和 `SkSVGFilterContext` 调用,负责协调滤镜效果的渲染
- **下层依赖**: 使用 Skia 的 `SkImageFilter` 作为底层图像滤镜实现

在滤镜处理流程中,该类处于 SVG DOM 结构和 Skia 渲染引擎之间的适配层,负责将 SVG 属性转换为 Skia 可理解的图像滤镜参数。

## 主要类与结构体

### SkSVGFe (基类)
所有 SVG 滤镜效果的抽象基类,定义了滤镜元素的公共接口和通用属性:

**核心属性**:
- `fIn`: 输入源标识符(SkSVGFeInputType 类型)
- `fResult`: 滤镜输出结果的命名标识
- `fX, fY, fWidth, fHeight`: 定义滤镜效果子区域的矩形边界

**核心方法**:
- `makeImageFilter()`: 创建对应的 SkImageFilter 对象
- `resolveFilterSubregion()`: 计算滤镜效果的作用区域
- `resolveColorspace()`: 确定滤镜的颜色空间

### SkSVGFeInputType
表示滤镜输入源的类型系统,支持以下输入类型:

**标准输入**:
- `kSourceGraphic`: 原始图形内容
- `kSourceAlpha`: 原始图形的 alpha 通道
- `kBackgroundImage`: 背景图像
- `kBackgroundAlpha`: 背景图像的 alpha 通道
- `kFillPaint`: 填充画笔
- `kStrokePaint`: 描边画笔

**引用输入**:
- `kFilterPrimitiveReference`: 引用其他滤镜效果的输出结果
- `kUnspecified`: 未指定,使用前一个滤镜的输出

## 公共 API 函数

### makeImageFilter()
```cpp
sk_sp<SkImageFilter> makeImageFilter(
    const SkSVGRenderContext& ctx,
    const SkSVGFilterContext& fctx) const
```
创建 Skia 的 ImageFilter 对象。这是一个委托方法,实际调用纯虚函数 `onMakeImageFilter()`,由子类实现具体的滤镜逻辑。

**参数**:
- `ctx`: SVG 渲染上下文,包含变换矩阵、长度解析器等信息
- `fctx`: 滤镜上下文,管理滤镜效果的输入输出和子区域

### resolveFilterSubregion()
```cpp
SkRect resolveFilterSubregion(
    const SkSVGRenderContext& ctx,
    const SkSVGFilterContext& fctx) const
```
计算滤镜效果的作用子区域。实现了 SVG 规范中定义的复杂区域计算逻辑:

**计算规则**:
1. 如果没有输入或输入为标准源,默认子区域为滤镜效果区域
2. 如果有输入引用,默认子区域为所有输入子区域的并集
3. 如果 x/y/width/height 属性被显式指定,则覆盖对应的默认值

**返回**: 计算得到的完整解析后的矩形区域

### resolveBoundaries()
```cpp
SkRect resolveBoundaries(
    const SkSVGRenderContext& ctx,
    const SkSVGFilterContext& fctx) const
```
解析滤镜元素的边界属性(x, y, width, height)为绝对坐标矩形。

**默认值处理**:
- x, y 默认为 0%
- width, height 默认为 100%
- 百分比值相对于对象边界框(OBB)或用户空间坐标计算

### resolveColorspace()
```cpp
SkSVGColorspace resolveColorspace(
    const SkSVGRenderContext& ctx,
    const SkSVGFilterContext& fctx) const
```
确定滤镜效果使用的颜色空间。默认实现返回 `color-interpolation-filters` 属性的值,如果为 `auto` 则使用 sRGB。

### parseAndSetAttribute()
```cpp
bool parseAndSetAttribute(const char* name, const char* value)
```
解析并设置滤镜元素的属性。处理以下标准属性:
- `in`: 输入源
- `result`: 输出结果标识
- `x`, `y`, `width`, `height`: 子区域边界

## 内部实现细节

### AnyIsStandardInput() 辅助函数
```cpp
static bool AnyIsStandardInput(
    const SkSVGFilterContext& fctx,
    const std::vector<SkSVGFeInputType>& inputs)
```
判断输入列表中是否包含标准输入源(非引用类型)。这个函数用于确定默认子区域的计算方式:
- 标准输入源需要使用完整的滤镜效果区域
- 引用输入可以使用更精确的子区域并集

### 输入类型解析
`SkSVGAttributeParser::parse<SkSVGFeInputType>()` 模板特化实现了输入类型的解析:

**解析逻辑**:
1. 首先尝试匹配预定义的标准输入关键字(SourceGraphic 等)
2. 如果不是关键字,则解析为字符串,视为引用其他滤镜的结果标识符
3. 返回包装后的 SkSVGFeInputType 对象

**枚举映射表**:
```cpp
static constexpr std::tuple<const char*, Type> gTypeMap[] = {
    {"SourceGraphic", Type::kSourceGraphic},
    {"SourceAlpha", Type::kSourceAlpha},
    {"BackgroundImage", Type::kBackgroundImage},
    {"BackgroundAlpha", Type::kBackgroundAlpha},
    {"FillPaint", Type::kFillPaint},
    {"StrokePaint", Type::kStrokePaint},
};
```

### 子区域计算算法
`resolveFilterSubregion()` 的实现体现了 SVG 规范的精确要求:

1. **获取输入列表**: 调用子类的 `getInputs()` 方法
2. **计算默认子区域**:
   - 空输入或包含标准输入 → 使用 `filterEffectsRegion()`
   - 仅引用输入 → 计算所有输入子区域的 `join()`(并集)
3. **解析显式边界**: 调用 `resolveBoundaries()` 获取属性值
4. **合并结果**: 对于每个维度,如果属性存在则使用属性值,否则使用默认值

## 依赖关系

### 头文件依赖
- `modules/svg/include/SkSVGFe.h`: 类声明
- `modules/svg/include/SkSVGAttribute.h`: 属性类型定义
- `modules/svg/include/SkSVGAttributeParser.h`: 属性解析框架
- `modules/svg/include/SkSVGFilterContext.h`: 滤镜上下文管理
- `modules/svg/include/SkSVGRenderContext.h`: 渲染上下文

### 标准库依赖
- `<cstddef>`: 大小类型定义
- `<tuple>`: 用于枚举映射表

### 被依赖关系
所有具体滤镜效果类都依赖此基类:
- SkSVGFeBlend
- SkSVGFeColorMatrix
- SkSVGFeComposite
- SkSVGFeGaussianBlur
- SkSVGFeMorphology
- SkSVGFeLighting (及其子类)
- 等 15+ 个滤镜效果类

## 设计模式与设计决策

### 模板方法模式
`makeImageFilter()` 使用模板方法模式:
- **public 接口**: `makeImageFilter()` 提供统一的外部调用点
- **protected 钩子**: `onMakeImageFilter()` 由子类实现具体逻辑
- **优势**: 保持接口稳定性的同时允许子类定制行为

### 策略模式 - 输入类型
`SkSVGFeInputType` 采用策略模式,支持多种输入源类型:
- **类型枚举**: 定义预定义的输入类型
- **动态引用**: 支持通过字符串引用其他滤镜结果
- **统一接口**: 上层代码无需关心输入类型的具体实现

### 责任链模式 - 属性解析
属性解析使用责任链模式:
```cpp
return INHERITED::parseAndSetAttribute(name, value) ||
       this->setIn(...) ||
       this->setResult(...) ||
       this->setX(...);
```
每个方法尝试处理,失败则传递给下一个处理器,直到成功或全部失败。

### 设计决策说明

**为何使用虚函数 onMakeImageFilter()**:
- 允许子类完全控制 ImageFilter 的创建逻辑
- 保持基类接口简洁,避免在基类中堆积大量子类特定的代码

**为何区分边界和子区域**:
- `resolveBoundaries()`: 仅处理属性解析
- `resolveFilterSubregion()`: 实现完整的规范逻辑
- 分离关注点,便于测试和维护

**为何使用静态辅助函数**:
- `AnyIsStandardInput()` 不需要访问成员变量
- 降低耦合度,可能被编译器更好地优化

## 性能考量

### 子区域计算优化
- **懒计算**: 子区域只在需要时计算,不预先缓存
- **短路求值**: 标准输入检测使用早期返回,避免遍历全部输入
- **引用计数**: 使用 `sk_sp<>` 智能指针管理 ImageFilter 生命周期

### 属性解析效率
- **短路机制**: 属性匹配成功后立即返回,平均复杂度 O(1)
- **字符串比较**: 直接使用字符串指针,避免不必要的复制
- **枚举映射**: 使用 constexpr 数组,编译时确定,零运行时开销

### 内存管理
- **智能指针**: 所有 ImageFilter 使用 sk_sp 管理,自动释放
- **临时对象**: 子区域计算使用栈上临时变量,无堆分配
- **向量操作**: 输入列表通常很小(1-2个),避免动态扩容

### 潜在优化点
1. **子区域缓存**: 对于静态滤镜,可以缓存计算结果
2. **输入类型预编译**: 可以在解析时确定输入类型,避免运行时查询
3. **属性哈希表**: 对于属性较多的子类,可以使用哈希表加速查找

## 相关文件

### 核心头文件
- `modules/svg/include/SkSVGFe.h` - 基类声明
- `modules/svg/include/SkSVGFilterContext.h` - 滤镜上下文
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文

### 子类实现文件
- `modules/svg/src/SkSVGFeBlend.cpp` - 混合滤镜
- `modules/svg/src/SkSVGFeColorMatrix.cpp` - 颜色矩阵滤镜
- `modules/svg/src/SkSVGFeComposite.cpp` - 合成滤镜
- `modules/svg/src/SkSVGFeGaussianBlur.cpp` - 高斯模糊滤镜
- `modules/svg/src/SkSVGFeLighting.cpp` - 光照滤镜基类

### 相关系统文件
- `include/effects/SkImageFilters.h` - Skia 图像滤镜工厂
- `modules/svg/include/SkSVGAttribute.h` - SVG 属性类型系统
- `modules/svg/include/SkSVGTypes.h` - SVG 基础类型定义

### 测试文件
- `modules/svg/tests/*FilterTest.cpp` - 滤镜效果单元测试
- `resources/svg/filters/*` - SVG 滤镜测试资源

该模块是 Skia SVG 滤镜系统的基石,通过提供统一的基类接口和完善的子区域计算逻辑,支撑起了整个滤镜效果体系的运作。其设计充分考虑了 SVG 规范的要求,同时兼顾了性能和可扩展性。
