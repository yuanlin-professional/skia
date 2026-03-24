# GrGLProgram

> 源文件
> - src/gpu/ganesh/gl/GrGLProgram.h
> - src/gpu/ganesh/gl/GrGLProgram.cpp

## 概述

`GrGLProgram` 是 Skia Ganesh OpenGL 后端中代表一个完整 GPU 着色器程序的类。它管理着一个已编译和链接的 OpenGL 程序对象，并记录该程序的所有相关信息，包括顶点和实例属性布局、uniform 数据管理器、以及各种着色器阶段的实现（几何处理器、片段处理器、传输处理器）。

该类封装了 OpenGL 程序的生命周期管理、uniform 数据上传、纹理绑定以及渲染目标状态更新等功能。它是 Skia 渲染管线中连接高层抽象（如 `GrProgramInfo`）和底层 OpenGL API 的关键组件。

## 架构位置

```
GrGLSLProgramBuilder
    ↓ (构建)
GrGLProgram
    ├── GrGLProgramDataManager (uniform管理)
    ├── GrGeometryProcessor::ProgramImpl (几何处理器)
    ├── GrFragmentProcessor::ProgramImpl (片段处理器)
    └── GrXferProcessor::ProgramImpl (传输处理器)

渲染流程:
GrProgramInfo -> GrGLProgram::updateUniforms() -> GPU Shader
```

`GrGLProgram` 位于 Ganesh 图形栈的程序管理层，是 OpenGL 着色器程序的完整封装，负责协调所有着色器阶段和资源。

## 主要类与结构体

### GrGLProgram

**继承关系:**
- 继承自: `SkRefCnt`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fProgramID` | `GrGLuint` | OpenGL 程序 ID |
| `fGpu` | `GrGLGpu*` | 指向 GL GPU 对象的指针 |
| `fProgramDataManager` | `GrGLProgramDataManager` | Uniform 数据管理器 |
| `fBuiltinUniformHandles` | `GrGLSLBuiltinUniformHandles` | 内置 uniform 句柄集合 |
| `fGPImpl` | `std::unique_ptr<GrGeometryProcessor::ProgramImpl>` | 几何处理器实现 |
| `fXPImpl` | `std::unique_ptr<GrXferProcessor::ProgramImpl>` | 传输处理器实现 |
| `fFPImpls` | `std::vector<std::unique_ptr<GrFragmentProcessor::ProgramImpl>>` | 片段处理器实现数组 |
| `fAttributes` | `std::unique_ptr<Attribute[]>` | 顶点属性数组 |
| `fVertexAttributeCnt` | `int` | 顶点属性数量 |
| `fInstanceAttributeCnt` | `int` | 实例属性数量 |
| `fVertexStride` | `int` | 顶点步长（字节） |
| `fInstanceStride` | `int` | 实例步长（字节） |
| `fNumTextureSamplers` | `int` | 纹理采样器数量 |
| `fRenderTargetState` | `RenderTargetState` | 渲染目标状态缓存 |

### Attribute 结构体

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCPUType` | `GrVertexAttribType` | CPU 侧属性类型 |
| `fGPUType` | `SkSLType` | GPU 侧 GLSL 类型 |
| `fOffset` | `size_t` | 属性在缓冲中的偏移量 |
| `fLocation` | `GrGLint` | OpenGL 属性位置 |

