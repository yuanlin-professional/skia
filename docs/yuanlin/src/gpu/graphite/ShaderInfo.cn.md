# ShaderInfo

> 源文件: src/gpu/graphite/ShaderInfo.h, src/gpu/graphite/ShaderInfo.cpp

## 概述

`ShaderInfo` 是 Skia Graphite 渲染架构中负责着色器信息管理和 SkSL 代码生成的核心类。该类持有渲染管线中定义的所有根着色器节点（`ShaderNode`），提取固定功能混合参数，并聚合片段着色器树的需求信息。它负责将 `PaintParams` 的着色器节点树转换为完整的顶点和片段着色器 SkSL 代码，同时处理 uniform 绑定、纹理采样器、varying 变量以及复杂的混合模式策略。

`ShaderInfo` 在渲染管线创建阶段使用，为给定的 `RenderStep` 和 `PaintParamsID` 组合生成最终的着色器代码。它支持多种后端特性，包括存储缓冲区（SSBO）、固定采样器、目标读取策略以及梯度缓冲区优化。

## 架构位置

`ShaderInfo` 位于 Graphite GPU 架构的着色器编译层：

```
Graphite 架构层次：
  ├── 客户端 API（SkCanvas, SkPaint）
  ├── PaintParams（描述绘制参数）
  ├── PaintParamsKey（压缩的着色器节点标识）
  └── ShaderInfo（着色器代码生成器）★
      ├── ShaderCodeDictionary（节点字典）
      ├── RuntimeEffectDictionary（运行时效果）
      ├── ShaderNode（着色器节点树）
      └── 生成的 SkSL 代码 → 后端编译器（Metal/Vulkan/Dawn）
```

该类与以下组件紧密协作：
- **ShaderCodeDictionary**: 提供代码片段的静态定义和节点注册表
- **PaintParamsKey**: 压缩的着色器节点序列化表示
- **RenderStep**: 定义几何处理和顶点着色器逻辑
- **UniformManager**: 处理 uniform 数据的布局和写入
- **Caps**: 查询后端能力和资源绑定需求

## 主要类与结构体

### ShaderInfo 类

```cpp
class ShaderInfo {
public:
    // 工厂方法：从 PaintParamsID 和 RenderStep 创建 ShaderInfo
    static std::unique_ptr<ShaderInfo> Make(
        const Caps* caps,
        const ShaderCodeDictionary* dict,
        const RuntimeEffectDictionary* rteDict,
        const RenderPassDesc& rpDesc,
        const RenderStep* step,
        UniquePaintParamsID paintID,
        skia_private::TArray<SamplerDesc>* outDescs = nullptr);

    // 访问器
    const ShaderCodeDictionary* shaderCodeDictionary() const;
    const RuntimeEffectDictionary* runtimeEffectDictionary() const;
    const char* uniformSsboIndex() const;
    DstReadStrategy dstReadStrategy() const;
    const skgpu::BlendInfo& blendInfo() const;

    // 生成的着色器代码
    const std::string& vertexSkSL() const;
    const std::string& fragmentSkSL() const;

    // 着色器标签（用于调试）
    const std::string& vsLabel() const;
    const std::string& fsLabel() const;
    const std::string& pipelineLabel() const;

    // 资源需求
    int numFragmentTexturesAndSamplers() const;
    bool hasCombinedUniforms() const;
    bool hasGradientBuffer() const;

    // 梯度缓冲区名称常量
    static constexpr char kGradientBufferName[] = "fsGradientBuffer";

private:
    struct SharedGeneratorData; // 顶点和片段着色器生成的共享数据

    void generateFragmentSkSL(...);
    void generateVertexSkSL(...);
};
```

### SharedGeneratorData 内部结构体

```cpp
struct ShaderInfo::SharedGeneratorData {
    SkSpan<const ShaderNode*> fRootNodes;           // 解压后的着色器树
    std::vector<LiftedExpression> fLiftedExpr;       // 提升到顶点着色器的表达式
    std::string fSharedPreamble;                     // 两个着色器阶段共享的前导代码
    bool fNeedsLocalCoords;                          // 是否需要局部坐标
    bool fHasSsboIndexVarying;                       // 是否需要 SSBO 索引 varying
    bool fHasStepUniforms;                           // RenderStep 是否有 uniform
    bool fHasPaintUniforms;                          // Paint 是否有 uniform
    bool fHasLiftedPaintUniforms;                    // 是否有被提升的 Paint uniform
    bool fUseUniformStorageBufferVS;                 // 顶点着色器是否使用 SSBO
    bool fUseUniformStorageBufferFS;                 // 片段着色器是否使用 SSBO
};
```

