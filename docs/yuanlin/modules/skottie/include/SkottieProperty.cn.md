# SkottieProperty.h

> 源文件: `modules/skottie/include/SkottieProperty.h`

## 概述

`SkottieProperty.h` 是 Skottie 动画引擎的属性系统公共头文件，定义了动画属性的值类型、属性句柄以及属性观察者接口。该文件是 Skottie 属性操控系统的核心，允许外部代码在运行时读取和修改 Lottie 动画中的颜色、不透明度、文本和变换等关键属性，实现动画的动态定制。这是 Skottie 实现"数据驱动动画"的关键基础设施。

## 架构位置

该文件位于 `modules/skottie/include/` 目录下，属于 Skottie 模块的公共 API 层。在 Skottie 的属性系统架构中，它扮演"用户侧接口"的角色：

```
用户代码 <-> PropertyObserver/PropertyHandle <-> Internal Adapters <-> Scene Graph Nodes
```

`PropertyHandle` 是用户面向的 AE（After Effects）模型值与内部场景图表示之间的适配器。

## 主要类与结构体

### `GlyphDecorator`
```cpp
class GlyphDecorator : public SkRefCnt
```
- **职责**: 可选的回调接口，在绘制文本图层时被调用，允许客户端渲染自定义文本装饰效果。
- **内部结构**:
  - `GlyphInfo`: 单个字形的信息（边界、矩阵、簇索引、水平步进）
  - `TextInfo`: 文本信息（字形数组和自动缩放比例）

### `TextPropertyValue`
```cpp
struct TextPropertyValue
```
- **职责**: 文本属性值的完整描述，包含字体、内容、尺寸、对齐、颜色、描边等所有文本相关参数。
- **关键字段**:
  - `fTypeface`: 字体
  - `fText`: 文本内容
  - `fTextSize`, `fMinTextSize`, `fMaxTextSize`: 字号及自动缩放范围
  - `fHAlign`, `fVAlign`: 水平/垂直对齐
  - `fResize`, `fLineBreak`, `fDirection`, `fCapitalization`: 排版控制
  - `fFillColor`, `fStrokeColor`: 填充/描边颜色
  - `fLocale`, `fFontFamily`: 本地化和字体族信息

### `TransformPropertyValue`
```cpp
struct TransformPropertyValue
```
- **职责**: 2D 变换属性值，包含锚点、位置、缩放、旋转、倾斜参数。
- **字段**:
  - `fAnchorPoint` (`SkPoint`): 变换锚点
  - `fPosition` (`SkPoint`): 位置
  - `fScale` (`SkVector`): 缩放
  - `fRotation` (`SkScalar`): 旋转角度
  - `fSkew` (`SkScalar`): 倾斜
  - `fSkewAxis` (`SkScalar`): 倾斜轴角度

### `PropertyHandle<ValueT, NodeT>`
```cpp
template <typename ValueT, typename NodeT>
class SK_API PropertyHandle final
```
- **职责**: 属性句柄模板，作为用户代码与内部场景图节点之间的适配器。通过 `get()` 和 `set()` 方法读写属性值。
- **模板参数**: `ValueT` 为属性值类型，`NodeT` 为内部场景图节点类型。
- **具体特化**:
  - `ColorPropertyHandle`: `PropertyHandle<SkColor, sksg::Color>`
  - `OpacityPropertyHandle`: `PropertyHandle<float, sksg::OpacityEffect>`
  - `TextPropertyHandle`: `PropertyHandle<TextPropertyValue, internal::TextAdapter>`
  - `TransformPropertyHandle`: `PropertyHandle<TransformPropertyValue, internal::TransformAdapter2D>`

### `PropertyObserver`
```cpp
class SK_API PropertyObserver : public SkRefCnt
```
- **职责**: 属性观察者接口，在动画解析时接收属性通知。注册到 `Animation::Builder` 后，会在解析过程中回调相关属性。
- **节点类型枚举**: `NodeType { COMPOSITION, LAYER, EFFECT, OTHER }` -- 标识当前正在解析的节点类型
- **LazyHandle**: `std::function<std::unique_ptr<T>()>` 延迟创建句柄，避免不必要的开销。只有调用该函数时才实际创建 PropertyHandle 对象。
- **使用模式**: 子类覆盖感兴趣的 `onXxxProperty` 方法，在回调中调用 LazyHandle 获取 PropertyHandle，保存后在运行时使用 `get()`/`set()` 操控属性。

## 公共 API 函数

### PropertyHandle 方法
- `PropertyHandle(sk_sp<NodeT>)`: 构造函数，仅接受节点（revalidator 为 nullptr）
- `PropertyHandle(sk_sp<NodeT>, sk_sp<SceneGraphRevalidator>)`: 构造函数，接受节点和重验证器
- `PropertyHandle(const PropertyHandle&)`: 拷贝构造函数
- `~PropertyHandle()`: 析构函数
- `get() const -> ValueT`: 获取当前属性值，从内部节点读取
- `set(const ValueT&)`: 设置属性值到内部节点，并触发场景图重验证

### PropertyObserver 回调
- `onColorProperty(const char[], const LazyHandle<ColorPropertyHandle>&)`: 颜色属性通知
- `onOpacityProperty(const char[], const LazyHandle<OpacityPropertyHandle>&)`: 不透明度属性通知
- `onTextProperty(const char[], const LazyHandle<TextPropertyHandle>&)`: 文本属性通知
- `onTransformProperty(const char[], const LazyHandle<TransformPropertyHandle>&)`: 变换属性通知
- `onEnterNode(const char[], NodeType)`: 进入节点通知
- `onLeavingNode(const char[], NodeType)`: 离开节点通知

