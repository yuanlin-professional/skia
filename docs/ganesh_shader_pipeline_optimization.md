# Ganesh Vulkan Shader/Pipeline 膨胀问题分析与优化方案

## 目录

- [一、Shader 生成的完整路径](#一shader-生成的完整路径)
  - [1.1 总体流程](#11-总体流程)
  - [1.2 GeometryProcessor (GP)](#12-geometryprocessor-gp)
  - [1.3 FragmentProcessor (FP)](#13-fragmentprocessor-fp)
  - [1.4 XferProcessor (XP)](#14-xferprocessor-xp)
  - [1.5 Vulkan 特有的 Pipeline Key 扩展](#15-vulkan-特有的-pipeline-key-扩展)
- [二、膨胀根因分析](#二膨胀根因分析)
  - [2.1 组合爆炸公式](#21-组合爆炸公式)
  - [2.2 各因素膨胀程度](#22-各因素膨胀程度)
  - [2.3 GrProgramDesc Key 结构详解](#23-grprogramdesc-key-结构详解)
- [三、优化方案](#三优化方案)
  - [方案 1: Specialization Constants](#方案-1-specialization-constants-vulkan-spir-v)
  - [方案 2: 减少 GrProgramDesc Key 中的无效变量](#方案-2-减少-grprogramdesc-key-中的无效变量)
  - [方案 3: Extended Dynamic State](#方案-3-extended-dynamic-state-减少-vulkan-pipeline-变体)
  - [方案 4: Uber Shader](#方案-4-uber-shader-统一着色器)
  - [方案 5: Pipeline Derivatives](#方案-5-pipeline-derivatives)
  - [方案 6: 参考 Graphite 架构](#方案-6-参考-graphite-架构)
- [四、验证方法](#四验证方法)
  - [4.1 内置统计计数器](#41-内置统计计数器)
  - [4.2 PersistentCache 精确计数](#42-persistentcache-精确计数)
  - [4.3 GrProgramDesc Key 分析](#43-grprogramdesc-key-分析)
  - [4.4 Trace Event 追踪](#44-trace-event-追踪)
  - [4.5 推荐的完整验证流程](#45-推荐的完整验证流程)
- [五、关键源码索引](#五关键源码索引)

---

## 一、Shader 生成的完整路径

### 1.1 总体流程

Ganesh 中的 shader 由三类处理器**组合拼接**生成。每个 `GrProgramDesc` 唯一对应一套
shader + pipeline：

```
SkPaint + SkShader + SkColorFilter + Clips
    │  (Skia core → Ganesh 翻译, 见 GrFragmentProcessors.h)
    ▼
GrPaint { fColor, fColorFragmentProcessor, fCoverageFragmentProcessor, fXPFactory }
    │  (DrawOp 创建时)
    ▼
GrProcessorSet { colorFP, coverageFP, XP }
    │  (finalize: 常量折叠, 优化分析)
    ▼
GrPipeline { fFragmentProcessors[color..., coverage...], fXferProcessor }
    │  (ProgramBuilder)
    ▼
GrGLSLProgramBuilder::emitAndInstallProcs()
    ├── (1) emitAndInstallPrimProc()    → GP 写入 VS + FS
    ├── (2) emitAndInstallDstTexture()  → dst color 读取代码
    ├── (3) emitAndInstallFragProcs()   → FP 树递归展开为 FS 中的独立函数
    └── (4) emitAndInstallXferProc()    → XP 写入最终混合代码
    │
    ▼
finalizeShaders() → fVS.finalize() + fFS.finalize()  (拼接所有字符串段)
    │
    ▼
SkSL → SPIR-V (GrCompileVkShaderModule) → VkShaderModule → VkPipeline
```

**关键拼接点** (`src/gpu/ganesh/glsl/GrGLSLProgramBuilder.cpp`):

- `emitAndInstallProcs()` (line 61): 总调度入口
- `writeFPFunction()` (line 245): 将每个 FP 编译为独立 GLSL 函数
- `writeChildFPFunctions()` (line 311): 递归处理子 FP
- `finalizeShaders()` (line 543): 将所有字符串段拼接为最终 shader 源码

### 1.2 GeometryProcessor (GP)

GP 负责顶点处理，是 vertex shader 的主要贡献者。约 21 种子类：

| 子类 | 源文件 | Key 变量因素 |
|------|--------|-------------|
| `DefaultGeoProc` | `GrDefaultGeoProcFactory.cpp:47` | color/coverage/localCoord 属性开关(6 flags) + 矩阵类型(4×4) ≈ **500+ 组合** |
| `QuadPerEdgeAAGeometryProcessor` | `QuadPerEdgeAA.cpp:619` | subset/textured/perspective/saturate/colorType/coverageMode |
| `CircleGeometryProcessor` | `GrOvalOpFactory.cpp:118` | stroke/clipPlane/isectPlane/unionPlane/roundCap |
| `ButtCapDashedCircleGeometryProcessor` | `GrOvalOpFactory.cpp:319` | 类似 CircleGP |
| `EllipseGeometryProcessor` | `GrOvalOpFactory.cpp:576` | stroke/wideColor/useScale/localMatrix |
| `DIEllipseGeometryProcessor` | `GrOvalOpFactory.cpp:773` | wideColor/viewMatrix/style |
| `GrBitmapTextGeoProc` | `GrBitmapTextGeoProc.h:37` | maskFormat/usesW/color/localMatrix |
| `GrDistanceFieldA8TextGeoProc` | `GrDistanceFieldGeoProc.h:72` | flags + matrixKey |
| `FillRRectOp::Processor` | `FillRRectOp.cpp:464` | flags (少量 bit) |
| `DashingCircleEffect` | `DashOp.cpp:754` | addToKey at line 766 |
| `DashingLineEffect` | `DashOp.cpp:941` | addToKey at line 955 |
| `MeshGP` | `DrawMeshOp.cpp:117` | 自定义 mesh spec |
| `GrRRectShadowGeoProc` | `GrShadowGeoProc.h:26` | 空 addToKey |
| `BoundingBoxShader` | `PathStencilCoverOp.cpp:63` | 空 addToKey |
| `GrTessellationShader` 子类 | `GrTessellationShader.h:31` | tessellation 相关 |

**矩阵精度分级**（`GrGeometryProcessor.h:347`）产生额外变体：
```cpp
static uint32_t ComputeMatrixKey(const GrShaderCaps& caps, const SkMatrix& mat) {
    if (!caps.fReducedShaderMode) {
        if (mat.isIdentity())       return 0b00;  // 恒等
        if (mat.isScaleTranslate()) return 0b01;  // 缩放+平移
    }
    if (!mat.hasPerspective())      return 0b10;  // 仿射
    return 0b11;                                   // 透视
}
```
每个矩阵最多 4 种变体，view matrix + local matrix = 最多 4×4 = 16 种组合。

**属性布局入 key**（`GrGeometryProcessor.cpp:556`）：
```
stride(16bit) + attributeCount(16bit) + [cpuType(8bit) + gpuType(8bit) + offset(16bit)] × N
```

### 1.3 FragmentProcessor (FP)

FP 是 shader 膨胀的**最大来源**。每个 FP 被 `writeFPFunction()` 编译为独立 GLSL
函数，树状递归展开。

#### 公开 FP 子类（独立头文件）

| 类名 | 头文件 | 用途 |
|------|--------|------|
| `GrTextureEffect` | `effects/GrTextureEffect.h` | 纹理采样（wrap/filter模式入key） |
| `GrSkSLFP` | `effects/GrSkSLFP.h` | **SkRuntimeEffect，变体无上限** |
| `GrBicubicEffect` | `effects/GrBicubicEffect.h` | 双三次滤波 |
| `GrMatrixEffect` | `effects/GrMatrixEffect.h` | 矩阵坐标变换 |
| `GrConvexPolyEffect` | `effects/GrConvexPolyEffect.h` | 凸多边形裁剪 |
| `GrYUVtoRGBEffect` | `effects/GrYUVtoRGBEffect.h` | YUV 转 RGB |
| `GrPerlinNoise2Effect` | `effects/GrPerlinNoise2Effect.h` | Perlin 噪声 |
| `ColorTableEffect` | `effects/GrColorTableEffect.h` | 颜色查找表 |
| `GrModulateAtlasCoverageEffect` | `effects/GrModulateAtlasCoverageEffect.h` | atlas 覆盖调制 |
| `GrColorSpaceXformEffect` | `GrColorSpaceXform.h` | 色彩空间转换 |

#### 内部 FP 子类（匿名/工厂函数，定义在 .cpp 中）

| 类名 | 源文件 | 用途 |
|------|--------|------|
| `BlendFragmentProcessor` | `effects/GrBlendFragmentProcessor.cpp:39` | 两个子 FP 混合 |
| `CircularRRectEffect` | `effects/GrRRectEffect.cpp:42` | 圆角矩形裁剪 |
| `EllipticalRRectEffect` | `effects/GrRRectEffect.cpp:402` | 椭圆角矩形裁剪 |
| `SwizzleFragmentProcessor` | `GrFragmentProcessor.cpp:262` | 通道重排 |
| `ComposeProcessor` | `GrFragmentProcessor.cpp:379` | 串行组合 f(g(x)) |
| `SurfaceColorProcessor` | `GrFragmentProcessor.cpp:513` | 读取 dst color |
| `HighPrecisionFragmentProcessor` | `GrFragmentProcessor.cpp:812` | 强制高精度 |
| `DeviceSpace` | `GrFragmentProcessor.cpp:558` | 设备坐标求值 |

#### 通过 GrSkSLFP 实现的工具 FP

均定义在 `GrFragmentProcessor.cpp` 中：

- `MakeColor()` (line 204) — 常量色
- `ApplyPaintAlpha()` (line 225) — 应用 paint alpha
- `OverrideInput()` (line 330) — 覆盖输入色
- `DisableCoverageAsAlpha()` (line 351) — 禁用优化
- `DestColor()` (line 366) — 返回混合目标色
- `ClampOutput()` (line 247) — 输出钳位 [0,1]
- `ColorMatrix()` (line 467) — 4×5 颜色矩阵
- `Rect()` (line 615) — 矩形裁剪形状
- `Circle()` (line 658) — 圆形裁剪形状
- `Ellipse()` (line 709) — 椭圆裁剪形状

#### FP 树状组合模式

FP 形成**树**（非扁平列表），通过 `registerChild()` 注册子节点：

```
GrPaint's colorFragmentProcessor (root)
  └── GrMatrixEffect (坐标变换)
        └── GrColorSpaceXformEffect (色彩空间)
              └── GrTextureEffect (实际采样)
```

组合方式：
- **串行组合** (`ComposeProcessor`): f(g(x))
- **混合组合** (`BlendFragmentProcessor`): blend(src_child, dst_child, mode)
- **装饰器** (`SwizzleFragmentProcessor`, `GrMatrixEffect` 等): 单子节点包装
- **多子节点** (`GrYUVtoRGBEffect` 最多 4 个 plane 子节点)

#### FP Key 结构（递归）

```
classID(8bit) + coordTransformKey(4bit) + samplerKey + addToKey()
+ numChildren + [子 FP 的 Key 递归...]
```

### 1.4 XferProcessor (XP)

XP 处理最终混合，6 种子类：

| 子类 | 源文件 | 触发条件 | Key 贡献 |
|------|--------|---------|---------|
| `PorterDuffXferProcessor` | `effects/GrPorterDuffXferProcessor.cpp:36` | 标准 PD 混合(硬件可处理) | primaryOutput × secondaryOutput (6×6) |
| `ShaderPDXferProcessor` | `effects/GrPorterDuffXferProcessor.cpp:138` | PD 需读 dst color | blendMode enum |
| `PDLCDXferProcessor` | `effects/GrPorterDuffXferProcessor.cpp:211` | SrcOver + LCD 特殊路径 | 无额外 key |
| `CustomXP` | `effects/GrCustomXfermode.cpp:82` | 高级混合(Overlay/Darken等) | hwBlendEq flag + mode/interaction |
| `DisableColorXP` | `effects/GrDisableColorXP.cpp:26` | 仅 stencil pass | 无额外 key |
| `CoverageSetOpXP` | `effects/GrCoverageSetOpXP.cpp:23` | coverage 集合操作 | invertCoverage flag |

**两种 shader 发射路径**：
- `emitOutputsForBlendState()` — 当 `willReadDstColor() == false`，硬件混合
- `emitBlendCodeForDstRead()` — 当 `willReadDstColor() == true`，shader 内混合

每个 XP 基类固定贡献: `willReadDstColor(1bit)` + `isLCD(1bit)` + 子类 key。

### 1.5 Vulkan 特有的 Pipeline Key 扩展

在 `GrVkCaps::makeDesc()` (`src/gpu/ganesh/vk/GrVkCaps.cpp:1990`) 中,
base key 之后追加:

```
kShader_PersistentCacheKeyType (uint32 = 0)   // 持久化缓存 key 分割标记
+ RenderPass key:
    attachment flags (color/resolve/stencil)
    每个 attachment 的 VkFormat + sampleCount
    selfDependency / loadFromResolve flags
+ StencilSettings (stencil.genKey())
+ GrPipeline::genKey():
    pipeline flags (wireframe/conservativeRaster)
    blend info: srcBlend(5bit) + dstBlend(5bit) + equation(5bit) + writesColor(1bit)
    usesDstInputAttachment(1bit)
+ SampleCount (uint32)
+ PrimitiveType (uint32)
```

这些在 GL 后端是**动态状态**，但 **Vulkan 必须烘焙到 pipeline 中**，进一步乘倍了组合数。

---

## 二、膨胀根因分析

### 2.1 组合爆炸公式

```
总 Pipeline 数 ≈ GP变体 × FP树组合 × XP变体 × Vulkan管线状态
                  (~500)   (无上限)    (~50)    (~N倍放大)
```

### 2.2 各因素膨胀程度

| 膨胀因素 | 严重程度 | 说明 |
|---------|---------|------|
| FP 树的排列组合 | **极高** | 每种 shader + colorFilter + clip 的组合产生不同 FP 树，classID + 子树递归入 key |
| GP 属性/矩阵变体 | **高** | DefaultGeoProc 的 6 个 flag + 4 级矩阵类型 = 数百变体 |
| GrSkSLFP (Runtime Effect) | **高** | 每个不同的 SkRuntimeEffect 都是唯一 key |
| Vulkan 管线状态 | **中** | 同一 shader 因 blend/stencil/renderpass/sampleCount 不同产生多个 pipeline |
| 纹理 sampler 配置 | **中** | texture type × swizzle 入 key |
| 矩阵精度分级 | **低** | identity/scaleTranslate/affine/perspective 4 级 |

### 2.3 GrProgramDesc Key 结构详解

`GrProgramDesc` 是二进制 key，存储为 `uint32_t` 数组
（`src/gpu/ganesh/GrProgramDesc.h`），由 `Build()` → `gen_key()` 生成：

```
┌─────────────────── Base Key (跨后端通用) ───────────────────┐
│ [1] gen_geomproc_key:                                       │
│     GP classID(8bit) + GP.addToKey() + attributeKey + samplerKeys │
│ [2] gen_dstTexture_key:                                     │
│     dst texture type + swizzle + origin + inputAttachment   │
│ [3] FP header:                                              │
│     numFragmentProcessors(2bit) + numColorFPs(1bit)         │
│ [4] gen_fp_key × N (递归):                                  │
│     classID + coordTransformKey + samplerKey + addToKey()   │
│     + numChildren + [子FP key 递归]                          │
│ [5] gen_xp_key:                                             │
│     XP classID + XP.addToKey()                              │
│ [6] writeSwizzle (16bit)                                    │
│ [7] snapVerticesToPixelCenters (1bit)                       │
│ [8] isPoints (1bit)                                         │
│ [9] flush() → 记录 fInitialKeyLength                        │
├─────────────────── Vulkan 扩展 Key ─────────────────────────┤
│ kShader_PersistentCacheKeyType (uint32 = 0)                 │
│ RenderPass key (attachment formats, sampleCount, selfDep)   │
│ StencilSettings                                             │
│ Pipeline blend info (srcBlend/dstBlend/equation/writesColor)│
│ SampleCount                                                 │
│ PrimitiveType                                               │
└─────────────────────────────────────────────────────────────┘
```

**持久化缓存 key 裁剪**：存储/加载 SPIR-V 时只使用 `initialKeyLength + 4` 字节
（即 base key 部分），因为 SPIR-V 只依赖 shader 代码，不依赖管线状态。

---

## 三、优化方案

### 方案 1: Specialization Constants (Vulkan SPIR-V)

**核心思路**：利用 Vulkan 的 `VkSpecializationInfo` 在 pipeline 创建时特化常量，
而非编译时拼接不同 shader。

```glsl
// 一个通用 SPIR-V shader 模板:
layout(constant_id = 0) const int BLEND_MODE = 0;
layout(constant_id = 1) const bool HAS_COLOR_FILTER = false;
layout(constant_id = 2) const bool HAS_CLIP = false;
layout(constant_id = 3) const int MATRIX_TYPE = 0;  // 0=identity, 1=affine, 2=perspective
```

```cpp
// pipeline 创建时通过 VkSpecializationMapEntry 注入具体值
VkSpecializationMapEntry entries[] = {
    {0, offsetof(SpecData, blendMode),      sizeof(int32_t)},
    {1, offsetof(SpecData, hasColorFilter),  sizeof(VkBool32)},
    {2, offsetof(SpecData, hasClip),         sizeof(VkBool32)},
    {3, offsetof(SpecData, matrixType),      sizeof(int32_t)},
};
VkSpecializationInfo specInfo = {
    .mapEntryCount = 4,
    .pMapEntries = entries,
    .dataSize = sizeof(SpecData),
    .pData = &specData,
};
```

**优点**：
- 大幅减少 unique SPIR-V 数量（预计 50-80%），多个变体共享同一 SPIR-V 模块
- 驱动在 pipeline 创建时做死代码消除，最终 ISA 与专用 shader 性能接近
- 与 VkPipelineCache 完美配合
- 持久化缓存条目数量大幅减少

**缺点**：
- 需要重构 shader 生成逻辑，将 `addToKey()` 中的部分变量改为 spec constant
- 对 GL 后端不适用（仅 Vulkan）
- 需要验证各厂商驱动对 spec constant 死代码消除的质量

**实施路径**：
1. 在 `GrVkPipelineStateBuilder::finalize()` 中生成带 specialization constant 的 SPIR-V
2. 将 GP 矩阵类型、FP 开关 flag、XP blend mode 改为 spec constant
3. `GrProgramDesc` base key 可以合并更多变体（SPIR-V 相同，只是 spec 值不同）
4. 修改持久化缓存 key 裁剪逻辑以适应新的 key 结构

**预计效果**：Shader 减少 50-80%，Pipeline 不变但创建速度提升（共享 SPIR-V 编译结果）

### 方案 2: 减少 GrProgramDesc Key 中的无效变量

**具体措施**：

#### 2a. GP 矩阵精度统一化

将 `ComputeMatrixKey` 的 4 级合并为 2 级：

```cpp
// 修改前 (GrGeometryProcessor.h:347): 4 种变体
static uint32_t ComputeMatrixKey(...) {
    if (!caps.fReducedShaderMode) {
        if (mat.isIdentity())       return 0b00;
        if (mat.isScaleTranslate()) return 0b01;
    }
    if (!mat.hasPerspective())      return 0b10;
    return 0b11;
}

// 修改后: 2 种变体
static uint32_t ComputeMatrixKey(...) {
    if (!mat.hasPerspective()) return 0b0;
    return 0b1;
}
```

**影响**：view matrix × local matrix 从 16 种降到 4 种（4 倍减少）。
代价是 identity 和 scaleTranslate 路径多做几次乘法。

#### 2b. 移除属性布局中冗余的 offset

当前每个属性的 offset 都入 key：
```cpp
// GrGeometryProcessor.cpp:556
b->addBits(16, offset, "attrOffset");  // ← 冗余: stride+type 相同时 offset 确定
```

如果 stride 和各属性 type 相同，offset 总是固定的。可简化为只 key stride + type。

#### 2c. 纹理 swizzle 归一化

很多 swizzle 变体可以通过 output swizzle 统一处理，减少因 sampler swizzle 产生的
key 差异。

#### 2d. 启用 fReducedShaderVariations

`GrContextOptions::fReducedShaderVariations`（line 291）已存在但默认关闭。
开启后会设置 `GrShaderCaps::fReducedShaderMode`，影响数十个位置的 shader 变体：
- `ComputeMatrixKey` 跳过 identity/scaleTranslate 分支
- 多处 FP/GP 简化其 addToKey 逻辑

```cpp
GrContextOptions opts;
opts.fReducedShaderVariations = true;  // 简单开关
```

**预计效果**：Pipeline 减少 10-30%，改动量小

### 方案 3: Extended Dynamic State (减少 Vulkan Pipeline 变体)

**核心思路**：利用 `VK_EXT_extended_dynamic_state3` 将更多状态从 pipeline 烘焙中
移出变为动态设置。

当前 `GrVkPipeline::Make()` (`src/gpu/ganesh/vk/GrVkPipeline.cpp:481`) 已使用
3 种动态状态：
```cpp
dynamicStates[0] = VK_DYNAMIC_STATE_VIEWPORT;
dynamicStates[1] = VK_DYNAMIC_STATE_SCISSOR;
dynamicStates[2] = VK_DYNAMIC_STATE_BLEND_CONSTANTS;
```

可以扩展为：
```cpp
// VK_EXT_extended_dynamic_state3
dynamicStates[3] = VK_DYNAMIC_STATE_COLOR_BLEND_EQUATION_EXT;
dynamicStates[4] = VK_DYNAMIC_STATE_COLOR_BLEND_ENABLE_EXT;
dynamicStates[5] = VK_DYNAMIC_STATE_DEPTH_STENCIL_STATE; // VK_EXT_extended_dynamic_state
```

对应需要从 `GrVkCaps::makeDesc()` 的 Vulkan 扩展 key 中移除这些字段。

**优点**：
- 不改变 shader 生成逻辑
- blend state / stencil state 不再产生额外 pipeline 变体
- 对于 `PorterDuffXferProcessor`（使用硬件混合的 majority case）效果显著

**缺点**：
- 需要 Vulkan 1.3 或扩展支持，老设备不可用
- 需要 capability 检查和 fallback 路径
- 仅减少 pipeline 数，不减少 shader 数

**预计效果**：Pipeline 减少 20-50%（取决于场景中 blend/stencil 变体比例）

### 方案 4: Uber Shader (统一着色器)

**核心思路**：将多种 FP 的逻辑合并到一个大型 shader 中，通过 uniform 控制分支。

```glsl
// 不再为每种 colorFilter 生成独立 shader
uniform int u_effectType;  // 0=none, 1=matrix, 2=table, 3=blend...
uniform half4x5 u_colorMatrix;

half4 applyEffect(half4 color) {
    if (u_effectType == 0) return color;
    if (u_effectType == 1) return u_colorMatrix * color;
    if (u_effectType == 2) return tableFilter(color);
    // ...
}
```

**设计思路**：

将常见绘制模式归类为有限数量的 uber shader：

| Uber Shader | 覆盖场景 |
|------------|---------|
| `UberSimple` | 纯色 + 标准混合 |
| `UberTextured` | 单纹理 + 可选 colorMatrix + 标准混合 |
| `UberClipped` | 上述 + 裁剪(rect/rrect/circle) |
| `UberText` | 文字渲染(bitmap/SDF) |
| `UberCustom` | fallback 到当前拼接方式 |

**优点**：
- 大幅减少 shader 数量（从 O(N×M) 降到 O(N+M)）
- 适用于所有后端（GL/Vulkan/Metal/D3D）

**缺点**：
- GPU 上动态分支有性能代价（尤其低端移动设备）
- 单个 shader 编译时间可能更长
- 需要仔细设计哪些变体合并、哪些保持独立
- Uniform 数量增加

**预计效果**：Shader 减少 60-90%（常见场景），但有一定运行时性能代价

### 方案 5: Pipeline Derivatives

**核心思路**：利用 `VK_PIPELINE_CREATE_DERIVATIVE_BIT` 告知驱动一组 pipeline 高度相似。

```cpp
// 创建 base pipeline
pipelineInfo.flags = VK_PIPELINE_CREATE_ALLOW_DERIVATIVES_BIT;
vkCreateGraphicsPipelines(device, cache, 1, &pipelineInfo, nullptr, &basePipeline);

// 创建 derivative pipeline
pipelineInfo.flags = VK_PIPELINE_CREATE_DERIVATIVE_BIT;
pipelineInfo.basePipelineHandle = basePipeline;
vkCreateGraphicsPipelines(device, cache, 1, &pipelineInfo, nullptr, &derivedPipeline);
```

**注意**：当前 Skia 已有类似的优化路径——通过 `VK_EXT_pipeline_creation_cache_control`
的 `VK_PIPELINE_CREATE_FAIL_ON_PIPELINE_COMPILE_REQUIRED_BIT_EXT` 实现快速 cache
lookup（见 `GrVkPipeline.cpp:562-603`）。

**优点**：不改变 shader 生成逻辑，仅优化 pipeline 创建速度
**缺点**：不减少 shader/pipeline 数量，驱动实际优化效果因厂商而异

**预计效果**：Pipeline 创建速度提升 10-30%，数量不变

### 方案 6: 参考 Graphite 架构

Skia 的新一代后端 **Graphite** (`src/gpu/graphite/`) 正是为了解决 Ganesh 的
shader 爆炸问题而设计的：

```
Ganesh:   拼接生成 → 每种 FP 组合一个 shader → 爆炸
Graphite: PaintParamsKey + Precompilation → 预定义固定数量的 shader 组合
```

Graphite 的关键设计：
- 用 `PaintParamsKey` 将绘制参数编码为紧凑 key
- **预编译**所有可能需要的 shader 组合（数量可控）
- 使用 `ShaderCodeDictionary` 管理 shader 片段复用
- Pipeline 按 `(RenderStep, PaintParamsKey)` 组织

如果不想整体迁移到 Graphite，可以借鉴其**字典化 shader 片段 + 预编译**的思路：
1. 将 FP 的 emitCode 结果缓存在字典中（按 classID + config key）
2. shader 组装时从字典拼接，而非每次重新生成
3. 预编译高频组合，减少运行时首次绘制卡顿

---

## 四、验证方法

### 4.1 内置统计计数器

#### 4.1.1 GrThreadSafePipelineBuilder::Stats

定义在 `src/gpu/ganesh/GrThreadSafePipelineBuilder.h:22`。
编译时定义 `SK_DUMP_STATS` 或 `GPU_TEST_UTILS`（debug 默认开启）。

核心指标：

| 字段 | 含义 |
|------|------|
| `fShaderCompilations` | SkSL→SPIR-V 编译总次数 |
| `fInlineProgramCacheStats[kMiss]` | 绘制时 LRU 缓存未命中 = 新建 pipeline 数 |
| `fInlineProgramCacheStats[kHit]` | 绘制时缓存命中 |
| `fNumCompilationSuccesses` | 编译成功总数 |

```cpp
// 跑一遍测试场景后 dump
context->priv().resetGpuStats();
// ... 执行绘制场景 ...
context->flushAndSubmit(GrSyncCpu::kYes);

SkString stats;
context->priv().dumpGpuStats(&stats);
SkDebugf("%s", stats.c_str());
```

输出示例：
```
Shader Compilations: 147
Number of Inline compile failures 0
Inline Program Cache hits 1203
Inline Program Cache misses 147
Inline Program Cache hit/miss ratio: 8.18
```

#### 4.1.2 Vulkan Pipeline Cache 析构统计

`src/gpu/ganesh/vk/GrVkPipelineStateCache.cpp:29`：

```cpp
#ifdef SK_DEBUG
static const bool c_DisplayVkPipelineCache{false};  // ← 改为 true
#endif
```

context 销毁时输出：
```
--- Pipeline State Cache ---
Total requests: 1350
Cache misses: 147
Cache miss %%: 10.888889
```

### 4.2 PersistentCache 精确计数

#### 4.2.1 使用 sk_gpu_test::MemoryCache

`tools/ganesh/MemoryCache.h` 提供开箱即用的实现：

```cpp
#include "tools/ganesh/MemoryCache.h"

sk_gpu_test::MemoryCache cache;
GrContextOptions options;
options.fPersistentCache = &cache;

auto ctx = GrDirectContexts::MakeVulkan(backendContext, options);
// ... 执行绘制 ...
ctx->flushAndSubmit(GrSyncCpu::kYes);

// 唯一 shader 总数
SkDebugf("Unique shaders: %d\n", cache.numCacheStores());
SkDebugf("Cache misses:   %d\n", cache.numCacheMisses());

// 遍历每个唯一 shader
cache.foreach([](const SkData& key, const SkData& data,
                 const SkString& desc, int hitCount) {
    SkDebugf("  shader [%s] hit %d times\n", desc.c_str(), hitCount);
});
```

#### 4.2.2 Dump 所有 shader 到磁盘

```cpp
cache.writeShadersToDisk("/tmp/shaders_before/", GrBackendApi::kVulkan);
// 优化后
cache.writeShadersToDisk("/tmp/shaders_after/", GrBackendApi::kVulkan);
```

写出 `.vert`、`.frag`、`.spv`、`.key` 文件，可以：
- `ls *.spv | wc -l` 比较 shader 文件数
- `diff` 具体 shader 内容

### 4.3 GrProgramDesc Key 分析

#### 4.3.1 人类可读的 Key 描述

`GrProgramDesc::Describe()` 使用 `StringKeyBuilder` 输出带标签的字段值：

```cpp
// 在 GrVkPipelineStateBuilder::CreatePipelineState() 入口处加:
SkString descStr = GrProgramDesc::Describe(programInfo, gpu->caps());
SkDebugf("=== ProgramDesc ===\n%s\n", descStr.c_str());
```

输出：
```
fpClassID: 14
fpTransforms: 0
fpNumChildren: 2
  fpClassID: 7
  ...
xpClassID: 3
willReadDstColor: 0
isLCD: 0
stride: 20
attribute count: 3
...
```

#### 4.3.2 收集唯一 Key 做分组统计

在 `GrVkPipelineStateCache::findOrCreatePipelineStateImpl()` 中插桩：

```cpp
// src/gpu/ganesh/vk/GrVkPipelineStateCache.cpp, ~line 114
static std::set<std::vector<uint32_t>> sUniqueKeys;
static int sTotal = 0;

std::vector<uint32_t> keyVec(desc.asKey(), desc.asKey() + desc.keyLength()/4);
sUniqueKeys.insert(keyVec);
sTotal++;

if (sTotal % 100 == 0) {
    SkDebugf("[PipelineCache] total=%d, unique=%zu\n", sTotal, sUniqueKeys.size());
}
```

### 4.4 Trace Event 追踪

Skia 在 shader 路径已有 Chrome trace event：

| 位置 | 事件名 |
|------|--------|
| `GrVkPipelineStateBuilder::finalize()` | `"skia.shaders"` |
| `GrVkPipeline::Make()` | `"skia.shaders", "CreateGraphicsPipeline"` |
| `GrVkPipeline::Make()` cache lookup | `"skia.shaders", "CreateGraphicsPipeline-CacheLookup"` |

使用 Android `systrace` 或 Chrome `about:tracing` 抓取 `skia.shaders` 分类。

### 4.5 推荐的完整验证流程

```
┌────────────────────────────────────────────────────────┐
│  Step 1: 基准测量（优化前）                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │ • 定义 SK_DUMP_STATS 编译                         │  │
│  │ • 设置 MemoryCache 为 PersistentCache             │  │
│  │ • c_DisplayVkPipelineCache = true (SK_DEBUG)      │  │
│  │ • 跑固定的测试场景（如 SKP 回放 或 dm --config vk） │  │
│  │ • 记录:                                           │  │
│  │   A = Shader Compilations                         │  │
│  │   B = Inline Program Cache misses (unique pipeline)│  │
│  │   C = numCacheStores (unique shaders)             │  │
│  │   D = writeShadersToDisk → count files            │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  Step 2: 实施优化                                       │
│                                                         │
│  Step 3: 优化后测量（同一场景）                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │ • 记录 A', B', C', D'                             │  │
│  │ • Shader 减少率 = (C - C') / C × 100%            │  │
│  │ • Pipeline 减少率 = (B - B') / B × 100%          │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  Step 4: 正确性验证                                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │ • dm --config vk 跑 gold image 对比               │  │
│  │ • nanobench --config vk 确认性能无回退             │  │
│  │ • SKPBench 跑典型页面确认帧率                      │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

**最小改动快速验证代码**：

```cpp
#include "tools/ganesh/MemoryCache.h"

sk_gpu_test::MemoryCache shaderCache;
GrContextOptions opts;
opts.fPersistentCache = &shaderCache;

auto ctx = GrDirectContexts::MakeVulkan(backendContext, opts);
// ... 执行绘制 ...
ctx->flushAndSubmit(GrSyncCpu::kYes);

SkDebugf("===== Shader/Pipeline Stats =====\n");
SkDebugf("Unique shader programs: %d\n", shaderCache.numCacheStores());

SkString gpuStats;
ctx->priv().dumpGpuStats(&gpuStats);
SkDebugf("%s\n", gpuStats.c_str());

shaderCache.writeShadersToDisk("/tmp/skia_shaders/", GrBackendApi::kVulkan);
```

---

## 五、关键源码索引

### Shader 生成核心

| 文件 | 关键类/函数 |
|------|------------|
| `src/gpu/ganesh/glsl/GrGLSLProgramBuilder.h/.cpp` | 程序构建调度器, `emitAndInstallProcs()` |
| `src/gpu/ganesh/glsl/GrGLSLShaderBuilder.h/.cpp` | Shader 字符串拼接基类, `finalize()` |
| `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h/.cpp` | Fragment shader 构建器 |
| `src/gpu/ganesh/glsl/GrGLSLVertexGeoBuilder.h/.cpp` | Vertex shader 构建器 |
| `src/gpu/ganesh/glsl/GrGLSLVarying.h/.cpp` | Varying 声明管理 |
| `src/gpu/ganesh/glsl/GrGLSLUniformHandler.h/.cpp` | Uniform 声明管理 |

### 处理器体系

| 文件 | 关键类/函数 |
|------|------------|
| `src/gpu/ganesh/GrFragmentProcessor.h/.cpp` | FP 基类 + 内部 FP 子类 |
| `src/gpu/ganesh/GrGeometryProcessor.h/.cpp` | GP 基类, `ComputeMatrixKey()` |
| `src/gpu/ganesh/GrXferProcessor.h/.cpp` | XP 基类 |
| `src/gpu/ganesh/GrProcessor.h` | 处理器公共基类, ClassID |
| `src/gpu/ganesh/effects/` | 所有具体 FP/XP 子类 |

### Pipeline 描述与缓存

| 文件 | 关键类/函数 |
|------|------------|
| `src/gpu/ganesh/GrProgramDesc.h/.cpp` | Program 描述符 (缓存 key), `Build()`, `Describe()` |
| `src/gpu/ganesh/GrProgramInfo.h/.cpp` | Pipeline + GP 参数封装 |
| `src/gpu/ganesh/GrPipeline.h/.cpp` | 管线状态, `genKey()` |
| `src/gpu/ganesh/GrThreadSafePipelineBuilder.h/.cpp` | 统计计数器基类 |

### Vulkan 后端

| 文件 | 关键类/函数 |
|------|------------|
| `src/gpu/ganesh/vk/GrVkPipelineStateBuilder.h/.cpp` | Vulkan pipeline 创建, `finalize()` |
| `src/gpu/ganesh/vk/GrVkPipelineStateCache.cpp` | LRU 缓存, 析构统计 |
| `src/gpu/ganesh/vk/GrVkPipeline.h/.cpp` | `VkPipeline` 包装, `Make()` |
| `src/gpu/ganesh/vk/GrVkResourceProvider.h/.cpp` | 资源管理, `VkPipelineCache` |
| `src/gpu/ganesh/vk/GrVkCaps.cpp` | `makeDesc()` Vulkan key 扩展 (line ~1990) |

### 调试与统计工具

| 文件 | 关键类/函数 |
|------|------------|
| `tools/ganesh/MemoryCache.h/.cpp` | 测试用 PersistentCache, shader 计数与 dump |
| `src/gpu/ganesh/GrDirectContextPriv.h/.cpp` | `dumpGpuStats()`, `resetGpuStats()` |
| `src/gpu/ganesh/GrGpu.h/.cpp` | GPU 级统计, `Stats` |
| `include/gpu/ganesh/GrContextOptions.h` | `fPersistentCache`, `fReducedShaderVariations` 等 |
| `src/gpu/KeyBuilder.h` | `StringKeyBuilder` 带标签的 key 输出 |
| `include/core/SkTypes.h` | `GR_GPU_STATS`, `GR_CACHE_STATS` 编译开关 |

### 编译开关速查

| 宏 | 效果 | 默认启用条件 |
|----|------|-------------|
| `SK_DEBUG` | 开启断言 + 统计 | Debug 编译 |
| `SK_DUMP_STATS` | 开启 `GR_GPU_STATS` + `GR_CACHE_STATS` | 手动定义 |
| `GPU_TEST_UTILS` | 开启 `Stats::dump()` + 测试选项 | Debug 或 test 编译 |
| `SK_ENABLE_DUMP_GPU` | 开启 `GrDirectContext::dump()` JSON | Debug 编译 |
| `GR_GPU_STATS` | GPU/Pipeline 统计计数器 | SK_DEBUG / SK_DUMP_STATS / GPU_TEST_UTILS |
| `GR_CACHE_STATS` | 资源缓存统计 | SK_DEBUG / SK_DUMP_STATS |
