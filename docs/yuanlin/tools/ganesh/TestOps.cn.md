# TestOps

> 源文件：tools/ganesh/TestOps.h, tools/ganesh/TestOps.cpp

## 概述

TestOps 是 Skia Ganesh 测试工具集中的一个核心组件，专门用于在测试环境中创建和执行简单的矩形绘制操作。该模块提供了一组工厂函数，用于构建测试用的 GPU 绘制操作（GrOp），主要用于验证 GPU 管线、效果处理器（Fragment Processor）和本地坐标变换的正确性。

TestOps 实现了一个完整的设备空间矩形绘制操作，包括本地坐标和本地矩阵支持。这对于测试图形效果至关重要，因为标准的矩形绘制代码通常会将本地矩阵应用到预变换的顶点属性上，而 TestOps 则保留了本地矩阵在几何处理器（GeometryProcessor）中的应用，从而能够测试更复杂的场景。

该模块的设计目标是提供简单、可预测且易于控制的测试操作，使开发人员能够在隔离的环境中验证 GPU 渲染管线的各个组件。

## 架构位置

TestOps 位于 Skia 项目的测试工具层级中，具体路径为 `tools/ganesh/`。它与以下组件密切相关：

- **上层调用者**：各种 Ganesh GPU 测试用例，包括效果处理器测试、管线测试等
- **同级组件**：ProxyUtils、TestContext、MemoryCache 等其他测试工具
- **下层依赖**：
  - `src/gpu/ganesh/ops/GrMeshDrawOp.h` - 网格绘制操作基类
  - `src/gpu/ganesh/GrGeometryProcessor.h` - 几何处理器接口
  - `src/gpu/ganesh/GrProgramInfo.h` - 程序信息管理
  - `include/gpu/ganesh/GrRecordingContext.h` - GPU 录制上下文

TestOps 作为测试工具，不属于 Skia 的生产代码路径，而是专门为单元测试和集成测试提供支持。

## 主要类与结构体

### GP（GeometryProcessor）

```cpp
class GP : public GrGeometryProcessor {
public:
    GP(const SkMatrix& localMatrix, bool wideColor);
    const char* name() const override;
    std::unique_ptr<ProgramImpl> makeProgramImpl(const GrShaderCaps&) const override;
    void addToKey(const GrShaderCaps&, skgpu::KeyBuilder*) const override;
    bool wideColor() const;
};
```

GP 是测试专用的几何处理器，负责处理顶点数据和着色器代码生成。它包含三个顶点属性：
- `fInPosition` - 设备空间位置
- `fInLocalCoords` - 本地坐标
- `fInColor` - 顶点颜色（支持宽色域和窄色域）

该处理器的核心特性是支持本地矩阵变换，这使得测试能够验证在几何处理器中应用本地变换的效果处理器。

### TestRectOp

```cpp
class TestRectOp final : public GrMeshDrawOp {
public:
    static GrOp::Owner Make(GrRecordingContext*, GrPaint&&,
                            const SkRect& drawRect,
                            const SkRect& localRect,
                            const SkMatrix& localM);

    GrProcessorSet::Analysis finalize(const GrCaps&,
                                      const GrAppliedClip*,
                                      GrClampType) override;
};
```

TestRectOp 是测试矩形操作的主要实现类，继承自 GrMeshDrawOp。它封装了绘制单个矩形所需的所有数据：
- `fDrawRect` - 设备空间绘制矩形
- `fLocalRect` - 本地坐标矩形
- `fColor` - 预乘颜色
- `fGP` - 几何处理器实例
- `fProcessorSet` - 片段处理器集合
- `fProgramInfo` - 程序信息（用于预准备场景）
- `fMesh` - 网格数据

## 公共 API 函数

### MakeRect（完整版本）

```cpp
GrOp::Owner MakeRect(GrRecordingContext* context,
                     GrPaint&& paint,
                     const SkRect& drawRect,
                     const SkRect& localRect,
                     const SkMatrix& localM = SkMatrix::I());
```

创建一个完全指定的矩形绘制操作，支持独立的绘制矩形、本地坐标矩形和本地变换矩阵。这是最灵活的版本，允许测试复杂的坐标变换场景。

