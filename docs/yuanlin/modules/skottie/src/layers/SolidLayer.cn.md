# SolidLayer - Skottie 纯色图层

> 源文件: `modules/skottie/src/layers/SolidLayer.cpp`

## 概述

SolidLayer 实现了 Lottie 动画中纯色图层的解析与渲染节点构建。它从 JSON 图层数据中提取尺寸和颜色信息，创建一个由纯色填充的矩形渲染节点。该实现简洁高效，是所有 Skottie 图层类型中最简单的可视图层。

## 架构位置

SolidLayer 是 Skottie `AnimationBuilder` 图层附加管线中的一种图层类型。它位于图层解析阶段，将 Lottie JSON 数据转换为 Scene Graph（sksg）渲染节点。

```
Skottie AnimationBuilder
  -> attachSolidLayer()
    -> sksg::Color (颜色节点)
    -> sksg::Rect (矩形几何节点)
    -> sksg::Draw (绘制节点 = 几何 + 画笔)
```

## 主要类与结构体

本文件没有定义独立的类。功能通过 `AnimationBuilder::attachSolidLayer` 成员函数直接实现。

## 公共 API 函数

### `AnimationBuilder::attachSolidLayer`
```cpp
sk_sp<sksg::RenderNode> attachSolidLayer(const skjson::ObjectValue& jlayer,
                                          LayerInfo* layer_info) const;
```
- 从 `jlayer["sw"]` 和 `jlayer["sh"]` 解析图层宽度和高度，存入 `layer_info->fSize`
- 从 `jlayer["sc"]` 解析十六进制颜色字符串（如 `"#FF0000"`）
- 校验尺寸非空、颜色字符串格式正确
- 创建 `sksg::Color` 颜色节点（强制不透明 `0xff000000 | c`）
- 启用抗锯齿并通过 `dispatchColorProperty` 注册颜色属性
- 返回 `sksg::Draw` 节点（矩形几何 + 纯色画笔的组合）

## 内部实现细节

1. **颜色解析**：颜色以 `"#RRGGBB"` 格式的十六进制字符串编码。解析时跳过前导 `#`，使用 `SkParse::FindHex` 转换为 `uint32_t`，然后与 `0xff000000` 进行或运算以确保完全不透明。
2. **错误处理**：当尺寸为空、颜色字符串缺失、首字符不是 `#` 或十六进制解析失败时，记录错误日志并返回 `nullptr`。
3. **颜色属性分发**：调用 `dispatchColorProperty(solid_paint)` 将颜色节点注册到属性分发系统，使外部可以通过属性接口动态修改颜色。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkColor.h` | SkColor 颜色类型 |
| `SkRect.h` | SkRect 矩形构造 |
| `SkParse.h` | FindHex 十六进制解析 |
| `SkJSONReader.h` | JSON 解析 |
| `SkSGDraw.h` | Draw 渲染节点 |
| `SkSGRect.h` | Rect 几何节点 |
| `SkSGPaint.h` | Color 画笔节点 |
| `SkottieJson.h` | ParseDefault 辅助函数 |
| `SkottiePriv.h` | AnimationBuilder 定义 |

## 设计模式与设计决策

- **组合模式**：渲染节点通过 `sksg::Draw` 将几何（`sksg::Rect`）与画笔（`sksg::Color`）组合，遵循 Scene Graph 的组合式设计。
- **强制不透明**：纯色图层的颜色始终设为完全不透明（alpha = 0xFF），图层级别的透明度由上层变换控制。
- **抗锯齿默认启用**：即使是矩形填充，也开启抗锯齿以确保与其他图层混合时的边缘质量。

## 性能考量

- 纯色图层的渲染开销极低，仅为一次矩形填充操作。
- 不涉及纹理采样或复杂着色器，是最轻量的可视图层类型。
- 颜色属性通过 Scene Graph 的失效机制按需更新，避免不必要的重绘。
- `SkParse::FindHex` 是一次线性扫描的十六进制解析，解析时间与颜色字符串长度（固定 6 字符）成正比，开销可忽略。
- `sksg::Draw` 节点在 GPU 管线中被优化为单次绘制调用，不涉及额外的图层合成开销。
- 矩形由 `SkRect::MakeSize` 从 `layer_info->fSize` 直接创建，避免了冗余的几何计算。

## 相关文件

- `modules/skottie/src/SkottiePriv.h` - AnimationBuilder 定义
- `modules/sksg/include/SkSGDraw.h` - Draw 渲染节点
- `modules/sksg/include/SkSGRect.h` - Rect 几何节点
- `modules/sksg/include/SkSGPaint.h` - Color 画笔节点
- `modules/skottie/src/layers/NullLayer.cpp` - 更简单的空图层
- `modules/skottie/src/layers/FootageLayer.cpp` - 更复杂的图像图层
