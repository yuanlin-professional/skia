# OpsTask · Flush 管线

> 源码: `src/gpu/ganesh/ops/OpsTask.cpp` (1101行)
> 主文档: [OpsTask.cn.md](./OpsTask.cn.md)

---

## 5. Flush 管线

### 5.1 `onPrePrepare()` (line 489-511)

提前准备阶段 (DDL 录制时调用)。跳过 colorNoOp 或空 bounds 的情况，然后遍历每条 OpChain 调用 `head()->prePrepare()`。

---

### 5.2 `onPrepare()` (line 514-553)

Flush 时的准备阶段。设置 sampledProxies，遍历每条 OpChain 创建 `OpArgs` 后调用 `head()->prepare(flushState)`。

---

### 5.3 `onExecute()` (line 558-679)

**最核心的函数**: 创建 RenderPass 并执行所有 Op。

```mermaid
flowchart TD
    A[获取 RenderTargetProxy] --> B[SK_AT_SCOPE_EXIT: clearArenas]
    B --> C{isColorNoOp 或 bounds 为空?}
    C -->|是| Z[返回 false]
    C -->|否| D[断言 loadOp 合法]
    D --> E[获取 caps & renderTarget]
    E --> F{proxy needsStencil?}
    F -->|是| G[attachStencilAttachment]
    G --> H{成功?}
    H -->|否| I[打印警告, 返回 false]
    H -->|是| J[stencil = getStencilAttachment]
    F -->|否| K[stencil = nullptr]
    J --> L[确定 stencilLoadOp]
    K --> L
    L --> M[确定 stencilStoreOp]
    M --> N[create_render_pass]
    N --> O{renderPass 有效?}
    O -->|否| P[返回 false]
    O -->|是| Q[markStencilCleared 如需]
    Q --> R[renderPass->begin]
    R --> S[遍历 fOpChains]
    S --> T{shouldExecute?}
    T -->|否| U[continue]
    T -->|是| V[创建 OpArgs]
    V --> W[chain.head->execute]
    W --> S
    S -->|遍历完毕| X[renderPass->end]
    X --> Y[gpu->submit renderPass]
    Y --> ZZ[返回 true]
```

**stencilLoadOp 决策子流程** (line 590-618):

```mermaid
flowchart TD
    A{fInitialStencilContent?}
    A -->|kDontCare| B[stencilLoadOp = kDiscard]
    A -->|kUserBitsCleared| C{discardStencilValuesAfterRenderPass?}
    C -->|是 tiler| D[stencilLoadOp = kClear]
    C -->|否| E{stencil 已 initialClear?}
    E -->|否 首次| F[stencilLoadOp = kClear, markStencilCleared=true]
    E -->|是| G[fallthrough 到 kPreserved]
    A -->|kPreserved| H[stencilLoadOp = kLoad]
    G --> H
```
