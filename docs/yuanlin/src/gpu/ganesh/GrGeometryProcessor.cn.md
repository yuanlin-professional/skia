# GrGeometryProcessor 学习笔记

> 源文件
> - src/gpu/ganesh/GrGeometryProcessor.h
> - src/gpu/ganesh/GrGeometryProcessor.cpp

## 1. 类定义与继承关系

- **头文件**: `src/gpu/ganesh/GrGeometryProcessor.h`
- **实现文件**: `src/gpu/ganesh/GrGeometryProcessor.cpp`
- **继承**: `GrGeometryProcessor : public GrProcessor`

```
GrProcessor (基类)
    └── GrGeometryProcessor (几何处理器)
            ├── ProgramImpl (着色器实现)
            ├── Attribute (顶点/实例属性)
            ├── AttributeSet (属性集合)
            └── TextureSampler (纹理采样器)
```

GrGeometryProcessor 代表某种几何图元，负责向 Ganesh 渲染管线提供颜色（color）和覆盖度（coverage）输入。它**不是纯虚类**本身，但包含纯虚方法，必须由子类实现。

所有子类应隐藏构造函数，提供 `Make` 工厂函数（接受 `SkArenaAlloc*`）。

它与以下组件紧密协作：
- `GrFragmentProcessor`: 接收 GP 输出的颜色和坐标
- `GrPipeline`: 组装完整的渲染管线
- `GrOpsRenderPass`: 执行渲染命令
- GLSL 代码生成器：生成特定后端的着色器代码

## 2. 纯虚方法（子类必须实现）

| 方法 | 位置 | 作用 |
|------|------|------|
| `addToKey(const GrShaderCaps&, skgpu::KeyBuilder*) const` | .h:223 | 生成 shader 缓存 key，反映该 GP 可能发出的代码变体 |
| `makeProgramImpl(const GrShaderCaps&) const` | .h:231 | 创建对应的 `ProgramImpl` 实例，用于 shader 代码生成 |
| `ProgramImpl::setData(...)` | .h:341 | 从 GP 读取数据更新 shader uniform 变量 |
| `ProgramImpl::onEmitCode(EmitArgs&, GrGPArgs*)` | .h:438 | 子类特定的 shader 代码生成逻辑 |

## 3. 核心内部类

### 3.1 Attribute（.h:78-139）

描述顶点或实例属性：name、cpuType、gpuType、offset。支持隐式偏移（按声明顺序自动计算）和显式偏移。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fName` | `const char*` | 属性名称 |
| `fCPUType` | `GrVertexAttribType` | CPU 端数据类型 |
| `fGPUType` | `SkSLType` | GPU 端着色器类型 |
| `fOffset` | `uint32_t` | 内存偏移量（可隐式计算）|

### 3.2 AttributeSet（.h:146-189）

属性集合容器，提供迭代器，自动跳过未初始化的属性。通过 `initImplicit()` 或 `initExplicit()` 初始化。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fAttributes` | `const Attribute*` | 属性数组指针 |
| `fCount` | `int` | 已初始化属性数量 |
| `fStride` | `size_t` | 顶点/实例步长 |

两种初始化模式：
1. **隐式偏移模式**：自动计算属性偏移和步长，确保 4 字节对齐
2. **显式偏移模式**：手动指定每个属性的偏移和总步长

属性迭代器 `Iter` 实现特殊逻辑：跳过未初始化的属性，动态计算或使用预设偏移量。

### 3.3 TextureSampler（.h:480-507）

捕获纹理属性：采样状态、后端格式、通道重排（swizzle）。

注意：TextureSampler **不包含纹理代理**，实际纹理代理存储在 Op 的固定或动态状态数组中。TextureSampler 只描述采样属性和格式要求，这允许在不同渲染通道间复用相同的 GP 定义。

### 3.4 ProgramImpl（.h:273-470）

Shader 代码生成的核心抽象类，包含：
- `EmitArgs` 结构：携带 vertex/fragment builder、varying/uniform handler 等
- `GrGPArgs` 结构：输出 `fPositionVar`（设备坐标）和 `fLocalCoordVar`（局部坐标）
- 静态辅助方法：`WriteOutputPosition()`、`WriteLocalCoord()`、`SetTransform()`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fTransformVaryingsMap` | `std::unordered_map` | 坐标变换 varying 映射 |
| `fFunctionName` | `SkString` | 着色器函数名 |
| `fChildProcessors` | `TArray<ProgramImpl*>` | 子处理器实现 |

## 4. FPCoordsMap 与 collectTransforms 机制

这是 GrGeometryProcessor 中最复杂的部分，负责**将 FragmentProcessor 的坐标变换从片元着色器提升到顶点着色器**（性能优化）。

### 4.1 数据结构

```cpp
// .h:282-283
struct FPCoords {
    GrShaderVar coordsVarying;  // 替代输入坐标的 varying 变量
    bool hasCoordsParam;         // FP 是否需要坐标参数
};
using FPCoordsMap = std::unordered_map<const GrFragmentProcessor*, FPCoords>;
```

```cpp
// .h:454-461 - ProgramImpl 内部
struct TransformInfo {
    GrGLSLVarying varying;      // 传递坐标到 FS 的 varying
    GrShaderVar   inputCoords;  // 被变换的原始坐标
    int           traversalOrder; // 用于排序，确保祖先 FP 的 varying 先于后代初始化
};
std::unordered_map<const GrFragmentProcessor*, TransformInfo> fTransformVaryingsMap;
```

### 4.2 执行流程

**`emitCode()`**（.cpp:84-108）中调用 `collectTransforms()`：

```
emitCode()
  ├── onEmitCode()           // 子类生成 GP 特定的 shader 代码，设置 gpArgs
  ├── collectTransforms()    // 遍历 FP 树，决定哪些坐标变换可以提升到 VS
  │     → 返回 FPCoordsMap（transformMap）
  └── emitNormalizedSkPosition()  // 输出顶点位置
