# GrRenderTaskCluster

> 源文件
> - src/gpu/ganesh/GrRenderTaskCluster.h
> - src/gpu/ganesh/GrRenderTaskCluster.cpp

## 概述

`GrRenderTaskCluster` 提供了一个渲染任务聚类算法,用于优化已经按拓扑排序的渲染任务 DAG(有向无环图)。该算法在保持依赖关系的前提下,将具有相同目标 surface 的任务聚集在一起,从而减少 GPU 上下文切换,提高渲染效率。核心函数 `GrClusterRenderTasks` 接收按依赖顺序排列的任务数组,输出重新排序后的任务链表。

## 架构位置

在 Skia GPU 渲染流水线中的位置:

```
GrDrawingManager
    └── flush() 流程
        ├── 生成拓扑排序的 RenderTask DAG
        ├── GrClusterRenderTasks (优化任务顺序)
        └── 按优化后的顺序执行任务
```

该模块是渲染任务调度优化的关键组件,位于任务排序和执行之间。

## 主要类与结构体

### 核心函数

```cpp
bool GrClusterRenderTasks(SkSpan<const sk_sp<GrRenderTask>> input,
                          SkTInternalLList<GrRenderTask>* llist);
```

**参数**:
- `input`: 按拓扑排序的任务数组
- `llist`: 输出的任务链表

**返回值**:
- `true`: 发生了重排序,任务已优化
- `false`: 未能优化或任务数量过少

## 公共 API 函数

### 主函数

```cpp
bool GrClusterRenderTasks(SkSpan<const sk_sp<GrRenderTask>> input,
                          SkTInternalLList<GrRenderTask>* llist);
```

该函数是模块唯一的公共接口,实现了完整的聚类算法。

## 内部实现细节

### 聚类算法核心逻辑

算法采用贪心策略,尝试将每个新任务移动到与其目标相同的任务簇中:

```cpp
static bool task_cluster_visit(GrRenderTask* task,
                                SkTInternalLList<GrRenderTask>* llist,
                                THashMap<GrSurfaceProxy*, GrRenderTask*>* lastTaskMap)
```

**算法步骤**:

1. **检查目标数量**:
   - 0 或多个目标的任务作为全屏障(barrier)
   - 这些任务会清空 `lastTaskMap`
   - 直接追加到列表末尾,不尝试聚类

2. **单目标任务处理**:
   - 查找同一目标的最后一个任务(簇尾)
   - 如果簇尾已经在列表末尾,无需优化
   - 否则尝试将簇尾之后的所有任务移动到簇头之前

3. **依赖性检查**:
   - 遍历要移动的所有任务
   - 检查它们是否依赖于簇中的任何任务
   - 使用 `depends_on` 函数判断依赖关系

4. **执行重排序**:
   - 如果没有依赖冲突,执行移动操作
   - 将簇尾之后的任务逐个移到簇头之前
   - 更新 `lastTaskMap` 中的簇尾指针

### 依赖关系判断

```cpp
static bool depends_on(GrRenderTask* depender, GrRenderTask* dependee)
```

判断 `depender` 是否依赖 `dependee`:

1. **写后读依赖**:
   - 检查 `depender` 写入的 surface 是否被 `dependee` 读取
   - 如果是,则存在数据依赖,不能重排序

2. **形式化依赖**:
   - 检查是否存在显式的任务依赖关系
   - 通过 `depender->dependsOn(dependee)` 查询

### 性能优化特点

**早期退出条件**:
```cpp
if (input.size() < 3) {
    // 任务太少,不值得优化
    for (const auto& t : input) {
        llist->addToTail(t.get());
    }
    return false;
}
```

**避免不必要的遍历**:
- 只对单目标任务尝试聚类
- 多目标任务自然形成同步点
- 减少了复杂度检查

**链表操作优化**:
- 使用侵入式链表 `SkTInternalLList`
- O(1) 的插入和移除操作
- 避免额外的内存分配

### 调试支持

```cpp
#define CLUSTER_DEBUGF(...) //SkDebugf(__VA_ARGS__)
```

提供详细的调试日志输出(默认禁用):
- 每一步的决策过程
- 依赖关系检查结果
- 重排序操作记录

**验证机制**(调试模式):
```cpp
static void validate(SkSpan<const sk_sp<GrRenderTask>> input,
                     const SkTInternalLList<GrRenderTask>& llist)
```

验证内容:
- 依赖关系未被破坏
- 输出包含输入的所有任务
- 任务不重不漏

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrRenderTask` | 被聚类的任务对象 |
| `GrSurfaceProxy` | 任务的目标 surface |
| `SkTInternalLList` | 输出的链表数据结构 |
| `SkTHash` | 哈希表用于跟踪簇尾 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `GrDrawingManager` | 在 flush 时调用聚类优化 |

## 设计模式与设计决策

### 设计模式

1. **贪心算法**:
   - 逐个处理任务,局部最优选择
   - 尝试将任务移动到最近的同目标簇

2. **屏障模式**:
   - 多目标任务作为同步屏障
   - 防止过度激进的重排序

3. **验证模式**:
   - 在调试模式下验证优化正确性
   - 确保依赖关系和任务完整性

### 关键设计决策

**为何使用贪心策略而非全局优化**:
- 全局优化复杂度高(NP-hard)
- 贪心算法在实践中效果良好
- 实现简单,性能开销低

**为何多目标任务是屏障**:
- 多目标任务通常涉及复杂的同步
- 将其作为屏障简化了依赖分析
- 保守策略避免正确性问题

**为何检查写后读而非完整数据流分析**:
- 简化依赖分析复杂度
- 结合形式化依赖,已足够保证正确性
- 性能开销可接受

## 性能考量

### 时间复杂度

- **最好情况**: O(n),任务已经聚类良好
- **最坏情况**: O(n²),每个任务都需要检查所有后续任务
- **实际情况**: 通常接近 O(n),因为簇通常较短

### 空间复杂度

- O(n),需要哈希表跟踪每个目标的簇尾
- 链表本身不需要额外空间(侵入式)

### 性能收益

**减少上下文切换**:
- 连续处理同一目标的任务
- 减少 GPU 状态切换
- 提高缓存命中率

**实际测试数据**:
根据代码注释中的统计:
- 83% 的任务直接追加到尾部(已排序良好)
- 只有少数任务需要重排序
- 优化开销很小

### 优化权衡

**保守的依赖检查**:
- 检查所有可能的依赖关系
- 宁可漏过优化机会,也不破坏正确性
- 确保渲染结果的一致性

**簇大小限制**:
- 没有显式限制簇的大小
- 依赖关系自然限制了簇的增长
- 避免过度聚类导致延迟

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrRenderTask.h` | 操作对象 | 被聚类的任务类 |
| `src/gpu/ganesh/GrSurfaceProxy.h` | 依赖 | 任务的目标 surface |
| `src/gpu/ganesh/GrDrawingManager.cpp` | 使用者 | 调用聚类算法 |
| `src/base/SkTInternalLList.h` | 数据结构 | 输出的链表容器 |
| `src/core/SkTHash.h` | 数据结构 | 哈希表实现 |
