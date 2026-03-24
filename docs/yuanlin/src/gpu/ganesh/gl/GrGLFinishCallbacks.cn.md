# GrGLFinishCallbacks

> 源文件: src/gpu/ganesh/gl/GrGLFinishCallbacks.h, src/gpu/ganesh/gl/GrGLFinishCallbacks.cpp

## 概述

`GrGLFinishCallbacks` 是 Skia 图形库 Ganesh OpenGL 后端中用于管理 GPU 工作完成回调的类。该类维护一个回调列表,每个回调关联一个 OpenGL 同步对象(fence sync)和可选的计时器查询。当 GPU 完成相应的工作后,会自动调用对应的回调函数,并可选地传递 GPU 执行时间等性能统计信息。

该类提供了异步 GPU 工作完成通知机制,对于实现非阻塞的 GPU 操作和性能监控至关重要。

## 架构位置

`GrGLFinishCallbacks` 位于 Skia GPU 渲染架构的 OpenGL 后端同步机制层:

```
skia/
└── src/gpu/ganesh/gl/
    ├── GrGLFinishCallbacks.h/cpp  <- 本模块
    ├── GrGLGpu.h/cpp              <- GPU 实现(使用本模块)
    ├── GrGLInterface.h            <- OpenGL 函数接口
    └── RefCntedCallback.h         <- 回调基类
```

该模块在 `GrGLGpu` 中作为成员变量使用,负责管理所有与渲染工作完成相关的回调。

## 主要类与结构体

### GrGLFinishCallbacks 类