```

### 4.3 collectTransforms 详解（.cpp:110-242）

**目的**：前序遍历 pipeline 中所有 FragmentProcessor，识别使用矩阵变换局部坐标的 FP，为它们生成 varying，从而在顶点着色器中完成坐标变换（而非逐像素计算）。

**遍历逻辑**（`liftTransforms` lambda）：

对每个 FP，根据其 `sampleUsage().kind()` 分类处理：

| SampleUsage::Kind | 处理 |
|---|---|
| `kNone` | 只出现在根节点 |
| `kPassThrough` | 透传，不影响变换链 |
| `kUniformMatrix` | 更新 `lastMatrixFP`，记录矩阵变换 |
| `kFragCoord` | 切换基坐标为设备坐标（`BaseCoord::kPosition`），重置矩阵链 |
| `kExplicit` | 显式采样，无法提升（`BaseCoord::kNone`） |

**实现关键点**：
```cpp
// Lambda 递归遍历 FP 树
auto liftTransforms = [&, traversalIndex = 0](
    auto& self, const GrFragmentProcessor& fp,
    bool hasPerspective,
    const GrFragmentProcessor* lastMatrixFP = nullptr,
    int lastMatrixTraversalIndex = -1,
    BaseCoord baseCoord = BaseCoord::kLocal) mutable -> void {
    // 根据采样类型更新追踪状态
    switch (fp.sampleUsage().kind()) {
        case SkSL::SampleUsage::Kind::kUniformMatrix:
            lastMatrixFP = &fp;
            lastMatrixTraversalIndex = traversalIndex;
            break;
        case SkSL::SampleUsage::Kind::kFragCoord:
            baseCoord = BaseCoord::kPosition;
            break;
        // ...
    }

    // 决定是否创建 varying
    if (fp.usesSampleCoordsDirectly() && should_create_varying) {
        // 查找或创建共享的 varying
        auto& [varying, inputCoords, idx] = fTransformVaryingsMap[lastMatrixFP];
        // ...
    }

    // 递归处理子 FP
    for (int c = 0; c < fp.numChildProcessors(); ++c) {
        self(self, *fp.childProcessor(c), ...);
    }
};
```

**Varying 共享优化**：
- 如果多个 FP 共享相同的矩阵变换链（到 `lastMatrixFP` 的路径相同），它们复用同一个 varying
- 通过 `fTransformVaryingsMap` 按 `lastMatrixFP` 去重

**结果**：
- `FPCoordsMap`（返回给调用方）：每个 FP 对应一个 `FPCoords`，告知 FP 使用哪个 varying 作为坐标输入
- `fTransformVaryingsMap`（内部保存）：记录需要在 VS 中计算的 varying 及其变换矩阵

### 4.4 emitTransformCode（.cpp:244-328）

在所有 FP 的 `emitCode()` 完成后调用。按遍历顺序（优先队列）为 `fTransformVaryingsMap` 中的每个条目生成顶点着色器代码：

1. 获取 FP 的 uniform 矩阵
2. 向上遍历 FP 树，累积矩阵乘法表达式（或找到已有 varying 作为输入）
3. 生成 `varying_out = matrixExpr * inputCoords` 代码
4. 处理透视/非透视、float2/float3、是否支持非方阵等情况

```cpp
std::priority_queue<FPAndInfo, std::vector<FPAndInfo>, decltype(compare)> pq(compare);

for (; !pq.empty(); pq.pop()) {
    const auto& [fp, info] = pq.top();
    // 构建变换表达式：matrix1 * matrix2 * ... * input
    SkString transformExpression = uniform.getName();

    // 向上遍历 FP 树累积矩阵
    for (const auto* base = fp->parent(); base; base = base->parent()) {
        if (base->sampleUsage().isUniformMatrix()) {
            transformExpression.appendf(" * %s", parentUniform.getName().c_str());
        }
    }

    // 发射着色器代码
    vb->codeAppendf("%s = %s * %s", info.varying.vsOut(),
                    transformExpression.c_str(), inputStr.c_str());
}
```

## 5. 具体子类（14+ 个）

**文本渲染**：
- `GrBitmapTextGeoProc` — `src/gpu/ganesh/effects/GrBitmapTextGeoProc.h`
- `GrDistanceFieldA8TextGeoProc` / `GrDistanceFieldLCDTextGeoProc` / `GrDistanceFieldPathGeoProc` — `src/gpu/ganesh/effects/GrDistanceFieldGeoProc.h`

**形状渲染**：
- `GrConicEffect` / `GrQuadEffect` — `src/gpu/ganesh/effects/GrBezierEffect.h`
- `GrRRectShadowGeoProc` — `src/gpu/ganesh/effects/GrShadowGeoProc.h`

**曲面细分**（通过 GrTessellationShader 间接继承）：
- `GrPathTessellationShader` — `src/gpu/ganesh/tessellate/GrPathTessellationShader.h`
- `GrStrokeTessellationShader` — `src/gpu/ganesh/tessellate/GrStrokeTessellationShader.h`

**Ops 内部定义的**：
- `QuadPerEdgeAAGeometryProcessor` — `src/gpu/ganesh/ops/QuadPerEdgeAA.cpp`（最常用，处理矩形/四边形）
- `DashingCircleEffect` / `DashingLineEffect` — `src/gpu/ganesh/ops/DashOp.cpp`
- `FillRRectOpImpl::Processor` — `src/gpu/ganesh/ops/FillRRectOp.cpp`
- `DrawAtlasPathShader` — `src/gpu/ganesh/ops/DrawAtlasPathOp.cpp`

## 6. 在渲染管线中的完整使用流程

```
┌────────────────────────────────────────────────────────────────────────┐
│  GrDrawOp (如 FillRectOp)                                              │
│  ├── onCreateProgramInfo()                                             │
│  │   ├── 创建 GrGeometryProcessor (通过 Make 工厂函数, arena 分配)       │
│  │   └── 封装进 GrProgramInfo (持有 GP + Pipeline + PrimitiveType)      │
│  └── onExecute()                                                       │
│      ├── flushState->bindPipelineAndScissorClip(*fProgramInfo, ...)    │
│      ├── flushState->bindTextures(fProgramInfo->geomProc(), ...)       │
│      └── 发出 draw call                                                │
└────────────────────────────────────────────────────────────────────────┘

Shader 编译阶段：
  GrProgramInfo.geomProc().makeProgramImpl()
    → ProgramImpl.emitCode()
      → onEmitCode()          // GP 子类生成 VS/FS 代码
      → collectTransforms()   // 生成 FPCoordsMap (transformMap)
      → emitNormalizedSkPosition()
    → 返回 (FPCoordsMap, localCoordVar)
  各 FP.emitCode()            // 使用 FPCoordsMap 中的 varying 作为坐标
  ProgramImpl.emitTransformCode()  // 生成 VS 中的坐标变换代码
```

### 关键代码路径

**创建 GP**（以 FillRectOp 为例）— `src/gpu/ganesh/ops/FillRectOp.cpp:241`：
```cpp
GrGeometryProcessor* gp = skgpu::ganesh::QuadPerEdgeAA::MakeProcessor(arena, vertexSpec);
```

**封装到 ProgramInfo** — `src/gpu/ganesh/ops/FillRectOp.cpp:244`：
```cpp
fProgramInfo = fHelper.createProgramInfoWithStencil(caps, arena, ..., gp, ...);
```

**GrProgramInfo 持有 GP** — `src/gpu/ganesh/GrProgramInfo.h:90`：
```cpp
const GrGeometryProcessor* fGeomProc;
```

**执行绘制** — `src/gpu/ganesh/ops/FillRectOp.cpp:328-352`：
```cpp
flushState->bindPipelineAndScissorClip(*fProgramInfo, chainBounds);
flushState->bindTextures(fProgramInfo->geomProc(), nullptr, fProgramInfo->pipeline());
```

## 7. 公共 API 函数

### 属性管理

```cpp
// 获取属性信息
int numVertexAttributes() const;
int numInstanceAttributes() const;
const AttributeSet& vertexAttributes() const;
const AttributeSet& instanceAttributes() const;
size_t vertexStride() const;
size_t instanceStride() const;

