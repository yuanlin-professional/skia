# RuntimeEffectDictionary (运行时效果字典)

> 源文件：[src/gpu/graphite/RuntimeEffectDictionary.h](../../../../src/gpu/graphite/RuntimeEffectDictionary.h)、[src/gpu/graphite/RuntimeEffectDictionary.cpp](../../../../src/gpu/graphite/RuntimeEffectDictionary.cpp)

## 概述

`RuntimeEffectDictionary` 是一个轻量级字典类，用于在单次 Recording 过程中跟踪所有被使用的 `SkRuntimeEffect`（运行时着色器效果）。它维护从代码片段 ID（code snippet ID）到 `SkRuntimeEffect` 对象的映射关系，确保在绘制过程中使用到的每个运行时效果都有一个活跃的引用，同时提供一种在管线创建阶段通过代码片段 ID 检索着色器文本的途径。

每个 `RuntimeEffectDictionary` 实例的生命周期仅限于一次 Recording。在录制过程中不断填充，在 `Recorder::snap()` 时其所有权被转移给需要其内容的 `PipelineCreationTask`，之后 Recorder 会创建一个新的空字典继续使用。

## 架构位置

`RuntimeEffectDictionary` 位于着色器管线编译系统中：

- **上游**：`PaintParams` 在构建着色器键时，将遇到的 `SkRuntimeEffect` 注册到字典中。
- **下游**：`PipelineCreationTask` 在编译管线时，通过代码片段 ID 从字典中查找运行时效果的着色器文本。
- **生命周期管理**：由 `Recorder` 持有和管理，在 `snap()` 时转移所有权。

## 主要类与结构体

### `RuntimeEffectDictionary` (继承自 SkRefCnt)
引用计数的字典类，支持跨组件共享所有权。

**成员变量：**
- `fDict`：`THashMap<int, sk_sp<const SkRuntimeEffect>>`，从整数代码片段 ID 映射到运行时效果的智能指针。

## 公共 API 函数

### `find(int codeSnippetID) -> const SkRuntimeEffect*`
根据代码片段 ID 查找对应的运行时效果。返回裸指针，如果未找到则返回 `nullptr`。内联实现，零开销。

### `set(int codeSnippetID, sk_sp<const SkRuntimeEffect> effect)`
将代码片段 ID 与运行时效果关联。包含断言检查：同一代码片段 ID 不应关联不同的效果（通过 `SkRuntimeEffectPriv::Hash` 比较）。允许重复设置相同的映射。

### `empty() -> bool`
返回字典是否为空。

## 内部实现细节

- `set()` 方法在调试模式下使用 `SkRuntimeEffectPriv::Hash` 验证一致性。如果同一 ID 已存在映射，断言新旧效果的哈希值一致，防止 ID 冲突导致着色器代码不匹配。
- 使用 `sk_sp<const SkRuntimeEffect>` 保持对效果对象的强引用，确保在管线编译期间效果不会被释放。
- 继承 `SkRefCnt` 使字典可以被多个 `PipelineCreationTask` 共享，直到所有管线编译完成。

## 依赖关系

### 上游依赖
- `SkRuntimeEffect`：运行时着色器效果定义。
- `SkRuntimeEffectPriv`：运行时效果的私有工具（哈希计算）。
- `THashMap`：Skia 内部哈希映射实现。

### 下游使用者
- `Recorder`：持有并管理字典生命周期。
- `PipelineCreationTask`：编译管线时查找运行时效果。
- `ShaderCodeDictionary`：着色器代码生成时可能引用。

## 设计模式与设计决策

1. **生命周期绑定到 Recording**：每次 `snap()` 后创建新字典，避免跨 Recording 的效果引用导致内存泄漏或过期指针。

2. **ID 唯一性断言**：通过哈希比较确保同一 ID 始终指向同一效果，这是一种防御性设计，防止运行时错误。

3. **引用计数共享**：继承 `SkRefCnt` 允许多个管线创建任务持有字典引用，避免不必要的复制。

## 性能考量

- 字典操作（查找和插入）基于哈希表，时间复杂度为 O(1)。
- 字典在每次 Recording 中通常包含少量条目（仅限当前绘制使用的运行时效果），内存开销极小。
- 强引用保证了效果对象不会在使用期间被释放，但在 Recording 完成后会随字典一起清理。

## 相关文件

- `include/effects/SkRuntimeEffect.h`：运行时着色器效果公共 API。
- `src/core/SkRuntimeEffectPriv.h`：运行时效果内部工具。
- `src/gpu/graphite/ShaderCodeDictionary.h/.cpp`：着色器代码字典。
- `include/gpu/graphite/Recorder.h`：Recorder 管理字典生命周期。
