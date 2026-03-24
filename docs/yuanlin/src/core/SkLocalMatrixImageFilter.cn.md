# SkLocalMatrixImageFilter

> 源文件
> - src/core/SkLocalMatrixImageFilter.h
> - src/core/SkLocalMatrixImageFilter.cpp

## 概述

`SkLocalMatrixImageFilter` 是一个包装器图像滤镜,用于在执行子滤镜时应用额外的本地矩阵变换。它不直接修改图像内容,而是通过修改滤镜上下文的参数空间来影响子滤镜的行为。该滤镜将本地矩阵与子滤镜结合在一起,使得在应用子滤镜时就像先对上下文应用了该矩阵一样。

这个类的主要作用是在不改变子滤镜实现的情况下,通过矩阵变换来修改滤镜的执行方式,实现了装饰器模式的变体应用。

## 架构位置

`SkLocalMatrixImageFilter` 位于 Skia 图像处理管道中的核心层:

```
include/core/SkImageFilter (公共接口)
    ↓
src/core/SkImageFilter_Base (基础实现)
    ↓
src/core/SkLocalMatrixImageFilter (本地矩阵变换包装器)
    ↓ (包装)
任意其他 SkImageFilter 子类
```

它作为一个中间层存在,用于在滤镜链中插入矩阵变换逻辑,而不需要每个滤镜自己实现变换支持。

## 主要类与结构体

### SkLocalMatrixImageFilter

