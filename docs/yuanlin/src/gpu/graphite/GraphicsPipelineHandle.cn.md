# GraphicsPipelineHandle

> 源文件
> - src/gpu/graphite/GraphicsPipelineHandle.h

## 概述

`GraphicsPipelineHandle` 是一个轻量级的句柄类，用于延迟和异步创建图形管线。它允许 `DrawPass` 在管线编译完成之前引用管线，支持多线程编译和更好的CPU/GPU并行性。

## 主要类

### GraphicsPipelineHandle 类

```cpp
class GraphicsPipelineHandle {
public:
    GraphicsPipelineHandle();
    ~GraphicsPipelineHandle();

    // 检查管线是否准备好
    bool isValid() const;

    // 获取实际管线（可能阻塞）
    sk_sp<GraphicsPipeline> getPipeline() const;

private:
    // 后端特定的实现细节
};
```

## 使用模式

### 创建句柄

```cpp
GraphicsPipelineHandle handle = pipelineManager->createHandle(desc);
```

### 解析管线

```cpp
sk_sp<GraphicsPipeline> pipeline = handle.getPipeline();
if (pipeline) {
    // 使用管线
}
```

## 异步编译

1. **记录阶段**：创建句柄，开始异步编译
2. **准备阶段**：检查编译是否完成
3. **执行阶段**：等待并获取管线

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/GraphicsPipeline.h` | 管线类型 |
| `src/gpu/graphite/PipelineManager.h` | 创建句柄 |
| `src/gpu/graphite/DrawPass.h` | 使用句柄 |
