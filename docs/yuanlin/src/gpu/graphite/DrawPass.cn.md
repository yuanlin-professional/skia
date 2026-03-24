# DrawPass

> 源文件
> - src/gpu/graphite/DrawPass.h
> - src/gpu/graphite/DrawPass.cpp

## 概述

`DrawPass` 是 Graphite 渲染管线中的不可变绘制命令序列，类似于渲染子通道（subpass）的概念。它存储了按执行顺序排列的绘制操作，以及这些操作所针对的渲染目标代理。`DrawPass` 由 `DrawList` 或 `DrawListLayer` 通过 `snapDrawPass()` 生成，代表尽可能接近最终命令缓冲区的形式。

与 `DrawList` 不同，`DrawPass` 是完全不可变的，并且可以直接将累积的顶点和 uniform 数据写入映射的 GPU 内存。多个兼容的 `DrawPass` 可以被 `RenderPassTask` 分组到单个渲染通道中执行。

## 主要类与结构体

### DrawPass 类

```cpp
class DrawPass {
public:
    ~DrawPass();

    // 访问器
    const SkIRect& bounds() const;
    TextureProxy* target() const;
    FloatStorageManager* floatStorageManager() const;
    std::pair<LoadOp, StoreOp> ops() const;
    std::array<float, 4> clearColor() const;

    // 资源准备
    bool prepareResources(ResourceProvider*,
                         sk_sp<const RuntimeEffectDictionary>,
                         const RenderPassDesc&);

    // 命令迭代
    DrawPassCommands::List::Iter commands() const;

    // 获取管线
    const GraphicsPipeline* getPipeline(size_t index) const;

    // 纹理和管线访问
    SkSpan<const sk_sp<TextureProxy>> sampledTextures() const;
    SkSpan<const sk_sp<GraphicsPipeline>> pipelines() const;

    // 添加资源引用
    [[nodiscard]] bool addResourceRefs(ResourceProvider*, CommandBuffer*);

private:
    friend class DrawList;
    friend class DrawListLayer;

    DrawPass(sk_sp<TextureProxy> target,
            std::pair<LoadOp, StoreOp> ops,
            std::array<float, 4> clearColor,
            sk_sp<FloatStorageManager> floatStorageManager);

    DrawPassCommands::List fCommandList;
    sk_sp<TextureProxy> fTarget;
    SkIRect fBounds;
    std::pair<LoadOp, StoreOp> fOps;
    std::array<float, 4> fClearColor;

    // 管线描述符和句柄
    skia_private::TArray<GraphicsPipelineDesc> fPipelineDescs;
    skia_private::TArray<float> fPipelineDrawAreas;
    skia_private::TArray<GraphicsPipelineHandle> fPipelineHandles;
    skia_private::TArray<sk_sp<TextureProxy>> fSampledTextures;
    skia_private::TArray<sk_sp<GraphicsPipeline>> fFullPipelines;

    sk_sp<FloatStorageManager> fFloatStorageManager;
};
```

## 公共 API 函数

### prepareResources

```cpp
bool prepareResources(ResourceProvider*,
                     sk_sp<const RuntimeEffectDictionary>,
                     const RenderPassDesc&);
```

实例化并准备 `DrawPass` 使用的所有资源：
- **GraphicsPipeline**：从描述符创建或查找管线对象
- **Texture**：实例化采样纹理
- **Sampler**：创建采样器状态

由于可能的多线程编译，管线在 `Context::insertRecording` 时才保证完成。

### addResourceRefs

```cpp
[[nodiscard]] bool addResourceRefs(ResourceProvider*, CommandBuffer*);
```

向 `CommandBuffer` 添加资源引用，确保执行期间资源保持有效。返回 `false` 表示失败。

### commands

```cpp
DrawPassCommands::List::Iter commands() const;
```

返回命令序列的迭代器，用于后端执行命令。

## 内部实现细节

### 不可变性

`DrawPass` 一旦创建就不可修改：
- 命令序列固定
- 资源引用固定
- 仅允许资源实例化（`prepareResources`）

这允许安全的并发访问和优化。

### 管线延迟创建

管线创建分两阶段：

1. **记录阶段**：存储 `GraphicsPipelineDesc`
2. **准备阶段**：
   - 创建 `GraphicsPipelineHandle`（异步编译）
   - 解析为 `GraphicsPipeline`（可能延迟）

### 绘制面积跟踪

`fPipelineDrawAreas` 记录每个管线的绘制面积：
- 用于选择最优的管线编译优先级
- 面积大的管线优先编译

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/DrawList.h/cpp` | 生成 DrawPass |
| `src/gpu/graphite/DrawListLayer.h/cpp` | 生成 DrawPass（分层版本） |
| `src/gpu/graphite/DrawCommands.h` | 命令定义 |
| `src/gpu/graphite/task/RenderPassTask.h` | 执行 DrawPass |
| `src/gpu/graphite/GraphicsPipeline.h` | 管线对象 |
| `src/gpu/graphite/GraphicsPipelineDesc.h` | 管线描述符 |
| `src/gpu/graphite/TextureProxy.h` | 纹理代理 |
| `src/gpu/graphite/ResourceProvider.h` | 资源提供者 |
