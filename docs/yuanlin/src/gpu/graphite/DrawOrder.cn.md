# DrawOrder

> 源文件
> - src/gpu/graphite/DrawOrder.h

## 概述

`DrawOrder.h` 定义了 Graphite 用于重新排序绘制命令的三个独立序列系统，在保持 Skia API 画家顺序语义的同时，最大化绘制重排序的灵活性。该文件包含三个单调值类型和一个聚合类，共同实现了复杂的绘制顺序管理。

核心思想：虽然绘制必须尊重原始的画家顺序（后绘制覆盖先绘制），但通过深度测试、透明度分析和模板缓冲区，许多绘制可以安全地重新排序，从而减少状态切换和提高批处理效率。

## 主要类与结构体

### MonotonicValue 模板

强制单调递增序列的模板类：

```cpp
template<typename Sequence>
class MonotonicValue {
public:
    static constexpr MonotonicValue First();
    static constexpr MonotonicValue Last();

    MonotonicValue next() const;
    uint16_t bits() const;

    // 比较操作符
    bool operator<(MonotonicValue o) const;
    bool operator==(MonotonicValue o) const;
    // ...
};
```

模板参数 `Sequence` 用于类型安全，防止不同序列之间的混淆。

### CompressedPaintersOrder

压缩的画家顺序，允许多个原始绘制共享同一顺序：

```cpp
struct CompressedPaintersOrderSequence {};
using CompressedPaintersOrder = MonotonicValue<CompressedPaintersOrderSequence>;
```

**用途**：具有相同 `CompressedPaintersOrder` 的绘制可以以任意顺序执行（如通过深度测试或边界管理器确定）。

### DisjointStencilIndex

不相交模板索引，指定一组不重叠的绘制：

```cpp
struct DisjointStencilIndexSequence {};
using DisjointStencilIndex = MonotonicValue<DisjointStencilIndexSequence>;
```

**用途**：相同 `CompressedPaintersOrder` 和 `DisjointStencilIndex` 的绘制可以交错其多通道渲染子步骤（如模板-覆盖）而不影响结果。

### PaintersDepth

画家深度值，存储到深度附件中：

```cpp
struct PaintersDepthSequence {};
using PaintersDepth = MonotonicValue<PaintersDepthSequence>;
```

**用途**：使用 GREATER 深度测试，允许不依赖前一颜色的绘制大幅重新排序。

### DrawOrder 类

聚合三个序列的类：

```cpp
class DrawOrder {
public:
    static constexpr PaintersDepth kClearDepth;
    static constexpr CompressedPaintersOrder kNoIntersection;
    static constexpr DisjointStencilIndex kUnassigned;

    explicit DrawOrder(PaintersDepth originalOrder);
    DrawOrder(PaintersDepth originalOrder, CompressedPaintersOrder compressedOrder);

    CompressedPaintersOrder paintOrder() const;
    DisjointStencilIndex stencilIndex() const;
    PaintersDepth depth() const;

    float depthAsFloat() const;  // 归一化并翻转为 [1.0, 0.0]

    // 修改方法
    DrawOrder& reverseDepthAsStencil();
    DrawOrder& dependsOnPaintersOrder(CompressedPaintersOrder prevDraw);
    DrawOrder& dependsOnStencil(DisjointStencilIndex disjointSet);
};
```

## 公共 API 函数

### 构造函数

```cpp
explicit DrawOrder(PaintersDepth originalOrder);
```

创建具有给定原始深度的绘制顺序，压缩顺序初始化为 `kNoIntersection`，模板索引为 `kUnassigned`。

### dependsOnPaintersOrder

```cpp
DrawOrder& dependsOnPaintersOrder(CompressedPaintersOrder prevDraw);
```

标记该绘制依赖于先前的绘制，更新压缩顺序为 `prevDraw.next()` 或更大。用于透明绘制或需要混合的绘制。

### dependsOnStencil

```cpp
DrawOrder& dependsOnStencil(DisjointStencilIndex disjointSet);
```

分配模板索引，表示该绘制使用模板缓冲区。

### reverseDepthAsStencil

```cpp
DrawOrder& reverseDepthAsStencil();
```

特殊方法：将画家深度编码到模板索引中（递减顺序），用于强制前到后（F2B）顺序。与压缩顺序的后到前（B2F）形成对比。

### depthAsFloat

```cpp
float depthAsFloat() const;
```

将 `PaintersDepth` 转换为浮点深度值，范围 [1.0, 0.0]，适合深度缓冲区（清除值 1.0，使用 LESS/LEQUAL 比较）。

## 内部实现细节

### 三序列系统

**1. PaintersDepth**（原始顺序）：
- 每个绘制的原始画家顺序
- 决定实际执行顺序的基础
- 存储到深度缓冲区

**2. CompressedPaintersOrder**（压缩顺序）：
- 多个绘制可以共享
- 定义执行顺序的主要键
- 允许后到前（B2F）渲染优化

**3. DisjointStencilIndex**（模板索引）：
- 区分不重叠的模板绘制集
- 允许交错多通道绘制的子步骤
- 次要排序键（在压缩顺序之后）

### 排序优先级

实际执行顺序：
1. `CompressedPaintersOrder`（主要）
2. `DisjointStencilIndex`（次要）
3. 其他因素（管线、uniform 等）

虽然 `PaintersDepth` 定义逻辑顺序，但压缩允许大幅重排序。

### 深度测试策略

使用 GREATER 深度测试而非 GEQUAL：
- 避免重叠几何的双重命中（如描边）
- 深度值从 1.0 递减到 0.0

### 模板索引复用

`reverseDepthAsStencil()` 复用模板索引字段：
- 正常：真实的模板集索引
- 反转深度：编码画家深度的递减值
- 用于 F2B 绘制（透明混合等）

## 设计模式与设计决策

### 1. 类型安全的单调序列

`MonotonicValue` 模板通过类型参数防止不同序列混淆：
- 编译时错误检测
- 无运行时开销
- 清晰的语义

### 2. 流式 API

`DrawOrder` 修改方法返回 `*this`：
```cpp
order.dependsOnPaintersOrder(prev).dependsOnStencil(index);
```
提高可读性和简洁性。

### 3. 保留值约定

特殊值用于表示状态：
- `kClearDepth`：清除深度，总是失败测试
- `kNoIntersection`：无依赖
- `kUnassigned`：未使用模板

### 4. 浮点归一化

`depthAsFloat()` 归一化和翻转：
- 适配 GPU 深度缓冲区约定
- 清除值 1.0，绘制值递减
- 支持 LESS 测试（GPU 更常见）

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/DrawParams.h` | 使用 DrawOrder 的绘制参数 |
| `src/gpu/graphite/DrawList.h` | 使用 DrawOrder 排序绘制 |
| `src/gpu/graphite/DrawListLayer.h` | 使用压缩顺序分层 |
| `src/gpu/graphite/BoundsManager.h` | 计算压缩顺序 |
| `src/gpu/graphite/Renderer.h` | 渲染器指定深度模板需求 |
