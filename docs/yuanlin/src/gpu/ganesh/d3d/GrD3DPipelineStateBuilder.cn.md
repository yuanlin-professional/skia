# GrD3DPipelineStateBuilder

> 源文件
> - src/gpu/ganesh/d3d/GrD3DPipelineStateBuilder.h
> - src/gpu/ganesh/d3d/GrD3DPipelineStateBuilder.cpp

## 概述

`GrD3DPipelineStateBuilder` 是 D3D12 管线状态的构建器类,负责编译着色器、配置管线状态描述符和创建 D3D12 管线状态对象。该类实现了复杂的管线创建流程,包括着色器编译、混合状态配置、深度模板状态设置和顶点输入布局定义。

## 架构位置

```
Skia
└── src/gpu/ganesh/d3d
    ├── GrD3DResourceProvider
    │   └── PipelineStateCache
    │       └── GrD3DPipelineStateBuilder ← 构建器类
    │           ├── SkSLCompiler (着色器编译)
    │           ├── GrD3DPipeline (创建目标)
    │           └── GrD3DRootSignature (根签名)
    └── GrD3DPipelineState (构建结果)
```

## 主要类与结构体

### GrD3DPipelineStateBuilder

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGpu` | `GrD3DGpu*` | GPU设备指针 |
| `fVS` | `CompiledShaderInfo` | 顶点着色器信息 |
| `fPS` | `CompiledShaderInfo` | 像素着色器信息 |
| `fInputLayout` | `std::vector<D3D12_INPUT_ELEMENT_DESC>` | 顶点输入布局 |
| `fPipelineDesc` | `D3D12_GRAPHICS_PIPELINE_STATE_DESC` | 管线状态描述符 |

## 公共 API 函数

```cpp
// 创建管线状态
static GrD3DPipelineState* CreatePipelineState(
    GrD3DGpu* gpu,
    GrD3DRenderTarget* renderTarget,
    const GrProgramInfo& programInfo,
    const GrProgramDesc* desc);
```

## 内部实现细节

### 着色器编译

```cpp
bool compileShaders() {
    // 1. 生成HLSL代码
    SkSL::String hlslVS = ..., hlslPS = ...;
    
    // 2. 编译为DXIL字节码
    ComPtr<ID3DBlob> vsBlob, psBlob;
    D3DCompile(hlslVS.c_str(), ..., &vsBlob, ...);
    D3DCompile(hlslPS.c_str(), ..., &psBlob, ...);
    
    // 3. 保存编译结果
    fVS.fShaderBlob = vsBlob;
    fPS.fShaderBlob = psBlob;
    
    return true;
}
```

### 管线状态配置

```cpp
void configurePipelineState() {
    // 配置光栅化状态
    fPipelineDesc.RasterizerState.FillMode = D3D12_FILL_MODE_SOLID;
    fPipelineDesc.RasterizerState.CullMode = D3D12_CULL_MODE_NONE;
    
    // 配置混合状态
    setupBlendState(programInfo.pipeline().getXferProcessor());
    
    // 配置深度模板状态
    setupDepthStencilState(programInfo.pipeline().getStencilSettings());
    
    // 配置顶点输入布局
    setupInputLayout(programInfo.geomProc());
}
```

### 管线创建

```cpp
GrD3DPipelineState* finalize() {
    // 1. 创建D3D12管线对象
    ComPtr<ID3D12PipelineState> pso;
    device->CreateGraphicsPipelineState(&fPipelineDesc, IID_PPV_ARGS(&pso));
    
    // 2. 封装为GrD3DPipeline
    auto pipeline = GrD3DPipeline::Make(pso);
    
    // 3. 创建管线状态对象
    return new GrD3DPipelineState(pipeline, rootSignature, ...);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `SkSLCompiler` | SkSL到HLSL编译器 |
| `D3DCompile` | HLSL到DXIL编译器 |
| `GrProgramInfo` | 程序配置信息 |
| `ID3D12Device` | D3D12设备 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrD3DResourceProvider` | 通过缓存调用构建器 |

## 设计模式与设计决策

### 构建器模式

分步骤构建复杂对象:
- 清晰的构建流程
- 便于错误处理
- 支持配置验证

### 静态工厂方法

使用静态方法封装构建流程:
- 隐藏构建细节
- 统一错误处理
- 便于单元测试

## 性能考量

### 着色器缓存

编译后的着色器被缓存:
- 避免重复编译
- 减少CPU时间
- 提高启动速度

### 异步编译

支持后台编译管线(未来):
- 减少帧率卡顿
- 提高用户体验
- 更好的资源利用

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/sksl/SkSLCompiler.h` | 依赖 | SkSL编译器 |
| `src/gpu/ganesh/d3d/GrD3DPipelineState.h/cpp` | 创建目标 | 管线状态 |
| `src/gpu/ganesh/d3d/GrD3DPipeline.h/cpp` | 创建目标 | D3D12管线 |
