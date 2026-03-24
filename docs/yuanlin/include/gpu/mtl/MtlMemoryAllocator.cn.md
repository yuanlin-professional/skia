# MtlMemoryAllocator

> 源文件: `include/gpu/mtl/MtlMemoryAllocator.h`

## 概述
MtlMemoryAllocator 定义了 Skia Metal 后端的内存分配器抽象接口。该文件提供了 Metal 缓冲区和纹理的内存管理抽象,允许客户端自定义内存分配策略,实现资源池化、内存跟踪等高级功能,是 Skia Metal GPU 后端的核心内存管理组件。

## 架构位置
该文件位于 Skia 的 GPU 抽象层中,属于 `skgpu` 命名空间,专门服务于 Metal 后端实现。它为 Ganesh 和 Graphite 两种 GPU 架构提供统一的 Metal 内存管理接口,位于平台抽象层和具体 Metal 实现之间。

## 主要类与结构体

### MtlAlloc
Metal 内存分配的抽象句柄类,继承自 `SkRefCnt`。

**继承关系**: `SkRefCnt` → `MtlAlloc`

**设计特点**:
- 纯抽象类,不包含公共成员变量
- 使用引用计数管理生命周期 (`sk_sp<MtlAlloc>`)
- 不透明设计,内部实现可存储 Metal 分配器的私有数据
- 虚析构函数确保正确释放派生类资源

**用途**:
- 跟踪 Metal 资源的内存分配信息
- 关联缓冲区/纹理与其底层内存
- 实现自定义内存管理策略 (如资源池、内存预算)

### MtlMemoryAllocator
Metal 内存分配器接口,定义缓冲区和纹理的创建方法。

**继承关系**: `SkRefCnt` → `MtlMemoryAllocator`

**设计特点**:
- 仅在 Objective-C 环境中定义完整接口 (`#ifdef __OBJC__`)
- 纯虚方法,必须由客户端实现
- 使用 Metal 原生类型 (`id<MTLBuffer>`, `id<MTLTexture>`)
- 输出参数返回分配信息 (`sk_sp<MtlAlloc>*`)

## 公共 API 函数

### `newBufferWithLength`
```cpp
virtual id<MTLBuffer> newBufferWithLength(
    NSUInteger length,
    MTLResourceOptions options,
    sk_sp<MtlAlloc>* allocation) = 0;
```
- **功能**: 创建指定大小和选项的 Metal 缓冲区
- **参数**:
  - `length`: 缓冲区字节大小
  - `options`: Metal 资源选项标志 (存储模式、缓存模式、危险追踪等)
  - `allocation`: 输出参数,返回分配信息句柄
- **返回值**: Metal 缓冲区对象,失败返回 nil
- **职责**: 实现需要创建 MTLBuffer 并关联分配信息

**典型 options 组合**:
- `MTLResourceStorageModeShared`: 共享内存,CPU/GPU 都可访问
- `MTLResourceStorageModePrivate`: 私有内存,仅 GPU 可访问
- `MTLResourceStorageModeManaged`: 托管内存 (macOS 特有)
- `MTLResourceCPUCacheModeWriteCombined`: 写合并模式,优化 CPU 顺序写

### `newTextureWithDescriptor`
```cpp
virtual id<MTLTexture> newTextureWithDescriptor(
    MTLTextureDescriptor* texDesc,
    sk_sp<MtlAlloc>* allocation) = 0;
```
- **功能**: 根据描述符创建 Metal 纹理
- **参数**:
  - `texDesc`: Metal 纹理描述符 (格式、大小、mipmap、用途等)
  - `allocation`: 输出参数,返回分配信息句柄
- **返回值**: Metal 纹理对象,失败返回 nil
- **职责**: 实现需要创建 MTLTexture 并关联分配信息

**描述符关键属性**:
- `textureType`: 2D、3D、Cube 等
- `pixelFormat`: RGBA8Unorm、BGRA8Unorm 等
- `width/height/depth`: 纹理尺寸
- `mipmapLevelCount`: Mipmap 级数
- `usage`: 着色器读取、渲染目标、像素格式视图等

## 内部实现细节

### 平台限定编译
```cpp
#ifdef __APPLE__
    // 定义 MtlAlloc 基类
    #ifdef __OBJC__
        // 定义 MtlMemoryAllocator 完整接口
    #endif
#endif
```
**设计原因**:
- `MtlAlloc` 不依赖 Objective-C,可在 C++ 代码中使用
- `MtlMemoryAllocator` 使用 Metal 框架类型,仅在 Objective-C/Objective-C++ 中可用
- 允许非 Apple 平台编译 (接口为空)

