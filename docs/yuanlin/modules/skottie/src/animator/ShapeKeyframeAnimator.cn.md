# ShapeKeyframeAnimator - Skottie 形状关键帧动画器

> 源文件: `modules/skottie/src/animator/ShapeKeyframeAnimator.cpp`

## 概述

ShapeKeyframeAnimator 实现了 Lottie 动画中形状（路径）属性的关键帧动画编解码。该文件定义了形状数据的编码格式（每个顶点 6 个浮点数加一个闭合标志）、JSON 解析逻辑、以及从编码数据到 SkPath 的转换。形状动画通过向量关键帧动画器（VectorKeyframeAnimator）框架实现，支持贝塞尔曲线的平滑插值和自动降次优化。

## 架构位置

ShapeKeyframeAnimator 位于 Skottie 动画器子系统中，是属性绑定框架的一个特化实现。

```
Skottie 属性动画系统
  |
  +-> AnimatablePropertyContainer::bind<ShapeValue>()
  |     +-> VectorAnimatorBuilder (向量动画构建器)
  |     |     +-> parse_encoding_len (编码长度解析)
  |     |     +-> parse_encoding_data (编码数据解析)
  |     |
  |     +-> VectorKeyframeAnimator (关键帧插值引擎)
  |
  +-> ShapeValue::operator SkPath() [编码 -> 路径转换]
```

## 主要类与结构体

### ShapeEncodingInfo (枚举)
定义形状编码的索引布局：
- `kX_Index = 0` / `kY_Index = 1` - 顶点坐标
- `kInX_Index = 2` / `kInY_Index = 3` - 入切线控制点
- `kOutX_Index = 4` / `kOutY_Index = 5` - 出切线控制点
- `kFloatsPerVertex = 6` - 每顶点浮点数

### ShapeValue（在 SkottieValue.h 中定义）
- 继承自 `std::vector<float>` 的形状值类型
- 提供 `operator SkPath()` 转换运算符将编码数据转换为可渲染路径

## 公共 API 函数

### `AnimatablePropertyContainer::bind<ShapeValue>`
```cpp
template <>
bool AnimatablePropertyContainer::bind<ShapeValue>(const AnimationBuilder& abuilder,
                                                    const skjson::ObjectValue* jprop,
                                                    ShapeValue* v);
```
- 模板特化，将 JSON 属性绑定到 ShapeValue
- 创建 `VectorAnimatorBuilder`，传入 `parse_encoding_len` 和 `parse_encoding_data` 回调
- 委托给 `bindImpl` 执行实际的动画器构建和绑定

### `ShapeValue::operator SkPath()`
```cpp
ShapeValue::operator SkPath() const;
```
- 将浮点数组编码转换为 SkPath 对象
- 使用 `SkPathBuilder` 构建路径，预分配顶点空间
- 支持三次贝塞尔曲线自动降次为直线段

## 内部实现细节

### 编码格式
形状数据编码为连续的浮点数组：
```
[v0.x, v0.y, v0_in.x, v0_in.y, v0_out.x, v0_out.y,
 v1.x, v1.y, v1_in.x, v1_in.y, v1_out.x, v1_out.y,
 ...,
 closed_flag]
```
- 总长度 = `vertex_count * 6 + 1`
- 入/出切线是相对于顶点的偏移量
- `closed_flag` 非零表示路径闭合

### JSON 解析
- `shape_root()` 处理某些版本将形状值包装为单元素数组的兼容性问题
- `parse_encoding_len()` 从 JSON 的 `"v"` 数组获取顶点数量，计算编码长度
- `parse_encoding_data()` 从三个 JSON 数组解析数据：
  - `"v"` - 必须的顶点坐标数组
  - `"i"` - 可选的入切线数组（默认 0,0）
  - `"o"` - 可选的出切线数组（默认 0,0）

### 路径构建
- `moveTo` 第一个顶点
- 逐顶点调用 `addCubic`，构建三次贝塞尔曲线段
- **降次优化**：当控制点与端点重合（`c0 == p0 && c1 == p1`）时，自动降次为 `lineTo`
- 闭合路径时从最后一个顶点到第一个顶点额外添加一条曲线段，然后调用 `close()`
- 使用 `incReserve(1 + vertex_count * 3)` 保守预分配（假设全部为三次曲线）

