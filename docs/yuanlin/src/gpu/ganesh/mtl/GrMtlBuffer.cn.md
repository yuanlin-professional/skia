# GrMtlBuffer

> 源文件
> - src/gpu/ganesh/mtl/GrMtlBuffer.h
> - src/gpu/ganesh/mtl/GrMtlBuffer.mm

## 概述

`GrMtlBuffer` 是 Skia 图形库中 Metal 后端的缓冲区管理类,继承自 `GrGpuBuffer` 基类。它封装了 Metal 的 `id<MTLBuffer>` 对象,用于管理顶点缓冲区、索引缓冲区、Uniform 缓冲区、间接绘制缓冲区以及传输缓冲区。该类根据缓冲区的访问模式(静态/动态)选择不同的存储策略,并提供高效的数据更新和映射机制。

## 架构位置

`GrMtlBuffer` 位于 Skia 的 GPU Ganesh 渲染架构中的 Metal 后端资源管理层,是连接 CPU 数据和 GPU 内存的桥梁。

```
Skia Graphics Library
└── src/gpu/ganesh/
    ├── GrGpuBuffer          (抽象缓冲区基类)
    └── mtl/
        ├── GrMtlGpu         (Metal GPU管理器)
        ├── GrMtlBuffer      (Metal缓冲区) ← 当前类
        └── GrMtlCommandBuffer (命令缓冲区)
```

## 主要类与结构体

### GrMtlBuffer

Metal 缓冲区封装类,管理各类 GPU 缓冲区资源。

