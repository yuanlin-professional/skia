# SkPathOpsSimplify - 路径简化

> 源文件:
> - `src/pathops/SkPathOpsSimplify.cpp`

## 概述

`SkPathOpsSimplify.cpp` 实现了 Skia 的路径简化（Simplify）操作。路径简化将一条可能包含自相交的路径转换为等价的非自相交路径，使用 evenodd 填充规则。这是路径操作子系统的核心入口点之一。

简化算法的主要步骤包括：构建边列表、计算交点、处理重合、然后通过"桥接"算法沿 winding 或 xor 规则遍历边来构建最终的轮廓。

## 架构位置

```
include/pathops/SkPathOps.h       // 公共 API：Simplify()
  |
  v
src/pathops/SkPathOpsSimplify.cpp  // 本文件
  |
  +-- SkOpEdgeBuilder             // 构建边列表
  +-- SkAddIntersections          // 计算交点
  +-- SkOpCoincidence             // 处理重合
  +-- SkPathOpsCommon             // 通用操作
  +-- SkPathWriter                // 输出路径
```

## 主要类与结构体

### `Trivializer` (内部类)

嵌套在 `path_is_trivial()` 中的辅助类，用于检测路径是否退化。

| 成员 | 说明 |
|------|------|
| `prevPt` | 前一个点 |
| `prevVec` | 前一个向量 |
| `addTrivialContourPoint()` | 检查新点是否与已有点共线 |

## 公共 API 函数

### `Simplify()`

```cpp
std::optional<SkPath> Simplify(const SkPath& path);
```

公共入口函数。调用 `SimplifyDebug()` 并可选地进行验证。

### `SimplifyDebug()`

```cpp
std::optional<SkPath> SimplifyDebug(const SkPath& path
    SkDEBUGPARAMS(bool skipAssert)
    SkDEBUGPARAMS(const char* testName));
```

带调试参数的核心实现。

## 内部实现细节

### 简化算法流程

1. **凸路径快速路径**：若路径已凸，检查是否退化（`path_is_trivial`），退化则返回空路径，否则直接复制
2. **填充规则转换**：结果使用 evenodd 填充规则（inverse 类型转为 `kInverseEvenOdd`）
3. **构建边列表**：使用 `SkOpEdgeBuilder` 将路径转换为段列表
4. **排序轮廓**：`SortContourList()` 对轮廓进行排序
5. **计算交点**：对每对轮廓调用 `AddIntersectTs()` 计算所有交点
6. **处理重合**：`HandleCoincidence()` 处理重合边
7. **桥接遍历**：根据填充规则选择 `bridgeWinding()` 或 `bridgeXor()` 构建输出路径
8. **组装**：`wrapper.assemble()` 处理未能解析的边

### `bridgeWinding()` - Winding 规则桥接

```cpp
static bool bridgeWinding(SkOpContourHead* contourList, SkPathWriter* writer);
```

1. 查找可排序的起始 span（`FindSortableTop`）
2. 检查当前段是否 activeWinding
3. 若活跃：沿着边追踪（`findNextWinding`），将曲线添加到输出路径
4. 若非活跃：标记为完成（`markAndChaseDone`），将末端加入 chase 列表
5. 从 chase 列表中取下一个段继续处理

### `bridgeXor()` - XOR 规则桥接

```cpp
static bool bridgeXor(SkOpContourHead* contourList, SkPathWriter* writer);
```

类似 winding 版本但更简单：
- 查找未完成的 span（`FindUndone`）
- 沿边追踪（`findNextXor`）
- 包含安全网计数器（1,000,000 次迭代）防止无限循环

### `path_is_trivial()` - 退化路径检测

检测路径是否为"退化"的：
- 所有点共线或重合
- 使用叉积检测共线性（与 `SkPath::Convexicator` 保持一致）
- 处理所有曲线类型（line、quad、conic、cubic）

## 依赖关系

- `SkOpEdgeBuilder` - 从路径构建操作边
- `SkAddIntersections` - 计算段间交点
- `SkOpCoincidence` - 重合边处理
- `SkPathOpsCommon` - `SortContourList()`, `HandleCoincidence()`, `FindSortableTop()` 等
- `SkPathWriter` - 构建输出路径
- `SkOpContour` / `SkOpSegment` / `SkOpSpan` - 操作数据结构
- `SkSTArenaAlloc` - 栈上 arena 分配器（4096 字节）

## 设计模式与设计决策

1. **两阶段处理**：先计算所有交点，再遍历构建输出（避免边计算边修改）
2. **Chase 列表**：使用 chase 列表追踪待处理的分支点，实现深度优先遍历
3. **安全网**：XOR 桥接包含迭代计数器防止无限循环
4. **凸路径优化**：凸路径直接跳过交点计算，仅检查退化性
5. **Arena 分配**：使用栈上 4096 字节 arena 减少堆分配

## 性能考量

1. **凸路径快速返回**：`isConvex()` 检查避免对简单路径进行昂贵的交点计算
2. **退化检测**：`path_is_trivial()` 使用简单的叉积检测，开销低
3. **Arena 分配器**：使用 `SkSTArenaAlloc<4096>` 减少路径操作中的堆分配
4. **XOR 安全网**：1,000,000 次迭代限制防止病态输入导致的无限循环
5. **debug 模式验证**：验证操作仅在 debug 构建中执行

### bridgeWinding 与 bridgeXor 的区别

| 特性 | bridgeWinding | bridgeXor |
|------|-------------|-----------|
| 起始查找 | `FindSortableTop` | `FindUndone` |
| 下一段查找 | `findNextWinding` | `findNextXor` |
| Chase 列表 | 是 | 否 |
| 安全网 | 无 | 1,000,000 次迭代 |
| 非活跃段处理 | `markAndChaseDone` + chase | 无 |
| 用于 | winding 填充规则 | evenodd/xor 填充规则 |

### 全局状态对象

`SkOpGlobalState` 管理路径操作的全局状态：
- 重合检测器（`SkOpCoincidence`）
- Arena 分配器
- 调试参数（跳过断言、测试名称）
- 调试阶段追踪（`SkOpPhase`）

### 错误处理

简化操作在以下情况返回空 `optional`（失败）：
- `SkOpEdgeBuilder::finish()` 失败
- `HandleCoincidence()` 失败
- `bridgeWinding()` / `bridgeXor()` 返回 false
- `addCurveTo()` 失败

成功但结果为空路径的情况：
- `SortContourList()` 返回 false（无有效轮廓）
- 凸路径的退化检测通过

## 相关文件

- `include/pathops/SkPathOps.h` - 公共 API
- `src/pathops/SkOpEdgeBuilder.h` - 边构建器
- `src/pathops/SkAddIntersections.h` - 交点计算
- `src/pathops/SkOpCoincidence.h` - 重合处理
- `src/pathops/SkPathWriter.h` - 路径输出
- `src/pathops/SkPathOpsCommon.h` - 通用工具函数
- `src/pathops/SkOpContour.h` - 轮廓数据结构
- `src/pathops/SkOpSegment.h` - 段数据结构
