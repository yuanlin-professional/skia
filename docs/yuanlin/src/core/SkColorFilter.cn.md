# SkColorFilter

> 源文件: include/core/SkColorFilter.h, src/core/SkColorFilter.cpp

## 概述

`SkColorFilter` 是 Skia 绘制管线中的可选对象,用于在绘制过程中对颜色进行变换。当存在于 `SkPaint` 中时,它会接收源颜色并返回新颜色,然后传递给管线的下一阶段(如 ImageFilter 或 Xfermode)。颜色过滤器必须是线程安全的,可以在多个线程间共享同一实例。

## 架构位置

`SkColorFilter` 位于 Skia 核心公共 API 层(include/core),是绘制管线的关键组件之一。它位于着色器输出和混合模式之间,提供颜色变换能力。实际实现由 `SkColorFilterBase` 提供,但对外暴露的是简洁的抽象接口。

## 主要类与结构体

### SkColorFilter

| 特性 | 说明 |
|------|------|
| 继承关系 | 继承自 `SkFlattenable` |
| 线程安全 | 必须线程安全 |
| 不可变性 | 一旦创建,状态不可变 |

**关键成员变量:**

此类只定义接口,无公开成员变量。实际数据由子类(如 `SkColorFilterBase`)管理。

### SkColorFilters

工厂类,提供静态方法创建各种类型的颜色过滤器。

## 公共 API 函数

### 查询和转换

```cpp
bool asAColorMode(SkColor* color, SkBlendMode* mode) const;
```
- 如果过滤器可以表示为"颜色 + 混合模式",返回 true 并设置参数
- 用于优化特定类型的颜色过滤器

```cpp
bool asAColorMatrix(float matrix[20]) const;
```
- 如果过滤器可以表示为 5x4 矩阵,返回 true 并设置矩阵
- 矩阵格式:[R, G, B, A, Offset] 五行

```cpp
bool isAlphaUnchanged() const;
```
- 如果过滤器保证不改变 alpha 值,返回 true
- 用于优化某些混合操作

### 颜色过滤

```cpp
SkColor4f filterColor4f(const SkColor4f& srcColor, SkColorSpace* srcCS,
                        SkColorSpace* dstCS) const;
```
- 将源颜色从源色彩空间转换到目标色彩空间,然后应用过滤器
- 返回目标色彩空间中的过滤后颜色

### 组合和变换

```cpp
sk_sp<SkColorFilter> makeComposed(sk_sp<SkColorFilter> inner) const;
```
- 创建组合过滤器: `result = this(inner(...))`
- 先应用 inner,再应用当前过滤器

```cpp
sk_sp<SkColorFilter> makeWithWorkingColorSpace(sk_sp<SkColorSpace>) const;
```
- 创建在特定色彩空间中计算的过滤器
- 默认在目标(表面)色彩空间中操作

### 序列化

```cpp
static sk_sp<SkColorFilter> Deserialize(const void* data, size_t size,
                                        const SkDeserialProcs* procs = nullptr);
```
- 从序列化数据重建颜色过滤器

## SkColorFilters 工厂方法

### 基础过滤器

```cpp
static sk_sp<SkColorFilter> Compose(const sk_sp<SkColorFilter>& outer,
                                    sk_sp<SkColorFilter> inner);
```
- 组合两个颜色过滤器

```cpp
static sk_sp<SkColorFilter> Blend(const SkColor4f& c, sk_sp<SkColorSpace>, SkBlendMode mode);
static sk_sp<SkColorFilter> Blend(SkColor c, SkBlendMode mode);
```
- 在常量颜色(src)和输入颜色(dst)之间混合
- 如果色彩空间为 null,假定常量颜色定义在 sRGB

### 矩阵过滤器

```cpp
static sk_sp<SkColorFilter> Matrix(const SkColorMatrix&, Clamp clamp = Clamp::kYes);
static sk_sp<SkColorFilter> Matrix(const float rowMajor[20], Clamp clamp = Clamp::kYes);
```
- 应用 5x4 颜色矩阵变换
- 可选择是否钳位输出到 [0, 1]

```cpp
static sk_sp<SkColorFilter> HSLAMatrix(const SkColorMatrix&);
static sk_sp<SkColorFilter> HSLAMatrix(const float rowMajor[20]);
```
- 在 HSLA 色彩空间中应用矩阵
- 等价于: `HSLA-to-RGBA(Matrix(RGBA-to-HSLA(input)))`

### 伽马过滤器

```cpp
static sk_sp<SkColorFilter> LinearToSRGBGamma();
static sk_sp<SkColorFilter> SRGBToLinearGamma();
```
- 线性和 sRGB 伽马空间之间的转换

### 插值过滤器

