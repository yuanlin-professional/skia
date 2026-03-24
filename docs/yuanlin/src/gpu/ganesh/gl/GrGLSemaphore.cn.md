# GrGLSemaphore

> 源文件
> - src/gpu/ganesh/gl/GrGLSemaphore.h
> - src/gpu/ganesh/gl/GrGLSemaphore.cpp

## 概述

`GrGLSemaphore` 是 Skia Ganesh OpenGL 后端中表示同步信号量的类。它继承自 `GrSemaphore`，封装了 OpenGL 的 `GLsync` 对象，用于 GPU 命令流的同步操作。该类管理 `glFenceSync` 创建的同步对象的生命周期，并区分拥有和借用的同步对象。

该类的实现非常简洁，主要职责是持有 `GLsync` 对象的句柄，并在析构时根据所有权决定是否删除该对象。它是 Skia 跨 API 同步机制的一部分，但在 OpenGL 上主要用于内部同步，不直接暴露给外部应用。

## 架构位置

```
GrSemaphore (抽象基类)
    ├── GrGLSemaphore (GL实现)
    ├── GrVkSemaphore (Vulkan实现)
    └── GrMtlSemaphore (Metal实现)

使用场景:
GrGLGpu -> GrGLSemaphore (GLsync) -> GPU同步
```

该类位于 Ganesh 同步抽象层的 OpenGL 实现，用于跨命令流的同步。

## 主要类与结构体

### GrGLSemaphore

**继承关系:**
- 继承自: `GrSemaphore`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fGpu` | `GrGLGpu*` | 指向 GL GPU 对象的指针 |
| `fSync` | `GrGLsync` | OpenGL 同步对象句柄 |
| `fIsOwned` | `bool` | 是否拥有同步对象 |

## 公共 API 函数

### 工厂方法
- `static std::unique_ptr<GrGLSemaphore> Make(GrGLGpu* gpu, bool isOwned)` - 创建信号量对象

### 访问器
- `GrGLsync sync() const` - 获取 GLsync 句柄
- `void setSync(const GrGLsync& sync)` - 设置 GLsync 句柄

### 后端接口
- `GrBackendSemaphore backendSemaphore() const` - 获取后端信号量（未实现）

### 析构
- `~GrGLSemaphore()` - 析构函数，删除拥有的同步对象

## 内部实现细节

### 构造函数

```cpp
GrGLSemaphore::GrGLSemaphore(GrGLGpu* gpu, bool isOwned)
        : fGpu(gpu), fSync(nullptr), fIsOwned(isOwned) {
}
```

**特点**:
- 初始时 `fSync` 为 `nullptr`
- 需要后续调用 `setSync()` 设置实际的同步对象

### 析构函数

```cpp
GrGLSemaphore::~GrGLSemaphore() {
    if (fSync && fIsOwned) {
        fGpu->deleteSync(fSync);  // 仅删除拥有的对象
    }
}
```

**逻辑**:
- 如果拥有同步对象（`fIsOwned == true`），则删除
- 如果仅借用（`fIsOwned == false`），则不删除

### 所有权设置

```cpp
void setIsOwned() override {
    fIsOwned = true;
}
```

允许将借用的对象转换为拥有。

### 后端信号量获取（未实现）

```cpp
GrBackendSemaphore backendSemaphore() const override {
    SK_ABORT("Unsupported");
}
```

**原因**:
- OpenGL 的 `GLsync` 不能跨上下文共享
- 不适合作为公共后端信号量

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLGpu` | 删除同步对象 |
| `GrSemaphore` | 基类接口 |
| `GrBackendSemaphore` | 后端信号量类型 |
| `GrGLTypes` | `GrGLsync` 类型定义 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrGLGpu` | 创建和管理信号量 |

## 设计模式与设计决策

### 1. 工厂方法模式

使用静态工厂方法创建对象：

```cpp
static std::unique_ptr<GrGLSemaphore> Make(GrGLGpu* gpu, bool isOwned) {
    return std::unique_ptr<GrGLSemaphore>(new GrGLSemaphore(gpu, isOwned));
}
```

**优势**:
- 封装构造细节
- 返回智能指针，明确所有权
- 私有构造函数防止直接实例化

### 2. RAII（资源获取即初始化）

析构时自动清理：

```cpp
~GrGLSemaphore() {
    if (fSync && fIsOwned) {
        fGpu->deleteSync(fSync);
    }
}
```

**优势**: 无需手动管理生命周期

### 3. 延迟初始化

构造时不创建 `GLsync`，需要后续设置：

```cpp
GrGLSemaphore(...) : fSync(nullptr) { }
void setSync(const GrGLsync& sync) { fSync = sync; }
```

**原因**:
- 创建和设置可能在不同时机
- 允许重用信号量对象

### 4. 所有权语义

明确区分拥有和借用：

```cpp
bool fIsOwned;  // true: 析构时删除, false: 不删除
```

## 性能考量

### 1. 轻量级对象

```cpp
sizeof(GrGLSemaphore) ≈ 16-24 字节
```

非常轻量，适合频繁创建。

### 2. 无虚函数开销（除继承）

除了来自基类的虚函数，没有额外的虚函数。

### 3. 直接指针访问

```cpp
GrGLGpu* fGpu;  // 直接指针，无引用计数开销
```

## 使用场景

### 1. GPU 命令同步

```cpp
// 插入栅栏
auto semaphore = GrGLSemaphore::Make(gpu, true);
GrGLsync sync = gpu->insertFence();
semaphore->setSync(sync);

// 等待
gpu->waitForSync(semaphore->sync());
```

### 2. 跨表面同步

```cpp
// 表面 A 渲染完成
auto semaphore = createSemaphore();
surfaceA->flush(semaphore);

// 表面 B 等待
surfaceB->wait(semaphore);
```

### 3. CPU-GPU 同步

```cpp
// GPU 工作完成后通知 CPU
auto semaphore = createSemaphore();
gpu->insertSemaphore(semaphore);

// CPU 等待
if (gpu->checkSemaphore(semaphore)) {
    // 工作完成
}
```

## OpenGL 同步机制

### glFenceSync

```cpp
// 在 GPU 命令流中插入栅栏
GLsync sync = glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE, 0);

// 检查状态
GLenum result = glClientWaitSync(sync, GL_SYNC_FLUSH_COMMANDS_BIT, timeout);

// 删除
glDeleteSync(sync);
```

`GrGLSemaphore` 封装了这个流程。

## 限制

### 1. 不支持跨上下文

OpenGL 的 `GLsync` 不能跨上下文共享：

```cpp
GrBackendSemaphore backendSemaphore() const override {
    SK_ABORT("Unsupported");  // 无法导出
}
```

### 2. 不支持跨 API

不能与 Vulkan、Metal 等 API 互操作。

### 3. 仅限内部使用

主要用于 Skia 内部同步，不推荐应用程序直接使用。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrSemaphore.h` | 基类 | 信号量抽象 |
| `src/gpu/ganesh/gl/GrGLGpu.h` | 使用者 | GPU 接口 |
| `include/gpu/ganesh/GrBackendSemaphore.h` | 依赖 | 后端信号量类型 |
| `include/gpu/ganesh/gl/GrGLTypes.h` | 依赖 | `GrGLsync` 类型 |

## 总结

`GrGLSemaphore` 是一个简洁的同步原语封装类，提供了 OpenGL `GLsync` 对象的生命周期管理。虽然功能有限（不支持跨上下文、跨 API），但在 Skia 内部的 GPU 命令同步中发挥重要作用。其设计遵循 RAII 原则，使用智能指针管理所有权，确保资源正确释放。
