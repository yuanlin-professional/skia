# MtlComputePipeline -- Metal 计算管线

> 源文件:
> - `src/gpu/graphite/mtl/MtlComputePipeline.h`
> - `src/gpu/graphite/mtl/MtlComputePipeline.mm`

## 概述

MtlComputePipeline 是 Graphite Metal 后端的计算管线实现,继承自 `ComputePipeline` 基类。它将计算着色器编译为 Metal 的 `MTLComputePipelineState` 对象,支持原生 MSL 着色器和 SkSL 编译两种路径。

## 架构位置

```
ComputePipeline (抽象基类)
  -> MtlComputePipeline  <-- 本模块
       -> id<MTLComputePipelineState> (Metal 计算管线状态)
```

## 主要类与结构体

### MtlComputePipeline

```cpp
class MtlComputePipeline final : public ComputePipeline {
    sk_cfp<id<MTLComputePipelineState>> fPipelineState;
};
```

## 公共 API 函数

### Make

```cpp
static sk_sp<MtlComputePipeline> Make(const MtlSharedContext*, const ComputePipelineDesc&);
```

### 访问器

```cpp
id<MTLComputePipelineState> mtlPipelineState() const;
```

## 内部实现细节

### 双路径着色器编译

1. **原生 MSL 路径**: 当 `computeStep->supportsNativeShader()` 为真时,直接使用 `nativeShaderSource(MSL)` 获取 MSL 代码和入口点名
2. **SkSL 编译路径**: 通过 `BuildComputeSkSL` 生成 SkSL,再用 `SkSLToMSL` 编译为 MSL,入口点固定为 `"computeMain"`

### 管线创建

使用 `MTLComputePipelineDescriptor`:
- 设置标签为计算步骤名称
- 设置计算函数
- 使用 `MTLPipelineOptionNone` 创建（不需要反射信息）

### TODO 项

代码中标注了多个待优化项:
- 使用 `stageInputDescriptor` 描述输入数据布局
- 使用 `buffers` 属性设置缓冲区可变性
- 考虑设置 `threadGroupSizeIsMultipleOfThreadExecutionWidth`

## 依赖关系

- `ComputePipeline` -- 基类
- `MtlGraphiteUtils` -- MSL 编译
- `MtlSharedContext` -- 设备访问
- `ComputePipelineDesc` -- 管线描述
- `ContextUtils` -- `BuildComputeSkSL`

## 设计模式与设计决策

1. **双路径选择**: 原生 MSL 支持手写优化着色器,SkSL 路径提供跨后端可移植性。
2. **轻量构造**: 私有构造函数仅接收已编译的 PSO,所有验证和编译在 `Make` 中完成。

## 性能考量

- 着色器编译是一次性开销,通过 Graphite 的管线缓存系统避免重复。
- `MTLPipelineOptionNone` 跳过反射信息生成,加速管线创建。

## 相关文件

- `src/gpu/graphite/ComputePipeline.h` -- 计算管线基类
- `src/gpu/graphite/ComputePipelineDesc.h` -- 管线描述
- `src/gpu/graphite/mtl/MtlGraphiteUtils.h` -- MSL 编译工具
- `src/gpu/graphite/mtl/MtlCommandBuffer.h` -- 计算调度