### 切线坐标系
- 入/出切线在 JSON 中以相对坐标存储
- 在 `addCubic` 中转换为绝对坐标：`c0 = out_tangent + p0`，`c1 = in_tangent + p1`

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkPath.h` / `SkPathBuilder.h` | 路径构建 |
| `SkPoint.h` | 点和向量运算 |
| `SkJSONReader.h` / `SkottieJson.h` | JSON 解析 |
| `SkottieValue.h` | ShapeValue 类型定义 |
| `Animator.h` | AnimatablePropertyContainer 基类 |
| `VectorKeyframeAnimator.h` | 向量关键帧动画器框架 |

## 设计模式与设计决策

- **编码/解码分离**：形状数据使用紧凑的浮点数组编码，适合关键帧之间的逐分量线性插值，解码为 SkPath 仅在需要渲染时执行。
- **回调式解析**：`parse_encoding_len` 和 `parse_encoding_data` 作为回调传给 `VectorAnimatorBuilder`，实现了编码格式与动画框架的解耦。
- **自动降次**：贝塞尔曲线在控制点退化时自动降次为直线，减少渲染复杂度。
- **兼容性包装**：`shape_root()` 处理 Lottie JSON 的版本差异（单值 vs 单元素数组包装）。
- **模板特化扩展**：通过 `bind<ShapeValue>` 模板特化，将形状动画无缝集成到通用的属性绑定框架中。

## 性能考量

- 浮点数组编码支持高效的逐分量插值，无需在关键帧之间解码/重编码路径。
- `SkPathBuilder::incReserve` 预分配避免了路径构建过程中的内存重分配。
- 贝塞尔曲线降次减少了 GPU 曲线细分的工作量。
- 路径转换（`operator SkPath()`）仅在属性值变化时调用，通过动画器的脏标记系统控制。
- 编码长度通过顶点数计算而非遍历数据，O(1) 复杂度。

### 插值行为分析

形状动画的关键帧插值发生在编码的浮点数组级别而非路径级别。这意味着：

1. **逐分量线性插值**：VectorKeyframeAnimator 对两个关键帧的浮点数组进行逐元素线性插值。对于形状数据，这等同于顶点坐标、入切线和出切线的独立线性插值。

2. **顶点数一致性要求**：关键帧之间的形状必须具有相同的顶点数量（编码长度相同），否则无法进行逐分量插值。这是 Lottie 形状动画的基本约束。

3. **闭合标志插值**：闭合标志也参与浮点插值，但由于它仅在路径构建时与零比较（`this->back() != 0`），非零值和零值之间的过渡会在插值过程中自然发生。

4. **切线空间的连续性**：由于入/出切线以相对坐标存储，线性插值能保持切线与顶点之间的相对关系，产生平滑的形变动画。

### 与 VectorKeyframeAnimator 的集成

`VectorAnimatorBuilder` 接收三个参数：
- 目标 `ShapeValue*` 指针
- `parse_encoding_len` 回调 - 从 JSON 值获取编码长度
- `parse_encoding_data` 回调 - 从 JSON 值填充浮点数组

这种回调式设计使得向量关键帧动画器框架完全不需要了解形状数据的具体语义，只需要知道如何确定数组长度和如何从 JSON 填充数据即可。

### JSON 版本兼容性

`shape_root()` 函数处理了 Lottie JSON 格式的一个版本差异：某些版本将形状关键帧值包装在单元素数组中（`[{...}]`），而其他版本直接使用对象（`{...}`）。该函数统一了两种格式，确保后续解析逻辑无需关心包装差异。

## 相关文件

- `modules/skottie/src/SkottieValue.h` - ShapeValue 类型定义
- `modules/skottie/src/animator/VectorKeyframeAnimator.h` - 向量关键帧动画器
- `modules/skottie/src/animator/Animator.h` - AnimatablePropertyContainer 基类
- `modules/skottie/src/SkottieJson.h` - JSON 解析工具
- `include/core/SkPathBuilder.h` - 路径构建器
