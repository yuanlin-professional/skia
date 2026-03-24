# SkSVGNode

> 源文件: [modules/svg/src/SkSVGNode.cpp](../../../../modules/svg/src/SkSVGNode.cpp)

## 概述

`SkSVGNode` 是 Skia SVG 模块中所有 SVG 节点的基类。它定义了 SVG DOM 树中每个节点的核心行为，包括渲染、属性解析、路径转换以及 viewBox 矩阵计算等基础功能。所有具体的 SVG 元素（如 `<circle>`、`<rect>`、`<path>` 等）都直接或间接地继承自此类。

该类继承自 `SkRefCnt`，采用引用计数机制进行内存管理，是 SVG 模块中最核心的抽象基类。

## 架构位置

```
SkRefCnt
  └── SkSVGNode                    ← 本文件（SVG 所有节点的基类）
        ├── SkSVGContainer           （容器节点基类）
        │     ├── SkSVGSVG           （根 SVG 元素）
        │     ├── SkSVGG             （分组元素）
        │     └── SkSVGHiddenContainer
        │           ├── SkSVGDefs
        │           ├── SkSVGFilter
        │           └── SkSVGGradient
        └── SkSVGTransformableNode   （可变换节点基类）
              └── SkSVGShape         （形状基类）
                    ├── SkSVGCircle
                    ├── SkSVGRect
                    ├── SkSVGPath
                    └── ...
```

`SkSVGNode` 处于 SVG 模块的最底层抽象层，定义了所有 SVG 元素共有的接口和行为。

## 主要类与结构体

### `SkSVGNode`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fTag` | `SkSVGTag` | 标识节点对应的 SVG 元素类型（如 kCircle、kRect 等） |
| `fPresentationAttributes` | `SkSVGPresentationAttributes` | 存储所有 SVG 展示属性（fill、stroke、opacity 等） |

### `SkSVGTag` 枚举

定义了所有支持的 SVG 元素标签类型，包括基本形状（kCircle、kRect、kPath）、容器（kG、kSvg、kDefs）、滤镜（kFilter、kFeBlend 等）以及渐变（kLinearGradient、kRadialGradient）等。

## 公共 API 函数

### `render(const SkSVGRenderContext& ctx) const`
渲染当前节点。创建本地上下文副本，先调用 `onPrepareToRender()` 应用属性，然后调用 `onRender()` 执行实际绘制。

### `asPaint(const SkSVGRenderContext& ctx, SkPaint* paint) const`
将当前节点转换为 SkPaint 对象。主要用于渐变和图案等"paint server"类型节点。

### `asPath(const SkSVGRenderContext& ctx) const`
将当前节点转换为 SkPath。如果存在 clip-path，会自动对路径执行布尔交集运算。

### `objectBoundingBox(const SkSVGRenderContext& ctx) const`
返回节点的对象边界框（object bounding box），用于 objectBoundingBox 单位系统的坐标解析。

### `setAttribute(SkSVGAttribute attr, const SkSVGValue& v)`
通过枚举类型设置属性值，委托给虚函数 `onSetAttribute()`。

### `setAttribute(const char* attributeName, const char* attributeValue)`
通过字符串名/值对设置属性，该方法定义在 SkSVGDOM.cpp 中，使用属性解析字典进行查找。

### `parseAndSetAttribute(const char* name, const char* value)`
解析并设置 SVG 展示属性。使用宏 `PARSE_AND_SET` 实现对 30 多种展示属性的统一解析，支持 fill、stroke、opacity、font、color 等全部标准 SVG 展示属性。

### `ComputeViewboxMatrix(const SkRect& viewBox, const SkRect& viewPort, SkSVGPreserveAspectRatio par)`
静态方法，根据 viewBox、viewPort 和 preserveAspectRatio 计算视口变换矩阵。实现了 SVG 1.1 规范中 `preserveAspectRatio` 属性的完整语义，包括 meet/slice 缩放和 Min/Mid/Max 对齐方式。

## 内部实现细节

### 构造函数初始化
构造函数设置非继承展示属性的默认值：
- `fStopColor`：黑色（`SK_ColorBLACK`）
- `fStopOpacity`：1.0
- `fFloodColor`：黑色
- `fFloodOpacity`：1.0
- `fLightingColor`：白色（`SK_ColorWHITE`）

### 渲染准备机制 (`onPrepareToRender`)
在渲染前应用展示属性到上下文中，并检查两个关键的可见性条件：
1. `visibility` 属性不为 `hidden`
2. `display` 属性不为 `none`

对于叶子节点（无子节点），传递 `SkSVGRenderContext::kLeaf` 标志位。

