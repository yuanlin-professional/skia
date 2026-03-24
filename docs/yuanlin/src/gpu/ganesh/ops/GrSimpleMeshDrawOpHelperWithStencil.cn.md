# GrSimpleMeshDrawOpHelperWithStencil

> 源文件
> - `src/gpu/ganesh/ops/GrSimpleMeshDrawOpHelperWithStencil.h`
> - `src/gpu/ganesh/ops/GrSimpleMeshDrawOpHelperWithStencil.cpp`

## 概述

`GrSimpleMeshDrawOpHelperWithStencil` 是 `GrSimpleMeshDrawOpHelper` 的扩展版本，添加了对模板设置（Stencil Settings）的支持。该类通过私有继承方式扩展基类，提供了在绘制操作中使用模板测试和模板缓冲区操作的能力。

模板缓冲区是 GPU 渲染中用于实现复杂效果的重要机制，如路径裁剪、阴影体积和非零缠绕规则填充等。该辅助类使得在标准网格绘制操作中集成模板功能变得简单。

## 架构位置

在 Skia 的 Ganesh 架构中，该类位于以下层次：

```
skia/
  src/
    gpu/
      ganesh/
        ops/
          GrSimpleMeshDrawOpHelper (基类)
            └── GrSimpleMeshDrawOpHelperWithStencil (私有继承)
```

它为需要模板功能的网格绘制操作提供了便捷的实现基础。

## 主要类与结构体

### GrSimpleMeshDrawOpHelperWithStencil

带模板支持的网格绘制辅助类。

**继承关系：** 私有继承自 `GrSimpleMeshDrawOpHelper`

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fStencilSettings` | `const GrUserStencilSettings*` | 模板设置指针 |

**从基类暴露的接口：**
```cpp
using GrSimpleMeshDrawOpHelper::visitProxies;
using GrSimpleMeshDrawOpHelper::createPipeline;
using GrSimpleMeshDrawOpHelper::aaType;
using GrSimpleMeshDrawOpHelper::setAAType;
using GrSimpleMeshDrawOpHelper::isTrivial;
using GrSimpleMeshDrawOpHelper::usesLocalCoords;
using GrSimpleMeshDrawOpHelper::compatibleWithCoverageAsAlpha;
using GrSimpleMeshDrawOpHelper::detachProcessorSet;
using GrSimpleMeshDrawOpHelper::pipelineFlags;
```

## 公共 API 函数

### 工厂方法

```cpp
template <typename Op, typename... OpArgs>
static GrOp::Owner FactoryHelper(
    GrRecordingContext* context,
    GrPaint&& paint,
    OpArgs... opArgs
)
```
创建操作的工厂辅助函数，透传到基类实现。

### 构造函数

```cpp
GrSimpleMeshDrawOpHelperWithStencil(
    GrProcessorSet* processorSet,
    GrAAType aaType,
    const GrUserStencilSettings* stencilSettings,
    InputFlags inputFlags = InputFlags::kNone
)
```
构造带模板支持的辅助器。

**参数说明：**
- `processorSet`：处理器集指针
- `aaType`：抗锯齿类型
- `stencilSettings`：模板设置（如果为 `nullptr`，使用 `kUnused`）
- `inputFlags`：输入标志

### 固定功能标志

```cpp
GrDrawOp::FixedFunctionFlags fixedFunctionFlags() const
```
返回固定功能标志，如果使用模板则包含 `kUsesStencil` 标志。

### 处理器最终化

```cpp
GrProcessorSet::Analysis finalizeProcessors(
    const GrCaps& caps,
    const GrAppliedClip* clip,
    GrClampType clampType,
    GrProcessorAnalysisCoverage geometryCoverage,
    GrProcessorAnalysisColor* geometryColor
)
```
最终化处理器，传递模板设置到基类。

```cpp
GrProcessorSet::Analysis finalizeProcessors(
    const GrCaps& caps,
    const GrAppliedClip* clip,
    GrClampType clampType,
    GrProcessorAnalysisCoverage geometryCoverage,
    SkPMColor4f* geometryColor,
    bool* wideColor
)
```
另一个重载版本，支持常量颜色输出。

### 兼容性检查

```cpp
bool isCompatible(
    const GrSimpleMeshDrawOpHelperWithStencil& that,
    const GrCaps& caps,
    const SkRect& thisBounds,
    const SkRect& thatBounds,
    bool ignoreAAType = false
) const
```
检查两个辅助器是否兼容，除了基类检查外还要求模板设置相同。

### 程序信息创建

```cpp
GrProgramInfo* createProgramInfoWithStencil(
    const GrCaps* caps,
    SkArenaAlloc* arena,
    const GrSurfaceProxyView& writeView,
    bool usesMSAASurface,
    GrAppliedClip&& appliedClip,
    const GrDstProxyView& dstProxyView,
    GrGeometryProcessor* gp,
    GrPrimitiveType primType,
    GrXferBarrierFlags renderPassXferBarriers,
    GrLoadOp colorLoadOp
)
```
创建包含模板设置的程序信息。

### 访问器

```cpp
const GrUserStencilSettings* stencilSettings() const
```
获取模板设置指针。

## 内部实现细节

### 私有继承设计

该类使用私有继承而非公有继承的原因：
1. **防止向上转型**：不应该将该类当作基类使用
2. **选择性暴露接口**：通过 `using` 声明控制哪些基类方法可见
3. **方法覆盖**：可以非虚地覆盖基类方法

```cpp
class GrSimpleMeshDrawOpHelperWithStencil : private GrSimpleMeshDrawOpHelper {
    // 私有继承，外部不能转换为基类指针
}
```

### 模板设置存储

```cpp
GrSimpleMeshDrawOpHelperWithStencil::GrSimpleMeshDrawOpHelperWithStencil(
    GrProcessorSet* processorSet,
    GrAAType aaType,
    const GrUserStencilSettings* stencilSettings,
    InputFlags inputFlags
)
    : INHERITED(processorSet, aaType, inputFlags)
    , fStencilSettings(stencilSettings ? stencilSettings
                                        : &GrUserStencilSettings::kUnused) {}
