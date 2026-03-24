# GrColorSpaceXform

> 源文件
> - src/gpu/ganesh/GrColorSpaceXform.h
> - src/gpu/ganesh/GrColorSpaceXform.cpp

## 概述

`GrColorSpaceXform` 是 Ganesh GPU 后端中负责颜色空间转换的核心类。它封装了从一个颜色空间到另一个颜色空间的转换步骤，并提供了在 GPU 上执行这些转换的基础设施。该类基于 `SkColorSpaceXformSteps`，后者定义了转换所需的具体步骤（线性化、色域转换、编码等）。

`GrColorSpaceXformEffect` 是一个配套的片段处理器（Fragment Processor），它将颜色空间转换应用到渲染管线中。它可以包装另一个片段处理器，对其输出进行颜色空间转换，从而实现灵活的颜色管理流程。

这两个类共同构成了 Skia GPU 渲染中颜色管理的基础，确保颜色在不同颜色空间之间正确转换，对于支持宽色域和 HDR 渲染至关重要。

## 架构位置

在 Skia 的 Ganesh GPU 渲染架构中，`GrColorSpaceXform` 位于颜色管理层：

```
GrRecordingContext
    └── GrFragmentProcessor (片段处理器)
        ├── GrColorSpaceXformEffect (颜色空间转换效果)
        │   └── GrColorSpaceXform (转换逻辑封装)
        │       └── SkColorSpaceXformSteps (转换步骤)
        └── 其他片段处理器
```

该类被用于纹理采样、图像绘制、效果处理等需要颜色空间转换的场景。

## 主要类与结构体

### GrColorSpaceXform

该类封装了颜色空间转换的数学运算。

**继承关系：**
```
SkRefCnt (引用计数基类)
    └── GrColorSpaceXform
```

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSteps` | `SkColorSpaceXformSteps` | 转换步骤，包含转换矩阵和传输函数 |

### GrColorSpaceXformEffect

该类是将颜色空间转换集成到渲染管线的片段处理器。

**继承关系：**
```
GrFragmentProcessor (片段处理器基类)
    └── GrColorSpaceXformEffect
```

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fColorXform` | `sk_sp<GrColorSpaceXform>` | 要应用的颜色空间转换 |

## 公共 API 函数

### GrColorSpaceXform 核心方法

#### 工厂方法

```cpp
static sk_sp<GrColorSpaceXform> Make(SkColorSpace* src, SkAlphaType srcAT,
                                     SkColorSpace* dst, SkAlphaType dstAT);
static sk_sp<GrColorSpaceXform> Make(const GrColorInfo& srcInfo,
                                     const GrColorInfo& dstInfo);
```

**功能：** 创建颜色空间转换对象。

如果转换是空操作（noop），返回 `nullptr`。这基于 `SkColorSpaceXformSteps` 的标志掩码，如果为 0 表示不需要任何转换。

**参数说明：**
- `src/dst`: 源和目标颜色空间
- `srcAT/dstAT`: 源和目标的透明度类型
- `srcInfo/dstInfo`: 完整的颜色信息对象

#### 转换访问

```cpp
const SkColorSpaceXformSteps& steps() const;
```

**功能：** 获取转换步骤的只读引用，用于在 GPU 代码生成时使用。

#### 键生成

```cpp
static uint32_t XformKey(const GrColorSpaceXform* xform);
```

**功能：** 生成用于着色器缓存键的 32 位哈希值。

键的生成基于：
- 转换步骤的标志掩码（低 8 位）
- 源传输函数类型（位 8-15，如果需要线性化）
- 目标传输函数类型（位 16-23，如果需要编码）

这确保了不同的转换配置生成不同的着色器程序。

#### 相等性比较

```cpp
static bool Equals(const GrColorSpaceXform* a, const GrColorSpaceXform* b);
```

**功能：** 比较两个转换是否相等。

比较包括：
- 转换步骤标志相同
- 如果有线性化，源传输函数相同
- 如果有色域转换，转换矩阵相同
- 如果有编码，目标传输函数相同

使用 `memcmp` 进行深度比较，确保浮点数值完全匹配。

#### CPU 端转换

```cpp
SkColor4f apply(const SkColor4f& srcColor);
```

**功能：** 在 CPU 上应用颜色空间转换（主要用于测试和常量折叠优化）。

### GrColorSpaceXformEffect 核心方法

#### 工厂方法

