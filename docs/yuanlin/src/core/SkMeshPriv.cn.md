# SkMeshPriv

> 源文件: src/core/SkMeshPriv.h

## 概述

`SkMeshPriv` 是 Skia 中为 Mesh API 提供内部访问和实现支持的私有头文件。它包含两个主要部分：

1. **`SkMeshSpecificationPriv`**：提供对公共 `SkMeshSpecification` 类私有成员的访问接口，允许内部代码获取着色器程序、varying 变量、颜色信息等细节
2. **`SkMeshPriv` 命名空间**：定义 Mesh 的顶点缓冲区和索引缓冲区的内部实现，包括 CPU 端缓冲区的具体实现

该文件是 Skia Mesh 系统的基础设施，为渲染后端（如 Ganesh、Graphite）提供统一的缓冲区抽象和规格访问接口。

## 架构位置

`SkMeshPriv` 位于 Skia 的 Mesh 渲染子系统中，处于以下架构层次：

- **公共 API 层**：`SkMesh`、`SkMeshSpecification`（`include/core/SkMesh.h`）
- **内部访问层**：`SkMeshPriv`、`SkMeshSpecificationPriv`（本文件）
- **后端实现层**：Ganesh/Graphite 的 Mesh 渲染器

在渲染流程中，公共 API 创建 Mesh 对象，内部代码通过 `SkMeshPriv` 访问规格细节和缓冲区数据，后端渲染器根据这些信息生成 GPU 绘制指令。

## 主要类与结构体

### SkMeshSpecificationPriv

工具类，提供静态方法访问 `SkMeshSpecification` 的私有成员：

| **特性** | **说明** |
|---------|---------|
| **类型** | 工具类，只包含静态方法 |
| **访问权限** | 访问公共类的私有成员（友元关系或直接访问） |

**类型别名：**

```cpp
using Varying   = SkMeshSpecification::Varying;
using Attribute = SkMeshSpecification::Attribute;
using ColorType = SkMeshSpecification::ColorType;
```

### SkMeshPriv::Buffer

抽象基类，定义 Mesh 缓冲区的接口：

| **特性** | **说明** |
|---------|---------|
| **继承关系** | 纯虚基类 |
| **派生类** | `IB`（索引缓冲区）、`VB`（顶点缓冲区） |

**关键成员变量**：无（纯接口类）

**关键虚函数**：

| **方法** | **说明** |
|---------|---------|
| `virtual ~Buffer() = 0` | 纯虚析构函数，强制抽象 |
| `virtual const void* peek() const` | 返回缓冲区数据指针（默认 `nullptr`） |
| `virtual bool isGaneshBacked() const` | 是否为 Ganesh GPU 缓冲区（默认 `false`） |

### SkMeshPriv::IB / VB

类型别名，继承自 `Buffer` 并实现对应的公共接口：

```cpp
class IB : public Buffer, public SkMesh::IndexBuffer  {};
class VB : public Buffer, public SkMesh::VertexBuffer {};
```

### SkMeshPriv::CpuBuffer<Base>

模板类，CPU 端缓冲区的具体实现：

| **特性** | **说明** |
|---------|---------|
| **模板参数** | `Base`：`IB` 或 `VB` |
| **数据存储** | 使用 `sk_sp<SkData>` 管理内存 |

**关键成员变量**：

| **成员变量** | **类型** | **说明** |
|------------|---------|---------|
| `fData` | `sk_sp<SkData>` | 智能指针，持有缓冲区数据 |

**类型别名**：

```cpp
using CpuIndexBuffer  = CpuBuffer<IB>;
using CpuVertexBuffer = CpuBuffer<VB>;
```

## 公共 API 函数

### SkMeshSpecificationPriv 静态方法

#### 访问 Varying 信息

```cpp
static SkSpan<const Varying> Varyings(const SkMeshSpecification& spec);
static int PassthroughLocalCoordsVaryingIndex(const SkMeshSpecification& spec);
static bool VaryingIsDead(const SkMeshSpecification& spec, int v);
```

- **`Varyings`**：获取所有 varying 变量的列表
- **`PassthroughLocalCoordsVaryingIndex`**：获取直通本地坐标的 varying 索引
- **`VaryingIsDead`**：判断指定 varying 是否未被使用（死代码消除）