// 设置属性（受保护方法供子类使用）
void setVertexAttributes(const Attribute* attrs, int count, size_t stride);
void setInstanceAttributes(const Attribute* attrs, int count, size_t stride);
void setVertexAttributesWithImplicitOffsets(const Attribute* attrs, int count);
void setInstanceAttributesWithImplicitOffsets(const Attribute* attrs, int count);
```

### 纹理采样器

```cpp
int numTextureSamplers() const;
const TextureSampler& textureSampler(int index) const;
void setTextureSamplerCnt(int cnt);
```

### 着色器代码生成

```cpp
// 生成 ProgramImpl 实例
virtual std::unique_ptr<ProgramImpl> makeProgramImpl(const GrShaderCaps&) const = 0;

// 添加到着色器 key
virtual void addToKey(const GrShaderCaps&, skgpu::KeyBuilder*) const = 0;
void getAttributeKey(skgpu::KeyBuilder* b) const;

// 计算坐标变换 key
static uint32_t ComputeCoordTransformsKey(const GrFragmentProcessor& fp);
```

### ProgramImpl 核心方法

```cpp
// 发射着色器代码
std::tuple<FPCoordsMap, GrShaderVar> emitCode(EmitArgs&, const GrPipeline&);

// 发射变换代码
void emitTransformCode(GrGLSLVertexBuilder*, GrGLSLUniformHandler*);

// 设置 uniform 数据
virtual void setData(const GrGLSLProgramDataManager&,
                     const GrShaderCaps&,
                     const GrGeometryProcessor&) = 0;

// 辅助方法：输出位置
static void WriteOutputPosition(GrGLSLVertexBuilder*, GrGPArgs*, const char* posName);
static void WriteOutputPosition(GrGLSLVertexBuilder*, GrGLSLUniformHandler*,
                                const GrShaderCaps&, GrGPArgs*, const char* posName,
                                const SkMatrix& viewMatrix, UniformHandle* viewMatrixUniform);

// 辅助方法：局部坐标
static void WriteLocalCoord(GrGLSLVertexBuilder*, GrGLSLUniformHandler*,
                            const GrShaderCaps&, GrGPArgs*, GrShaderVar localVar,
                            const SkMatrix& localMatrix, UniformHandle* localMatrixUniform);
```

### 工具方法

```cpp
// 创建颜色属性
static Attribute MakeColorAttribute(const char* name, bool wideColor);

// 计算矩阵 key
static uint32_t ComputeMatrixKey(const GrShaderCaps& caps, const SkMatrix& mat);
static uint32_t ComputeMatrixKeys(const GrShaderCaps&, const SkMatrix& view,
                                  const SkMatrix& local);
static uint32_t AddMatrixKeys(const GrShaderCaps&, uint32_t flags,
                              const SkMatrix& view, const SkMatrix& local);

// 设置变换矩阵
static void SetTransform(const GrGLSLProgramDataManager&, const GrShaderCaps&,
                        const UniformHandle&, const SkMatrix&, SkMatrix* state = nullptr);
