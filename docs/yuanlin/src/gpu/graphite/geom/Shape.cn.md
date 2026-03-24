# Shape

> 源文件
> - src/gpu/graphite/geom/Shape.h
> - src/gpu/graphite/geom/Shape.cpp

## 概述

`Shape` 是 Skia Graphite 图形后端中用于表示几何形状的统一抽象类，本质上是对不同几何类型的变体封装（类似于 `std::variant`）。它支持线段、矩形、圆角矩形、圆弧和路径等多种几何形状，提供了一致的接口用于查询几何属性，如凸性判定、点包含测试和边界计算等。该类是 Graphite 渲染管线中几何处理的核心组件，为上层绘制操作提供了灵活而高效的几何表达方式。

`Shape` 类通过联合体（union）存储不同类型的几何数据，配合类型标签实现零开销的类型区分。它还支持反转填充（inverted fill）语义，可以表示几何形状的内部或外部区域，这在实现复杂的裁剪效果时非常有用。

## 架构位置

`Shape` 位于 Skia Graphite 渲染架构的几何层（geometry layer），在整个渲染流程中处于以下位置：

```
应用层绘制命令
    ↓
SkPath / SkRect / SkRRect 等公共几何类型
    ↓
Shape（几何统一抽象层）← 当前组件
    ↓
Transform（几何变换）
    ↓
BoundsManager / Clip（边界管理与裁剪）
    ↓
Renderer（渲染器）
    ↓
命令缓冲区
```

该类是 Graphite 后端特有的内部表示，将 Skia 公共 API 的几何类型统一转换为 Graphite 可处理的格式。它与 `Transform` 类协同工作，共同完成几何的变换和属性查询。

## 主要类与结构体

### Shape::Type 枚举

定义了支持的几何类型：

```cpp
enum class Type : uint8_t {
    kEmpty,   // 空形状
    kLine,    // 线段
    kRect,    // 矩形
    kRRect,   // 圆角矩形
    kArc,     // 圆弧
    kPath     // 通用路径
};
```

### 核心成员变量

```cpp
union {
    Rect    fRect;   // 矩形数据（线段类型时存储端点）
    SkRRect fRRect;  // 圆角矩形数据
    SkArc   fArc;    // 圆弧数据
    SkPath  fPath;   // 路径数据
};
Type fType;          // 当前几何类型
bool fInverted;      // 是否反转填充
```

联合体设计使得 `Shape` 对象可以存储任意一种几何类型，而不增加额外的内存开销。

## 公共 API 函数

### 构造与赋值

```cpp
// 默认构造函数
Shape();

// 拷贝构造与赋值
Shape(const Shape& shape);
Shape& operator=(const Shape& shape);

// 类型化构造函数
Shape(SkPoint p0, SkPoint p1);           // 线段
explicit Shape(const Rect& rect);        // 矩形
explicit Shape(const SkRRect& rrect);    // 圆角矩形
explicit Shape(const SkArc& arc);        // 圆弧
explicit Shape(const SkPath& path);      // 路径
```

### 类型查询

```cpp
Type type() const;                       // 获取当前类型
bool isEmpty() const;                    // 是否为空
bool isLine() const;                     // 是否为线段
bool isRect() const;                     // 是否为矩形
bool isRRect() const;                    // 是否为圆角矩形
bool isArc() const;                      // 是否为圆弧
bool isPath() const;                     // 是否为路径
bool isVolatilePath() const;             // 是否为易失路径
bool inverted() const;                   // 是否反转填充
```

### 几何属性查询

```cpp
// 保守包含测试（假设为填充闭合形状）
bool conservativeContains(const Rect& rect) const;
bool conservativeContains(skvx::float2 point) const;

// 凸性判定
bool convex(bool simpleFill = true) const;

// 边界框计算
Rect bounds() const;

// 转换为路径表示
SkPath asPath() const;
```

### 几何数据访问

