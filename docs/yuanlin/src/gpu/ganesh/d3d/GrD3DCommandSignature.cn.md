# GrD3DCommandSignature

> 源文件
> - src/gpu/ganesh/d3d/GrD3DCommandSignature.h
> - src/gpu/ganesh/d3d/GrD3DCommandSignature.cpp

## 概述

`GrD3DCommandSignature` 是 Skia 图形库中 Ganesh D3D 后端的命令签名封装类,用于管理 Direct3D 12 的 `ID3D12CommandSignature` 对象。命令签名在 D3D12 中定义了间接绘制命令的参数布局和格式,允许 GPU 直接从缓冲区读取绘制参数而无需 CPU 干预。该类继承自 `GrManagedResource`,提供了资源生命周期管理和引用计数功能。

该类的主要职责是创建和管理支持索引绘制和非索引绘制的命令签名对象,这对于实现高性能的间接绘制(indirect drawing)至关重要。通过缓存不同配置的命令签名,可以避免重复创建相同的 D3D 资源,提高渲染效率。

## 架构位置

`GrD3DCommandSignature` 位于 Skia 图形库的 GPU 渲染层次结构中:

```
Skia
└── src/gpu/ganesh (Ganesh GPU 后端)
    └── d3d (Direct3D 12 实现)
        ├── GrD3DGpu (D3D GPU 主类)
        ├── GrD3DCommandSignature (命令签名管理)
        └── GrManagedResource (资源管理基类)
```

该类是 Ganesh D3D 后端的底层资源管理组件,与 `GrD3DGpu` 紧密协作,为上层的渲染管线提供间接绘制能力。

## 主要类与结构体

### GrD3DCommandSignature

**继承关系**:
- 继承自: `GrManagedResource` (提供引用计数和资源生命周期管理)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCommandSignature` | `gr_cp<ID3D12CommandSignature>` | D3D12 命令签名对象的智能指针 |
| `fIndexed` | `ForIndexed` | 标记是否为索引绘制命令签名 |
| `fSlot` | `unsigned int` | 顶点缓冲区插槽编号 |

### ForIndexed 枚举

```cpp
enum class ForIndexed : bool {
    kYes = true,   // 索引绘制
    kNo = false    // 非索引绘制
};
```

该枚举用于区分命令签名是用于索引绘制还是非索引绘制,这决定了内部使用的 D3D 参数类型。

## 公共 API 函数

### 静态工厂方法

```cpp
static sk_sp<GrD3DCommandSignature> Make(GrD3DGpu* gpu,
                                          ForIndexed indexed,
                                          unsigned int slot);
```

创建命令签名对象的工厂方法:
- **参数**:
  - `gpu`: D3D GPU 设备对象指针
  - `indexed`: 是否为索引绘制
  - `slot`: 顶点缓冲区插槽编号
- **返回值**: 智能指针包装的命令签名对象,创建失败返回 `nullptr`

### 兼容性检查

```cpp
bool isCompatible(ForIndexed indexed, unsigned int slot) const;
```

检查当前命令签名是否与指定的参数兼容,用于命令签名复用:
- **参数**: 索引类型和槽位
- **返回值**: 兼容返回 `true`,否则返回 `false`

### 访问器

```cpp
ID3D12CommandSignature* commandSignature() const;
```

获取底层的 D3D12 命令签名对象指针,供 D3D API 调用使用。

### 调试接口

```cpp
void dumpInfo() const override;  // 仅在 SK_TRACE_MANAGED_RESOURCES 定义时可用
```

输出资源的调试信息,包括对象地址和引用计数。

## 内部实现细节

### 命令签名创建流程

`Make` 方法实现了完整的 D3D12 命令签名创建流程:

1. **确定参数类型**: 根据 `forIndexed` 参数选择间接参数类型:
   - 索引绘制: `D3D12_INDIRECT_ARGUMENT_TYPE_DRAW_INDEXED`
   - 非索引绘制: `D3D12_INDIRECT_ARGUMENT_TYPE_DRAW`

2. **配置参数描述符**:
   ```cpp
   D3D12_INDIRECT_ARGUMENT_DESC argumentDesc = {};
   argumentDesc.Type = indexed ? D3D12_INDIRECT_ARGUMENT_TYPE_DRAW_INDEXED
                               : D3D12_INDIRECT_ARGUMENT_TYPE_DRAW;
   argumentDesc.VertexBuffer.Slot = slot;
   ```

3. **设置命令签名描述符**:
   - `ByteStride`: 根据绘制类型设置步长
     - 索引绘制: `sizeof(D3D12_DRAW_INDEXED_ARGUMENTS)` (20 字节)
     - 非索引绘制: `sizeof(D3D12_DRAW_ARGUMENTS)` (16 字节)
   - `NumArgumentDescs`: 参数数量为 1
   - `NodeMask`: 设为 0 (单 GPU 场景)

4. **创建 D3D 对象**:
   ```cpp
   gpu->device()->CreateCommandSignature(&commandSigDesc, nullptr,
                                         IID_PPV_ARGS(&commandSig));
   ```

5. **错误处理**: 创建失败时输出调试信息并返回 `nullptr`

### 资源管理

该类通过以下机制管理资源:
- **智能指针**: 使用 `gr_cp<>` (COM 智能指针)自动管理 D3D 对象生命周期
- **空实现**: `freeGPUData()` 为空实现,因为智能指针的析构函数会自动释放资源
- **引用计数**: 继承自 `GrManagedResource` 的引用计数机制

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrD3DTypes.h` | D3D 类型定义,包括 `gr_cp<>` 智能指针 |
| `GrManagedResource` | 提供资源管理基类和引用计数功能 |
| `GrD3DGpu` | D3D GPU 设备接口,提供 D3D12 设备对象 |
| `ID3D12CommandSignature` | D3D12 命令签名 COM 接口 |
| `ID3D12Device` | D3D12 设备对象 (通过 `GrD3DGpu` 访问) |

