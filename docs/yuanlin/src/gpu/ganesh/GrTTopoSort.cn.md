# GrTTopoSort

> 源文件: src/gpu/ganesh/GrTTopoSort.h

## 概述

`GrTTopoSort` 是一个模板化的拓扑排序（topological sort）工具，用于对有向无环图（DAG）中的节点进行排序。在 Ganesh GPU 后端中，它主要用于对渲染任务（`GrRenderTask`）进行依赖关系排序，确保渲染任务按正确的顺序执行（依赖的任务先执行，被依赖的任务后执行）。

该模板提供了泛型的拓扑排序实现，通过 Traits 模式支持任意类型的节点。它使用深度优先搜索（DFS）算法实现，并在检测到循环依赖时返回失败。排序结果直接修改输入数组，将节点重排为拓扑顺序。

## 架构位置

`GrTTopoSort` 位于 Ganesh GPU 后端的图算法工具层：

- **主要应用**: `GrDrawingManager` 对 `GrRenderTask` DAG 进行排序
- **算法类型**: 图算法（DFS-based topological sort）
- **模板设计**: 泛型算法，可用于任意符合 Traits 的类型
- **依赖检测**: 检测循环依赖并报告错误
- **原地排序**: 直接修改输入数组，节省内存

该工具是 Ganesh 任务调度系统的核心组件，确保渲染操作的正确顺序。

## 主要类与结构体

### GrTTopoSort 函数模板

这是一个独立的模板函数，不属于任何类：

```cpp
template <typename T, typename Traits = T>
bool GrTTopoSort(SkSpan<sk_sp<T>> graph, uint32_t offset = 0)
```

**模板参数:**
- `T`: 节点类型（如 `GrRenderTask`）
- `Traits`: Traits 类，提供节点操作接口（默认为 `T` 自身）

**参数:**
- `graph`: 节点数组（`SkSpan<sk_sp<T>>`）
- `offset`: 偏移量，用于局部排序时记录全局索引

**返回值:**
- `true`: 排序成功（无循环）
- `false`: 存在循环依赖

### Traits 接口要求

任何用于 `GrTTopoSort` 的类型必须提供（通过类本身或 Traits 类）：

**输出相关:**
```cpp
static void Output(T* t, uint32_t index);  // 标记节点已输出并记录索引
static bool WasOutput(const T* t);         // 检查节点是否已输出
static uint32_t GetIndex(const T* t);      // 获取节点的输出索引
```

**临时标记:**
```cpp
static void SetTempMark(T* t);             // 设置临时标记（DFS 访问中）
static void ResetTempMark(T* t);           // 清除临时标记
static bool IsTempMarked(const T* t);      // 检查是否有临时标记
```

**依赖关系:**
```cpp
static int NumDependencies(const T* t);    // 返回依赖数量
static T* Dependency(T* t, int index);     // 返回第 index 个依赖节点
```

### 辅助函数

#### GrTTopoSort_Visit
```cpp
template <typename T, typename Traits = T>
bool GrTTopoSort_Visit(T* node, uint32_t* counter)
```

递归访问节点的核心函数：
- 检测循环（临时标记）
- 递归访问依赖
- 标记节点为已输出

#### GrTTopoSort_CheckAllUnmarked（DEBUG）
```cpp
template <typename T, typename Traits = T>
void GrTTopoSort_CheckAllUnmarked(SkSpan<const sk_sp<T>> graph)
```

调试模式下检查所有节点未标记。

#### GrTTopoSort_CleanExit（DEBUG）
```cpp
template <typename T, typename Traits = T>
void GrTTopoSort_CleanExit(SkSpan<const sk_sp<T>> graph, uint32_t offset)
```

调试模式下验证排序结果的正确性。

## 公共 API 函数

### GrTTopoSort（主函数）

```cpp
template <typename T, typename Traits = T>
bool GrTTopoSort(SkSpan<sk_sp<T>> graph, uint32_t offset = 0)
```

**功能**: 对节点数组进行拓扑排序

**语义**: "节点 i 依赖节点 j" 意味着"节点 j 必须在节点 i 之前"

**前置条件**:
- 节点的所有依赖必须也在数组中，或已标记为 `WasOutput() = true`
- 节点未被临时标记
- 节点未被标记为已输出（除非是外部已排序的依赖）

