# GrCpuBuffer

> 源文件
> - src/gpu/ganesh/GrCpuBuffer.h

## 概述

`GrCpuBuffer` 是 Ganesh GPU 后端中表示 CPU 端缓冲区的类。与 GPU 缓冲区不同，该类管理的是主机内存中的缓冲区，通常用于临时存储、数据准备或作为 GPU 缓冲区的备份。它实现了 `GrBuffer` 接口，允许在需要缓冲区抽象但不需要 GPU 分配的场景中使用。

该类的关键特性是使用自定义内存分配策略：缓冲区数据紧跟在对象本身之后分配，从而减少内存碎片和分配次数。这种"placement new"技术在性能敏感的代码中很常见。

## 架构位置

在 Skia 的 Ganesh GPU 渲染架构中，`GrCpuBuffer` 位于缓冲区层次结构的一个分支：

```
GrBuffer (抽象缓冲区接口)
    ├── GrGpuBuffer (GPU 端缓冲区)
    └── GrCpuBuffer (CPU 端缓冲区)
```

该类实现了与 `GrGpuBuffer` 相同的接口，但内存位于主机而非设备。

## 主要类与结构体

### GrCpuBuffer

该类是 CPU 端缓冲区的完整实现。

**继承关系：**
```
GrNonAtomicRef<GrCpuBuffer> (非原子引用计数)
GrBuffer (缓冲区基类)
    └── GrCpuBuffer (派生类)
```

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fData` | `void*` | 指向缓冲区数据的指针，指向对象后的连续内存 |
| `fSize` | `size_t` | 缓冲区的大小（字节） |

## 公共 API 函数

### 工厂方法

```cpp
static sk_sp<GrCpuBuffer> Make(size_t size);
```

**功能：** 创建一个指定大小的 CPU 缓冲区。

**参数：**
- `size`: 缓冲区大小（字节），必须大于 0

**实现细节：**
该方法使用特殊的内存分配策略：
1. 计算总内存大小：`sizeof(GrCpuBuffer) + size`
2. 使用 `operator new` 分配连续内存
3. 使用 placement new 在分配的内存上构造对象
4. 数据指针指向对象后的内存区域

```cpp
auto mem = ::operator new(combinedSize);
return sk_sp<GrCpuBuffer>(new (mem) GrCpuBuffer((char*)mem + sizeof(GrCpuBuffer), size));
```

如果大小计算溢出（通过 `SkSafeMath` 检测），函数会终止程序（`SK_ABORT`）。

### 自定义删除运算符

```cpp
static void operator delete(void* p);
```

**功能：** 释放 `Make()` 分配的内存。

由于对象和数据在同一个内存块中，删除运算符只需调用标准的 `operator delete` 释放整个块。

**注释：** 代码注释提到一旦 P0722R3（sized delete）可用，应该使用 sized delete 以提高性能。

### 引用计数

```cpp
void ref() const override;
void unref() const override;
```

**功能：** 实现引用计数接口。

这些方法委托给 `GrNonAtomicRef<GrCpuBuffer>` 的实现。使用非原子引用计数是因为 CPU 缓冲区通常在单线程环境中使用。

### 大小查询

```cpp
size_t size() const override;
```

**功能：** 返回缓冲区的大小（字节）。

### 类型识别

```cpp
bool isCpuBuffer() const override;
```

**功能：** 返回 `true`，表示这是一个 CPU 缓冲区。

这允许运行时类型识别而无需 RTTI（运行时类型信息）。

### 数据访问

```cpp
char* data();
const char* data() const;
```

**功能：** 提供对缓冲区数据的直接访问。

返回指向缓冲区内存的指针，允许读取和写入（非 const 版本）。

## 内部实现细节

### 自定义内存布局

`GrCpuBuffer` 使用特殊的内存布局：

```
+-------------------+-------------------+
| GrCpuBuffer object | Buffer data       |
| (固定大小)         | (可变大小)         |
+-------------------+-------------------+
^                   ^
|                   |
mem                 fData
```

这种布局的优势：
- 单次分配，减少堆管理开销
- 数据局部性更好，可能改善缓存性能
- 避免了对象和数据分离可能导致的碎片

### 私有构造函数

```cpp
GrCpuBuffer(void* data, size_t size) : fData(data), fSize(size) {}
```

构造函数是私有的，只能通过 `Make()` 工厂方法创建对象。这确保了正确的内存分配策略。

### 安全数学检查

`Make()` 方法使用 `SkSafeMath` 检测溢出：

```cpp
SkSafeMath sm;
size_t combinedSize = sm.add(sizeof(GrCpuBuffer), size);
if (!sm.ok()) {
    SK_ABORT("Buffer size is too big.");
}
```

这防止了在极端大小情况下的内存分配错误。

### 非原子引用计数

该类继承 `GrNonAtomicRef<GrCpuBuffer>` 而非标准的原子引用计数。这是一个性能优化，假设 CPU 缓冲区不会跨线程共享。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrBuffer` | 抽象缓冲区基类 |
| `GrNonAtomicRef` | 非原子引用计数实现 |
| `SkRefCnt` | 引用计数基础设施 |
| `SkSafeMath` | 安全的算术运算，防止溢出 |
| `SkAssert` | 断言宏 |

