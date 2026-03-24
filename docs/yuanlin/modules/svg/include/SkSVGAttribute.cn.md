# SkSVGAttribute

> 源文件: modules/svg/include/SkSVGAttribute.h

## 概述

`SkSVGAttribute` 定义了 Skia SVG 模块中所有支持的 SVG 属性类型和表现属性结构。该文件是 SVG 属性系统的核心,通过枚举类型 `SkSVGAttribute` 定义了所有可识别的 SVG 属性名称,并通过 `SkSVGPresentationAttributes` 结构体管理影响渲染的属性值。

这个模块为 SVG 元素的属性解析、存储和应用提供了类型安全的基础设施,支持属性继承机制,使得子元素可以从父元素继承某些视觉属性。

## 架构位置

该文件位于 Skia SVG 模块的公共接口层:

```
skia/
└── modules/
    └── svg/
        ├── include/
        │   ├── SkSVGAttribute.h       # 本文件:属性定义
        │   ├── SkSVGTypes.h           # 属性值类型定义
        │   ├── SkSVGNode.h            # SVG 节点基类
        │   └── SkSVGAttributeParser.h # 属性解析器
        └── src/
            ├── SkSVGAttribute.cpp     # 属性实现
            └── SkSVGNode.cpp          # 节点属性处理
```

## 主要类与结构体

### SkSVGAttribute 枚举

定义所有支持的 SVG 属性类型:

```cpp
enum class SkSVGAttribute {
    kClipRule,               // 裁剪规则
    kColor,                  // 颜色
    kColorInterpolation,     // 颜色插值
    kColorInterpolationFilters,  // 滤镜颜色插值
    kCx, kCy,               // 圆心坐标
    kFill,                  // 填充
    kFillOpacity,           // 填充不透明度
    kFillRule,              // 填充规则
    kFilter,                // 滤镜
    kFilterUnits,           // 滤镜单位
    kFontFamily,            // 字体族
    kFontSize,              // 字体大小
    kFontStyle,             // 字体样式
    kFontWeight,            // 字体粗细
    kFx, kFy,               // 焦点坐标
    kGradientUnits,         // 渐变单位
    kGradientTransform,     // 渐变变换
    kHeight,                // 高度
    kHref,                  // 链接引用
    kOpacity,               // 不透明度
    kPoints,                // 点集
    kPreserveAspectRatio,   // 保持纵横比
    kR,                     // 半径
    kRx, kRy,               // 椭圆半径
    kSpreadMethod,          // 扩展方法
    kStroke,                // 描边
    kStrokeDashArray,       // 虚线数组
    kStrokeDashOffset,      // 虚线偏移
    kStrokeOpacity,         // 描边不透明度
    kStrokeLineCap,         // 线端样式
    kStrokeLineJoin,        // 线连接样式
    kStrokeMiterLimit,      // 斜接限制
    kStrokeWidth,           // 描边宽度
    kTransform,             // 变换
    kText,                  // 文本内容
    kTextAnchor,            // 文本锚点
    kViewBox,               // 视图框
    kVisibility,            // 可见性
    kWidth,                 // 宽度
    kX, kY,                 // 坐标
    kX1, kY1,               // 起点坐标
    kX2, kY2,               // 终点坐标
    kUnknown,               // 未知属性
};
```

### SkSVGPresentationAttributes 结构体

管理所有影响元素视觉表现的属性:

```cpp
struct SkSVGPresentationAttributes {
    static SkSVGPresentationAttributes MakeInitial();

    // 填充属性 (可继承)
    SkSVGProperty<SkSVGPaint, true> fFill;
    SkSVGProperty<SkSVGNumberType, true> fFillOpacity;
    SkSVGProperty<SkSVGFillRule, true> fFillRule;
    SkSVGProperty<SkSVGFillRule, true> fClipRule;

    // 描边属性 (可继承)
    SkSVGProperty<SkSVGPaint, true> fStroke;
    SkSVGProperty<SkSVGDashArray, true> fStrokeDashArray;
    SkSVGProperty<SkSVGLength, true> fStrokeDashOffset;
    SkSVGProperty<SkSVGLineCap, true> fStrokeLineCap;
    SkSVGProperty<SkSVGLineJoin, true> fStrokeLineJoin;
    SkSVGProperty<SkSVGNumberType, true> fStrokeMiterLimit;
    SkSVGProperty<SkSVGNumberType, true> fStrokeOpacity;
    SkSVGProperty<SkSVGLength, true> fStrokeWidth;

    // 可见性 (可继承)
    SkSVGProperty<SkSVGVisibility, true> fVisibility;

    // 颜色属性 (可继承)
    SkSVGProperty<SkSVGColorType, true> fColor;
    SkSVGProperty<SkSVGColorspace, true> fColorInterpolation;
    SkSVGProperty<SkSVGColorspace, true> fColorInterpolationFilters;

    // 字体属性 (可继承)
    SkSVGProperty<SkSVGFontFamily, true> fFontFamily;
    SkSVGProperty<SkSVGFontStyle, true> fFontStyle;
    SkSVGProperty<SkSVGFontSize, true> fFontSize;
    SkSVGProperty<SkSVGFontWeight, true> fFontWeight;
    SkSVGProperty<SkSVGTextAnchor, true> fTextAnchor;

    // 非继承属性 (第二个模板参数为 false)
    SkSVGProperty<SkSVGNumberType, false> fOpacity;
    SkSVGProperty<SkSVGFuncIRI, false> fClipPath;
    SkSVGProperty<SkSVGDisplay, false> fDisplay;
    SkSVGProperty<SkSVGFuncIRI, false> fMask;
    SkSVGProperty<SkSVGFuncIRI, false> fFilter;
    SkSVGProperty<SkSVGColor, false> fStopColor;
    SkSVGProperty<SkSVGNumberType, false> fStopOpacity;
    SkSVGProperty<SkSVGColor, false> fFloodColor;
    SkSVGProperty<SkSVGNumberType, false> fFloodOpacity;
    SkSVGProperty<SkSVGColor, false> fLightingColor;
};
```

