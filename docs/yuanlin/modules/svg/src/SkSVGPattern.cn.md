# SkSVGPattern

> 源文件: [modules/svg/src/SkSVGPattern.cpp](../../../../modules/svg/src/SkSVGPattern.cpp)

## 概述

`SkSVGPattern` 实现了 SVG `<pattern>` 元素，用于定义可重复平铺的图案填充。图案元素允许将一组 SVG 内容定义为一个平铺单元（tile），然后通过 `fill` 或 `stroke` 属性的 `url(#id)` 引用将其重复铺设在目标形状上。

该类处理了 SVG 图案的核心复杂性：通过 `xlink:href` 属性实现的属性和内容继承链，允许一个图案从另一个图案继承几何属性和子元素内容。

## 架构位置

```
SkSVGNode
  └── SkSVGContainer
        └── SkSVGHiddenContainer
              └── SkSVGPattern         ← 本文件
                    └── children        （图案内容：任意 SVG 元素）

作为 Paint Server 的使用方式:
  <defs>
    <pattern id="myPattern" ...>
      <circle .../> <!-- 图案内容 -->
    </pattern>
  </defs>
  <rect fill="url(#myPattern)" .../>
```

图案作为"paint server"存在于 `<defs>` 中，不直接渲染，仅在被引用时生效。与渐变（`SkSVGGradient`）共享相同的 `onAsPaint()` 接口模式。

### href 继承链示例

```
<pattern id="base" width="20" height="20">
  <circle cx="10" cy="10" r="5"/>
</pattern>
<pattern id="derived" xlink:href="#base" patternTransform="rotate(45)"/>
```

`derived` 从 `base` 继承 width、height 和子元素内容，自身提供 patternTransform。

## 主要类与结构体

### `SkSVGPattern`

| 属性 | 类型 | 说明 |
|------|------|------|
| `fX` | `std::optional<SkSVGLength>` | 平铺区域 X 坐标 |
| `fY` | `std::optional<SkSVGLength>` | 平铺区域 Y 坐标 |
| `fWidth` | `std::optional<SkSVGLength>` | 平铺区域宽度 |
| `fHeight` | `std::optional<SkSVGLength>` | 平铺区域高度 |
| `fPatternTransform` | `std::optional<SkSVGTransformType>` | 图案变换矩阵 |
| `fHref` | `SkSVGIRI` | 引用的图案 ID |

### `PatternAttributes`（内部结构体）

用于 href 继承链解析的临时属性容器，包含与 `SkSVGPattern` 相同的可选属性集合。

## 公共 API 函数

### `parseAndSetAttribute(const char* name, const char* value)`
解析图案的属性：`x`、`y`、`width`、`height`、`patternTransform`、`xlink:href`。

## 内部实现细节

### href 目标查找 (`hrefTarget`)

通过渲染上下文的 `findNodeById()` 查找引用的图案节点，验证其确实是 `kPattern` 类型。

### href 继承解析 (`resolveHref`)

实现了 SVG 规范中图案的 href 属性和内容继承机制：

1. 从当前节点开始，沿 href 链遍历
2. 对每个节点，使用 `inherit_if_needed()` 尝试继承尚未设定的属性（x, y, width, height, patternTransform）
3. 同时追踪内容节点（content node）：
   - 如果当前内容节点无子元素，则更新为链中第一个有子元素的节点
4. 提前终止条件：当所有属性都已解析且内容节点已找到
5. 返回内容节点指针

`inherit_if_needed` 辅助函数模板实现了"仅在目标属性未设置时继承源属性"的语义，返回值指示是否发生了继承。

### Paint 生成 (`onAsPaint`)

将图案转换为 `SkPaint` 的平铺着色器：

1. **解析 href 链**: 调用 `resolveHref()` 获取最终的属性值和内容节点
2. **计算平铺矩形**: 使用解析后的 x, y, width, height（未设置的属性默认为 0）
3. **空矩形检查**: 平铺矩形为空时返回 false（无法创建着色器）
4. **获取变换指针**: 使用 `SkOptAddressOrNull(attrs.fPatternTransform)` 安全地获取可能为空的变换矩阵指针
5. **录制图案内容**:
   - 使用 `SkPictureRecorder` 创建录制画布，范围为平铺矩形
   - 创建录制用的 `SkSVGRenderContext`，传入录制画布
   - 直接调用 `SkSVGContainer::onRender()` 渲染内容节点的子元素
