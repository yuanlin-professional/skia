# SkWorkingFormatColorFilter

> 源文件
> - `src/effects/colorfilters/SkWorkingFormatColorFilter.h`
> - `src/effects/colorfilters/SkWorkingFormatColorFilter.cpp`

## 概述

`SkWorkingFormatColorFilter` 是 Skia 颜色过滤器系统中的一个特殊过滤器，用于在应用子颜色过滤器时临时切换到指定的工作色彩空间和透明度类型。该过滤器充当色彩空间转换的包装器，在处理颜色之前将其从目标色彩空间转换为工作色彩空间，处理完成后再转换回目标色彩空间。这种机制确保子过滤器在正确的色彩空间中工作，对于需要精确色彩管理的场景至关重要。

该模块还包含 `SkWorkingFormatCalculator` 辅助类，用于计算和管理工作色彩空间的参数。这个计算器可以选择性地使用目标色彩空间的传递函数、色域或透明度类型，也可以使用自定义参数。

## 架构位置

```
skia/
├── include/core/
│   ├── SkColorFilter.h          # 公共颜色过滤器接口
│   └── SkColorSpace.h           # 色彩空间定义
├── src/
│   ├── core/
│   │   ├── SkColorFilterPriv.h  # 颜色过滤器私有API
│   │   └── SkColorSpaceXformSteps.h  # 色彩空间转换步骤
│   └── effects/
│       └── colorfilters/
│           ├── SkColorFilterBase.h       # 颜色过滤器基类
│           ├── SkWorkingFormatColorFilter.h    # 本模块头文件
│           └── SkWorkingFormatColorFilter.cpp  # 本模块实现
└── modules/
    └── skcms/
        └── skcms.h              # 色彩管理系统
```

在 Skia 的颜色过滤器架构中，本模块处于装饰器层级，它包装其他颜色过滤器并提供色彩空间转换功能。它依赖于底层的 `SkColorSpaceXformSteps` 进行实际的转换操作。

## 主要类与结构体

### 1. SkWorkingFormatCalculator

工作色彩空间格式计算器类。

```cpp
class SkWorkingFormatCalculator {
public:
    SkWorkingFormatCalculator(const skcms_TransferFunction* tf,
                              const skcms_Matrix3x3* gamut,
                              const SkAlphaType* at);

    sk_sp<SkColorSpace> workingFormat(const sk_sp<SkColorSpace>& dstCS,
                                      SkAlphaType* outAT) const;
    void flatten(SkWriteBuffer& buffer) const;

private:
    skcms_TransferFunction fTF;    // 传递函数
    bool fUseDstTF = true;          // 是否使用目标传递函数
    skcms_Matrix3x3 fGamut;        // 色域矩阵
    bool fUseDstGamut = true;       // 是否使用目标色域
    SkAlphaType fAT;               // 透明度类型
    bool fUseDstAT = true;          // 是否使用目标透明度类型
};
```

**职责**：
- 管理工作色彩空间的配置参数
- 根据目标色彩空间计算实际的工作色彩空间
- 支持选择性地使用目标或自定义参数
- 处理序列化和反序列化

### 2. SkWorkingFormatColorFilter

工作格式颜色过滤器类。

```cpp
class SkWorkingFormatColorFilter final : public SkColorFilterBase {
public:
    SkWorkingFormatColorFilter(sk_sp<SkColorFilter> child,
                               const skcms_TransferFunction* tf,
                               const skcms_Matrix3x3* gamut,
                               const SkAlphaType* at);

    sk_sp<SkColorSpace> workingFormat(const sk_sp<SkColorSpace>& dstCS,
                                      SkAlphaType* outAT) const;

    bool appendStages(const SkStageRec& rec, bool shaderIsOpaque) const override;
    SkPMColor4f onFilterColor4f(const SkPMColor4f& origColor,
                                SkColorSpace* rawDstCS) const override;
    bool onIsAlphaUnchanged() const override;

private:
    sk_sp<SkColorFilter> fChild;                        // 子颜色过滤器
    SkWorkingFormatCalculator fWorkingFormatCalculator; // 格式计算器
};
```

**特性**：
- 装饰器模式包装子颜色过滤器
- 自动处理色彩空间的往返转换
- 支持自定义或继承的色彩空间参数
- 透明传递部分 API 调用（如 `asAColorMode`）

## 公共 API 函数

### SkColorFilterPriv::WithWorkingFormat

```cpp
sk_sp<SkColorFilter> SkColorFilterPriv::WithWorkingFormat(
    sk_sp<SkColorFilter> child,
    const skcms_TransferFunction* tf,
    const skcms_Matrix3x3* gamut,
    const SkAlphaType* at);
```