### RenderTargetState 结构体

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRenderTargetSize` | `SkISize` | 渲染目标尺寸 |
| `fRenderTargetOrigin` | `GrSurfaceOrigin` | 渲染目标原点位置 |

## 公共 API 函数

### 静态工厂方法
- `static sk_sp<GrGLProgram> Make(...)` - 创建 GL 程序对象

### 生命周期管理
- `~GrGLProgram()` - 析构函数，删除 GL 程序
- `void abandon()` - 放弃 GL 对象所有权

### 访问器
- `GrGLuint programID() const` - 获取 GL 程序 ID
- `int vertexStride() const` - 获取顶点步长
- `int instanceStride() const` - 获取实例步长
- `int numVertexAttributes() const` - 获取顶点属性数量
- `int numInstanceAttributes() const` - 获取实例属性数量
- `const Attribute& vertexAttribute(int i) const` - 获取顶点属性
- `const Attribute& instanceAttribute(int i) const` - 获取实例属性

### 数据更新
- `void updateUniforms(const GrRenderTarget*, const GrProgramInfo&)` - 更新所有 uniform 数据
- `void bindTextures(const GrGeometryProcessor&, const GrSurfaceProxy* const[], const GrPipeline&)` - 绑定所有纹理

## 内部实现细节

### 程序创建和初始化

工厂方法负责创建程序并设置采样器 uniform：

```cpp
sk_sp<GrGLProgram> GrGLProgram::Make(...) {
    sk_sp<GrGLProgram> program(new GrGLProgram(...));

    // 激活程序并设置采样器单元
    gpu->flushProgram(program);
    program->fProgramDataManager.setSamplerUniforms(textureSamplers, 0);

    return program;
}
```

### Uniform 数据更新流程

`updateUniforms` 方法按特定顺序更新所有着色器阶段的数据：

```cpp
void GrGLProgram::updateUniforms(const GrRenderTarget* renderTarget,
                                 const GrProgramInfo& programInfo) {
    // 1. 更新渲染目标状态（RT 调整、翻转等）
    this->setRenderTargetState(renderTarget, programInfo.origin(), programInfo.geomProc());

    // 2. 更新几何处理器 uniform
    fGPImpl->setData(fProgramDataManager, *fGpu->caps()->shaderCaps(), programInfo.geomProc());

    // 3. 更新所有片段处理器 uniform
    for (int i = 0; i < programInfo.pipeline().numFragmentProcessors(); ++i) {
        const auto& fp = programInfo.pipeline().getFragmentProcessor(i);
        fp.visitWithImpls([&](const GrFragmentProcessor& fp,
                              GrFragmentProcessor::ProgramImpl& impl) {
            impl.setData(fProgramDataManager, fp);
        }, *fFPImpls[i]);
    }

    // 4. 更新目标纹理 uniform
    programInfo.pipeline().setDstTextureUniforms(fProgramDataManager, &fBuiltinUniformHandles);

    // 5. 更新传输处理器 uniform
    fXPImpl->setData(fProgramDataManager, programInfo.pipeline().getXferProcessor());
}
```

### 纹理绑定策略

纹理按特定顺序绑定到纹理单元：

```cpp
void GrGLProgram::bindTextures(...) {
    int nextTexSamplerIdx = 0;

    // 1. 绑定几何处理器纹理
    for (int i = 0; i < geomProc.numTextureSamplers(); ++i) {
        fGpu->bindTexture(nextTexSamplerIdx++, ...);
    }

    // 2. 绑定目标纹理（如果存在）
    GrTexture* dstTexture = pipeline.peekDstTexture();
    if (dstTexture) {
        fGpu->bindTexture(nextTexSamplerIdx++, ...);
    }

    // 3. 绑定片段处理器纹理
    pipeline.visitTextureEffects([&](const GrTextureEffect& te) {
        fGpu->bindTexture(nextTexSamplerIdx++, ...);
    });
}
```

### 渲染目标坐标转换

`setRenderTargetState` 计算从 Skia 设备空间到 OpenGL NDC 空间的转换：

```cpp
void GrGLProgram::setRenderTargetState(const GrRenderTarget* rt,
                                       GrSurfaceOrigin origin,
                                       const GrGeometryProcessor& geomProc) {
    SkISize dimensions = rt->dimensions();
    if (fRenderTargetState.fRenderTargetOrigin != origin ||
        fRenderTargetState.fRenderTargetSize != dimensions) {
        fRenderTargetState.fRenderTargetSize = dimensions;
        fRenderTargetState.fRenderTargetOrigin = origin;

        // GL 的帧缓冲空间 (0,0) 在左下角，需要翻转
        bool flip = (origin == kBottomLeft_GrSurfaceOrigin);

        // 设置 RT 调整向量（用于坐标变换）
        std::array<float, 4> v = SkSL::Compiler::GetRTAdjustVector(dimensions, flip);
        fProgramDataManager.set4fv(fBuiltinUniformHandles.fRTAdjustmentUni, 1, v.data());

        // 设置 RT 翻转向量（如果需要）
        if (fBuiltinUniformHandles.fRTFlipUni.isValid()) {
            std::array<float, 2> d = SkSL::Compiler::GetRTFlipVector(dimensions.height(), flip);
            fProgramDataManager.set2fv(fBuiltinUniformHandles.fRTFlipUni, 1, d.data());
        }
    }
}
```

### 属性布局管理

顶点和实例属性在连续数组中存储：

```cpp
const Attribute& vertexAttribute(int i) const {
    SkASSERT(i >= 0 && i < fVertexAttributeCnt);
    return fAttributes[i];  // 顶点属性在前
}