**参数说明**：
- `context` - GPU 录制上下文
- `paint` - 包含颜色和效果处理器的绘制配置
- `drawRect` - 设备空间的绘制矩形
- `localRect` - 本地坐标空间的矩形
- `localM` - 应用于本地坐标的变换矩阵

### MakeRect（片段处理器版本）

```cpp
GrOp::Owner MakeRect(GrRecordingContext* context,
                     std::unique_ptr<GrFragmentProcessor> fp,
                     const SkRect& drawRect,
                     const SkRect& localRect,
                     const SkMatrix& localM = SkMatrix::I());
```

简化版本，接受单个片段处理器而非完整的 GrPaint 对象，自动使用 `SkBlendMode::kSrcOver` 混合模式。这个版本特别适合测试单个效果处理器的行为。

### MakeRect（简化版本）

```cpp
GrOp::Owner MakeRect(GrRecordingContext* context,
                     GrPaint&& paint,
                     const SkRect& rect);
```

最简化的版本，使用同一个矩形作为绘制矩形和本地坐标矩形，本地矩阵为单位矩阵。适合不需要复杂坐标变换的基本测试场景。

## 内部实现细节

### 顶点数据准备

在 `onPrepareDraws` 方法中，TestRectOp 使用 QuadHelper 和 VertexWriter 来生成矩形的顶点数据：

```cpp
void TestRectOp::onPrepareDraws(GrMeshDrawTarget* target) {
    QuadHelper helper(target, fGP.vertexStride(), 1);
    skgpu::VertexWriter writer{helper.vertices()};
    auto pos = skgpu::VertexWriter::TriStripFromRect(fDrawRect);
    auto local = skgpu::VertexWriter::TriStripFromRect(fLocalRect);
    skgpu::VertexColor color(fColor, fGP.wideColor());
    writer.writeQuad(pos, local, color);
    fMesh = helper.mesh();
}
```

顶点数据以三角形带（Triangle Strip）的形式组织，每个矩形由四个顶点组成。每个顶点包含位置、本地坐标和颜色三个属性。

### 着色器代码生成

GP::ProgramImpl::onEmitCode 方法负责生成 GLSL 着色器代码：

1. **顶点着色器部分**：
   - 将顶点颜色传递到片段着色器（通过 varying）
   - 写入设备空间位置到 `gl_Position`
   - 应用本地矩阵并计算本地坐标

2. **片段着色器部分**：
   - 接收插值后的顶点颜色
   - 输出不透明的覆盖率（`coverage = 1.0`）

### 宽色域支持

TestOps 支持两种颜色编码方式：
- **窄色域**：使用 `kUByte4_norm_GrVertexAttribType`（8位/通道）
- **宽色域**：当颜色值超出 [0,1] 范围且硬件支持半精度浮点时，使用 half-float 格式

选择逻辑在 `use_wide_color` 函数中：

```cpp
static bool use_wide_color(const GrPaint& paint, const GrCaps* caps) {
    return !paint.getColor4f().fitsInBytes() && caps->halfFloatVertexAttributeSupport();
}
```

### 程序信息创建

TestRectOp 支持两种程序创建模式：

1. **延迟创建**：在 `onExecute` 中调用 `createProgramInfo`
2. **预准备创建**：在 `onCreateProgramInfo` 中提前创建并缓存在 `fProgramInfo` 中

这种双模式设计支持 Ganesh 的优化策略，允许在录制时预先准备程序信息以减少渲染时的开销。

### 处理器分析

`finalize` 方法执行处理器集合的分析，确定最终的颜色和覆盖率特性：

```cpp
GrProcessorSet::Analysis TestRectOp::finalize(...) {
    return fProcessorSet.finalize(GrProcessorAnalysisColor::Opaque::kYes,
                                  GrProcessorAnalysisCoverage::kSingleChannel,
                                  clip, &GrUserStencilSettings::kUnused,
                                  caps, clampType, &fColor);
}
```

这个分析假设输入颜色是不透明的，并使用单通道覆盖率。

## 依赖关系

### 核心依赖

- **GrMeshDrawOp**：提供网格绘制操作的基础设施
- **GrGeometryProcessor**：定义几何处理器接口
- **GrPaint**：封装绘制状态和效果处理器
- **GrRecordingContext**：提供 GPU 操作的录制上下文

### 工具类依赖

- **QuadHelper**：简化四边形网格的创建
- **VertexWriter**：高效的顶点数据写入工具
- **GrSimpleMeshDrawOpHelper**：提供程序信息创建的辅助功能