### 被依赖的模块

该类作为底层资源管理组件,可能被以下模块使用:

| 模块 | 使用场景 |
|------|----------|
| `GrD3DGpu` | 创建和缓存命令签名对象 |
| `GrD3DCommandList` | 执行间接绘制命令时使用 |
| `GrD3DOpsRenderPass` | 渲染过程中的间接绘制操作 |

## 设计模式与设计决策

### 工厂模式

使用静态 `Make` 方法而非公共构造函数,符合 Skia 的资源创建惯例:
- 允许创建失败时返回 `nullptr`
- 封装复杂的 D3D 对象创建逻辑
- 保持对象不变性(私有构造函数)

### 智能指针与 RAII

使用 `gr_cp<>` 智能指针和 `sk_sp<>` 引用计数指针实现自动资源管理:
- 避免手动调用 `Release()`
- 防止资源泄漏
- 支持对象共享和缓存

### 轻量级兼容性检查

`isCompatible` 方法通过简单的值比较实现快速的命令签名复用:
- 避免重复创建相同配置的 D3D 对象
- 减少 API 调用开销
- 支持命令签名缓存策略

### 类型安全的枚举

使用 `enum class ForIndexed : bool` 而非布尔值:
- 提高代码可读性
- 防止隐式类型转换
- 明确表达语义意图

## 性能考量

### 资源复用

命令签名是相对静态的资源,通过 `isCompatible` 方法支持高效复用:
- 避免每次绘制都创建新对象
- 减少 D3D 驱动开销
- 配合资源缓存策略提升性能

### 间接绘制优化

支持间接绘制是关键的性能优化手段:
- GPU 可直接从缓冲区读取绘制参数
- 减少 CPU-GPU 同步
- 支持多绘制调用批处理(multi-draw indirect)

### 轻量级对象

该类只存储 3 个成员变量,内存开销小:
- 智能指针占 8 字节
- 枚举占 1 字节
- 槽位占 4 字节
- 加上虚函数表指针和引用计数,总共约 24-32 字节

### 编译时优化

枚举使用底层布尔类型存储,避免额外的类型转换开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/d3d/GrD3DGpu.h/cpp` | 创建者 | 负责创建和管理命令签名对象 |
| `src/gpu/ganesh/d3d/GrD3DCommandList.h/cpp` | 使用者 | 执行间接绘制命令 |
| `src/gpu/ganesh/GrManagedResource.h` | 基类 | 提供资源管理框架 |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | 类型依赖 | 定义 D3D 相关类型和智能指针 |
| `src/gpu/ganesh/d3d/GrD3DOpsRenderPass.h/cpp` | 潜在使用者 | 渲染通道中可能使用间接绘制 |