```

## 8. 内存管理

所有 GP 通过 `SkArenaAlloc` 分配，生命周期绑定到 arena（DDL 录制期间或单次 flush 期间），统一释放，无需手动 delete。

```cpp
class MyGeometryProcessor : public GrGeometryProcessor {
private:
    MyGeometryProcessor(...) : INHERITED(...) {}
public:
    static GrGeometryProcessor* Make(SkArenaAlloc* arena, ...) {
        return arena->make<MyGeometryProcessor>(...);
    }
};
```

## 9. 核心设计思想

| 组件 | 职责 |
|------|------|
| **GrDrawOp** | 定义"画什么"（几何数据） |
| **GrGeometryProcessor** | 定义"顶点怎么处理"（属性布局 + VS 代码） |
| **GrFragmentProcessor** (Pipeline) | 定义"像素怎么着色"（FS 代码） |
| **GrProgramInfo** | 将以上三者组合，提交给 GPU 执行 |

`collectTransforms` / `FPCoordsMap` 机制是连接 GP 和 FP 的桥梁——它让 GP 在顶点着色器阶段就为 FP 预计算好坐标变换，避免在片元着色器中逐像素重复计算，是 Ganesh 管线的一个重要性能优化。

### 设计模式

**工厂模式**：所有 GP 子类应隐藏构造函数，提供静态 `Make` 工厂方法。GP 可能在记录时或刷新时的不同 arena 中创建，工厂方法允许调用者控制生命周期。

**策略模式**：`ProgramImpl` 作为策略对象，封装着色器代码生成逻辑。一个 GP 类对应一个 ProgramImpl 类，GP 实例在运行时可以复用 ProgramImpl，通过 key 系统确保兼容性。

**模板方法模式**：`ProgramImpl::emitCode` 定义代码生成流程：
1. 调用子类 `onEmitCode` 生成核心逻辑
2. 自动收集坐标变换信息（`collectTransforms`）
3. 发射位置到硬件（`emitNormalizedSkPosition`）
子类只需实现 `onEmitCode`，框架处理其余逻辑。

**迭代器模式**：`AttributeSet::Iter` 提供统一的属性遍历接口，隐藏底层存储细节（隐式/显式偏移）。

**优化反馈循环**：GP 参与两个反馈循环（在 `GrDrawOp` 和 `GrXferProcessor` 之间）：
1. **前向分析**：Op 提供初始颜色/覆盖率 → FP 处理 → XferProcessor 分析
2. **反向优化**：分析结果反馈给 Op → Op 根据结果优化 GP 创建

## 10. 性能考量

**属性对齐**：所有属性偏移强制 4 字节对齐（`Attribute::AlignOffset`），避免未对齐访问的性能损失。

**Varying 共享优化**：通过共享 varying 减少顶点到片段的插值数量——识别 FP 树中相同的变换链，将相同变换结果共享给多个 FP。

**矩阵优化**：针对不同矩阵类型的优化路径：
```cpp
if (matrix.isIdentity()) {
    // 无操作
} else if (matrix.isScaleTranslate()) {
    // 使用 float4 而非 float3x3，减少 uniform 大小和计算
} else if (!matrix.hasPerspective()) {
    // 使用 float2 输出而非 float3
} else {
    // 完整透视计算
}
```

**状态追踪**：`SetTransform` 支持可选的状态指针，如果矩阵未变化则跳过 uniform 更新，减少 GPU 命令流量。

**Key 计算效率**：属性和变换 key 使用位打包（`kCoordTransformKeyBits = 4`, `kMatrixKeyBits = 2`），紧凑的 key 提高着色器缓存命中率。

## 11. 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrProcessor` | 基类，提供处理器基础功能 |
| `GrFragmentProcessor` | 接收 GP 输出，处理颜色和纹理 |
| `GrPipeline` | 组装完整渲染管线 |
| `GrShaderCaps` | 查询着色器能力 |
| `GrGLSLVertexBuilder` | 构建顶点着色器代码 |
| `GrGLSLVaryingHandler` | 管理 varying 变量 |
| `GrGLSLUniformHandler` | 管理 uniform 变量 |
| `GrGLSLProgramDataManager` | 更新 uniform 数据 |
| `GrBackendFormat` | 后端纹理格式信息 |
| `GrSamplerState` | 采样器状态配置 |
| `skgpu::Swizzle` | 纹理通道重排 |
| `skgpu::KeyBuilder` | 构建着色器缓存 key |
| `SkMatrix` | 矩阵变换 |
| `SkSL::SampleUsage` | FP 采样使用信息 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| 具体 GP 子类 | 继承并实现几何处理逻辑 |
| `GrOpsRenderPass` | 使用 GP 执行绘制命令 |
| `GrPipeline` | 组装管线时使用 GP |
| `GrProgramInfo` | 封装 GP 和管线信息 |
| `GrGLSLProgramBuilder` | 使用 GP 生成着色器程序 |
| `GrDrawOp` | 创建和配置 GP 实例 |

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/ganesh/GrProcessor.h` | GP 基类定义 |
| `src/gpu/ganesh/GrFragmentProcessor.h` | 片段处理器，接收 GP 输出 |
| `src/gpu/ganesh/GrPipeline.h` | 渲染管线组装 |
| `src/gpu/ganesh/GrProgramInfo.h` | 封装 GP 和管线信息 |
| `src/gpu/ganesh/glsl/GrGLSLVertexGeoBuilder.h` | 顶点着色器构建器 |
| `src/gpu/ganesh/glsl/GrGLSLVarying.h` | Varying 变量管理 |
| `src/gpu/ganesh/glsl/GrGLSLUniformHandler.h` | Uniform 变量管理 |
| `src/gpu/ganesh/glsl/GrGLSLProgramDataManager.h` | Uniform 数据更新 |
| `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h` | 片段着色器构建器 |
| `src/gpu/ganesh/GrDrawOp.h` | 绘制操作，创建 GP |
| `src/gpu/ganesh/GrOpsRenderPass.h` | 渲染通道，使用 GP 执行绘制 |
| `src/gpu/ganesh/effects/GrBitmapTextGeoProc.h` | 位图文本 GP 子类 |
| `src/gpu/ganesh/effects/GrDistanceFieldGeoProc.h` | 距离场文本 GP 子类 |
| `src/gpu/ganesh/effects/GrBezierEffect.h` | 贝塞尔曲线 GP 子类 |
| `src/gpu/ganesh/effects/GrShadowGeoProc.h` | 圆角矩形阴影 GP 子类 |
| `src/gpu/ganesh/ops/QuadPerEdgeAA.cpp` | 最常用的四边形 GP |
| `src/gpu/ganesh/ops/FillRRectOp.cpp` | 填充圆角矩形 GP |

## 附录：为什么 FP 是树结构而 GP 不是

### 根本原因：GPU 管线中的数量约束

每次 draw call 只有**一个** GP，但可以有**多个** FP（颜色 FP + 覆盖度 FP），每个 FP 还能包含子 FP。

代码证据：
- `GrProgramInfo.h:49` — `const GrGeometryProcessor* fGeomProc`（单数指针）
- `GrPipeline.h` — `FragmentProcessorArray fFragmentProcessors`（数组，每个元素是一棵 FP 树的根）

```
一次 draw call 的结构：
  GrProgramInfo
  ├── 1 个 GrGeometryProcessor        ← 单个，不需要组合
  └── GrPipeline
      ├── N 个 color FP（每个是树根）  ← 可组合，需要树
      └── M 个 coverage FP（每个是树根）
```

### GP 不需要树的原因

GP 对应 GPU 的**顶点处理阶段**，其职责是：
1. 定义顶点/实例属性布局（position, color, texcoord...）
2. 生成顶点着色器代码（变换顶点位置、传递属性到 varying）

这些工作本质上是**不可组合的**——一个三角形的顶点属性布局就是固定的，不存在"把两种顶点布局嵌套组合"的需求。每种几何图元（矩形、文本、贝塞尔曲线）有自己专用的 GP 子类，彼此独立。

### FP 为什么不能只用列表？关键在于分支

很多 FP 组合确实是线性链（每个 FP 只有 1 个子 FP），比如：
```
ColorSpaceXformFP → ColorFilterFP → TextureEffectFP   （线性链）
HslToRgbFP → ColorMatrixFP → RgbToHslFP               （线性链）
```

如果只有这些场景，用一个扁平列表就够了。**但树结构存在的根本原因是：某些 FP 需要同时拥有多个独立的子 FP（真正的分支）。**

#### 真正的分支场景（一个父 FP 有 2+ 个子 FP）

**1. GrBlendFragmentProcessor — 2 个子 FP**（`src/gpu/ganesh/effects/GrBlendFragmentProcessor.cpp`）
```cpp
this->registerChild(std::move(src));  // 子 FP 0
this->registerChild(std::move(dst));  // 子 FP 1
// emitCode 中：
SkString srcColor = this->invokeChild(0, args);  // 独立求值 src
SkString dstColor = this->invokeChild(1, args);  // 独立求值 dst
// 然后 blend(srcColor, dstColor)
```
对应用户代码 `SkShaders::Blend(mode, shaderA, shaderB)`：
```
  BlendFragmentProcessor
  ├── ShaderA_FP (src)     ← 可以是任意复杂的子树
  └── ShaderB_FP (dst)     ← 可以是任意复杂的子树
