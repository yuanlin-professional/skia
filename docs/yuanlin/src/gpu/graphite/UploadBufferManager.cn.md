# UploadBufferManager

> 源文件: src/gpu/graphite/UploadBufferManager.h, src/gpu/graphite/UploadBufferManager.cpp

## 概述

`UploadBufferManager` 是 Skia Graphite 架构中管理纹理上传缓冲区的核心类。该类负责分配和管理临时 GPU 缓冲区，用于从 CPU 向 GPU 纹理传输数据。它通过缓冲区池化和重用机制优化上传性能，避免频繁的小缓冲区分配，并支持跨帧的缓冲区复用。

## 架构位置

```
Graphite 上传系统：
  ├── UploadBufferManager（缓冲区管理器）★
  ├── Buffer（GPU 缓冲区）
  ├── TextureUtils（纹理上传）
  └── Recorder（命令录制）
```

## 主要类与结构体

### UploadBufferManager 类

```cpp
class UploadBufferManager {
public:
    UploadBufferManager(ResourceProvider* resourceProvider);

    // 分配上传缓冲区
    std::tuple<Buffer*, size_t> getUploadBuffer(size_t requiredBytes,
                                               size_t alignment);

    // 帧结束时重置
    void reset();

private:
    ResourceProvider* fResourceProvider;
    std::vector<sk_sp<Buffer>> fBuffers;  // 当前帧的缓冲区
    size_t fCurrentBufferOffset = 0;
    static constexpr size_t kDefaultBufferSize = 64 * 1024;  // 64KB
};
```

## 公共 API 函数

### getUploadBuffer

```cpp
std::tuple<Buffer*, size_t> getUploadBuffer(size_t requiredBytes, size_t alignment);
```

**功能**: 分配指定大小和对齐的上传缓冲区空间。

**返回值**: (缓冲区指针, 偏移位置)

**策略**:
1. 尝试从当前缓冲区分配（如果空间足够）
2. 如果空间不足，创建新缓冲区
3. 对于大请求，创建独立的专用缓冲区

### reset

```cpp
void reset();
```

**功能**: 帧结束时重置管理器，释放或回收缓冲区。

## 内部实现细节

### 缓冲区分配策略

```cpp
std::tuple<Buffer*, size_t> getUploadBuffer(size_t requiredBytes, size_t alignment) {
    size_t alignedOffset = SkAlignTo(fCurrentBufferOffset, alignment);

    if (!fBuffers.empty()) {
        Buffer* currentBuffer = fBuffers.back().get();
        if (alignedOffset + requiredBytes <= currentBuffer->size()) {
            // 从当前缓冲区分配
            fCurrentBufferOffset = alignedOffset + requiredBytes;
            return {currentBuffer, alignedOffset};
        }
    }

    // 创建新缓冲区
    size_t newSize = std::max(requiredBytes, kDefaultBufferSize);
    sk_sp<Buffer> newBuffer = fResourceProvider->findOrCreateBuffer(
        newSize, BufferType::kXferCpuToGpu, AccessPattern::kHostVisible);

    fBuffers.push_back(newBuffer);
    fCurrentBufferOffset = requiredBytes;
    return {newBuffer.get(), 0};
}
```

### 缓冲区复用

`reset()` 后，缓冲区可能被资源缓存保留并在下一帧复用。

### 对齐处理

所有分配自动对齐到指定边界（通常为纹理行对齐需求）。

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `ResourceProvider` | 缓冲区创建 |
| `Buffer` | GPU 缓冲区对象 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `TextureUtils` | 纹理数据上传 |
| `Recorder` | 上传命令记录 |

## 设计模式与设计决策

### 池化模式

维护缓冲区池，复用已分配的缓冲区。

### 线性分配器

在当前缓冲区中线性分配，减少碎片。

### 关键设计决策

1. **默认缓冲区大小**: 64KB 平衡内存使用和分配频率
2. **自动扩展**: 大请求创建专用缓冲区
3. **帧级生命周期**: 缓冲区在帧结束时释放或回收
4. **对齐保证**: 自动处理对齐需求

## 性能考量

### 内存管理

1. **池化**: 减少缓冲区创建开销
2. **批量分配**: 多个小上传共享大缓冲区
3. **内存复用**: 跨帧复用缓冲区

### 上传效率

1. **线性写入**: CPU 端顺序写入缓冲区
2. **减少映射**: 每个缓冲区仅映射一次
3. **批处理**: 多个上传合并到同一缓冲区

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/Buffer.h` | GPU 缓冲区定义 |
| `src/gpu/graphite/ResourceProvider.h` | 资源创建 |
| `src/gpu/graphite/TextureUtils.h` | 纹理上传 |
| `src/gpu/graphite/Recorder.h` | 命令录制 |