6. **创建平铺着色器**:
   - 将录制完成的 `SkPicture` 通过 `makeShader()` 转换为着色器
   - 设置 `SkTileMode::kRepeat` 双向重复
   - 应用线性滤波 (`SkFilterMode::kLinear`)
   - 传入 `patternTransform` 和平铺矩形

### 绕过 HiddenContainer 渲染限制

由于 `SkSVGHiddenContainer` 的 `onRender()` 会跳过渲染，图案内容的渲染必须直接调用 `SkSVGContainer::onRender()`，绕过隐藏容器的渲染抑制。代码中明确注释了这一决策："Cannot call into INHERITED:: because SkSVGHiddenContainer skips rendering."

### 平铺矩形计算

平铺矩形通过 `ctx.lengthContext().resolveRect()` 解析，将 SVG 长度单位（px, em, %, 等）转换为像素值。未继承到的属性默认为 `SkSVGLength(0)`，这会导致宽度或高度为零的平铺矩形，从而安全地禁止渲染。

## 依赖关系

- **Skia Core**: `SkPaint`, `SkPicture`, `SkPictureRecorder`, `SkRect`, `SkSamplingOptions`, `SkTileMode`, `SkMatrix`
- **SVG 模块**: `SkSVGAttributeParser`, `SkSVGContainer`, `SkSVGRenderContext`

## 设计模式与设计决策

1. **href 继承链**: 完整实现了 SVG 规范的图案继承机制，包括属性继承和内容继承两个独立的维度。属性继承使用"首个设定值优先"原则，内容继承使用"首个有子元素节点优先"原则。

2. **Picture 录制模式**: 使用 `SkPictureRecorder` 将图案内容录制为 `SkPicture`，然后转换为可重复的着色器。这是 Skia 中实现平铺图案的标准方法，确保图案内容可以高效地被 GPU 重复绘制。

3. **可选属性**: 所有几何属性使用 `std::optional`，精确区分"未设置"（从 href 继承）和"设置为 0"。这与渐变的 href 继承语义一致。

4. **提前终止优化**: href 链遍历在所有属性和内容都已解析后提前终止，避免不必要的链追踪。使用 `didInherit` 标志追踪每轮是否有新属性被继承。

5. **位操作 OR**: 使用位操作 OR（`|`）而非逻辑 OR（`||`）连接 `inherit_if_needed` 调用，避免短路求值，确保所有属性在每轮迭代中都被检查。

6. **TODO 标注**: 尚未实现 href 引用循环检测，与渐变的 href 链面临相同的问题。

7. **HiddenContainer 绕过**: 直接调用 `SkSVGContainer::onRender()` 而非通过常规渲染路径，是因为 `SkSVGHiddenContainer` 的 `onRender` 为空操作。这是一个明确的设计选择，注释中有说明。

8. **默认值处理**: 未继承到值的属性默认为 `SkSVGLength(0)`，这意味着没有 x/y/width/height 时图案区域为零大小，渲染被跳过。

## 性能考量

- `SkPictureRecorder` 录制图案内容的开销取决于内容复杂度，简单图案录制成本很低
- `SkPicture` 转着色器后，Skia 可以高效地重复平铺，GPU 硬件纹理重复是零额外开销的
- href 链遍历通常很短（1-2 层），但无循环检测可能导致无限循环
- 线性滤波确保缩放时的平滑过渡，比最近邻采样有更高的质量但稍大的开销
- 每次 Paint 解析都重新录制图案，缺少缓存机制，这对于频繁重绘的场景是潜在的优化点
- `inherit_if_needed` 模板函数的条件检查极其轻量（`has_value` 是常量时间操作）
- `SkOptAddressOrNull` 对 std::optional 取地址，用于传递可能为空的 `patternTransform`
- 图案内容通过 `SkSVGContainer::onRender` 绕过隐藏容器渲染，直接调用虚函数，无额外分发开销
- 平铺矩形为空时（tile.isEmpty()）提前返回 false，避免不必要的录制操作
- 属性继承提前终止检查减少了 href 链遍历的平均开销

## 相关文件

- `modules/svg/include/SkSVGPattern.h` - 头文件定义，包含属性和 PatternAttributes 声明
- `modules/svg/include/SkSVGHiddenContainer.h` - 隐藏容器基类，onRender 为空操作
- `modules/svg/include/SkSVGContainer.h` - 容器基类，提供被绕过调用的 onRender
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文，提供长度解析和画布管理
- `modules/svg/src/SkSVGGradient.cpp` - 类似的"paint server"实现，共享 onAsPaint 模式
- `modules/svg/include/SkSVGAttributeParser.h` - 属性解析器，处理长度和变换的解析
