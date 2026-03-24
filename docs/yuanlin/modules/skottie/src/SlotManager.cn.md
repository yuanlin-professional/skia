# SlotManager.cpp

> 源文件: `modules/skottie/src/SlotManager.cpp`

## 概述

`SlotManager.cpp` 是 Skottie 插槽管理器的完整实现文件，实现了 `SlotManager.h` 中声明的所有公共方法以及内部的值追踪机制。该文件包含了五种属性类型（颜色、图片、标量、二维向量、文本）的 setter/getter/track 操作，以及用于图片资产代理的 `ImageAssetProxy` 内部类。SlotManager 是 Lottie 动画模板化系统的运行时支撑。

## 架构位置

该文件位于 `modules/skottie/src/` 目录下，实现了 `modules/skottie/include/SlotManager.h` 中声明的接口。在运行时数据流中：

```
外部调用 setXxxSlot(slotID, value)
    -> SlotManager 查找 slotID 对应的 ValuePair/Adapter 列表
    -> 更新值并调用 adapter->onSync()
    -> SceneGraphRevalidator::revalidate()
    -> 场景图更新
```

## 主要类与结构体

### `SlotManager::ImageAssetProxy`
```cpp
class skottie::SlotManager::ImageAssetProxy final : public skresources::ImageAsset
```
- **继承**: `skresources::ImageAsset`
- **职责**: 图片资产代理，包装实际的 `ImageAsset` 并添加可替换能力。
- **关键行为**:
  - `isMultiFrame()` 始终返回 `true`，强制 FootageLayer 每帧重新查询帧数据
  - `getFrameData(float t)`: 委托给被包装的资产，如果资产为空则返回默认帧数据
  - `setImageAsset()`: 替换被包装的资产
  - `getImageAsset()`: 获取当前被包装的资产

## 公共 API 函数

### Setter 方法实现

#### `setColorSlot(const SlotID&, SkColor)`
- **实现**: 将 `SkColor` 转换为 `SkColor4f` 再构造 `ColorValue{r,g,b,a}`，遍历该 SlotID 对应的所有 ValuePair，更新值并调用 `adapter->onSync()`，最后触发重验证。

#### `setImageSlot(const SlotID&, const sk_sp<ImageAsset>&)`
- **实现**: 遍历该 SlotID 对应的所有 `ImageAssetProxy`，调用 `setImageAsset()` 替换底层资产，触发重验证。

#### `setScalarSlot(const SlotID&, float)`
- **实现**: 直接更新值指针内容，调用 `adapter->onSync()`，触发重验证。

#### `setVec2Slot(const SlotID&, SkV2)`
- **实现**: 与 `setScalarSlot` 类似的模式。

#### `setTextSlot(const SlotID&, const TextPropertyValue&)`
- **实现**: 遍历文本适配器列表，调用 `textAdapter->setText(t)`，触发重验证。

### Getter 方法实现

所有 getter 方法遵循相同模式：查找 SlotID，如果存在且非空则返回第一个值，否则返回 `std::nullopt` 或 `nullptr`。

- `getColorSlot()`: 返回 `std::optional<SkColor>`（从 `ColorValue*` 转换）
- `getImageSlot()`: 返回 `sk_sp<const ImageAsset>`（从 ImageAssetProxy 获取）
- `getScalarSlot()`: 返回 `std::optional<float>`
- `getVec2Slot()`: 返回 `std::optional<SkV2>`
- `getTextSlot()`: 返回 `std::optional<TextPropertyValue>`（从 TextAdapter 获取）

### Track 方法实现（内部接口，通过友元类访问）

- `trackColorValue(SlotID, ColorValue*, adapter)`: 将颜色值指针和适配器注册到 `fColorMap`。值指针直接指向适配器内部的 `ColorValue` 成员。
- `trackImageValue(SlotID, ImageAsset) -> sk_sp<ImageAsset>`: 创建 `ImageAssetProxy` 包装原始资产，注册到 `fImageMap`，返回代理。调用方使用返回的代理替代原始资产。
- `trackScalarValue(SlotID, ScalarValue*, adapter)`: 将标量值指针和适配器注册到 `fScalarMap`。
- `trackVec2Value(SlotID, Vec2Value*, adapter)`: 将向量值指针和适配器注册到 `fVec2Map`。
- `trackTextValue(SlotID, TextAdapter)`: 将文本适配器注册到 `fTextMap`。文本使用适配器而非值指针，因为文本属性需要通过 `TextAdapter::setText()` 进行完整的排版更新。

