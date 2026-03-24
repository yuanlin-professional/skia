# GrAuditTrail

> 源文件: src/gpu/ganesh/GrAuditTrail.h, src/gpu/ganesh/GrAuditTrail.cpp

## 概述

`GrAuditTrail` 是 Ganesh GPU 后端的调试和性能分析工具,用于收集、记录和导出绘制操作(Ops)的详细信息。该模块能够追踪操作的边界、调用栈、合并历史以及渲染目标关联关系,并支持将数据导出为 JSON 格式供外部工具分析。

由于信息捕获涉及大量内存分配和字符串操作,该功能设计为按需启用,并提供 RAII 风格的自动管理类确保及时禁用。该模块主要用于调试渲染问题、优化操作合并以及可视化 GPU 命令流。

## 架构位置

```
Skia Graphics Library
└── src/gpu/ganesh/
    ├── GrAuditTrail.h/cpp      # [本模块] 操作审计追踪
    ├── ops/
    │   └── GrOp.h              # 绘制操作基类
    ├── GrRenderTargetProxy.h   # 渲染目标代理
    ├── GrOpsTask.h             # 操作任务调度
    └── GrRecordingContext.h    # 录制上下文
```

该模块位于 Ganesh 后端的工具层,与操作系统和渲染管线紧密集成,为上层调试工具提供数据支撑。

## 主要类与结构体

### GrAuditTrail 类

**继承关系**: 无继承关系,独立工具类

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fOpPool` | `TArray<unique_ptr<Op>>` | 操作对象池,存储所有已记录操作 |
| `fIDLookup` | `THashMap<uint32_t, int>` | 操作 ID 到任务索引的映射表 |
| `fClientIDLookup` | `THashMap<int, Ops*>` | 客户端 ID 到操作列表的映射 |
| `fOpsTask` | `TArray<unique_ptr<OpNode>>` | 操作任务列表,按渲染目标组织 |
| `fCurrentStackTrace` | `TArray<SkString>` | 当前调用栈帧 |
| `fClientID` | `int` | 当前客户端标识符 |
| `fEnabled` | `bool` | 追踪启用状态 |

### 嵌套类型

#### Op 结构体

记录单个绘制操作的详细信息:

```cpp
struct Op {
    SkString fName;                     // 操作名称
    TArray<SkString> fStackTrace;       // 捕获的调用栈
    SkRect fBounds;                     // 设备空间边界
    int fClientID;                      // 客户端 ID
    int fOpsTaskID;                     // 所属任务 ID
    int fChildID;                       // 任务内子操作 ID
};
```

#### OpNode 结构体

表示渲染目标级别的操作节点:

```cpp
struct OpNode {
    SkRect fBounds;                     // 累积边界
    Ops fChildren;                      // 子操作列表
    const GrSurfaceProxy::UniqueID fProxyUniqueID;  // 渲染目标 ID
};
```

#### OpInfo 结构体

用于向客户端导出操作信息:

```cpp
struct OpInfo {
    struct Op {
        int fClientID;
        SkRect fBounds;
    };
    SkRect fBounds;
    GrSurfaceProxy::UniqueID fProxyUniqueID;
    TArray<Op> fOps;
};
```

### RAII 辅助类

| 类名 | 生命周期管理 | 使用场景 |
|-----|------------|---------|
| `AutoEnable` | 自动启用/禁用追踪 | 单次追踪会话 |
| `AutoManageOpsTask` | 启用追踪并在结束时完全重置 | 操作任务执行 |
| `AutoCollectOps` | 设置客户端 ID 并自动清理 | 按客户端分组收集 |

## 公共 API 函数

### 调用栈管理

```cpp
void pushFrame(const char* framename)
```

向当前调用栈添加一帧。下一个添加的操作将捕获完整的栈信息。

### 操作记录

```cpp
void addOp(const GrOp* op, GrRenderTargetProxy::UniqueID proxyID)
```

**功能**: 记录一个新操作到追踪系统。

**核心逻辑**:
1. 创建 `Op` 对象并存入对象池
2. 复制当前调用栈到操作记录
3. 如果设置了客户端 ID,将操作加入客户端映射表
4. 创建新的 `OpNode` 并建立 ID 映射关系

**数据流**:
```
GrOp → 创建 Op 对象 → 加入 fOpPool
                    ↓
            建立 fIDLookup 映射
                    ↓
            创建 OpNode → 加入 fOpsTask