const Attribute& instanceAttribute(int i) const {
    SkASSERT(i >= 0 && i < fInstanceAttributeCnt);
    return fAttributes[i + fVertexAttributeCnt];  // 实例属性在后
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLGpu` | GPU 接口和程序绑定 |
| `GrGLProgramDataManager` | Uniform 数据上传 |
| `GrGeometryProcessor` | 几何处理器抽象 |
| `GrFragmentProcessor` | 片段处理器抽象 |
| `GrXferProcessor` | 传输处理器抽象 |
| `GrPipeline` | 图形管线状态 |
| `GrGLTexture` | GL 纹理对象 |
| `SkSL::Compiler` | 着色器编译器（RT 调整计算） |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrGLGpu` | 通过该类管理程序生命周期 |
| `GrGLOpsRenderPass` | 使用该类进行绘制 |
| `GrGLProgramBuilder` | 构建该类实例 |

## 设计模式与设计决策

### 1. 智能指针管理

使用 `sk_sp<GrGLProgram>` 管理程序生命周期：

```cpp
static sk_sp<GrGLProgram> Make(...) {
    sk_sp<GrGLProgram> program(new GrGLProgram(...));
    return program;
}
```

**优势**: 自动引用计数，防止内存泄漏

### 2. 访客模式 (Visitor Pattern)

使用访客模式遍历片段处理器树：

```cpp
fp.visitWithImpls([&](const GrFragmentProcessor& fp,
                      GrFragmentProcessor::ProgramImpl& impl) {
    impl.setData(fProgramDataManager, fp);
}, *fFPImpls[i]);
```

### 3. 状态缓存模式

缓存渲染目标状态，避免重复设置：

```cpp
if (fRenderTargetState.fRenderTargetOrigin != origin ||
    fRenderTargetState.fRenderTargetSize != dimensions) {
    // 仅在状态变化时更新
    ...
}
```

### 4. 组合模式 (Composition Pattern)

将多个处理器实现组合到程序对象中：

```cpp
std::unique_ptr<GrGeometryProcessor::ProgramImpl> fGPImpl;
std::unique_ptr<GrXferProcessor::ProgramImpl> fXPImpl;
std::vector<std::unique_ptr<GrFragmentProcessor::ProgramImpl>> fFPImpls;
```

## 性能考量

### 1. 状态变化最小化

通过 `RenderTargetState` 缓存避免不必要的 uniform 更新：

```cpp
if (fRenderTargetState.fRenderTargetOrigin != origin ||
    fRenderTargetState.fRenderTargetSize != dimensions) {
    // 仅在 RT 状态变化时更新
}
```

**优势**: 减少 GL 调用和驱动开销

### 2. 采样器单元预分配

在程序创建时一次性设置所有采样器单元：

```cpp
program->fProgramDataManager.setSamplerUniforms(textureSamplers, 0);
```

**优势**: 运行时不需要重复设置采样器 uniform

### 3. 属性数组连续存储

顶点和实例属性存储在同一数组中：

```cpp
std::unique_ptr<Attribute[]> fAttributes;
```

**优势**: 提高缓存局部性，减少间接访问

### 4. 析构时资源释放

及时释放 OpenGL 程序对象：

```cpp
GrGLProgram::~GrGLProgram() {
    if (fProgramID) {
        GL_CALL(DeleteProgram(fProgramID));
    }
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/gl/GrGLProgramDataManager.h` | 组合 | Uniform 数据管理 |
| `src/gpu/ganesh/gl/GrGLGpu.h` | 依赖 | GPU 接口 |
| `src/gpu/ganesh/gl/builders/GrGLProgramBuilder.h` | 构建者 | 程序构建器 |
| `src/gpu/ganesh/GrGeometryProcessor.h` | 依赖 | 几何处理器 |
| `src/gpu/ganesh/GrFragmentProcessor.h` | 依赖 | 片段处理器 |
| `src/gpu/ganesh/GrXferProcessor.h` | 依赖 | 传输处理器 |
| `src/gpu/ganesh/GrProgramInfo.h` | 依赖 | 程序信息容器 |
| `src/sksl/SkSLCompiler.h` | 依赖 | RT 调整计算 |