```cpp
static std::unique_ptr<GrFragmentProcessor> Make(
    std::unique_ptr<GrFragmentProcessor> child,
    SkColorSpace* src, SkAlphaType srcAT,
    SkColorSpace* dst, SkAlphaType dstAT);

static std::unique_ptr<GrFragmentProcessor> Make(
    std::unique_ptr<GrFragmentProcessor> child,
    const GrColorInfo& srcInfo,
    const GrColorInfo& dstInfo);

static std::unique_ptr<GrFragmentProcessor> Make(
    std::unique_ptr<GrFragmentProcessor> child,
    sk_sp<GrColorSpaceXform> colorXform);
```

**功能：** 创建颜色空间转换效果处理器。

如果 `child` 为 null，效果会应用到输入颜色（`fInputColor`）。如果 `colorXform` 为 null，直接返回 `child`（空操作优化）。

#### 转换访问

```cpp
const GrColorSpaceXform* colorXform() const;
```

**功能：** 获取关联的颜色空间转换对象。

#### 标准片段处理器方法

```cpp
const char* name() const override;
std::unique_ptr<GrFragmentProcessor> clone() const override;
```

**功能：** 实现片段处理器接口的标准方法。

## 内部实现细节

### 转换步骤封装

`GrColorSpaceXform` 主要是 `SkColorSpaceXformSteps` 的薄包装，提供 GPU 特定的接口：

```cpp
GrColorSpaceXform(const SkColorSpaceXformSteps& steps) : fSteps(steps) {}
```

实际的转换逻辑在 `SkColorSpaceXformSteps` 中实现，包括：
- `fFlags`: 标志位，指示需要哪些转换步骤
- `fSrcTF`: 源传输函数（用于线性化）
- `fSrcToDstMatrix`: 3x3 色域转换矩阵
- `fDstTFInv`: 目标传输函数的逆（用于编码）

### 着色器代码生成

`GrColorSpaceXformEffect::onMakeProgramImpl()` 返回一个实现类，其 `emitCode()` 方法生成 GLSL 代码：

```cpp
void emitCode(EmitArgs& args) override {
    const GrColorSpaceXformEffect& proc = args.fFp.cast<GrColorSpaceXformEffect>();
    GrGLSLFPFragmentBuilder* fragBuilder = args.fFragBuilder;
    GrGLSLUniformHandler* uniformHandler = args.fUniformHandler;

    fColorSpaceHelper.emitCode(uniformHandler, proc.colorXform());
    SkString childColor = this->invokeChild(0, args);
    SkString xformedColor;
    fragBuilder->appendColorGamutXform(&xformedColor, childColor.c_str(), &fColorSpaceHelper);
    fragBuilder->codeAppendf("return %s;", xformedColor.c_str());
}
```

该代码：
1. 通过 `GrGLSLColorSpaceXformHelper` 生成转换所需的 uniform 声明
2. 调用子处理器获取输入颜色
3. 使用 `appendColorGamutXform()` 生成转换代码
4. 返回转换后的颜色

### 优化标志

`OptFlags()` 方法确定效果的优化标志：

```cpp
static OptimizationFlags OptFlags(const GrFragmentProcessor* child) {
    return ProcessorOptimizationFlags(child) & (kCompatibleWithCoverageAsAlpha_OptimizationFlag |
                                                kPreservesOpaqueInput_OptimizationFlag |
                                                kConstantOutputForConstantInput_OptimizationFlag);
}
```

这些标志告诉渲染系统：
- `kCompatibleWithCoverageAsAlpha`: 转换不影响透明度处理
- `kPreservesOpaqueInput`: 不透明输入产生不透明输出
- `kConstantOutputForConstantInput`: 常量输入产生常量输出（支持常量折叠）

### 常量折叠

`constantOutputForConstantInput()` 支持编译时优化：

```cpp
SkPMColor4f constantOutputForConstantInput(const SkPMColor4f& input) const override {
    const auto c0 = ConstantOutputForConstantInput(this->childProcessor(0), input);
    return this->fColorXform->apply(c0.unpremul()).premul();
}
```

如果输入颜色是编译时常量，该方法在 CPU 上计算结果，避免生成 GPU 代码。

### Uniform 数据更新

`onSetData()` 方法在每帧渲染时更新 uniform 数据：