### 分配信息的生命周期管理
通过智能指针 `sk_sp<MtlAlloc>` 管理:
1. **创建时**: 分配器实现创建 `MtlAlloc` 派生对象并包装成 `sk_sp`
2. **使用时**: Skia 持有智能指针引用,与 Metal 资源关联
3. **销毁时**: Metal 资源释放后,`sk_sp` 引用计数归零,自动释放分配信息

### 分离的分配跟踪
设计将 Metal 对象创建和分配跟踪分离:
- **Metal 对象**: 由 Metal 框架管理,通过 ARC 或手动引用计数
- **分配信息**: 由 `MtlAlloc` 跟踪,可包含池化、统计、调试信息

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkRefCnt.h | 引用计数基类 |
| Metal.framework | MTLBuffer、MTLTexture、MTLResourceOptions 等类型 |

### 被依赖的模块
- Metal 后端上下文: 初始化时提供分配器实例
- Skia GPU 资源类: 纹理、缓冲区创建时调用分配接口
- Metal 后端实现: 资源管理、内存统计

## 设计模式与设计决策

### 抽象工厂模式 (Abstract Factory)
`MtlMemoryAllocator` 作为抽象工厂创建 Metal 资源:
- **产品族**: `MTLBuffer` 和 `MTLTexture`
- **具体工厂**: 客户端提供的实现类
- **产品跟踪**: 通过 `MtlAlloc` 关联额外信息

### 策略模式 (Strategy Pattern)
允许客户端插入自定义内存管理策略:
- **默认策略**: 直接调用 `MTLDevice` 的创建方法
- **自定义策略**: 资源池化、内存预算控制、延迟分配
- **上下文**: Skia Metal 上下文持有分配器引用

### 不透明指针模式 (Opaque Pointer)
`MtlAlloc` 作为不透明句柄:
- Skia 核心不需要知道分配信息的具体内容
- 客户端可在派生类中存储任意私有数据
- 保持接口稳定性,内部实现可灵活变化

## 性能考量

### 缓冲区存储模式选择
- **Private 模式**: GPU 独占,最佳性能,用于大型静态资源
- **Shared 模式**: CPU/GPU 共享,易用但性能较差,用于小型动态数据
- **Managed 模式** (macOS): 自动同步,用于 CPU 写入 + GPU 读取场景

### 纹理内存优化
- **像素格式压缩**: 使用 PVRTC、ASTC 等压缩格式减少内存占用
- **Mipmap 控制**: 只在需要时生成 mipmap,避免浪费 1/3 额外内存
- **瞬态纹理**: 使用 `MTLStorageModeMemoryless` 用于渲染目标 (iOS/tvOS)

### 内存对齐
Metal 有特定的对齐要求:
- 缓冲区偏移: 通常 256 字节对齐 (常量缓冲区)
- 纹理行对齐: 取决于像素格式
- 实现应考虑对齐以避免性能损失

### 资源池化示例
```cpp
class PooledMtlAllocator : public MtlMemoryAllocator {
    std::map<size_t, std::vector<id<MTLBuffer>>> fBufferPool;

    id<MTLBuffer> newBufferWithLength(NSUInteger length,
                                       MTLResourceOptions options,
                                       sk_sp<MtlAlloc>* allocation) override {
        // 尝试从池中复用
        if (!fBufferPool[length].empty()) {
            id<MTLBuffer> buffer = fBufferPool[length].back();
            fBufferPool[length].pop_back();
            return buffer;
        }
        // 创建新缓冲区
        return [fDevice newBufferWithLength:length options:options];
    }
};
```

## 平台相关说明

### iOS/tvOS 特性
- **Memoryless 存储**: 用于瞬态渲染目标,不占用内存预算
- **共享事件**: Metal 2+ 支持 CPU-GPU 同步
- **资源堆**: Metal 2+ 支持子分配

### macOS 特性
- **统一内存** (Apple Silicon): Private 和 Shared 性能差距减小
- **Managed 模式**: Intel Mac 需要,Apple Silicon 已弃用
- **更大的内存预算**: 桌面级 GPU 内存

### 跨平台兼容性
```cpp
#if TARGET_OS_IPHONE
    options = MTLResourceStorageModeShared;  // iOS 默认
#else
    options = MTLResourceStorageModeManaged; // macOS (Intel)
#endif
```

## 典型实现示例

