# SlotManager.h

> 源文件: `modules/skottie/include/SlotManager.h`

## 概述

`SlotManager.h` 定义了 Skottie 动画引擎的插槽管理器（Slot Manager）接口。SlotManager 是 Lottie 动画中"命名插槽"系统的核心，允许外部代码通过字符串 ID 在运行时动态修改动画中标记为"可替换"的属性值，包括颜色、标量、二维向量、图片和文本。这一机制通常用于实现动画模板系统，即同一个 Lottie 文件可以通过替换插槽内容来生成不同的视觉变体。

## 架构位置

该文件位于 `modules/skottie/include/` 目录下，属于 Skottie 模块的公共 API 层。在 Skottie 架构中，SlotManager 与 PropertyObserver 是两种互补的属性控制机制：

- **PropertyObserver**: 基于节点名称发现和操控属性，适用于通用的属性访问。
- **SlotManager**: 基于显式标记的插槽 ID 操控属性，适用于模板化的属性替换。

SlotManager 在 `Animation::Builder` 构建动画时自动创建，通过 `Builder::getSlotManager()` 获取。

## 主要类与结构体

### `SlotManager`
```cpp
class SK_API SlotManager final : public SkRefCnt
```
- **继承**: `SkRefCnt`（引用计数基类），支持通过 `sk_sp` 智能指针管理生命周期
- **final**: 不可被进一步继承
- **类型别名**: `SlotID = SkString`，使用字符串作为插槽标识符
- **职责**: 管理动画中所有命名插槽的注册、值追踪和运行时修改
- **构造**: 需要传入 `SceneGraphRevalidator` 实例，用于在值修改后触发场景图更新
- **生命周期**: 与 `Animation::Builder` 关联，在动画构建完成后通过 `getSlotManager()` 获取

### `SlotInfo`
```cpp
struct SlotInfo
```
- **职责**: 聚合所有插槽 ID 信息，按类型分类：
  - `fColorSlotIDs`: 颜色插槽 ID 列表
  - `fScalarSlotIDs`: 标量插槽 ID 列表
  - `fVec2SlotIDs`: 二维向量插槽 ID 列表
  - `fImageSlotIDs`: 图片插槽 ID 列表
  - `fTextSlotIDs`: 文本插槽 ID 列表

### `ValuePair<T>`（内部模板）
```cpp
template <typename T>
struct ValuePair
```
- **职责**: 关联一个可修改的值指针和一个用于失效通知的适配器（`AnimatablePropertyContainer`），确保值修改后能正确触发场景图更新。

## 公共 API 函数

### Setter 方法
- `setColorSlot(const SlotID&, SkColor)`: 设置颜色插槽值，内部将 SkColor 转换为浮点 RGBA
- `setImageSlot(const SlotID&, const sk_sp<skresources::ImageAsset>&)`: 设置图片插槽资产，通过代理层替换底层资产
- `setScalarSlot(const SlotID&, float)`: 设置标量插槽值（如不透明度、角度等）
- `setVec2Slot(const SlotID&, SkV2)`: 设置二维向量插槽值（如位置、缩放等）
- `setTextSlot(const SlotID&, const TextPropertyValue&)`: 设置文本插槽值，包含字体、内容、样式等完整文本属性

所有 setter 返回 `bool`：找到并更新插槽返回 `true`，ID 不存在返回 `false`。

### Getter 方法
- `getColorSlot(const SlotID&) const -> std::optional<SkColor>`: 返回颜色值或 nullopt
- `getImageSlot(const SlotID&) const -> sk_sp<const skresources::ImageAsset>`: 返回图片资产或 nullptr
- `getScalarSlot(const SlotID&) const -> std::optional<float>`: 返回标量值或 nullopt
- `getVec2Slot(const SlotID&) const -> std::optional<SkV2>`: 返回向量值或 nullopt
- `getTextSlot(const SlotID&) const -> std::optional<TextPropertyValue>`: 返回文本属性或 nullopt

所有 getter 在 SlotID 不存在时返回空值（`std::nullopt` 或 `nullptr`），调用方应检查返回值。

### 查询方法
- `getSlotInfo() const -> SlotInfo`: 返回所有已注册插槽的 ID 信息

## 内部实现细节

- **SlotMap**: 内部使用 `THashMap<SlotID, TArray<T>>` 存储每种类型的插槽映射。一个 SlotID 可以映射到多个值（即同一插槽可以关联多个场景图节点），setter 操作会更新所有关联的值。五种类型分别维护独立的 SlotMap：
  - `fColorMap`: `SlotMap<ValuePair<ColorValue*>>` -- 颜色值追踪
  - `fScalarMap`: `SlotMap<ValuePair<ScalarValue*>>` -- 标量值追踪
  - `fVec2Map`: `SlotMap<ValuePair<Vec2Value*>>` -- 二维向量值追踪
  - `fImageMap`: `SlotMap<sk_sp<ImageAssetProxy>>` -- 图片资产代理追踪
  - `fTextMap`: `SlotMap<sk_sp<TextAdapter>>` -- 文本适配器追踪
