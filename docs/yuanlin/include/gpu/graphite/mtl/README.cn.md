# include/gpu/graphite/mtl - Graphite Metal 后端公共 API

## 概述

`include/gpu/graphite/mtl` 目录包含 Graphite 渲染引擎中 Apple Metal 后端的公共 API。
Metal 后端是 Apple 平台上 Graphite 的主要渲染后端，支持 macOS、iOS、iPadOS 和 tvOS。

`MtlBackendContext` 封装了 Metal 的核心设备对象 (`MTLDevice`) 和命令队列 (`MTLCommandQueue`)，
使用 Core Foundation 的 `CFTypeRef` 包装以在 C++ 代码中引用 Objective-C 对象。

`MtlTextureInfo` 继承自 `TextureInfo::Data`，封装了 `MTLPixelFormat`、`MTLTextureUsage`、
`MTLStorageMode` 和 `framebufferOnly` 等 Metal 特有的纹理属性。由于 Metal API 基于
Objective-C，`MtlGraphiteTypes.h`（完整版）仅在 `__OBJC__` 编译环境下可用，
而 `MtlGraphiteTypes_cpp.h` 提供了 C++ 兼容的子集。

Graphite 的 Metal 后端利用了 Metal 的低级特性，如命令缓冲区并行编码、图像共享和管线状态
缓存，以实现高效的 GPU 渲染。

## 架构图

```
include/gpu/graphite/mtl/
    |
    +-- MtlBackendContext.h        <-- Metal 后端上下文 + 工厂方法
    |       |
    |       +-- MtlBackendContext      (CFTypeRef fDevice, fQueue)
    |       +-- ContextFactory::MakeMetal()
    |
    +-- MtlGraphiteTypes.h         <-- Metal 纹理类型（需要 __OBJC__）
    |       |
    |       +-- MtlTextureInfo         (MTLPixelFormat, Usage, StorageMode)
    |
    +-- MtlGraphiteTypes_cpp.h     <-- C++ 兼容的类型子集
    +-- MtlGraphiteTypesUtils.h    <-- 类型工具（重定向）
    +-- MtlGraphiteUtils.h         <-- 工具函数（重定向）
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `MtlBackendContext.h` | `MtlBackendContext` 结构体和 `ContextFactory::MakeMetal()` |
| `MtlGraphiteTypes.h` | `MtlTextureInfo` 类（完整版，需 Objective-C） |
| `MtlGraphiteTypes_cpp.h` | C++ 兼容的 Metal 类型定义 |
| `MtlGraphiteTypesUtils.h` | Metal 类型辅助工具（重定向头文件） |
| `MtlGraphiteUtils.h` | Metal 工具函数（重定向头文件） |

## 关键类与函数

### `MtlBackendContext` 结构体

```cpp
struct MtlBackendContext {
    sk_cfp<CFTypeRef> fDevice;  // MTLDevice* (通过 CFTypeRef 桥接)
    sk_cfp<CFTypeRef> fQueue;   // MTLCommandQueue* (通过 CFTypeRef 桥接)
};
```

### `MtlTextureInfo` 类 (需要 __OBJC__)

```cpp
class MtlTextureInfo final : public TextureInfo::Data {
    MTLPixelFormat  fFormat;
    MTLTextureUsage fUsage;
    MTLStorageMode  fStorageMode;
    bool            fFramebufferOnly;

    static constexpr BackendApi kBackend = BackendApi::kMetal;
};
```

### 上下文创建

```cpp
namespace skgpu::graphite::ContextFactory {
    std::unique_ptr<Context> MakeMetal(const MtlBackendContext&, const ContextOptions&);
}
```

### 后端纹理工厂 (MtlGraphiteTypes_cpp.h)

```cpp
namespace skgpu::graphite::BackendTextures {
    BackendTexture MakeMetal(SkISize, CFTypeRef mtlTexture);
}

namespace skgpu::graphite::TextureInfos {
    TextureInfo MakeMetal(const MtlTextureInfo&);
}
```

## 依赖关系

- **上游依赖**: `include/gpu/graphite/Context.h`, `include/gpu/graphite/TextureInfo.h`
- **上游依赖**: `include/ports/SkCFObject.h` (Core Foundation 智能指针)
- **系统依赖**: Apple Metal 框架 (`<Metal/Metal.h>`)
- **条件编译**: `__OBJC__` 控制完整 Metal 类型的可见性
- **平台**: macOS, iOS, iPadOS, tvOS
- **实现代码**: `src/gpu/graphite/mtl/`

## 相关文档与参考

- `include/gpu/graphite/` - Graphite 引擎主目录
- `include/gpu/mtl/` - 共享 Metal 类型（Ganesh + Graphite）
- `include/gpu/ganesh/mtl/` - Ganesh Metal 后端
- Apple Metal 文档: https://developer.apple.com/metal/
