# GrTextureResolveManager

> 源文件: src/gpu/ganesh/GrTextureResolveManager.h

## 概述

`GrTextureResolveManager` 是 Ganesh GPU 后端中的一个轻量级管理类，作为 `GrDrawingManager` 的浅层视图（shallow view）。它在渲染任务设置依赖 DAG（有向无环图）时被传递给渲染任务，为它们提供有限的功能访问，专门用于创建纹理解析渲染任务（`GrTextureResolveRenderTask`）。

该类的设计体现了"最小权限原则"：渲染任务在构建依赖关系时只能访问它们真正需要的功能（创建 mipmap 生成和 MSAA 解析任务），而不能访问 `GrDrawingManager` 的其他管理功能。

## 架构位置

`GrTextureResolveManager` 位于 Skia GPU 渲染任务管理层的访问控制组件：

```
Skia GPU 渲染任务系统
├── GrDrawingManager                          # 绘制管理器（完整功能）
│   ├── 创建各种渲染任务
│   ├── 管理任务图 (DAG)
│   └── 刷新操作
└── GrTextureResolveManager (本类)             # 受限视图
    └── newTextureResolveRenderTask()          # 只能创建解析任务
        └── 调用 GrDrawingManager::newTextureResolveRenderTaskBefore()
```

使用场景：
```
GrRenderTask (设置依赖) → GrTextureResolveManager → GrDrawingManager
                         (受限访问)              (实际执行)
```

## 主要类与结构体

### 继承关系

该类没有继承关系，是一个独立的简单包装类。

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fDrawingManager | GrDrawingManager* | 指向实际的绘制管理器 |

### 简单性特点

- 只有一个成员变量
- 只有一个公共方法
- 总代码量不到 40 行
- 纯粹的访问控制类

## 公共 API 函数

### 构造函数

```cpp
explicit GrTextureResolveManager(GrDrawingManager* drawingManager)
    : fDrawingManager(drawingManager) {}
```

**功能**：创建管理器实例，关联到绘制管理器。

**参数**：
- `drawingManager`: 底层的绘制管理器指针

**使用场景**：
- 在 `GrRenderTask` 设置依赖关系时创建
- 通常作为临时对象使用

### 创建纹理解析渲染任务

```cpp
GrTextureResolveRenderTask* newTextureResolveRenderTask(
    const GrCaps& caps) const
```

**功能**：创建新的纹理解析渲染任务。

**参数**：
- `caps`: GPU 能力对象，用于查询硬件特性

**返回值**：
- 指向新创建的 `GrTextureResolveRenderTask` 的指针

**实现**：
```cpp
SkASSERT(fDrawingManager);
return fDrawingManager->newTextureResolveRenderTaskBefore(caps);
```

**断言保护**：
- 确保 `fDrawingManager` 非空
- 调试模式下捕获错误使用

## 内部实现细节

### 构造函数实现

构造函数非常简单，只是初始化成员变量：

```cpp
explicit GrTextureResolveManager(GrDrawingManager* drawingManager)
    : fDrawingManager(drawingManager) {}
```

**设计特点**：
- 使用 `explicit` 防止隐式转换
- 浅拷贝指针（不拥有所有权）
- 无需析构函数（非所有者）

### newTextureResolveRenderTask 实现

该方法是简单的转发（forwarding）：

```cpp
GrTextureResolveRenderTask* newTextureResolveRenderTask(
    const GrCaps& caps) const {
    SkASSERT(fDrawingManager);
    return fDrawingManager->newTextureResolveRenderTaskBefore(caps);
}
```

**关键点**：
1. **断言检查**：确保管理器有效
2. **const 限定**：不修改管理器状态
3. **方法名映射**：`newTextureResolveRenderTask` → `newTextureResolveRenderTaskBefore`

**为什么使用 "Before"**：
- 创建的任务会插入到当前任务之前
- 确保依赖关系正确
- 解析任务在使用纹理的任务之前执行

### 访问控制机制

该类实现了"门面模式"（Facade Pattern）的简化版本：

```
渲染任务
   ↓ (只能看到)
GrTextureResolveManager
   ↓ (访问特定方法)
GrDrawingManager
   ↓ (执行实际操作)
创建并插入任务到 DAG
```

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|-----|---------|------|
| GrDrawingManager | 转发调用 | 实际的绘制管理器 |
| GrTextureResolveRenderTask | 创建 | 解析任务类型 |
| GrCaps | 参数类型 | GPU 能力查询 |
| SkRefCnt | 包含 | 引用计数支持 |

