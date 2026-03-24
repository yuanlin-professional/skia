# glsl - Ganesh GLSL 着色器代码生成框架

## 概述

`src/gpu/ganesh/glsl` 目录是 Skia Ganesh GPU 后端的着色器代码生成基础框架，包含约 17 个源文件（头文件与实现文件成对出现，外加一个纯头文件）。该框架虽然以 "GLSL" 命名，但实际上是所有 GPU 后端（OpenGL、Vulkan、Metal、Dawn/WebGPU、Direct3D）共用的着色器构建抽象层。它提供了一套统一的 API，使得 effects 目录中的各种处理器能够以 GPU 后端无关的方式生成着色器代码。

该框架的核心职责包括：(1) 着色器代码的分段构建与拼接，包括扩展声明、精度声明、uniform 声明、输入/输出声明、函数定义、主函数等各部分；(2) uniform 变量的声明、管理和数据上传；(3) varying 变量在顶点着色器和片段着色器之间的传递；(4) 着色器程序的整体组装，将几何处理器、片段处理器链和混合传输处理器的代码组合为完整的着色器程序。

框架采用了分层抽象的设计，`GrGLSLShaderBuilder` 作为所有着色器构建器的基类，`GrGLSLVertexBuilder` 和 `GrGLSLFragmentShaderBuilder` 分别负责顶点和片段着色器的特定逻辑。`GrGLSLProgramBuilder` 作为顶层协调者，驱动整个着色器程序的生成过程。具体的 GPU 后端（如 `GrGLProgramBuilder`、`GrVkPipelineStateBuilder`、`GrMtlPipelineStateBuilder`）继承这些抽象类，提供各自的实现。

此框架与 `effects` 目录紧密配合：每个效果处理器都包含一个内部 `ProgramImpl` 类（或 `Impl` 类），这些 Impl 类使用本框架提供的 API 来生成对应的着色器代码。这种处理器与代码生成的分离使得同一个逻辑效果可以在不同 GPU 后端上复用。

## 架构图

```
                    ┌────────────────────────────────────────┐
                    │        GrGLSLProgramBuilder            │
                    │        (着色器程序顶层构建器)            │
                    │                                        │
                    │  ┌─ fVS: GrGLSLVertexBuilder          │
                    │  ├─ fFS: GrGLSLFragmentShaderBuilder  │
                    │  ├─ uniformHandler()                   │
                    │  └─ varyingHandler()                   │
                    └───┬──────────────────────┬─────────────┘
                        │                      │
           ┌────────────┘                      └──────────────┐
           v                                                   v
  ┌─────────────────────────┐              ┌─────────────────────────────┐
  │  GrGLSLVertexGeoBuilder │              │  GrGLSLFragmentShaderBuilder│
  │  (顶点/几何着色器构建器) │              │  (片段着色器构建器)          │
  │                         │              │                             │
  │  GrGLSLVertexBuilder    │              │  ┌ GrGLSLFPFragmentBuilder │
  │   └─ onFinalize()      │              │  │ (FP 使用的接口)          │
  │   └─ emitNormalized    │              │  └ GrGLSLXPFragmentBuilder │
  │       SkPosition()     │              │    (XP 使用的接口)          │
  └────────┬────────────────┘              └─────────┬───────────────────┘
           │                                          │
           └──────────────┬───────────────────────────┘
                          v
              ┌───────────────────────┐
              │  GrGLSLShaderBuilder  │
              │  (着色器构建器基类)    │
              │                       │
              │  - codeAppend()       │
              │  - codeAppendf()      │
              │  - emitFunction()     │
              │  - appendTexture      │
              │    Lookup()           │
              │  - defineConstant()   │
              │  - finalize()         │
              └───────────────────────┘
                          │
           ┌──────────────┼──────────────────┐
           v              v                  v
  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐
  │GrGLSLUniform│  │GrGLSLVarying │  │GrGLSLProgram     │
  │Handler      │  │Handler       │  │DataManager       │
  │(uniform管理)│  │(varying管理) │  │(运行时数据上传)   │
  └─────────────┘  └──────────────┘  └──────────────────┘

  ┌─────────────────────┐  ┌─────────────────────────────┐
  │  GrGLSLBlend        │  │  GrGLSLColorSpaceXformHelper│
  │  (混合模式辅助)      │  │  (色彩空间变换辅助)          │
  └─────────────────────┘  └─────────────────────────────┘
```

