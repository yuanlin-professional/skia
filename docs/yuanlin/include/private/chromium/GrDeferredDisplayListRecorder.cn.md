# GrDeferredDisplayListRecorder

> 源文件: `include/private/chromium/GrDeferredDisplayListRecorder.h`

## 概述

GrDeferredDisplayListRecorder 是 Ganesh 延迟显示列表系统的录制器类，负责将绘制命令录制为 GrDeferredDisplayList 对象。它提供了线程安全的命令录制能力，允许在 CPU 线程上预先执行所有渲染准备工作，而无需访问 GPU，是 Chromium 实现多线程渲染的核心工具。

## 架构位置

本类位于 Skia 的 Ganesh GPU 后端子系统，专为 Chromium 的 DDL（Deferred Display List）架构设计。它在渲染流水线中充当命令捕获的角色，位于应用层绘制代码和 GrDeferredDisplayList 之间。

## 主要类与结构体

### GrDeferredDisplayListRecorder

延迟显示列表录制器类，提供栈上使用的值语义。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fCharacterization | const GrSurfaceCharacterization | 表面特性描述（不可变） |
| fContext | sk_sp&lt;GrRecordingContext&gt; | 录制上下文 |
| fTargetProxy | sk_sp&lt;GrRenderTargetProxy&gt; | 目标渲染代理 |
| fLazyProxyData | sk_sp&lt;GrDeferredDisplayList::LazyProxyData&gt; | 延迟代理数据 |
| fSurface | sk_sp&lt;SkSurface&gt; | 内部表面对象 |

## 公共 API 函数

### 构造函数

```cpp
explicit GrDeferredDisplayListRecorder(const GrSurfaceCharacterization&)
```

- **功能**: 创建 DDL 录制器
- **参数**: `GrSurfaceCharacterization` - 表示预期的 GPU 后端目标 SkSurface 的表面特性
- **用途**: 在栈上创建录制器对象
- **注意**: 构造函数调用内部 `init()` 方法进行初始化

### 析构函数

```cpp
~GrDeferredDisplayListRecorder()
```

- **功能**: 销毁录制器
- **副作用**: 如果未调用 `detach()`，录制的命令将被丢弃

### `characterization()`

```cpp
const GrSurfaceCharacterization& characterization() const
```

- **功能**: 获取录制器关联的表面特性
- **返回值**: 表面特性的常量引用
- **用途**: 验证目标表面兼容性

### `getCanvas()`

```cpp
SkCanvas* getCanvas()
```

- **功能**: 获取用于录制绘制命令的画布
- **返回值**: SkCanvas 指针（所有权不转移）
- **注意**: 调用 `detach()` 后，此方法将返回 nullptr，画布将失效
- **用途**: 在此画布上执行所有绘制操作

### `detach()`

```cpp
sk_sp<GrDeferredDisplayList> detach()
```

- **功能**: 分离并返回录制的延迟显示列表
- **返回值**: 包含所有录制命令的 GrDeferredDisplayList 智能指针
- **副作用**:
  - 后续调用 `getCanvas()` 将返回 nullptr
  - 录制器对象仍然有效但不可再使用
- **用途**: 完成录制后获取 DDL 对象用于后续回放

## 内部实现细节

### 初始化流程

构造函数调用私有的 `init()` 方法，该方法：

1. 创建 GrRecordingContext
2. 分配 GrRenderTargetProxy
3. 创建延迟代理数据 (LazyProxyData)
4. 构建内部 SkSurface

如果初始化失败，`getCanvas()` 将返回 nullptr。

### 表面特性约束

`fCharacterization` 在构造时设置，整个生命周期内保持不可变，确保录制的命令与预期的目标表面兼容。

### 录制上下文

`fContext` 是一个 GrRecordingContext（而非 GrDirectContext），这是关键设计：
- GrRecordingContext 不允许直接访问 GPU
- 所有操作都是纯 CPU 侧的
- 保证了线程安全性

### 延迟代理机制

`fLazyProxyData` 在录制时创建，在 DDL 回放时被填充：
- 录制阶段：代理指向虚拟目标
- 回放阶段：代理被解析为真实的渲染目标

这种机制允许录制和回放解耦。

