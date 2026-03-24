# GrD3DRootSignature

> 源文件
> - `src/gpu/ganesh/d3d/GrD3DRootSignature.h`
> - `src/gpu/ganesh/d3d/GrD3DRootSignature.cpp`

## 概述

`GrD3DRootSignature` 是 Skia 图形库中用于封装 Direct3D 12 根签名(Root Signature)的资源管理类。根签名是 D3D12 中定义着色器与资源之间绑定关系的关键对象,类似于 Vulkan 中的 Pipeline Layout。该类负责创建和管理包含常量缓冲区、纹理采样器和无序访问视图(UAV)的根签名配置。

根签名定义了着色器程序如何访问 GPU 资源,包括常量缓冲区(用于 uniform 数据)、着色器资源视图(用于纹理)和采样器。`GrD3DRootSignature` 通过自动化配置这些资源的布局,简化了 D3D12 渲染管线的设置过程。

## 架构位置

该类位于 Skia 的 GPU 后端架构中,专门服务于 Direct3D 12 实现:

```
Skia Graphics Library
└── src/gpu/ganesh/          # Ganesh GPU 后端
    └── d3d/                 # Direct3D 12 特定实现
        ├── GrD3DGpu         # D3D12 GPU 接口实现
        ├── GrD3DRootSignature  # 根签名封装 (当前类)
        └── GrD3DPipeline    # 使用根签名的渲染管线
```

该类是 Ganesh D3D12 后端的基础设施组件,为所有使用 D3D12 的渲染操作提供资源绑定配置。

## 主要类与结构体

### GrD3DRootSignature

**继承关系**
- 继承自: `GrManagedResource` - 提供资源生命周期管理和引用计数

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRootSignature` | `gr_cp<ID3D12RootSignature>` | D3D12 根签名对象的智能指针封装 |
| `fNumTextureSamplers` | `int` | 根签名支持的纹理采样器数量 |
| `fNumUAVs` | `int` | 根签名支持的无序访问视图数量 |

### ParamIndex 枚举

定义根签名参数的索引位置:

| 枚举值 | 索引 | 说明 |
|-------|------|------|
| `kConstantBufferView` | 0 | 常量缓冲区视图(用于 uniform 数据) |
| `kShaderViewDescriptorTable` | 1 | 着色器资源视图描述符表(纹理和 UAV) |
| `kSamplerDescriptorTable` | 2 | 采样器描述符表 |

## 公共 API 函数

### 静态工厂方法

```cpp
static sk_sp<GrD3DRootSignature> Make(GrD3DGpu* gpu,
                                      int numTextureSamplers,
                                      int numUAVs);