**继承关系:**
- 基类: `GrGpuBuffer`
- 派生类: 无(终端类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fMtlBuffer` | `id<MTLBuffer>` | Metal 缓冲区对象引用 |
| `fIsDynamic` | `bool` | 是否为动态缓冲区(影响存储模式和更新策略) |

## 公共 API 函数

### 工厂方法

```cpp
static sk_sp<GrMtlBuffer> Make(
    GrMtlGpu* gpu,
    size_t size,
    GrGpuBufferType intendedType,
    GrAccessPattern accessPattern
);
```
创建指定类型和访问模式的 Metal 缓冲区。

**参数说明:**
- `intendedType`: 缓冲区类型(顶点/索引/Uniform/间接绘制/传输)
- `accessPattern`: 访问模式(kStatic/kDynamic/kStream)

### 访问器

```cpp
id<MTLBuffer> mtlBuffer() const;
```
获取底层 Metal 缓冲区对象。

## 内部实现细节

### 存储模式选择策略

构造函数根据访问模式和平台选择最优存储模式:

```cpp
NSUInteger options = 0;
if (fIsDynamic) {
    #ifdef SK_BUILD_FOR_MAC
        if (gpu->mtlCaps().isMac()) {
            options |= MTLResourceStorageModeManaged;  // Mac: 管理模式
        } else {
            options |= MTLResourceStorageModeShared;   // Apple Silicon: 共享模式
        }
    #else
        options |= MTLResourceStorageModeShared;       // iOS: 共享模式
    #endif
} else {
    options |= MTLResourceStorageModePrivate;          // 静态缓冲区: 私有模式
}
```

**存储模式说明:**
- **Private:** GPU 专用,无法从 CPU 访问,最高效
- **Shared:** CPU-GPU 共享,零拷贝,适合频繁更新
- **Managed:** Mac 特有,需要显式同步但提供更好性能

### 数据更新策略

`onUpdateData` 方法根据缓冲区类型选择更新方式:

#### 动态缓冲区(Direct Update)
```cpp
if (fIsDynamic) {
    this->internalMap();                               // 映射缓冲区
    memcpy(SkTAddOffset<void>(fMapPtr, offset), src, size);
    this->internalUnmap(offset, size);                 // 解映射并同步
    return true;
}
```

#### 静态缓冲区(Transfer Buffer)
使用中间缓冲区进行传输:
```cpp
// 1. 分配暂存缓冲区
GrStagingBufferManager::Slice slice =
    stagingBufferManager()->allocateStagingBufferSlice(transferSize);

// 2. 拷贝数据到暂存区
memcpy(slice.fOffsetMapPtr, src, size);

// 3. 使用 Blit 命令拷贝到目标缓冲区
id<MTLBlitCommandEncoder> blitEncoder = cmdBuffer->getBlitCommandEncoder();
[blitEncoder copyFromBuffer:transferBuffer
               sourceOffset:slice.fOffset
                   toBuffer:fMtlBuffer
          destinationOffset:offset
                       size:transferSize];
```

### 映射与同步

#### Mac 的 Managed 模式同步
```cpp
void GrMtlBuffer::internalUnmap(size_t writtenOffset, size_t writtenSize) {
    #ifdef SK_BUILD_FOR_MAC
        if (this->mtlGpu()->mtlCaps().isMac() && writtenSize) {
            // 通知 Metal 驱动指定范围已修改
            [fMtlBuffer didModifyRange:NSMakeRange(writtenOffset, writtenSize)];
        }
    #endif
    fMapPtr = nullptr;
}
```

### 缓冲区清零操作

```cpp
bool GrMtlBuffer::onClearToZero() {
    id<MTLBlitCommandEncoder> blitEncoder = cmdBuffer->getBlitCommandEncoder();
    [blitEncoder fillBuffer:fMtlBuffer range:NSMakeRange(0, size) value:0];
    cmdBuffer->addGrBuffer(sk_ref_sp(this));  // 添加依赖追踪
    return true;
}
```

### 对齐处理

缓冲区大小自动对齐到平台要求:
```cpp
size = SkAlignTo(size, gpu->mtlCaps().getMinBufferAlignment());
```
- **Mac:** 4 字节对齐
- **iOS/Apple Silicon:** 1 字节对齐(无限制)

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrGpuBuffer` | 基类,提供跨平台缓冲区接口 |
| `GrMtlGpu` | GPU 管理器,提供设备和命令缓冲区 |
| `GrMtlCommandBuffer` | 命令编码器,执行 Blit 操作 |
| `GrMtlCaps` | 能力查询,获取对齐要求 |
| `GrStagingBufferManager` | 暂存缓冲区管理 |
| `Metal/Metal.h` | Metal API |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrMtlOpsRenderPass` | 绑定顶点/索引缓冲区 |
| `GrMtlPipelineState` | 绑定 Uniform 缓冲区 |
| `GrMtlGpu` | 读取像素到传输缓冲区 |
| `GrMtlTexture` | 纹理数据传输源 |

## 设计模式与设计决策

### 策略模式
根据 `fIsDynamic` 标志在运行时选择不同的更新策略:
- **动态缓冲区:** 直接映射 + memcpy
- **静态缓冲区:** 暂存缓冲区 + Blit 传输

### 延迟资源释放
析构函数使用断言而非直接释放,确保资源通过 `onRelease()` 或 `onAbandon()` 正确清理:
```cpp
GrMtlBuffer::~GrMtlBuffer() {
    SkASSERT(!fMtlBuffer);  // 确保已释放
    SkASSERT(!fMapPtr);
}
```

### 平台适配策略
通过条件编译和运行时检查实现跨平台优化:
- **编译时:** `#ifdef SK_BUILD_FOR_MAC`
- **运行时:** `gpu->mtlCaps().isMac()`

### 调试模式标签
在调试模式下为不同类型缓冲区添加描述性标签:
```cpp
#ifdef SK_ENABLE_MTL_DEBUG_INFO
NSString* kBufferTypeNames[] = {
    @"Vertex", @"Index", @"Indirect",
    @"Xfer CPU to GPU", @"Xfer GPU to CPU", @"Uniform"
};
fMtlBuffer.label = kBufferTypeNames[(int)intendedType];
#endif
```

## 性能考量

### 零拷贝优化
- **共享模式(iOS/Apple Silicon):** CPU 和 GPU 共享同一物理内存,无需数据传输
- **私有模式(静态数据):** 数据驻留在 GPU 专用内存,访问延迟最低

### 批量传输
静态缓冲区更新使用暂存缓冲区批处理:
- 减少内存分配次数
- 利用 Blit 命令的 DMA 加速
- 支持传输对齐优化

### 内存对齐
自动对齐到硬件要求避免:
- 未对齐访问导致的性能惩罚
- 潜在的驱动层内存浪费

### Managed 模式的同步开销
Mac 上使用 `didModifyRange:` 精确指定修改范围,避免全缓冲区同步:
```cpp
// 仅同步实际修改的区域
[fMtlBuffer didModifyRange:NSMakeRange(writtenOffset, writtenSize)];
```

### 缓存一致性
使用 `addGrBuffer` 将缓冲区添加到命令缓冲区依赖列表,确保:
- 缓冲区在命令执行期间不被释放
- 防止写后写冲突

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrGpuBuffer.h` | 基类 | 平台无关缓冲区接口 |
| `src/gpu/ganesh/mtl/GrMtlGpu.h` | 管理者 | 创建和持有缓冲区 |
| `src/gpu/ganesh/mtl/GrMtlCommandBuffer.h` | 协作 | 提供 Blit 编码器 |
| `src/gpu/ganesh/mtl/GrMtlCaps.h` | 查询 | 获取对齐和能力信息 |
| `src/gpu/ganesh/GrStagingBufferManager.h` | 依赖 | 管理暂存缓冲区 |
| `src/gpu/ganesh/mtl/GrMtlUniformHandler.h` | 使用者 | 处理 Uniform 缓冲区 |
