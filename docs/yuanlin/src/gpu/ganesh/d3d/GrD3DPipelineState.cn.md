# GrD3DPipelineState

> 源文件
> - src/gpu/ganesh/d3d/GrD3DPipelineState.h
> - src/gpu/ganesh/d3d/GrD3DPipelineState.cpp

## 概述

`GrD3DPipelineState` 封装 D3D12 图形管线状态对象及相关资源绑定,管理着色器、uniform 数据、根签名和描述符表。该类是 Skia 程序与 D3D12 管线之间的桥梁,负责设置渲染管线的所有状态和资源。

## 架构位置

```
Skia
└── src/gpu/ganesh/d3d
    ├── GrD3DResourceProvider (创建管线状态)
    │   └── PipelineStateCache (缓存管线状态)
    │       └── GrD3DPipelineState ← 核心类
    │           ├── GrD3DPipeline (D3D管线对象)
    │           ├── GrD3DRootSignature (根签名)
    │           └── GrD3DPipelineStateDataManager (uniform数据)
    └── GrD3DOpsRenderPass (使用管线状态)
```

## 主要类与结构体

### GrD3DPipelineState

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPipeline` | `sk_sp<GrD3DPipeline>` | D3D12 管线状态对象 |
| `fRootSignature` | `sk_sp<GrD3DRootSignature>` | 根签名 |
| `fDataManager` | `GrD3DPipelineStateDataManager` | Uniform 数据管理器 |
| `fNumSamplers` | `int` | 采样器数量 |
| `fNumTextures` | `int` | 纹理数量 |

## 公共 API 函数

```cpp
// 获取D3D管线对象
sk_sp<GrD3DPipeline> pipeline() const;

// 设置渲染数据(uniform、纹理、采样器)
void setData(GrD3DRenderTarget* renderTarget, const GrProgramInfo& programInfo);

// 绑定uniform数据
void bindUniforms(GrD3DGpu* gpu);

// 绑定纹理和采样器
void bindTextures(GrD3DGpu* gpu, const GrGeometryProcessor& geomProc);
```

## 内部实现细节

### Uniform 数据上传

```cpp
void setData(GrD3DRenderTarget* rt, const GrProgramInfo& programInfo) {
    // 1. 上传 uniform 数据
    fDataManager.set(programInfo.pipeline().uniforms(), ...);
    
    // 2. 绑定到GPU
    this->bindUniforms(gpu);
}
```

### 资源绑定

```cpp
void bindTextures(GrD3DGpu* gpu, const GrGeometryProcessor& geomProc) {
    // 1. 收集纹理和采样器句柄
    std::vector<D3D12_CPU_DESCRIPTOR_HANDLE> srvs;
    std::vector<D3D12_CPU_DESCRIPTOR_HANDLE> samplers;
    
    // 2. 创建描述符表
    auto srvTable = gpu->resourceProvider().findOrCreateShaderViewTable(srvs);
    auto samplerTable = gpu->resourceProvider().findOrCreateSamplerTable(samplers);
    
    // 3. 绑定到根签名
    fCommandList->setGraphicsRootDescriptorTable(kTextureSlot, srvTable->baseGpuDescriptor());
    fCommandList->setGraphicsRootDescriptorTable(kSamplerSlot, samplerTable->baseGpuDescriptor());
}
```

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrD3DPipeline` | D3D12管线对象 |
| `GrD3DRootSignature` | 根签名 |
| `GrD3DPipelineStateDataManager` | Uniform数据管理 |
| `GrProgramInfo` | 程序信息 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrD3DOpsRenderPass` | 渲染时使用管线状态 |
| `GrD3DResourceProvider` | 创建和缓存管线状态 |

## 设计模式与设计决策

### 组合模式

组合多个子对象(管线、根签名、数据管理器):
- 清晰的职责分离
- 便于单独测试
- 支持资源复用

### 延迟绑定

在渲染时才绑定资源:
- 支持动态资源
- 减少状态切换
- 优化性能

## 性能考量

### 描述符表缓存

缓存相同的描述符表组合:
- 避免重复创建
- 减少描述符拷贝
- 提高帧率

### Uniform 缓冲区复用

使用环形缓冲区上传 uniform:
- 避免每次分配
- 减少内存开销
- 提高上传效率

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/d3d/GrD3DPipeline.h/cpp` | 组件 | D3D12管线对象 |
| `src/gpu/ganesh/d3d/GrD3DRootSignature.h/cpp` | 组件 | 根签名 |
| `src/gpu/ganesh/d3d/GrD3DPipelineStateDataManager.h/cpp` | 组件 | Uniform管理 |
| `src/gpu/ganesh/d3d/GrD3DResourceProvider.h/cpp` | 创建者 | 资源提供者 |
