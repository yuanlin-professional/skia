# GrMtlPipelineStateBuilder

> 源文件
> - `src/gpu/ganesh/mtl/GrMtlPipelineStateBuilder.h`
> - `src/gpu/ganesh/mtl/GrMtlPipelineStateBuilder.mm`

## 概述

`GrMtlPipelineStateBuilder` 是 Ganesh 图形后端中 Metal 实现的管道状态构建器类,负责从着色器源代码和渲染配置生成完整的 Metal 渲染管道状态对象。该类作为管道编译的核心组件,协调着色器编译、顶点描述符创建、混合状态配置以及管道缓存等复杂流程。支持从 SkSL 到 MSL 的着色器转换、持久化缓存、预编译优化等高级特性,是连接 Skia 高层渲染抽象与 Metal 底层 API 的关键桥梁。

## 架构位置

`GrMtlPipelineStateBuilder` 位于 Skia 图形库的 GPU 后端着色器编译层次结构中:

```
Skia 图形库
└── GPU 后端 (src/gpu)
    └── Ganesh 渲染引擎 (ganesh)
        ├── GLSL 程序构建器 (glsl)
        │   └── GrGLSLProgramBuilder (抽象构建器基类)
        │       └── GrMtlPipelineStateBuilder (Metal 构建器) ← 当前类
        └── Metal 后端实现 (mtl)
            ├── GrMtlPipelineState (管道状态)
            ├── GrMtlUniformHandler (Uniform 处理器)
            ├── GrMtlVaryingHandler (Varying 处理器)
            └── GrMtlGpu (GPU 接口)
```

该类继承通用程序构建器,实现 Metal 特定的管道生成逻辑。

## 主要类与结构体

### GrMtlPrecompiledLibraries 结构体

存储预编译的 Metal 着色器库。

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fVertexLibrary` | `id<MTLLibrary>` | 顶点着色器库 |
| `fFragmentLibrary` | `id<MTLLibrary>` | 片段着色器库 |
| `fRTFlip` | `bool` | 是否需要渲染目标翻转 |

### GrMtlPipelineStateBuilder 类

Metal 管道状态构建器。

**继承关系:**
- 继承: `GrGLSLProgramBuilder` (GLSL 程序构建器基类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGpu` | `GrMtlGpu*` | Metal GPU 对象指针 |
| `fUniformHandler` | `GrMtlUniformHandler` | Uniform 变量处理器 |
| `fVaryingHandler` | `GrMtlVaryingHandler` | Varying 变量处理器 |

## 公共 API 函数

### 静态工厂方法

```cpp
static GrMtlPipelineState* CreatePipelineState(
    GrMtlGpu* gpu,
    const GrProgramDesc& desc,
    const GrProgramInfo& programInfo,
    const GrMtlPrecompiledLibraries* precompiledLibs = nullptr)
```
创建 Metal 管道状态对象。这是主要的入口函数,协调整个管道构建流程。可选的 `precompiledLibs` 参数允许使用预编译的着色器库。

### 预编译支持

```cpp
static bool PrecompileShaders(
    GrMtlGpu* gpu,
    const SkData& cachedData,
    GrMtlPrecompiledLibraries* precompiledLibs)
```
从缓存数据预编译着色器库。用于延迟显示列表(DDL)和启动性能优化场景,异步触发管道编译。

## 内部实现细节

### 管道构建流程

`CreatePipelineState()` 实现完整的管道构建流程:

1. **设置区域**: 使用 `GrAutoLocaleSetter` 确保数值格式一致
2. **发射处理器**: `emitAndInstallProcs()` 生成着色器代码
3. **最终化**: `finalize()` 编译着色器并创建管道状态

### 着色器编译路径

`finalize()` 支持多种着色器来源:

1. **预编译库**: 直接使用传入的 `precompiledLibs`
2. **持久化缓存**:
   - **MSL 缓存**: 从缓存加载已编译的 MSL 代码
   - **SkSL 缓存**: 从缓存加载 SkSL,实时转换为 MSL
3. **实时编译**: 从 SkSL 源代码生成 MSL 并编译

### 着色器缓存策略

支持两种缓存标签:

```cpp
static constexpr SkFourByteTag kMSL_Tag = 'MSL ';   // 缓存 MSL 代码
static constexpr SkFourByteTag kSKSL_Tag = 'SKSL';  // 缓存 SkSL 代码
```

缓存策略由 `GrContextOptions::ShaderCacheStrategy` 控制:
- **SkSL 策略**: 缓存平台无关的 SkSL 源代码,启动时转换
- **Backend 策略**: 缓存平台相关的 MSL 代码,减少编译时间

### 顶点描述符创建

`create_vertex_descriptor()` 从几何处理器生成 Metal 顶点描述符:

```cpp
// 顶点属性
for (auto attribute : geomProc.vertexAttributes()) {
    mtlAttribute.format = attribute_type_to_mtlformat(type);
    mtlAttribute.offset = *attribute.offset();
    mtlAttribute.bufferIndex = vertexBinding;
}

// 实例属性
for (auto attribute : geomProc.instanceAttributes()) {
    mtlAttribute.format = attribute_type_to_mtlformat(type);
    mtlAttribute.bufferIndex = instanceBinding;
}
```