## 文件分类索引

### 1. 混合操作 — Blend Helpers

| 文件 | 说明 |
|------|------|
| GrGLSLBlend.h / GrGLSLBlend.cpp | 混合模式 SkSL 表达式生成 |

### 2. 着色器构建块 — Shader Builders

| 文件 | 说明 |
|------|------|
| GrGLSLShaderBuilder.h / GrGLSLShaderBuilder.cpp | 着色器构建器基类（代码分段拼接与函数管理） |
| GrGLSLFragmentShaderBuilder.h / GrGLSLFragmentShaderBuilder.cpp | 片段着色器构建器（FP/XP 接口 + 实现） |
| GrGLSLVertexGeoBuilder.h / GrGLSLVertexGeoBuilder.cpp | 顶点/几何着色器构建器 |

### 3. Uniform/Varying 处理 — Variable Management

| 文件 | 说明 |
|------|------|
| GrGLSLUniformHandler.h / GrGLSLUniformHandler.cpp | Uniform 变量声明与管理 |
| GrGLSLVarying.h / GrGLSLVarying.cpp | Varying 变量声明与管理 |

### 4. 程序构建/数据管理 — Program Builder

| 文件 | 说明 |
|------|------|
| GrGLSLProgramBuilder.h / GrGLSLProgramBuilder.cpp | 程序顶层构建器（协调 GP/FP/XP 代码生成） |
| GrGLSLProgramDataManager.h / GrGLSLProgramDataManager.cpp | 运行时 Uniform 数据上传管理器 |

### 5. 色彩空间工具 — Color Space Helper

| 文件 | 说明 |
|------|------|
| GrGLSLColorSpaceXformHelper.h | 色彩空间变换 Uniform 管理辅助 |

## 关键类与函数

### 1. GrGLSLShaderBuilder - 着色器构建器基类

所有着色器构建器的基类，管理着色器代码的各个段落并提供代码生成 API：

```cpp
class GrGLSLShaderBuilder {
public:
    // 向当前着色器追加代码
    void codeAppendf(const char format[], ...);
    void codeAppend(const char* str);
    void codePrependf(const char format[], ...);

    // 纹理采样
    void appendTextureLookup(SamplerHandle, const char* coordName,
                             GrGLSLColorSpaceXformHelper* = nullptr);

    // 纹理采样并混合
    void appendTextureLookupAndBlend(const char* dst, SkBlendMode,
                                     SamplerHandle, const char* coordName, ...);

    // 常量定义
    void defineConstant(const char* type, const char* name, const char* value);

    // 函数发射
    void emitFunction(SkSLType returnType, const char* mangledName,
                      SkSpan<const GrShaderVar> args, const char* body);

    // 名称混淆 - 生成唯一函数名
    SkString getMangledFunctionName(const char* baseName);

    // 最终化 - 拼接所有段落为完整着色器字符串
    void finalize(uint32_t visibility);
};
```

内部将着色器代码分为多个有序段落（通过 `fShaderStrings` 数组）：
- `kExtensions` - GLSL 扩展声明（如 `#extension GL_ARB_...`）
- `kDefinitions` - 常量和类型定义
- `kPrecisionQualifier` - 精度限定符
- `kLayoutQualifiers` - 布局限定符
- `kUniforms` - uniform 变量声明
- `kInputs` / `kOutputs` - 输入/输出变量
- `kFunctions` - 辅助函数
- `kMain` - 主函数及后续各阶段代码

### 2. GrGLSLFragmentShaderBuilder - 片段着色器构建器

采用虚拟菱形继承结构，同时实现两个接口：

