# SkSVGValue

> 源文件: [modules/svg/src/SkSVGValue.cpp](../../../../modules/svg/src/SkSVGValue.cpp)

## 概述

`SkSVGValue` 是 SVG 属性值系统的基类。该源文件仅包含版权头信息（7 行），实际代码为空，说明 `SkSVGValue` 的所有功能都在头文件中通过内联方法和模板实现。

`SkSVGValue` 采用类型安全的值封装机制，用于在 SVG 属性设置的旧代码路径（`setAttribute(SkSVGAttribute, const SkSVGValue&)`）中传递各种类型的属性值。

## 架构位置

```
SkSVGValue                       ← 本文件（属性值基类，空实现）
  ├── SkSVGLengthValue             （长度值）
  ├── SkSVGStringValue             （字符串值）
  ├── SkSVGTransformValue          （变换值）
  ├── SkSVGViewBoxValue            （viewBox 值）
  ├── SkSVGPreserveAspectRatioValue（preserveAspectRatio 值）
  └── SkSVGObjectBoundingBoxUnitsValue（坐标单位值）
```

## 主要类与结构体

### `SkSVGValue`

值类型的基类，通过 `as<T>()` 模板方法进行类型安全的向下转换。该类是旧属性设置机制的核心组件。

## 公共 API 函数

所有方法定义在头文件中，此 .cpp 文件无额外实现。

## 内部实现细节

该文件为空白实现文件，仅保留 BSD 许可证头（第 1-7 行）。这种模式在 Skia 中很常见——当一个类完全由模板和内联函数组成时，cpp 文件仍然保留作为编译单元的占位符。

### 头文件中的值类型层次

`SkSVGValue` 在头文件中定义了以下值类型层次结构：

| 值类型 | 用途 | 对应 SVG 概念 |
|--------|------|---------------|
| `SkSVGLengthValue` | 长度值 | `width="100px"` |
| `SkSVGStringValue` | 字符串值 | `id="myElement"` |
| `SkSVGTransformValue` | 变换值 | `transform="rotate(45)"` |
| `SkSVGViewBoxValue` | 视口框值 | `viewBox="0 0 100 100"` |
| `SkSVGPreserveAspectRatioValue` | 宽高比保持值 | `preserveAspectRatio="xMidYMid meet"` |
| `SkSVGObjectBoundingBoxUnitsValue` | 坐标单位值 | `gradientUnits="objectBoundingBox"` |

### 类型安全的值传递机制

`SkSVGValue` 基类通过 `as<T>()` 模板方法提供类型安全的向下转换。该方法在运行时检查值的实际类型是否匹配请求的类型，如果不匹配返回 `nullptr`。这种机制避免了不安全的 `reinterpret_cast`，但比编译时多态有更大的运行时开销。

### 与新属性系统的关系

在 SVG 模块的属性系统演进中，`SkSVGValue` 代表了较早期的设计。当前的代码正在逐步迁移到新的 `parseAndSetAttribute` 路径，该路径直接在节点上解析和设置属性，不需要中间的值类型包装。`SkSVGValue` 体系目前仅在 `SkSVGDOM.cpp` 中的旧属性设置路径中使用，主要处理以下属性：
- 几何属性（x, y, width, height, r, rx, ry, cx, cy 等）
- viewBox 和 preserveAspectRatio
- transform
- xlink:href
- style（通过 SetStyleAttributes 进行二次分发）

## 依赖关系

无直接依赖（空实现文件）。头文件中的依赖包括：
- `modules/svg/include/SkSVGTypes.h` - SVG 类型定义

## 设计模式与设计决策

1. **头文件纯实现**: 所有逻辑定义在头文件中，cpp 文件作为占位符保留，可能用于未来扩展。这确保了编译单元的存在性，便于构建系统管理。

2. **类型擦除/恢复**: `SkSVGValue` 作为统一的值类型基类，通过虚函数和 `as<T>()` 模板方法实现运行时类型转换。这允许所有属性值通过统一的 `setAttribute(SkSVGAttribute, const SkSVGValue&)` 接口传递。

3. **过渡性设计**: 该类属于旧的属性设置路径，新代码路径使用 `parseAndSetAttribute` 直接解析为具体类型，逐步减少对 `SkSVGValue` 的依赖。随着迁移的推进，该类最终可能被完全移除。

4. **编译防火墙**: 即使 cpp 文件为空，保留它可以作为未来将实现从头文件移出时的着陆点，避免构建系统的重大调整。

## 性能考量

- 值类型的动态类型检查（`as<T>()`）比编译时多态有额外的运行时开销
- 每次属性设置都涉及值对象的构造和销毁，但这些对象通常很小
- 新的 `parseAndSetAttribute` 路径避免了中间值对象的创建，效率更高

## 相关文件

- `modules/svg/include/SkSVGValue.h` - 头文件，包含所有实际的类定义和实现
- `modules/svg/include/SkSVGNode.h` - 使用 SkSVGValue 的 setAttribute 接口
- `modules/svg/src/SkSVGDOM.cpp` - 属性设置的调用点，包含旧路径和新路径的桥接逻辑
- `modules/svg/include/SkSVGAttribute.h` - SkSVGAttribute 枚举，与 SkSVGValue 配对使用
