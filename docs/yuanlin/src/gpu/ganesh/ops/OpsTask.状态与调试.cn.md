# OpsTask · 状态与调试

> 源码: `src/gpu/ganesh/ops/OpsTask.cpp` (1101行)
> 主文档: [OpsTask.cn.md](./OpsTask.cn.md)

---

## 6. 状态管理与任务合并

### 6.1 `setColorLoadOp()` (line 681-689)

设置颜色加载操作和清除颜色。若为 `kClear` 则将 `fTotalBounds` 扩展到整个 backingStore。

---

### 6.2 `reset()` (line 691-698)

完全重置 OpsTask 状态：清除代理列表、bounds、deleteOps、重置 XferBarriers。用于合并算法中被跳过的任务。

---

### 6.3 `canMerge()` (line 700-704)

判断另一个 OpsTask 是否可合并到当前任务：要求 target 相同、arenas 相同、且目标未设置 `fCannotMergeBackward`。

---

### 6.4 `mergeFrom()` (line 706-777)

**任务合并核心算法**: 将多个连续 OpsTask 合并为一个。

```mermaid
flowchart TD
    A[遍历 tasks 计算可合并数量] --> B{有 kClear loadOp?}
    B -->|是| C[返回 0 放弃合并]
    B -->|否| D[mergedCount 确定]
    D --> E[统计 addl 容量]
    E --> F[合并元数据: bounds/xferBarriers/stencil/MSAA]
    F --> G[reserve 容器空间]
    G --> H[遍历 mergingNodes]
    H --> I[替换依赖关系 replaceDependency/replaceDependent]
    I --> J[move_back_n: deferredProxies/sampledProxies/opChains]
    J --> K[清空源任务容器]
    K --> L{还有下一个?}
    L -->|是| H
    L -->|否| M[fMustPreserveStencil = 最后一个的值]
    M --> N[返回 mergedCount]
```

---

### 6.5 `resetForFullscreenClear()` (line 779-793)

全屏清除时的预处理。

```mermaid
flowchart TD
    A{canDiscard 或 isEmpty?}
    A -->|是| B[deleteOps, clear proxies]
    B --> C{wrapsVkSecondaryCB?}
    C -->|是| D[返回 false, 需要 ClearOp]
    C -->|否| E[返回 true, 可用 loadOp]
    A -->|否| F[返回 false, 需要添加 Op]
```

---

### 6.6 `discard()` (line 795-803)

丢弃操作：仅在 OpsTask 为空时生效，设置 `fColorLoadOp = kDiscard`，stencil 设为 `kDontCare`，清空 bounds。

---

## 7. 调试与诊断

### 7.1 `dump()` (line 808-871)

`GPU_TEST_UTILS` 条件编译。输出颜色 loadOp、stencil 内容、所有 OpChain 的名称和边界信息。

---

### 7.2 `visitProxies_debugOnly()` (line 874-884)

`SK_DEBUG` 条件编译。遍历所有 OpChain 调用 `visitProxies` 用于调试验证。

---

### 7.3 `onMakeSkippable()` (line 888-893)

标记任务可跳过：deleteOps、clear deferredProxies、将 loadOp 重置为 `kLoad` (使 `isColorNoOp()` 返回 true)。

---

### 7.4 `onIsUsed()` (line 895-915)

检查指定 proxy 是否被当前任务采样。线性遍历 `fSampledProxies`，调试模式下与 `visitProxies_debugOnly` 交叉验证。
