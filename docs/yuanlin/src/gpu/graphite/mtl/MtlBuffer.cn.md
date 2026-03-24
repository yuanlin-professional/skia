# MtlBuffer

> 源文件
> - src/gpu/graphite/mtl/MtlBuffer.h
> - src/gpu/graphite/mtl/MtlBuffer.mm

## 概述

`MtlBuffer` 是 Skia Graphite Metal 后端的缓冲区实现类，封装了 `MTLBuffer` 对象并提供统一的缓冲区管理接口。该类继承自 `Buffer` 基类，负责创建、映射、取消映射和释放 Metal 缓冲区资源。它根据访问模式和平台特性选择合适的存储模式（Private、Shared、Managed），优化内存管理和数据传输性能。

`MtlBuffer` 是 GPU 资源管理的基础组件，用于存储顶点数据、索引数据、uniform 缓冲区和存储缓冲区等各类 GPU 数据。

## 架构位置

`MtlBuffer` 位于 Skia Graphite Metal 后端的资源管理层：

```
应用层绘制调用
    ↓
Recorder / DrawContext
    ↓
ResourceProvider
    ↓
MtlResourceProvider
    ↓
MtlBuffer（缓冲区实现）← 当前组件
    ↓
MTLBuffer（Metal 原生对象）
```

它是 `Buffer` 抽象接口的 Metal 平台实现，与 `MtlTexture`、`MtlSampler` 等共同构成资源管理体系。

## 主要类与结构体

### MtlBuffer 类

```cpp
class MtlBuffer final : public Buffer {
public:
    static sk_sp<Buffer> Make(const MtlSharedContext*,
                              size_t size,
                              BufferType type,
                              AccessPattern accessPattern,
                              std::string_view label);

    id<MTLBuffer> mtlBuffer() const { return fBuffer.get(); }

private:
    sk_cfp<id<MTLBuffer>> fBuffer;  // 持有 Metal 缓冲区对象
};
```

## 公共 API 函数

### 工厂方法

```cpp
static sk_sp<Buffer> Make(const MtlSharedContext* sharedContext,
                          size_t size,
                          BufferType type,
                          AccessPattern accessPattern,
                          std::string_view label);
```

创建 Metal 缓冲区，根据 `accessPattern` 选择存储模式：
- `AccessPattern::kHostVisible`：CPU 可访问（Shared 或 Managed）
- 其他：GPU 独占（Private）

### Metal 对象访问

```cpp
id<MTLBuffer> mtlBuffer() const;
```

返回底层的 `MTLBuffer` 对象，供 Metal 命令编码器使用。

### 内存映射（继承自 Buffer）

```cpp
void* map();         // 映射缓冲区到 CPU 地址空间
void unmap();        // 取消映射
```

## 内部实现细节

### 存储模式选择

`Make` 方法根据平台和访问模式选择最优存储模式：

```cpp
NSUInteger options = 0;
if (accessPattern == AccessPattern::kHostVisible) {
#ifdef SK_BUILD_FOR_MAC
    if (mtlCaps.isMac()) {
        options |= MTLResourceStorageModeManaged;  // Mac 使用 Managed
    } else {
        options |= MTLResourceStorageModeShared;   // Apple Silicon 使用 Shared
    }
#else
    options |= MTLResourceStorageModeShared;       // iOS 使用 Shared
#endif
} else {
    options |= MTLResourceStorageModePrivate;      // GPU 独占
}
```

**存储模式说明**：
- **Private**：GPU 独占，CPU 不可访问，性能最高
- **Shared**：CPU 和 GPU 共享，同步开销小，适合 UMA 架构（Apple Silicon）
- **Managed**：Mac 专用，支持独立显存，需手动同步

### 内存映射实现

```cpp
void MtlBuffer::onMap() {
    if ((*fBuffer).storageMode == MTLStorageModePrivate) {
        return;  // Private 模式不可映射
    }
    fMapPtr = static_cast<char*>((*fBuffer).contents);
}
```

Private 缓冲区不支持映射，尝试映射会导致 `fMapPtr` 保持为 `nullptr`。

### 取消映射与同步

```cpp
void MtlBuffer::onUnmap() {
#ifdef SK_BUILD_FOR_MAC
    if ((*fBuffer).storageMode == MTLStorageModeManaged) {
        [*fBuffer didModifyRange: NSMakeRange(0, this->size())];  // 通知 GPU 更新
    }
#endif
    fMapPtr = nullptr;
}
```

Managed 模式下，CPU 修改后必须调用 `didModifyRange` 通知 Metal 驱动将数据同步到 GPU 显存。

### 资源释放