无继承关系,作为独立的管理类存在。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGpu` | `GrGLGpu*` | 指向拥有此对象的 GPU 实例 |
| `fCallbacks` | `std::list<FinishCallback>` | 待处理的回调列表 |

### FinishCallback 结构体

内部结构,表示单个完成回调。

| 字段 | 类型 | 说明 |
|------|------|------|
| `fCallback` | `skgpu::AutoCallback` | 自动管理的回调对象 |
| `fSync` | `GrGLsync` | OpenGL 同步对象(fence) |
| `fTimerQuery` | `GrGLint` | 计时器查询对象 ID(可选,0 表示无) |

## 公共 API 函数

### 构造与析构

```cpp
GrGLFinishCallbacks(GrGLGpu* gpu);
~GrGLFinishCallbacks();
```

- **构造函数**: 初始化时关联到特定的 `GrGLGpu` 实例
- **析构函数**: 调用所有未处理的回调并删除同步对象

### 添加回调

```cpp
void add(skgpu::AutoCallback callback, GrGLint timerQuery = 0);
```

**功能**: 添加新的完成回调到列表末尾

**参数**:
- `callback`: 自动管理的回调对象,在 GPU 工作完成时调用
- `timerQuery`: 可选的计时器查询 ID,用于获取 GPU 执行时间

**实现细节**:
1. 创建 OpenGL fence sync 对象 (`fGpu->insertSync()`)
2. 将回调、sync 和 timerQuery 封装为 `FinishCallback` 结构
3. 添加到列表末尾

### 检查回调

```cpp
void check();
```

**功能**: 非阻塞地检查是否有 GPU 工作已完成,并调用相应回调

**实现逻辑**:
1. 遍历回调列表(从前向后)
2. 测试每个 sync 对象是否已完成 (`fGpu->testSync()`)
3. 如果已完成:
   - 删除 sync 对象
   - 获取计时器查询结果(如果有)
   - 将性能统计数据传递给回调
   - 从列表中移除该回调
4. 遇到第一个未完成的 sync 时停止(保证顺序性)

**关键特性**: 提前终止遍历,因为 OpenGL sync 对象按插入顺序完成。

### 调用所有回调

```cpp
void callAll(bool doDelete);
```

**功能**: 同步等待所有 GPU 工作完成并调用所有回调

**参数**:
- `doDelete`: 是否删除 sync 对象和查询计时器结果

**使用场景**:
- 析构时: `callAll(true)`
- 强制同步: `callAll(true)`
- 上下文丢失: `callAll(false)` (不查询 GPU 状态)

### 查询状态

```cpp
bool empty() const;
```

返回回调列表是否为空。

## 内部实现细节

### 同步对象生命周期管理

1. **创建**: 调用 `add()` 时通过 `fGpu->insertSync()` 创建
2. **查询**: 在 `check()` 中通过 `fGpu->testSync()` 查询状态
3. **删除**: 完成后通过 `fGpu->deleteSync()` 删除

### 计时器查询处理

```cpp
if (auto timerQuery = finishCallback.fTimerQuery) {
    stats.elapsedTime = fGpu->getTimerQueryResult(timerQuery);
    if (finishCallback.fCallback.receivesGpuStats()) {
        finishCallback.fCallback.setStats(stats);
    }
}
```

仅在回调需要性能统计信息时设置数据,避免不必要的查询开销。

### 回调执行顺序保证

使用 `std::list` 并在 `check()` 中遇到未完成的 sync 时立即终止:

```cpp
while (!fCallbacks.empty() && fGpu->testSync(fCallbacks.front().fSync)) {
    // 处理已完成的回调
}
```

**设计理念**: OpenGL 保证 fence sync 按提交顺序完成,因此可以提前终止遍历以提高效率。

### 回调列表修改的线程安全性

**注意**: 在处理回调时必须先从列表中移除,然后再调用回调:

```cpp
auto& finishCallback = fCallbacks.front();
// ... 处理 sync 和 timer query ...
fCallbacks.pop_front();  // 在回调可能触发的任何操作之前移除
```

**原因**: 回调函数可能触发 `flushAndSubmit(/*sync=*/true)`,导致递归调用 `check()` 或 `callAll()`。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLGpu` | 管理 OpenGL sync 对象和计时器查询 |
| `skgpu::AutoCallback` | 自动管理的回调对象 |
| `skgpu::GpuStats` | GPU 性能统计信息结构 |
| `GrGLTypes` | OpenGL 类型定义(`GrGLsync`, `GrGLint`) |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrGLGpu` | 作为成员变量 `fFinishCallbacks` |
| 客户端代码 | 通过 `GrGLGpu::addFinishedCallback()` 间接使用 |

## 设计模式与设计决策

### 1. RAII 资源管理

使用 `skgpu::AutoCallback` 实现自动资源管理:

```cpp
struct FinishCallback {
    skgpu::AutoCallback fCallback;  // 自动析构,无需手动清理
    GrGLsync            fSync;
    GrGLint             fTimerQuery;
};
```

**优点**: 即使发生异常或提前返回,回调对象也会被正确清理。

### 2. 组合优于继承

`GrGLFinishCallbacks` 不继承任何基类,而是作为 `GrGLGpu` 的成员:

```cpp
class GrGLGpu {
    GrGLFinishCallbacks fFinishCallbacks;
};
```

**设计理念**: 回调管理是 GPU 类的一个功能组件,而非核心身份,使用组合更灵活。

### 3. 顺序处理优化

利用 OpenGL fence sync 的顺序完成特性:

```cpp
// 提前终止,避免测试所有 sync
while (!fCallbacks.empty() && fGpu->testSync(fCallbacks.front().fSync)) {
    // ...
}
```

**性能优势**: 在有大量待处理回调时,平均只需测试前几个 sync 对象。

### 4. 双路径处理

提供 `check()`(非阻塞)和 `callAll()`(阻塞)两种处理方式:

- **`check()`**: 用于异步轮询,不阻塞渲染线程
- **`callAll()`**: 用于同步等待,确保所有工作完成(析构、上下文丢失)

## 性能考量

### 1. 列表选择

使用 `std::list` 而非 `std::vector`:

- **优点**: O(1) 的头部删除操作,适合队列场景
- **缺点**: 更高的内存开销和较差的缓存局部性
- **权衡**: 由于列表通常较短(< 10 项),内存开销可接受

### 2. 提前终止优化

在 `check()` 中遇到未完成的 sync 时立即停止:

- **最好情况**: O(1) - 所有回调都未完成
- **最坏情况**: O(n) - 所有回调都已完成
- **平均情况**: O(k),k << n - 只有前几个回调完成

### 3. 计时器查询的条件执行

仅在需要时查询计时器结果:

```cpp
if (finishCallback.fCallback.receivesGpuStats()) {
    finishCallback.fCallback.setStats(stats);
}
```

**优化效果**: 避免不必要的 GPU 状态查询,可能触发驱动开销。

### 4. Sync 对象查询开销

`testSync()` 是轻量级查询,不会阻塞 CPU:

- **实现**: 通常映射到 `glGetSynciv(GL_SYNC_STATUS)`
- **开销**: 微秒级,可频繁调用

### 5. 内存占用

每个 `FinishCallback` 约占用:
- `AutoCallback`: ~32 字节(回调对象 + 引用计数)
- `GrGLsync`: 8 字节(指针)
- `GrGLint`: 4 字节
- 总计: ~44 字节 + std::list 节点开销(~16 字节)

**结论**: 即使有 100 个待处理回调,总内存开销也仅约 6KB。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/ganesh/gl/GrGLGpu.h` | 使用此类管理回调的 GPU 实现 |
| `src/gpu/RefCntedCallback.h` | 回调基类定义 |
| `include/gpu/GpuTypes.h` | GPU 统计信息类型定义 |
| `include/gpu/ganesh/gl/GrGLTypes.h` | OpenGL 类型定义 |
| `src/gpu/ganesh/GrGpu.h` | GPU 基类,定义回调接口 |
