# GrD3DPipelineStateDataManager

> 源文件
> - src/gpu/ganesh/d3d/GrD3DPipelineStateDataManager.h
> - src/gpu/ganesh/d3d/GrD3DPipelineStateDataManager.cpp

## 概述

`GrD3DPipelineStateDataManager` 管理管线状态的 uniform 数据,负责追踪、打包和上传 uniform 变量到 GPU。该类继承自 `GrUniformDataManager`,提供 D3D12 特定的 uniform 数据管理,包括数据对齐、脏标记追踪和常量缓冲区上传。

## 架构位置

```
Skia
└── src/gpu/ganesh
    ├── GrUniformDataManager (基类)
    │   └── GrD3DPipelineStateDataManager ← 核心类
    └── d3d
        └── GrD3DPipelineState (使用数据管理器)
```

## 主要类与结构体

### GrD3DPipelineStateDataManager

**继承关系**:
- 继承自: `GrUniformDataManager`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fUniformData` | `SkTArray<char>` | Uniform数据缓冲区 |
| `fUniformsDirty` | `bool` | 脏标记,标识数据是否需要重新上传 |
| `fUniformSize` | `uint32_t` | Uniform数据总大小 |

## 公共 API 函数

```cpp
// 设置uniform数据
void set1i(UniformHandle, int32_t);
void set1f(UniformHandle, float);
void set2f(UniformHandle, float, float);
void set3f(UniformHandle, float, float, float);
void set4f(UniformHandle, float, float, float, float);
void setMatrix3f(UniformHandle, const float matrix[9]);
void setMatrix4f(UniformHandle, const float matrix[16]);

// 上传数据到GPU
void uploadUniformData(GrD3DGpu* gpu, GrD3DPipelineState* pipelineState);

// 标记为脏
void markDirty();
```

## 内部实现细节

### Uniform 数据设置

```cpp
void set4f(UniformHandle handle, float v0, float v1, float v2, float v3) {
    // 1. 获取uniform的偏移和大小
    const Uniform& uni = fUniforms[handle.toIndex()];
    
    // 2. 写入数据到缓冲区
    float* data = reinterpret_cast<float*>(fUniformData.begin() + uni.fOffset);
    data[0] = v0;
    data[1] = v1;
    data[2] = v2;
    data[3] = v3;
    
    // 3. 标记为脏
    fUniformsDirty = true;
}
```

### 数据上传

```cpp
void uploadUniformData(GrD3DGpu* gpu, GrD3DPipelineState* pipelineState) {
    if (!fUniformsDirty) {
        return;  // 无需上传
    }
    
    // 1. 上传到常量缓冲区
    D3D12_GPU_VIRTUAL_ADDRESS address =
        gpu->resourceProvider().uploadConstantData(fUniformData.begin(), fUniformSize);
    
    // 2. 绑定到根签名
    gpu->currentCommandList()->setGraphicsRootConstantBufferView(0, address);
    
    // 3. 清除脏标记
    fUniformsDirty = false;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrUniformDataManager` | 基类,提供通用uniform管理 |
| `GrD3DGpu` | GPU设备,用于上传数据 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrD3DPipelineState` | 使用数据管理器管理uniform |

## 设计模式与设计决策

### 脏标记模式

只上传改变的数据:
- 减少带宽占用
- 降低上传开销
- 提高帧率

### 数据对齐

确保数据符合D3D12对齐要求:
- 256字节对齐常量缓冲区
- 16字节对齐向量
- 避免硬件访问错误

## 性能考量

### 延迟上传

在实际绘制前才上传:
- 合并多次设置
- 减少上传次数
- 优化带宽使用

### 缓冲区复用

使用环形缓冲区:
- 避免重复分配
- 减少内存碎片
- 提高上传效率

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrUniformDataManager.h` | 基类 | 通用uniform管理 |
| `src/gpu/ganesh/d3d/GrD3DPipelineState.h/cpp` | 使用者 | 管线状态 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h/cpp` | 依赖 | GPU设备 |