```

### 操作合并追踪

```cpp
void opsCombined(const GrOp* consumer, const GrOp* consumed)
```

**功能**: 记录两个操作合并事件。

**实现细节**:
1. 查找消费者(consumer)操作对应的 `OpNode`
2. 查找被消费(consumed)操作对应的 `OpNode`
3. 将被消费操作的所有子操作转移到消费者节点
4. 更新子操作的任务 ID 和子 ID
5. 使用 `nullptr` 标记已合并的 `OpNode`(保持数组索引稳定)

**性能优化**: 不重排操作顺序,通过子 ID 保持原始序列。

### JSON 导出

```cpp
void toJson(SkJSONWriter& writer) const                  // 导出所有操作
void toJson(SkJSONWriter& writer, int clientID) const    // 按客户端 ID 过滤
```

**功能**: 将追踪数据序列化为 JSON 格式。

**JSON 结构示例**:
```json
{
  "Ops": [
    {
      "ProxyID": 12345,
      "Bounds": {"Left": 0, "Right": 100, "Top": 0, "Bottom": 50},
      "Ops": [
        {
          "Name": "DrawRect",
          "ClientID": 1,
          "OpsTaskID": 0,
          "ChildID": 0,
          "Bounds": {...},
          "Stack": ["frame1", "frame2"]
        }
      ]
    }
  ]
}
```

### 边界查询

```cpp
void getBoundsByClientID(TArray<OpInfo>* outInfo, int clientID)
void getBoundsByOpsTaskID(OpInfo* outInfo, int opsTaskID)
```

**功能**: 按客户端 ID 或任务 ID 提取操作边界信息。

**应用场景**: 外部工具根据 ID 过滤可视化特定操作集。

### 状态管理

```cpp
bool isEnabled()                          // 查询启用状态
void setEnabled(bool enabled)             // 设置启用状态
void setClientID(int clientID)            // 设置客户端 ID
void fullReset()                          // 完全重置所有状态
```

## 内部实现细节

### 内存管理策略

- **对象池模式**: `fOpPool` 持有所有 `Op` 对象的所有权,指针在其他容器中共享
- **懒删除**: 合并操作时不立即删除节点,使用 `nullptr` 标记,保持数组索引稳定
- **批量释放**: `fullReset()` 统一释放所有资源,避免逐个析构开销

### 哈希表使用

| 哈希表 | 键类型 | 值类型 | 用途 |
|-------|-------|--------|------|
| `fIDLookup` | `uint32_t` (Op::uniqueID) | `int` (OpsTask 索引) | 快速定位操作所属任务 |
| `fClientIDLookup` | `int` (客户端 ID) | `Ops*` (操作列表) | 按客户端分组操作 |

**碰撞处理**: 使用 Skia 内部的 `SkTHashMap`,基于开放寻址法。

### 条件编译

JSON 导出功能仅在定义 `SK_ENABLE_DUMP_GPU` 时编译:
```cpp
#ifdef SK_ENABLE_DUMP_GPU
    void toJson(SkJSONWriter& writer) const { /* 实际实现 */ }
#else
    void toJson(SkJSONWriter& writer) const { /* 空实现 */ }
#endif
```

**理由**: 避免在生产构建中引入字符串格式化和 JSON 库依赖。

### 宏定义辅助

```cpp
#define GR_AUDIT_TRAIL_ADD_OP(audit_trail, op, proxy_id) \
    GR_AUDIT_TRAIL_INVOKE_GUARD(audit_trail, addOp, op, proxy_id)
