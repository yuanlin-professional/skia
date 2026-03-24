# SkColorSpaceXformColorFilter - 色彩空间变换颜色滤镜

> 源文件:
> - `src/effects/colorfilters/SkColorSpaceXformColorFilter.h`
> - `src/effects/colorfilters/SkColorSpaceXformColorFilter.cpp`

## 概述

`SkColorSpaceXformColorFilter` 实现了在两个颜色空间之间进行颜色变换的颜色滤镜。它通过 `SkColorSpaceXformSteps` 执行实际的颜色空间转换，支持从任意源颜色空间到目标颜色空间的映射。

该类还提供了两个常用的单例实例：线性到 sRGB gamma 转换和 sRGB 到线性 gamma 转换。

## 架构位置

```
SkColorFilters::LinearToSRGBGamma()    // 公共工厂 (单例)
SkColorFilters::SRGBToLinearGamma()    // 公共工厂 (单例)
SkColorFilterPriv::MakeColorSpaceXform() // 内部工厂
  |
  v
SkColorSpaceXformColorFilter          // 本类
  |
  v
SkColorFilterBase -> SkColorFilter    // 继承链
```

## 主要类与结构体

### `SkColorSpaceXformColorFilter`

继承自 `SkColorFilterBase`，为 `final` 类。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fSrc` | `sk_sp<SkColorSpace>` | 源颜色空间 |
| `fDst` | `sk_sp<SkColorSpace>` | 目标颜色空间 |
| `fSteps` | `SkColorSpaceXformSteps` | 预计算的变换步骤 |

构造函数中 `fSteps` 以 `kUnpremul_SkAlphaType` -> `kUnpremul_SkAlphaType` 初始化，premul/unpremul 处理由 `appendStages()` 单独控制。

## 公共 API 函数

### `SkColorFilters::LinearToSRGBGamma()`

返回将线性 RGB 转换为 sRGB gamma 的颜色滤镜。使用 `SkNoDestructor` 实现的全局单例。

### `SkColorFilters::SRGBToLinearGamma()`

返回将 sRGB gamma 转换为线性 RGB 的颜色滤镜。同样使用全局单例。

### `SkColorFilterPriv::MakeColorSpaceXform()`

```cpp
static sk_sp<SkColorFilter> MakeColorSpaceXform(sk_sp<SkColorSpace> src,
                                                  sk_sp<SkColorSpace> dst);
```

内部工厂方法，创建任意源到目标的颜色空间变换滤镜。

## 内部实现细节

### `appendStages()` 实现

```cpp
bool appendStages(const SkStageRec& rec, bool shaderIsOpaque) const;
```

1. 若输入非不透明，先追加 `unpremul` 操作
2. 通过 `fSteps.apply(pipeline)` 追加颜色空间变换步骤
3. 若输入非不透明，追加 `premul` 操作

这种 unpremul -> xform -> premul 的模式确保颜色空间变换在非预乘空间中进行。

### 序列化/反序列化

- `flatten()`：将源和目标 `SkColorSpace` 各自序列化为字节数组
- `CreateProc()`：读取两个颜色空间的字节数组并反序列化重建
- `LegacyGammaOnlyCreateProc()`：处理旧版 `SkSRGBGammaColorFilter` 格式（仅包含方向标志）

### 兼容性注册

```cpp
void SkRegisterSkColorSpaceXformColorFilterFlattenable();
```

注册三个名称：
1. `SkColorSpaceXformColorFilter`（当前名称）
2. `ColorSpaceXformColorFilter`（旧名称）
3. `SkSRGBGammaColorFilter`（更旧的名称，使用旧版反序列化）

## 依赖关系

- `SkColorFilterBase`：基类
- `SkColorSpaceXformSteps`：核心变换逻辑
- `SkColorSpace`：颜色空间表示
- `SkNoDestructor`：用于实现全局单例
- `SkRasterPipeline`：光栅管线

## 设计模式与设计决策

1. **单例模式**：线性/sRGB gamma 转换使用 `SkNoDestructor` 全局单例，避免重复创建
2. **分离关注点**：premul/unpremul 与颜色空间变换分离处理
3. **多版本兼容**：支持三种不同的序列化名称以兼容不同时期的 SKP 格式
4. **预计算变换步骤**：在构造时即计算 `SkColorSpaceXformSteps`，避免运行时重复计算

## 性能考量

1. **单例复用**：常用的 linear-to-sRGB 和 sRGB-to-linear 转换使用全局单例
2. **步骤预计算**：`SkColorSpaceXformSteps` 在构造时预计算转换矩阵和传递函数
3. **条件跳过 premul**：当 `shaderIsOpaque=true` 时跳过 unpremul/premul 操作

### 管线阶段详细说明

`SkColorSpaceXformSteps::apply(pipeline)` 可能追加以下管线阶段：

1. **linearize**：将非线性传递函数转换为线性值（如 sRGB -> linear）
2. **gamut_transform**：应用 3x3 色域矩阵将颜色从源色域映射到目标色域
3. **encode**：将线性值转换为目标传递函数（如 linear -> sRGB）

若源和目标在某一步骤上相同，该步骤会被跳过。例如，sRGB -> sRGB linear 只需 linearize 步骤。

### 序列化格式

```
[src SkColorSpace 字节数组长度: 4 bytes]
[src SkColorSpace 数据: 变长]
[dst SkColorSpace 字节数组长度: 4 bytes]
[dst SkColorSpace 数据: 变长]
```

### 旧版格式兼容

`LegacyGammaOnlyCreateProc` 处理旧版 `SkSRGBGammaColorFilter` 格式：
- 读取 uint32 方向值（0 = linear->sRGB, 1 = sRGB->linear）
- 映射到对应的单例实例

### 全局单例实例

```cpp
// LinearToSRGBGamma 单例
static SkNoDestructor<SkColorSpaceXformColorFilter> gSingleton(
    SkColorSpace::MakeSRGBLinear(),  // 源：线性
    SkColorSpace::MakeSRGB());       // 目标：sRGB

// SRGBToLinearGamma 单例
static SkNoDestructor<SkColorSpaceXformColorFilter> gSingleton(
    SkColorSpace::MakeSRGB(),         // 源：sRGB
    SkColorSpace::MakeSRGBLinear()); // 目标：线性
```

使用 `SkNoDestructor` 确保单例永不销毁，避免静态析构顺序问题。

## 相关文件

- `include/core/SkColorFilter.h` - 公共 API
- `src/effects/colorfilters/SkColorFilterBase.h` - 基类
- `src/core/SkColorSpaceXformSteps.h` - 颜色空间变换步骤
- `src/core/SkColorFilterPriv.h` - 内部工厂方法声明
- `src/base/SkNoDestructor.h` - 全局单例工具
- `include/core/SkColorSpace.h` - 颜色空间定义
