# VertState

> 源文件: src/core/SkVertState.h, src/core/SkVertState.cpp

## 概述

`VertState` 是 Skia 图形渲染系统中用于顶点绘制的辅助结构体,专门用于迭代和生成三角形顶点索引。它支持多种顶点模式(三角形列表、三角形带、三角形扇),并能处理索引和非索引顶点数据。该结构体通过函数指针机制实现高效的顶点遍历,是 `drawVertices()` API 的核心实现组件。

## 架构位置

`VertState` 位于 Skia 核心层 (`src/core`) 的几何图形渲染子系统中,专门服务于顶点绘制功能:

- **上游**: `SkCanvas::drawVertices()`, `SkVertices` 对象
- **下游**: GPU 渲染管线、软件光栅化器
- **用途**: 将高级顶点描述转换为底层可用的三角形索引序列

## 主要类与结构体

### VertState

**继承关系**:
- 无继承,纯数据结构体

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `f0`, `f1`, `f2` | `int` | 当前三角形的三个顶点索引(输出) |
| `fCount` | `int` | 顶点总数或索引总数 |
| `fCurrIndex` | `int` | 当前迭代位置 |
| `fIndices` | `const uint16_t*` | 可选的索引数组指针 |

## 公共 API 函数

### 构造函数

```cpp
VertState(int vCount, const uint16_t indices[], int indexCount)
```

**参数说明**:
- `vCount`: 顶点数量
- `indices`: 索引数组(如果为 `nullptr` 则使用直接顶点)
- `indexCount`: 索引数量

### 核心方法

| 函数签名 | 功能描述 |
|---------|---------|
| `Proc chooseProc(SkVertices::VertexMode mode)` | 根据顶点模式选择合适的迭代函数 |

### 函数指针类型

```cpp
typedef bool (*Proc)(VertState*);
```

返回 `true` 表示成功生成一个三角形,返回 `false` 表示迭代结束。

## 内部实现细节

### 顶点模式支持

`VertState` 支持三种顶点模式,每种模式有索引和非索引两个变体:

#### 1. Triangles (三角形列表)

```cpp
bool VertState::Triangles(VertState* state) {
    int index = state->fCurrIndex;
    if (index + 3 > state->fCount) {
        return false;
    }
    state->f0 = index + 0;
    state->f1 = index + 1;
    state->f2 = index + 2;
    state->fCurrIndex = index + 3;
    return true;
}
```

- 每次消耗 3 个顶点/索引
- 生成独立的三角形

#### 2. TriangleStrip (三角形带)

```cpp
bool VertState::TriangleStrip(VertState* state) {
    int index = state->fCurrIndex;
    if (index + 3 > state->fCount) {
        return false;
    }
    state->f2 = index + 2;
    if (index & 1) {
        state->f0 = index + 1;
        state->f1 = index + 0;
    } else {
        state->f0 = index + 0;
        state->f1 = index + 1;
    }
    state->fCurrIndex = index + 1;
    return true;
}
```

- 每次前进 1 个顶点
- 奇偶三角形的顶点顺序不同,保证一致的缠绕方向
- 共享两个顶点,减少顶点数据

#### 3. TriangleFan (三角形扇)

```cpp
bool VertState::TriangleFan(VertState* state) {
    int index = state->fCurrIndex;
    if (index + 3 > state->fCount) {
        return false;
    }
    state->f0 = 0;  // 始终使用第一个顶点
    state->f1 = index + 1;
    state->f2 = index + 2;
    state->fCurrIndex = index + 1;
    return true;
}
```

- 所有三角形共享第一个顶点
- 每次前进 1 个顶点
- 适合绘制扇形、圆形等图形

### 索引变体

每种模式都有对应的索引版本(后缀 `X`),例如 `TrianglesX`:

```cpp
bool VertState::TrianglesX(VertState* state) {
    const uint16_t* indices = state->fIndices;
    int index = state->fCurrIndex;
    if (index + 3 > state->fCount) {
        return false;
    }
    state->f0 = indices[index + 0];
    state->f1 = indices[index + 1];
    state->f2 = indices[index + 2];
    state->fCurrIndex = index + 3;
    return true;
}
```

- 通过索引数组间接访问顶点
- 允许顶点重用,减少数据传输

### 函数选择逻辑

```cpp
VertState::Proc VertState::chooseProc(SkVertices::VertexMode mode) {
    switch (mode) {
        case SkVertices::kTriangles_VertexMode:
            return fIndices ? TrianglesX : Triangles;
        case SkVertices::kTriangleStrip_VertexMode:
            return fIndices ? TriangleStripX : TriangleStrip;
        case SkVertices::kTriangleFan_VertexMode:
            return fIndices ? TriangleFanX : TriangleFan;
        default:
            return nullptr;
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkVertices` | 定义顶点模式枚举 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| `SkCanvas::onDrawVertices()` | 使用 `VertState` 迭代顶点 |
| `SkDevice` 实现 | 处理顶点绘制命令 |
| GPU 后端 | 转换为 GPU 绘制调用 |

## 设计模式与设计决策

### 设计模式

1. **策略模式**: 使用函数指针实现不同的迭代策略
2. **迭代器模式**: 提供统一的三角形遍历接口

### 设计决策

**为什么使用函数指针而不是虚函数?**
- 结构体而非类,保持轻量级
- 避免虚表开销
- 编译期确定函数指针,便于内联优化

**为什么区分索引和非索引版本?**
- 避免在循环中进行条件判断
- 针对不同情况优化性能
- 减少分支预测失败

**三角形带的顶点顺序处理**

```cpp
if (index & 1) {
    state->f0 = index + 1;
    state->f1 = index + 0;
} else {
    state->f0 = index + 0;
    state->f1 = index + 1;
}
```

- 奇数索引三角形反转前两个顶点
- 保证所有三角形具有一致的缠绕方向
- 对背面剔除和法线计算至关重要

**边界检查**
- 所有迭代函数在生成三角形前检查剩余顶点
- 避免越界访问
- 提供明确的迭代结束条件

## 性能考量

### 优化策略

1. **零虚函数开销**: 使用函数指针而非虚函数
2. **分支优化**: 预先选择函数,避免循环内判断
3. **紧凑内存布局**: 结构体成员紧密排列
4. **内联友好**: 简单函数易于编译器内联

### 使用模式

```cpp
VertState state(vertexCount, indices, indexCount);
VertState::Proc proc = state.chooseProc(mode);
while (proc(&state)) {
    // 使用 state.f0, state.f1, state.f2 绘制三角形
    drawTriangle(vertices[state.f0],
                 vertices[state.f1],
                 vertices[state.f2]);
}
```

### 性能特性

- **Triangles**: 最简单,每次固定步进 3
- **TriangleStrip**: 最高效,顶点复用率高
- **TriangleFan**: 中等效率,适合特定几何形状

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkVertices.h` | 定义顶点模式和顶点数据结构 |
| `include/core/SkCanvas.h` | 提供 `drawVertices()` API |
| `src/core/SkDevice.cpp` | 使用 `VertState` 实现顶点绘制 |
| `src/gpu/ganesh/GrDrawVerticesOp.cpp` | GPU 路径的顶点处理 |