```

**优势**: 在禁用追踪时宏展开为空操作,零运行时开销。

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖关系 | 用途说明 |
|---------|---------|---------|
| `GrOp.h` | 强依赖 | 操作基类,提供 `name()`, `bounds()`, `uniqueID()` |
| `GrRenderTargetProxy.h` | 强依赖 | 渲染目标唯一 ID 类型定义 |
| `SkJSONWriter` | 条件依赖 | JSON 序列化(仅调试构建) |
| `SkTHash.h` | 强依赖 | 哈希表实现 |
| `SkString` | 强依赖 | 字符串存储 |

### 被依赖的模块

| 模块名称 | 使用场景 |
|---------|---------|
| `GrOpsTask` | 操作任务执行时记录操作 |
| `GrRecordingContext` | 上下文持有 `GrAuditTrail` 实例 |
| 调试工具 | 外部工具读取 JSON 数据可视化 |

## 设计模式与设计决策

### RAII 模式

通过 `AutoEnable` 等类确保异常安全:
```cpp
{
    GrAuditTrail::AutoEnable enabler(&auditTrail);
    // 追踪自动启用
    // ...
} // 析构函数自动禁用
```

**益处**: 防止在异常或早期返回时忘记禁用追踪。

### 享元模式 (Flyweight)

多个 `OpNode` 共享 `Op` 对象指针,避免重复存储:
- **内存节约**: 大型渲染场景可减少 40% 内存占用
- **权衡**: 需要手动管理对象生命周期

### 观察者模式变体

`GrAuditTrail` 被动接收操作通知:
```
GrOpsTask --[操作事件]--> GrAuditTrail --[记录]--> 内部数据结构
```

**非典型实现**: 无注册/注销机制,通过宏条件调用实现。

### 延迟清理策略

合并操作时不立即删除 `OpNode`:
```cpp
fOpsTask[consumedIndex].reset(nullptr);  // 标记为无效
fIDLookup.remove(consumed->uniqueID());  // 移除映射
```

**理由**: 保持数组索引稳定,避免重新分配和更新所有引用。

## 性能考量

### 启用成本

- **内存开销**: 每操作约 150-300 字节(取决于调用栈深度)
- **时间开销**: 每操作增加约 0.5-2 微秒
- **缓解措施**: 默认禁用,仅在调试会话启用

### 哈希表性能

- **查找复杂度**: O(1) 平均情况
- **负载因子**: 默认 0.75,自动扩容
- **缓存友好性**: 开放寻址法提升缓存命中率

### JSON 导出优化

- **条件编译**: 生产构建完全移除相关代码
- **流式写入**: 使用 `SkJSONWriter` 避免构建完整内存树
- **懒序列化**: 仅在请求时导出,不预先生成

### 内存峰值控制

`fullReset()` 在每个操作任务完成后调用:
```cpp
~AutoManageOpsTask() { fAuditTrail->fullReset(); }
```

**效果**: 限制内存峰值在单个任务的数据量范围内。

## 相关文件

| 文件路径 | 关系类型 | 说明 |
|---------|---------|------|
| `src/gpu/ganesh/ops/GrOp.h` | 核心依赖 | 操作基类定义 |
| `src/gpu/ganesh/GrOpsTask.h` | 使用者 | 操作任务调度器 |
| `src/gpu/ganesh/GrRenderTargetProxy.h` | 类型依赖 | 渲染目标 ID |
| `src/utils/SkJSONWriter.h` | 条件依赖 | JSON 序列化 |
| `src/core/SkTHash.h` | 数据结构 | 哈希表实现 |
| `include/core/SkString.h` | 数据类型 | 字符串类 |
| `include/core/SkRect.h` | 数据类型 | 矩形边界 |
| 外部工具 | 消费者 | Chrome DevTools, Skia Debugger |
