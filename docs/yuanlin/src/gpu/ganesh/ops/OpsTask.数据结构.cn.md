# OpsTask · 数据结构

> 源码: `src/gpu/ganesh/ops/OpsTask.cpp` (1101行)
> 主文档: [OpsTask.cn.md](./OpsTask.cn.md)

---

## 2. OpChain::List 方法

### 2.1 `List(GrOp::Owner)` 构造 (line 99-102)

从单个 Op 构建链表：`fHead = op`, `fTail = fHead.get()`。

---

### 2.2 `List(List&&)` 移动构造 (line 104)

委托给 `operator=(List&&)`。

---

### 2.3 `operator=(List&&)` (line 106-112)

移动 fHead 和 fTail，清空源链表的 fTail。

---

### 2.4 `popHead()` (line 114-123)

```mermaid
flowchart TD
    A[断言 fHead 非空] --> B[temp = fHead->cutChain]
    B --> C[swap temp, fHead]
    C --> D{fHead 为空?}
    D -->|是| E[fTail = nullptr]
    D -->|否| F[保持 fTail]
    E --> G[返回 temp]
    F --> G
```

---

### 2.5 `removeOp()` (line 125-145)

从链表中移除指定 Op 并返回其 Owner。

```mermaid
flowchart TD
    A[找到 op 的 prev] --> B{prev 为空?}
    B -->|是 op==head| C[调用 popHead]
    B -->|否| D[prev->cutChain 得到 temp=op]
    D --> E{op 有 next?}
    E -->|是| F[prev->chainConcat next]
    E -->|否 op==tail| G[fTail = prev]
    F --> H[validate & 返回 temp]
    G --> H
    C --> H
```

---

### 2.6 `pushHead()` (line 147-158)

将 Op 插入链表头部。

```mermaid
flowchart TD
    A[断言 op 是独立节点] --> B{fHead 非空?}
    B -->|是| C[op->chainConcat fHead]
    C --> D[fHead = op]
    B -->|否| E[fHead = op, fTail = fHead.get]
```

---

### 2.7 `pushTail()` (line 160-164)

将 Op 追加到链表尾部：`fTail->chainConcat(op)`, 然后更新 `fTail = fTail->nextInChain()`。

---

### 2.8 `validate()` (line 166-173)

调试断言：若 fHead 非空则验证 fTail 非空且 `fHead->validateChain(fTail)` 通过。

---

## 3. OpChain 方法

### 3.1 `OpChain()` 构造 (line 177-187)

```mermaid
flowchart TD
    A[List fList 从 op 构建] --> B[保存 processorAnalysis]
    B --> C[保存 appliedClip]
    C --> D{requiresDstTexture?}
    D -->|是| E[fDstProxyView = *dstProxyView]
    D -->|否| F[fDstProxyView 保持空]
    E --> G[fBounds = head->bounds]
    F --> G
```

---

### 3.2 `visitProxies()` (line 189-202)

遍历链中每个 Op 调用 `op.visitProxies(func)`，再访问 `fDstProxyView.proxy()` 和 `fAppliedClip`。

---

### 3.3 `deleteOps()` (line 204-209)

循环 `fList.popHead()` 直到链表为空，利用 `GrOp::Owner` 的析构释放内存。

---

### 3.4 `DoConcat()` (line 213-287)

**核心合并算法**: 将 chainB 的每个 Op 合并到 chainA 中。

```mermaid
flowchart TD
    A[origATail = chainA.tail] --> B[skipBounds = 空]
    B --> C{chainB 非空?}
    C -->|否| Z[返回 chainA]
    C -->|是| D[从 origATail 开始向前遍历 chainA]
    D --> E{canForward 或 canBackward?}
    E -->|是| F[combineIfPossible]
    F --> G{merged?}
    G -->|是 backward| H[chainB.popHead 释放]
    G -->|是 forward| I[从 chainA 移除 a 放入 chainB 头]
    I --> J{chainA 空?}
    J -->|是| K[返回 chainB]
    J -->|否| L[break 继续外层循环]
    H --> L
    G -->|否| M{达到 kMaxOpMergeDistance?}
    M -->|是| N[break]
    M -->|否| O[a = a->prevInChain, 累计 forwardMergeBounds]
    O --> E
    E -->|否| O
    N --> P{merged?}
    P -->|否| Q[chainA.pushTail chainB.popHead]
    Q --> R[更新 skipBounds]
    R --> C
    P -->|是| C
    L --> C
```

**三种结局**:
1. **backward merge**: B 的 head 被合并入 A 的某个 Op (B.popHead 释放)
2. **forward merge**: A 的某个 Op 被合并入 B 的 head (该 Op 从 A 移到 B 头部，重新处理)
3. **无法合并**: B.head 弹出追加到 A 尾部

---

### 3.5 `tryConcat()` (line 291-349)

尝试将外部 List 拼接到当前 OpChain。

```mermaid
flowchart TD
    A[兼容性检查] --> B{classID 相同?}
    B -->|否| Z[返回 false]
    B -->|是| C{clip 兼容?}
    C -->|否| Z
    C -->|是| D{nonOverlapping 且 bounds 重叠?}
    D -->|是| Z
    D -->|否| E{dstTexture 兼容?}
    E -->|否| Z
    E -->|是| F[进入 do-while 循环]
    F --> G[tail->combineIfPossible head]
    G --> H{结果?}
    H -->|kCannotCombine| I[仅首次允许, 返回 false]
    H -->|kMayChain| J[DoConcat 合并双链]
    H -->|kMerged| K[popHead 释放被合并 Op]
    J --> L{list 空?}
    K --> L
    L -->|否| F
    L -->|是| M[joinBounds, 返回 true]
```

---

### 3.6 `prependChain()` (line 351-372)

将 `that` 的链合并到自身前面：调用 `that->tryConcat(&fList, ...)` 反向拼接，成功后将结果移回。

---

### 3.7 `appendOp()` (line 374-395)

将单个 Op 追加到链中：将 Op 包装为 List 后调用 `tryConcat`。失败则返回 Op 给调用者。

---

### 3.8 `validate()` (line 397-406)

调试断言：验证链表有效，且每个 Op 的 bounds 都包含在 fBounds 内。
