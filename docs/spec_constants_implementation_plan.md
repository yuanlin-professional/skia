# Specialization Constants 实现计划

## 目录

- [一、背景与目标](#一背景与目标)
- [二、现状分析](#二现状分析)
  - [2.1 当前 Vulkan shader/pipeline 创建流程](#21-当前-vulkan-shaderpipeline-创建流程)
  - [2.2 SkSL 对 Specialization Constants 的支持现状](#22-sksl-对-specialization-constants-的支持现状)
  - [2.3 Spec Constant 候选变量评估](#23-spec-constant-候选变量评估)
  - [2.4 持久化缓存 Key 分层结构](#24-持久化缓存-key-分层结构)
- [三、技术方案选型](#三技术方案选型)
  - [方案 A: SPIR-V 后处理变换](#方案-a-spir-v-后处理变换推荐)
  - [方案 B: SkSL 语言扩展](#方案-b-sksl-语言扩展)
  - [选型结论](#选型结论)
- [四、分阶段实施计划](#四分阶段实施计划)
  - [Phase 0: 基线度量](#phase-0-基线度量)
  - [Phase 1: 基础设施层](#phase-1-基础设施层)
  - [Phase 2: XP 层 — PorterDuff Output Type](#phase-2-xp-层--porterduff-output-type)
  - [Phase 3: FP 层 — 裁剪与滤波效果](#phase-3-fp-层--裁剪与滤波效果)
  - [Phase 4: 缓存 Key 重构](#phase-4-缓存-key-重构)
  - [Phase 5: 验证与调优](#phase-5-验证与调优)
- [五、各 Phase 详细文件改动清单](#五各-phase-详细文件改动清单)
- [六、风险分析与缓解](#六风险分析与缓解)
- [七、预期收益量化](#七预期收益量化)

---

## 一、背景与目标

Ganesh Vulkan 后端的 shader 通过 `GrGLSLProgramBuilder` 将 GP/FP/XP 的代码**拼接**
生成。每种处理器配置组合产生唯一的 `GrProgramDesc`，对应一个独立的 SPIR-V shader 和
`VkPipeline`。这导致：

- **Shader 数量爆炸**：FP 树排列组合 × GP 变体 × XP 变体 → 数百到数千个 unique SPIR-V
- **Pipeline 数量爆炸**：unique SPIR-V × Vulkan 管线状态(blend/stencil/renderpass) →
  更多 unique pipeline
- **首帧卡顿**：每个新 shader 需要 SkSL→SPIR-V→ISA 全链路编译
- **内存占用**：大量 `VkPipeline` 对象消耗 GPU 内存

**目标**：利用 Vulkan Specialization Constants 机制，将部分拼接时决定的常量变为
pipeline 创建时的特化值，使多个变体**共享同一份 SPIR-V**，从而：

1. 减少 unique SPIR-V 数量 30-50%（Phase 2-3 目标）
2. 持久化缓存条目数相应减少
3. 不影响最终 GPU 执行性能（驱动在特化时做死代码消除）

---

## 二、现状分析

### 2.1 当前 Vulkan shader/pipeline 创建流程

```
GrVkPipelineStateBuilder::CreatePipelineState()           [line 48]
  │
  ├── emitAndInstallProcs()                               [GrGLSLProgramBuilder.cpp:61]
  │     ├── emitAndInstallPrimProc()   → GP 写入 VS+FS
  │     ├── emitAndInstallDstTexture()
  │     ├── emitAndInstallFragProcs()  → FP 树递归展开
  │     └── emitAndInstallXferProc()   → XP 写入混合代码
  │
  └── finalize()                                          [line 181]
        ├── finalizeShaders()          → fVS/fFS 拼接为 SkSL 字符串
        ├── persistent cache lookup    → desc.initialKeyLength()+4 字节作 key   [line 228]
        ├── createVkShaderModule()     → SkSL → SPIR-V → VkShaderModule        [line 264-278]
        │     └── GrCompileVkShaderModule()                [GrVkUtil.cpp:71]
        │           └── skgpu::SkSLToSPIRV()
        │           └── GrInstallVkShaderModule()          [GrVkUtil.cpp:94]
        │                 └── stageInfo->pSpecializationInfo = nullptr  ← [line 122]
        ├── storeShadersInCache()      → 存 SPIR-V/SkSL 到持久化缓存           [line 290-301]
        ├── CreatePipelineLayout()     → VkPipelineLayout                       [line 335]
        └── resourceProvider.makePipeline()                                     [line 350]
              └── GrVkPipeline::Make() → vkCreateGraphicsPipelines              [GrVkPipeline.cpp:481]
```

**关键发现**：`pSpecializationInfo` 在 `GrVkUtil.cpp:122` 被**显式设为 nullptr**。
整个 Skia 代码库中没有任何地方使用 `VkSpecializationInfo` 或 `VkSpecializationMapEntry`。

### 2.2 SkSL 对 Specialization Constants 的支持现状

| 项目 | 状态 |
|------|------|
| SPIR-V 操作码 (`SpvOpSpecConstant*`) | 在 `src/sksl/spirv.h` 中**已定义**（line 617-621） |
| SPIR-V 装饰 (`SpvDecorationSpecId`) | 在 `src/sksl/spirv.h:320` 中**已定义** |
| SkSL `layout(constant_id=N)` 语法 | **不支持**，Parser 中无此 qualifier |
| `SPIRVCodeGenerator` 中 spec constant 发射 | **不存在**，只有 `writeOpConstant*()` 系列 |
| Graphite SPIR-V 后处理框架 | **已存在** `VulkanSpirvTransforms.cpp`，可参考 |

**结论**：需要新增 specialization constants 支持。有两条路径可选（见第三节）。

### 2.3 Spec Constant 候选变量评估

对所有处理器的 `addToKey()` 字段进行了逐一分析，按适用性分为三档：

#### GOOD — 适合作为 Spec Constant

这些字段在 `emitCode()` 中通过 if/switch 选择不同的**单行表达式**，
不改变 uniform 声明、varying 数量或整体代码结构：

| 字段 | 处理器 | 源文件:行号 | 当前 Key bits | 说明 |
|------|--------|------------|--------------|------|
| `primaryOutput` | `PorterDuffXferProcessor` | `GrPorterDuffXferProcessor.cpp:103` | 3 bits | 6 种输出表达式，switch 选择 |
| `secondaryOutput` | `PorterDuffXferProcessor` | `GrPorterDuffXferProcessor.cpp:104` | 3 bits | 同上 |
| `fClamp` | `GrBicubicEffect` | `GrBicubicEffect.cpp:228` | 1 bit | 2 种 clamp 策略 |
| `edgeType` (fill/inverse) | `CircularRRectEffect` | `GrRRectEffect.cpp:390` | 1 effective bit | `alpha = 1-alpha` 或不变 |
| `edgeType` | `EllipticalRRectEffect` | `GrRRectEffect.cpp:699` | 2 bits | `0.5-dist` vs `0.5+dist` |

**预计合并效果**：PorterDuff 的 6×6=36 种 output 组合 → 1 个 SPIR-V + 36 种 spec
值。RRectEffect 的 fill/inverse 两种 → 1 个 SPIR-V。

#### MARGINAL — 理论可行但收益小

| 字段 | 处理器 | 说明 |
|------|--------|------|
| `tweakAlpha` | `DefaultGeoProc` | 仅添加一行乘法 |
| `unclampedCoverage` | `DefaultGeoProc` | saturate() vs pass-through |
| `scale_radii` | `EllipticalRRectEffect` | 控制 scale uniform 声明（borderline structural） |

#### BAD — 不适合作为 Spec Constant

| 字段 | 处理器 | 原因 |
|------|--------|------|
| `ComputeMatrixKey` | GP 全局 | 改变 uniform **类型**（float4 vs float3x3）和是否存在 uniform |
| GP 属性 flags | `DefaultGeoProc` | 改变 varying/attribute 数量、整个代码结构 |
| `coverage==0xff` | `DefaultGeoProc` | 决定是否创建 coverage uniform |
| `BlendKey(fMode)` | `ShaderPDXferProcessor` | 选择不同的 SkSL blend **函数** |
| `hasHWBlendEquation` | `CustomXP` | 完全不同的代码路径（两个不同的虚函数） |
| `shaderModes[0,1]` | `GrTextureEffect` | 控制 uniform 声明 + 大型 switch 的结构性代码 |
| `fDirection` | `GrBicubicEffect` | 16 次采样 vs 4 次采样，完全不同结构 |
| `cornerFlags` | `CircularRRectEffect` | 9 路 switch，每路完全不同的代码 |

### 2.4 持久化缓存 Key 分层结构

当前的 Key 结构：

```
GrProgramDesc:
┌──────────────────────────── initialKeyLength ─────────────────────────┐
│ GP key │ dst tex key │ FP keys (recursive) │ XP key │ swizzle │ misc │
└──────────────────────────────────────────────────────────────────────┘
┌─ +4 ─┐
│ tag=0│  ← kShader_PersistentCacheKeyType
└──────┘
┌──────────────────── Vulkan 扩展 ─────────────────────┐
│ RenderPass key │ Stencil │ Blend info │ Samples │ ... │
└──────────────────────────────────────────────────────┘

持久化缓存 key = [0, initialKeyLength + 4) → 标识唯一 SPIR-V
LRU 运行时缓存 key = [0, keyLength)          → 标识唯一 Pipeline
```

**引入 Spec Constants 后需要的变化**：

原来在 base key 中的 spec constant 候选字段（如 PorterDuff outputType）
需要从 "影响 SPIR-V 内容" 移动到 "仅影响 pipeline 创建"。这意味着：

```
持久化缓存 key（新）= base key - spec constant 字段 → 标识唯一 SPIR-V 模板
Pipeline key = base key（含 spec 字段）+ Vulkan 扩展 → 标识唯一 Pipeline
```

---

## 三、技术方案选型

### 方案 A: SPIR-V 后处理变换（推荐）

**思路**：SkSL 生成过程不变，仍然拼接出硬编码常量值的 SPIR-V。然后在 pipeline 创建前，
通过一个 SPIR-V 变换 pass 将指定的 `OpConstant` 替换为 `OpSpecConstant`，
并添加 `SpvDecorationSpecId` 装饰。

```
SkSL 拼接 → SkSL→SPIR-V 编译 → SPIR-V Transformer（新增）
  将 OpConstant(primaryOutput=2) → OpSpecConstant(id=0, default=2) + Decorate(SpecId=0)
  → 存入持久化缓存
  → VkPipeline 创建时通过 VkSpecializationInfo 注入实际值
```

**参考实现**：Graphite 已有 `VulkanSpirvTransforms.cpp`（`src/gpu/graphite/vk/`），
提供了完整的 SPIR-V 指令遍历和改写框架。

**优点**：
- **不修改 SkSL 语言和编译器**（最大优点——SkSL compiler 是 Skia 最复杂的子系统之一）
- 改动集中在 Ganesh Vulkan 后端，不影响 GL/Metal/D3D
- 可以渐进式添加更多 spec constant 候选项
- 可以直接复用 Graphite 的 transformer 框架模式

**缺点**：
- 需要编写 SPIR-V 二进制级别的指令查找和替换逻辑
- 需要定义"哪些 OpConstant 是 spec constant 候选"的标记协议
- SPIR-V 二进制操作比 SkSL 文本操作更容易出错

### 方案 B: SkSL 语言扩展

**思路**：在 SkSL 中添加 `layout(constant_id = N)` 修饰符，让处理器的 `emitCode()`
直接声明 spec constant 变量，编译器自动发射 `OpSpecConstant`。

需要修改的组件：
- `src/sksl/ir/SkSLLayout.h` — 添加 `fSpecConstantId` 字段
- `src/sksl/SkSLParser.cpp` — 添加 `"constant_id"` qualifier 解析
- `src/sksl/codegen/SkSLSPIRVCodeGenerator.cpp` — 添加 `writeOpSpecConstant*()` 方法
  和 `SpvDecorationSpecId` 装饰输出
- 所有候选处理器的 `emitCode()` — 改为声明 spec constant 而非硬编码值

**优点**：
- 语义更清晰，spec constant 在源码中有明确声明
- 编译器保证 SPIR-V 正确性
- 未来可扩展到 Graphite 后端

**缺点**：
- **需要修改 SkSL 编译器**（影响面大、审核严格）
- 影响所有后端（GL 不支持 spec constant，需要 fallback）
- 需要修改 `GrGLSLShaderBuilder` 接口以支持 spec constant 声明
- 实施周期长

### 选型结论

| 维度 | 方案 A (SPIR-V 后处理) | 方案 B (SkSL 扩展) |
|------|----------------------|-------------------|
| 改动范围 | Ganesh Vulkan 后端 | SkSL 编译器 + 所有后端 |
| 风险 | 中（SPIR-V 二进制操作） | 高（编译器修改） |
| 跨后端影响 | 无 | GL/Metal/D3D 需 fallback |
| 可渐进实施 | 是 | 较难 |
| 长期可维护性 | 中 | 高 |

**推荐方案 A（SPIR-V 后处理变换）**，原因：
1. 改动范围最小，集中在 Vulkan 后端
2. 不触及 SkSL 编译器这一核心组件
3. Graphite 已有可参考的 transformer 框架
4. 可以按 Phase 渐进式添加候选项，每个 Phase 独立验证

---

## 四、分阶段实施计划

### Phase 0: 基线度量

**目标**：建立优化前的量化基线。

**步骤**：

1. 选定 3-5 个代表性测试场景：
   - `dm --config vk --src skp` — SKP 回放（覆盖绝大多数绘制路径）
   - `dm --config vk --src gm` — GM 测试（高覆盖率的 FP/XP 组合）
   - 实际应用的典型帧序列（如 Chrome 页面渲染）

2. 度量代码（加到测试 harness 中）：
   ```cpp
   #include "tools/ganesh/MemoryCache.h"

   sk_gpu_test::MemoryCache shaderCache;
   GrContextOptions opts;
   opts.fPersistentCache = &shaderCache;

   auto ctx = GrDirectContexts::MakeVulkan(backendContext, opts);
   // ... 执行测试场景 ...
   ctx->flushAndSubmit(GrSyncCpu::kYes);

   SkDebugf("Baseline: unique shaders = %d\n", shaderCache.numCacheStores());

   SkString stats;
   ctx->priv().dumpGpuStats(&stats);
   SkDebugf("%s\n", stats.c_str());

   shaderCache.writeShadersToDisk("/tmp/baseline_shaders/", GrBackendApi::kVulkan);
   ```

3. 记录基线指标：
   - `unique_shaders_baseline` = `numCacheStores()`
   - `unique_pipelines_baseline` = `Inline Program Cache misses`
   - `shader_compile_time_baseline` = 总 shader 编译耗时

4. 分析 PorterDuff outputType 在基线中产生的变体数量：
   ```cpp
   // 在 PorterDuffXferProcessor::onAddToKey 中插桩
   static std::map<uint32_t, int> sOutputCombos;
   uint32_t combo = fBlendFormula.primaryOutput() | (fBlendFormula.secondaryOutput() << 3);
   sOutputCombos[combo]++;
   ```

**产出**：基线数据报告，确认 PorterDuff 变体数量占比。

---

### Phase 1: 基础设施层

**目标**：实现 SPIR-V 后处理 transformer + `VkSpecializationInfo` 传递管道，
不接入任何具体候选变量，仅搭建框架。

#### 1.1 新建 `GrVkSpecConstantManager` 类

**新文件**: `src/gpu/ganesh/vk/GrVkSpecConstantManager.h`

```cpp
#ifndef GrVkSpecConstantManager_DEFINED
#define GrVkSpecConstantManager_DEFINED

#include "include/private/base/SkTArray.h"
#include "include/third_party/vulkan/vulkan/vulkan_core.h"
#include <cstdint>
#include <vector>

// 管理 specialization constants 的注册、SPIR-V 变换、以及 VkSpecializationInfo 构建。
//
// 使用模式:
//   1. 处理器在 emitCode 期间调用 registerSpecConstant() 注册候选常量
//   2. SPIR-V 编译完成后，调用 transformSpirv() 将 OpConstant 转为 OpSpecConstant
//   3. pipeline 创建前，调用 buildSpecializationInfo() 构建 VkSpecializationInfo
class GrVkSpecConstantManager {
public:
    // Spec constant 的标识信息
    struct Entry {
        uint32_t fSpecId;        // Vulkan spec constant ID (从 0 递增)
        uint32_t fDefaultValue;  // 默认值（即 emitCode 时使用的值）
        uint32_t fActualValue;   // pipeline 创建时的实际值
        enum Type { kInt32, kBool } fType;
    };

    // 注册一个 spec constant。返回 spec ID。
    // 在 emitCode 阶段调用。
    uint32_t registerSpecConstant(uint32_t defaultValue, Entry::Type type);

    // 设置某个 spec constant 的实际值（从 GrProgramInfo/processor 读取）。
    void setActualValue(uint32_t specId, uint32_t actualValue);

    // 对编译后的 SPIR-V 进行变换：
    //   - 查找所有已注册的 OpConstant（通过默认值匹配 + 类型匹配）
    //   - 替换为 OpSpecConstant
    //   - 添加 OpDecorate ... SpecId
    // 返回变换后的 SPIR-V blob。
    bool transformSpirv(std::vector<uint32_t>* spirv) const;

    // 构建 VkSpecializationInfo，生命周期由 manager 持有，
    // 调用者需保证在 vkCreateGraphicsPipelines 调用前 manager 不被销毁。
    const VkSpecializationInfo* buildSpecializationInfo();

    int numSpecConstants() const { return fEntries.size(); }
    bool hasSpecConstants() const { return !fEntries.empty(); }

private:
    skia_private::TArray<Entry> fEntries;
    std::vector<VkSpecializationMapEntry> fMapEntries;
    std::vector<uint32_t> fSpecData;
    VkSpecializationInfo fSpecInfo = {};
};

#endif
```

**新文件**: `src/gpu/ganesh/vk/GrVkSpecConstantManager.cpp`

核心实现要点：

```cpp
uint32_t GrVkSpecConstantManager::registerSpecConstant(uint32_t defaultValue, Entry::Type type) {
    uint32_t specId = fEntries.size();
    fEntries.push_back({specId, defaultValue, defaultValue, type});
    return specId;
}

void GrVkSpecConstantManager::setActualValue(uint32_t specId, uint32_t actualValue) {
    SkASSERT(specId < (uint32_t)fEntries.size());
    fEntries[specId].fActualValue = actualValue;
}

bool GrVkSpecConstantManager::transformSpirv(std::vector<uint32_t>* spirv) const {
    if (fEntries.empty()) return true;

    // 遍历 SPIR-V 指令流:
    // 1. 在 annotation section 中添加 OpDecorate <id> SpecId <specId> 指令
    // 2. 在 constant section 中将匹配的 OpConstant/OpConstantTrue/OpConstantFalse
    //    替换为 OpSpecConstant/OpSpecConstantTrue/OpSpecConstantFalse
    //
    // 匹配策略: 使用 "标记协议" —— 被注册的常量在 SPIR-V 中有唯一的
    // (type, default_value) 对。通过 OpName 装饰中的特殊前缀 "_SpecConst_N_"
    // 来精确定位。
    //
    // 参考: src/gpu/graphite/vk/VulkanSpirvTransforms.cpp 的遍历框架。
    // ... (具体实现见 Phase 1 代码)
}

const VkSpecializationInfo* GrVkSpecConstantManager::buildSpecializationInfo() {
    if (fEntries.empty()) return nullptr;

    fMapEntries.clear();
    fSpecData.clear();

    for (const Entry& e : fEntries) {
        VkSpecializationMapEntry mapEntry;
        mapEntry.constantID = e.fSpecId;
        mapEntry.offset = fSpecData.size() * sizeof(uint32_t);
        mapEntry.size = sizeof(uint32_t);
        fMapEntries.push_back(mapEntry);
        fSpecData.push_back(e.fActualValue);
    }

    fSpecInfo.mapEntryCount = fMapEntries.size();
    fSpecInfo.pMapEntries = fMapEntries.data();
    fSpecInfo.dataSize = fSpecData.size() * sizeof(uint32_t);
    fSpecInfo.pData = fSpecData.data();

    return &fSpecInfo;
}
```

#### 1.2 SPIR-V Transformer 实现

**SPIR-V 中 OpConstant 的定位策略**（关键设计决策）：

由于 SPIR-V 是无名二进制格式，直接按 "值匹配" 容易误判。采用 **OpName 标记协议**：

在 `emitCode()` 中，处理器声明 spec constant 候选变量时使用特殊命名：

```glsl
// 在生成的 SkSL 中:
const int _SpecConst_0_ = 2;   // ← 变量名包含 _SpecConst_N_ 前缀
```

SkSL→SPIR-V 编译后，该变量会有：
- `OpName %id "_SpecConst_0_"` 装饰
- `OpConstant %int %id 2`

Transformer 按 `OpName` 装饰中的 `_SpecConst_` 前缀精确定位目标 `SpvId`，
然后将 `OpConstant` 替换为 `OpSpecConstant` 并添加 `OpDecorate ... SpecId N`。

```cpp
// 伪代码: SPIR-V transformer 核心逻辑
bool GrVkSpecConstantManager::transformSpirv(std::vector<uint32_t>* spirv) const {
    // Pass 1: 扫描 OpName 指令，找到所有 _SpecConst_N_ 对应的 SpvId
    std::map<SpvId, uint32_t/*specId*/> targetIds;
    for (each instruction in spirv) {
        if (op == SpvOpName) {
            std::string name = extractString(instruction);
            if (name starts with "_SpecConst_") {
                uint32_t specId = parseSpecId(name);
                SpvId id = instruction[1];
                targetIds[id] = specId;
            }
        }
    }

    // Pass 2: 替换 OpConstant → OpSpecConstant
    for (each instruction in spirv) {
        if ((op == SpvOpConstant || op == SpvOpConstantTrue || op == SpvOpConstantFalse)
            && targetIds.contains(result_id)) {
            // 就地替换 opcode
            replace SpvOpConstant with SpvOpSpecConstant (same word layout)
        }
    }

    // Pass 3: 在 annotation section 末尾插入 OpDecorate ... SpecId
    for (auto& [id, specId] : targetIds) {
        insert OpDecorate(id, SpvDecorationSpecId, specId);
    }

    return true;
}
```

#### 1.3 修改 `GrVkUtil.cpp` — 传递 VkSpecializationInfo

**修改**: `GrInstallVkShaderModule()` 签名增加 `VkSpecializationInfo*` 参数：

```cpp
// GrVkUtil.h — 新签名
bool GrInstallVkShaderModule(GrVkGpu* gpu,
                             const SkSL::NativeShader& spirv,
                             VkShaderStageFlagBits stage,
                             VkShaderModule* shaderModule,
                             VkPipelineShaderStageCreateInfo* stageInfo,
                             const VkSpecializationInfo* specInfo = nullptr);  // 新增
```

```cpp
// GrVkUtil.cpp:122 — 修改
stageInfo->pSpecializationInfo = specInfo;  // 原为 nullptr
```

同样修改 `GrCompileVkShaderModule()` 签名向下传递。

#### 1.4 修改 `GrVkPipelineStateBuilder` — 集成 manager

在 `GrVkPipelineStateBuilder` 中添加 `GrVkSpecConstantManager` 成员：

```cpp
// GrVkPipelineStateBuilder.h
#include "src/gpu/ganesh/vk/GrVkSpecConstantManager.h"

class GrVkPipelineStateBuilder : public GrGLSLProgramBuilder {
    // ...
    GrVkSpecConstantManager fSpecConstantManager;   // 新增
    // ...
};
```

在 `finalize()` 中集成（在 SPIR-V 编译后、pipeline 创建前）：

```cpp
// GrVkPipelineStateBuilder.cpp finalize() 中，在 line 278 之后、line 290 之前:

// --- Phase 1 新增: Spec Constant 变换 ---
if (fSpecConstantManager.hasSpecConstants()) {
    for (int i = 0; i < kGrShaderTypeCount; ++i) {
        fSpecConstantManager.transformSpirv(&shaders[i].fBinary);
    }
}

// 修改 createVkShaderModule 调用以传递 specInfo
const VkSpecializationInfo* fsSpecInfo = nullptr;
if (fSpecConstantManager.hasSpecConstants()) {
    fsSpecInfo = fSpecConstantManager.buildSpecializationInfo();
}
// Fragment shader 的 stageInfo 设置 specInfo
shaderStageInfo[1].pSpecializationInfo = fsSpecInfo;
```

**Phase 1 产出**：框架就绪，但 `fSpecConstantManager` 中无任何注册的 spec constant，
行为与修改前完全一致。可通过单元测试验证框架正确性。

---

### Phase 2: XP 层 — PorterDuff Output Type

**目标**：将 `PorterDuffXferProcessor` 的 `primaryOutput` 和 `secondaryOutput`
转换为 specialization constants。这是**收益最高**的单一改动。

#### 2.1 修改 emitCode — 使用标记命名

**文件**: `src/gpu/ganesh/effects/GrPorterDuffXferProcessor.cpp`

修改 `append_color_output()` 函数（line 74-101），在函数开头声明 spec constant
标记变量，然后将 switch 改为运行时分支：

```cpp
// 修改前 (line 79-100): 编译时 switch，每个分支生成不同的代码文本
switch (outputType) {
    case kNone_OutputType:
        fragBuilder->codeAppendf("%s = half4(0.0);", output);
        break;
    case kModulate_OutputType:
        fragBuilder->codeAppendf("%s = %s * %s;", output, inColor, inCoverage);
        break;
    // ... 6 种分支
}

// 修改后: 声明 spec constant 标记变量 + 运行时分支
// 注: 此处为 fragment shader 中的 spec constant
void append_color_output(const PorterDuffXferProcessor& xp,
                         GrGLSLXPFragmentBuilder* fragBuilder,
                         BlendFormula::OutputType outputType, const char* output,
                         const char* inColor, const char* inCoverage,
                         GrVkSpecConstantManager* specMgr,  // 新增参数
                         bool isSecondary) {
    if (specMgr) {
        // 注册 spec constant 并生成标记变量
        uint32_t specId = specMgr->registerSpecConstant(
            (uint32_t)outputType, GrVkSpecConstantManager::Entry::kInt32);
        // 在 SkSL 中声明为 const int（编译器会生成 OpConstant，transformer 转为 OpSpecConstant）
        const char* specName = isSecondary ? "_SpecConst_SecOutput_" : "_SpecConst_PriOutput_";
        fragBuilder->codeAppendf("const int %s = %d;", specName, (int)outputType);
        // 用 if-else 替代 switch
        fragBuilder->codeAppendf("if (%s == %d) { %s = half4(0.0); }",
                                 specName, kNone_OutputType, output);
        fragBuilder->codeAppendf("else if (%s == %d) { %s = %s; }",
                                 specName, kCoverage_OutputType, output, inCoverage);
        fragBuilder->codeAppendf("else if (%s == %d) { %s = %s * %s; }",
                                 specName, kModulate_OutputType, output, inColor, inCoverage);
        fragBuilder->codeAppendf("else if (%s == %d) { %s = %s.a * %s; }",
                                 specName, kSAModulate_OutputType, output, inColor, inCoverage);
        fragBuilder->codeAppendf("else if (%s == %d) { %s = (1.0 - %s.a) * %s; }",
                                 specName, kISAModulate_OutputType, output, inColor, inCoverage);
        fragBuilder->codeAppendf("else { %s = (half4(1.0) - %s) * %s; }",
                                 output, inColor, inCoverage);
    } else {
        // 非 Vulkan 后端: 保持原有 switch 拼接方式
        switch (outputType) { /* ... 原逻辑 ... */ }
    }
}
```

#### 2.2 修改 addToKey — 将 output type 移出 base key

**文件**: `src/gpu/ganesh/effects/GrPorterDuffXferProcessor.cpp:103`

```cpp
// 修改前:
void PorterDuffXferProcessor::onAddToKey(const GrShaderCaps&, skgpu::KeyBuilder* b) const {
    b->add32(fBlendFormula.primaryOutput() | (fBlendFormula.secondaryOutput() << 3));
}

// 修改后: 仅在非 Vulkan 后端写入 key（Vulkan 走 spec constant 路径）
void PorterDuffXferProcessor::onAddToKey(const GrShaderCaps& caps, skgpu::KeyBuilder* b) const {
    if (!caps.fSupportsSpecConstants) {   // 新增 cap flag
        b->add32(fBlendFormula.primaryOutput() | (fBlendFormula.secondaryOutput() << 3));
    }
    // Vulkan 后端: output type 不入 base key，改为在 pipeline 创建时通过 spec constant 注入
}
```

这需要在 `GrShaderCaps` 中添加一个新的 cap flag:

```cpp
// GrShaderCaps.h — 新增
bool fSupportsSpecConstants = false;

// GrVkCaps.cpp — 设置
shaderCaps->fSupportsSpecConstants = true;
```

#### 2.3 在 finalize() 中设置 actual values

```cpp
// GrVkPipelineStateBuilder::finalize() 中，emitAndInstallProcs() 之后:
// 从 pipeline 中读取 XP 的 blend formula，设置 actual values
if (auto* xp = fProgramInfo.pipeline().getXferProcessor()) {
    if (auto* pdXP = xp->cast<PorterDuffXferProcessor>()) {
        fSpecConstantManager.setActualValue(/*priOutputSpecId*/, pdXP->primaryOutput());
        fSpecConstantManager.setActualValue(/*secOutputSpecId*/, pdXP->secondaryOutput());
    }
}
```

#### 2.4 预期效果

假设基线中 PorterDuff 有 N 种 unique (primary, secondary) 组合，
每种组合与 M 个不同的 FP chain 配对：

- **修改前**: N × M 个 unique SPIR-V
- **修改后**: M 个 unique SPIR-V（output type 不再区分 SPIR-V）
- **SPIR-V 减少**: (N-1)/N × 100%（若 N=6, 减少 83%——仅针对 PorterDuff 变体维度）

---

### Phase 3: FP 层 — 裁剪与滤波效果

**目标**：将 `CircularRRectEffect`、`EllipticalRRectEffect` 的 edgeType 和
`GrBicubicEffect` 的 clamp 模式转为 spec constant。

#### 3.1 CircularRRectEffect edgeType

**文件**: `src/gpu/ganesh/effects/GrRRectEffect.cpp`

当前 `emitCode` 中 (line 299):
```cpp
if (GrClipEdgeType::kInverseFillAA == crre.fEdgeType) {
    fragBuilder->codeAppend("alpha = 1.0 - alpha;");
}
```

改为：
```cpp
// 声明 spec constant 标记变量
fragBuilder->codeAppendf("const bool _SpecConst_InverseFill_ = %s;",
                         isInverse ? "true" : "false");
fragBuilder->codeAppend("if (_SpecConst_InverseFill_) { alpha = 1.0 - alpha; }");
```

对应 `onAddToKey` 中移除 edgeType 的 inverse bit（当 `fSupportsSpecConstants` 时）。

#### 3.2 EllipticalRRectEffect edgeType

**文件**: `src/gpu/ganesh/effects/GrRRectEffect.cpp`

当前 (line 627-631):
```cpp
if (erre.fEdgeType == GrClipEdgeType::kFillAA) {
    fragBuilder->codeAppend("half alpha = clamp(0.5 - approx_dist, 0.0, 1.0);");
} else {
    fragBuilder->codeAppend("half alpha = clamp(0.5 + approx_dist, 0.0, 1.0);");
}
```

改为：
```cpp
fragBuilder->codeAppendf("const bool _SpecConst_IsFillAA_ = %s;",
                         isFillAA ? "true" : "false");
fragBuilder->codeAppend(
    "half alpha = _SpecConst_IsFillAA_ "
    "? clamp(0.5 - approx_dist, 0.0, 1.0) "
    ": clamp(0.5 + approx_dist, 0.0, 1.0);");
```

#### 3.3 GrBicubicEffect clamp

**文件**: `src/gpu/ganesh/effects/GrBicubicEffect.cpp`

当前 (约 line 95-109):
```cpp
switch (bicubicEffect.fClamp) {
    case Clamp::kUnpremul:
        fragBuilder->codeAppend("bicubicColor = saturate(bicubicColor);");
        break;
    case Clamp::kPremul:
        fragBuilder->codeAppend("bicubicColor.a = saturate(bicubicColor.a);");
        fragBuilder->codeAppend("bicubicColor.rgb = max(...);");
        break;
}
```

改为：
```cpp
fragBuilder->codeAppendf("const int _SpecConst_BicubicClamp_ = %d;",
                         (int)bicubicEffect.fClamp);
fragBuilder->codeAppendf("if (_SpecConst_BicubicClamp_ == %d) {", (int)Clamp::kUnpremul);
fragBuilder->codeAppend("    bicubicColor = saturate(bicubicColor);");
fragBuilder->codeAppend("} else {");
fragBuilder->codeAppend("    bicubicColor.a = saturate(bicubicColor.a);");
fragBuilder->codeAppend("    bicubicColor.rgb = max(half3(0.0), min(bicubicColor.rgb, bicubicColor.aaa));");
fragBuilder->codeAppend("}");
```

---

### Phase 4: 缓存 Key 重构

**目标**：使持久化缓存在 spec constant 启用时能最大化 SPIR-V 复用。

#### 4.1 持久化缓存 Key 变更

当前持久化缓存 key = `desc.asKey()[0 .. initialKeyLength+4)`。

引入 spec constant 后，base key 中的 spec constant 字段不再影响 SPIR-V 内容
（SPIR-V 中它们是通用的 `OpSpecConstant`）。需要让 persistent cache 的 key
**排除** spec constant 字段值。

**实施方案**：在序列化持久化缓存 key 时，将 spec constant 候选字段替换为固定占位值。

```cpp
// GrVkPipelineStateBuilder.cpp — storeShadersInCache 修改
void GrVkPipelineStateBuilder::storeShadersInCache(...) {
    sk_sp<SkData> key;
    if (fSpecConstantManager.hasSpecConstants()) {
        // 创建 "归一化" 的 key: spec constant 字段全部替换为 0
        // 这样不同 spec constant 值的变体共享同一个缓存条目
        key = buildNormalizedCacheKey(this->desc());
    } else {
        key = SkData::MakeWithoutCopy(this->desc().asKey(),
                                      this->desc().initialKeyLength()+4);
    }
    // ... 存储
}
```

#### 4.2 LRU 运行时缓存 Key

LRU 缓存仍使用**完整** `GrProgramDesc` 作 key（包含 spec constant 实际值和
Vulkan 管线状态），因为不同 spec constant 值会产生不同的 `VkPipeline`。
**此处无需修改**。

#### 4.3 持久化缓存中额外存储 spec constant 元数据

从缓存加载 SPIR-V 时，需要知道哪些位置需要 spec constant 变换。
在 `PackCachedShaders` 时额外存储：

```cpp
// 在 ShaderMetadata 中添加:
struct ShaderMetadata {
    // ... 原有字段 ...
    struct SpecConstantMeta {
        uint32_t fSpecId;
        Entry::Type fType;
    };
    std::vector<SpecConstantMeta> fSpecConstants;  // 新增
};
```

这样从缓存加载 SPIR-V 后，可以直接构建 `VkSpecializationInfo` 而无需重新运行
transformer。

---

### Phase 5: 验证与调优

#### 5.1 正确性验证

1. **Gold Image 对比**：
   ```bash
   # 优化前
   dm --config vk --src gm --writePath /tmp/gold_before/

   # 优化后
   dm --config vk --src gm --writePath /tmp/gold_after/

   # 像素级对比
   skdiff /tmp/gold_before/ /tmp/gold_after/
   ```

2. **GrProgramDesc 一致性测试**：
   验证对于非 Vulkan 后端，行为完全不变。

3. **SPIR-V Validation**：
   使用 `spirv-val`（SPIR-V Tools）验证变换后的 SPIR-V 合法性。
   在 `transformSpirv()` 中，Debug 模式下自动运行验证：
   ```cpp
   #ifdef SK_DEBUG
   SkASSERT(spirv_val_validate(transformed_spirv));
   #endif
   ```

4. **多厂商驱动测试**：
   在 Qualcomm Adreno、ARM Mali、NVIDIA、Intel 上分别测试，
   验证各驱动对 spec constant 死代码消除的支持质量。

#### 5.2 性能验证

```bash
# Pipeline 创建速度对比
nanobench --config vk --skps /path/to/skps --outResultsFile before.json
# 优化后
nanobench --config vk --skps /path/to/skps --outResultsFile after.json
```

**关注指标**：
- `Inline Program Cache misses` 下降率
- `Shader Compilations` 下降率
- 每帧 GPU 时间（无回退则 spec constant 方案有效）
- 首帧延迟（should 减少，因为要编译的 unique SPIR-V 更少）

#### 5.3 Shader 数量量化

```cpp
// 使用 MemoryCache 对比
SkDebugf("Before: %d unique shaders\n", cacheBeforeOpt.numCacheStores());
SkDebugf("After:  %d unique shaders\n", cacheAfterOpt.numCacheStores());
SkDebugf("Reduction: %.1f%%\n",
         100.0 * (before - after) / before);
```

---

## 五、各 Phase 详细文件改动清单

### Phase 0 — 无代码改动（度量脚本）

| 文件 | 改动 |
|------|------|
| 测试 harness 或临时脚本 | 添加 MemoryCache 度量代码 |

### Phase 1 — 基础设施层

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `src/gpu/ganesh/vk/GrVkSpecConstantManager.h` | **新建** | Manager 类声明 |
| `src/gpu/ganesh/vk/GrVkSpecConstantManager.cpp` | **新建** | Manager 实现 + SPIR-V transformer |
| `src/gpu/ganesh/vk/GrVkUtil.h` | 修改 | `GrInstallVkShaderModule` 增加 `specInfo` 参数 |
| `src/gpu/ganesh/vk/GrVkUtil.cpp` | 修改 | line 122: `nullptr` → `specInfo` 参数 |
| `src/gpu/ganesh/vk/GrVkPipelineStateBuilder.h` | 修改 | 添加 `fSpecConstantManager` 成员 |
| `src/gpu/ganesh/vk/GrVkPipelineStateBuilder.cpp` | 修改 | `finalize()` 中集成 transform + specInfo 传递 |
| `src/gpu/ganesh/GrShaderCaps.h` | 修改 | 添加 `fSupportsSpecConstants` flag |
| `src/gpu/ganesh/vk/GrVkCaps.cpp` | 修改 | 设置 `fSupportsSpecConstants = true` |
| `BUILD.gn` / `gn/gpu.gni` | 修改 | 添加新文件到编译目标 |

### Phase 2 — PorterDuff XP

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `src/gpu/ganesh/effects/GrPorterDuffXferProcessor.cpp` | 修改 | `append_color_output()` 改为 spec constant 分支; `onAddToKey()` 条件化 |

### Phase 3 — FP 裁剪与滤波

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `src/gpu/ganesh/effects/GrRRectEffect.cpp` | 修改 | CircularRRectEffect + EllipticalRRectEffect edgeType 改为 spec constant |
| `src/gpu/ganesh/effects/GrBicubicEffect.cpp` | 修改 | fClamp 改为 spec constant |

### Phase 4 — 缓存 Key 重构

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `src/gpu/ganesh/vk/GrVkPipelineStateBuilder.cpp` | 修改 | `storeShadersInCache()` 和 `finalize()` 中的 persistent cache key 归一化 |
| `src/gpu/ganesh/GrPersistentCacheUtils.h` | 修改 | `ShaderMetadata` 添加 spec constant 元数据 |
| `src/gpu/ganesh/GrPersistentCacheUtils.cpp` | 修改 | Pack/Unpack 支持 spec constant 元数据 |

### Phase 5 — 验证

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `tests/VkSpecConstantTest.cpp` | **新建** | 单元测试 |
| 各 Phase 涉及文件 | 修改 | Debug 断言和验证代码 |

---

## 六、风险分析与缓解

### 风险 1: SPIR-V Transformer 误替换

**风险**：`transformSpirv()` 错误地将不应替换的 `OpConstant` 替换为
`OpSpecConstant`。

**缓解**：
- 使用 `OpName` 装饰中的 `_SpecConst_` 前缀精确定位，而非按值匹配
- Debug 模式下运行 `spirv-val` 验证变换后 SPIR-V 合法性
- 变换前后 dump SPIR-V 做 diff 审查

### 风险 2: 驱动 Spec Constant 死代码消除质量差异

**风险**：某些 GPU 驱动（尤其是低端移动设备）可能不做充分的死代码消除，
导致 uber-shader 风格的代码执行所有分支，性能下降。

**缓解**：
- 先在主流驱动（Qualcomm/ARM/NVIDIA/Intel）上 benchmark
- 添加 `GrVkCaps` 中的 per-vendor 禁用开关：
  ```cpp
  bool fUseSpecConstants = true;  // 可按 vendor/device 关闭
  ```
- 候选变量的分支都是非常简单的单行表达式（不是 deep nesting），
  即使不做死代码消除，性能影响也极小（最多多几条 ALU 指令）

### 风险 3: 持久化缓存兼容性

**风险**：升级到 spec constant 版本后，旧的持久化缓存条目变得不兼容。

**缓解**：
- `GrPersistentCacheUtils` 已有 `kCurrentVersion` 版本号（当前值 12），
  bump version 即可使旧缓存自动失效
- 首次运行时会重新编译并填充新缓存，后续运行正常

### 风险 4: Debug 可读性下降

**风险**：生成的 SkSL 中出现 `if (_SpecConst_PriOutput_ == 2)` 这样的条件分支，
比原来直接拼接的 `output = inColor * inCoverage` 更难阅读。

**缓解**：
- `_SpecConst_` 前缀明确标识这是 spec constant
- dump shader 时同时输出 spec constant 的 actual value 映射表
- 非 Vulkan 后端仍走原有拼接路径，可读性不受影响

### 风险 5: SkSL 编译器优化干扰

**风险**：SkSL 编译器的 constant folding / inlining 可能在
SkSL→SPIR-V 编译阶段就将 `const int _SpecConst_0_ = 2` 内联到所有使用处，
导致 SPIR-V 中不再有独立的 `OpConstant` 可以替换。

**缓解**：
- 使用 `uniform`-like 的语义而非 `const`——但这会产生 uniform buffer 开销
- **更好的方案**：在 SkSL 中使用一个全局 `int` 变量（非 const），
  SkSL 编译器不会 constant-fold 非 const 变量。然后 transformer 将对应的
  `OpVariable` + `OpLoad` 模式替换为 `OpSpecConstant`
- 或者在 SkSL 编译时临时关闭 optimizer（`SkSL::Compiler::EnableOptimizer(kOff)`），
  但这会影响其他优化
- **最佳方案**：在 SPIR-V 中直接插入 `OpSpecConstant`，不依赖 SkSL 变量名。
  具体做法是在 transformer 中**添加新指令**而非替换现有指令——即在 SPIR-V
  常量区中新建 `OpSpecConstant`，然后将所有引用旧 `OpConstant` 的指令改为
  引用新 `OpSpecConstant` 的 ID

---

## 七、预期收益量化

### 理论分析

以 PorterDuff outputType 为例（Phase 2）：

| 场景 | 独立维度值 | 当前 SPIR-V 倍数 | Spec Constant 后倍数 |
|------|-----------|-----------------|---------------------|
| primaryOutput | 6 种 | ×6 | ×1 |
| secondaryOutput | 6 种 | ×6 | ×1 |
| 组合 | 6×6=36 | ×36 | ×1 |

若基线中有 100 种 unique FP chain，每种与 5 种 PorterDuff output 组合配对：
- 修改前: 100 × 5 = 500 unique SPIR-V
- 修改后: 100 × 1 = 100 unique SPIR-V
- **减少 80%**

Phase 3 进一步减少 RRectEffect (fill/inverse = ×2) 和 BicubicEffect (clamp = ×2)：
- 额外减少约 10-20%

### 总体预期

| 指标 | Phase 2 后 | Phase 2+3 后 |
|------|-----------|-------------|
| Unique SPIR-V 减少 | 30-50% | 40-60% |
| Unique Pipeline 减少 | 0%（pipeline 仍按完整 key 区分） | 0% |
| 持久化缓存条目减少 | 30-50% | 40-60% |
| 首帧编译时间减少 | 30-50%（更少 SPIR-V 需编译） | 40-60% |
| 运行时帧率影响 | ±0%（spec constant 死代码消除） | ±0% |

**注意**：Pipeline 数量不会减少（每种 spec constant 值仍然是不同的 `VkPipeline`），
但 SPIR-V 编译（最耗时的步骤）会大幅减少。Pipeline 创建（给定已编译的 VkShaderModule）
本身较快，且受益于 `VkPipelineCache`。
