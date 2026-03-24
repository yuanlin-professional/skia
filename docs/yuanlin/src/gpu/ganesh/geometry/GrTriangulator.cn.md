# GrTriangulator

> 源文件
> - src/gpu/ganesh/geometry/GrTriangulator.h
> - src/gpu/ganesh/geometry/GrTriangulator.cpp

## 概述

`GrTriangulator` 是 Skia GPU 后端的通用路径三角化器，使用扫描线算法将任意复杂路径（包括自相交、多轮廓、填充规则）转换为三角形网格。支持 Even-Odd 和 Winding 填充规则，处理退化情况（重合点、零面积三角形），并提供高效的内存分配策略。该类是 GPU 路径渲染的基础组件，生成的三角形可直接提交到 GPU 光栅化器。

## 架构位置

- **模块层级**：`src/gpu/ganesh/geometry/` - Ganesh 几何处理
- **作用**：路径到三角形网格的转换
- **使用者**：AA 三角化器、软件路径渲染器、填充操作
- **算法**：改进的扫描线三角化算法

## 主要类与结构体

### GrTriangulator

**核心数据结构**：
- `Vertex` - 顶点（位置、连通性）
- `Edge` - 边（连接两个顶点）
- `Poly` - 多边形链表（winding 计数）
- `MonotonePoly` - 单调多边形（可直接三角化）

**主要方法**：
```cpp
int PathToTriangles(const SkPath&, SkScalar tolerance, const SkRect& clipBounds,
                    GrEagerVertexAllocator*, bool* isLinear);
```

## 内部实现细节

### 扫描线算法

**步骤**：
1. **构建顶点列表**：提取路径控制点，线性化曲线
2. **构建边列表**：连接顶点形成边
3. **排序顶点**：Y 坐标优先，X 坐标次之
4. **扫描线扫描**：
   - 维护活跃边列表（AEL）
   - 计算边的交点
   - 合并/分裂多边形
5. **单调化**：分解为 Y 单调多边形
6. **三角化**：扇形三角化单调多边形

### 填充规则

**Even-Odd**：
- 奇数 winding：内部
- 偶数 winding：外部

**Winding**：
- winding != 0：内部
- winding == 0：外部

### 自相交处理

**边交点计算**：
- 检测边的几何交点
- 分裂相交边
- 更新拓扑连接

**退化处理**：
- 重合顶点：合并
- 零长度边：移除
- 零面积三角形：跳过

### 内存管理

使用 `SkArenaAlloc` 快速分配顶点、边、多边形对象，避免频繁堆分配。

## 设计模式与设计决策

### 扫描线算法

经典计算几何算法，时间复杂度 O((n + k) log n)，n 为顶点数，k 为交点数。

### 单调化策略

分解为 Y 单调多边形简化三角化，O(n) 时间完成。

### 拓扑修复

动态维护顶点和边的连通性，处理复杂自相交。

## 性能考量

### Arena 分配

批量预分配内存，减少分配器调用，提高缓存局部性。

### 交点惰性计算

仅在需要时计算交点，避免不必要的几何计算。

### 单调多边形优化

扇形三角化单调多边形，O(n) 复杂度，无需耳切法。

## 相关文件

- `src/gpu/ganesh/geometry/GrAATriangulator.h/cpp` - AA 扩展
- `src/gpu/ganesh/geometry/GrPathUtils.h` - 路径工具
- `src/gpu/ganesh/GrEagerVertexAllocator.h` - 顶点分配器
