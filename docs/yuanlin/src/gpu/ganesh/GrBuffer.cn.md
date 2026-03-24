# GrBuffer

> 源文件
> - src/gpu/ganesh/GrBuffer.h

## 概述

`GrBuffer` 是 Ganesh GPU 后端中缓冲区对象的抽象基类，为 GPU 缓冲区（`GrGpuBuffer`）和客户端数组（`GrCpuBuffer`）提供统一的接口。该类定义了缓冲区的基本操作和属性，使上层代码能够以统一的方式处理不同类型的缓冲区。

这是一个非常轻量级的接口类，仅定义了最核心的虚函数，具体的缓冲区管理、映射、更新等功能由子类实现。

## 架构位置

`GrBuffer` 位于 Skia 图形库的架构中：

- **模块**: Ganesh GPU 后端
- **层级**: 资源抽象层（Resource Abstraction Layer）
- **继承关系**: `GrBuffer` (基类) -> `GrGpuBuffer` / `GrCpuBuffer` (子类)
- **协作对象**: 与 `GrBufferAllocPool`、`GrResourceProvider`、`GrGpu` 协作

该类是 Ganesh 资源系统中的基础抽象，允许 CPU 和 GPU 缓冲区的多态使用。

## 主要类与结构体

### GrBuffer（抽象基类）

继承关系：
```
GrBuffer (抽象基类)
  ├── GrGpuBuffer (GPU 端缓冲区)
  └── GrCpuBuffer (CPU 端缓冲区)
```

关键成员变量：无（纯接口类）

## 公共 API 函数

### 生命周期管理

#### ref()

```cpp
virtual void ref() const = 0;
```

**功能**: 增加引用计数。

**说明**: 虚函数设计允许子类使用不同的引用计数基类。

#### unref()

```cpp
virtual void unref() const = 0;
```

**功能**: 减少引用计数，可能触发对象销毁。

**说明**: 与 `ref()` 配对使用，支持智能指针（`sk_sp`）管理。

### 属性查询

#### size()

```cpp
virtual size_t size() const = 0;
```

**功能**: 返回缓冲区的大小（字节数）。

**返回值**: 缓冲区的字节大小

**使用场景**:
- 验证偏移量和大小参数
- 计算对齐和填充
- 统计内存使用

#### isCpuBuffer()

```cpp
virtual bool isCpuBuffer() const = 0;
```

**功能**: 判断缓冲区是否为 CPU 缓冲区。

**返回值**:
- `true`: `GrCpuBuffer` 实例
- `false`: `GrGpuBuffer` 实例

**使用场景**: 运行时类型判断，决定访问策略

### 析构函数

```cpp
virtual ~GrBuffer() = default;
```

虚析构函数确保通过基类指针删除子类对象时能正确调用子类析构函数。

### 禁用复制

```cpp
GrBuffer(const GrBuffer&) = delete;
GrBuffer& operator=(const GrBuffer&) = delete;
```

缓冲区对象不可复制，只能通过引用计数共享。

## 内部实现细节

### 为何虚化 ref() 和 unref()

不同的缓冲区类型继承自不同的引用计数基类：
- `GrGpuBuffer` 继承自 `GrGpuResource`（使用 `GrResourceCache`）
- `GrCpuBuffer` 继承自 `GrRefCnt`（简单引用计数）

通过虚化 `ref()` 和 `unref()`，基类指针可以正确调用子类的引用计数方法，使 `sk_sp<GrBuffer>` 能够统一管理两种类型的缓冲区。

### 纯接口设计

`GrBuffer` 不包含任何数据成员，仅定义纯虚函数。这种设计：
- 零内存开销（除虚表指针）
- 最大灵活性
- 强制子类实现所有必需功能

### 多态使用示例

```cpp
void processBuffer(const GrBuffer* buffer) {
    if (buffer->isCpuBuffer()) {
        auto cpuBuffer = static_cast<const GrCpuBuffer*>(buffer);
        // 直接访问 CPU 内存
    } else {
        auto gpuBuffer = static_cast<const GrGpuBuffer*>(buffer);
        // 通过 GPU API 访问
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrTypes.h` | GPU 类型定义 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGpuBuffer` | GPU 端缓冲区实现 |
| `GrCpuBuffer` | CPU 端缓冲区实现 |
| `GrBufferAllocPool` | 缓冲区分配池 |
| `GrResourceProvider` | 资源创建 |
| `GrMeshDrawOp` | 使用缓冲区进行绘制 |

## 设计模式与设计决策

### 1. 接口隔离原则

`GrBuffer` 只定义最核心的接口，不包含任何实现细节。

### 2. 策略模式

不同类型的缓冲区（CPU vs GPU）使用不同的内存管理和访问策略。

### 3. 模板方法模式（间接应用）

子类实现基类定义的虚函数，但没有调用顺序约束。

### 4. 虚析构函数模式

确保多态删除的正确性。

### 5. 禁止复制模式

通过删除复制构造和赋值操作符，强制引用计数管理。

### 6. 最小接口原则

只暴露绝对必要的接口，保持基类轻量。

## 性能考量

### 1. 虚函数开销

- 每个对象一个虚表指针（8 字节）
- 虚函数调用轻微开销（通常可预测分支）

### 2. 类型判断优化

`isCpuBuffer()` 是虚函数，但通常会被内联或分支预测优化。

### 3. 零数据成员

基类无数据成员，子类布局紧凑。

### 4. 引用计数友好

虚化的 `ref()/unref()` 允许高效的智能指针管理。

### 5. 缓存友好

轻量级基类减少了对象大小，提高缓存命中率。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/gpu/ganesh/GrGpuBuffer.h` | GPU 缓冲区子类 |
| `src/gpu/ganesh/GrCpuBuffer.h` | CPU 缓冲区子类 |
| `src/gpu/ganesh/GrBufferAllocPool.h` | 缓冲区分配池 |
| `src/gpu/ganesh/GrResourceProvider.h` | 资源创建接口 |
| `include/gpu/ganesh/GrTypes.h` | GPU 类型定义 |
| `include/core/SkRefCnt.h` | 引用计数基类 |
| `src/gpu/ganesh/GrGpuResource.h` | GPU 资源基类 |