### 属性解析宏 (`PARSE_AND_SET`)
使用模板元编程和 `decltype` 自动推导属性类型，通过 `SkSVGAttributeParser::parseProperty` 实现类型安全的属性解析。支持的属性包含完整的 SVG 展示属性集合。

### ViewBox 矩阵计算
`ComputeViewboxMatrix` 实现了两步计算：
1. **缩放计算**：根据 `preserveAspectRatio` 的 align 和 scale 参数，选择各向异性缩放（none）或等比缩放（meet 取最小值，slice 取最大值）
2. **平移计算**：使用对齐系数数组 `[0.0, 0.5, 1.0]` 对应 Min、Mid、Max 三种对齐方式，通过位操作从 `fAlign` 中提取 X 和 Y 方向的对齐系数

### SetInheritedByDefault 辅助模板
处理 `inherit` 值语义：当属性值为 `kInherit` 时，重置本地属性（等同于没有本地值），否则设置为具体值。这个辅助函数确保了 CSS `inherit` 关键字的正确语义——显式指定 `inherit` 等价于移除本地属性值，让属性从父节点继承。

### SVG_PRES_ATTR 宏

在头文件中定义的宏，为每个展示属性自动生成：
- `get<Name>()` - 返回属性的 `SkSVGProperty` 引用
- `set<Name>(const SkSVGProperty&)` - 设置属性（拷贝语义）
- `set<Name>(SkSVGProperty&&)` - 设置属性（移动语义）
- `set<Name>(ParseResult&&)` - 从解析结果设置属性（私有）

宏参数包括属性名、属性类型和是否可继承的布尔值。对于不可继承属性，`inherit` 值的处理当前标记为 TODO。

### 纯虚接口

`SkSVGNode` 声明了以下纯虚方法，要求所有子类实现：
- `appendChild(sk_sp<SkSVGNode>)` - 添加子节点
- `onRender(const SkSVGRenderContext&)` - 执行渲染
- `onAsPath(const SkSVGRenderContext&)` - 转换为路径

## 依赖关系

- **Skia Core**: `SkColor`, `SkM44`, `SkMatrix`, `SkPath`, `SkRefCnt`
- **Skia PathOps**: `SkPathOps`（用于 clip-path 的路径布尔运算）
- **SVG 模块内部**: `SkSVGRenderContext`, `SkSVGAttribute`, `SkSVGTypes`, `SkSVGAttributeParser`
- **标准库**: `<algorithm>`, `<array>`, `<cstddef>`, `<optional>`

## 设计模式与设计决策

1. **模板方法模式**: `render()` 方法实现了固定的渲染流程（prepareToRender -> onRender），子类通过覆盖 `onRender()` 和 `onPrepareToRender()` 自定义行为。

2. **引用计数 (SkRefCnt)**: 使用 Skia 的引用计数机制管理节点生命周期，配合 `sk_sp` 智能指针实现安全的共享所有权。

3. **属性继承体系**: 展示属性分为可继承和不可继承两类，通过 `SVG_PRES_ATTR` 宏自动生成 getter/setter，遵循 SVG 规范的属性继承规则。

4. **本地上下文复制**: 每次 render/asPaint/asPath 调用都创建 `SkSVGRenderContext` 的本地副本，确保属性变更不会影响兄弟节点。

5. **双层属性设置机制**: 同时支持新的 `parseAndSetAttribute` 路径和旧的 `setAttribute` 路径，保持向后兼容性。

## 性能考量

- **展示属性存储开销**: 注释中标注 `fPresentationAttributes` 应该稀疏存储（`FIXME: this should be sparse`），当前每个节点都完整分配所有属性空间，对内存使用有一定影响。
- **路径 clip 操作**: `asPath()` 中的 `SkPathOps::Op()` 路径布尔运算是一个相对耗时的操作。
- **上下文复制**: 每次渲染都创建上下文副本，在深层嵌套的 SVG DOM 中可能产生一定开销。
- **属性解析**: `parseAndSetAttribute()` 使用短路求值的逻辑或链，当属性名匹配到较前的属性时可以快速返回。

## 相关文件

- `modules/svg/include/SkSVGNode.h` - 头文件，定义 SkSVGNode 类接口、SkSVGTag 枚举和 SVG_ATTR 宏
- `modules/svg/include/SkSVGAttribute.h` - SVG 属性枚举和展示属性结构体定义
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文类
- `modules/svg/include/SkSVGTypes.h` - SVG 类型定义
- `modules/svg/include/SkSVGTransformableNode.h` - 可变换节点中间类
- `modules/svg/src/SkSVGDOM.cpp` - 包含 `SkSVGNode::setAttribute(const char*, const char*)` 的实现