### 内部表面

`fSurface` 是一个内部 SkSurface，提供了画布接口：
- 通过 `getCanvas()` 暴露其画布
- 在 `detach()` 时，其内容被提取为 DDL

### 不可拷贝设计

显式删除了拷贝构造函数和拷贝赋值运算符：

```cpp
GrDeferredDisplayListRecorder(const GrDeferredDisplayListRecorder&) = delete;
GrDeferredDisplayListRecorder& operator=(const GrDeferredDisplayListRecorder&) = delete;
```

这确保了录制器的唯一所有权语义。

## 典型使用模式

```cpp
// 1. 获取目标表面的特性
GrSurfaceCharacterization characterization;
surface->characterize(&characterization);

// 2. 在栈上创建录制器
GrDeferredDisplayListRecorder recorder(characterization);

// 3. 获取画布并绘制
SkCanvas* canvas = recorder.getCanvas();
canvas->drawRect(...);
canvas->drawText(...);

// 4. 分离 DDL
sk_sp<GrDeferredDisplayList> ddl = recorder.detach();

// 5. 后续在任意时间/线程回放
skgpu::ganesh::DrawDDL(surface, ddl);
```

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkRefCnt | 智能指针基类 |
| GrDeferredDisplayList | DDL 对象定义 |
| GrSurfaceCharacterization | 表面特性描述 |
| GrRecordingContext | 录制上下文 |
| GrRenderTargetProxy | 渲染目标代理 |
| SkCanvas | 画布接口 |
| SkSurface | 表面对象 |

### 被依赖的模块

- Chromium 渲染进程：使用录制器捕获绘制命令
- Skia 应用程序：利用 DDL 进行多线程渲染
- 性能测试工具：用于预录制基准测试场景

## 设计模式与设计决策

### 建造者模式变体

录制器充当建造者角色，逐步构建 DDL 对象，`detach()` 返回最终产品。

### RAII 资源管理

通过栈上使用和智能指针，确保资源自动释放，但 DDL 需要显式 `detach()` 获取。

### 单一职责原则

录制器只负责命令录制，不涉及回放、编译或 GPU 交互，职责清晰。

### 接口隔离

通过 `getCanvas()` 提供标准 SkCanvas 接口，用户无需了解 DDL 内部细节。

### 不可变特性保证

`fCharacterization` 的 const 声明确保录制过程中目标特性不被修改。

## 性能考量

### 零 GPU 访问

所有操作都在 CPU 侧完成，不触发 GPU 命令提交，允许：
- 在后台线程录制
- 避免 GPU 同步开销
- 提高 CPU-GPU 并行度

### 延迟编译

着色器编译可以推迟到回放时或使用 `ProgramIterator` 预编译，避免阻塞录制线程。

### 内存复用

内部使用内存池（arenas）分配临时对象，减少堆分配碎片。

### 轻量级对象

录制器本身是轻量级的，适合在栈上创建和销毁。

### 无虚函数开销

类未使用虚函数，减少了函数调用开销。

## 线程安全说明

### 线程安全保证

录制器本身是线程安全的：
- 不访问共享的 GPU 状态
- 每个录制器拥有独立的 GrRecordingContext
- 可以在任意线程上创建和使用

### 并行录制

多个录制器可以并发工作：
```cpp
// 线程 1
GrDeferredDisplayListRecorder recorder1(char1);
recorder1.getCanvas()->draw...

// 线程 2
GrDeferredDisplayListRecorder recorder2(char2);
recorder2.getCanvas()->draw...
```

### 回放约束

DDL 的回放必须在拥有 GrDirectContext 的线程上执行（通常是 GPU 线程）。

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/private/chromium/GrDeferredDisplayList.h` | DDL 对象定义 |
| `include/private/chromium/GrSurfaceCharacterization.h` | 表面特性描述 |
| `include/gpu/ganesh/GrRecordingContext.h` | 录制上下文 |
| `include/core/SkCanvas.h` | 画布接口 |
| `include/core/SkSurface.h` | 表面对象 |
| `src/gpu/ganesh/GrRenderTargetProxy.h` | 渲染目标代理 |
| `src/gpu/ganesh/GrDrawingManager.h` | 绘制管理器 |