```cpp
// 常量访问器
skvx::float2   p0() const;               // 线段起点
skvx::float2   p1() const;               // 线段终点
const Rect&    rect() const;             // 矩形引用
const SkRRect& rrect() const;            // 圆角矩形引用
const SkArc&   arc() const;              // 圆弧引用
const SkPath&  path() const;             // 路径引用

// 非常量访问器（用于修改）
Rect&    rect();
SkRRect& rrect();
SkArc&   arc();
SkPath&  path();
```

### 几何数据设置

```cpp
void setLine(SkPoint p0, SkPoint p1);
void setRect(const Rect& rect);
void setRRect(const SkRRect& rrect);
void setArc(const SkArc& arc);
void setPath(const SkPath& path);
void setInverted(bool inverted);         // 设置反转状态
void reset();                            // 重置为空
```

### 序列化与缓存键生成

```cpp
int keySize() const;                     // 获取键的大小
void writeKey(uint32_t* key, bool includeInverted) const;  // 写入缓存键
```

## 内部实现细节

### 类型切换机制

`Shape` 使用联合体存储不同类型的几何数据，但 `SkPath` 需要显式构造和析构：

```cpp
void setType(Type type) {
    if (this->isPath() && type != Type::kPath) {
        fPath.~SkPath();  // 显式析构路径对象
    }
    fType = type;
}
```

当从路径类型切换到其他类型时，必须调用析构函数释放路径资源；从其他类型切换到路径时，使用 placement new 在联合体内存上构造路径对象。

### 保守包含测试实现

`conservativeContains` 方法根据几何类型采用不同的包含测试策略：

- **矩形**：直接使用边界比较
- **圆角矩形**：调用 `SkRRectPriv::ContainsPoint`
- **路径**：使用 `SkPath::contains` 或 `conservativelyContainsRect`
- **圆弧**：对于楔形（wedge）类型，转换为路径后进行测试

对于反转形状，需要临时创建非反转副本进行测试。

### 凸性判定

```cpp
bool Shape::convex(bool simpleFill) const {
    if (this->isPath()) {
        return (simpleFill || fPath.isLastContourClosed()) && fPath.isConvex();
    } else if (this->isArc()) {
        return SkPathPriv::DrawArcIsConvex(fArc.sweepAngle(), fArc.fType, simpleFill);
    } else {
        return true;  // 其他类型天然是凸的
    }
}
```

线段、矩形和圆角矩形在构造上都是凸形状，只有路径和圆弧需要动态判定。

### 缓存键生成

`Shape` 实现了高效的缓存键生成机制，用于着色器缓存和几何去重：

1. **小路径优化**：对于动词数不超过 `kMaxKeyFromDataVerbCnt`（10）的路径，直接序列化路径数据作为键，提高不同 genID 路径的匹配率
2. **大路径处理**：使用路径的生成 ID（generation ID）作为键
3. **其他类型**：直接序列化几何数据

键的第一个 uint32_t 存储状态标志：

```cpp
uint32_t Shape::stateKey(bool includeInverted) const {
    uint32_t key = /* 填充类型或反转标志 */;
    key |= ((uint32_t) fType) << 2;  // 低 2 位存填充类型，后续位存几何类型
    return key;
}
```

### 路径转换

`asPath()` 方法将所有几何类型统一转换为 `SkPath` 表示：

- **线段**：`moveTo` + `lineTo`
- **矩形**：`addRect`
- **圆角矩形**：`addRRect`
- **圆弧**：调用 `SkPathPriv::CreateDrawArcPath` 创建圆弧路径
- **路径**：直接返回副本

这为需要通用路径接口的上层代码提供了便利。

## 依赖关系

### 直接依赖

- **Rect**：Graphite 的矩形表示，用于边界和线段存储
- **SkRRect**：Skia 的圆角矩形类
- **SkArc**：Skia 的圆弧表示
- **SkPath**：Skia 的通用路径类
- **skvx**：SIMD 向量类型，用于高效的点和线段表示

