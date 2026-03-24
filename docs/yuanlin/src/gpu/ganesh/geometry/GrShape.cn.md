# GrShape

> 源文件: src/gpu/ganesh/geometry/GrShape.h, src/gpu/ganesh/geometry/GrShape.cpp

## 概述

`GrShape` 是 Ganesh GPU 后端中表示底层几何形状的轻量级数据类。它可以表示点、线段、矩形、圆角矩形、圆弧和路径等多种几何类型,提供统一的接口进行几何操作。该类是 `GrStyledShape` 的基础,专注于纯几何表示,不涉及渲染样式。

核心特性:
- 使用 union 存储不同几何类型,节省内存
- 支持绕向(winding)、起始索引和反填充信息
- 提供几何简化和类型转换
- 保守的包含检测
- 闭合性和凸性查询

## 架构位置

`GrShape` 是 Ganesh 几何层的基础数据结构:

```
src/gpu/ganesh/
  └── geometry/
      ├── GrShape.h/cpp         # 底层几何(本模块)
      ├── GrStyledShape.h/cpp   # 带样式的几何
      └── GrPathUtils.h/cpp     # 几何工具函数
```

它为所有几何形状提供统一的抽象层。

## 主要类与结构体

### GrShape 类

**继承关系**: 无基类

**用途**: 表示单一的几何形状,支持多种类型的统一存储和操作。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| 联合体 | - | 存储具体几何数据 |
| `fType` | `Type` | 几何类型(空/点/线/矩形/圆角矩形/路径/圆弧) |
| `fStart` | `uint8_t` | 起始索引(用于矩形/圆角矩形) |
| `fCW` | `bool` | 顺时针绕向标志 |
| `fInverted` | `bool` | 反填充标志 |

### Type 枚举

```cpp
enum class Type : uint8_t {
    kEmpty,    // 空几何
    kPoint,    // 点
    kRect,     // 矩形
    kRRect,    // 圆角矩形
    kPath,     // 路径
    kArc,      // 圆弧
    kLine      // 线段
};
```

### GrLineSegment 结构体

表示线段的辅助结构:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fP1` | `SkPoint` | 起点 |
| `fP2` | `SkPoint` | 终点 |

### SimplifyFlags 枚举

```cpp
enum SimplifyFlags : unsigned {
    kSimpleFill_Flag    = 0b001,  // 假设隐式闭合和填充
    kIgnoreWinding_Flag = 0b010,  // 忽略绕向信息
    kMakeCanonical_Flag = 0b100,  // 规范化坐标