### 被依赖的模块

`GrCpuBuffer` 被以下组件使用：

| 模块 | 使用方式 |
|------|---------|
| `GrBufferAllocPool` | 缓冲区池可能使用 CPU 缓冲区作为临时存储 |
| 数据准备代码 | 在上传到 GPU 前准备数据 |
| 测试代码 | 作为 GPU 缓冲区的轻量级替代品 |

## 设计模式与设计决策

### 工厂方法模式

使用静态 `Make()` 方法而非公共构造函数：
- 允许复杂的初始化逻辑
- 返回智能指针，明确所有权
- 支持分配失败时的错误处理（虽然此处使用 abort）

### Placement New

使用 placement new 技术在预分配的内存上构造对象：
```cpp
new (mem) GrCpuBuffer(...)
```

这是一种高级 C++ 技术，允许精确控制对象的内存位置。

### 自定义内存管理

通过将对象和数据放在连续内存中，该类实现了一种优化的内存布局。这类似于"柔性数组成员"（flexible array member）模式，但更安全。

### 接口隔离

`isCpuBuffer()` 方法提供类型识别，避免使用 C++ RTTI。这在性能敏感的代码中很常见，因为 RTTI 有额外开销。

### 非原子优化

使用非原子引用计数是基于使用模式的性能优化。如果未来需要线程安全，可以切换到原子版本。

## 性能考量

### 单次分配

将对象和数据放在同一内存块中意味着：
- 只需一次 `new` 调用（相比两次）
- 减少堆管理开销
- 更少的内存碎片

### 缓存局部性

连续的内存布局提高了缓存局部性，因为访问对象元数据后立即访问数据时，数据可能已在缓存中。

### 非原子引用计数

非原子操作比原子操作快得多（避免了内存屏障），适用于单线程场景。

### 直接内存访问

`data()` 方法提供原始指针，允许直接内存访问而无额外抽象层，这对性能敏感的数据操作很重要。

### Sized Delete 潜力

代码注释提到未来可以使用 sized delete（P0722R3），这将允许更高效的内存释放，因为分配器知道块的大小。

### 溢出检查开销

`SkSafeMath` 的溢出检查有轻微开销，但这是必要的安全措施，且只在创建时执行一次。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrBuffer.h` | 基类 | 抽象缓冲区接口 |
| `src/gpu/ganesh/GrNonAtomicRef.h` | 引用计数 | 非原子引用计数实现 |
| `src/base/SkSafeMath.h` | 工具 | 安全的算术运算 |
| `include/core/SkRefCnt.h` | 基础 | 引用计数基础类型 |
| `src/gpu/ganesh/GrGpuBuffer.h` | 相关类 | GPU 端缓冲区实现 |
| `src/gpu/ganesh/GrBufferAllocPool.h` | 使用者 | 缓冲区池管理 |
