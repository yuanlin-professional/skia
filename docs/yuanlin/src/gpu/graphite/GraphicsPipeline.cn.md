# GraphicsPipeline

> 源文件
> - src/gpu/graphite/GraphicsPipeline.h
> - src/gpu/graphite/GraphicsPipeline.cpp

## 概述

`GraphicsPipeline` 是 Graphite 中图形管线状态对象（PSO）的抽象基类。它封装了渲染管线的所有固定功能和可编程阶段状态，包括顶点输入、光栅化设置、着色器、混合模式等。每个后端（Metal、Vulkan、Dawn）都有自己的具体实现。

## 主要类与结构体

### GraphicsPipeline 类

```cpp
class GraphicsPipeline : public Resource {
public:
    ~GraphicsPipeline() override;

    // 访问器
    PrimitiveType primitiveType() const;
    bool hasStepUniforms() const;
    bool hasPaintUniforms() const;
    bool hasGradientBuffer() const;

    // 资源类型
    const char* getResourceType() const override;

protected:
    GraphicsPipeline(const SharedContext*, const GraphicsPipelineDesc&);

private:
    GraphicsPipelineDesc fDesc;
};
```

## 主要概念

### 管线描述符

`GraphicsPipelineDesc` 包含创建管线所需的所有信息：
- 渲染步骤 ID
- 着色器代码片段 ID
- 顶点属性布局
- 混合模式
- 深度模板设置

### 延迟创建

管线创建通常很昂贵（特别是着色器编译），因此 Graphite 使用：
1. **描述符缓存**：`GraphicsPipelineCache` 存储描述符
2. **句柄系统**：`GraphicsPipelineHandle` 允许异步编译
3. **全局缓存**：`GlobalCache` 在 Context 间共享管线

## 后端实现

| 后端 | 实现文件 | 对应 API 类型 |
|------|---------|--------------|
| Metal | `MtlGraphicsPipeline.h` | `MTLRenderPipelineState` |
| Vulkan | `VulkanGraphicsPipeline.h` | `VkPipeline` |
| Dawn | `DawnGraphicsPipeline.h` | `WGPURenderPipeline` |

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/GraphicsPipelineDesc.h` | 管线描述符 |
| `src/gpu/graphite/GraphicsPipelineHandle.h` | 管线句柄 |
| `src/gpu/graphite/PipelineManager.h` | 管线管理器 |
| `src/gpu/graphite/GlobalCache.h` | 全局管线缓存 |
| `src/gpu/graphite/Resource.h` | 资源基类 |
