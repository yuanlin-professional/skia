# mtl - Skia GPU 通用 Metal 工具层

## 概述

`src/gpu/mtl` 目录包含 Skia 图形库中 Apple Metal 图形 API 的通用工具代码。这些代码是 Ganesh(旧版 GPU 后端)和 Graphite(新一代 GPU 后端)共享的 Metal 基础设施,提供了内存分配、着色器编译和像素格式工具等核心功能。

Metal 是 Apple 平台(iOS、macOS、tvOS)上的低级别 GPU 图形和计算 API。Skia 通过该目录中的共享代码层将 Metal 特定的功能抽象出来,使得 Ganesh 和 Graphite 可以复用相同的内存分配逻辑、着色器翻译管线和像素格式查询函数。这种分层设计避免了代码重复,确保两个后端在 Metal 交互层面保持一致。

内存分配方面,`MtlMemoryAllocatorImpl` 类实现了 `MtlMemoryAllocator` 接口,为 Metal 缓冲区和纹理提供分配服务。目前该实现是直接透传到 MTLDevice 的简单封装,预留了未来进行子分配(suballocation)优化的接口。

着色器编译方面,`MtlUtilsPriv.h` 提供了 `SkSLToMSL()` 函数,将 Skia 内部的 SkSL 着色器语言翻译为 Metal Shading Language (MSL)。该函数是 `SkSLToBackend()` 通用框架的 Metal 特化,调用 `SkSL::ToMetal` 代码生成器完成实际翻译。

像素格式工具函数则提供了 `MTLPixelFormat` 与 Skia 内部格式之间的查询和转换,涵盖通道映射、每块字节数、压缩格式检测和格式名称字符串化等功能。这些函数大部分仅被 Ganesh 使用,Graphite 有自己独立的格式管理。

## 架构图

```
+----------------------------------------------------------+
|                     Skia 应用层                           |
+----------------------------------------------------------+
        |                    |                    |
+-------v--------+  +-------v--------+  +-------v--------+
|  Ganesh/Metal  |  | Graphite/Metal |  |    通用 Skia    |
|  GPU 后端      |  |  GPU 后端      |  |    核心层       |
+-------+--------+  +-------+--------+  +----------------+
        |                    |
        +--------+-----------+
                 |
     +-----------v-----------+
     |   src/gpu/mtl (共享)  |
     |                       |
     |  +------------------+ |
     |  | MtlMemoryAlloc   | |  <-- 内存分配器
     |  | atorImpl         | |
     |  +------------------+ |
     |                       |
     |  +------------------+ |
     |  | SkSLToMSL()      | |  <-- SkSL -> MSL 翻译
     |  +------------------+ |
     |                       |
     |  +------------------+ |
     |  | MtlFormat*()     | |  <-- 像素格式工具
     |  | 系列函数         | |
     |  +------------------+ |
     +-----------+-----------+
                 |
     +-----------v-----------+
     |    Apple Metal API    |
     |  (MTLDevice,          |
     |   MTLBuffer,          |
     |   MTLTexture)         |
     +------------------------+
```

## 目录结构

```
src/gpu/mtl/
|-- BUILD.bazel                    # Bazel 构建配置 (Objective-C++ 库)
|-- MtlMemoryAllocatorImpl.h       # Metal 内存分配器实现 (头文件)
|-- MtlMemoryAllocatorImpl.mm      # Metal 内存分配器实现 (Objective-C++)
|-- MtlUtilsPriv.h                 # Metal 工具函数私有头文件
|-- MtlUtils.mm                    # Metal 工具函数实现 (Objective-C++)
```

## 关键类与函数

### `MtlMemoryAllocatorImpl` (MtlMemoryAllocatorImpl.h)

Metal 内存分配器的默认实现,继承自公共接口 `MtlMemoryAllocator`(定义在 `include/gpu/mtl/MtlMemoryAllocator.h`):

```objc
class MtlMemoryAllocatorImpl : public MtlMemoryAllocator {
public:
    // 工厂方法: 根据 MTLDevice 创建分配器
    static sk_sp<MtlMemoryAllocator> Make(id<MTLDevice>);

    // 分配 Metal 缓冲区
    id<MTLBuffer> newBufferWithLength(NSUInteger length,
                                      MTLResourceOptions options,
                                      sk_sp<skgpu::MtlAlloc>* allocation) override;

    // 分配 Metal 纹理
    id<MTLTexture> newTextureWithDescriptor(MTLTextureDescriptor* texDesc,
                                            sk_sp<skgpu::MtlAlloc>* allocation) override;
};
```

**内部 `Alloc` 类**: 继承自 `MtlAlloc`,作为分配跟踪句柄。当前实现为空壳,预留了子分配(suballocation)扩展点。

**当前实现特点**: 直接调用 `[fDevice newBufferWithLength:options:]` 和 `[fDevice newTextureWithDescriptor:]`,每次分配都是独立的 Metal 资源对象。未来可以在此层引入内存池化或子分配策略。

### `SkSLToMSL()` (MtlUtilsPriv.h)

SkSL 到 Metal Shading Language 的翻译入口:

```cpp
inline bool SkSLToMSL(const SkSL::ShaderCaps* caps,
                      const std::string& sksl,
                      SkSL::ProgramKind programKind,
                      const SkSL::ProgramSettings& settings,
                      SkSL::NativeShader* msl,
                      SkSL::ProgramInterface* outInterface,
                      ShaderErrorHandler* errorHandler);
```

该函数是 `SkSLToBackend()` 通用转换框架的薄封装,具体使用 `SkSL::ToMetal` 代码生成后端。错误通过 `ShaderErrorHandler` 回调处理。

### 像素格式工具函数 (MtlUtils.mm)