```

**安全默认值：**
- 如果传入 `nullptr`，自动使用 `kUnused`
- 避免了空指针检查的需要

### 固定功能标志增强

```cpp
GrDrawOp::FixedFunctionFlags
GrSimpleMeshDrawOpHelperWithStencil::fixedFunctionFlags() const {
    GrDrawOp::FixedFunctionFlags flags = INHERITED::fixedFunctionFlags();
    if (fStencilSettings != &GrUserStencilSettings::kUnused) {
        flags |= GrDrawOp::FixedFunctionFlags::kUsesStencil;
    }
    return flags;
}
```

只有在实际使用模板时才设置 `kUsesStencil` 标志。

### 兼容性检查增强

```cpp
bool GrSimpleMeshDrawOpHelperWithStencil::isCompatible(
    const GrSimpleMeshDrawOpHelperWithStencil& that,
    const GrCaps& caps,
    const SkRect& thisBounds,
    const SkRect& thatBounds,
    bool ignoreAAType
) const {
    return INHERITED::isCompatible(that, caps, thisBounds, thatBounds, ignoreAAType) &&
           fStencilSettings == that.fStencilSettings;
}
```

**指针比较：**
- 使用指针相等性检查模板设置
- 这是安全的，因为模板设置通常是静态常量
- 如果不同的操作使用相同的设置，指针相同

### 处理器最终化传递

```cpp
GrProcessorSet::Analysis
GrSimpleMeshDrawOpHelperWithStencil::finalizeProcessors(
    const GrCaps& caps,
    const GrAppliedClip* clip,
    GrClampType clampType,
    GrProcessorAnalysisCoverage geometryCoverage,
    SkPMColor4f* geometryColor,
    bool* wideColor
) {
    GrProcessorAnalysisColor color = *geometryColor;
    auto result = this->finalizeProcessors(caps, clip, clampType,
                                          geometryCoverage, &color);
    color.isConstant(geometryColor);
    if (wideColor) {
        *wideColor = !geometryColor->fitsInBytes();
    }
    return result;
}
```

将颜色转换在公共接口和内部实现之间进行协调。

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrSimpleMeshDrawOpHelper` | 基类，提供核心功能 |
| `GrUserStencilSettings` | 模板设置 |
| `GrProcessorSet` | 处理器集合 |
| `GrProgramInfo` | 程序信息 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `RegionOp` | 区域操作，使用模板 |
| 其他需要模板的绘制操作 | 各种路径和形状操作 |

## 设计模式与设计决策

### 装饰器模式

该类通过添加模板功能来装饰基类功能：
- 保持基类接口
- 添加模板特定的行为
- 最小化对基类的修改

### 静态多态

使用私有继承和方法覆盖实现静态多态：
- 无虚函数开销
- 编译时解析方法调用
- 类型安全

### 模板方法透传

```cpp
template <typename Op, typename... OpArgs>
static GrOp::Owner FactoryHelper(...) {
    return GrSimpleMeshDrawOpHelper::FactoryHelper<Op, OpArgs...>(...);
}
```

由于模板不能通过 `using` 声明暴露，使用包装函数透传。

### 安全默认值模式

```cpp
fStencilSettings(stencilSettings ? stencilSettings
                                  : &GrUserStencilSettings::kUnused)
```

提供合理的默认值，减少客户端代码的负担。

## 性能考量

### 零开销抽象

1. **无虚函数**：所有方法调用都是直接调用
2. **内联友好**：小方法可以被内联
3. **单指针开销**：只增加一个指针成员

### 快速兼容性检查

```cpp
fStencilSettings == that.fStencilSettings
```
指针比较是最快的相等性检查。

### 条件标志设置

```cpp
if (fStencilSettings != &GrUserStencilSettings::kUnused) {
    flags |= GrDrawOp::FixedFunctionFlags::kUsesStencil;
}
```
只有在实际使用模板时才设置标志，避免不必要的GPU状态变化。

### 静态常量共享

模板设置通常定义为静态常量：
```cpp
static constexpr GrUserStencilSettings gMyStencil(...);
```
多个操作可以共享同一个设置实例。

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `GrSimpleMeshDrawOpHelper.h/cpp` | 基类 | 核心辅助功能 |
| `GrUserStencilSettings.h` | 依赖 | 模板设置定义 |
| `RegionOp.cpp` | 使用者 | 区域操作实现 |
| `GrPathStencilSettings.h` | 相关 | 路径模板设置 |
| `GrProgramInfo.h` | 依赖 | 程序信息 |