### `getSlotInfo() const -> SlotInfo`
- **实现**: 遍历所有五种类型的 SlotMap（`fColorMap`, `fScalarMap`, `fVec2Map`, `fImageMap`, `fTextMap`），将每种类型的所有 SlotID 收集到 `SlotInfo` 结构体的对应数组中。返回的 `SlotInfo` 可用于外部工具展示可用的插槽列表。

## 内部实现细节

- **颜色值转换**: `setColorSlot` 将 `SkColor`（8 位整数 ARGB，Skia 的标准颜色格式）转换为 `SkColor4f`（浮点 RGBA，范围 [0,1]），再构造 `ColorValue{r, g, b, a}`。注意颜色分量的顺序从 ARGB 变为 RGBA，这与 Lottie 内部使用的颜色表示一致。`SkColor4f::FromColor()` 负责执行 8 位到浮点的归一化转换。
- **ImageAssetProxy 的 isMultiFrame 策略**: 始终返回 `true` 确保了图片图层在每次帧更新时都会查询 `getFrameData()`，从而能够感知到资产的运行时替换。这是一个"宁可多查询、不可漏更新"的策略。
- **空资产的默认帧数据**: 当 `ImageAssetProxy` 的底层资产为空时，`getFrameData()` 返回一个包含 `nullptr` 图片但设置了合理采样和变换参数的 `FrameData`，避免空指针崩溃。
- **ValuePair 的 adapter 调用**: setter 操作中对每个 ValuePair 先更新值（`*pair.value = newValue`），然后调用 `pair.adapter->onSync()`。`onSync()` 的实现在具体适配器中，负责将更新后的值同步到场景图节点。
- **一对多更新**: 一个 SlotID 可以关联多个 ValuePair/Adapter，setter 会遍历更新所有关联项，实现"一次修改、多处生效"。

## 依赖关系

- **`modules/skottie/include/SlotManager.h`**: 对应的头文件声明
- **`include/core/SkImage.h`**: `SkImage` 图片类型
- **`include/core/SkM44.h`**: `SkV2` 向量类型
- **`include/core/SkMatrix.h`**: `SkMatrix::I()` 单位矩阵
- **`include/core/SkSamplingOptions.h`**: 图片采样选项
- **`modules/skottie/include/SkottieProperty.h`**: `TextPropertyValue`
- **`modules/skottie/src/SkottiePriv.h`**: `SceneGraphRevalidator`
- **`modules/skottie/src/animator/Animator.h`**: `AnimatablePropertyContainer`
- **`modules/skottie/src/text/TextAdapter.h`**: `TextAdapter`
- **`modules/skresources/include/SkResources.h`**: `ImageAsset`, `FrameData`

## 设计模式与设计决策