### 被依赖的模块

| 模块 | 使用方式 | 说明 |
|-----|---------|------|
| GrRenderTask | 使用 | 渲染任务使用管理器创建依赖 |
| GrOpsTask | 使用 | 操作任务创建 MSAA 解析 |
| GrTextureProxy | 间接使用 | 通过任务创建解析操作 |

## 设计模式与设计决策

### 最小权限原则（Principle of Least Privilege）

渲染任务只能访问它们真正需要的功能：

**限制前**：
```cpp
void GrRenderTask::setupDependencies(GrDrawingManager* manager) {
    // 可以访问 GrDrawingManager 的所有功能
    manager->addTask(...);              // 不应允许
    manager->flush();                   // 不应允许
    manager->newTextureResolveTask();   // 应允许
}
```

**限制后**：
```cpp
void GrRenderTask::setupDependencies(
    GrTextureResolveManager resolveManager) {
    // 只能访问解析相关功能
    resolveManager.newTextureResolveRenderTask(caps);  // 可以
    // resolveManager.flush();                         // 编译错误
}
```

### 轻量级代理模式（Lightweight Proxy Pattern）

`GrTextureResolveManager` 是 `GrDrawingManager` 的轻量级代理：
- 不持有所有权（原始指针）
- 不增加引用计数
- 按值传递，栈分配
- 零运行时开销

### 按值传递策略

该类设计为按值传递：
```cpp
void setupDependencies(GrTextureResolveManager manager);
// 而非：
void setupDependencies(GrTextureResolveManager* manager);
```

**优势**：
- 语法更简洁
- 无需空指针检查
- 编译器可优化

### 临时对象模式

预期使用模式：
```cpp
// 在 GrDrawingManager 中
void setupTaskDependencies(GrRenderTask* task) {
    task->setupDependencies(GrTextureResolveManager(this));
    // 临时对象，调用结束即销毁
}
```

不持久化管理器对象。

### 单一职责原则

该类只负责一件事：提供创建解析任务的接口。
- 不管理任务生命周期
- 不调度任务执行
- 不管理资源

## 性能考量

### 零开销抽象

- 类大小：单个指针（8 字节）
- 构造成本：单次指针拷贝
- 方法调用：可内联，无虚函数开销
- 内存分配：栈分配，无堆操作

### 编译器优化

由于类非常简单，编译器可以：
1. **内联所有方法调用**
2. **优化掉临时对象**
3. **直接展开为底层调用**

优化后效果：
```cpp
// 源代码
manager.newTextureResolveRenderTask(caps);

// 优化后（概念上）
fDrawingManager->newTextureResolveRenderTaskBefore(caps);
```

### 短生命周期

临时对象使用模式：
- 创建快速（指针赋值）
- 销毁快速（无操作）
- 无需内存管理

### 断言成本

```cpp
SkASSERT(fDrawingManager);
```

- 仅在调试构建中生效
- 发布构建编译掉
- 零运行时开销（发布版）

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/gpu/ganesh/GrDrawingManager.h | 包含 | 绘制管理器定义（核心依赖） |
| src/gpu/ganesh/GrTextureResolveRenderTask.h | 前向声明 | 解析任务类型 |
| src/gpu/ganesh/GrRenderTask.h | 使用者 | 渲染任务使用该管理器 |
| src/gpu/ganesh/GrCaps.h | 参数类型 | GPU 能力类 |
| include/core/SkRefCnt.h | 包含 | 引用计数基础设施 |

## 使用示例

### 典型使用场景

```cpp
// 在 GrOpsTask 中设置依赖
void GrOpsTask::setupDependencies(
    GrTextureResolveManager resolveManager,
    const GrCaps& caps) {

    // 创建 MSAA 解析任务
    GrTextureResolveRenderTask* resolveTask =
        resolveManager.newTextureResolveRenderTask(caps);

    // 添加代理到解析任务
    resolveTask->addProxy(drawingManager,
                         std::move(proxy),
                         GrSurfaceProxy::ResolveFlags::kMSAA,
                         caps);
}
```

### 与 GrDrawingManager 交互

```cpp
// 在 GrDrawingManager 内部
void GrDrawingManager::setupRenderTaskDependencies() {
    for (auto& task : fDAG) {
        // 创建受限视图
        GrTextureResolveManager resolveManager(this);

        // 传递给任务
        task->setupDependencies(resolveManager, *fContext->caps());
    }
}
```