一组 `MTLPixelFormat` 查询函数:

| 函数 | 功能 |
|------|------|
| `MtlFormatIsCompressed(MTLPixelFormat)` | 检测是否为压缩格式(ETC2/BC1) |
| `MtlFormatChannels(MTLPixelFormat)` | 返回颜色通道标志位(RGBA等) |
| `MtlFormatBytesPerBlock(MTLPixelFormat)` | 返回每块的字节数 |
| `MtlFormatToCompressionType(MTLPixelFormat)` | 转换为 `SkTextureCompressionType` |
| `MtlFormatToString(MTLPixelFormat)` | 返回格式的可读名称字符串 |

**支持的格式**: 包括 RGBA8Unorm、R8Unorm、A8Unorm、BGRA8Unorm、B5G6R5Unorm、RGBA16Float、R16Float、RG8Unorm、RGB10A2Unorm、BGR10A2Unorm、ABGR4Unorm、RGBA8Unorm_sRGB、R16Unorm、RG16Unorm、ETC2_RGB8、RGBA16Unorm、RG16Float、Stencil8 等。macOS 额外支持 BC1_RGBA 格式(通过 `SK_BUILD_FOR_MAC` 宏控制)。

## 依赖关系

```
src/gpu/mtl/ 依赖:
  +-- Apple Metal Framework (<Metal/Metal.h>)
  +-- include/core/SkRefCnt.h (引用计数)
  +-- include/core/SkTextureCompressionType.h (压缩类型)
  +-- include/gpu/mtl/MtlMemoryAllocator.h (公共内存分配器接口)
  +-- include/gpu/ShaderErrorHandler.h (着色器错误处理)
  +-- src/gpu/SkSLToBackend.h (SkSL通用转换框架)
  +-- src/sksl/codegen/SkSLMetalCodeGenerator.h (SkSL->MSL代码生成)
  +-- src/sksl/SkSLCompiler.h (SkSL编译器)
  +-- src/core/SkImageInfoPriv.h (图像信息工具)

被以下模块使用:
  +-- src/gpu/ganesh/mtl/ (Ganesh Metal后端)
  +-- src/gpu/graphite/mtl/ (Graphite Metal后端)
```

## 设计模式分析

### 1. 桥接模式 (Bridge Pattern)

`MtlMemoryAllocator` 公共接口与 `MtlMemoryAllocatorImpl` 实现分离。公共接口在 `include/gpu/mtl/` 中定义,客户端可以提供自己的实现来替换默认行为。这使得 Skia 的 Metal 内存管理策略可以在不修改上层代码的情况下被替换:

```
MtlMemoryAllocator (公共接口, include/)
       ^
       |
MtlMemoryAllocatorImpl (默认实现, src/)
       |
   id<MTLDevice> (Apple Metal设备)
```

### 2. 适配器模式 (Adapter Pattern)

`SkSLToMSL()` 将 Skia 内部着色器语言适配为 Metal 特定着色器语言,同时保持与 `SkSLToSPIRV()`(Vulkan 版)相同的调用接口。两者都通过 `SkSLToBackend()` 通用转换函数实现。

### 3. 工厂方法 (Factory Method)

`MtlMemoryAllocatorImpl::Make(id<MTLDevice>)` 作为工厂方法创建分配器实例,返回 `sk_sp<MtlMemoryAllocator>` 智能指针,隐藏了具体实现类型。

### 4. Objective-C++ 混合编程

该目录中的 `.mm` 文件使用 Objective-C++ 编写,允许在 C++ 代码中直接调用 Metal 的 Objective-C API(如 `[fDevice newBufferWithLength:options:]`)。构建系统通过 `skia_objc_library` 规则处理混合编译。

## 数据流

```
1. 着色器编译流:
   SkSL源码 --> SkSLToMSL() --> SkSL::ToMetal代码生成器 --> MSL着色器代码
                                                              |
                                                     MTLDevice编译为
                                                     MTLLibrary/MTLFunction

2. 内存分配流:
   GPU后端需要缓冲区/纹理
        |
   MtlMemoryAllocatorImpl::newBufferWithLength()
   MtlMemoryAllocatorImpl::newTextureWithDescriptor()
        |
   [MTLDevice newBufferWithLength:options:]
   [MTLDevice newTextureWithDescriptor:]
        |
   返回 id<MTLBuffer> / id<MTLTexture> + MtlAlloc跟踪句柄

3. 格式查询流:
   MTLPixelFormat --> MtlFormatChannels() --> SkColorChannelFlags
   MTLPixelFormat --> MtlFormatBytesPerBlock() --> 每块字节数
   MTLPixelFormat --> MtlFormatIsCompressed() --> 是否压缩
   MTLPixelFormat --> MtlFormatToCompressionType() --> SkTextureCompressionType
```

## 相关文档与参考

- **Apple Metal 文档**: https://developer.apple.com/metal/
- **MTLPixelFormat 参考**: https://developer.apple.com/documentation/metal/mtlpixelformat
- **SkSL 着色器语言**: Skia 内部着色器语言,类似 GLSL 语法
- **Metal Shading Language (MSL)**: Apple GPU 着色器语言规范
- **Ganesh Metal 后端**: `src/gpu/ganesh/mtl/` - Ganesh 特定的 Metal 渲染管线
- **Graphite Metal 后端**: `src/gpu/graphite/mtl/` - Graphite 特定的 Metal 渲染管线
- **公共 Metal 头文件**: `include/gpu/mtl/` - 面向客户端的 Metal API 接口
- **Bazel 构建**: 通过 `skia_objc_library` 规则构建为 Objective-C++ 库,依赖 `:core`、`//src/gpu` 和 `//src/sksl/codegen:metal`