```cpp
// 片段处理器使用的接口
class GrGLSLFPFragmentBuilder : virtual public GrGLSLShaderBuilder {
public:
    enum class ScopeFlags {
        kTopLevel = 0,                    // 所有片段都执行
        kInsidePerPrimitiveBranch = 1<<0, // 按图元级分支
        kInsidePerPixelBranch = 1<<1,     // 按像素级分支
        kInsideLoop = 1<<2               // 循环内部
    };
    virtual void forceHighPrecision() = 0;
    virtual const char* dstColor() = 0;   // 目标颜色变量名
};

// 混合传输处理器使用的接口
class GrGLSLXPFragmentBuilder : virtual public GrGLSLShaderBuilder {
public:
    virtual bool hasSecondaryOutput() const = 0;
    virtual const char* dstColor() = 0;
    virtual void enableAdvancedBlendEquationIfNeeded(skgpu::BlendEquation) = 0;
};

// 最终实现类 - 同时实现上述两个接口
class GrGLSLFragmentShaderBuilder : public GrGLSLFPFragmentBuilder,
                                     public GrGLSLXPFragmentBuilder {
    // 输出颜色变量: "sk_FragColor"
    // 二级输出颜色: "fsSecondaryColorOut" (双源混合)
};
```

### 3. GrGLSLVertexGeoBuilder / GrGLSLVertexBuilder - 顶点着色器构建器

```cpp
class GrGLSLVertexGeoBuilder : public GrGLSLShaderBuilder {
public:
    void insertFunction(const char* functionDefinition);

protected:
    // 发射标准化 sk_Position 计算代码
    void emitNormalizedSkPosition(const char* devPos,
                                  SkSLType devPosType = SkSLType::kFloat2);
};

class GrGLSLVertexBuilder : public GrGLSLVertexGeoBuilder {
    // 具体的顶点着色器构建器
};
```

### 4. GrGLSLProgramBuilder - 程序顶层构建器

协调整个着色器程序的生成过程，是最核心的管理类：

```cpp
class GrGLSLProgramBuilder {
public:
    // 访问器
    virtual const GrCaps* caps() const = 0;
    const GrShaderCaps* shaderCaps() const;
    const GrPipeline& pipeline() const;
    const GrGeometryProcessor& geometryProcessor() const;

    // 名称管理 - 生成带阶段前缀的变量名
    SkString nameVariable(char prefix, const char* name, bool mangle = true);

    // 阶段推进 - 每个处理器之间调用
    void advanceStage();

    // FP 函数生成
    void writeFPFunction(const GrFragmentProcessor& fp, ...);
    std::string invokeFP(const GrFragmentProcessor& fp, ...);

    // 纹理采样器发射
    bool emitTextureSamplersForFPs(const GrFragmentProcessor& fp, ...);

    // 子类访问器
    virtual GrGLSLUniformHandler* uniformHandler() = 0;
    virtual GrGLSLVaryingHandler* varyingHandler() = 0;

protected:
    // 核心组装流程
    bool emitAndInstallProcs();

    // 内部成员
    GrGLSLVertexBuilder          fVS;    // 顶点着色器构建器
    GrGLSLFragmentShaderBuilder  fFS;    // 片段着色器构建器
    std::unique_ptr<GrGeometryProcessor::ProgramImpl>  fGPImpl;
    std::unique_ptr<GrXferProcessor::ProgramImpl>      fXPImpl;
    std::vector<std::unique_ptr<GrFragmentProcessor::ProgramImpl>> fFPImpls;
};
```

名称混淆策略：使用 `_S<stage>` 后缀区分不同处理阶段，子处理器使用 `_c<index>` 后缀。例如第一个根 FP 的第三个子 FP 的变量名后缀为 `_S1_c2`。

### 5. GrGLSLUniformHandler - Uniform 变量管理器

