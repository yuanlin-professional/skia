# SkottiePriv.h

> 源文件: `modules/skottie/src/SkottiePriv.h`

## 概述

`SkottiePriv.h` 是 Skottie 动画引擎的核心内部头文件，定义了 `AnimationBuilder`（动画构建器）和 `SceneGraphRevalidator`（场景图重验证器）等关键内部类型。`AnimationBuilder` 是整个 Lottie JSON 解析和场景图构建过程的核心驱动类，负责解析 JSON 结构、构建场景图节点、关联动画器、管理资产和字体，并协调属性分发。该文件是理解 Skottie 内部工作原理的关键入口。

## 架构位置

该文件位于 `modules/skottie/src/` 目录下，属于 Skottie 模块的内部实现层（非公共 API）。`AnimationBuilder` 是连接公共 `Animation::Builder` API 与内部场景图构建逻辑的桥梁：

```
Animation::Builder::make() -> AnimationBuilder::parse() -> CompositionBuilder/LayerBuilder
                                    |
                                    +-> 场景图 (sksg::RenderNode)
                                    +-> 动画器 (Animator)
                                    +-> 属性分发 (PropertyObserver)
                                    +-> 插槽注册 (SlotManager)
```

## 主要类与结构体

### `SceneGraphRevalidator`
```cpp
class SceneGraphRevalidator final : public SkNVRefCnt<SceneGraphRevalidator>
```
- **职责**: 管理场景图根节点的重验证。当属性被外部修改时，调用 `revalidate()` 以恢复场景图的一致性。
- **方法**: `revalidate()`, `setRoot(sk_sp<sksg::RenderNode>)`

### `AnimationBuilder`
```cpp
class AnimationBuilder final : public SkNoncopyable
```
- **职责**: Lottie JSON 的核心解析器和场景图构建器。
- **不可复制**: 继承 `SkNoncopyable`，确保构建过程的唯一性。

### `AnimationBuilder::AnimationInfo`
```cpp
struct AnimationInfo
```
- **成员**: `fSceneRoot`（场景图根）、`fAnimators`（动画器列表）、`fSlotManager`（插槽管理器）、`fLayerInfo`（图层信息）

### `AnimationBuilder::FontInfo`
```cpp
struct FontInfo
```
- **职责**: 字体信息记录，包含字体族、样式、路径、上升高度百分比、字体对象、自定义字体构建器和变体实例。

### `AnimationBuilder::AutoScope`
```cpp
class AutoScope final
```
- **职责**: RAII 动画器作用域管理，确保在构建子树时动画器被正确收集到对应的作用域中，并在作用域结束时恢复上层作用域。

### `AnimationBuilder::AutoPropertyTracker`
```cpp
class AutoPropertyTracker
```
- **职责**: RAII 属性上下文追踪器，管理 `PropertyObserver` 的 `onEnterNode`/`onLeavingNode` 回调配对。

### `AnimationBuilder::AssetInfo` / `FootageAssetInfo`
```cpp
struct AssetInfo { const skjson::ObjectValue* fAsset; mutable bool fIsAttaching; }
struct FootageAssetInfo { sk_sp<ImageAsset> fAsset; SkISize fSize; }
```
- **职责**: 资产信息记录。`fIsAttaching` 标志用于检测循环引用。

### `AnimationBuilder::ScopedAssetRef`
```cpp
class ScopedAssetRef
```
- **职责**: RAII 资产引用，自动管理 `fIsAttaching` 标志的设置和重置，防止解析循环引用时导致无限递归。

## 公共 API 函数

（注意：这些是 internal 命名空间内的"公共"方法，对模块外部不可见）

### AnimationBuilder 核心方法

- `parse(const skjson::ObjectValue&) -> AnimationInfo`: 解析 Lottie JSON 根对象，返回完整的动画信息。
- `findFont(const SkString&) -> const FontInfo*`: 按名称查找字体信息。
- `log(Logger::Level, const skjson::Value*, const char fmt[], ...) const`: 格式化日志输出。

### 变换与效果附加方法

- `attachMatrix2D()`: 附加 2D 变换矩阵
- `attachMatrix3D()`: 附加 3D 变换矩阵
- `attachCamera()`: 附加相机变换
- `attachOpacity()`: 附加不透明度效果
- `attachPath()`: 附加路径

### 属性分发方法

- `dispatchColorProperty()`: 分发颜色属性通知
- `dispatchOpacityProperty()`: 分发不透明度属性通知
- `dispatchTextProperty()`: 分发文本属性通知
- `dispatchTransformProperty()`: 分发变换属性通知

### 图层附加方法