创建一个工作格式颜色过滤器的工厂函数。

**参数**：
- `child` - 要包装的子颜色过滤器
- `tf` - 可选的自定义传递函数（nullptr 表示使用目标的）
- `gamut` - 可选的自定义色域矩阵（nullptr 表示使用目标的）
- `at` - 可选的自定义透明度类型（nullptr 表示使用预乘 alpha）

**返回值**：包装后的颜色过滤器，如果 `child` 为 nullptr 则返回 nullptr

**特殊处理**：当 `child` 为 nullptr 时，整个过滤器被视为恒等变换并返回 nullptr，因为双向转换会相互抵消。

### workingFormat

```cpp
sk_sp<SkColorSpace> workingFormat(const sk_sp<SkColorSpace>& dstCS,
                                  SkAlphaType* outAT) const;
```

根据目标色彩空间计算实际的工作色彩空间。

**计算逻辑**：
- 如果指定了自定义传递函数，使用自定义值；否则从目标色彩空间提取
- 如果指定了自定义色域，使用自定义值；否则从目标色彩空间提取
- 如果指定了自定义透明度类型，使用自定义值；否则使用 `kPremul_SkAlphaType`

## 内部实现细节

### 色彩空间转换流程

`appendStages` 方法展示了完整的转换流程：

```cpp
bool SkWorkingFormatColorFilter::appendStages(const SkStageRec& rec,
                                               bool shaderIsOpaque) const {
    // 1. 确定目标色彩空间（默认使用 sRGB）
    sk_sp<SkColorSpace> dstCS = sk_ref_sp(rec.fDstCS);
    if (!dstCS) {
        dstCS = SkColorSpace::MakeSRGB();
    }

    // 2. 计算工作色彩空间
    SkAlphaType workingAT;
    sk_sp<SkColorSpace> workingCS = this->workingFormat(dstCS, &workingAT);

    // 3. 创建转换步骤
    SkColorInfo dst = {rec.fDstColorType, kPremul_SkAlphaType, dstCS};
    SkColorInfo working = {rec.fDstColorType, workingAT, workingCS};
    const auto* dstToWorking = rec.fAlloc->make<SkColorSpaceXformSteps>(dst, working);
    const auto* workingToDst = rec.fAlloc->make<SkColorSpaceXformSteps>(working, dst);

    // 4. 应用转换管线：目标 -> 工作 -> 子过滤器 -> 工作 -> 目标
    dstToWorking->apply(rec.fPipeline);
    if (!as_CFB(fChild)->appendStages(workingRec, shaderIsOpaque)) {
        return false;
    }
    workingToDst->apply(rec.fPipeline);
    return true;
}
```

**关键设计点**：
- 使用 `SkColorSpaceXformSteps` 实现高效的色彩空间转换
- 在栈分配器中创建转换步骤对象以提高性能
- 保证了色彩空间的往返一致性

### 单色过滤实现

对于单个颜色的过滤，`onFilterColor4f` 实现了类似的转换逻辑：

```cpp
SkPMColor4f SkWorkingFormatColorFilter::onFilterColor4f(
    const SkPMColor4f& origColor,
    SkColorSpace* rawDstCS) const {
    // 设置目标色彩空间
    sk_sp<SkColorSpace> dstCS = sk_ref_sp(rawDstCS);
    if (!dstCS) {
        dstCS = SkColorSpace::MakeSRGB();
    }

    // 计算工作色彩空间
    SkAlphaType workingAT;
    sk_sp<SkColorSpace> workingCS = this->workingFormat(dstCS, &workingAT);

    // 执行双向转换
    SkPMColor4f color = origColor;
    SkColorSpaceXformSteps{dst, working}.apply(color.vec());
    color = as_CFB(fChild)->onFilterColor4f(color, working.colorSpace());
    SkColorSpaceXformSteps{working, dst}.apply(color.vec());
    return color;
}
```

### 序列化机制

```cpp
void SkWorkingFormatColorFilter::flatten(SkWriteBuffer& buffer) const {
    buffer.writeFlattenable(fChild.get());
    fWorkingFormatCalculator.flatten(buffer);
}

void SkWorkingFormatCalculator::flatten(SkWriteBuffer& buffer) const {
    // 写入标志位
    buffer.writeBool(fUseDstTF);
    buffer.writeBool(fUseDstGamut);
    buffer.writeBool(fUseDstAT);

    // 仅在使用自定义值时写入数据
    if (!fUseDstTF) {
        buffer.writeScalarArray({&fTF.g, sizeof(skcms_TransferFunction) / sizeof(SkScalar)});
    }
    if (!fUseDstGamut) {
        buffer.writeScalarArray({&fGamut.vals[0][0], sizeof(skcms_Matrix3x3) / sizeof(SkScalar)});
    }
    if (!fUseDstAT) {
        buffer.writeInt(fAT);
    }
}
```