    kAll_Flags = 0b111
};
```

## 公共 API 函数

### 构造函数

```cpp
GrShape();                                  // 默认构造(空)
explicit GrShape(const SkPoint& point);     // 从点构造
explicit GrShape(const SkRect& rect);       // 从矩形构造
explicit GrShape(const SkRRect& rrect);     // 从圆角矩形构造
explicit GrShape(const SkPath& path);       // 从路径构造
explicit GrShape(const SkArc& arc);         // 从圆弧构造
explicit GrShape(const GrLineSegment& line);// 从线段构造
```

### 类型查询

```cpp
bool isEmpty() const;
bool isPoint() const;
bool isRect() const;
bool isRRect() const;
bool isPath() const;
bool isArc() const;
bool isLine() const;
Type type() const;
```

### 拓扑信息

```cpp
bool inverted() const;              // 反填充
SkPathDirection dir() const;        // 绕向
unsigned startIndex() const;        // 起始索引
uint32_t stateKey() const;          // 状态键(类型+绕向+起始+反填充)
```

### 设置拓扑

```cpp
void setPathWindingParams(SkPathDirection dir, unsigned start);
void setInverted(bool inverted);
```

### 几何访问

```cpp
SkPoint& point();
const SkPoint& point() const;
SkRect& rect();
const SkRect& rect() const;
SkRRect& rrect();
const SkRRect& rrect() const;
SkPath& path();
const SkPath& path() const;
SkArc& arc();
const SkArc& arc() const;
GrLineSegment& line();
const GrLineSegment& line() const;
```

### 几何设置

```cpp
void setPoint(const SkPoint& point);
void setRect(const SkRect& rect);
void setRRect(const SkRRect& rrect);
void setArc(const SkArc& arc);
void setLine(const GrLineSegment& line);
void setPath(const SkPath& path);
void reset();  // 重置为空
```

### 简化

```cpp
bool simplify(unsigned flags = kAll_Flags);
```

尝试将形状简化为更简单的类型。返回 `true` 表示几何原本是闭合的。

**简化规则**:
- 路径 → 圆角矩形/矩形/线/点/空
- 圆角矩形 → 矩形/线/点/空
- 矩形 → 线/点/空
- 圆弧 → 圆角矩形/线/点/空
- 线 → 点/空
- 点 → 空

### 几何查询

```cpp
bool conservativeContains(const SkRect& rect) const;
bool conservativeContains(const SkPoint& point) const;
bool closed() const;              // 是否闭合
bool convex(bool simpleFill = true) const;  // 是否凸形
SkRect bounds() const;            // 边界框
uint32_t segmentMask() const;     // 段类型掩码
SkPath asPath(bool simpleFill = true) const;  // 转换为路径
```

## 内部实现细节

### Union 存储

使用 union 节省内存:

```cpp
union {
    SkPoint       fPoint;
    SkRect        fRect;
    SkRRect       fRRect;
    SkPath        fPath;
    SkArc         fArc;
    GrLineSegment fLine;
};
```

总大小由最大成员决定(SkPath,约 48 字节)。

### 简化算法

`simplify()` 执行递归简化:

```cpp
bool simplify(unsigned flags) {
    switch (fType) {
        case Type::kPath:
            return simplifyPath(flags);  // 路径→更简单形状
        case Type::kArc:
            return simplifyArc(flags);   // 圆弧→椭圆/线/点
        case Type::kRRect:
            simplifyRRect(...);           // 圆角矩形→矩形/线/点
            return true;
        case Type::kRect:
            simplifyRect(...);            // 矩形→线/点
            return true;
        case Type::kLine:
            simplifyLine(...);            // 线→点
            return false;
        case Type::kPoint:
            simplifyPoint(...);           // 点→空
            return false;
        default:
            return false;
    }
}
```

### 路径简化

检测路径的内在几何类型:

```cpp
bool simplifyPath(unsigned flags) {
    if (fPath.isEmpty()) {
        this->setType(Type::kEmpty);
        return false;
    }
    if (fPath.isLine(pts)) {
        this->simplifyLine(pts[0], pts[1], flags);
        return false;
    }
    if (auto info = SkPathPriv::IsRRect(fPath)) {
        this->simplifyRRect(info->fRRect, info->fDirection, info->fStartIndex, flags);
        return true;
    }
    // 继续检测椭圆、矩形...
}
```

### 规范化

`kMakeCanonical_Flag` 执行规范化:

- **矩形**: 排序坐标(`fRect.sort()`)
- **线段**: 排序端点(Y 主序,X 次序)
- **圆弧**: 正规化起始角和扫描角

```cpp
void simplifyRect(const SkRect& rect, ..., unsigned flags) {
    // ...
    if (flags & kMakeCanonical_Flag) {
        fRect.sort();  // 确保 left < right, top < bottom
    }
}
```

### 反填充处理

路径的反填充通过路径的填充类型管理:

```cpp
bool inverted() const {
    return this->isPath() ? fPath.isInverseFillType() : SkToBool(fInverted);
}