**继承关系:**
- 继承自: `SkImageFilter_Base`
- 实现接口: `SkFlattenable` (通过基类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fLocalMatrix | SkMatrix | 要应用于子滤镜上下文的本地矩阵 |
| fInvLocalMatrix | SkMatrix | fLocalMatrix 的逆矩阵,用于边界计算 |

**关键方法:**

| 方法 | 说明 |
|------|------|
| Make() | 静态工厂方法,创建本地矩阵滤镜实例 |
| onFilterImage() | 应用本地矩阵后执行子滤镜 |
| onGetInputLayerBounds() | 计算所需的输入边界 |
| onGetOutputLayerBounds() | 计算输出边界 |
| localMapping() | 创建应用了本地矩阵的新映射 |

## 公共 API 函数

### Make

```cpp
static sk_sp<SkImageFilter> Make(const SkMatrix& localMatrix, sk_sp<SkImageFilter> input);
```

**功能:** 创建一个新的本地矩阵图像滤镜。

**参数:**
- `localMatrix`: 要应用的本地矩阵变换
- `input`: 被包装的子图像滤镜

**返回值:**
- 成功时返回新创建的 `SkLocalMatrixImageFilter` 智能指针
- 如果 input 为空或矩阵是单位矩阵,返回原始 input
- 如果矩阵不可逆或子滤镜不支持该变换,返回 nullptr

**验证逻辑:**
1. 检查 input 是否为空
2. 如果矩阵是单位矩阵,直接返回 input
3. 检查子滤镜的 CTM 能力是否支持该矩阵类型
4. 尝试计算矩阵逆,失败则返回 nullptr

### computeFastBounds

```cpp
SkRect computeFastBounds(const SkRect& bounds) const override;
```

**功能:** 快速计算滤镜输出的边界,不需要 Mapping 参数。

**实现策略:**
- 使用逆矩阵将 bounds 映射到局部空间
- 传递给子滤镜计算
- 将结果使用正矩阵映射回原始空间

## 内部实现细节

### 矩阵应用机制

`SkLocalMatrixImageFilter` 的核心在于如何修改滤镜上下文:

```cpp
skif::Mapping localMapping(const skif::Mapping& mapping) const {
    skif::Mapping localMapping = mapping;
    localMapping.concatLocal(fLocalMatrix);
    return localMapping;
}
```

这个方法创建了一个新的映射,通过 `concatLocal()` 将本地矩阵与现有映射组合。关键点在于:
- **参数空间变换:** 本地矩阵直接修改参数空间,而不是层空间
- **变换顺序:** 使用 L*P 形式,而不是 (L*P*L^-1) 形式

### 滤镜执行流程

```cpp
skif::FilterResult SkLocalMatrixImageFilter::onFilterImage(const skif::Context& ctx) const {
    skif::Mapping localMapping = this->localMapping(ctx.mapping());
    return this->getChildOutput(0, ctx.withNewMapping(localMapping));
}
```

执行步骤:
1. 从当前上下文提取映射
2. 应用本地矩阵创建新映射
3. 用新映射创建新上下文
4. 递归调用子滤镜

### 边界计算

**输入边界计算:**
```cpp
skif::LayerSpace<SkIRect> onGetInputLayerBounds(
        const skif::Mapping& mapping,
        const skif::LayerSpace<SkIRect>& desiredOutput,
        std::optional<skif::LayerSpace<SkIRect>> contentBounds) const {
    return this->getChildInputLayerBounds(0, this->localMapping(mapping),
                                          desiredOutput, contentBounds);
}
```

关键点:
- `desiredOutput` 和 `contentBounds` 已经在层空间,无需变换
- 只需将本地矩阵应用到 mapping 上
- 层空间参数保持不变,因为它们与映射无关

**输出边界计算:**
类似的逻辑,也是修改映射而不是边界本身。

### 序列化支持

```cpp
void SkLocalMatrixImageFilter::flatten(SkWriteBuffer& buffer) const {
    this->SkImageFilter_Base::flatten(buffer);
    buffer.writeMatrix(fLocalMatrix);
    // fInvLocalMatrix 在反序列化时重新计算
}
```

- 只保存正矩阵,不保存逆矩阵
- 反序列化时通过 `CreateProc` 重新计算逆矩阵

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkImageFilter_Base | 基类,提供滤镜框架 |
| SkMatrix | 矩阵变换 |
| skif::Context | 滤镜执行上下文 |
| skif::Mapping | 坐标空间映射 |
| SkReadBuffer / SkWriteBuffer | 序列化支持 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkImageFilters | 作为工厂方法的返回值 |
| 各种具体滤镜实现 | 作为包装器使用 |
| SkPicture / SKP 序列化 | 保存滤镜图 |

## 设计模式与设计决策

### 装饰器模式

`SkLocalMatrixImageFilter` 是装饰器模式的典型应用:
- **包装对象:** 包装任意 `SkImageFilter`
- **透明扩展:** 在不修改子滤镜的情况下添加矩阵变换功能
- **职责明确:** 只负责矩阵变换,实际滤镜逻辑由子滤镜处理

### 参数空间 vs 层空间设计

代码注释中强调了一个重要设计决策:

```cpp
// NOTE: This is not a ParameterSpace<SkMatrix> like that of SkMatrixTransformImageFilter.
// It's a bit pedantic, but does impact the math. A parameter-space transform has to be modified
// to represent a layer-space transform: (L*P*L^-1); while this local matrix changes L directly
// to L*P for its child filter.
```

**设计决策:**
- `SkLocalMatrixImageFilter` 直接修改层到参数空间的映射 (L → L*P)
- `SkMatrixTransformImageFilter` 应用层空间变换 (L*P*L^-1)
- 这种区别影响了边界计算和滤镜执行的数学逻辑

### 早期返回优化

在 `Make()` 方法中实现了多个早期返回优化:

1. **空输入检查:** 如果没有子滤镜,返回 nullptr
2. **单位矩阵优化:** 如果矩阵不改变任何东西,直接返回原始滤镜
3. **能力检查:** 如果子滤镜不支持所需的矩阵类型,返回 nullptr
4. **可逆性检查:** 如果矩阵不可逆,无法计算边界,返回 nullptr

这些优化避免了不必要的对象创建和计算。

## 性能考量

### 矩阵缓存

滤镜同时存储正矩阵和逆矩阵:
```cpp
SkMatrix fLocalMatrix;
SkMatrix fInvLocalMatrix;
```

**优势:**
- 避免重复计算逆矩阵
- 逆矩阵用于 `computeFastBounds()` 计算

**成本:**
- 增加了 18 个 float 的内存开销 (两个 3x3 矩阵)
- 对于频繁调用的滤镜,这个权衡是值得的

### 递归效率

滤镜执行是单次递归调用:
```cpp
return this->getChildOutput(0, ctx.withNewMapping(localMapping));
```

- 没有额外的像素复制
- 只修改上下文对象,基本上是零开销的装饰
- 实际的滤镜工作由子滤镜完成

### 能力检查避免无效操作

在 `Make()` 中检查子滤镜的 CTM 能力:
```cpp
if ((inputCapability == MatrixCapability::kTranslate && !localMatrix.isTranslate()) ||
    (inputCapability == MatrixCapability::kScaleTranslate && !localMatrix.isScaleTranslate())) {
    return nullptr;
}
```

这防止了创建无法正确执行的滤镜实例,避免了运行时错误。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkImageFilter_Base.h | 基类 | 提供滤镜基础框架 |
| src/core/SkImageFilterTypes.h | 依赖 | 定义 skif::Context, skif::Mapping 等类型 |
| src/effects/imagefilters/SkMatrixTransformImageFilter.cpp | 相关 | 另一种矩阵变换滤镜实现 |
| include/core/SkMatrix.h | 依赖 | 矩阵数学运算 |
| src/core/SkReadBuffer.h | 依赖 | 反序列化支持 |
| src/core/SkWriteBuffer.h | 依赖 | 序列化支持 |
