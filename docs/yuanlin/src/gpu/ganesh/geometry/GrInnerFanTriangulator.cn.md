# GrInnerFanTriangulator

> 源文件: src/gpu/ganesh/geometry/GrInnerFanTriangulator.h

## 概述

`GrInnerFanTriangulator` 是 Ganesh GPU 后端中专门用于路径内部扇形三角化的工具类。它继承自 `GrTriangulator`,专注于生成路径的内部填充三角形(类似于 OpenGL Redbook 中的扇形填充方法)。该类与外部曲线和面包屑三角形(breadcrumb triangles)配合使用,共同实现完整的路径渲染。

核心特性:
- 继承并特化 `GrTriangulator` 的功能
- 生成内部多边形的三角化
- 收集面包屑三角形(用于消除 T 型接缝)
- 保留共线顶点以保证几何拓扑
- 仅在非优化大小模式下可用

## 架构位置

`GrInnerFanTriangulator` 位于 Ganesh 几何层,作为路径三角化器的特化版本:

```
src/gpu/ganesh/
  └── geometry/
      ├── GrTriangulator.h/cpp         # 通用三角化器(基类)
      ├── GrInnerFanTriangulator.h     # 内部扇形三角化器(本模块)
      └── ops/
          └── PathInnerTriangulateOp.cpp # 使用者: 路径内部三角化操作
```

该模块是路径镶嵌渲染管线的关键组件之一。

## 主要类与结构体

### GrInnerFanTriangulator 类

**继承关系**:
```
GrTriangulator (基类)
    └── GrInnerFanTriangulator (派生类)
```

**用途**: 专门用于生成路径内部的三角形填充,配合外部曲线渲染使用。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| (继承自基类) | - | 路径数据、内存分配器、各种控制标志 |

**关键配置**:

构造函数会设置特定的基类标志:

```cpp
GrInnerFanTriangulator(const SkPath& path, SkArenaAlloc* alloc)
        : GrTriangulator(path, alloc) {
    fPreserveCollinearVertices = true;   // 保留共线顶点
    fCollectBreadcrumbTriangles = true;  // 收集面包屑三角形
}
```

### BreadcrumbTriangleList 类型别名

```cpp
using GrTriangulator::BreadcrumbTriangleList;
```

继承自基类的面包屑三角形列表类型,用于存储消除 T 型接缝的辅助三角形。

## 公共 API 函数

### 路径到三角形的完整转换

```cpp
int pathToTriangles(GrEagerVertexAllocator* vertexAlloc,
                    BreadcrumbTriangleList* breadcrumbList,
                    bool* isLinear)
```

将路径一步转换为三角形,并收集面包屑三角形。

**参数**:
- `vertexAlloc`: 顶点分配器,用于写入三角形顶点
- `breadcrumbList`: 输出参数,收集面包屑三角形
- `isLinear`: 输出参数,指示路径是否为线性(无曲线)

**返回值**: 生成的顶点数量

**内部流程**:
```cpp
Poly* polys = this->pathToPolys(breadcrumbList, isLinear);
return this->polysToTriangles(polys, vertexAlloc, breadcrumbList);
```

### 路径到多边形

```cpp
Poly* pathToPolys(BreadcrumbTriangleList* breadcrumbList, bool* isLinear)
```

将路径转换为单调多边形链表,这是三角化的中间表示。

**参数**:
- `breadcrumbList`: 输出参数,收集面包屑三角形
- `isLinear`: 输出参数,指示路径是否为线性

**返回值**: 多边形链表头指针,失败时返回 `nullptr`

**调用基类方法**:
```cpp
auto [ polys, success ] = this->GrTriangulator::pathToPolys(
    0,                     // tolerance (0 表示使用默认值)
    SkRect::MakeEmpty(),   // clipBounds (空矩形表示不裁剪)
    isLinear);
```

### 多边形到三角形

```cpp
int polysToTriangles(Poly* polys,
                     GrEagerVertexAllocator* vertexAlloc,
                     BreadcrumbTriangleList* breadcrumbList) const
```

将多边形链表转换为三角形顶点。

**参数**:
- `polys`: 输入的单调多边形链表
- `vertexAlloc`: 顶点分配器
- `breadcrumbList`: 输出参数,收集面包屑三角形

**返回值**: 生成的顶点数量

## 内部实现细节

### 继承与特化

`GrInnerFanTriangulator` 不添加新的成员变量或重写虚函数,而是通过:

1. **配置基类标志**: 在构造函数中设置特定的行为开关
2. **组合基类方法**: `pathToTriangles()` 将 `pathToPolys()` 和 `polysToTriangles()` 组合
3. **暴露受保护方法**: 公开基类的 `pathToPolys()` 和 `polysToTriangles()`

这是一种轻量级的特化模式,避免了代码重复。