- **ImageAssetProxy**: 私有内部类，包装 `skresources::ImageAsset`，始终返回 `isMultiFrame() == true` 以强制 FootageLayer 在资产被替换后重新绘制。这是一个"宁可多查询、不可漏更新"的设计权衡。
- **track 方法**: `trackColorValue`, `trackImageValue`, `trackScalarValue`, `trackVec2Value`, `trackTextValue` 是在动画构建阶段由 `AnimationBuilder` 调用的注册方法，将场景图中的值指针和适配器注册到对应的 SlotMap 中。这些方法通过友元类声明对 `AnimationBuilder` 和 `AnimatablePropertyContainer` 可见。
- **SceneGraphRevalidator**: 每次 setter 操作后调用 `fRevalidator->revalidate()` 触发场景图重验证，确保修改的属性值正确反映到渲染结果中。
- **JSON "sid" 字段**: Lottie JSON 中通过 `"sid"` (Slot ID) 字段标记可替换的属性。在动画构建阶段，`AnimationBuilder` 解析到 `"sid"` 字段时，会调用对应的 track 方法将该属性注册到 SlotManager 中。
- **文本插槽的特殊处理**: 文本插槽不使用 `ValuePair` 模式，而是直接持有 `TextAdapter` 的智能指针。设置文本时调用 `TextAdapter::setText()`，获取文本时调用 `TextAdapter::getText()`，这是因为文本属性比简单的标量/向量值复杂得多，需要通过适配器进行完整的属性转换。
- **trackImageValue 的返回值**: `trackImageValue` 与其他 track 方法不同，它返回一个 `sk_sp<ImageAsset>`（实际是 `ImageAssetProxy`），调用方使用返回的代理替代原始资产。这使得 SlotManager 可以在运行时透明地替换底层图片。

## 依赖关系

- **Skia 核心**: `SkColor`, `SkRefCnt`, `SkString`
- **`modules/skottie/src/SkottieValue.h`**: `ColorValue`, `ScalarValue`, `Vec2Value` 值类型
- **`modules/skottie/src/text/TextAdapter.h`**: 文本适配器
- **`modules/skresources/include/SkResources.h`**: `ImageAsset` 图片资产接口
- **`src/core/SkTHash.h`**: 哈希表实现
- **`include/private/base/SkTArray.h`**: 动态数组

## 设计模式与设计决策

- **代理模式**: `ImageAssetProxy` 代理了 `ImageAsset`，添加了强制重绘逻辑。
- **观察者/中介者模式**: SlotManager 作为中介者，连接外部 API 调用与内部场景图节点。
- **一对多映射**: 同一个 SlotID 可以关联多个值，支持"一次修改影响多处"的模板化场景。
- **std::optional 返回值**: getter 使用 `std::optional` 优雅地处理 ID 不存在的情况。
- **友元类**: `AnimationBuilder` 和 `AnimatablePropertyContainer` 被声明为友元，访问私有的 track 方法。

## 性能考量

- **哈希表查找**: setter/getter 操作的时间复杂度为 O(1)（`THashMap` 查找） + O(k)（k 为同一 SlotID 关联的值数量），在绝大多数场景下 k 为 1 或非常小的常数。
- **重验证开销**: 每次 setter 调用都会触发 `revalidate()`，这会从场景图根节点开始重新验证脏子树。如需批量修改多个插槽，建议连续调用后手动触发一次重验证（当前 API 不直接支持此优化，每次 set 都会触发独立的重验证）。
- **ImageAssetProxy 的 isMultiFrame**: 强制返回 `true` 意味着图片图层每帧都会查询新帧数据（`getFrameData`），即使资产未变化也会有少量查询开销。这是正确性优先的设计选择。
- **内存占用**: 每个注册的插槽在对应的 `SlotMap` 中占用一个哈希表条目和 `TArray` 存储。对于典型的 Lottie 模板（10-50 个插槽），内存开销可以忽略不计。
- **getSlotInfo 的遍历**: `getSlotInfo()` 遍历所有五种 SlotMap 收集 ID，复杂度与总插槽数成正比。但该方法通常仅在初始化时调用一次，不影响运行时性能。

## 相关文件

- `modules/skottie/src/SlotManager.cpp` -- SlotManager 的完整实现，包括 `ImageAssetProxy` 内部类
- `modules/skottie/include/Skottie.h` -- `Animation::Builder::getSlotManager()` 获取 SlotManager
- `modules/skottie/include/SkottieProperty.h` -- `TextPropertyValue` 等属性值类型定义
- `modules/skottie/src/SkottiePriv.h` -- `AnimationBuilder` 在构建阶段调用 track 方法
- `modules/skottie/src/Skottie.cpp` -- `AnimationBuilder::parse()` 中处理 `"slots"` JSON 字段
- `modules/skottie/src/SkottieValue.h` -- `ColorValue`, `ScalarValue`, `Vec2Value` 内部值类型
- `modules/skottie/src/text/TextAdapter.h` -- 文本适配器，`setText()`/`getText()` 方法
- `modules/skottie/src/animator/Animator.h` -- `AnimatablePropertyContainer` 适配器基类
- `modules/skresources/include/SkResources.h` -- `ImageAsset` 图片资产接口

### 使用示例（概念性）

```
// 构建动画
auto builder = skottie::Animation::Builder();
auto animation = builder.make(data, length);
auto slotMgr = builder.getSlotManager();

// 查询可用插槽
auto info = slotMgr->getSlotInfo();

// 修改颜色插槽
slotMgr->setColorSlot("primary_color", SK_ColorRED);

// 修改文本插槽
TextPropertyValue text;
text.fText = SkString("Hello");
slotMgr->setTextSlot("title_text", text);

// 渲染修改后的动画
animation->seekFrame(0);
animation->render(canvas);
```
