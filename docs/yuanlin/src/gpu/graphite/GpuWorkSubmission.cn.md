# GpuWorkSubmission

> 源文件
> - src/gpu/graphite/GpuWorkSubmission.h
> - src/gpu/graphite/GpuWorkSubmission.cpp

## 概述

`GpuWorkSubmission` 是 Graphite 中用于跟踪提交到 GPU 的工作完成状态的抽象基类。它提供了检查 GPU 命令是否完成执行的机制，是资源管理和同步的重要组成部分。每个后端（Metal、Vulkan、Dawn）都有自己的实现。

## 主要类与结构体

### GpuWorkSubmission 类

```cpp
class GpuWorkSubmission {
public:
    virtual ~GpuWorkSubmission();

    // 检查工作是否完成（非阻塞）
    virtual bool isFinished() const = 0;

    // 等待工作完成（阻塞）
    virtual void waitUntilFinished() const = 0;

protected:
    GpuWorkSubmission();
};
```

## 公共 API 函数

### isFinished

```cpp
virtual bool isFinished() const = 0;
```

非阻塞检查 GPU 工作是否完成。用于轮询状态或条件性资源回收。

### waitUntilFinished

```cpp
virtual void waitUntilFinished() const = 0;
```

阻塞等待 GPU 工作完成。用于强制同步点。

## 使用场景

- **资源回收**：检查资源是否仍被 GPU 使用
- **缓冲区重用**：确定映射缓冲区何时可安全重用
- **同步**：确保 CPU 和 GPU 协调

## 后端实现

| 后端 | 实现文件 |
|------|---------|
| Metal | `src/gpu/graphite/mtl/MtlGpuWorkSubmission.h` |
| Vulkan | `src/gpu/graphite/vk/VulkanGpuWorkSubmission.h` |
| Dawn | `src/gpu/graphite/dawn/DawnGpuWorkSubmission.h` |

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/QueueManager.h` | 管理工作提交 |
| `src/gpu/graphite/ResourceCache.h` | 使用完成状态回收资源 |
| `include/gpu/graphite/Context.h` | 提交和检查工作 |