### 基础实现
```cpp
class SimpleMtlAllocator : public skgpu::MtlMemoryAllocator {
public:
    SimpleMtlAllocator(id<MTLDevice> device) : fDevice(device) {}

    id<MTLBuffer> newBufferWithLength(NSUInteger length,
                                       MTLResourceOptions options,
                                       sk_sp<MtlAlloc>* allocation) override {
        id<MTLBuffer> buffer = [fDevice newBufferWithLength:length options:options];
        *allocation = sk_make_sp<SimpleMtlAlloc>();
        return buffer;
    }

    id<MTLTexture> newTextureWithDescriptor(MTLTextureDescriptor* texDesc,
                                             sk_sp<MtlAlloc>* allocation) override {
        id<MTLTexture> texture = [fDevice newTextureWithDescriptor:texDesc];
        *allocation = sk_make_sp<SimpleMtlAlloc>();
        return texture;
    }

private:
    id<MTLDevice> fDevice;

    class SimpleMtlAlloc : public MtlAlloc {
        ~SimpleMtlAlloc() override = default;
    };
};
```

### 带统计的实现
```cpp
class TrackedMtlAlloc : public skgpu::MtlAlloc {
public:
    TrackedMtlAlloc(size_t size) : fSize(size) {
        gTotalAllocated += size;
    }
    ~TrackedMtlAlloc() override {
        gTotalAllocated -= fSize;
    }
    size_t size() const { return fSize; }

private:
    size_t fSize;
    static std::atomic<size_t> gTotalAllocated;
};
```

## 使用场景

### 场景 1: 创建顶点缓冲区
```objc
sk_sp<skgpu::MtlMemoryAllocator> allocator = getSkiaAllocator();
sk_sp<skgpu::MtlAlloc> alloc;

id<MTLBuffer> vertexBuffer = allocator->newBufferWithLength(
    vertexDataSize,
    MTLResourceStorageModeShared | MTLResourceCPUCacheModeWriteCombined,
    &alloc
);

memcpy(vertexBuffer.contents, vertexData, vertexDataSize);
```

### 场景 2: 创建渲染目标纹理
```objc
MTLTextureDescriptor* desc = [MTLTextureDescriptor
    texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm
    width:1920 height:1080 mipmapped:NO];
desc.usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead;

sk_sp<skgpu::MtlAlloc> alloc;
id<MTLTexture> renderTarget = allocator->newTextureWithDescriptor(desc, &alloc);
```

## 错误处理

### 内存分配失败
```cpp
id<MTLBuffer> buffer = allocator->newBufferWithLength(length, options, &alloc);
if (!buffer) {
    // 处理失败情况:
    // 1. 清理缓存释放内存
    // 2. 降低资源质量
    // 3. 抛出异常或返回错误码
}
```

### 无效描述符
Metal 在创建纹理时会验证描述符:
- 不支持的像素格式
- 超出设备限制的尺寸
- 不兼容的用途标志组合

实现应捕获这些错误并返回 nil。

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/mtl/MtlBackendContext.h | 使用此接口初始化 Metal 上下文 |
| include/gpu/mtl/MtlTypes.h | Metal 相关的 Skia 类型定义 |
| src/gpu/mtl/GrMtlGpu.h | Ganesh Metal 后端实现 |
| src/gpu/graphite/mtl/MtlGraphiteContext.h | Graphite Metal 后端实现 |

## 常见问题与解决方案

### 问题 1: 内存泄漏
**症状**: 内存使用持续增长
**原因**: `MtlAlloc` 引用计数未正确释放或 Metal 对象未释放
**解决**: 使用 Instruments 的 Allocations 工具追踪,确保 `sk_sp` 正确管理生命周期

### 问题 2: 跨平台崩溃
**症状**: macOS 上正常,iOS 上崩溃
**原因**: 使用了平台不支持的存储模式 (如 iOS 上的 Managed 模式)
**解决**: 使用编译时或运行时检查选择合适的存储模式

### 问题 3: 性能下降
**症状**: 频繁小缓冲区分配导致帧率下降
**原因**: 直接分配未使用池化
**解决**: 实现资源池,复用相同大小的缓冲区

## 最佳实践

1. **使用 Shared 模式的写合并缓存**: 提升 CPU 顺序写入性能
2. **为静态资源使用 Private 模式**: 减少同步开销
3. **实现资源池**: 减少分配/释放开销
4. **监控内存预算**: 使用 Metal 的内存推荐大小 API
5. **延迟创建纹理 mipmap**: 仅在需要时生成
6. **使用 Memoryless 存储** (iOS): 用于不需要保存的渲染目标

## 扩展建议

虽然当前接口简洁,实际项目可能需要扩展:
- 添加 `freeBuffer/freeTexture` 方法实现池化
- 提供内存统计接口 (类似 Vulkan 版本的 `totalAllocatedAndUsedMemory`)
- 支持 Metal 资源堆 (Heap) 的子分配
- 实现内存预算管理,防止超出设备限制