```cpp
class GrGLSLUniformHandler {
public:
    struct UniformInfo {
        GrShaderVar        fVariable;   // 变量声明
        uint32_t           fVisibility; // 可见性标志（顶点/片段着色器）
        const GrProcessor* fOwner;      // 所属处理器
        SkString           fRawName;    // 未混淆的原始名称
    };

    // 添加单个 uniform
    UniformHandle addUniform(const GrProcessor* owner, uint32_t visibility,
                             SkSLType type, const char* name,
                             const char** outName = nullptr);

    // 添加 uniform 数组
    UniformHandle addUniformArray(const GrProcessor* owner, uint32_t visibility,
                                  SkSLType type, const char* name,
                                  int arrayCount, const char** outName = nullptr);

    // 查找与提升
    GrShaderVar getUniformMapping(const GrProcessor& owner, SkString rawName) const;
    GrShaderVar liftUniformToVertexShader(const GrProcessor& owner, SkString rawName);
};
```

以 `GR_NO_MANGLE_PREFIX`（"sk_"）开头的变量名不会被混淆，用于系统内置 uniform。

### 6. GrGLSLVaryingHandler - Varying 变量管理器

```cpp
class GrGLSLVarying {
public:
    enum class Scope {
        kVertToFrag,  // 顶点 -> 片段
        kVertToGeo,   // 顶点 -> 几何（已弃用）
        kGeoToFrag    // 几何 -> 片段（已弃用）
    };

    const char* vsOut() const;  // 顶点着色器中的输出变量名
    const char* fsIn() const;   // 片段着色器中的输入变量名
};

class GrGLSLVaryingHandler {
public:
    enum class Interpolation {
        kInterpolated,  // 标准插值
        kCanBeFlat,     // 可选 flat（如果更快则使用）
        kMustBeFlat     // 强制 flat（即使已知较慢）
    };

    void setNoPerspective();  // 禁用透视校正插值
    void addVarying(const char* name, GrGLSLVarying*, Interpolation);
    void addPassThroughAttribute(const GrShaderVar& vsVar, const char* output, ...);
    void emitAttributes(const GrGeometryProcessor&);
    void finalize();
};
```

注意：由于 Metal 不支持 varying 矩阵类型，框架禁止所有后端使用矩阵类型的 varying。

### 7. GrGLSLProgramDataManager - 运行时数据管理器

在着色器程序编译后负责将 CPU 端数据上传到 GPU uniform：

```cpp
class GrGLSLProgramDataManager {
public:
    // 标量和向量上传
    virtual void set1f(UniformHandle, float v0) const = 0;
    virtual void set2f(UniformHandle, float, float) const = 0;
    virtual void set3f(UniformHandle, float, float, float) const = 0;
    virtual void set4f(UniformHandle, float, float, float, float) const = 0;

    // 矩阵上传（列主序）
    virtual void setMatrix2f(UniformHandle, const float matrix[]) const = 0;
    virtual void setMatrix3f(UniformHandle, const float matrix[]) const = 0;
    virtual void setMatrix4f(UniformHandle, const float matrix[]) const = 0;

    // Skia 类型便利方法
    void setSkMatrix(UniformHandle, const SkMatrix&) const;
    void setSkM44(UniformHandle, const SkM44&) const;

    // 运行时效果 uniform 批量上传，支持特化标记跳过
    void setRuntimeEffectUniforms(SkSpan<const SkRuntimeEffect::Uniform>,
                                  SkSpan<const UniformHandle>,
                                  SkSpan<const Specialized>,
                                  const void* src) const;
};
```

### 8. GrGLSLBlend - 混合模式辅助

生成混合模式的 SkSL 表达式代码：

```cpp
namespace GrGLSLBlend {
    // 生成混合表达式字符串
    std::string BlendExpression(const GrProcessor* processor,
                                GrGLSLUniformHandler* uniformHandler,
                                GrGLSLProgramDataManager::UniformHandle* uniform,
                                const char* srcColor, const char* dstColor,
                                SkBlendMode mode);

    // 生成缓存键
    int BlendKey(SkBlendMode mode);

    // 设置运行时 uniform 数据
    void SetBlendModeUniformData(const GrGLSLProgramDataManager& pdman,
                                 UniformHandle uniform, SkBlendMode mode);
}
```