```

**2. GrYUVtoRGBEffect — 2~4 个子 FP**（`src/gpu/ganesh/effects/GrYUVtoRGBEffect.cpp`）
```cpp
for (int i = 0; i < numPlanes; ++i) {
    this->registerChild(std::move(planeFPs[i]));  // 每个 YUV 平面一个子 FP
}
```
YUV 视频解码时，Y/U/V（可能还有 A）分别在不同纹理中，需要独立采样后合成 RGB。

**3. GrColorTableEffect — 2 个子 FP**（`src/gpu/ganesh/effects/GrColorTableEffect.cpp`）
```cpp
this->registerChild(GrTextureEffect::Make(...));  // 查找表纹理
this->registerChild(std::move(inputFP));           // 输入颜色
// 用输入颜色的 r/g/b/a 分量作为坐标去查找表纹理采样
```

**4. GrPerlinNoise2Effect — 2 个子 FP**（`src/gpu/ganesh/effects/GrPerlinNoise2Effect.h`）
```cpp
this->registerChild(std::move(permutationsFP));  // 排列表纹理
this->registerChild(std::move(noiseFP));          // 噪声纹理
```

#### 为什么列表做不到

列表是线性的：`FP_0 → FP_1 → FP_2 → ...`，每个节点只有一个后继。但 BlendFP 需要**同时、独立地**对两个子树求值，然后合并结果。这在列表中无法表达——你无法在一个扁平序列中表示"这两个子树是并行输入同一个父节点的"。

注意 `fChildProcessors` 的类型是 `STArray<1, ...>`，内联存储优化为 1 个元素（最常见的情况），但可以增长。这个设计也侧面印证：**大部分 FP 只有 0~1 个子节点（链式），但必须支持 2+ 个子节点（分支）的场景。**

### FP 树如何生成着色器代码

#### 步骤一：ProgramImpl 树镜像 FP 树

`GrFragmentProcessor::makeProgramImpl()`（`GrFragmentProcessor.cpp:130-138`）递归创建：

```cpp
std::unique_ptr<ProgramImpl> GrFragmentProcessor::makeProgramImpl() const {
    std::unique_ptr<ProgramImpl> impl = this->onMakeProgramImpl();
    impl->fChildProcessors.push_back_n(fChildProcessors.size());
    for (int i = 0; i < fChildProcessors.size(); ++i) {
        impl->fChildProcessors[i] = fChildProcessors[i]
            ? fChildProcessors[i]->makeProgramImpl() : nullptr;
    }
    return impl;
}
```

FP 树和 ProgramImpl 树是完全镜像的——每个 FP 节点对应一个 ProgramImpl 节点，子节点数量和顺序相同。

#### 步骤二：深度优先遍历，每个节点生成一个 GLSL 函数

`GrGLSLProgramBuilder::writeFPFunction()`（`glsl/GrGLSLProgramBuilder.cpp:245-328`）：

```cpp
void GrGLSLProgramBuilder::writeFPFunction(const GrFragmentProcessor& fp,
                                           GrFragmentProcessor::ProgramImpl& impl) {
    this->writeChildFPFunctions(fp, impl);  // 1. 先递归生成所有子节点的函数
    // ...
    impl.emitCode(args);                     // 2. 调用当前节点的 emitCode()
    impl.setFunctionName(fFS.getMangledFunctionName(fp.name()));
    fFS.emitFunction(SkSLType::kHalf4,       // 3. 把生成的代码包装成一个 GLSL 函数
                     impl.functionName(), params, fFS.code().c_str());
}
```

**关键**：先递归处理子节点（深度优先），确保子函数已经存在，然后父节点的 `emitCode()` 才能调用它们。

#### 步骤三：invokeChild() 生成函数调用字符串

`ProgramImpl::invokeChild()`（`GrFragmentProcessor.cpp:867-910`）：

```cpp
SkString ProgramImpl::invokeChild(int childIndex, const char* inputColor,
                                  const char* destColor, EmitArgs& args, ...) {
    // 返回类似 "child_func_S0_c0(_input)" 的函数调用字符串
    auto invocation = SkStringPrintf("%s(%s",
        this->childProcessor(childIndex)->functionName(), inputColor);
    if (childProc->isBlendFunction()) {
        invocation.appendf(", %s", destColor);
    }
    if (hasCoordsParam) {
        invocation.appendf(", %s", skslCoords);
    }
    invocation.append(")");
    return invocation;
}
```

`invokeChild()` **不执行**子 FP 的代码——它只返回一个函数调用字符串，父 FP 将这个字符串嵌入自己的代码中。

#### 步骤四：函数名 mangle 避免冲突

函数名通过 `_S<stage>_c<child>` 后缀 mangle（`GrGLSLProgramBuilder.cpp:486-494`）：
- `_S0` — pipeline 中第 0 个 FP 阶段
- `_c0`, `_c1` — 该 FP 的第 0、第 1 个子节点

#### 完整示例：BlendFP 树生成的 GLSL

FP 树：
```
BlendFP (SrcOver)          ← 根节点，2 个子节点
├── TextureEffectFP        ← 子节点 0 (src)
└── ColorFP(red)           ← 子节点 1 (dst)
```

生成的 GLSL（伪代码，简化）：
```glsl
// ① 最先生成：叶子节点的函数（深度优先）
half4 TextureEffect_S0_c0(half4 _input, float2 _coords) {
    return sample(u_sampler, _coords);
}

half4 Color_S0_c1(half4 _input) {
    return half4(1.0, 0.0, 0.0, 1.0);  // 常量红色
}