### 类型别名
```cpp
using ColorPropertyValue   = SkColor;
using OpacityPropertyValue = float;
```

### 枚举类型
- `TextPaintOrder`: `kFillStroke` / `kStrokeFill`，文本绘制顺序

## 内部实现细节

- **LazyHandle 机制**: `PropertyObserver` 的回调使用 `LazyHandle`（即 `std::function<std::unique_ptr<T>()>`），只有当观察者实际调用该函数时才创建 `PropertyHandle`，避免为不需要的属性分配句柄资源。这种延迟求值策略在动画包含大量属性但观察者只关心少数几个时特别有效。
- **SceneGraphRevalidator 集成**: `PropertyHandle` 持有 `SceneGraphRevalidator` 的引用，`set()` 操作后自动触发场景图重验证，确保视觉一致性。`fRevalidator` 可以为 `nullptr`（如测试场景），此时跳过重验证。
- **文本属性完整性**: `TextPropertyValue` 包含 20 多个字段，完整覆盖了 After Effects 文本图层的所有可调参数。这些字段的默认值被精心设定以匹配 AE 的默认行为。
- **PropertyHandle 的双构造器**: `PropertyHandle` 有两个构造器——一个只接受节点（用于无 revalidator 的场景），另一个同时接受节点和 revalidator（用于正常动画属性访问）。这种设计支持了测试场景和正常使用场景。
- **GlyphDecorator 的扩展点**: `GlyphDecorator` 接口通过 `TextPropertyValue::fDecorator` 成员关联到文本属性上，在文本渲染时被调用。它提供了逐字形的边界和矩阵信息，允许实现下划线、高亮、自定义边框等装饰效果。
- **BCP47 locale 支持**: `TextPropertyValue::fLocale` 接受 BCP47 格式的区域标识符，并支持 RFC6067 扩展（如 `ja-u-lb-strict` 用于选择严格的日语换行规则），展示了对国际化的深入支持。

## 依赖关系

- **Skia 核心**: `SkColor`, `SkMatrix`, `SkPaint`, `SkPoint`, `SkRect`, `SkRefCnt`, `SkScalar`, `SkString`, `SkTypeface`
- **`include/utils/SkTextUtils.h`**: 提供 `SkTextUtils::Align` 文本对齐枚举
- **`modules/skottie/include/TextShaper.h`**: 提供 `Shaper::VAlign`, `Shaper::ResizePolicy` 等排版相关枚举
- **内部依赖**: `sksg::Color`, `sksg::OpacityEffect`, `internal::TextAdapter`, `internal::TransformAdapter2D`

## 设计模式与设计决策

- **适配器模式**: `PropertyHandle` 是用户面向的 AE 模型值与内部场景图节点之间的适配器，隔离了内部实现细节。
- **观察者模式**: `PropertyObserver` 提供了动画属性的发现机制，允许在解析时注册对感兴趣属性的回调。
- **延迟初始化**: `LazyHandle` 的使用确保了只有被观察者实际请求的属性才会创建句柄，遵循"按需创建"原则。
- **值类型语义**: `TextPropertyValue` 和 `TransformPropertyValue` 是值类型（struct），支持复制和比较操作，简化了状态管理。
- **模板特化**: `PropertyHandle` 使用模板统一了不同属性类型的接口，但各特化的 `get()`/`set()` 实现完全不同（在 `.cpp` 中显式特化）。

## 性能考量

- **LazyHandle 避免不必要的分配**: 不感兴趣的属性不会创建句柄对象。在典型使用中，一个 Lottie 动画可能包含数百个属性，但观察者通常只关心少数几个，LazyHandle 确保了线性而非二次的资源使用。
- **SceneGraphRevalidator 批量更新**: `set()` 调用后触发 `revalidate()`，场景图使用脏标记（dirty flag）机制，只重新处理被修改的子树。但如果需要连续修改多个属性，每次 `set()` 都会触发独立的重验证。
- **TextPropertyValue 的比较操作**: `operator==` 逐字段比较所有 20+ 字段，使用短路求值 (`&&`)，在频繁比较场景下可能成为瓶颈，但在实际使用中比较频率较低。`SkString` 的比较需要逐字符检查，`sk_sp` 的比较则是轻量的指针比较。
- **PropertyHandle 的拷贝成本**: `PropertyHandle` 支持拷贝构造，拷贝操作涉及 `sk_sp` 的引用计数增减，但成本极低。
- **回调的 std::function 开销**: `LazyHandle` 使用 `std::function` 包装，可能涉及堆分配（当闭包大小超过小缓冲区优化阈值时）。但由于 LazyHandle 仅在解析时创建且通常只调用一次，这个开销可以忽略。

## 相关文件

- `modules/skottie/src/SkottieProperty.cpp` -- `PropertyHandle` 模板特化实现
- `modules/skottie/include/Skottie.h` -- `Animation::Builder` 中注册 `PropertyObserver`
- `modules/skottie/include/TextShaper.h` -- 文本排版相关类型定义
- `modules/skottie/include/SlotManager.h` -- 插槽管理器，另一种属性控制机制
- `modules/skottie/src/SkottiePriv.h` -- 属性分发逻辑
- `modules/sksg/include/SkSGPaint.h` -- `sksg::Color` 场景图节点
- `modules/sksg/include/SkSGOpacityEffect.h` -- `sksg::OpacityEffect` 场景图节点