### 9. GrGLSLColorSpaceXformHelper - 色彩空间变换辅助

管理颜色空间变换所需的所有 uniform，包括源传递函数（SrcTF）、色域变换矩阵（GamutXform）和目标传递函数（DstTF）：

```cpp
class GrGLSLColorSpaceXformHelper {
public:
    // 声明所需的 uniform
    void emitCode(GrGLSLUniformHandler*, const GrColorSpaceXform*,
                  uint32_t visibility = kFragment_GrShaderFlag);

    // 上传 uniform 数据
    void setData(const GrGLSLProgramDataManager&, const GrColorSpaceXform*);

    // 查询各步骤是否需要
    bool isNoop() const;
    bool applyUnpremul() const;
    bool applySrcTF() const;
    bool applyGamutXform() const;
    bool applyDstTF() const;
    bool applyPremul() const;
};
```

## 依赖关系

### 上游依赖（被谁使用）

| 上游模块 | 说明 |
|---------|------|
| `src/gpu/ganesh/effects/` | 所有效果处理器的 ProgramImpl 使用此框架生成着色器代码 |
| `src/gpu/ganesh/GrFragmentProcessor` | FP 基类的 ProgramImpl 使用 `GrGLSLFPFragmentBuilder` |
| `src/gpu/ganesh/GrGeometryProcessor` | GP 基类的 ProgramImpl 使用 `GrGLSLVertexBuilder` |
| `src/gpu/ganesh/GrXferProcessor` | XP 基类的 ProgramImpl 使用 `GrGLSLXPFragmentBuilder` |
| `src/gpu/ganesh/gl/GrGLProgramBuilder` | OpenGL 后端的程序构建器 |
| `src/gpu/ganesh/vk/GrVkPipelineStateBuilder` | Vulkan 后端的管线状态构建器 |
| `src/gpu/ganesh/mtl/GrMtlPipelineStateBuilder` | Metal 后端的管线状态构建器 |
| `src/gpu/ganesh/d3d/GrD3DPipelineStateBuilder` | Direct3D 后端的管线状态构建器 |
| `src/gpu/ganesh/dawn/GrDawnProgramBuilder` | Dawn/WebGPU 后端的程序构建器 |

### 下游依赖（依赖谁）

| 下游模块 | 说明 |
|---------|------|
| `src/gpu/ganesh/GrProcessor.h` | 处理器基类 |
| `src/gpu/ganesh/GrPipeline.h` | 渲染管线 |
| `src/gpu/ganesh/GrProgramInfo.h` | 程序信息 |
| `src/gpu/ganesh/GrProgramDesc.h` | 程序描述符（缓存键） |
| `src/gpu/ganesh/GrCaps.h` / `GrShaderCaps.h` | GPU/着色器能力查询 |
| `src/gpu/ganesh/GrShaderVar.h` | 着色器变量描述 |
| `src/gpu/ganesh/GrResourceHandle.h` | 资源句柄类型 |
| `src/gpu/ganesh/GrColorSpaceXform.h` | 颜色空间变换 |
| `src/gpu/Swizzle.h` | 通道重排 |
| `src/core/SkSLTypeShared.h` | SkSL 类型定义 |
| `src/sksl/` | SkSL 编译器基础设施 |

### 外部依赖

- **skcms**：`GrGLSLColorSpaceXformHelper` 使用 skcms 的传递函数类型
- **SkSL IR**：`GrGLSLShaderBuilder` 持有 `SkSL::StatementArray`

## 设计模式分析

### 1. 模板方法模式 (Template Method)

`GrGLSLProgramBuilder::emitAndInstallProcs()` 定义了着色器程序生成的骨架算法，子类通过重写 `uniformHandler()`、`varyingHandler()` 等方法提供后端特定的行为：

```
emitAndInstallProcs()
  ├─ emitAndInstallPrimProc()     // 发射几何处理器代码
  ├─ emitAndInstallFragProcs()    // 发射片段处理器链代码
  ├─ emitAndInstallXferProc()     // 发射混合传输处理器代码
  └─ finalizeShaders()            // 最终化着色器
```