// ② 然后生成：父节点的函数
half4 Blend_S0(half4 _input) {
    half4 _src = TextureEffect_S0_c0(_input, _coords);  // invokeChild(0)
    half4 _dst = Color_S0_c1(_input);                    // invokeChild(1)
    return _src + _dst * (1 - _src.a);                   // SrcOver 混合
}
```

**核心思想**：FP 树中的每个节点变成一个独立的 GLSL 函数，父节点通过函数调用组合子节点的输出。树的深度优先遍历确保子函数在父函数之前定义。

对于 `GrBlendFragmentProcessor` 的实际 emitCode（`GrBlendFragmentProcessor.cpp:225-268`）：
```cpp
void emitCode(EmitArgs& args) override {
    SkString srcColor = this->invokeChild(0, args);   // → "TextureEffect_S0_c0(_input, _coords)"
    SkString dstColor = this->invokeChild(1, args);   // → "Color_S0_c1(_input)"
    std::string blendExpr = GrGLSLBlend::BlendExpression(
        ..., srcColor.c_str(), dstColor.c_str(), mode);
    fragBuilder->codeAppendf("return %s;", blendExpr.c_str());
}
```

### 类比总结

| | GrGeometryProcessor | GrFragmentProcessor |
|---|---|---|
| GPU 阶段 | 顶点处理 | 片元处理 |
| 每次 draw 数量 | 恰好 1 个 | 多个（每个可含子树） |
| 是否可组合 | 不可组合 | 天然可组合（嵌套效果） |
| 数据结构 | 单个对象（无 children） | 树（fChildProcessors + fParent） |
| 子类关系 | 继承多态（每种图元一个子类） | 继承 + 组合（树形嵌套） |

## 附录 B：SkSL 着色器拼接完整流程

### 总体流程图

```
GrGLProgramBuilder::CreateProgram()                    [gl/builders/GrGLProgramBuilder.cpp:62]
  │
  ├─ 1. emitAndInstallProcs()                          [glsl/GrGLSLProgramBuilder.cpp:61]
  │    │
  │    ├─ 1.1 emitAndInstallPrimProc()                 ── 几何处理器（VS + FS 颜色/覆盖度）
  │    │    ├─ advanceStage()                           ── fStageIndex → 0
  │    │    ├─ gp.makeProgramImpl()                    ── 创建 GP 的 ProgramImpl
  │    │    ├─ emitSampler() × N                       ── GP 纹理采样器 → uniform 声明
  │    │    └─ gpImpl->emitCode(args, pipeline)        [GrGeometryProcessor.cpp:84]
  │    │         ├─ onEmitCode(args, &gpArgs)          ── 子类写 VS/FS 代码
  │    │         │    → 设置 gpArgs.fPositionVar       ── 顶点位置变量
  │    │         │    → 设置 gpArgs.fLocalCoordVar     ── 局部坐标变量
  │    │         ├─ collectTransforms(pipeline)        [GrGeometryProcessor.cpp:110]
  │    │         │    └─ 前序遍历 FP 树               ── 分析哪些坐标变换可提升到 VS
  │    │         │       → 填充 fTransformVaryingsMap  ── 记录需要的 varying
  │    │         │       → 返回 FPCoordsMap            ── 每个 FP 的坐标来源
  │    │         └─ emitNormalizedSkPosition()         ── 输出标准化设备坐标
  │    │
  │    ├─ 1.2 emitAndInstallDstTexture()               [GrGLSLProgramBuilder.cpp:330]
  │    │    └─ 若需要 dst 纹理：创建采样器、计算采样坐标、声明 _dstColor
  │    │
  │    ├─ 1.3 emitAndInstallFragProcs()                [GrGLSLProgramBuilder.cpp:135]
  │    │    └─ 对每个根 FP：
  │    │         ├─ advanceStage()                     ── fStageIndex → 1, 2, 3...
  │    │         ├─ fp.makeProgramImpl()               ── 递归创建 FP + 子 FP 的 ProgramImpl
  │    │         └─ emitRootFragProc()                 [GrGLSLProgramBuilder.cpp:198]
  │    │              ├─ emitTextureSamplersForFPs()   ── 递归遍历 FP 树，为每个纹理创建采样器
  │    │              ├─ writeChildFPFunctions()       ── 递归（后序）先生成子 FP 函数
  │    │              └─ writeFPFunction()             [GrGLSLProgramBuilder.cpp:245]
  │    │                   ├─ writeChildFPFunctions()  ── 确保子函数已定义
  │    │                   ├─ 分析坐标需求（查 FPCoordsMap）
  │    │                   ├─ impl.emitCode(args)      ── FP 子类写 FS 代码
  │    │                   └─ fFS.emitFunction(...)    ── 包装成 half4 func_SN(...) 函数
  │    │
  │    ├─ 1.4 emitAndInstallXferProc()                 [GrGLSLProgramBuilder.cpp:405]
  │    │    ├─ advanceStage()                          ── fStageIndex → N（最后阶段）
  │    │    ├─ xp.makeProgramImpl()
  │    │    └─ xpImpl->emitCode(args)                 ── 混合最终颜色 + 覆盖度 → sk_FragColor
  │    │
  │    └─ 1.5 gpImpl->emitTransformCode()             [GrGeometryProcessor.cpp:244]
  │         └─ 遍历 fTransformVaryingsMap              ── 为每个 lifted varying 生成 VS 代码
  │              └─ varying_out = matrix * inputCoords ── 在 VS 中预计算坐标变换
  │
  ├─ 2. finalizeShaders()                              [GrGLSLProgramBuilder.cpp:543]
  │    ├─ varyingHandler()->finalize()                 ── 收集所有 varying 声明
  │    ├─ fVS.finalize(kVertex)                        ── 拼接 VS 各 section → fCompilerString
  │    └─ fFS.finalize(kFragment)                      ── 拼接 FS 各 section → fCompilerString
  │
  └─ 3. 编译 SkSL → 后端着色器
       └─ fVS.fCompilerString / fFS.fCompilerString    ── 最终 SkSL 源码
```

### Shader 字符串的 section 拼接顺序

每个 `GrGLSLShaderBuilder` 内部维护多个字符串 section，`finalize()` 时按顺序拼接：

```
┌─────────────────────────────────┐
│  #extension ...                 │  ← kExtensions
├─────────────────────────────────┤
│  const half4 ... ;              │  ← kDefinitions
├─────────────────────────────────┤
│  precision mediump float;       │  ← kPrecisionQualifier
├─────────────────────────────────┤
│  layout(location=0) ...         │  ← kLayoutQualifiers
├─────────────────────────────────┤
│  uniform float4x4 uMatrix;     │  ← kUniforms（由 uniformHandler 收集）
│  uniform sampler2D uSampler;    │
├─────────────────────────────────┤
│  in float2 vLocalCoord;         │  ← kInputs（varying 输入，由 varyingHandler 收集）
├─────────────────────────────────┤
│  out half4 sk_FragColor;        │  ← kOutputs
├─────────────────────────────────┤
│  half4 TextureEffect_S1_c0(...) │  ← kFunctions（FP 函数，深度优先序）
│  half4 Blend_S1(...)            │
│  half4 Color_S2(...)            │
├─────────────────────────────────┤
│  void main() {                  │  ← kMain
│    half4 _out0;                 │
│    _out0 = Blend_S1(_input);    │     ← GP/FP/XP 的 codeAppendf() 写入
│    sk_FragColor = _out0;        │
│  }                              │
└─────────────────────────────────┘
```

### 函数名 mangle 规则

```
命名格式：<FPName>_S<stageIndex>[_c<childIndex>]*