**后置条件**:
- 数组被重排为拓扑顺序
- 每个节点的索引被设置为其在结果中的位置
- 所有节点标记为已输出
- 临时标记被清除

**返回值**:
- `true`: 成功（无环）
- `false`: 存在循环依赖，数组状态未定义

**算法流程**:
1. DEBUG 模式下检查初始状态
2. 遍历所有节点
3. 对每个未输出的节点调用 `GrTTopoSort_Visit`
4. 根据输出索引重排数组
5. DEBUG 模式下验证结果

### GrTTopoSort_Visit（递归核心）

```cpp
template <typename T, typename Traits = T>
bool GrTTopoSort_Visit(T* node, uint32_t* counter)
```

**功能**: 递归访问节点及其依赖

**算法**:
1. 检查临时标记（如果有，说明存在环）
2. 检查是否已输出（如果是，直接返回）
3. 设置临时标记
4. 递归访问所有依赖
5. 标记为已输出并分配索引
6. 清除临时标记

**循环检测**: 如果访问到已临时标记的节点，说明存在反向边（环）

## 内部实现细节

### 拓扑排序算法

使用深度优先搜索（DFS）的后序遍历：

```cpp
for (size_t i = 0; i < graph.size(); ++i) {
    if (Traits::WasOutput(graph[i].get())) {
        continue;  // 已处理
    }
    if (!GrTTopoSort_Visit<T, Traits>(graph[i].get(), &counter)) {
        succeeded = false;  // 检测到环
    }
}
```

**关键特性:**
- **后序遍历**: 依赖先输出，依赖者后输出
- **备忘录**: 已输出的节点不再访问
- **环检测**: 临时标记检测反向边

### 循环检测机制

```cpp
bool GrTTopoSort_Visit(T* node, uint32_t* counter) {
    if (Traits::IsTempMarked(node)) {
        return false;  // 检测到环
    }
    // ...
    Traits::SetTempMark(node);
    // 访问依赖
    Traits::ResetTempMark(node);
}
```

**原理:**
- **临时标记**: 表示节点在当前 DFS 路径上
- **反向边**: 如果访问到已临时标记的节点，说明存在从该节点回到自身的路径（环）

### 数组重排

排序完成后，根据输出索引重排数组：

```cpp
for (uint32_t i = 0; i < (uint32_t) graph.size(); ++i) {
    for (uint32_t correctIndex = Traits::GetIndex(graph[i].get()) - offset;
         correctIndex != i;
         correctIndex = Traits::GetIndex(graph[i].get()) - offset) {
         graph[i].swap(graph[correctIndex]);
    }
}
```

**算法:**
- 遍历每个位置
- 将正确的节点交换到当前位置
- 循环直到当前位置正确

**复杂度**: O(n)（每个节点最多被移动一次）

### 偏移量支持

`offset` 参数支持对大图的子范围排序：

```cpp
Traits::Output(node, *counter);  // *counter 包含 offset
uint32_t correctIndex = Traits::GetIndex(graph[i].get()) - offset;
```

**用途:**
- 对大型 DAG 的部分进行局部排序
- 保持全局索引的连续性

### DEBUG 验证

#### 初始状态检查
```cpp
void GrTTopoSort_CheckAllUnmarked(SkSpan<const sk_sp<T>> graph) {
    for (const auto& node : graph) {
        SkASSERT(!Traits::IsTempMarked(node.get()));
        SkASSERT(!Traits::WasOutput(node.get()));
    }
}
```

确保输入状态正确。

#### 结果验证
```cpp
void GrTTopoSort_CleanExit(SkSpan<const sk_sp<T>> graph, uint32_t offset) {
    for (size_t i = 0; i < graph.size(); ++i) {
        SkASSERT(!Traits::IsTempMarked(graph[i].get()));
        SkASSERT(Traits::WasOutput(graph[i].get()));
        SkASSERT(Traits::GetIndex(graph[i].get()) - offset == (uint32_t) i);
    }
}
```

验证：
- 无临时标记残留
- 所有节点已输出
- 索引连续且正确

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkRefCnt` | 智能指针类型（`sk_sp`） |
| `SkSpan` | 数组视图 |
| `SkTypes` | 基础类型和断言 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrDrawingManager` | 对 `GrRenderTask` 进行拓扑排序 |
| `GrRenderTask` | 作为节点类型，提供 Traits 接口 |
| 图算法工具 | 通用的 DAG 排序需求 |