```cpp
static sk_sp<SkColorFilter> Lerp(float t, sk_sp<SkColorFilter> dst, sk_sp<SkColorFilter> src);
```
- 在两个颜色过滤器之间插值

### 表格过滤器

```cpp
static sk_sp<SkColorFilter> Table(const uint8_t table[256]);
```
- 对所有 4 个通道应用相同的查找表
- 操作在非预乘空间,如果输入是预乘的,会自动处理

```cpp
static sk_sp<SkColorFilter> TableARGB(const uint8_t tableA[256],
                                      const uint8_t tableR[256],
                                      const uint8_t tableG[256],
                                      const uint8_t tableB[256]);
```
- 为每个通道指定不同的查找表
- null 表示该通道不变(恒等变换)

```cpp
static sk_sp<SkColorFilter> Table(sk_sp<SkColorTable> table);
```
- 使用共享的颜色表

### 光照过滤器

```cpp
static sk_sp<SkColorFilter> Lighting(SkColor mul, SkColor add);
```
- 先乘以 mul 颜色,然后加上 add 颜色
- 结果钳位到 [0, 255]
- 忽略 alpha 通道

## 内部实现细节

### 实际实现委托

公共 API 方法委托给 `SkColorFilterBase`:

```cpp
bool SkColorFilter::asAColorMode(SkColor* color, SkBlendMode* mode) const {
    return as_CFB(this)->onAsAColorMode(color, mode);
}
```

### 色彩空间转换

`filterColor4f` 使用 `SkColorSpaceXformSteps` 进行色彩空间转换:
```cpp
SkColorSpaceXformSteps(srcCS, kUnpremul_SkAlphaType,
                       dstCS, kPremul_SkAlphaType).apply(color.vec());
```
- 将输入从源色彩空间转换到目标色彩空间
- 在目标色彩空间中应用过滤器
- 结果钳位 alpha 到 [0, 1] 并去预乘

### 工作色彩空间

`makeWithWorkingColorSpace` 使用 `SkColorFilterPriv::WithWorkingFormat` 包装过滤器,使其在指定色彩空间中操作。

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkFlattenable` | 序列化基类 |
| `SkColorSpace` | 色彩空间管理 |
| `SkColorSpaceXformSteps` | 色彩空间转换 |
| `SkColorTable` | 表格查找 |
| `SkColorMatrix` | 矩阵变换 |
| `SkBlendMode` | 混合模式定义 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkPaint` | 包含颜色过滤器 |
| `SkCanvas` | 通过 Paint 应用过滤器 |
| `SkShader` | 可能包含颜色过滤器 |
| `SkRasterPipeline` | 执行过滤器操作 |
| GPU 后端 | 在 GPU 上实现过滤器效果 |

## 设计模式与设计决策

### 抽象基类模式

`SkColorFilter` 定义接口,`SkColorFilterBase` 提供实现:
- 隐藏实现细节
- 保持公共 API 稳定
- 便于扩展新类型的过滤器

### 工厂模式

`SkColorFilters` 提供静态工厂方法:
- 避免暴露具体实现类
- 便于内部优化和类型选择
- 简化客户端代码

### 不可变对象

颜色过滤器一旦创建就不可变:
- 线程安全,无需锁
- 可以安全缓存和共享
- 简化内存管理

### 组合模式

支持通过 `makeComposed` 组合多个过滤器:
- 提供灵活的颜色变换能力
- 可以构建复杂的效果链
- 实现类似函数组合的语义

## 性能考量

### 类型优化

某些过滤器类型可以优化为简单操作:
- `asAColorMode`: 单次混合操作
- `asAColorMatrix`: 矩阵乘法
- `isAlphaUnchanged`: 跳过 alpha 相关优化

### 色彩空间转换缓存

`filterColor4f` 在需要时进行色彩空间转换,但实际过滤器实现可能缓存转换矩阵。

### GPU 加速

大多数颜色过滤器都有对应的 GPU 实现,通过着色器或固定功能硬件加速。

### 预乘 alpha 处理

表格过滤器在非预乘空间操作,自动处理预乘/去预乘转换,避免精度损失。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkFlattenable.h` | 基类 | 序列化支持 |
| `include/core/SkColorSpace.h` | 依赖 | 色彩空间定义 |
| `include/core/SkColorTable.h` | 依赖 | 表格查找 |
| `src/core/SkColorFilterPriv.h` | 实现 | 私有辅助函数 |
| `src/effects/colorfilters/SkColorFilterBase.h` | 实现 | 基础实现类 |
| `src/core/SkColorSpaceXformSteps.h` | 依赖 | 色彩空间转换 |
| `include/core/SkPaint.h` | 使用者 | 包含颜色过滤器 |
