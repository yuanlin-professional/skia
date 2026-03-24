# MiddleOutPolygonTriangulator - 中间外展多边形三角化

> 源文件: `src/gpu/tessellate/MiddleOutPolygonTriangulator.h`

## 概述

MiddleOutPolygonTriangulator 是 Skia GPU 细分系统中的多边形三角化器，实现了"中间外展"（middle-out）三角化算法。该算法将多边形分割为三角形时，优先生成覆盖面积较大的三角形，从而显著减少光栅化器（rasterizer）的工作量。

与线性三角形条带或扇形不同，middle-out 算法递归地选择中间点构建三角形，然后在两侧递归。这种策略生成的三角形在屏幕空间中分布更均匀，减少了光栅化器的过度绘制。本实现使用 O(log N) 栈替代递归，支持流式输入（不需要预先知道所有顶点）。

## 架构位置

```
Skia GPU 曲线细分
  -> PatchWriter (补丁写入器)
    -> MiddleOutPolygonTriangulator (内扇三角化)
      -> 切分曲线时填充空隙
  -> PathMiddleOutFanIter (路径扇形迭代)
    -> MiddleOutPolygonTriangulator (路径内扇)
```

MiddleOutPolygonTriangulator 被 PatchWriter（通过 `AddTrianglesWhenChopping` 特性）和 PathMiddleOutFanIter 使用。

## 主要类与结构体

### `MiddleOutPolygonTriangulator`
- **职责**: 流式接收多边形顶点，使用 O(log N) 栈生成 middle-out 三角化
- **核心思想**: 概念上是递归的二分三角化，但通过栈操作实现非递归版本

### `StackVertex`（内部结构体）
- `fPoint`: 顶点坐标
- `fVertexIdxDelta`: 距离栈中前一顶点的原始多边形索引差。栈底元素的 delta 始终为 0。

### `PoppedTriangleStack`（RAII 辅助类）
- **职责**: 在遍历弹出的三角形后，自动执行栈更新操作
- **使用模式**: 通过 range-for 遍历三角形，析构时更新栈
- **Iter**: 反向遍历栈中待弹出的顶点，每次产生一个三角形 `(prev, current, lastPoint)`

### `PathMiddleOutFanIter`（路径扇形迭代器）
- **职责**: 将 SkPath 的内扇顶点送入 MiddleOutPolygonTriangulator
- **使用模式**: `while (!it.done()) { for (auto [p0,p1,p2] : it.nextStack()) {...} }`

## 公共 API 函数

### MiddleOutPolygonTriangulator
| 函数 | 说明 |
|------|------|
| `MiddleOutPolygonTriangulator(maxPushVertexCalls, startPoint)` | 构造，预分配 log2(max)+1 深度的栈 |
| `pushVertex(SkPoint)` | 推入顶点，返回可迭代的弹出三角形栈 |
| `closeAndMove(SkPoint)` | 关闭当前多边形并重置到新起点 |
| `close()` | 关闭当前多边形（回到原起点） |

### PathMiddleOutFanIter
| 函数 | 说明 |
|------|------|
| `PathMiddleOutFanIter(const SkPath&)` | 从路径构造 |
| `done()` | 是否迭代完成 |
| `nextStack()` | 返回下一批待输出的三角形栈 |

## 内部实现细节

### Middle-Out 算法原理
概念上的递归算法：
```
emit_middle_out(start, end):
  middle = start + nextPow2(end - start) / 2
  recurse(start, middle)
  emit(vertices[start], vertices[middle], vertices[end-1])
  recurse(middle, end)
```
对于 9 个顶点的多边形，三角化顺序为：
```
[0,1,2], [2,3,4], [4,5,6], [6,7,8]  // delta=1
[0,2,4], [4,6,8]                      // delta=2
[0,4,8]                                // delta=4
```

### 栈操作实现
`pushVertex(pt)` 的核心逻辑：
1. 从栈顶开始，查找连续 `fVertexIdxDelta` 相等的顶点（它们形成待弹出的三角形序列）
2. 这些顶点对应递归算法中"同一深度"的三角形
3. 弹出后推入新顶点，其 delta 为弹出顶点 delta 之和