### 着色器相关

- **GrGLSLFragmentShaderBuilder**：构建片段着色器代码
- **GrGLSLVarying**：管理顶点着色器和片段着色器之间的变量传递
- **GrGLSLVertexGeoBuilder**：构建顶点/几何着色器代码

## 设计模式与设计决策

### 工厂模式

TestOps 使用工厂函数而非直接构造，提供了多个重载的 `MakeRect` 函数。这种设计：
- 隐藏了内部 TestRectOp 类的实现细节
- 通过不同的重载提供了灵活性和便利性
- 返回 `GrOp::Owner`（unique_ptr）确保内存安全

### 命名空间隔离

API 函数位于 `sk_gpu_test::test_ops` 命名空间中，清晰地标识这是测试工具代码，避免与生产代码混淆。

### 最小化设计原则

TestRectOp 故意设计得非常简单：
- 不支持反锯齿（`HasAABloat::kNo`）
- 不支持发线渲染（`IsHairline::kNo`）
- 固定功能标志为 None
- 不支持操作合并

这种最小化设计使测试结果更可预测、更容易验证。

### 本地矩阵在 GP 中的处理

与标准的矩形绘制代码不同，TestOps 将本地矩阵保留在几何处理器中而非预先应用到顶点坐标。这是一个关键的设计决策，因为：
- 许多效果处理器依赖于几何处理器中的本地坐标变换
- 标准绘制路径会优化掉这种变换
- 测试需要覆盖这种更通用的场景

### 双模式程序创建

支持延迟和预准备两种程序创建模式，这反映了 Ganesh 的优化策略：
- 预准备模式允许在录制时创建程序，减少渲染时延迟
- 延迟模式提供了简单性和灵活性
- 通过 `fProgramInfo` 指针的空检查来决定使用哪种模式

## 性能考量

### 顶点数据写入优化

使用 `skgpu::VertexWriter` 和 `TriStripFromRect` 提供高效的顶点数据写入：
- 顶点数据连续写入，减少内存碎片
- 使用三角形带减少顶点数量（4个顶点而非6个）
- 直接写入 GPU 缓冲区，避免中间拷贝

### 着色器键缓存

通过 `addToKey` 方法为每个几何处理器配置生成唯一的键：
```cpp
void addToKey(..., skgpu::KeyBuilder* b) const override {
    b->add32(ProgramImpl::ComputeMatrixKey(shaderCaps, fLocalMatrix));
}
```

这允许 Ganesh 缓存和重用编译好的着色器程序，避免重复编译。

### 内存池分配

TestRectOp 通过 `GrOp::Make` 使用内存池分配，这是 Ganesh 操作的标准做法：
- 减少内存分配和释放的开销
- 提高缓存局部性
- 支持批量释放

### 测试场景的简化

作为测试工具，TestOps 有意不实现某些优化特性：
- 不支持操作合并（Op batching）
- 不支持动态状态
- 固定使用三角形图元类型

这些简化使测试更专注于验证核心功能，而不是性能优化。

## 相关文件

### 同目录工具文件
- `tools/ganesh/ProxyUtils.h/cpp` - 代理工具函数
- `tools/ganesh/TestContext.h/cpp` - 测试上下文管理
- `tools/ganesh/MemoryCache.h/cpp` - 内存缓存测试工具

### Ganesh 核心文件
- `src/gpu/ganesh/ops/GrMeshDrawOp.h` - 网格绘制操作基类
- `src/gpu/ganesh/ops/GrSimpleMeshDrawOpHelper.h` - 操作辅助工具
- `src/gpu/ganesh/GrGeometryProcessor.h` - 几何处理器接口
- `src/gpu/ganesh/GrProgramInfo.h` - 程序信息管理

### 着色器构建文件
- `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h` - 片段着色器构建器
- `src/gpu/ganesh/glsl/GrGLSLVarying.h` - Varying 变量管理
- `src/gpu/ganesh/glsl/GrGLSLVertexGeoBuilder.h` - 顶点/几何着色器构建器

### 工具类文件
- `src/gpu/BufferWriter.h` - 缓冲区写入工具
- `src/core/SkPointPriv.h` - 点操作私有接口
- `include/core/SkRefCnt.h` - 引用计数基础设施
