# SkImageFilter_Base

> 源文件
> - src/core/SkImageFilter_Base.h

## 概述

`SkImageFilter_Base` 是 Skia 图像滤镜系统的真正基类,所有图像滤镜实现都必须继承自这个类。它提供了图像滤镜执行、边界计算和缓存管理的完整框架。虽然公共 API 使用 `SkImageFilter`,但内部实现实际上继承自 `SkImageFilter_Base`。

该类定义了图像滤镜的核心接口,包括像素处理、输入/输出边界计算、透明度行为查询、矩阵能力检查等。它还管理子滤镜的递归调用和结果缓存,是 Skia 图像处理管道的核心组件。

## 架构位置

`SkImageFilter_Base` 在 Skia 图像滤镜系统中的位置:

```
应用层 (SkImageFilters 工厂)
    ↓
SkImageFilter (公共接口)
    ↓
SkImageFilter_Base (真正基类)
    ↓ (具体实现)
SkBlurImageFilter, SkColorFilterImageFilter, ...
```

它是连接公共 API 和具体滤镜实现的关键抽象层。

## 主要类与结构体

### SkImageFilter_Base

**继承关系:**
- 继承自: `SkImageFilter`
- 实现接口: `SkFlattenable` (通过基类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fInputs | AutoSTArray&lt;2, sk_sp&lt;SkImageFilter&gt;&gt; | 子滤镜数组 |
| fUsesSrcInput | bool | 是否使用源图像输入 |
| fUniqueID | uint32_t | 全局唯一标识符 |

**枚举类型:**

#### MatrixCapability

```cpp
using MatrixCapability = skif::MatrixCapability;
```

表示滤镜支持的矩阵变换能力:
- `kTranslate`: 只支持平移
- `kScaleTranslate`: 支持缩放和平移
- `kComplex`: 支持任意变换(包括旋转、斜切、透视)

### Common

**辅助类,用于反序列化:**

```cpp
class Common {
public:
    bool unflatten(SkReadBuffer&, int expectedInputs);
    std::optional<SkRect> cropRect() const;
    int inputCount() const;
    sk_sp<SkImageFilter>* inputs();
    sk_sp<SkImageFilter> getInput(int index);

private:
    std::optional<SkRect> fCropRect;
    skia_private::STArray<2, sk_sp<SkImageFilter>, true> fInputs;
};
```

**用途:** 从 SkReadBuffer 反序列化滤镜的通用数据。

## 公共 API 函数

### filterImage

```cpp
skif::FilterResult filterImage(const skif::Context& context) const;
```

**功能:** 执行图像滤镜,生成滤镜结果。

**参数:**
- `context`: 滤镜上下文,包含源图像、映射、输出边界等

**返回值:** `skif::FilterResult`,包含输出图像和位置信息。

**注意:** 如果结果为透明黑色或无法创建,返回 null FilterResult。

### makeImageWithFilter

```cpp
sk_sp<SkImage> makeImageWithFilter(sk_sp<skif::Backend> backend,
                                   sk_sp<SkImage> src,
                                   const SkIRect& subset,
                                   const SkIRect& clipBounds,
                                   SkIRect* outSubset,
                                   SkIPoint* offset) const;
```

**功能:** 直接对图像应用滤镜(实现 `SkImages::MakeWithFilter` API)。

**参数:**
- `backend`: 后端实现(CPU 或 GPU)
- `src`: 源图像
- `subset`: 源图像的感兴趣区域
- `clipBounds`: 裁剪边界
- `outSubset`: 输出区域(相对于 offset)
- `offset`: 输出图像的位置偏移

**返回值:** 滤镜后的图像。

### getInputBounds

```cpp
skif::LayerSpace<SkIRect> getInputBounds(
        const skif::Mapping& mapping,
        const skif::DeviceSpace<SkIRect>& desiredOutput,
        std::optional<skif::ParameterSpace<SkRect>> knownContentBounds) const;
```

**功能:** 计算为了生成指定输出所需的输入边界。

**参数:**
- `mapping`: 坐标空间映射
- `desiredOutput`: 期望的输出边界(设备空间)
- `knownContentBounds`: 已知的内容边界(参数空间,可选)

**返回值:** 所需的输入边界(层空间)。

**用途:** 确定需要绘制多大的源图像来满足输出需求。

### getOutputBounds

```cpp
std::optional<skif::DeviceSpace<SkIRect>> getOutputBounds(
        const skif::Mapping& mapping,
        const skif::ParameterSpace<SkRect>& contentBounds) const;
```

**功能:** 计算给定内容边界时滤镜的输出边界。

**参数:**
- `mapping`: 坐标空间映射
- `contentBounds`: 内容边界(参数空间)

**返回值:**
- 有值: 输出边界(设备空间)
- 无值: 输出无界(填充整个设备)

**用途:** 确定滤镜的影响范围。

### affectsTransparentBlack

```cpp
bool affectsTransparentBlack() const;
```

**功能:** 判断滤镜是否会将透明黑色转换为其他颜色。

**返回值:**
- true: 滤镜会改变透明黑色(如光照效果、纯色填充)
- false: 透明输入产生透明输出(如模糊、颜色调整)

**用途:** 优化,跳过已知为透明的区域。

### usesSource

```cpp
bool usesSource() const;
```

**功能:** 判断滤镜图是否引用源图像。

**返回值:** 如果滤镜或其子滤镜使用源图像,返回 true。

### getCTMCapability

```cpp
MatrixCapability getCTMCapability() const;
```

**功能:** 返回滤镜及其所有输入支持的最严格的矩阵能力。

**返回值:**
- `kTranslate`: 只能处理平移
- `kScaleTranslate`: 可以处理缩放和平移
- `kComplex`: 可以处理任意变换

### uniqueID

```cpp
uint32_t uniqueID() const;
```

**功能:** 返回滤镜的全局唯一标识符。

**用途:** 缓存键、调试标识。

## 受保护的方法(供子类使用)

### 构造函数

```cpp
SkImageFilter_Base(sk_sp<SkImageFilter> const* inputs, int inputCount,
                   std::optional<bool> usesSrc = {});
```

**参数:**
- `inputs`: 子滤镜数组
- `inputCount`: 子滤镜数量
- `usesSrc`: 是否使用源图像(可选,自动推断)

### flatten

```cpp
void flatten(SkWriteBuffer&) const override;
```

**功能:** 序列化滤镜。

**行为:** 写入子滤镜列表和滤镜特定数据。

### 辅助方法

#### getChildInputLayerBounds

```cpp
skif::LayerSpace<SkIRect> getChildInputLayerBounds(
        int index,
        const skif::Mapping& mapping,
        const skif::LayerSpace<SkIRect>& desiredOutput,
        std::optional<skif::LayerSpace<SkIRect>> contentBounds) const;
```

**功能:** 计算子滤镜的输入边界。

**行为:** 如果子滤镜为 null,返回 desiredOutput;否则递归调用子滤镜的 `onGetInputLayerBounds()`。

#### getChildOutputLayerBounds

```cpp
std::optional<skif::LayerSpace<SkIRect>> getChildOutputLayerBounds(
        int index,
        const skif::Mapping& mapping,
        std::optional<skif::LayerSpace<SkIRect>> contentBounds) const;
```

**功能:** 计算子滤镜的输出边界。

#### getChildOutput

```cpp
skif::FilterResult getChildOutput(int index, const skif::Context& ctx) const;
```

**功能:** 递归调用子滤镜的 `filterImage()`。

**行为:**
- 如果子滤镜为 null,返回上下文的动态源图像
- 否则,调用子滤镜的 `filterImage()`

## 纯虚函数(子类必须实现)

### onFilterImage

```cpp
virtual skif::FilterResult onFilterImage(const skif::Context& context) const = 0;
```

**功能:** 执行实际的滤镜操作。

**实现要求:**
- 处理输入为透明黑色的情况
- 如果不影响透明黑色,可以返回空结果
- 如果影响透明黑色,必须返回覆盖输出边界的图像

### onGetInputLayerBounds

```cpp
virtual skif::LayerSpace<SkIRect> onGetInputLayerBounds(
        const skif::Mapping& mapping,
        const skif::LayerSpace<SkIRect>& desiredOutput,
        std::optional<skif::LayerSpace<SkIRect>> contentBounds) const = 0;
```

**功能:** 计算所需的输入边界。

**实现要求:**
- 考虑滤镜的扩展(如模糊半径)
- 递归查询子滤镜的输入需求

### onGetOutputLayerBounds

```cpp
virtual std::optional<skif::LayerSpace<SkIRect>> onGetOutputLayerBounds(
        const skif::Mapping& mapping,
        std::optional<skif::LayerSpace<SkIRect>> contentBounds) const = 0;
```

**功能:** 计算输出边界。

**实现要求:**
- 递归查询子滤镜的输出
- 如果输出无界,返回 std::nullopt

## 可选虚函数(子类可选实现)

### onIsColorFilterNode

```cpp
virtual bool onIsColorFilterNode(SkColorFilter** filterPtr) const;
```

**功能:** 检查滤镜是否可以表示为纯颜色滤镜。

**默认实现:** 返回 false。

**用途:** 优化,将图像滤镜简化为颜色滤镜。

### onGetCTMCapability

```cpp
virtual MatrixCapability onGetCTMCapability() const;
```

**功能:** 返回滤镜支持的矩阵能力。

**默认实现:** 返回 `kScaleTranslate`。

### onAffectsTransparentBlack

```cpp
virtual bool onAffectsTransparentBlack() const;
```

**功能:** 判断滤镜是否影响透明黑色。

**默认实现:** 返回 false。

### ignoreInputsAffectsTransparentBlack

```cpp
virtual bool ignoreInputsAffectsTransparentBlack() const;
```

**功能:** 是否忽略子滤镜的透明黑色行为。

**默认实现:** 返回 false。

**用途:** 某些滤镜(如 Merge)总是传递透明黑色,不管子滤镜行为。

## 内部实现细节

### 缓存管理

`SkImageFilter_Base` 管理全局滤镜结果缓存:

```cpp
friend class SkGraphics;
static void PurgeCache();
```

**缓存策略:** 使用 LRU 缓存存储最近的滤镜结果,避免重复计算。

### 坐标空间系统

滤镜系统使用多个坐标空间:

1. **ParameterSpace:** 滤镜参数定义的空间(如模糊半径)
2. **LayerSpace:** 中间层渲染空间
3. **DeviceSpace:** 最终输出设备空间

**skif::Mapping** 管理这些空间之间的变换。

### 递归调用模式

滤镜执行是递归的:
```
filterImage()
    ↓
onFilterImage()
    ↓
getChildOutput() → 子滤镜.filterImage()
    ↓
递归...
```

### 子滤镜管理

```cpp
skia_private::AutoSTArray<2, sk_sp<SkImageFilter>> fInputs;
```

**优化:** 使用 `AutoSTArray`,0-2 个子滤镜时栈上分配,超过才使用堆。

### uniqueID 生成

```cpp
fUniqueID = SkNextID::ImageID();
```

使用全局计数器生成唯一 ID。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkImageFilter | 公共接口基类 |
| skif::Context / skif::Mapping | 坐标空间管理 |
| skif::FilterResult | 滤镜结果 |
| SkColorFilter | 颜色滤镜优化 |
| SkReadBuffer / SkWriteBuffer | 序列化 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkBlurImageFilter | 具体滤镜实现 |
| SkColorFilterImageFilter | 具体滤镜实现 |
| SkComposeImageFilter | 具体滤镜实现 |
| SkMergeImageFilter | 具体滤镜实现 |
| 所有其他图像滤镜 | 继承关系 |

## 设计模式与设计决策

### 模板方法模式

`SkImageFilter_Base` 定义算法框架,子类实现具体步骤:

```cpp
// 公共方法(框架)
skif::FilterResult filterImage(const skif::Context& context) const {
    // 缓存检查
    // 边界计算
    // 调用虚函数
    return this->onFilterImage(context);
}

// 纯虚函数(待实现)
virtual skif::FilterResult onFilterImage(const skif::Context& context) const = 0;
```

### 组合模式

滤镜形成树形结构:
- **叶子节点:** 无子滤镜的滤镜(如 ImageShader)
- **组合节点:** 有子滤镜的滤镜(如 Blur, Compose)

**递归处理:** 通过 `getChildOutput()` 递归调用子树。

### 策略模式

`MatrixCapability` 定义不同的矩阵处理策略:
- `kTranslate`: 简单策略,只处理平移
- `kScaleTranslate`: 中等策略,处理缩放和平移
- `kComplex`: 完整策略,处理任意变换

### 访问者模式变体

`onIsColorFilterNode()` 是访问者模式的简化版本:
- 允许外部代码查询滤镜的特定属性
- 避免了类型转换和 RTTI

## 性能考量

### 缓存机制

滤镜结果缓存避免重复计算:
```cpp
static void PurgeCache();  // 清空全局缓存
```

**策略:** 使用 LRU 缓存,基于 uniqueID 和上下文哈希。

### 小对象优化

子滤镜数组使用 `AutoSTArray`:
```cpp
skia_private::AutoSTArray<2, sk_sp<SkImageFilter>> fInputs;
```

**优化:** 大多数滤镜有 0-2 个输入,栈上分配避免堆开销。

### 边界计算优化

`affectsTransparentBlack()` 允许跳过透明区域:
- 如果为 false,已知透明的区域可以不处理
- 减少不必要的计算和内存访问

### 递归优化

`getChildOutput()` 自动处理 null 子滤镜:
```cpp
if (input == nullptr) {
    return context.source();  // 快速路径
}
return input->filterImage(context);  // 递归
```

避免了子类的重复检查。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkImageFilter.h | 基类 | 公共接口 |
| src/core/SkImageFilterTypes.h | 依赖 | 坐标空间类型 |
| src/core/SkImageFilterCache.h | 相关 | 滤镜缓存实现 |
| src/effects/imagefilters/*.cpp | 子类 | 具体滤镜实现 |
| include/effects/SkImageFilters.h | 使用者 | 工厂方法 |
| src/core/SkReadBuffer.h | 依赖 | 反序列化 |
| src/core/SkWriteBuffer.h | 依赖 | 序列化 |