### PoppedTriangleStack 的 RAII 模式
`pushVertex` 返回 `PoppedTriangleStack` 对象，它持有：
- 当前栈顶 `fMiddleOut->fTop`（弹出的起始位置）
- 终止位置 `fEnd`
- 新栈顶信息 `fNewTopVertex` 和 `fNewTopValue`

遍历时从 `fTop` 到 `fEnd` 反向迭代，每步产生三角形 `(fVertex[-1].fPoint, fVertex[0].fPoint, fLastPoint)`。析构函数负责实际更新 `fTop` 和写入新顶点。

### closeAndMove 的处理
关闭多边形时不再追求纯粹的 middle-out 拓扑，而是直接生成剩余所有三角形（因为此时必须结束）。`endVertex` 限制为 `min(fTop, fVertexStack+1)` 确保至少保留起始点。

### 栈预分配
构造函数计算最大栈深度为 `SkNextLog2(maxPushVertexCalls) + 1`。如果超过预分配量（`kStackPreallocCount = 32`），则动态分配。32 的预分配量足以处理超过 20 亿个顶点的多边形。

### PathMiddleOutFanIter 的路径适配
将路径的各种动词映射为扇形顶点：
- `kMove`: 调用 `closeAndMove(pts[0])`
- `kLine/kQuad/kConic/kCubic`: 取最后一个点作为扇形顶点
- `kClose`: 调用 `close()`

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `include/core/SkPath.h` | SkPath 路径数据 |
| `include/core/SkPoint.h` | SkPoint 点类型 |
| `src/core/SkPathPriv.h` | 路径内部迭代 |
| `src/base/SkMathPriv.h` | SkNextLog2, SkNextPow2 |
| `include/private/base/SkTemplates.h` | AutoSTMalloc 栈预分配 |

## 设计模式与设计决策

1. **RAII 延迟更新**: `PoppedTriangleStack` 使用 RAII 模式，确保三角形在被消费后才更新内部栈。这允许调用者使用 range-for 语法自然遍历，同时保持状态一致性。

2. **流式处理**: 不需要预先知道所有顶点，每次 `pushVertex` 可能产生 0 到多个三角形。这使得三角化可以与路径解析同步进行。

3. **O(log N) 空间**: 栈深度仅为 O(log N)，远小于存储所有顶点的 O(N) 空间。

4. **[[nodiscard]] 标注**: `pushVertex`、`closeAndMove` 和 `close` 返回的 `PoppedTriangleStack` 标记为 `[[nodiscard]]`，因为忽略返回值会跳过栈更新导致状态损坏。

5. **对称的路径适配器**: `PathMiddleOutFanIter` 提供了将 SkPath 直接送入三角化器的便捷接口，隐藏了动词到顶点的映射细节。

## 性能考量

1. **光栅化友好**: Middle-out 三角化生成面积较均匀的三角形，减少了 GPU 光栅化器的过度绘制。线性扇形可能生成极其狭长的三角形，导致大量冗余的像素着色。

2. **O(log N) 每次操作**: `pushVertex` 的均摊时间复杂度为 O(1)，最坏情况为 O(log N)（当触发连续弹出时）。

3. **预分配优化**: 使用 `AutoSTMalloc` 预分配 32 个栈条目在栈上（128 字节），避免小多边形的堆分配。

4. **移动语义**: `PoppedTriangleStack` 支持移动构造，通过将源对象的 `fMiddleOut` 设为 nullptr 来防止重复栈更新。

5. **内存局部性**: 栈中的 `StackVertex` 结构体紧凑（8 字节 SkPoint + 4 字节 delta），对缓存友好。

## 相关文件

- `src/gpu/tessellate/PatchWriter.h` - 使用三角化器填充曲线切分空隙
- `src/gpu/tessellate/MidpointContourParser.h` - 轮廓中点计算（提供扇形中心）
- `src/gpu/tessellate/Tessellation.h` - 细分常量
- `src/base/SkMathPriv.h` - SkNextLog2 / SkNextPow2 数学工具
- `src/gpu/graphite/render/MiddleOutFanRenderStep.cpp` - Graphite 扇形渲染步骤