## 设计模式与设计决策

### Traits 模式

使用 Traits 模式实现泛型算法：

**优势:**
1. **类型无关**: 可用于任意符合接口的类型
2. **零开销抽象**: 编译时多态，无虚函数开销
3. **灵活性**: 可以为第三方类型提供 Traits 实现

**默认 Traits:**
```cpp
template <typename T, typename Traits = T>
```
默认使用 `T` 自身作为 Traits，要求 `T` 提供所需的静态方法。

### 原地排序

直接修改输入数组而非创建新数组：

**优势:**
- 节省内存（无需额外空间）
- 更新智能指针引用（不破坏外部引用）

**实现:**
- 使用 `swap` 重排元素
- 保持智能指针的有效性

### 深度优先搜索

选择 DFS 而非 BFS 的原因：

**DFS 优势:**
- 更容易检测环（临时标记）
- 递归实现简洁
- 适合输出后序遍历

**后序遍历:**
- 依赖先输出，依赖者后输出
- 自然满足拓扑顺序

### 环检测策略

使用三色标记变体：
- **白色**（未标记）: 未访问
- **灰色**（临时标记）: 访问中（DFS 栈上）
- **黑色**（已输出）: 已完成

检测到灰色到灰色的边即为反向边（环）。

### 失败处理

环检测失败时：
```cpp
if (!GrTTopoSort_Visit<T, Traits>(graph[i].get(), &counter)) {
    succeeded = false;  // 记录失败，但继续
}
```

**继续处理**: 即使检测到环，仍继续遍历，尽可能多地排序
**原因**: 提供更多调试信息，部分结果可能仍有用

### 索引记录

每个节点记录其在结果中的索引：

**用途:**
1. 重排数组时定位正确位置
2. 提供节点的拓扑顺序信息
3. 支持增量更新

### 偏移量设计

`offset` 参数的设计理念：

**场景**: 对大图的子范围排序，但需要保持全局索引
**实现**: 索引 = 本地位置 + 偏移量
**验证**: `GetIndex(node) - offset == local_position`

## 性能考量

### 时间复杂度

**算法复杂度**: O(V + E)
- V: 节点数
- E: 边数（依赖关系数）

**分析:**
- 每个节点访问一次: O(V)
- 每条边检查一次: O(E)
- 数组重排: O(V)

### 空间复杂度

**栈空间**: O(D)
- D: DAG 的最大深度
- 递归调用栈

**额外空间**: O(1)
- 原地排序，无额外数组
- 只使用 `counter` 变量

### 缓存友好性

**顺序访问**:
```cpp
for (size_t i = 0; i < graph.size(); ++i) { ... }
```
顺序遍历数组，缓存友好。

**随机访问**:
依赖关系访问可能随机，取决于 DAG 结构。

### 智能指针开销

使用 `sk_sp<T>`:
- **swap 操作**: O(1)，只交换指针
- **引用计数**: 原子操作，略有开销
- **无额外分配**: 不创建新的智能指针

### 递归 vs 迭代

**选择递归**的理由：
- 代码简洁，易于理解
- 现代编译器优化良好
- GPU 任务 DAG 深度通常不大（栈溢出风险低）

**栈使用**:
每层递归约 16-32 字节（取决于编译器），深度 100 时约 1.6-3.2 KB。

### DEBUG 开销

验证代码只在 DEBUG 模式：
```cpp
#ifdef SK_DEBUG
    GrTTopoSort_CheckAllUnmarked<T, Traits>(graph);
    // ...
    GrTTopoSort_CleanExit<T, Traits>(graph, offset);
#endif
```

**发布版本**: 零验证开销

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrRenderTask.h` | 主要使用者 | 提供 Traits 接口 |
| `src/gpu/ganesh/GrDrawingManager.cpp` | 调用者 | 对任务 DAG 排序 |
| `include/core/SkSpan.h` | 依赖 | 数组视图类型 |
| `include/core/SkRefCnt.h` | 依赖 | 智能指针 |
| `tests/GrTTopoSortTest.cpp` | 测试 | 单元测试 |