### LiftedExpression 结构体

```cpp
struct LiftedExpression {
    const ShaderNode* fNode;          // 需要提升的节点
    ShaderSnippet::Args fArgs;        // 提升表达式的参数
    bool fEmitVarying;                // 是否在顶点着色器中生成 varying 输出
};
```

## 公共 API 函数

### ShaderInfo::Make

```cpp
static std::unique_ptr<ShaderInfo> Make(
    const Caps* caps,                                // GPU 能力查询
    const ShaderCodeDictionary* dict,                // 着色器代码字典
    const RuntimeEffectDictionary* rteDict,          // 运行时效果字典
    const RenderPassDesc& rpDesc,                    // 渲染通道描述
    const RenderStep* step,                          // 渲染步骤
    UniquePaintParamsID paintID,                     // 绘制参数标识
    skia_private::TArray<SamplerDesc>* outDescs);    // 输出采样器描述（可选）
```

**功能**: 创建 `ShaderInfo` 实例并生成完整的顶点和片段着色器 SkSL 代码。

**工作流程**:
1. 解压 `PaintParamsKey` 为着色器节点树
2. 分析节点需求：局部坐标、uniform、纹理、表达式提升
3. 生成共享的 uniform 和 varying 声明
4. 调用 `generateFragmentSkSL()` 生成片段着色器
5. 调用 `generateVertexSkSL()` 生成顶点着色器
6. 确定混合策略和目标读取需求

**关键决策**:
- **SSBO vs Uniform Buffer**: 根据 `caps->storageBufferSupport()` 和 uniform 数量决定
- **目标读取策略**: 如果不能使用硬件混合，需要在着色器中读取目标纹理
- **固定采样器分析**: 如果传入 `outDescs` 参数，分析节点数据以提取固定采样器描述

### 访问器方法

- **shaderCodeDictionary()**: 返回着色器代码字典指针
- **runtimeEffectDictionary()**: 返回运行时效果字典指针
- **uniformSsboIndex()**: 返回 SSBO 索引变量名（如果使用）
- **dstReadStrategy()**: 返回目标读取策略枚举值
- **blendInfo()**: 返回 GPU 混合配置信息
- **vertexSkSL() / fragmentSkSL()**: 返回生成的 SkSL 代码字符串
- **numFragmentTexturesAndSamplers()**: 返回片段着色器使用的纹理/采样器数量
- **hasCombinedUniforms()**: 返回是否有合并的 uniform 缓冲区
- **hasGradientBuffer()**: 返回是否使用梯度缓冲区优化

## 内部实现细节

### 着色器节点树结构

`PaintParamsKey` 解压后生成 2-3 个根节点：
1. **源颜色节点** (index 0): 生成源颜色，接受局部坐标
2. **最终混合节点** (index 1): 混合源颜色和目标颜色
3. **裁剪节点** (index 2, 可选): 应用裁剪蒙版

### Uniform 处理

**合并 Uniform 缓冲区**:
```cpp
// 布局示例：
layout (set=0, binding=1) uniform CombinedUniforms {
    layout(offset=0) float4 paintColor_0;    // Paint uniform
    layout(offset=16) float2x2 matrix_3;     // 节点 #3 的 uniform
    layout(offset=48) float stepUniform;     // RenderStep uniform
};
```

**SSBO 模式** (当后端支持时):
```cpp
struct CombinedUniformData {
    float4 paintColor_0;
    float2x2 matrix_3;
    float stepUniform;
};
layout (set=0, binding=1) readonly buffer CombinedUniforms {
    CombinedUniformData combinedUniformData[];
};
// 顶点/片段着色器中：
uint uniformSsboIndex = ssboIndex;
float4 paintColor_0 = combinedUniformData[uniformSsboIndex].paintColor_0;
```

### 表达式提升（Expression Lifting）

某些计算可以从片段着色器提升到顶点着色器以提高性能：