支持每顶点(per-vertex)和每实例(per-instance)属性,buffer 索引从 `kLastUniformBinding + 1` 开始。

### 混合状态配置

`create_color_attachment()` 配置混合状态:

```cpp
// 检查是否需要混合
bool blendOn = !skgpu::BlendShouldDisable(equation, srcCoeff, dstCoeff);

if (blendOn) {
    // 配置 RGB 混合
    mtlColorAttachment.sourceRGBBlendFactor = ...;
    mtlColorAttachment.rgbBlendOperation = ...;

    // 配置 Alpha 混合
    mtlColorAttachment.sourceAlphaBlendFactor = ...;
    mtlColorAttachment.alphaBlendOperation = ...;
}
```

支持独立的 RGB 和 Alpha 混合方程。

### 属性类型转换

`attribute_type_to_mtlformat()` 将 Skia 属性类型映射到 Metal 格式:

- `Float/Float2/Float3/Float4` → `MTLVertexFormatFloat*`
- `Half/Half2/Half4` → `MTLVertexFormatHalf*`
- `Int/UInt` → `MTLVertexFormatInt/UInt`
- `Byte/UByte` → `MTLVertexFormatChar/UChar`
- `Short/UShort` → `MTLVertexFormatShort/UShort`

包含平台可用性检查,旧版本系统返回 `MTLVertexFormatInvalid`。

### 混合系数转换

`blend_coeff_to_mtl_blend()` 转换混合系数:

```cpp
kZero → MTLBlendFactorZero
kOne → MTLBlendFactorOne
kSC → MTLBlendFactorSourceColor
kDC → MTLBlendFactorDestinationColor
kSA → MTLBlendFactorSourceAlpha
kS2C → MTLBlendFactorSource1Color  // 双源混合
```

支持标准混合和双源混合(macOS 10.12+)。

### 混合方程转换

`blend_equation_to_mtl_blend_op()` 使用静态查找表:

```cpp
static const MTLBlendOperation gTable[] = {
    MTLBlendOperationAdd,
    MTLBlendOperationSubtract,
    MTLBlendOperationReverseSubtract,
};
```

### Uniform 缓冲对齐

`buffer_size()` 计算对齐的缓冲大小:

```cpp
uint32_t offsetDiff = offset & maxAlignment;
if (offsetDiff != 0) {
    offsetDiff = maxAlignment - offsetDiff + 1;
}
return offset + offsetDiff;
```

Metal 要求 uniform 缓冲按最大元素对齐方式填充。

### 序列化与反序列化

支持管道数据的序列化用于持久化缓存:

- **`create_vertex_descriptor()`**: 写入顶点描述符数据
- **`create_color_attachment()`**: 写入颜色附件配置
- **`read_pipeline_data()`**: 从缓存读取重建管道描述符

### 预编译异步执行

`PrecompileShaders()` 使用异步 API:

```objc
[gpu->device() newRenderPipelineStateWithDescriptor: desc
                                  completionHandler: ^(id<MTLRenderPipelineState> state,
                                                      NSError* error) {
    // 异步完成回调
}];
```

依赖 Apple 的管道缓存机制管理编译结果。

### RT 翻转支持

检测着色器是否需要渲染目标 Y 轴翻转:

```cpp
if (interface.fRTFlipUniform != SkSL::Program::Interface::kRTFlip_None) {
    this->addRTFlipUniform(SKSL_RTFLIP_NAME);
}
```

