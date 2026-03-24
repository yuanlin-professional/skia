# SkottieProperty.cpp

> 源文件: `modules/skottie/src/SkottieProperty.cpp`

## 概述

`SkottieProperty.cpp` 是 Skottie 属性系统的实现文件，提供了 `PropertyHandle` 模板类的四种显式特化实现（颜色、不透明度、文本、变换），以及 `TextPropertyValue`、`TransformPropertyValue` 的比较运算符实现和 `PropertyObserver` 的默认回调实现。该文件是连接用户面向的属性操作接口与内部场景图节点的关键桥梁。

## 架构位置

该文件位于 `modules/skottie/src/` 目录下，实现了 `modules/skottie/include/SkottieProperty.h` 中声明的接口。在属性系统的数据流中：

```
用户代码 -> PropertyHandle::set(value)
    -> 内部节点操作 (sksg::Color::setColor, sksg::OpacityEffect::setOpacity, ...)
    -> SceneGraphRevalidator::revalidate()
    -> 场景图更新
```

## 主要类与结构体

该文件不定义新类，而是为已声明的模板类提供显式特化实现。

## 公共 API 函数

### TextPropertyValue 比较运算符

#### `operator==(const TextPropertyValue&) const`
- **实现**: 逐字段比较 23 个成员，按以下顺序依次检查：
  - 字体相关: `fTypeface`（`sk_sp` 指针比较）, `fText`, `fTextSize`, `fStrokeWidth`, `fLineHeight`, `fLineShift`, `fAscent`, `fMaxLines`
  - 对齐与排版: `fHAlign`, `fVAlign`, `fResize`, `fLineBreak`, `fDirection`, `fCapitalization`
  - 几何与颜色: `fBox`, `fFillColor`, `fStrokeColor`, `fPaintOrder`, `fStrokeJoin`
  - 状态标志: `fHasFill`, `fHasStroke`
  - 扩展属性: `fDecorator`（`sk_sp` 指针比较）, `fLocale`, `fFontFamily`
- **特点**: 使用短路求值（`&&` 链），第一个不等字段即可终止比较。

#### `operator!=(const TextPropertyValue&) const`
- 委托给 `operator==` 取反。

### TransformPropertyValue 比较运算符

#### `operator==(const TransformPropertyValue&) const`
- **实现**: 比较 `fAnchorPoint`, `fPosition`, `fScale`, `fSkew`, `fSkewAxis` 五个字段。
- **注意**: 缺少 `fRotation` 的比较（可能是有意为之，也可能是遗漏）。源码中 `this->fRotation` 与 `other.fRotation` 的比较在等式链中不存在。

### PropertyHandle 特化实现

#### ColorPropertyHandle
```cpp
template <> ColorPropertyValue ColorPropertyHandle::get() const;
template <> void ColorPropertyHandle::set(const ColorPropertyValue&);
```
- **get()**: 调用 `fNode->getColor()` 获取 `sksg::Color` 节点的颜色值。
- **set()**: 调用 `fNode->setColor(c)` 设置颜色，然后触发重验证。

#### OpacityPropertyHandle
```cpp
template <> OpacityPropertyValue OpacityPropertyHandle::get() const;
template <> void OpacityPropertyHandle::set(const OpacityPropertyValue&);
```
- **get()**: 调用 `fNode->getOpacity() * 100` 将内部 [0,1] 范围转换为 AE 的 [0,100] 百分比范围。
- **set()**: 调用 `fNode->setOpacity(o / 100)` 将 AE 百分比值转换为内部 [0,1] 范围值。
- **注意**: 值域转换使用简单的乘除运算，没有钳制（clamp）操作，超出范围的值会被直接传递给场景图节点。

#### TextPropertyHandle
```cpp
template <> TextPropertyValue TextPropertyHandle::get() const;
template <> void TextPropertyHandle::set(const TextPropertyValue&);
```
- **get()**: 调用 `fNode->getText()` 从 `TextAdapter` 获取当前文本属性。
- **set()**: 调用 `fNode->setText(t)` 设置文本属性。

#### TransformPropertyHandle
```cpp
template <> TransformPropertyValue TransformPropertyHandle::get() const;
template <> void TransformPropertyHandle::set(const TransformPropertyValue&);
```
- **get()**: 从 `TransformAdapter2D` 读取六个变换参数（锚点、位置、缩放、旋转、倾斜、倾斜轴）。
- **set()**: 逐一设置 `TransformAdapter2D` 的六个参数。

### PropertyObserver 默认实现

所有六个回调方法（`onColorProperty`, `onOpacityProperty`, `onTextProperty`, `onTransformProperty`, `onEnterNode`, `onLeavingNode`）提供空的默认实现（函数体为空，不执行任何操作）。这允许子类只覆盖感兴趣的回调，无需为不关心的属性类型提供实现。这遵循了接口隔离原则的精神。

每个默认实现的函数签名都接受 `const char node_name[]` 参数（节点名称）和对应的类型特定参数，但默认实现中这些参数被忽略。

## 内部实现细节

- **SK_API 模板特化**: 每个特化都标记了 `SK_API`，确保在动态库构建中正确导出符号。注释特别提到了这一点的重要性。
- **不透明度的值域转换**: AE 使用 [0, 100] 表示不透明度，而 Skia/sksg 使用 [0, 1]。`get()` 乘以 100，`set()` 除以 100。
- **重验证的条件触发**: 所有 `set()` 方法在操作节点后检查 `fRevalidator` 是否非空再触发重验证。`fRevalidator` 为空表示句柄在无重验证器的情况下创建（如测试场景）。
- **TransformPropertyValue::get()** 的聚合构造: 使用结构化初始化列表一次性构造返回值，避免临时变量。

