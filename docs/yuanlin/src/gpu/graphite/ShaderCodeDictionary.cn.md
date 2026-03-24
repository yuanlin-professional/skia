# ShaderCodeDictionary (着色器代码字典)

> 源文件：[src/gpu/graphite/ShaderCodeDictionary.h](../../../../src/gpu/graphite/ShaderCodeDictionary.h)、[src/gpu/graphite/ShaderCodeDictionary.cpp](../../../../src/gpu/graphite/ShaderCodeDictionary.cpp)

## 概述

`ShaderCodeDictionary` 是 Graphite 着色器系统的核心组件，管理着色器代码片段（Snippets）的注册、组合和去重。它维护内置代码片段和运行时效果（SkRuntimeEffect）的映射关系，提供通过 `PaintParamsKey` 查找和创建 `UniquePaintParamsID` 的能力，并最终支持从效果树生成完整的 SkSL 着色器代码。

每个 `PaintParamsKey` 表示一棵效果树的序列化形式，可以被解压为 `ShaderNode` 树。`ShaderCodeDictionary` 对相同的键进行去重，返回唯一的 `UniquePaintParamsID`，从而确保相同的着色器配置共享同一个管线。

## 架构位置

`ShaderCodeDictionary` 位于着色器编译系统的核心：

- **上游**：`PaintParamsKeyBuilder` 根据绘制参数构建 `PaintParamsKey`。
- **下游**：`ShaderInfo::Make()` 使用字典将键展开为 ShaderNode 树并生成 SkSL 代码。
- **全局共享**：由 `SharedContext` 持有，跨 Recorder 共享，使用自旋锁保护并发访问。

## 主要类与结构体

### `ShaderSnippet`
描述一个着色器代码片段的 ABI（应用二进制接口）：
- `fName` / `fStaticFunctionName`：片段名称和静态函数名。
- `fSnippetRequirementFlags`：需求标志（局部坐标、前置阶段输出、混合器 dst 颜色等）。
- `fUniforms`：所需 uniform 列表。
- `fTexturesAndSamplers`：纹理和采样器列表。
- `fNumChildren`：子节点数量。
- `fPreambleGenerator`：自定义的着色器前导代码生成函数。
- `fLiftableExpressionGenerator`：可提升到顶点着色器的表达式生成器。

### `ShaderNode`
代码片段在效果树中的节点表示：
- 指向 `ShaderSnippet` 的指针。
- 子节点列表。
- 代码 ID 和键索引。
- 需求标志（从子节点向根传播）。
- 内联数据。

### `SnippetRequirementFlags` (位掩码枚举)
标志位包括：局部坐标、前置阶段输出、混合器目标颜色、原始颜色、梯度缓冲区、采样器描述数据、透传局部坐标、可提升表达式等。

### `ShaderCodeDictionary`
**核心功能：**
- 管理内置代码片段（`BuiltInCodeSnippetID`）和运行时效果片段。
- `PaintParamsKey` -> `UniquePaintParamsID` 的去重映射。
- 提供着色器代码生成所需的元数据。

## 公共 API 函数

### 键管理
- `findOrCreate(PaintParamsKey) -> UniquePaintParamsID`：查找或创建唯一的着色器参数 ID。
- `lookup(UniquePaintParamsID) -> PaintParamsKey`：根据 ID 查找对应的键。

### 片段注册
- 内置片段通过 `BuiltInCodeSnippetID` 枚举索引。
- 运行时效果通过 `findOrCreateRuntimeEffectSnippet(SkRuntimeEffect)` 注册。

### 着色器生成
- `getEntry(codeID) -> ShaderSnippet*`：获取代码片段定义。
- `idToString(Caps*, UniquePaintParamsID) -> SkString`：将 ID 转为可读标签。

## 内部实现细节

### 效果树与 PaintParamsKey
- `PaintParamsKey` 是效果树的序列化二进制表示。
- 键被解压为 `ShaderNode` 树（使用 `SkArenaAlloc` 分配）。
- 树中每个节点对应一个代码片段，按深度优先遍历序列化。

### 需求标志传播
构建 `ShaderNode` 时，子节点的需求标志向父节点传播（如需要局部坐标）。运行时效果和 compose 节点有特殊的传播规则。

### 线程安全
字典使用 `SkSpinlock` 保护键映射的并发读写，因为多个 Recorder 线程可能同时注册新的着色器配置。

### 可提升表达式
某些着色器表达式可以从片段着色器提升到顶点着色器（如坐标变换），通过 `LiftableExpressionType` 和相关生成器实现。这减少了片段着色器的指令数。

## 依赖关系

- `PaintParamsKey` / `PaintParamsKeyBuilder`：键的构建和序列化。
- `UniquePaintParamsID`：去重后的唯一标识。
- `BuiltInCodeSnippetID`：内置效果枚举。
- `SkRuntimeEffect`：运行时着色器效果。
- `ShaderInfo`：着色器代码生成。
- `Uniform` / `TextureAndSampler`：数据绑定描述。

## 设计模式与设计决策

1. **效果树序列化**：使用扁平的 `PaintParamsKey` 表示效果树，支持高效比较和哈希。
2. **全局去重**：相同的着色器配置全局唯一，避免重复编译。
3. **代码片段 ABI**：每个片段定义明确的输入/输出签名和需求标志，支持组合。
4. **表达式提升**：优化片段着色器性能，将可在顶点阶段计算的表达式移至顶点着色器。

## 性能考量

- 键的哈希和比较是 O(键长度)，通常很短。
- 自旋锁保护的临界区很小（仅映射查找/插入），竞争低。
- 全局去重显著减少管线编译次数。
- 可提升表达式减少片段着色器的 ALU 压力。

## 相关文件

- `src/gpu/graphite/PaintParamsKey.h/.cpp`：着色器参数键。
- `src/gpu/graphite/PaintParams.h/.cpp`：绘制参数封装。
- `src/gpu/graphite/BuiltInCodeSnippetID.h`：内置效果 ID。
- `src/gpu/graphite/ShaderInfo.h/.cpp`：着色器代码生成。
- `src/gpu/graphite/UniquePaintParamsID.h`：唯一着色器 ID。