```cpp
void MtlBuffer::freeGpuData() {
    fBuffer.reset();  // 释放 MTLBuffer 引用
}
```

使用智能指针 `sk_cfp` 自动管理 Metal 对象生命周期。

### 调试标签

```cpp
void MtlBuffer::setBackendLabel(char const* label) {
#ifdef SK_ENABLE_MTL_DEBUG_INFO
    NSString* labelStr = @(label);
    this->mtlBuffer().label = labelStr;
#endif
}
```

在调试构建中为 Metal 对象设置可读名称，便于 Xcode GPU 调试器识别。

## 依赖关系

### 直接依赖

- **Buffer**：缓冲区抽象基类
- **MtlSharedContext**：Metal 共享上下文，提供设备和能力查询
- **MTLBuffer**：Metal 原生缓冲区对象
- **MtlCaps**：能力查询，判断 GPU 家族

### 被依赖

- **MtlResourceProvider**：通过 `MtlBuffer::Make` 创建缓冲区
- **MtlCommandBuffer**：使用 `mtlBuffer()` 绑定到命令编码器
- **DrawBufferManager**：使用缓冲区存储绘制数据
- **UploadBufferManager**：使用缓冲区传输纹理数据

## 设计模式与设计决策

### 工厂模式

使用静态工厂方法 `Make` 而非公共构造函数，确保缓冲区创建失败时返回 `nullptr`：

```cpp
if (size <= 0) {
    return nullptr;  // 参数验证
}
```

### 智能指针管理

使用 `sk_cfp<id<MTLBuffer>>` 自动管理 Metal 对象的引用计数，避免手动 retain/release。

### 平台适配抽象

通过编译时宏 `SK_BUILD_FOR_MAC` 和运行时查询 `mtlCaps.isMac()` 实现跨平台适配：

```cpp
#ifdef SK_BUILD_FOR_MAC
    if (mtlCaps.isMac()) {
        // Mac 独立显存逻辑
    } else {
        // Apple Silicon UMA 逻辑
    }
#else
    // iOS 逻辑
#endif
```

### Purgeable 资源标记

构造函数中设置 `reusableRequiresPurgeable` 标志：

```cpp
/*reusableRequiresPurgeable=*/(*buffer).storageMode != MTLStorageModePrivate
```

非 Private 缓冲区占用系统内存，需要标记为 purgeable 以支持内存压力下的回收。

## 性能考量

### 存储模式性能

| 存储模式 | CPU 访问 | GPU 访问 | 同步开销 | 适用场景 |
|---------|---------|---------|---------|---------|
| Private | 不可访问 | 最快 | 无 | 静态 GPU 数据 |
| Shared | 快速 | 较快 | 无 | UMA 架构动态数据 |
| Managed | 较慢 | 快速 | 需手动同步 | Mac 独立显存 |

### Shared 模式优势（Apple Silicon）

Apple Silicon 的统一内存架构（UMA）使得 Shared 模式成为最优选择：
- CPU 和 GPU 访问同一物理内存
- 零拷贝，避免数据传输
- 无需同步调用

### Managed 模式开销（Mac）

传统 Mac 的独立显存架构下，Managed 模式需要额外的同步：

```cpp
[fBuffer didModifyRange: NSMakeRange(0, size)];  // 触发 PCIe 传输
```

这会引入数百微秒的延迟，因此应批量更新数据以摊薄开销。

### Private 模式最优性能

对于 GPU 独占数据（如静态几何、预生成纹理），Private 模式提供最高性能：
- GPU 可自由优化数据布局
- 避免缓存一致性开销
- 支持压缩存储

### 内存对齐

Metal 对缓冲区绑定的对齐要求（通过 `MtlCaps` 设置）：
- Mac：256 字节对齐（Uniform Buffer）
- Apple Silicon：16 字节对齐
- Transfer Buffer：Mac 4 字节，iOS 1 字节

错误的对齐会导致绑定失败或性能下降。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/Buffer.h` | 缓冲区抽象基类 |
| `src/gpu/graphite/mtl/MtlSharedContext.h` | Metal 共享上下文 |
| `src/gpu/graphite/mtl/MtlResourceProvider.h` | Metal 资源提供者 |
| `src/gpu/graphite/mtl/MtlCommandBuffer.h` | Metal 命令缓冲区，使用 MtlBuffer |
| `src/gpu/graphite/mtl/MtlCaps.h` | Metal 能力查询 |
| `src/gpu/graphite/DrawBufferManager.h` | 绘制缓冲区管理 |
| `src/gpu/graphite/UploadBufferManager.h` | 上传缓冲区管理 |