**局部坐标变换**:
```cpp
// 原始片段着色器代码：
half4 color = sample(shader, localMatrix * fragCoord);

// 提升后：
// 顶点着色器：
out float2 localCoordsVar_node5 = localMatrix * stepLocalCoords;
// 片段着色器：
half4 color = sample(shader, localCoordsVar_node5);
```

**标志**:
- `SnippetRequirementFlags::kLiftExpression`: 将表达式提升并通过 varying 传递
- `SnippetRequirementFlags::kOmitExpression`: 仅在顶点着色器中计算，不输出 varying

### 混合模式处理

**三种混合策略**:

1. **硬件混合** (`CanUseHardwareBlending()` 返回 true):
   - 直接配置 GPU 混合方程
   - `fBlendInfo` 从 `gBlendTable` 查找

2. **覆盖率调制混合** (Porter-Duff 模式 + 覆盖率):
   - 使用 `BlendFormula` 计算调制后的源/目标系数
   - 可能启用双源混合（`sk_SecondaryFragColor`）

3. **着色器内混合** (需要目标读取):
   - 在片段着色器中手动混合：`finalColor = srcColor * coverage + dstColor * (1 - coverage)`
   - 使用 `kSrc` 硬件混合模式将结果写出

**目标读取策略**:
- `kNoneRequired`: 不需要读取目标
- `kFramebufferFetch`: 使用 `sk_LastFragColor`（移动设备）
- `kTextureCopy` / `kTextureSample`: 从复制的目标纹理采样
- `kReadFromInput`: 使用输入附件（Vulkan subpass）

### 纹理和采样器

**固定采样器检测**:
```cpp
// 在 get_node_texture_samplers() 中：
if (snippetId == kImageShader && node->data().size() > 0) {
    // 解析节点数据为 SamplerDesc
    append_sampler_descs(node->data(), *outDescs);
}
```

**绑定生成**:
```cpp
// 片段着色器：
layout (set=2, binding=0) sampler2D tex_0;  // Paint 纹理
layout (set=2, binding=1) sampler2D tex_5;  // 节点 #5 的纹理
layout (set=2, binding=2) sampler2D dstSampler;  // 目标纹理（如需要）
```

### 前导代码生成

`emit_preambles()` 遍历节点树，为每个节点生成包装函数：

```cpp
// 节点 #3 的前导代码示例：
half4 node_3_wrapper(float2 coords) {
    return linear_gradient(coords,           // 静态函数
                          matrix_3,          // 混淆后的 uniform
                          colors_3,
                          stops_3);
}
```

### 顶点着色器生成

1. **固定前导**: Intrinsic constants, varyings, attributes
2. **RenderStep 逻辑**: 调用 `step->vertexSkSL()`
3. **sk_Position 计算**: 应用视口变换
4. **提升表达式**: 计算并输出到 varyings
5. **SSBO 索引传递**: 如果片段着色器需要

### 片段着色器生成

1. **资源声明**: Uniforms, samplers, gradient buffers
2. **前导函数**: 节点包装函数
3. **main() 逻辑**:
   - 从 varying 读取 SSBO 索引（如需要）
   - 计算原始颜色覆盖率（`step->fragmentColorSkSL()`）
   - 调用源颜色根节点
   - 读取目标颜色（如需要）
   - 调用最终混合节点
   - 应用写入调配（write swizzle）
   - 调用裁剪节点（如存在）
   - 计算并输出最终颜色和覆盖率

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `ShaderCodeDictionary` | 提供代码片段定义和节点解压 |
| `RuntimeEffectDictionary` | 管理用户自定义的运行时效果 |
| `PaintParamsKey` | 压缩的着色器树表示 |
| `ShaderNode` | 着色器树的节点表示 |
| `RenderStep` | 提供顶点着色器逻辑和步骤需求 |
| `UniformManager` | Uniform 布局计算和写入 |
| `Caps` | 查询后端能力和绑定需求 |
| `BlendFormula` | 计算覆盖率混合公式 |
| `TextureFormat` | 目标纹理格式信息 |

### 外部依赖

| 依赖 | 用途 |
|------|------|
| SkSL 编译器 | 编译生成的 SkSL 代码为后端着色器 |
| Skia 核心 | 混合模式、颜色类型定义 |
| 后端驱动 | 执行编译后的着色器程序 |