```
创建新的根签名对象。根据指定的纹理采样器和 UAV 数量配置根签名布局。

**参数:**
- `gpu` - D3D12 GPU 对象,用于访问设备
- `numTextureSamplers` - 需要支持的纹理采样器数量
- `numUAVs` - 需要支持的无序访问视图数量

**返回:** 成功时返回根签名智能指针,失败返回 `nullptr`

### 兼容性检查

```cpp
bool isCompatible(int numTextureSamplers, int numUAVs) const;
```
检查当前根签名是否与给定的资源配置兼容,用于根签名的重用和缓存。

### 访问器

```cpp
ID3D12RootSignature* rootSignature() const;
```
获取底层的 D3D12 根签名对象指针,供渲染管线绑定使用。

## 内部实现细节

### 根签名创建流程

根签名的创建过程遵循 D3D12 的标准流程:

1. **参数配置**: 总是从常量缓冲区视图开始配置参数数组
2. **描述符范围设置**: 为每个纹理采样器创建独立的描述符范围
3. **寄存器分配策略**:
   - 采样器使用寄存器 `s[2*i]`
   - 对应纹理使用寄存器 `t[2*i+1]`
   - UAV 使用后续的寄存器 `u[2*numTextureSamplers]` 开始

这种交替的寄存器分配模式是为了与 SPIRV-Cross 的绑定转换保持一致。

### 描述符表布局

根签名包含最多三个参数:

1. **常量缓冲区视图 (CBV)** - 索引 0
   - 直接绑定,不使用描述符表
   - 寄存器: `b0`
   - 空间: `kUniformDescriptorSet`

2. **着色器资源视图描述符表** - 索引 1
   - 包含所有纹理(SRV)和 UAV
   - 每个纹理占据连续的描述符位置
   - UAV 在纹理之后连续排列

3. **采样器描述符表** - 索引 2
   - 包含所有采样器对象
   - 每个采样器独立的描述符范围

### SPIRV-Cross 集成

代码中特别注意了与 SPIRV-Cross 的集成:
- 使用 `GrSPIRVUniformHandler` 定义的描述符集编号作为 HLSL 寄存器空间
- 每个绑定值直接映射到 HLSL 寄存器索引
- 采样器和纹理成对分配,采样器在偶数索引,纹理在奇数索引

### 错误处理

实现包含两层错误检查:
1. `D3D12SerializeRootSignature` 失败时输出错误详情
2. `CreateRootSignature` 失败时输出通用错误信息

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrManagedResource` | 提供基类资源管理功能 |
| `GrD3DGpu` | 访问 D3D12 设备进行根签名创建 |
| `GrSPIRVUniformHandler` | 获取描述符集常量定义 |
| `GrD3DTypes` | D3D12 类型定义和智能指针 `gr_cp` |
| `skia_private::AutoTArray` | 动态数组容器 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrD3DPipelineState` | 在创建渲染管线时引用根签名 |
| `GrD3DResourceProvider` | 缓存和重用根签名对象 |
| `GrD3DCommandList` | 绑定根签名到命令列表 |

## 设计模式与设计决策

### 工厂模式

使用静态 `Make` 方法而非公共构造函数,确保:
- 对象创建失败时能够返回 `nullptr`
- 构造过程的复杂初始化逻辑被封装
- 始终返回智能指针管理的对象

### 不可变对象

根签名一旦创建就不可修改,这是合理的设计因为:
- D3D12 的根签名本身就是不可变对象
- 允许安全的跨线程共享和缓存
- 通过 `isCompatible` 方法支持根签名重用

### 资源绑定策略

采用固定的三层参数结构:
1. **CBV 直接绑定** - 常量缓冲区使用根描述符,避免描述符表的间接访问开销
2. **纹理和 UAV 共享描述符表** - 减少根签名参数数量
3. **采样器独立描述符表** - 与纹理分离管理

这种设计在性能和灵活性之间取得平衡。

### 描述符范围分离

每个采样器-纹理对使用独立的描述符范围而非单一连续范围,原因是:
- SPIRV-Cross 的绑定编号映射到 HLSL 寄存器时不是连续的
- 采样器和纹理交替编号 (0, 2, 4... 和 1, 3, 5...)
- 虽然增加了复杂性,但保证了与 SPIR-V 着色器的正确互操作

## 性能考量

### 根签名重用

通过 `isCompatible` 方法支持根签名缓存:
- 相同配置的管线可以共享根签名
- 减少根签名对象的创建开销
- 降低 GPU 驱动的状态切换成本

### 寄存器空间优化

根签名设计考虑了 D3D12 的性能特性:
- 常量缓冲区使用根描述符(32-bit 根签名成本: 2 DWORD)
- 描述符表引用(32-bit 根签名成本: 1 DWORD per table)
- 总根签名大小控制在合理范围内

### 描述符堆访问

描述符在表中连续排列(`D3D12_DESCRIPTOR_RANGE_OFFSET_APPEND`):
- 提高 GPU 缓存局部性
- 简化描述符堆管理
- 支持高效的批量描述符设置

### 着色器可见性

所有参数使用 `D3D12_SHADER_VISIBILITY_ALL`:
- 简化了根签名配置
- 允许所有着色器阶段访问资源
- 在 Skia 的使用场景中不会造成明显的性能损失

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/d3d/GrD3DGpu.h` | 依赖 | 提供 D3D12 设备访问 |
| `src/gpu/ganesh/d3d/GrD3DPipelineState.h` | 被使用 | 渲染管线状态引用根签名 |
| `src/gpu/ganesh/d3d/GrD3DResourceProvider.h` | 被使用 | 管理根签名的缓存 |
| `src/gpu/ganesh/GrSPIRVUniformHandler.h` | 依赖 | 提供描述符集常量 |
| `src/gpu/ganesh/GrManagedResource.h` | 基类 | 资源管理基类 |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | 依赖 | D3D12 类型定义 |
| `src/gpu/ganesh/d3d/GrD3DCommandList.h` | 被使用 | 绑定根签名到命令列表 |
