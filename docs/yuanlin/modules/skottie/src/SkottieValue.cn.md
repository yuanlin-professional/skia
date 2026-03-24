# SkottieValue.h

> 源文件: `modules/skottie/src/SkottieValue.h`

## 概述

`SkottieValue.h` 定义了 Skottie 动画引擎内部使用的基础值类型，包括标量值（`ScalarValue`）、二维向量值（`Vec2Value`）、多维向量值（`VectorValue`）、颜色值（`ColorValue`）和形状值（`ShapeValue`）。这些类型是 Lottie 动画关键帧系统中属性值的载体，贯穿于动画构建、关键帧插值和场景图同步的全过程。

## 架构位置

该文件位于 `modules/skottie/src/` 目录下，虽然是源文件目录中的头文件，但被 `SlotManager.h` 等公共头文件直接包含，实际上具有半公开的可见性。在 Skottie 的值类型层次中：

```
Lottie JSON 关键帧值 -> SkottieValue 类型 -> 适配器 (onSync) -> 场景图节点属性
```

## 主要类与结构体

### `ScalarValue`
```cpp
using ScalarValue = SkScalar;
```
- **用途**: 单一浮点数值，用于不透明度、旋转角度等标量属性。

### `Vec2Value`
```cpp
using Vec2Value = SkV2;
```
- **用途**: 二维向量，用于位置、缩放等二维属性。

### `VectorValue`
```cpp
class VectorValue : public std::vector<float>
```
- **继承**: `std::vector<float>`
- **用途**: 多维浮点数组，是 `ColorValue` 的基类。
- **转换**: 提供到 `SkV3` 的隐式转换运算符。

### `ColorValue`
```cpp
class ColorValue final : public VectorValue
```
- **继承**: `VectorValue`
- **用途**: RGBA 颜色值，以浮点数组形式存储。
- **转换**: 提供到 `SkColor`（32 位整数颜色）和 `SkColor4f`（浮点颜色）的隐式转换运算符。

### `ShapeValue`
```cpp
class ShapeValue final : public std::vector<float>
```
- **继承**: `std::vector<float>`
- **用途**: 路径/形状数据，以扁平化的浮点数组存储贝塞尔控制点。
- **转换**: 提供到 `SkPath` 的隐式转换运算符。

## 公共 API 函数

### 转换运算符

- `VectorValue::operator SkV3() const`: 转换为三维向量
- `ColorValue::operator SkColor() const`: 转换为 32 位整数颜色
- `ColorValue::operator SkColor4f() const`: 转换为浮点颜色
- `ShapeValue::operator SkPath() const`: 转换为路径对象

所有转换运算符的实现位于对应的 `.cpp` 文件中。

## 内部实现细节

- **std::vector 继承**: `VectorValue`、`ColorValue` 和 `ShapeValue` 直接继承自 `std::vector<float>`，这种设计虽然通常不推荐（因为 `std::vector` 没有虚析构函数），但在 Skottie 的使用场景中是安全的，因为这些类型不会通过 `std::vector<float>*` 指针被多态删除。
- **initializer_list 构造**: `VectorValue` 和 `ColorValue` 支持 `std::initializer_list<float>` 构造，方便在代码中直接构造颜色值，如 `ColorValue{r, g, b, a}`。
- **扁平化存储**: 颜色和路径数据都使用扁平化的 `float` 数组存储，与 Lottie JSON 中的数据表示一致，方便关键帧插值器直接操作。

## 依赖关系

- **`include/core/SkColor.h`**: `SkColor`, `SkScalar` 类型
- **`include/core/SkM44.h`**: `SkV2`, `SkV3` 向量类型
- **`include/core/SkPath.h`**: `SkPath` 路径类型
- **`skjson::Value`**: 前向声明（在其他文件中用于 JSON 解析）

## 设计模式与设计决策

- **类型别名 vs. 包装类**: 简单值类型（`ScalarValue`, `Vec2Value`）使用 `using` 别名，复杂值类型（`VectorValue`, `ColorValue`, `ShapeValue`）使用包装类。这种区分反映了值类型的复杂度差异。
- **隐式转换运算符**: 提供到 Skia 核心类型的隐式转换，使得这些值类型可以直接传递给 Skia 绑图 API，减少了显式转换的代码噪声。
- **继承 std::vector**: 选择继承而非组合 `std::vector` 是为了简化代码——所有标准容器操作（如 `size()`、`operator[]`、`push_back()`）无需手动委托。
- **关键帧友好**: 扁平化的 float 数组存储使得关键帧插值器可以对任意维度的值进行统一的线性插值操作。

## 性能考量

- **零开销类型别名**: `ScalarValue` 和 `Vec2Value` 是零开销的类型别名。
- **std::vector 的动态分配**: `VectorValue`、`ColorValue`、`ShapeValue` 在堆上分配数据，对于频繁创建/销毁的场景可能有开销，但在 Skottie 中这些值通常在构建时创建后长期复用。
- **隐式转换的潜在开销**: `ShapeValue::operator SkPath()` 需要从扁平数组重建 `SkPath` 对象，涉及内存分配和贝塞尔点的解析，在频繁调用时可能成为瓶颈。

## 相关文件

- `modules/skottie/include/SlotManager.h` -- 包含此头文件，使用 `ColorValue`, `ScalarValue`, `Vec2Value`
- `modules/skottie/src/Adapter.h` -- 适配器基类，在 `onSync()` 中使用这些值类型
- `modules/skottie/src/Path.cpp` -- `ShapeValue` 到 `SkPath` 的实际使用
- `modules/skottie/src/SlotManager.cpp` -- `ColorValue` 的构造和使用
- `modules/skottie/src/animator/Animator.h` -- 关键帧插值使用这些值类型
