# SkSVGGradient

> 源文件: [modules/svg/src/SkSVGGradient.cpp](../../../../modules/svg/src/SkSVGGradient.cpp)

## 概述

`SkSVGGradient` 是 SVG 渐变（`<linearGradient>` 和 `<radialGradient>`）的抽象基类，实现了渐变的通用功能，包括颜色停止点（color stops）的收集、停止点颜色解析、渐变属性解析以及最终的 `SkPaint` 着色器生成。

该类处理了 SVG 渐变系统的核心复杂性：href 引用链（允许一个渐变继承另一个渐变的颜色停止点）、spreadMethod（平铺模式）以及 gradientUnits 坐标系统。

## 架构位置

```
SkSVGNode
  └── SkSVGContainer
        └── SkSVGHiddenContainer
              └── SkSVGGradient        ← 本文件（渐变基类）
                    ├── SkSVGLinearGradient
                    └── SkSVGRadialGradient
```

渐变作为"paint server"存在，通过 `fill` 或 `stroke` 属性的 `url(#id)` 引用被使用。

## 主要类与结构体

### `SkSVGGradient`

| 属性 | 类型 | 说明 |
|------|------|------|
| `fHref` | `SkSVGIRI` | 引用的渐变 ID（用于继承颜色停止点） |
| `fGradientTransform` | `SkSVGTransformType` | 渐变变换矩阵 |
| `fSpreadMethod` | `SkSVGSpreadMethod` | 扩展方法（pad/repeat/reflect） |
| `fGradientUnits` | `SkSVGObjectBoundingBoxUnits` | 坐标单位系统 |

### `SkSVGSpreadMethod`

| 类型 | 对应 SkTileMode | 说明 |
|------|-----------------|------|
| `kPad` | `kClamp` | 用边缘颜色填充 |
| `kRepeat` | `kRepeat` | 重复渐变 |
| `kReflect` | `kMirror` | 镜像重复渐变 |

## 公共 API 函数

### `parseAndSetAttribute(const char* name, const char* value)`
解析渐变的通用属性：
- `gradientTransform` - 渐变变换
- `xlink:href` - 颜色停止点引用
- `spreadMethod` - 扩展方法
- `gradientUnits` - 坐标单位

## 内部实现细节

### 颜色停止点收集 (`collectColorStops`)

递归收集渐变的颜色停止点：
1. 创建固定尺寸的长度上下文（1x1），用于解析百分比偏移值
2. 遍历 `<stop>` 子元素：
   - 调用 `resolveStopColor()` 解析每个停止点的颜色
   - 解析偏移位置并钳位到 [0, 1] 范围
3. 如果当前渐变无子停止点且有 href 引用，则递归查找引用渐变的停止点
4. href 查找仅限于 `<linearGradient>` 和 `<radialGradient>` 节点

### 停止点颜色解析 (`resolveStopColor`)

将 `<stop>` 元素的 `stop-color` 和 `stop-opacity` 属性解析为 `SkColor4f`：
1. 检查 `stop-color` 和 `stop-opacity` 是否有值
2. 解析颜色（可能涉及 `currentColor` 和命名颜色查找）
3. 将 `stop-opacity` 乘入 alpha 通道

### Paint 生成 (`onAsPaint`)

将渐变转换为 `SkPaint` 的着色器：
1. 收集颜色停止点和位置
2. 将 `SkSVGSpreadMethod` 映射到 `SkTileMode`（通过 static_assert 验证枚举对齐）
3. 计算本地变换矩阵：OBB 变换 * 渐变变换
4. 调用纯虚方法 `onMakeShader()` 创建具体的着色器（由子类实现）
5. 设置 Paint 的着色器

### SpreadMethod 解析

通过特化 `SkSVGAttributeParser::parse<SkSVGSpreadMethod>` 实现字符串到枚举的映射。

### OBB 变换计算

当 `gradientUnits` 为 `objectBoundingBox` 时，渐变坐标相对于目标元素的边界框。通过 `ctx.transformForCurrentOBB()` 获取偏移和缩放参数，组合成变换矩阵。最终的本地矩阵为：

```
localMatrix = Translate(obbt.offset) * Scale(obbt.scale) * gradientTransform
```

这确保了渐变坐标先从边界框空间映射到用户空间，然后再应用用户指定的渐变变换。

### SpreadMethod 解析