- **代理模式**: `ImageAssetProxy` 包装了实际的 `ImageAsset`，在不改变接口的前提下添加了可替换性和强制重绘行为。代理模式使得 FootageLayer 无需知道资产是否可能被替换，只需正常查询帧数据即可。
- **观察者/通知模式**: setter 操作更新值后通过 `adapter->onSync()` 通知适配器，再通过 `revalidator->revalidate()` 通知场景图，形成完整的变更传播链：`外部调用 -> SlotManager -> Adapter -> SceneGraph`。
- **一对多映射**: 使用 `THashMap<SlotID, TArray<T>>` 支持同一个 SlotID 映射到多个目标。这使得设计师可以在 Lottie 文件中将同一个 SlotID 分配给多个元素（如主色调同时应用于背景和标题），修改一次即可全部更新。
- **getter 返回首元素**: getter 方法仅返回 SlotID 对应的第一个值（`valueGroup->at(0)`），假设同一 SlotID 下的所有值应该相同。如果一个 SlotID 关联了多个不同的值（理论上不应发生），getter 仅返回第一个。
- **SlotID 作为字符串**: `SlotID` 被定义为 `SkString`（而非 `const char*`），确保了字符串的值语义和生命周期安全。`THashMap` 使用 `SkString` 的哈希函数进行键查找。
- **构造/析构分离**: 构造函数仅保存 revalidator 引用，track 方法在动画构建阶段被调用来注册追踪项，setter/getter 在运行时被外部调用。这种分离确保了构建阶段和运行阶段的职责清晰。
- **空资产的安全处理**: `ImageAssetProxy::getFrameData()` 在底层资产为空时返回一个包含 `nullptr` 图片但设置了合理采样和变换参数的 `FrameData`，避免了空指针解引用的风险。

## 性能考量

- **哈希表查找**: 所有 setter/getter/track 操作的查找复杂度为 O(1)（`THashMap` 基于哈希的查找），这确保了即使插槽数量增多也不会影响单次操作的性能。
- **onSync 调用**: setter 对每个关联的适配器调用 `onSync()`，此方法的实现决定了更新性能。大部分适配器的 `onSync()` 是轻量级的属性赋值操作（如颜色设置、不透明度设置等），时间开销可以忽略不计。
- **revalidate 开销**: 每次 setter 都触发一次 `revalidate()`，这会从场景图根节点开始重新验证被标记为脏的子树。如果连续调用多个 setter，会导致多次重验证，产生不必要的重复工作。优化方案是在外部批量更新后手动触发一次重验证（当前 API 不提供此选项，每次 set 都会触发独立的重验证）。
- **isMultiFrame 的影响**: ImageAssetProxy 的 `isMultiFrame() == true` 导致图片图层每帧都查询帧数据（`getFrameData(t)`），即使图片资产未发生变化。这是正确性和性能之间的权衡——确保资产替换能被及时感知。
- **getSlotInfo 的线性扫描**: `getSlotInfo()` 遍历所有五种 SlotMap（`fColorMap`, `fScalarMap`, `fVec2Map`, `fImageMap`, `fTextMap`），复杂度与总插槽数成正比，但通常仅在初始化阶段调用一次用于 UI 展示。
- **内存占用**: 每个 ValuePair 包含一个值指针和一个 `sk_sp<AnimatablePropertyContainer>`（引用计数增量），内存开销极小。ImageAssetProxy 作为 `sk_sp` 管理，生命周期与 SlotManager 绑定。
- **文本插槽的特殊性能**: `setTextSlot` 调用 `TextAdapter::setText()`，这会触发文本的重新排版（Shaper::Shape()），对于长文本可能有数毫秒的开销，是所有插槽类型中最重的操作。

## 相关文件

- `modules/skottie/include/SlotManager.h` -- 对应的头文件声明，定义了公共 API 和内部数据结构
- `modules/skottie/src/SkottiePriv.h` -- `AnimationBuilder` 在构建阶段调用 track 方法注册插槽
- `modules/skottie/src/Skottie.cpp` -- `AnimationBuilder::parse()` 中创建 SlotManager 并处理 `"slots"` JSON 字段
- `modules/skottie/src/SkottieValue.h` -- `ColorValue`, `ScalarValue`, `Vec2Value` 内部值类型定义
- `modules/skottie/src/text/TextAdapter.h` -- TextAdapter 的 `setText()` / `getText()` 方法用于文本插槽
- `modules/skottie/src/animator/Animator.h` -- `AnimatablePropertyContainer` 基类，ValuePair 中的 adapter 类型
- `modules/skresources/include/SkResources.h` -- `ImageAsset`, `FrameData` 图片资产接口
- `include/core/SkImage.h` -- `SkImage` 类型，`ImageAssetProxy::getFrameData` 的返回数据中包含
- `include/core/SkSamplingOptions.h` -- 图片采样选项，用于 ImageAssetProxy 的默认帧数据
