# GrD3DTypesPriv

> 源文件
> - `src/gpu/ganesh/d3d/GrD3DTypesPriv.h`
> - `src/gpu/ganesh/d3d/GrD3DTypesPriv.cpp`

## 概述

`GrD3DTypesPriv` 是 Skia 图形库中用于 Direct3D 12 后端的私有类型定义模块。它提供了内部使用的类型结构体和转换函数,主要用于简化纹理资源规格的表示和转换。该模块是 D3D12 后端内部实现细节的一部分,不暴露给外部 API 使用者。

核心组件是 `GrD3DTextureResourceSpec` 结构体,它是 `GrD3DSurfaceInfo` 的轻量级子集,仅包含纹理格式和采样质量模式。该模块还提供了在这两种表示之间转换的实用函数,支持纹理创建和配置的灵活处理。

## 架构位置

```
Skia GPU Backend (Ganesh)
└── Direct3D 12 后端
    ├── 公共类型层
    │   └── GrD3DTypes (公共 API)
    └── 私有类型层
        └── GrD3DTypesPriv (当前模块 - 内部实现)
            ├── GrD3DTextureResourceSpec (轻量级规格)
            └── 转换函数
```

该模块位于 D3D12 类型系统的私有层,为内部实现提供便利的类型表示。

## 主要类与结构体

### GrD3DTextureResourceSpec

纹理资源规格的轻量级表示。

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFormat` | `DXGI_FORMAT` | DXGI 纹理格式(如 `DXGI_FORMAT_R8G8B8A8_UNORM`) |
| `fSampleQualityPattern` | `unsigned int` | MSAA 采样质量模式 |

**构造函数**

1. **默认构造函数**
```cpp
GrD3DTextureResourceSpec()
```
初始化为未知格式和标准 MSAA 质量模式:
- `fFormat = DXGI_FORMAT_UNKNOWN`
- `fSampleQualityPattern = DXGI_STANDARD_MULTISAMPLE_QUALITY_PATTERN`

2. **转换构造函数**
```cpp
GrD3DTextureResourceSpec(const GrD3DSurfaceInfo& info)
```
从完整的表面信息提取格式和质量模式,丢弃采样数、层级数和保护标志等其他信息。

## 公共 API 函数

### 规格到表面信息转换

```cpp
GrD3DSurfaceInfo GrD3DTextureResourceSpecToSurfaceInfo(
    const GrD3DTextureResourceSpec& d3dSpec,
    uint32_t sampleCount,
    uint32_t levelCount,
    skgpu::Protected isProtected);
```

将轻量级的纹理资源规格扩展为完整的表面信息结构体。

**参数说明:**
- `d3dSpec` - 源规格,包含格式和质量模式
- `sampleCount` - MSAA 采样数(1 表示无 MSAA)
- `levelCount` - Mipmap 层级数
- `isProtected` - 是否为受保护内存

**返回:** 完整的 `GrD3DSurfaceInfo` 对象,包含所有纹理创建所需的参数。

## 内部实现细节

### GrD3DSurfaceInfo 结构

虽然该结构在 `GrD3DTypes.h` 中定义,但转换函数填充其所有字段:

**共享信息字段:**
- `fSampleCount` - 采样数量
- `fLevelCount` - Mipmap 层级
- `fProtected` - 保护内存标志

**D3D12 特定字段:**
- `fFormat` - DXGI 格式
- `fSampleQualityPattern` - 采样质量模式

### 简单的转换逻辑

`GrD3DTextureResourceSpecToSurfaceInfo` 实现非常直接:
1. 创建空的 `GrD3DSurfaceInfo`
2. 填充共享字段(采样数、层级数、保护标志)
3. 复制 D3D12 特定字段(格式和质量模式)
4. 返回完整结构体

没有复杂的验证或转换逻辑,纯粹的数据组装。

### 标准质量模式默认值

默认使用 `DXGI_STANDARD_MULTISAMPLE_QUALITY_PATTERN`:
- 这是 D3D12 推荐的质量模式
- 保证跨硬件兼容性
- 对应于标准的多重采样模式

### 最小化的类型表示

`GrD3DTextureResourceSpec` 仅保留核心信息:
- **包含**: 格式和质量模式(类型签名)
- **排除**: 采样数、层级数、保护标志(实例属性)

这种分离使得类型规格可以在不同配置的纹理之间共享。

### POD 结构体设计

两个结构体都是 POD(Plain Old Data):
- 可以安全地按值传递
- 支持内存布局优化
- 便于序列化和反序列化

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrD3DTypes` | 公共 D3D12 类型定义(包括 `GrD3DSurfaceInfo`) |
| `skgpu::Protected` | 保护内存标志枚举 |
| `<stdint.h>` | 标准整数类型 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrD3DTextureResource` | 可能使用规格表示纹理配置 |
| `GrD3DGpu` | 在纹理创建流程中使用转换函数 |
| `GrD3DCaps` | 格式能力查询可能使用规格 |
| 内部 D3D12 实现 | 简化纹理规格传递 |

## 设计模式与设计决策

### 数据传输对象(DTO)

`GrD3DTextureResourceSpec` 是典型的 DTO:
- 仅包含数据,无行为
- 用于在模块间传递配置
- 轻量级,可按值传递

### 类型投影

从完整类型(`GrD3DSurfaceInfo`)投影到子集(`GrD3DTextureResourceSpec`):
- 提取类型相关信息
- 忽略实例相关信息
- 支持类型级别的比较和哈希

### 转换函数模式

提供显式转换函数而非隐式转换:
- 明确转换的意图
- 需要提供额外参数(采样数、层级数等)
- 避免意外的隐式转换

### 命名空间分离

私有类型在 `GrD3DTypesPriv` 模块:
- 与公共类型(`GrD3DTypes`)明确分离
- 防止外部代码依赖内部实现
- 保留未来重构的灵活性

### 最小化设计

该模块保持极简:
- 仅 55 行代码
- 单一职责: 类型表示和转换
- 没有复杂的逻辑或验证

这种设计易于理解和维护。

## 性能考量

### 按值传递

结构体设计为按值传递:
- 总大小仅 8 字节(4 字节格式 + 4 字节质量模式)
- 小于指针大小,按值传递更高效
- 避免堆分配和间接访问

### 内联友好

转换函数非常简单:
- 仅包含字段赋值
- 易于编译器内联
- 内联后接近零开销

### 编译时优化

结构体字段都是 POD 类型:
- 编译器可以优化为寄存器操作
- 不需要构造函数调用开销
- 支持聚合初始化

### 无虚函数

结构体不包含虚函数:
- 无虚表指针开销
- 内存布局紧凑
- 可以使用 memcpy 等低级操作

### 缓存友好

小的结构体大小:
- 适合放入 CPU 缓存行
- 多个规格可以密集存储
- 遍历规格数组时缓存效率高

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | 依赖 | 公共 D3D12 类型定义 |
| `src/gpu/ganesh/d3d/GrD3DTextureResource.h` | 被使用 | 可能使用规格表示 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h` | 被使用 | GPU 实现使用规格和转换 |
| `src/gpu/ganesh/d3d/GrD3DCaps.h` | 被使用 | 能力检测使用规格 |
| `include/private/base/SkFeatures.h` | 依赖 | 平台特性宏 |