通过特化 `SkSVGAttributeParser::parse<SkSVGSpreadMethod>` 实现：
- 使用循环遍历 3 个枚举值进行字符串匹配
- 匹配成功后检查字符串结束标记（EOS token）确保完整匹配
- 返回 false 时不修改输出参数

### 颜色解析细节

`resolveStopColor` 方法的颜色解析流程：
1. 获取 `stop-color` 和 `stop-opacity` 属性（非继承属性，应该有具体值）
2. 通过 `ctx.resolveSvgColor()` 处理可能的 `currentColor` 引用和命名颜色查找
3. 将解析后的 SkColor 转换为 SkColor4f（浮点颜色）
4. 将 stop-opacity 乘入 alpha 通道，保持 RGB 不变

## 依赖关系

- **Skia Core**: `SkM44`, `SkPaint`, `SkShader`, `SkSize`, `SkTileMode`
- **Skia Internal**: `SkTPin`（值钳位）
- **SVG 模块**: `SkSVGAttributeParser`, `SkSVGRenderContext`, `SkSVGStop`

## 设计模式与设计决策

1. **模板方法模式**: `onAsPaint()` 定义了渐变着色器创建的算法骨架，`onMakeShader()` 由子类（LinearGradient/RadialGradient）实现具体的着色器类型。这确保了颜色停止点收集和坐标变换的通用逻辑只实现一次。

2. **href 继承链**: 支持通过 `xlink:href` 引用其他渐变的颜色停止点，实现了 SVG 规范中的渐变属性继承。代码中标注了 TODO：尚未实现 href 循环检测，也未实现非颜色停止点属性的继承。

3. **枚举对齐**: 使用 `static_assert` 确保 `SkSVGSpreadMethod` 枚举值与 `SkTileMode` 枚举值对齐，允许直接的 `static_cast` 转换，避免了运行时映射表查找。

4. **分离收集与创建**: 颜色停止点的收集和着色器的创建是分离的步骤，便于处理 href 继承。收集阶段可能递归遍历 href 链，而创建阶段仅在当前节点执行。

5. **TODO 标注**: 存在多个 TODO，包括停止点排序、href 循环检测、href 属性继承（不仅限于颜色停止点）、objectBoundingBox 支持改进等。这些标注反映了实现与完整 SVG 规范之间的差距。

6. **固定尺寸长度上下文**: 颜色停止点偏移解析使用 1x1 的固定尺寸上下文，因为偏移值始终是 [0, 1] 范围内的比例值。

7. **Paint Server 模式**: 渐变作为"paint server"，通过 `onAsPaint()` 虚函数参与 SVG 的填充/描边系统，与 `SkSVGPattern` 共享相同的接口模式。

## 性能考量

- 颜色停止点收集可能涉及递归的 href 查找，但嵌套深度通常很小（1-2 层）
- `forEachChild<SkSVGStop>` 遍历所有子节点但只处理 `<stop>` 类型，对非停止点子节点有少量开销
- OBB 变换和渐变变换的矩阵乘法是标准的 3x3 矩阵操作
- 着色器创建是一次性操作，后续渲染由 Skia 核心（可能 GPU 加速）处理
- 停止点未排序（TODO），可能影响某些边缘情况的正确性
- 颜色停止点使用 `StopColorArray` 和 `StopPositionArray`（动态数组），对于大量停止点有内存分配开销
- `SkTPin` 钳位操作确保偏移值在 [0, 1] 范围内，是简单的浮点比较
- `resolveStopColor` 对每个停止点都进行颜色解析，包括可能的 `currentColor` 查找
- 渐变着色器创建后被 Skia 核心缓存和管理，重复使用同一渐变的多个形状可以复用着色器
- 矩阵链计算（OBB * gradientTransform）仅在 `onAsPaint` 调用时执行
- `static_assert` 枚举对齐检查在编译期完成，零运行时开销
- 对于无停止点的渐变，href 查找可能递归到链尾，但实际 SVG 中这种情况较少

## 相关文件

- `modules/svg/include/SkSVGGradient.h` - 头文件定义
- `modules/svg/include/SkSVGLinearGradient.h` - 线性渐变子类
- `modules/svg/include/SkSVGRadialGradient.h` - 径向渐变子类
- `modules/svg/include/SkSVGStop.h` - 渐变停止点元素
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文和 OBB 变换