### 被依赖情况

- **GraphicsPipelineDesc**: 使用 `ShaderInfo` 生成管线描述符
- **PipelineCache**: 缓存 `ShaderInfo` 生成的着色器
- **ContextUtils**: 调用 `ShaderInfo::Make` 创建着色器

## 设计模式与设计决策

### 工厂模式

使用静态 `Make()` 方法而非公共构造函数，确保对象总是完全初始化的：
- 构造函数是私有的
- `Make()` 执行复杂的初始化逻辑
- 返回 `std::unique_ptr` 表达所有权转移

### 访问者模式（变体）

节点树遍历使用函数回调而非虚函数：
- `emit_preambles()` 递归遍历节点
- 每个节点提供 `fPreambleGenerator` 和 `fExpressionGenerator` 函数指针
- 避免在 `ShaderNode` 中使用虚函数开销

### 构建器模式

着色器代码通过字符串拼接逐步构建：
```cpp
std::string preamble = emit_intrinsic_constants(...);
preamble += emit_varyings(...);
preamble += emit_textures_and_samplers(...);
std::string mainBody = "void main() {";
mainBody += /* ... */;
fFragmentSkSL = preamble + "\n" + mainBody;
```

### 策略模式

目标读取策略通过 `DstReadStrategy` 枚举动态选择：
```cpp
switch (fDstReadStrategy) {
    case kFramebufferFetch: mainBody += "dstColor = sk_LastFragColor;"; break;
    case kTextureSample:    mainBody += "dstColor = sample(dstSampler, ...);"; break;
    case kReadFromInput:    mainBody += "dstColor = subpassLoad(...);"; break;
}
```

### 关键设计决策

1. **延迟代码生成**: 只在管线创建时生成着色器，而非在 `PaintParams` 创建时
2. **共享前导代码**: 避免顶点和片段着色器重复声明 uniform/varying
3. **统一 Uniform 缓冲区**: Paint 和 RenderStep 的 uniform 合并到一个绑定
4. **表达式提升优化**: 自动将重复计算从片段着色器移到顶点着色器
5. **固定采样器支持**: 预先分析节点数据以支持固定采样器（如 Vulkan YCbCr）

## 性能考量

### 着色器复杂度控制

1. **节点复用**: 相同的 `PaintParamsKey` 重用相同的着色器代码
2. **Varying 数量限制**: 通过 `caps->maxVaryings()` 限制提升表达式数量
3. **Uniform 去重**: `paintColor` 等常见 uniform 自动去重

### 内存管理

- 使用 `SkArenaAlloc` 为临时 `ShaderNode` 对象分配内存
- 着色器字符串使用 `std::string::reserve()` 预分配
- 共享字典避免重复存储代码片段

### 编译优化

1. **静态函数内联**: 生成的包装函数可被 SkSL 编译器内联
2. **Dead Code Elimination**: 未使用的 uniform/varying 由编译器移除
3. **常量折叠**: Uniform 值在某些后端可能被优化为常量

### 分支开销

- 避免在循环中进行动态分支（如节点遍历在 CPU 端完成）
- 混合模式在着色器中通过静态展开而非运行时分支
- 裁剪覆盖率乘法而非条件丢弃（除目标复制情况）

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/ShaderCodeDictionary.h/cpp` | 代码片段字典和节点注册表 |
| `src/gpu/graphite/PaintParamsKey.h/cpp` | 着色器树的压缩表示 |
| `src/gpu/graphite/RenderStep.h/cpp` | 渲染步骤定义和顶点逻辑 |
| `src/gpu/graphite/UniformManager.h/cpp` | Uniform 布局和数据管理 |
| `src/gpu/graphite/ContextUtils.h/cpp` | 管线创建的辅助函数 |
| `src/gpu/graphite/Caps.h` | GPU 能力查询接口 |
| `src/gpu/graphite/ResourceTypes.h` | 资源类型定义（SamplerDesc 等） |
| `src/gpu/BlendFormula.h` | 混合公式计算 |
| `src/sksl/sksl_graphite_frag.sksl` | Graphite 预编译的 SkSL 模块 |
| `src/gpu/graphite/TextureFormat.h` | 纹理格式定义 |
