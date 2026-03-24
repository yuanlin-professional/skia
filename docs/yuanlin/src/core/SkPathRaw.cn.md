# SkPathRaw

> 源文件
> - src/core/SkPathRaw.h
> - src/core/SkPathRaw.cpp

## 概述

`SkPathRaw` 是 Skia 中路径几何数据的一个轻量级、非拥有式、不可变视图结构。它提供了一种栈上分配路径的方式，避免堆内存分配，特别适合处理已知几何形状。这个结构体包含指向路径点、动词、圆锥曲线权重等数据的跨度（span），以及边界矩形、填充类型、凸性和分段掩码等元数据。

## 架构位置

`SkPathRaw` 位于 Skia 核心路径系统中，处于基础路径表示层：

- 位于 `src/core` 目录，属于内部实现模块
- 作为路径数据的只读视图，与 `SkPath` 和 `SkPathBuilder` 形成互补
- 为栈上分配的路径形状（如 `SkPathRawShapes`）提供基础结构
- 通过 `SkPathIter` 提供路径迭代能力

## 主要类与结构体

### SkPathRaw

路径几何数据的非拥有式视图结构。

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPoints` | `SkSpan<const SkPoint>` | 路径点数组的只读跨度 |
| `fVerbs` | `SkSpan<const SkPathVerb>` | 路径动词（命令）数组的只读跨度 |
| `fConics` | `SkSpan<const float>` | 圆锥曲线权重数组的只读跨度 |
| `fBounds` | `SkRect` | 路径的边界矩形 |
| `fFillType` | `SkPathFillType` | 填充类型（如 Winding、EvenOdd） |
| `fConvexity` | `SkPathConvexity` | 路径的凸性信息 |
| `fSegmentMask` | `uint8_t` | 路径分段类型掩码（线段、二次曲线、圆锥曲线、三次曲线） |

## 公共 API 函数

### 访问器函数

```cpp
SkSpan<const SkPoint> points() const;
SkSpan<const SkPathVerb> verbs() const;
SkSpan<const float> conics() const;
SkRect bounds() const;
SkPathFillType fillType() const;
SkPathConvexity convexity() const;
unsigned segmentMasks() const;
```

提供对路径数据各组成部分的只读访问。

### 状态查询函数

```cpp
bool empty() const;
```

判断路径是否为空（没有动词）。

```cpp
bool isInverseFillType() const;
```

判断是否为反向填充类型。

```cpp
bool isKnownToBeConvex() const;
```

判断路径是否已知为凸形。

```cpp
std::optional<SkRect> isRect() const;
```

检测路径是否为矩形，如果是则返回矩形对象。

### 迭代器函数

```cpp
SkPathIter iter() const;
```

返回用于遍历路径的迭代器，该迭代器使用路径的点、动词和圆锥曲线权重进行初始化。

### 静态工厂函数

```cpp
static SkPathRaw Empty(SkPathFillType ft = SkPathFillType::kDefault);
```

创建一个空的 `SkPathRaw` 实例，具有指定的填充类型。

## 内部实现细节

### 分段掩码计算

`SkPathPriv::ComputeSegmentMask` 函数通过遍历动词数组，使用查找表 `gVerbToSegmentMask` 快速计算路径包含的分段类型：

```cpp
const uint8_t gVerbToSegmentMask[] = {
    0,  // move
    kLine_SkPathSegmentMask,      // line
    kQuad_SkPathSegmentMask,      // quad
    kConic_SkPathSegmentMask,     // conic
    kCubic_SkPathSegmentMask,     // cubic
    0,  // close
};
```

该掩码用于快速判断路径是否包含特定类型的曲线段，无需完整遍历路径。

### 矩形检测

`SkPathRaw::isRect()` 使用 `SkPathPriv::IsRectContour` 进行检测：

- 利用已计算的分段掩码快速排除包含曲线的路径
- 检查路径是否由 4 条线段组成闭合轮廓
- 如果是矩形，返回边界矩形；否则返回空 optional

### 数据生命周期管理

`SkPathRaw` 不拥有数据，仅持有指向外部数据的跨度：

- 创建者负责确保被引用的数据在 `SkPathRaw` 生命周期内保持有效
- 适用于栈上分配的临时路径数据
- 避免不必要的内存分配和拷贝

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `SkPathIter` | 提供路径迭代能力 |
| `SkPathTypes` | 路径类型定义（填充类型、动词等） |
| `SkPoint` | 点数据类型 |
| `SkRect` | 矩形数据类型 |
| `SkSpan` | 提供只读数组视图 |
| `SkPathEnums` | 路径枚举（凸性等） |
| `SkPathPriv` | 路径私有辅助函数 |

**被依赖的模块**

| 模块 | 关系 |
|------|------|
| `SkPathRawShapes` | 使用 `SkPathRaw` 作为基类构建各种形状 |
| 路径渲染管线 | 作为轻量级路径表示的替代方案 |

## 设计模式与设计决策

### 非拥有式视图模式

`SkPathRaw` 采用视图模式（View Pattern），不拥有数据：

- 使用 `SkSpan` 提供对外部数据的只读访问
- 降低内存开销，避免数据拷贝
- 适合短生命周期的临时对象

### 栈分配优化

设计目标是支持栈上分配的路径对象：

- 配合 `SkPathRawShapes` 实现完全栈上的形状创建
- 避免堆内存分配，提高性能
- 适用于已知形状（矩形、椭圆、圆角矩形等）的快速创建

### 不可变性

所有成员函数返回 const 引用或值：

- 确保数据在使用过程中不会被修改
- 提供线程安全的读取保证
- 简化推理和调试

### 元数据缓存

结构体直接包含预计算的元数据：

- 边界矩形、凸性、分段掩码等信息已经计算好
- 避免重复计算，提高查询效率
- 适合频繁查询的场景

## 性能考量

### 内存效率

- 使用 `SkSpan` 而非 `std::vector`，避免动态内存分配
- 结构体大小固定，适合栈分配
- 零拷贝设计，直接引用外部数据

### 查询性能

- 分段掩码提供 O(1) 的曲线类型查询
- 边界矩形和凸性信息预先计算并缓存
- `isRect()` 利用分段掩码快速过滤

### 迭代性能

- `SkPathIter` 直接使用跨度，避免虚函数调用
- 数据局部性好，缓存友好

### 适用场景

最适合以下场景：

- 临时路径对象，生命周期短
- 已知几何形状的快速表示
- 需要避免堆分配的性能敏感代码
- 只读访问路径数据

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `src/core/SkPathRawShapes.h/.cpp` | 基于 `SkPathRaw` 的栈上形状实现 |
| `include/core/SkPathIter.h` | 路径迭代器定义 |
| `include/core/SkPathTypes.h` | 路径类型和枚举定义 |
| `src/core/SkPathPriv.h` | 路径私有辅助函数 |
| `src/core/SkPathEnums.h` | 路径枚举（凸性等） |
| `include/core/SkPath.h` | 标准路径类 |
