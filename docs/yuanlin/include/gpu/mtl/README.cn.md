# include/gpu/mtl - Metal 公共 API

## 概述

`include/gpu/mtl` 目录包含 Skia 中 Metal 相关的公共类型定义，这些类型被 Ganesh 和 Graphite
两个渲染引擎共同使用。相较于 Vulkan 的公共目录，Metal 的公共目录非常简洁，仅包含一个内存分配器
的抽象接口定义。

Metal 的内存分配器 `MtlMemoryAllocator` 允许客户端自定义 Metal 缓冲区和纹理的分配策略。
与 Vulkan 不同的是，Metal 的内存管理由驱动程序自动处理，因此 Metal 分配器的接口更为简洁，
主要围绕 `MTLBuffer` 和 `MTLTexture` 的创建展开。

需要注意的是，由于 Metal API 基于 Objective-C，部分接口需要在 Objective-C 编译环境下才可用。
头文件中通过 `__OBJC__` 和 `__APPLE__` 预编译宏来控制条件编译。

此目录下的类型主要为高级用户设计，大多数使用 Metal 后端的应用程序不需要自定义内存分配器。
Skia 内部会提供默认的实现。

## 架构图

```
include/gpu/mtl/
    |
    +-- MtlMemoryAllocator.h    <-- Metal 内存分配器抽象接口
            |
            +-- MtlAlloc              (内存分配记录基类)
            +-- MtlMemoryAllocator    (分配器抽象类, 需要 __OBJC__)
                    |
                    +-- newBufferWithLength()
                    +-- newTextureWithDescriptor()

                +--> include/gpu/ganesh/mtl/   (Ganesh Metal 后端)
                +--> include/gpu/graphite/mtl/ (Graphite Metal 后端)
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `MtlMemoryAllocator.h` | Metal 内存分配器的抽象基类 |
| `BUILD.bazel` | Bazel 构建配置 |

## 关键类与函数

### `skgpu::MtlAlloc` 类

```cpp
class MtlAlloc : public SkRefCnt {
public:
    ~MtlAlloc() override = default;
};
```

内存分配记录的基类，用于跟踪单次分配。客户端在实现 `MtlMemoryAllocator` 时，
可以通过派生此类来附加自定义的分配元数据。

### `skgpu::MtlMemoryAllocator` 类 (仅在 __OBJC__ 下可用)

```cpp
class MtlMemoryAllocator : public SkRefCnt {
    virtual id<MTLBuffer> newBufferWithLength(NSUInteger length,
                                              MTLResourceOptions options,
                                              sk_sp<MtlAlloc>* allocation) = 0;

    virtual id<MTLTexture> newTextureWithDescriptor(MTLTextureDescriptor* texDesc,
                                                     sk_sp<MtlAlloc>* allocation) = 0;
};
```

Metal 内存分配器的核心接口。两个纯虚方法分别用于创建 Metal 缓冲区和纹理。
每次分配时，分配器需要通过 `allocation` 参数返回一个 `MtlAlloc` 对象，
Skia 会持有该对象的引用直到资源被释放。

## 依赖关系

- **上游依赖**: `include/core/SkRefCnt.h`
- **系统依赖**: Apple Metal 框架 (`<Metal/Metal.h>`)
- **平台限制**: 仅在 Apple 平台 (`__APPLE__`) 可用
- **被引用**: `include/gpu/ganesh/mtl/` (Ganesh Metal 后端)
- **被引用**: `include/gpu/graphite/mtl/` (Graphite Metal 后端)

## 相关文档与参考

- `include/gpu/ganesh/mtl/` - Ganesh 引擎的 Metal 后端 API
- `include/gpu/graphite/mtl/` - Graphite 引擎的 Metal 后端 API
- `include/gpu/GpuTypes.h` - GPU 共享基础类型
- Apple Metal 文档: https://developer.apple.com/metal/
