# GraphicsPipelineDesc

> 源文件
> - src/gpu/graphite/GraphicsPipelineDesc.h

## 概述

`GraphicsPipelineDesc` 是图形管线状态对象（PSO）的描述符类，完整描述创建 `GraphicsPipeline` 所需的所有信息。它作为管线缓存的键，并包含渲染步骤标识和paint参数标识的组合。

## 主要类

### GraphicsPipelineDesc 类

```cpp
class GraphicsPipelineDesc {
public:
    GraphicsPipelineDesc();
    ~GraphicsPipelineDesc();

    // 构造
    GraphicsPipelineDesc(const RenderStepID& renderStepID,
                        UniquePaintParamsID paintParamsID);

    // 访问器
    const RenderStepID& renderStepID() const;
    UniquePaintParamsID paintParamsID() const;

    // 比较和哈希
    bool operator==(const GraphicsPipelineDesc& other) const;
    uint32_t hash() const;

private:
    RenderStepID fRenderStepID;
    UniquePaintParamsID fPaintParamsID;
};
```

## 组成部分

### RenderStepID

标识渲染步骤：
- 顶点属性布局
- 图元类型
- 深度/模板设置
- 光栅化状态

### UniquePaintParamsID

标识paint参数：
- 着色器组合
- 混合模式
- 颜色过滤器
- 图像过滤器

## 使用场景

### 作为缓存键

```cpp
GraphicsPipelineDesc desc{renderStep->id(), paintID};
sk_sp<GraphicsPipeline> pipeline = cache->find(desc);
if (!pipeline) {
    pipeline = create(desc);
    cache->insert(desc, pipeline);
}
```

### 序列化

描述符足够小且简单，可以高效序列化，支持管线预编译。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/GraphicsPipeline.h` | 使用描述符的管线 |
| `src/gpu/graphite/RenderStep.h` | 渲染步骤定义 |
| `src/gpu/graphite/PaintParams.h` | Paint 参数 |
| `src/gpu/graphite/GlobalCache.h` | 使用描述符作为键 |