#### 访问着色器程序

```cpp
static const SkSL::Program* VS(const SkMeshSpecification& spec);
static const SkSL::Program* FS(const SkMeshSpecification& spec);
```

返回顶点着色器和片段着色器的编译后程序对象。

#### 访问元信息

```cpp
static int Hash(const SkMeshSpecification& spec);
static ColorType GetColorType(const SkMeshSpecification& spec);
static bool HasColors(const SkMeshSpecification& spec);
static SkColorSpace* ColorSpace(const SkMeshSpecification& spec);
static SkAlphaType AlphaType(const SkMeshSpecification& spec);
```

提供规格的哈希值、颜色类型、颜色空间和 alpha 类型信息。

#### 类型转换

```cpp
static SkSLType VaryingTypeAsSLType(Varying::Type type);
static SkSLType AttrTypeAsSLType(Attribute::Type type);
```

将 Mesh API 的类型枚举转换为 SkSL 的类型枚举。

### SkMeshPriv::Buffer 接口

```cpp
virtual const void* peek() const;
virtual bool isGaneshBacked() const;
```

子类可选实现这些方法以提供缓冲区数据访问和后端类型查询。

### SkMeshPriv::CpuBuffer<Base> 方法

#### 工厂方法

```cpp
static sk_sp<Base> Make(const void* data, size_t size);
```

创建 CPU 缓冲区：

- 如果提供 `data`，拷贝数据到新分配的内存
- 如果 `data` 为 `nullptr`，分配零初始化的内存

#### 访问方法

```cpp
const void* peek() const override;
size_t size() const override;
```

- **`peek()`**：返回缓冲区数据指针
- **`size()`**：返回缓冲区大小（字节）

#### 更新方法

```cpp
bool onUpdate(GrDirectContext* dc, const void* data, size_t offset, size_t size) override;
```

更新缓冲区内容：

- 如果 `dc` 不为 `nullptr`（GPU 上下文），返回 `false`（CPU 缓冲区无法在 GPU 上下文更新）
- 否则通过 `std::memcpy` 更新指定范围的数据

## 内部实现细节

### SkMeshSpecificationPriv 访问器实现

所有方法直接访问 `SkMeshSpecification` 的私有成员：

```cpp
static SkSpan<const Varying> Varyings(const SkMeshSpecification& spec) {
    return SkSpan(spec.fVaryings);
}

static const SkSL::Program* VS(const SkMeshSpecification& spec) {
    return spec.fVS.get();
}
```

这种设计允许内部代码绕过封装直接访问数据，避免公共 API 暴露实现细节。

### 类型转换实现

使用 `switch` 语句将 Mesh API 类型映射到 SkSL 类型：

```cpp
static SkSLType VaryingTypeAsSLType(Varying::Type type) {
    switch (type) {
        case Varying::Type::kFloat:  return SkSLType::kFloat;
        case Varying::Type::kFloat2: return SkSLType::kFloat2;
        // ... 其他类型
    }
    SkUNREACHABLE;
}
```

特殊处理：`Attribute::Type::kUByte4_unorm` 映射到 `SkSLType::kHalf4`（归一化到 [0,1]）。

### CpuBuffer 工厂实现

```cpp
template <typename Base>
sk_sp<Base> SkMeshPriv::CpuBuffer<Base>::Make(const void* data, size_t size) {
    SkASSERT(size);
    sk_sp<SkData> storage;
    if (data) {
        storage = SkData::MakeWithCopy(data, size);
    } else {
        storage = SkData::MakeZeroInitialized(size);
    }
    return sk_sp<Base>(new CpuBuffer<Base>(std::move(storage)));
}
```

**设计要点**：

- 使用 `SkData` 管理内存生命周期
- 支持数据拷贝或零初始化两种模式
- 返回基类类型的智能指针，隐藏具体实现

### CpuBuffer 更新实现

```cpp
template <typename Base>
bool SkMeshPriv::CpuBuffer<Base>::onUpdate(GrDirectContext* dc,
                                          const void* data,
                                          size_t offset,
                                          size_t size) {
    if (dc) {
        return false;  // CPU 缓冲区不支持 GPU 上下文更新
    }
    std::memcpy(SkTAddOffset<void>(fData->writable_data(), offset), data, size);
    return true;
}
```

