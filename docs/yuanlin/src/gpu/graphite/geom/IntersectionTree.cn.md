# IntersectionTree -- 矩形相交检测树

> 源文件:
> - `src/gpu/graphite/geom/IntersectionTree.h`
> - `src/gpu/graphite/geom/IntersectionTree.cpp`

## 概述

IntersectionTree 是一个维护不重叠矩形集合的空间数据结构。它提供高效的矩形插入操作:如果新矩形与集合中任何已有矩形相交则返回 false,否则将其加入集合。该数据结构用于 Graphite 的绘制命令排序和批处理优化,判断绘制操作是否可以安全重排。

## 架构位置

```
DrawPass / DrawList (绘制排序)
  -> IntersectionTree  <-- 本模块
       -> BSP 树 (TreeNode<kX/kY>)
       -> 叶节点 (LeafNode, SIMD 加速暴力搜索)
```

该类是 Graphite 渲染器前端的几何工具组件,用于空间查询优化。

## 主要类与结构体

### IntersectionTree (公共接口)

```cpp
class IntersectionTree {
    enum class SplitType : bool { kX, kY };
    bool add(Rect rect);
private:
    SkArenaAlloc fArena;
    Node* fRoot;
};
```

### Node (抽象基类)

```cpp
class Node {
    virtual bool intersects(Rect) = 0;
    virtual Node* addNonIntersecting(Rect, SkArenaAlloc*) = 0;
};
```

### TreeNode<SplitType> (BSP 节点)

模板化的 BSP 分割节点,按 X 或 Y 轴将空间一分为二:
- `fSplitCoord`: 分割坐标
- `fLo` / `fHi`: 分割线两侧的子节点
- 跨越分割线的矩形同时出现在两侧

### LeafNode (叶节点)

存储最多 64 个矩形的暴力搜索节点:
- 使用 SoA (Structure of Arrays) 布局: `fLefts[]`, `fTops[]`, `fNegRights[]`, `fNegBots[]`
- SIMD 4 路并行相交测试
- 满载时自动分裂为 TreeNode

## 公共 API 函数

### add

```cpp
bool add(Rect rect);
```
- 空矩形直接返回 true（不修改树）
- 若与已有矩形相交返回 false
- 否则将矩形加入集合并返回 true

## 内部实现细节

### SIMD 相交测试

LeafNode 使用"补矩形"技巧进行 SIMD 加速的批量相交测试:

```cpp
auto comp = Rect::ComplementRect(rect).fVals;
for (int i = 0; i < fNumRects; i += 4) {
    auto l = skvx::float4::Load(fLefts + i);
    // ... 4 路并行比较
    if (any((l < comp[0]) & (t < comp[1]) & (nr < comp[2]) & (nb < comp[3])))
        return true;
}
```

每次比较 4 个矩形,利用 SSE/NEON 指令集加速。

### 自适应分裂

当叶节点的矩形数量达到 `kMaxRectsInList` (64) 时,自动分裂:

1. **选择分裂轴**: 计算可分裂区域的宽高 (`maxLeft - minRight`, `maxTop - minBot`)，选择较大维度
2. **选择分裂坐标**: 使用矩形坐标的几何中点,限制在可分裂范围内
3. **分配矩形**: 跨越分裂线的矩形同时放入两侧,保证两侧都严格小于原始数量
4. **复用节点**: 当前叶节点成为 "lo" 子节点,新分配一个 "hi" 叶节点

### 内存管理

使用 `SkArenaAlloc` 进行竞技场分配:
- 初始大小: `kLeafNodeSize + kTreeNodeSize + kPadSize*2`
- 所有节点从同一竞技场分配,销毁 IntersectionTree 时一次性释放
- 避免逐节点 new/delete 的开销

### 安全溢出处理

叶节点数组用 `+infinity` 初始化,这确保:
- 超出 `fNumRects` 范围的比较自动失败（infinity 不小于任何有限值）
- 无需在循环中检查边界条件

## 依赖关系

- `src/gpu/graphite/geom/Rect.h` -- SIMD 优化的矩形类
- `src/base/SkArenaAlloc.h` -- 竞技场内存分配器
- `src/base/SkVx.h` -- SIMD 向量运算

## 设计模式与设计决策

1. **自适应混合数据结构**: 叶节点用暴力搜索处理小规模数据,节点数增长时自动退化为 BSP 树,平衡了小规模高效和大规模可扩展的需求。

2. **SoA 布局**: 相比 AoS (Array of Structures),SoA 布局使 SIMD 加载更高效——每次加载连续的 4 个同类坐标值。

3. **补矩形技巧**: 将相交测试转化为四个同方向的比较,使得 SIMD 并行化更自然。

4. **竞技场分配**: 所有节点共享同一竞技场,避免小对象堆分配碎片化,且析构时一次性释放。

## 性能考量

- 64 个矩形的暴力搜索经 SIMD 优化后约等于 16 次 SIMD 比较操作,在实测中这是最优分裂阈值。
- BSP 分裂保证两侧严格小于原数组,避免退化。
- 分裂坐标选择几何中点并限制在可分裂范围内,趋向均匀分割。
- `static_assert` 验证节点大小常量与实际大小匹配,确保竞技场预分配正确。

## 相关文件

- `src/gpu/graphite/geom/Rect.h` -- Graphite 矩形类（含 SIMD 支持）
- `src/gpu/graphite/DrawPass.h` -- 使用 IntersectionTree 的绘制通道
- `src/base/SkArenaAlloc.h` -- 竞技场分配器