### 被依赖

- **Renderer**：渲染器使用 `Shape` 描述待绘制的几何
- **BoundsManager**：使用 `Shape::bounds()` 计算绘制边界
- **Clip**：裁剪系统使用 `Shape` 表示裁剪区域
- **Transform**：与 `Shape` 协同进行几何变换

## 设计模式与设计决策

### 变体模式（Variant Pattern）

`Shape` 本质上是手动实现的变体类型，使用联合体和类型标签实现。这种设计避免了虚函数的开销，同时保持了类型安全。

**设计优势**：
- 零虚函数调用开销
- 内存布局紧凑
- 类型安全的访问接口

### 值语义（Value Semantics）

`Shape` 设计为值类型，支持拷贝但不支持移动（移动对几何类型没有性能优势）：

```cpp
Shape(Shape&&) = delete;           // 删除移动构造
Shape& operator=(Shape&&) = delete; // 删除移动赋值
```

这简化了使用场景，避免了资源所有权的复杂性。

### 延迟简化（Lazy Simplification）

`Shape` 不会自动简化几何，例如半径为零的 `SkRRect` 仍然保持为 `kRRect` 类型：

```cpp
// 即使 rrect.isRect() 为 true，类型仍是 kRRect
shape.setRRect(rrect);
assert(shape.isRRect() == true);
```

这将简化决策留给调用者，避免不必要的类型转换开销。

### 反转填充支持

通过 `fInverted` 标志统一处理反转填充语义，而不是为每种类型创建独立的反转变体：

```cpp
bool inverted() const { return fInverted; }
void setInverted(bool inverted);
```

这使得裁剪操作可以方便地表示"外部区域"，减少了代码复杂度。

## 性能考量

### 内存布局优化

`Shape` 的内存占用约为：
```
sizeof(Shape) = sizeof(SkPath) + sizeof(Type) + sizeof(bool)
              ≈ 64 字节（取决于 SkPath 实现）
```

联合体确保不同类型共享内存，避免了多余的空间开销。

### 缓存友好性

状态标志（`fType` 和 `fInverted`）紧邻联合体，有利于 CPU 缓存预取。类型判定是非常热的代码路径，紧凑的布局有助于减少缓存未命中。

### 小路径键优化

通过直接序列化小路径数据生成缓存键，避免了路径生成 ID 碰撞导致的缓存未命中。经验数据显示动词数 ≤ 10 的路径占相当比例，这一优化能显著提高缓存命中率。

### 模糊容差常量

`kDefaultPixelTolerance = 0.0039f` 是经验确定的像素级容差，用于：
- 几何比较的模糊判等
- 抗锯齿半径计算
- 包含测试的误差容忍

该值约为 1/255 像素，符合人眼感知阈值。

### 避免不必要的路径转换

`asPath()` 创建新的 `SkPath` 对象，应避免在热路径频繁调用。渲染器优先使用特化的几何类型处理，仅在必要时才回退到通用路径表示。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/geom/Rect.h` | Graphite 矩形表示，`Shape` 内部使用 |
| `src/gpu/graphite/geom/Transform.h` | 几何变换类，与 `Shape` 协同工作 |
| `include/core/SkPath.h` | Skia 通用路径类 |
| `include/core/SkRRect.h` | Skia 圆角矩形类 |
| `include/core/SkArc.h` | Skia 圆弧表示 |
| `src/core/SkPathPriv.h` | 路径私有工具函数 |
| `src/core/SkRRectPriv.h` | 圆角矩形私有工具函数 |
| `src/gpu/graphite/Renderer.h` | 渲染器，消费 `Shape` 对象 |
| `src/gpu/graphite/geom/BoundsManager.h` | 边界管理器，使用 `Shape` 计算边界 |
| `src/base/SkVx.h` | SIMD 向量类型定义 |