### 2. 建造者模式 (Builder)

`GrGLSLShaderBuilder` 是典型的建造者模式。着色器代码的各个部分（扩展、定义、uniform、函数、主代码）按顺序构建，最后通过 `finalize()` 拼接为完整的着色器字符串：

```cpp
builder.defineConstant("float", "kEpsilon", "0.001");
builder.emitFunction(returnType, mangledName, args, body);
builder.codeAppendf("half4 color = %s;", inputColor);
builder.finalize(visibility);
```

### 3. 抽象工厂模式 (Abstract Factory)

`GrGLSLProgramBuilder` 定义了创建 uniform handler 和 varying handler 的抽象接口，各 GPU 后端提供具体实现。这使得同一套代码生成逻辑可以工作在不同后端上。

### 4. 访问者模式 (Visitor)

`emitAndInstallFragProcs` 遍历 FP 树时，先递归写出所有子 FP 的函数（`writeChildFPFunctions`），再写父 FP 的函数。这本质上是树的后序遍历模式。

### 5. 虚拟菱形继承

`GrGLSLFragmentShaderBuilder` 使用虚拟继承同时实现 `GrGLSLFPFragmentBuilder` 和 `GrGLSLXPFragmentBuilder` 两个接口，使得 FP 和 XP 可以使用各自独立的接口来操作同一个片段着色器构建器实例。

### 6. 句柄模式 (Handle)

`UniformHandle` 和 `SamplerHandle` 是类型安全的资源句柄，通过 `GR_DEFINE_RESOURCE_HANDLE_CLASS` 宏定义。处理器持有句柄来引用已声明的 uniform 或采样器，而非直接操作底层资源。

## 数据流

```
1. 着色器程序构建开始
   GrGLSLProgramBuilder(GrProgramDesc, GrProgramInfo)
        │
        v
2. 几何处理器代码发射
   emitAndInstallPrimProc()
   ├─ GP.makeProgramImpl() -> 创建 GP::Impl
   ├─ Impl.emitCode(vertBuilder, fragBuilder, varyingHandler,
   │                 uniformHandler, shaderCaps, ...)
   │   ├─ varyingHandler.emitAttributes(gp)     // 顶点属性
   │   ├─ uniformHandler.addUniform(...)         // GP uniform
   │   ├─ vertBuilder.codeAppendf(...)           // 顶点着色器代码
   │   └─ vertBuilder.emitNormalizedSkPosition() // 标准化位置输出
   └─ advanceStage()
        │
        v
3. 片段处理器树代码发射
   emitAndInstallFragProcs()
   对于每个根 FP:
   ├─ writeChildFPFunctions(fp)   // 递归: 先子后父
   │   ├─ 对每个子 FP 递归调用
   │   └─ writeFPFunction(fp)
   │       ├─ FP.onMakeProgramImpl() -> 创建 FP::Impl
   │       ├─ emitTextureSamplersForFPs()  // 纹理采样器
   │       └─ Impl.emitCode(EmitArgs{fragBuilder, uniformHandler, ...})
   │           ├─ fragBuilder.codeAppendf(...)
   │           └─ fragBuilder.appendTextureLookup(...)
   └─ emitRootFragProc(fp, input, output)
       └─ invokeFP() -> 生成 "FPname_S1(inputColor, destColor, coords)" 调用
        │
        v
4. 混合传输处理器代码发射
   emitAndInstallXferProc()
   ├─ XP.makeProgramImpl() -> 创建 XP::Impl
   └─ Impl.emitCode(fragBuilder, uniformHandler, ...)
       ├─ fragBuilder.enableAdvancedBlendEquationIfNeeded()
       └─ fragBuilder.codeAppendf("sk_FragColor = ...")
        │
        v
5. 着色器最终化
   finalizeShaders()
   ├─ fVS.finalize(kVertex_GrShaderFlag)
   │   └─ 拼接: extensions + definitions + precision + layout
   │      + uniforms + inputs + outputs + functions + main + code...
   └─ fFS.finalize(kFragment_GrShaderFlag)
       └─ 同上拼接
        │
        v
6. 后端编译
   各后端编译器将最终化的着色器字符串编译为:
   ├─ GL: glShaderSource() + glCompileShader()
   ├─ Vulkan: SkSL -> SPIR-V
   ├─ Metal: SkSL -> MSL
   └─ Dawn: SkSL -> WGSL
        │
        v
7. 运行时数据上传
   每帧 / 每次绘制:
   GrGLSLProgramDataManager.set*() 上传 uniform 值
   ├─ GP::Impl.setData(pdman, gp)
   ├─ FP::Impl.setData(pdman, fp)  // 递归
   └─ XP::Impl.setData(pdman, xp)
```