**限制**：CPU 缓冲区只能在 CPU 端更新，如果传入 GPU 上下文则拒绝操作。

### Varying 死代码检测

```cpp
static bool VaryingIsDead(const SkMeshSpecification& spec, int v) {
    SkASSERT(v >= 0 && SkToSizeT(v) < spec.fVaryings.size());
    return (1 << v) & spec.fDeadVaryingMask;
}
```

使用位掩码快速检测 varying 是否未被引用（通过着色器分析确定）。

## 依赖关系

### 依赖的模块

| **模块** | **用途** |
|---------|---------|
| `SkMesh` | 公共 API 定义 |
| `SkData` | 内存管理和数据存储 |
| `SkSLTypeShared` | SkSL 类型系统 |
| `GrDirectContext` | GPU 上下文接口（用于类型检查） |

### 被依赖的模块

| **模块** | **关系** |
|---------|---------|
| Ganesh 渲染器 | 访问 Mesh 规格和缓冲区数据 |
| Graphite 渲染器 | 使用内部接口进行 GPU 资源创建 |
| Mesh 构建工具 | 创建 CPU 缓冲区并填充数据 |
| 着色器编译器 | 获取 SkSL 程序和类型信息 |

## 设计模式与设计决策

### 私有访问器模式

`SkMeshSpecificationPriv` 作为友元类或通过直接访问私有成员，提供内部接口：

- 保持公共 API 简洁，不暴露实现细节
- 内部代码可以高效访问数据，无需额外封装
- 集中管理内部访问逻辑

### 策略模式（缓冲区抽象）

`Buffer` 基类定义接口，不同后端提供具体实现：

- **CPU 缓冲区**：`CpuBuffer`，内存中存储
- **GPU 缓冲区**：由 Ganesh/Graphite 提供的实现（未在此文件）

### 模板编程

`CpuBuffer<Base>` 使用模板参数化基类：

- 代码复用：顶点缓冲区和索引缓冲区共享实现
- 类型安全：编译时检查基类约束
- 零额外开销：模板展开后无虚函数调用

### 智能指针管理

使用 `sk_sp<SkData>` 管理缓冲区内存：

- 自动引用计数，防止内存泄漏
- 支持缓冲区在多处共享
- 线程安全的引用计数

### 防御性编程

- `SkASSERT` 检查前置条件（如索引范围、缓冲区大小）
- `SkUNREACHABLE` 标记不应到达的代码路径
- GPU 上下文检查防止误用

## 性能考量

### 内联访问

`SkMeshSpecificationPriv` 的方法都是内联的，直接访问成员变量：

- 零运行时开销
- 编译器可充分优化

### 零拷贝 peek

`CpuBuffer::peek()` 返回内部数据指针，避免拷贝：

- 适用于只读访问场景
- 调用者需确保不超出缓冲区边界

### 内存布局

`CpuBuffer` 使用 `SkData` 的连续内存：

- 缓存友好
- 易于传递给 GPU（通过 DMA）

### 位掩码优化

`VaryingIsDead` 使用位掩码快速检查：

- O(1) 复杂度
- 适合频繁查询的场景

### 使用建议

- 对于小型静态网格，使用 CPU 缓冲区
- 对于动态更新的大型网格，考虑 GPU 缓冲区（需后端支持）
- 避免频繁调用 `onUpdate`，批量更新以减少开销
- 使用 `peek()` 进行只读访问，避免不必要的拷贝

## 相关文件

| **文件路径** | **说明** |
|-------------|---------|
| `include/core/SkMesh.h` | 公共 API 定义 |
| `src/core/SkMeshPriv.cpp` | 可能存在的实现文件（如非模板方法） |
| `src/gpu/ganesh/GrMesh*` | Ganesh 后端的 Mesh 实现 |
| `src/gpu/graphite/Mesh*` | Graphite 后端的 Mesh 实现 |
| `include/core/SkData.h` | 数据容器 |
| `src/core/SkSLTypeShared.h` | SkSL 类型定义 |