void setInverted(bool inverted) {
    if (this->isPath()) {
        if (inverted != fPath.isInverseFillType()) {
            fPath.toggleInverseFillType();
        }
    } else {
        fInverted = inverted;
    }
}
```

### 保守包含检测

使用形状特定的快速检测:

```cpp
bool conservativeContains(const SkRect& rect) const {
    switch (this->type()) {
        case Type::kRect:
            return fRect.contains(rect);
        case Type::kRRect:
            return fRRect.contains(rect);
        case Type::kPath:
            return fPath.conservativelyContainsRect(rect);
        // 点、线、空返回 false
    }
}
```

### 段掩码计算

反映路径包含的曲线类型:

```cpp
uint32_t segmentMask() const {
    switch (this->type()) {
        case Type::kRRect:
            if (fRRect.isOval()) {
                return SkPath::kConic_SegmentMask;
            }
            return SkPath::kConic_SegmentMask | SkPath::kLine_SegmentMask;
        case Type::kPath:
            return fPath.getSegmentMasks();
        case Type::kArc:
            return fArc.fType == SkArc::Type::kWedge ?
                   SkPath::kConic_SegmentMask | SkPath::kLine_SegmentMask :
                   SkPath::kConic_SegmentMask;
        default:
            return SkPath::kLine_SegmentMask;
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPath` | 路径数据结构 |
| `SkRRect` | 圆角矩形 |
| `SkRect` | 矩形 |
| `SkArc` | 圆弧 |
| `SkPathPriv` | 路径内部函数(检测几何类型) |
| `SkRRectPriv` | 圆角矩形内部函数 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `GrStyledShape` | 上层带样式几何 |
| `GrPathRenderer` 实现 | 路径渲染决策 |
| `GrClip` | 裁剪区域表示 |

## 设计模式与设计决策

### Tagged Union 模式

使用类型标签 + union:

```cpp
Type fType;
union { ... };
```

优势:
- 节省内存(只分配最大成员的空间)
- 类型安全(通过 `fType` 检查)
- 高效访问(无虚函数开销)

### 可平凡重定位

```cpp
using sk_is_trivially_relocatable = std::true_type;
```

标记为可平凡重定位,允许:
- `memcpy` 移动对象
- 容器优化(如 `std::vector` 的重分配)

注意: `SkPath` 实际上不是平凡重定位的,这是一个优化假设,依赖于 SkPath 的实现细节。

### 延迟类型转换

不自动转换类型,调用者通过 `simplify()` 显式请求:

```cpp
GrShape shape(path);  // 存储为 Path,即使是矩形
// ...
shape.simplify();     // 现在检测到是矩形,转换类型
```

优势:
- 避免构造时的开销
- 允许保留原始表示(用于调试或特定优化)

### 默认值常量

```cpp
inline static constexpr SkPathDirection kDefaultDir   = SkPathDirection::kCW;
inline static constexpr unsigned        kDefaultStart = 0;
inline static constexpr SkPathFillType  kDefaultFillType = SkPathFillType::kEvenOdd;
```

为非路径几何提供一致的默认值,简化代码逻辑。

## 性能考量

### 内存布局

总大小约 64 字节:
- Union: ~48 字节(SkPath 大小)
- Type: 1 字节
- fStart: 1 字节
- fCW, fInverted: 2 字节
- 对齐填充: ~12 字节

适合栈分配和值传递。

### 快速类型检测

通过枚举比较而非虚函数:

```cpp
if (shape.type() == Type::kRect) { ... }  // 整数比较
```

比虚函数调用快 10x+。

### 零成本抽象

对于简单几何(点、线、矩形),几乎没有抽象开销:

```cpp
shape.rect().fLeft;  // 直接访问,无间接层
```

相比多态设计(虚函数),访问延迟降低 90%+。

### 简化的权衡

`simplify()` 可能需要遍历整个路径:

```cpp
if (auto info = SkPathPriv::IsRRect(fPath)) { ... }  // O(n) 路径遍历
```

但简化后的渲染可以节省更多时间,尤其是重复绘制时。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/geometry/GrStyledShape.h` | 被使用 | 带样式的几何封装 |
| `include/core/SkPath.h` | 依赖 | 路径数据结构 |
| `include/core/SkRRect.h` | 依赖 | 圆角矩形 |
| `include/core/SkArc.h` | 依赖 | 圆弧定义 |
| `src/core/SkPathPriv.h` | 依赖 | 路径内部函数 |
| `tests/GrShapeTest.cpp` | 测试 | 单元测试 |