## 相关文档与参考

### 相关目录

| 路径 | 说明 |
|------|------|
| `src/gpu/ganesh/effects/` | GPU 效果处理器，使用此框架生成着色器代码 |
| `src/gpu/ganesh/GrFragmentProcessor.h` | FP 基类，定义 ProgramImpl 接口 |
| `src/gpu/ganesh/GrGeometryProcessor.h` | GP 基类，定义 ProgramImpl 和 EmitArgs |
| `src/gpu/ganesh/GrXferProcessor.h` | XP 基类，定义 ProgramImpl |
| `src/gpu/ganesh/GrPipeline.h` | 渲染管线，组装所有处理器 |
| `src/gpu/ganesh/GrShaderCaps.h` | 着色器能力查询（导数支持、整数支持等） |
| `src/gpu/ganesh/gl/builders/` | OpenGL 后端的具体 builder 实现 |
| `src/gpu/ganesh/vk/` | Vulkan 后端实现 |
| `src/gpu/ganesh/mtl/` | Metal 后端实现 |
| `src/sksl/` | SkSL 编译器，将生成的代码编译为各后端格式 |
| `src/gpu/ganesh/GrColorSpaceXform.h` | 色彩空间变换数据，配合 ColorSpaceXformHelper |

### 文件功能速查表

| 文件名 | 核心类 | 功能 |
|--------|--------|------|
| `GrGLSLShaderBuilder.h/cpp` | `GrGLSLShaderBuilder` | 着色器代码分段构建与拼接 |
| `GrGLSLFragmentShaderBuilder.h/cpp` | `GrGLSLFragmentShaderBuilder` | 片段着色器构建，FP/XP 双接口 |
| `GrGLSLVertexGeoBuilder.h/cpp` | `GrGLSLVertexBuilder` | 顶点着色器构建，位置标准化 |
| `GrGLSLProgramBuilder.h/cpp` | `GrGLSLProgramBuilder` | 程序级构建协调，阶段管理 |
| `GrGLSLProgramDataManager.h/cpp` | `GrGLSLProgramDataManager` | 运行时 uniform 数据上传 |
| `GrGLSLUniformHandler.h/cpp` | `GrGLSLUniformHandler` | uniform 声明、混淆、查找 |
| `GrGLSLVarying.h/cpp` | `GrGLSLVarying`, `GrGLSLVaryingHandler` | varying 变量管理与插值控制 |
| `GrGLSLBlend.h/cpp` | `GrGLSLBlend` | 混合模式 SkSL 代码生成 |
| `GrGLSLColorSpaceXformHelper.h` | `GrGLSLColorSpaceXformHelper` | 色彩空间变换 uniform 管理 |

### 关键设计约束

1. **名称混淆**：所有 uniform 和函数名在生成时都会被添加阶段后缀以避免命名冲突。以 `sk_` 前缀开头的名称免于混淆。
2. **矩阵 varying 禁止**：由于 Metal 的限制，所有后端都不允许使用矩阵类型的 varying。
3. **抽象纯虚接口**：`uniformHandler()`、`varyingHandler()` 等为纯虚函数，必须由具体后端实现。
4. **两阶段生命周期**：着色器构建（编译时逻辑）和数据上传（每帧逻辑）严格分离，分别由 Builder 和 DataManager 负责。