```cpp
void onSetData(const GrGLSLProgramDataManager& pdman,
               const GrFragmentProcessor& fp) override {
    const GrColorSpaceXformEffect& proc = fp.cast<GrColorSpaceXformEffect>();
    fColorSpaceHelper.setData(pdman, proc.colorXform());
}
```

这确保转换矩阵和传输函数参数正确传递到着色器。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkColorSpaceXformSteps` | 核心转换逻辑和步骤定义 |
| `GrFragmentProcessor` | 片段处理器基类 |
| `GrColorInfo` | 颜色信息封装 |
| `SkColorSpace` | Skia 颜色空间表示 |
| `GrGLSLColorSpaceXformHelper` | GLSL 代码生成辅助类 |
| `GrGLSLFragmentShaderBuilder` | GLSL 片段着色器构建器 |
| `GrGLSLUniformHandler` | GLSL uniform 管理 |
| `skgpu::KeyBuilder` | 着色器键构建器 |
| `skcms` | 颜色管理库，提供传输函数类型识别 |

### 被依赖的模块

`GrColorSpaceXform` 被广泛使用于：

| 模块 | 使用方式 |
|------|---------|
| `GrColorInfo` | 缓存从 sRGB 的转换 |
| `GrTextureEffect` | 纹理采样时的颜色空间转换 |
| `GrImageContext` | 图像绘制时的颜色管理 |
| `GrYUVtoRGBEffect` | YUV 到 RGB 转换后的颜色空间调整 |
| `GrPorterDuffXferProcessor` | 混合前的颜色空间对齐 |

## 设计模式与设计决策

### 空对象模式

该类使用 null 指针表示无需转换（空操作）：
```cpp
return steps.fFlags.mask() == 0 ? nullptr : sk_make_sp<GrColorSpaceXform>(steps);
```

这避免了创建不必要的对象，并允许调用者使用简单的 null 检查。

### 装饰器模式

`GrColorSpaceXformEffect` 使用装饰器模式包装其他片段处理器：
```cpp
this->registerChild(std::move(child));
```

这允许在现有效果之上添加颜色空间转换，而无需修改原始效果。

### 不可变性

`GrColorSpaceXform` 对象创建后不可修改，所有方法都是 `const` 的。这确保了线程安全和缓存友好性。

### 延迟实例化

片段处理器通过 `onMakeProgramImpl()` 延迟创建实际的 GLSL 代码生成器。这允许根据运行时信息（如 GPU 能力）定制代码生成。

### 键驱动缓存

通过 `XformKey()` 生成唯一键，该类支持着色器程序缓存。相同的转换配置重用相同的编译后着色器，显著减少编译时间。

## 性能考量

### 着色器缓存

通过生成唯一的转换键，该类支持高效的着色器缓存。这对性能至关重要，因为着色器编译是昂贵的操作。

### GPU 端转换

颜色空间转换在 GPU 上并行执行，比 CPU 转换快得多，特别是对于大量像素。

### 常量折叠

对于常量输入，转换在编译时完成，避免运行时计算。这对于纯色填充等场景特别有效。

### 空操作检测

`Make()` 方法检测空操作转换并返回 null，避免不必要的处理器创建和 GPU 计算。

### Uniform 开销

每个转换可能需要多个 uniform（矩阵 + 传输函数参数），但这比在 CPU 上转换每个像素更高效。

### 子处理器调用

`invokeChild()` 允许内联子处理器的代码，避免函数调用开销。

### 优化标志传播

通过正确设置优化标志，该类允许渲染系统进行进一步优化，如跳过不必要的混合操作。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkColorSpaceXformSteps.h` | 依赖 | 核心转换步骤定义 |
| `src/gpu/ganesh/GrFragmentProcessor.h` | 基类 | 片段处理器基类 |
| `src/gpu/ganesh/GrColorInfo.h` | 依赖 | 颜色信息封装 |
| `src/gpu/ganesh/glsl/GrGLSLColorSpaceXformHelper.h` | 依赖 | GLSL 辅助类 |
| `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h` | 依赖 | 着色器构建器 |
| `src/gpu/KeyBuilder.h` | 依赖 | 键构建工具 |
| `modules/skcms/skcms.h` | 依赖 | 颜色管理系统 |
| `src/gpu/ganesh/effects/GrTextureEffect.h` | 使用者 | 纹理效果使用转换 |
| `include/core/SkColorSpace.h` | 依赖 | Skia 颜色空间 |