### 保留共线顶点

```cpp
fPreserveCollinearVertices = true;
```

为什么需要保留共线顶点?

- **拓扑完整性**: 内部三角形需要与外部曲线精确对接
- **避免间隙**: 删除共线顶点可能导致边缘不对齐
- **面包屑三角形**: 需要准确的顶点位置来生成覆盖 T 型接缝的三角形

### 面包屑三角形机制

面包屑三角形用于消除内部多边形和外部曲线之间的 T 型接缝:

```
原始边: A ------------- B
               ↓ 在 X 点分裂
分裂后: A ---- X ---- B

面包屑三角形: [A, B, X]  (非常细的三角形)
```

当所有这些三角形与主三角化一起绘制到模板缓冲时,它们的反向共享边会相互抵消,只留下原始多边形的边缘。

### 条件编译

```cpp
#if !defined(SK_ENABLE_OPTIMIZE_SIZE)
// GrInnerFanTriangulator 类定义
#else
// Stub 实现
namespace GrInnerFanTriangulator {
    struct BreadcrumbTriangleList {
        BreadcrumbTriangleList() = delete;
    };
}
#endif
```

在优化大小模式下,该类被桩实现替代,因为内部三角化功能对某些平台不是必需的。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrTriangulator` | 基类,提供核心三角化算法 |
| `SkPath` | 路径数据结构 |
| `SkArenaAlloc` | 内存分配器 |
| `SkRect` | 矩形类型(用于裁剪边界) |
| `GrEagerVertexAllocator` | 顶点缓冲区分配 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `PathInnerTriangulateOp` | 路径内部三角化操作 |
| `GrTessellationPathRenderer` | 镶嵌路径渲染器 |

## 设计模式与设计决策

### 配置继承模式

使用构造函数配置基类行为,而非重写虚函数:

```cpp
GrInnerFanTriangulator(const SkPath& path, SkArenaAlloc* alloc)
        : GrTriangulator(path, alloc) {
    fPreserveCollinearVertices = true;
    fCollectBreadcrumbTriangles = true;
}
```

**优势**:
- 避免虚函数开销
- 代码复用性高
- 行为通过数据驱动而非控制流

### 适配器模式

该类本质上是 `GrTriangulator` 的适配器:
- 提供更高层次的接口(`pathToTriangles`)
- 封装配置细节
- 简化调用者的使用

### 条件编译策略

通过 `SK_ENABLE_OPTIMIZE_SIZE` 宏有条件地编译功能:

**包含时**:
```cpp
#if !defined(SK_ENABLE_OPTIMIZE_SIZE)
class GrInnerFanTriangulator : private GrTriangulator { ... };
#else
namespace GrInnerFanTriangulator { struct BreadcrumbTriangleList { ... }; }
#endif
```

这允许:
- 在嵌入式或移动平台上减小二进制大小
- 保持 API 兼容性(类型名存在,但不可实例化)
- 编译期移除整个三角化管线

### 私有继承

```cpp
class GrInnerFanTriangulator : private GrTriangulator
```

使用私有继承而非公有继承:
- **隐藏实现**: 调用者不能通过多态使用基类接口
- **精确控制**: 显式 `using` 声明暴露 `BreadcrumbTriangleList`
- **避免误用**: 防止外部代码直接调用基类方法

## 性能考量

### 内存分配策略

使用 `SkArenaAlloc` 进行内存分配:

```cpp
GrInnerFanTriangulator(const SkPath& path, SkArenaAlloc* alloc)
```

优势:
- 快速的批量分配(无单独的 `new`/`delete` 开销)
- 生命周期自动管理(随分配器销毁)
- 缓存友好(连续内存布局)

### 面包屑三角形开销

收集面包屑三角形有额外开销:
- 每次边分裂增加链表节点
- 额外的三角形需要绘制

但换来的是:
- 无需昂贵的边缘重合检测
- 简化的模板缓冲区处理
- 精确的路径覆盖

实测表明,对于复杂路径(数千条边),面包屑三角形的数量通常少于原始三角形的 10%。

### 保留共线顶点的代价

`fPreserveCollinearVertices = true` 阻止了简化优化:
- 更多的顶点需要处理
- 更多的三角形生成

但这是内部填充的必需特性,而外部曲线渲染不需要这个约束,因此分离为独立的类是合理的。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/geometry/GrTriangulator.h` | 基类 | 通用路径三角化算法 |
| `src/gpu/ganesh/ops/PathInnerTriangulateOp.cpp` | 被使用 | 使用内部三角化的操作 |
| `src/gpu/ganesh/GrEagerVertexAllocator.h` | 依赖 | 顶点内存分配 |
| `src/base/SkArenaAlloc.h` | 依赖 | 内存池分配器 |
| `include/core/SkPath.h` | 依赖 | 路径数据结构 |