**优化**：通过标志位避免序列化不必要的数据，减少文件大小。

## 依赖关系

### 内部依赖

| 组件 | 用途 |
|-----|------|
| `SkColorFilterBase` | 颜色过滤器基类 |
| `SkColorSpaceXformSteps` | 执行色彩空间转换 |
| `SkColorFilterPriv` | 提供工厂函数 |
| `SkEffectPriv` | 效果相关工具 |
| `SkArenaAlloc` | 栈分配器，用于管线对象 |

### 外部依赖

| 组件 | 用途 |
|-----|------|
| `skcms` | 色彩管理系统，定义传递函数和色域 |
| `SkColorSpace` | 色彩空间抽象 |
| `SkReadBuffer` / `SkWriteBuffer` | 序列化支持 |

## 设计模式与设计决策

### 1. 装饰器模式（Decorator Pattern）

`SkWorkingFormatColorFilter` 是典型的装饰器模式实现：
- 包装子颜色过滤器，添加色彩空间转换功能
- 透明传递大部分 API 调用给子对象
- 在关键路径上注入转换逻辑

### 2. 策略模式（Strategy Pattern）

通过 `SkWorkingFormatCalculator` 封装工作色彩空间的计算策略：
- 支持使用目标色彩空间参数
- 支持使用自定义参数
- 可灵活组合不同的策略

### 3. 空对象优化（Null Object Optimization）

在 `WithWorkingFormat` 工厂函数中：
```cpp
if (!child) {
    // 转换到工作格式再转回来等价于恒等变换
    return nullptr;
}
```

这避免了创建无用的包装器对象。

### 4. Android 兼容性设计

注释中提到：
```cpp
// 我们实现这些方法以便调用者能获取信息，即使过滤器被包装后也能获取
// 这对 Android 很重要，因为 Android 的所有颜色过滤器都在 sRGB 中工作
bool onAsAColorMode(SkColor*, SkBlendMode*) const override;
bool onAsAColorMatrix(float[20]) const override;
```

这些方法透明传递给子过滤器，确保 Android 平台能够正确查询颜色过滤器的属性。

## 性能考量

### 1. 内联转换步骤

使用 `SkArenaAlloc` 在栈上分配转换步骤对象：
```cpp
const auto* dstToWorking = rec.fAlloc->make<SkColorSpaceXformSteps>(dst, working);
const auto* workingToDst = rec.fAlloc->make<SkColorSpaceXformSteps>(working, dst);
```

**优势**：
- 避免堆分配开销
- 提高缓存局部性
- 对象生命周期与管线绑定，自动管理

### 2. 延迟计算

工作色彩空间在实际使用时才计算：
```cpp
sk_sp<SkColorSpace> workingCS = this->workingFormat(dstCS, &workingAT);
```

如果目标色彩空间不变，可能会多次计算相同结果。但由于色彩空间对象是引用计数的，实际的色彩空间数据可以被共享。

### 3. 向量化优化

`SkColorSpaceXformSteps` 支持向量化操作：
```cpp
SkColorSpaceXformSteps{dst, working}.apply(color.vec());
```

通过直接操作颜色向量，可以利用 SIMD 指令加速转换。

### 4. 序列化优化

通过标志位避免序列化默认参数：
- 如果使用目标传递函数，不序列化 `fTF`
- 如果使用目标色域，不序列化 `fGamut`
- 如果使用目标透明度类型，不序列化 `fAT`

这显著减少了序列化数据的大小。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/effects/colorfilters/SkColorFilterBase.h` | 颜色过滤器基类定义 |
| `src/core/SkColorSpaceXformSteps.h` | 色彩空间转换步骤实现 |
| `src/core/SkColorFilterPriv.h` | 颜色过滤器私有 API |
| `modules/skcms/skcms.h` | 色彩管理系统接口 |
| `include/core/SkColorSpace.h` | 色彩空间公共接口 |
| `src/effects/colorfilters/SkMatrixColorFilter.cpp` | 矩阵颜色过滤器（可能的子过滤器） |
| `src/effects/colorfilters/SkRuntimeColorFilter.cpp` | 运行时颜色过滤器（可能的子过滤器） |
| `src/core/SkReadBuffer.h` | 反序列化支持 |
| `src/core/SkWriteBuffer.h` | 序列化支持 |
| `src/base/SkArenaAlloc.h` | 栈分配器 |