## 公共 API 函数

### MakeInitial()

创建初始的表现属性集合,包含所有属性的默认值。

```cpp
static SkSVGPresentationAttributes MakeInitial();
```

该方法在 `SkSVGAttribute.cpp` 中实现,返回符合 SVG 规范的默认属性值。

## 内部实现细节

### 属性继承机制

`SkSVGProperty` 的第二个模板参数控制属性是否可继承:

```cpp
SkSVGProperty<T, true>   // 可继承属性
SkSVGProperty<T, false>  // 不可继承属性
```

**可继承属性:**
- 填充和描边相关属性
- 字体属性
- 颜色插值属性
- 可见性属性

**不可继承属性:**
- 不透明度 (`opacity`)
- 裁剪路径 (`clip-path`)
- 显示模式 (`display`)
- 滤镜效果 (`filter`)
- 特效相关颜色 (`stop-color`, `flood-color`, `lighting-color`)

### 属性分组

属性按功能分为几个主要类别:

1. **几何属性**: `kX`, `kY`, `kWidth`, `kHeight`, `kR`, `kRx`, `kRy`, `kCx`, `kCy`
2. **填充属性**: `kFill`, `kFillOpacity`, `kFillRule`
3. **描边属性**: `kStroke`, `kStrokeWidth`, `kStrokeOpacity`, 等
4. **文本属性**: `kFontFamily`, `kFontSize`, `kTextAnchor`, 等
5. **变换属性**: `kTransform`, `kGradientTransform`
6. **引用属性**: `kHref`, `kClipPath`, `kMask`, `kFilter`
7. **效果属性**: `kOpacity`, `kVisibility`, `kDisplay`

## 依赖关系

**直接依赖:**
- `modules/svg/include/SkSVGTypes.h` - 所有属性值类型定义

**被依赖:**
- `modules/svg/include/SkSVGNode.h` - 节点使用属性
- `modules/svg/include/SkSVGAttributeParser.h` - 解析属性
- `modules/svg/src/SkSVGAttribute.cpp` - 属性实现
- 所有 SVG 元素类 - 使用和操作属性

## 设计模式与设计决策

### 枚举类 vs 字符串

使用枚举类而非字符串表示属性名的优点:
- 编译时类型检查
- 更高效的比较和 switch 语句
- 更小的内存占用
- 自动完成支持

### 属性包装器模式

使用 `SkSVGProperty<T, inheritable>` 包装属性值提供:
- 统一的接口
- 值未设置状态的表示
- 继承语义的编码
- 类型安全

### 分离定义与实现

头文件只包含接口定义,实际的属性值类型在 `SkSVGTypes.h` 中定义。这种分离:
- 减少编译依赖
- 提高编译速度
- 保持接口清晰

### 注释驱动的文档

枚举值使用注释说明其应用上下文:

```cpp
kCx, // <circle>, <ellipse>, <radialGradient>: center x position
kR,  // <circle>, <radialGradient>: radius
```

这帮助开发者理解属性的适用范围。

## 性能考量

### 内存布局

每个属性使用 `SkSVGProperty` 包装,根据注释:

```cpp
// TODO: SkSVGProperty adds an extra ptr per attribute; refactor to reduce overhead.
```

当前实现每个属性有额外的指针开销。考虑到一个元素可能有 20+ 个表现属性,这可能导致显著的内存开销。

**潜在优化:**
- 使用位域标记属性是否已设置
- 使用 union 或 variant 存储属性值
- 按需分配属性存储

### 属性查找

枚举类型使得属性查找可以通过:
- 数组索引 O(1)
- Switch 语句 O(1)
- Hash 表 O(1)

比字符串比较 O(n) 更高效。

### 继承处理

属性继承在运行时通过模板参数编码,无需运行时查询,提高了属性解析和应用的效率。

## 相关文件

**类型定义:**
- `/modules/svg/include/SkSVGTypes.h` - 所有属性值类型

**属性处理:**
- `/modules/svg/include/SkSVGAttributeParser.h` - 属性解析
- `/modules/svg/src/SkSVGAttribute.cpp` - 属性实现
- `/modules/svg/include/SkSVGNode.h` - 节点属性管理

**属性应用:**
- `/modules/svg/include/SkSVGRenderContext.h` - 渲染上下文中的属性应用
- `/modules/svg/src/SkSVGNode.cpp` - 节点属性处理逻辑

**SVG 元素:**
- 所有 `/modules/svg/include/SkSVG*.h` 文件 - 使用这些属性定义