用于协调不同图形 API 的坐标系差异。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLSLProgramBuilder` | 程序构建器基类 |
| `GrMtlGpu` | Metal GPU 接口 |
| `GrMtlPipelineState` | 生成的管道状态对象 |
| `GrMtlUniformHandler` | Uniform 变量管理 |
| `GrMtlVaryingHandler` | Varying 变量管理 |
| `GrMtlUtil` | Metal 工具函数 |
| `GrProgramDesc` | 程序描述符 |
| `GrProgramInfo` | 程序信息 |
| `GrPersistentCacheUtils` | 持久化缓存工具 |
| `skgpu::SkSLToMSL` | SkSL 到 MSL 转换器 |
| `SkSL::Compiler` | SkSL 编译器 |
| `Metal.framework` | Metal API |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| `GrMtlResourceProvider` | 使用构建器创建管道状态 |
| `GrMtlGpu` | 通过构建器生成管道 |

## 设计模式与设计决策

### 1. 构建器模式 (Builder Pattern)

类名明确表明使用构建器模式,分步骤构建复杂的管道状态对象:

```cpp
GrMtlPipelineStateBuilder builder(gpu, desc, programInfo);
builder.emitAndInstallProcs();
return builder.finalize(desc, programInfo, precompiledLibs);
```

### 2. 模板方法模式 (Template Method)

继承 `GrGLSLProgramBuilder`,重写关键方法实现 Metal 特定逻辑:

```cpp
const GrCaps* caps() const override;
void finalizeFragmentSecondaryColor(GrShaderVar&) override;
GrGLSLUniformHandler* uniformHandler() override;
```

### 3. 策略模式 (Strategy Pattern)

支持多种着色器缓存策略,通过配置选择:

```cpp
if (cacheStrategy == ShaderCacheStrategy::kSkSL) {
    // 缓存 SkSL
} else {
    // 缓存 MSL
}
```

### 4. 工厂模式 (Factory Pattern)

静态工厂方法封装创建逻辑:

```cpp
static GrMtlPipelineState* CreatePipelineState(...);
static bool PrecompileShaders(...);
```

### 5. 两阶段编译

支持编译和链接分离:
- **阶段一**: 预编译着色器库(`PrecompileShaders`)
- **阶段二**: 使用预编译库创建管道(`CreatePipelineState`)

这种设计支持离线编译和快速启动。

### 6. 缓存透明性

构建器内部透明处理缓存:
- 尝试从缓存加载
- 未命中则编译
- 编译结果自动写入缓存

调用者无需关心缓存细节。

### 7. 序列化支持

管道描述符可序列化,支持:
- 离线工具分析
- 持久化缓存
- 调试和诊断

### 8. 平台适配

运行时检查平台版本,优雅降级不支持的特性:

```objc
if (@available(macOS 10.13, iOS 11.0, tvOS 11.0, *)) {
    return MTLVertexFormatHalf;
} else {
    return MTLVertexFormatInvalid;
}
```

## 性能考量

### 1. 持久化缓存

利用 Skia 的持久化缓存机制,避免重复编译:
- 首次运行编译并缓存
- 后续启动从缓存加载
- 显著减少启动延迟

### 2. 预编译优化

`PrecompileShaders()` 支持异步预编译:
- 后台线程编译
- 不阻塞主渲染
- 依赖 Apple 的管道缓存

### 3. 着色器缓存策略

- **SkSL 缓存**: 跨 Metal 版本兼容,但需运行时转换
- **MSL 缓存**: 快速加载,但平台相关

根据场景选择策略权衡。

### 4. 对齐计算优化

Uniform 缓冲对齐计算高效:

```cpp
uint32_t offsetDiff = offset & maxAlignment;
```

使用位运算而非除法/取模。

### 5. 静态查找表

混合方程转换使用静态表,避免运行时 switch:

```cpp
static const MTLBlendOperation gTable[] = {...};
return gTable[(int)equation];
```

### 6. 延迟编译

仅在需要时编译着色器,避免无用编译:

```cpp
if (msl[kVertex_GrShaderType].fText.empty()) {
    // 编译顶点着色器
}
```

### 7. 调试信息控制

调试标签仅在 `SK_ENABLE_MTL_DEBUG_INFO` 时生成:

```cpp
#ifdef SK_ENABLE_MTL_DEBUG_INFO
    pipelineDescriptor.label = @(description.c_str());
#endif
```

生产环境减少开销。

### 8. Trace 事件

使用 `TRACE_EVENT0` 标记关键路径,支持性能分析:

```cpp
TRACE_EVENT0("skia.shaders", TRACE_FUNC);
TRACE_EVENT0("skia.shaders", "newRenderPipelineStateWithDescriptor");
```

### 9. 错误处理

着色器编译失败立即返回,避免后续无效操作:

```cpp
if (!shaderLibraries[kVertex_GrShaderType]) {
    return nullptr;
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/glsl/GrGLSLProgramBuilder.h` | 继承关系 | 程序构建器基类 |
| `src/gpu/ganesh/mtl/GrMtlGpu.h/mm` | 使用关系 | GPU 接口 |
| `src/gpu/ganesh/mtl/GrMtlPipelineState.h/mm` | 创建关系 | 生成的管道状态 |
| `src/gpu/ganesh/mtl/GrMtlUniformHandler.h/mm` | 组合关系 | Uniform 处理器 |
| `src/gpu/ganesh/mtl/GrMtlVaryingHandler.h/mm` | 组合关系 | Varying 处理器 |
| `src/gpu/ganesh/mtl/GrMtlUtil.h/mm` | 使用关系 | Metal 工具函数 |
| `src/gpu/ganesh/mtl/GrMtlResourceProvider.h/mm` | 被使用关系 | 资源提供者调用构建器 |
| `src/gpu/ganesh/GrProgramDesc.h` | 使用关系 | 程序描述符 |
| `src/gpu/ganesh/GrProgramInfo.h` | 使用关系 | 程序信息 |
| `src/gpu/ganesh/GrPersistentCacheUtils.h` | 使用关系 | 缓存工具 |
| `src/gpu/SkSLToBackend.h` | 使用关系 | SkSL 到后端转换 |
| `src/sksl/SkSLCompiler.h` | 使用关系 | SkSL 编译器 |
| `src/gpu/mtl/MtlUtilsPriv.h` | 使用关系 | Metal 内部工具 |