## 依赖关系

- **`modules/skottie/include/SkottieProperty.h`**: 对应的头文件声明
- **`modules/skottie/src/SkottiePriv.h`**: `SceneGraphRevalidator`
- **`modules/skottie/src/Transform.h`**: `TransformAdapter2D` 变换适配器
- **`modules/skottie/src/text/TextAdapter.h`**: `TextAdapter` 文本适配器
- **`modules/sksg/include/SkSGOpacityEffect.h`**: `sksg::OpacityEffect` 不透明度效果节点
- **`modules/sksg/include/SkSGPaint.h`**: `sksg::Color` 颜色节点

## 设计模式与设计决策

- **模板显式特化**: 使用 C++ 模板显式特化为四种属性类型提供不同的 `get()`/`set()` 实现，在编译时确定具体行为。每个特化标记了 `SK_API` 确保动态库导出。
- **适配器模式**: `PropertyHandle` 适配了用户面向的 AE 值域（如不透明度 0-100）与内部 Skia 值域（如不透明度 0-1）之间的差异。用户无需了解内部表示。
- **空实现默认回调**: `PropertyObserver` 的默认空实现遵循了 NVI（Non-Virtual Interface）模式的变体，子类可以选择性覆盖感兴趣的回调，不关心的回调使用空默认实现。
- **值域一致性**: 所有 PropertyHandle 对外暴露 AE 模型的值域，对内使用 Skia/sksg 的值域，隔离了两个世界的差异。这种隔离使得 AE 语义和 Skia 内部表示可以独立演进。
- **可选重验证器**: `fRevalidator` 可以为 `nullptr`（如测试场景中单独创建 PropertyHandle 时），此时 `set()` 仅更新节点值而不触发场景图重验证。这种设计提高了测试的灵活性。
- **拷贝语义**: `PropertyHandle` 支持拷贝构造，拷贝后的两个句柄指向同一个内部节点。这允许多个持有者独立地读写同一个属性。
- **TransformPropertyValue::get 的聚合构造**: 使用 C++ 聚合初始化一次性构造返回值 `{ fNode->getAnchorPoint(), fNode->getPosition(), ... }`，避免了临时变量和多次赋值。

## 性能考量

- **TextPropertyValue 比较的开销**: `operator==` 比较 23 个字段，使用短路求值（`&&` 链）。`SkString` 比较需要检查长度后逐字符比较，`sk_sp` 比较仅检查指针值。`SkColor` 和 `float` 是整数/浮点直接比较。在频繁比较场景下可能有开销，但在实际使用中（如脏检测）比较频率较低。
- **get()/set() 的轻量性**: 大部分 get/set 操作是简单的值读写加可选的 `revalidate()` 调用。例如 `ColorPropertyHandle::get()` 仅调用 `fNode->getColor()` 返回一个 `SkColor` 值，`set()` 仅调用 `fNode->setColor()` 后触发重验证。单次操作的开销极小。
- **revalidate 的传播**: `set()` 操作后的 `revalidate()` 从场景图根节点开始重新验证。`sksg` 使用脏标记（invalidation）优化，`revalidate()` 仅重新处理被标记为脏的子树，未被修改的子树跳过处理。因此实际开销与被修改节点的子树深度成正比，而非整棵树的大小。
- **不透明度的值域转换**: `OpacityPropertyHandle` 的 `get()` 和 `set()` 涉及乘法/除法运算（`* 100` / `/ 100`），但浮点乘除在现代 CPU 上只需一个时钟周期。
- **TransformPropertyHandle::set() 的六次调用**: 设置变换属性需要调用 `TransformAdapter2D` 的六个 setter 方法（锚点、位置、缩放、旋转、倾斜、倾斜轴），但每个 setter 都是简单的成员赋值，总开销极低。
- **模板特化的编译时开销**: 四种属性句柄的 `get()`/`set()` 在编译时通过显式特化确定，没有运行时虚函数调度的开销。

## 相关文件

- `modules/skottie/include/SkottieProperty.h` -- 对应的头文件，定义了 PropertyHandle 模板、值类型和 PropertyObserver
- `modules/skottie/src/SkottiePriv.h` -- `SceneGraphRevalidator` 定义和 `AnimationBuilder` 属性分发方法
- `modules/skottie/src/Transform.h` -- `TransformAdapter2D`，TransformPropertyHandle 操作的内部节点
- `modules/skottie/src/text/TextAdapter.h` -- `TextAdapter`，TextPropertyHandle 操作的内部节点
- `modules/sksg/include/SkSGPaint.h` -- `sksg::Color` 场景图颜色节点，ColorPropertyHandle 操作目标
- `modules/sksg/include/SkSGOpacityEffect.h` -- `sksg::OpacityEffect` 场景图不透明度节点
- `modules/skottie/src/Skottie.cpp` -- `AnimationBuilder::dispatchXxxProperty` 方法创建 PropertyHandle
- `modules/skottie/include/Skottie.h` -- `Animation::Builder::setPropertyObserver()` 注册观察者
- `modules/skottie/include/SlotManager.h` -- SlotManager 提供了另一种属性控制机制（基于命名插槽而非属性观察者）