示例 Pipeline:
  Stage 0: GP
  Stage 1: BlendFP (root FP #0)
    ├── child 0: TextureEffectFP
    │   └── child 0: ColorSpaceXformFP
    └── child 1: ColorFP
  Stage 2: CoverageFP (root FP #1)

生成的函数名：
  _S1           → Blend_S1(...)
  _S1_c0        → TextureEffect_S1_c0(...)
  _S1_c0_c0     → ColorSpaceXform_S1_c0_c0(...)
  _S1_c1        → Color_S1_c1(...)
  _S2           → Coverage_S2(...)
```

### 完整示例：一次 draw call 生成的 SkSL

假设 pipeline 为：`GP(QuadPerEdgeAA) → ColorFP(BlendFP(TextureFP, ColorFP)) → XP(PorterDuff)`

**顶点着色器（VS）**：
```glsl
// kUniforms
uniform float3x3 uViewMatrix_S0;

// kInputs (vertex attributes → VS inputs)
in float2 aPosition;
in half4 aColor;
in float2 aLocalCoord;

// kOutputs (varyings → FS)
out half4 vColor;
out float2 vTransformedCoords_S1_c0;  // collectTransforms() lifted

void main() {
    // ← GP.onEmitCode() 写入
    vColor = aColor;

    // ← emitTransformCode() 写入（坐标变换提升到 VS）
    vTransformedCoords_S1_c0 = (uMatrix_S1_c0 * float3(aLocalCoord, 1.0)).xy;

    // ← emitNormalizedSkPosition() 写入
    sk_Position = float4(aPosition, 0.0, 1.0);
}
```

**片元着色器（FS）**：
```glsl
// kUniforms
uniform sampler2D uSampler_S1_c0;

// kInputs (varyings from VS)
in half4 vColor;
in float2 vTransformedCoords_S1_c0;

// kFunctions — 深度优先序，叶子在前
half4 TextureEffect_S1_c0(half4 _input, float2 _coords) {   // ← writeFPFunction
    return sample(uSampler_S1_c0, _coords);
}

half4 Color_S1_c1(half4 _input) {                            // ← writeFPFunction
    return half4(1.0, 0.0, 0.0, 1.0);
}

half4 Blend_S1(half4 _input) {                               // ← writeFPFunction
    half4 _src = TextureEffect_S1_c0(_input, vTransformedCoords_S1_c0);  // invokeChild(0)
    half4 _dst = Color_S1_c1(_input);                                     // invokeChild(1)
    return _src + _dst * (1.0 - _src.a);                                  // SrcOver
}

// kMain
void main() {
    half4 outputColor = vColor;                  // ← GP 输出颜色
    half4 _tmp0 = Blend_S1(outputColor);         // ← FP 调用
    outputColor = _tmp0;
    sk_FragColor = outputColor;                  // ← XP 最终输出
}
```

### 关键设计：emitTransformCode 为什么在最后

`emitTransformCode()` 在所有 FP 的 `emitCode()` **之后**才调用，原因是：

1. `collectTransforms()` 在 GP 阶段分析 FP 树，**规划**哪些 varying 需要创建
2. 各 FP 的 `emitCode()` 执行时，会向 `uniformHandler` 注册自己的矩阵 uniform
3. `emitTransformCode()` 需要引用这些 uniform 来生成 `varying = matrix * coords`
4. 如果在 FP 之前生成变换代码，uniform 还不存在，无法引用

```
时序：
  collectTransforms()     → 规划：哪些 FP 需要 varying（记录到 fTransformVaryingsMap）
  各 FP.emitCode()        → 各 FP 注册自己的 uniform（矩阵等）
  emitTransformCode()     → 引用已注册的 uniform，生成 VS 变换代码
```

## 附录 C：GrGeometryProcessor 全部子类

### 继承树

```
GrGeometryProcessor
│
├── [文本渲染]
│   ├── GrBitmapTextGeoProc                    effects/GrBitmapTextGeoProc.h:37
│   ├── GrDistanceFieldA8TextGeoProc           effects/GrDistanceFieldGeoProc.h:72
│   ├── GrDistanceFieldPathGeoProc             effects/GrDistanceFieldGeoProc.h:153
│   └── GrDistanceFieldLCDTextGeoProc          effects/GrDistanceFieldGeoProc.h:209
│
├── [曲线渲染]
│   ├── GrConicEffect                          effects/GrBezierEffect.h:66
│   └── GrQuadEffect                           effects/GrBezierEffect.h:126
│
├── [阴影]
│   └── GrRRectShadowGeoProc                   effects/GrShadowGeoProc.h:26
│
├── [默认]
│   └── DefaultGeoProc                         GrDefaultGeoProcFactory.cpp:47
│
├── [椭圆/圆形]
│   ├── CircleGeometryProcessor                ops/GrOvalOpFactory.cpp:118
│   ├── ButtCapDashedCircleGeometryProcessor   ops/GrOvalOpFactory.cpp:319
│   ├── EllipseGeometryProcessor               ops/GrOvalOpFactory.cpp:576
│   └── DIEllipseGeometryProcessor             ops/GrOvalOpFactory.cpp:773
│
├── [四边形/矩形]
│   ├── QuadPerEdgeAAGeometryProcessor         ops/QuadPerEdgeAA.cpp:619
│   ├── QuadEdgeEffect                         ops/AAConvexPathRenderer.cpp:597
│   ├── FillRRectOpImpl::Processor             ops/FillRRectOp.cpp:454
│   └── LatticeGP                              ops/LatticeOp.cpp:84
│
├── [虚线]
│   ├── DashingCircleEffect                    ops/DashOp.cpp:754
│   └── DashingLineEffect                      ops/DashOp.cpp:941
│
├── [其他]
│   ├── DrawAtlasPathShader                    ops/DrawAtlasPathOp.cpp:54
│   ├── BoundingBoxShader                      ops/PathStencilCoverOp.cpp:63
│   └── MeshGP                                 ops/DrawMeshOp.cpp:117
│
└── [曲面细分] GrTessellationShader             tessellate/GrTessellationShader.h:31
     │
     ├── GrPathTessellationShader              tessellate/GrPathTessellationShader.h:34
     │   ├── SimpleTriangleShader              tessellate/GrPathTessellationShader.cpp:38
     │   ├── MiddleOutShader                   tessellate/GrPathTessellationShader.cpp:88
     │   └── HullShader                        ops/PathInnerTriangulateOp.cpp:55
     │
     └── GrStrokeTessellationShader            tessellate/GrStrokeTessellationShader.h:32
```

### 子类说明

| 子类 | 文件 | 用途 |
|------|------|------|
| **GrBitmapTextGeoProc** | effects/GrBitmapTextGeoProc.h | 位图文本渲染，从 atlas 纹理采样字形 |
| **GrDistanceFieldA8TextGeoProc** | effects/GrDistanceFieldGeoProc.h | A8 距离场文本，带 gamma 校正 LUT |
| **GrDistanceFieldPathGeoProc** | effects/GrDistanceFieldGeoProc.h | 距离场路径渲染，无 gamma 校正 |
| **GrDistanceFieldLCDTextGeoProc** | effects/GrDistanceFieldGeoProc.h | LCD 子像素距离场文本 |
| **GrConicEffect** | effects/GrBezierEffect.h | 圆锥曲线（hairline），用 Loop-Blinn 方法 |
| **GrQuadEffect** | effects/GrBezierEffect.h | 二次曲线（hairline） |
| **GrRRectShadowGeoProc** | effects/GrShadowGeoProc.h | 圆角矩形阴影的覆盖度掩码 |
| **DefaultGeoProc** | GrDefaultGeoProcFactory.cpp | 通用默认 GP（位置 × viewMatrix） |
| **CircleGeometryProcessor** | ops/GrOvalOpFactory.cpp | 圆形，在半径归一化空间中计算覆盖度 |
| **ButtCapDashedCircleGeometryProcessor** | ops/GrOvalOpFactory.cpp | 带 butt cap 的虚线圆形 |
| **EllipseGeometryProcessor** | ops/GrOvalOpFactory.cpp | 椭圆覆盖度计算 |
| **DIEllipseGeometryProcessor** | ops/GrOvalOpFactory.cpp | 基于距离的高质量椭圆 |
| **QuadPerEdgeAAGeometryProcessor** | ops/QuadPerEdgeAA.cpp | **最常用**，逐边 AA 四边形 |
| **QuadEdgeEffect** | ops/AAConvexPathRenderer.cpp | AA 凸路径的四边形边缘 |
| **FillRRectOpImpl::Processor** | ops/FillRRectOp.cpp | 填充圆角矩形 |
| **LatticeGP** | ops/LatticeOp.cpp | 九宫格（lattice/nine-patch）绘制 |
| **DashingCircleEffect** | ops/DashOp.cpp | 虚线圆点 |
| **DashingLineEffect** | ops/DashOp.cpp | 虚线线段 |
| **DrawAtlasPathShader** | ops/DrawAtlasPathOp.cpp | 从 atlas 绘制路径 |
| **BoundingBoxShader** | ops/PathStencilCoverOp.cpp | 路径模板-覆盖中的包围盒 |
| **MeshGP** | ops/DrawMeshOp.cpp | SkMesh 自定义网格绘制 |
| **GrTessellationShader** | tessellate/GrTessellationShader.h | 曲面细分基类 |
| **GrPathTessellationShader** | tessellate/GrPathTessellationShader.h | 路径细分基类 |
| **SimpleTriangleShader** | tessellate/GrPathTessellationShader.cpp | 简单三角形数组 |
| **MiddleOutShader** | tessellate/GrPathTessellationShader.cpp | middle-out 拓扑的曲线细分 |
| **HullShader** | ops/PathInnerTriangulateOp.cpp | 曲线凸包填充 |
| **GrStrokeTessellationShader** | tessellate/GrStrokeTessellationShader.h | 描边路径细分 |

## 附录 D：GrFragmentProcessor 全部子类

### 继承树

```
GrFragmentProcessor
│
├── [纹理采样]
│   ├── GrTextureEffect                        effects/GrTextureEffect.h:32
│   ├── GrBicubicEffect                        effects/GrBicubicEffect.h:28
│   └── GrModulateAtlasCoverageEffect          effects/GrModulateAtlasCoverageEffect.h:23
│
├── [颜色变换]
│   ├── GrColorSpaceXformEffect                GrColorSpaceXform.h:57
│   ├── GrColorTableEffect                     effects/GrColorTableEffect.h:26
│   └── GrYUVtoRGBEffect                       effects/GrYUVtoRGBEffect.h:28
│
├── [坐标变换]
│   └── GrMatrixEffect                         effects/GrMatrixEffect.h:24
│
├── [几何覆盖度]
│   ├── GrConvexPolyEffect                     effects/GrConvexPolyEffect.h:30
│   ├── CircularRRectEffect                    effects/GrRRectEffect.cpp:42     (匿名命名空间)
│   └── EllipticalRRectEffect                  effects/GrRRectEffect.cpp:402    (匿名命名空间)
│
├── [噪声]
│   └── GrPerlinNoise2Effect                   effects/GrPerlinNoise2Effect.h:35
│
├── [运行时效果]
│   └── GrSkSLFP                               effects/GrSkSLFP.h:70
│
├── [组合/混合]
│   └── BlendFragmentProcessor                 effects/GrBlendFragmentProcessor.cpp:39  (匿名命名空间)
│
└── [内部工具 FP]（定义在 GrFragmentProcessor.cpp 中）
    ├── SwizzleFragmentProcessor               GrFragmentProcessor.cpp:262     — 通道重排（RGBA→BGRA 等）
    ├── ComposeProcessor                       GrFragmentProcessor.cpp:379     — 函数组合 f(g(x))
    ├── SurfaceColorProcessor                  GrFragmentProcessor.cpp:513     — 读取帧缓冲目标颜色
    ├── DeviceSpace                            GrFragmentProcessor.cpp:558     — 在设备坐标空间求值子 FP
    └── HighPrecisionFragmentProcessor         GrFragmentProcessor.cpp:812     — 强制 float32 精度
```

### 子类说明

| 子类 | 文件 | 用途 |
|------|------|------|
| **GrTextureEffect** | effects/GrTextureEffect.h | 纹理采样，支持 wrap mode、subset/domain、边框颜色 |
| **GrBicubicEffect** | effects/GrBicubicEffect.h | 高质量双三次滤波（Mitchell/Catmull-Rom） |
| **GrModulateAtlasCoverageEffect** | effects/GrModulateAtlasCoverageEffect.h | 用 atlas 覆盖度调制输入颜色 |
| **GrColorSpaceXformEffect** | GrColorSpaceXform.h | 颜色空间变换（sRGB↔linear 等） |
| **GrColorTableEffect** | effects/GrColorTableEffect.h | 颜色查找表（LUT）映射 |
| **GrYUVtoRGBEffect** | effects/GrYUVtoRGBEffect.h | YUV→RGB 转换，2~4 个平面纹理输入 |
| **GrMatrixEffect** | effects/GrMatrixEffect.h | 对子 FP 坐标施加矩阵变换 |
| **GrConvexPolyEffect** | effects/GrConvexPolyEffect.h | 凸多边形覆盖度（基于边距离） |
| **CircularRRectEffect** | effects/GrRRectEffect.cpp | 圆角矩形（圆形角）AA 覆盖度 |
| **EllipticalRRectEffect** | effects/GrRRectEffect.cpp | 圆角矩形（椭圆角）AA 覆盖度 |
| **GrPerlinNoise2Effect** | effects/GrPerlinNoise2Effect.h | Perlin 噪声着色器，支持 octave 和 tiling |
| **GrSkSLFP** | effects/GrSkSLFP.h | **通用运行时效果**，执行任意 SkSL/SkRuntimeEffect |
| **BlendFragmentProcessor** | effects/GrBlendFragmentProcessor.cpp | 2 个子 FP 的混合（所有 SkBlendMode） |
| **SwizzleFragmentProcessor** | GrFragmentProcessor.cpp | 通道重排 `.rgba → .bgra` 等 |
| **ComposeProcessor** | GrFragmentProcessor.cpp | 函数组合 `outer(inner(input))` |
| **SurfaceColorProcessor** | GrFragmentProcessor.cpp | 读帧缓冲 dst 颜色（设置 willReadDstColor） |
| **DeviceSpace** | GrFragmentProcessor.cpp | 将子 FP 切换到 sk_FragCoord 坐标空间 |
| **HighPrecisionFragmentProcessor** | GrFragmentProcessor.cpp | 强制子 FP 使用 float32 高精度计算 |

### GrSkSLFP 的特殊地位

`GrSkSLFP` 是最通用的 FP——它执行任意 SkSL 代码（由 `SkRuntimeEffect` 编译）。许多用户层 API 最终走 `GrSkSLFP`：

```
SkRuntimeShaderBuilder   → GrSkSLFP
SkRuntimeColorFilter     → GrSkSLFP
SkRuntimeBlender         → GrSkSLFP
SkColorFilters::*        → 部分走 GrSkSLFP
SkImageFilters::*        → 部分走 GrSkSLFP
```

相比硬编码的 FP 子类（如 `GrTextureEffect`），`GrSkSLFP` 以运行时灵活性换取编译时优化机会。硬编码 FP 可以在 `emitCode()` 中做更多静态优化（常量折叠、分支消除），而 `GrSkSLFP` 依赖 SkSL 编译器的通用优化。