- `attachFootageLayer()`: 附加素材图层
- `attachNullLayer()`: 附加空图层
- `attachPrecompLayer()`: 附加预合成图层
- `attachShapeLayer()`: 附加形状图层
- `attachSolidLayer()`: 附加纯色图层
- `attachTextLayer()`: 附加文本图层
- `attachAudioLayer()`: 附加音频图层

### 模板方法

#### `attachDiscardableAdapter<T>`
```cpp
template <typename T>
void attachDiscardableAdapter(sk_sp<T> adapter) const;
```
- **功能**: 注册可丢弃的适配器。静态适配器仅触发一次同步后丢弃，动态适配器保留在当前动画器作用域中。

## 内部实现细节

- **动画器作用域栈**: `fCurrentAnimatorScope` 是一个可变指针，通过 `AutoScope` RAII 对象形成运行时栈结构，使得子合成的动画器被收集到正确的作用域中。
- **循环引用检测**: `ScopedAssetRef` 使用 `fIsAttaching` 布尔标志检测资产引用循环。当一个资产正在被附加时，如果再次被引用则说明存在循环。
- **属性上下文管理**: `AutoPropertyTracker` 在构造时从 JSON 对象的 "nm" 字段提取节点名称，设为当前属性观察者上下文，析构时恢复之前的上下文。
- **可丢弃适配器优化**: `attachDiscardableAdapter` 判断适配器是否静态（无动画关键帧），静态适配器执行一次同步后即可丢弃，不占用运行时资源。
- **mutable 成员**: 多个成员标记为 `mutable`（如 `fCurrentAnimatorScope`、`fHasNontrivialBlending`、`fImageAssetCache`），因为构建过程在 const 方法中修改状态。

## 依赖关系

- **Skia 核心**: `SkFontArguments`, `SkRefCnt`, `SkFontMgr`, `SkFontStyle`, `SkString`, `SkTypeface`
- **公共 Skottie**: `Skottie.h`, `ExternalLayer.h`, `SkottieProperty.h`, `SlotManager.h`
- **内部 Skottie**: `Animator.h`, `Font.h`
- **场景图**: `sksg::Color`, `sksg::Path`, `sksg::RenderNode`, `sksg::Transform`
- **JSON**: `skjson::ArrayValue`, `skjson::ObjectValue`, `skjson::Value`
- **文本排版**: `SkShaper_factory.h`
- **工具**: `SkUTF.h`, `SkTHash.h`

## 设计模式与设计决策

- **Builder/Director 模式**: `AnimationBuilder` 是 Builder 模式中的 Director 角色，协调多个子构建器（CompositionBuilder、LayerBuilder）完成复杂的场景图构建。
- **RAII 资源管理**: `AutoScope`、`AutoPropertyTracker`、`ScopedAssetRef` 三个 RAII 类分别管理动画器作用域、属性上下文和资产引用的生命周期。
- **Visitor 模式变体**: 图层附加方法（`attachFootageLayer` 等）按图层类型分发，类似于 Visitor 模式。
- **友元类**: `CompositionBuilder`、`CustomFont`、`LayerBuilder`、`AnimatablePropertyContainer`、`SkSLEffectBase` 被声明为友元，授予它们访问私有成员的权限。
- **常量 kBlurSizeToSigma**: 0.3f 是 After Effects 模糊大小到高斯 sigma 的近似转换系数。

## 性能考量

- **可丢弃适配器**: 静态属性的适配器在构建后立即丢弃，减少了 `seekFrame` 时需要遍历的动画器数量。
- **资产缓存**: `fImageAssetCache` 缓存已加载的素材资产，避免重复加载。
- **mutable 与 const**: 构建方法标记为 `const` 但通过 `mutable` 修改状态，这是因为构建过程从调用者视角应该是只读的（不改变构建器配置），但内部需要积累构建结果。
- **日志缓冲区**: `log()` 使用 1024 字节的栈缓冲区格式化日志消息，超长消息会被截断并附加省略号。

## 相关文件

- `modules/skottie/src/Skottie.cpp` -- AnimationBuilder 方法实现
- `modules/skottie/src/Composition.h` -- CompositionBuilder
- `modules/skottie/src/Adapter.h` -- DiscardableAdapterBase
- `modules/skottie/src/animator/Animator.h` -- 动画器基类
- `modules/skottie/src/text/Font.h` -- 自定义字体支持
- `modules/skottie/src/BlendModes.cpp` -- 混合模式附加
- `modules/skottie/src/Path.cpp` -- 路径附加
- `modules/skottie/include/Skottie.h` -- 公共 Animation 接口
