# GrMtlTypes - Metal 类型定义

> 源文件: `include/gpu/ganesh/mtl/GrMtlTypes.h`

## 概述

GrMtlTypes.h 定义了 Skia Ganesh GPU 后端中与 Apple Metal API 交互所需的核心数据结构和类型别名。该文件提供了 Metal 资源的封装结构体，使 Skia 能够在不直接依赖 Objective-C Metal 头文件的情况下与外部 Metal 资源交互，是跨语言（C++/Objective-C）边界的桥梁。

## 架构位置

- **所属子系统**: GPU/Ganesh 渲染后端
- **层级**: 公共 API 接口层
- **作用域**: Metal 后端专用（Apple 平台）

该文件位于 Ganesh GPU 后端的 Metal 实现模块中，为上层提供与 Metal 资源交互的标准化 C++ 接口。

## 主要类与结构体

### Metal 基础类型别名

为避免在 C++ 头文件中直接使用 Objective-C 类型，定义了一组类型别名：

| 类型别名 | 底层类型 | 对应 Metal 类型 | 说明 |
|---------|---------|----------------|------|
| GrMTLPixelFormat | unsigned int | MTLPixelFormat | 纹理像素格式 |
| GrMTLTextureUsage | unsigned int | MTLTextureUsage | 纹理用途标志 |
| GrMTLStorageMode | unsigned int | MTLStorageMode | 内存存储模式 |
| GrMTLHandle | const void* | id\<MTLResource\> | 不透明资源句柄 |

**设计意图**:
- 在 C++ 头文件中避免引入 Objective-C 语法
- 允许 C++ 代码操作 Metal 资源而无需了解 Objective-C
- 通过 `__bridge` 转换在使用点进行类型转换

### CAMetalLayer 可用性宏

```cpp
#if TARGET_OS_SIMULATOR
#define SK_API_AVAILABLE_CA_METAL_LAYER \
    SK_API_AVAILABLE(macos(10.11), ios(13.0), tvos(13.0))
#else
#define SK_API_AVAILABLE_CA_METAL_LAYER \
    SK_API_AVAILABLE(macos(10.11), ios(8.0), tvos(9.0))
#endif
```

**平台差异**:
- **模拟器**: iOS 13.0+ 才支持 CAMetalLayer（较晚）
- **真机设备**: iOS 8.0+ 即可支持
- **用途**: 标注使用 CAMetalLayer 的 API 可用性

### GrMtlTextureInfo

封装外部 Metal 纹理信息，用于包装已存在的 Metal 纹理对象。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fTexture | sk_cfp\<GrMTLHandle\> | Metal 纹理对象的智能指针封装 |

**成员函数**:

```cpp
bool operator==(const GrMtlTextureInfo& that) const
```
- **功能**: 比较两个纹理信息是否指向同一纹理对象
- **比较方式**: 通过智能指针的相等性比较（底层指针比较）
- **用途**: 资源去重、缓存查找

**智能指针封装**:
- `sk_cfp` 是 Core Foundation 智能指针模板
- 自动管理 Metal 对象的引用计数
- 当 `sk_cfp` 销毁时自动调用 `CFRelease`（对应 Objective-C 的 `release`）

### GrMtlSurfaceInfo

描述创建 Metal 表面所需的配置参数。

**关键成员变量**:

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| fSampleCount | uint32_t | 1 | 多重采样数量（1表示无MSAA） |
| fLevelCount | uint32_t | 0 | Mipmap 层级数量（0表示单层） |
| fProtected | skgpu::Protected | kNo | 是否使用受保护内存 |
| fFormat | GrMTLPixelFormat | 0 | 像素格式（0 = MTLPixelFormatInvalid） |
| fUsage | GrMTLTextureUsage | 0 | 纹理用途标志（0 = MTLTextureUsageUnknown） |
| fStorageMode | GrMTLStorageMode | 0 | 存储模式（0 = MTLStorageModeShared） |

**Metal 类型映射**:

注释中明确说明了各字段对应的 Metal 类型：
```cpp
// 实际使用时的转换：
MTLPixelFormat format = (MTLPixelFormat)surfaceInfo.fFormat;
MTLTextureUsage usage = (MTLTextureUsage)surfaceInfo.fUsage;
MTLStorageMode storageMode = (MTLStorageMode)surfaceInfo.fStorageMode;
```

## 公共 API 函数

### `GrMtlTextureInfo::operator==`
```cpp
bool operator==(const GrMtlTextureInfo& that) const
```
- **功能**: 比较两个纹理信息是否指向同一 Metal 纹理
- **参数**: `that` - 待比较的纹理信息对象
- **返回值**: 如果指向同一纹理对象返回 true
- **实现**: 委托给 `sk_cfp` 的相等性比较

## 内部实现细节

### C++/Objective-C 互操作机制

Metal 是 Objective-C API，而 Skia 是 C++ 代码库。这种互操作通过以下方式实现：

**在 Objective-C++ 代码中创建纹理信息**:
```objc
// .mm 文件（Objective-C++）
id<MTLTexture> metalTexture = [device newTextureWithDescriptor:desc];

GrMtlTextureInfo textureInfo;
textureInfo.fTexture.retain((__bridge GrMTLHandle)metalTexture);
```

**在 C++ 代码中使用纹理信息**:
```cpp
// .cpp 文件（纯 C++）
void useTexture(const GrMtlTextureInfo& info) {
    // 可以存储和传递 info，但不直接操作 fTexture
    // 实际操作在 .mm 文件中进行
}
```

**转换回 Objective-C 类型**:
```objc
// .mm 文件
id<MTLTexture> metalTexture = (__bridge id<MTLTexture>)info.fTexture.get();
```

### sk_cfp 智能指针机制

`sk_cfp` 是 Skia 提供的 Core Foundation 智能指针模板：

**引用计数管理**:
- `retain(ptr)`: 增加引用计数并存储指针
- `reset()`: 释放当前引用，计数减一
- 析构时自动释放引用

**与 ARC 的兼容性**:
- 在 ARC（Automatic Reference Counting）环境中仍需要手动管理
- `__bridge` 转换不改变引用计数
- `__bridge_retained` 会增加计数（对应 `CFBridgingRetain`）
- `__bridge_transfer` 会转移所有权（对应 `CFBridgingRelease`）

### Metal 存储模式说明

`fStorageMode` 字段决定纹理内存的可见性和同步需求：

**MTLStorageModeShared** (默认 0):
- CPU 和 GPU 共享内存
- 无需显式同步
- iOS/tvOS 唯一支持模式
- macOS 性能较低但易用

**MTLStorageModeManaged** (仅 macOS):
- CPU 和 GPU 各有副本
- 需要显式同步（`synchronizeResource`）
- 更高性能

**MTLStorageModePrivate**:
- 仅 GPU 可访问
- 最高性能
- CPU 无法直接读写

**MTLStorageModeMemoryless** (仅 iOS):
- Tile memory，不持久化
- 用于临时渲染目标（如深度/模板）
- 最节省内存

### 纹理用途标志组合

`fUsage` 是位掩码，可组合多个用途：
```cpp
// 常见组合示例（实际使用 Metal 常量）
fUsage = MTLTextureUsageShaderRead |    // 着色器采样
         MTLTextureUsageRenderTarget;   // 渲染目标
```

Skia 根据用途创建最优的 Metal 纹理。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/gpu/GpuTypes.h | skgpu::Protected 枚举定义 |
| include/ports/SkCFObject.h | sk_cfp 智能指针模板 |

### 被依赖的模块

- **GrMtlBackendContext**: 使用这些类型初始化 Metal 上下文
- **GrBackendTexture/GrBackendRenderTarget**: 使用 GrMtlTextureInfo 包装 Metal 纹理
- **SkSurfaceMetal.h**: 使用 GrMtlSurfaceInfo 创建 Metal 表面
- **GrMtlGpu**: Metal GPU 实现类使用这些类型与 Metal API 交互

## 设计模式与设计决策

### 1. 类型别名隔离模式

通过 `unsigned int` 和 `const void*` 隔离 Objective-C 类型：
- **优点**:
  - C++ 头文件无需引入 Objective-C 语法
  - 加快编译速度（避免解析庞大的 Metal 头文件）
  - 纯 C++ 客户端可使用这些类型
- **代价**:
  - 需要在使用点进行类型转换
  - 失去编译时类型检查

### 2. 智能指针自动管理

使用 `sk_cfp` 管理 Metal 对象生命周期：
- **避免泄漏**: 自动释放，无需手动调用 `release`
- **异常安全**: RAII 保证资源释放
- **值语义**: 可安全复制和传递

### 3. 平台条件编译

通过 `#ifdef __APPLE__` 隔离 Apple 平台代码：
- 非 Apple 平台编译时完全排除 Metal 相关定义
- 避免污染其他平台的构建
- 保持头文件的跨平台包含安全性

### 4. API 可用性标注

使用 `SK_API_AVAILABLE` 宏标注 API 版本需求：
- 编译器可在使用不支持 API 时发出警告
- 运行时可通过 `@available` 检查避免崩溃
- 文档清晰表明 API 的系统要求

## 性能考量

### 内存布局优化

**GrMtlTextureInfo**:
- 仅包含一个智能指针（8字节指针）
- 总大小约 8-16 字节（取决于 `sk_cfp` 实现）
- 适合按值传递

**GrMtlSurfaceInfo**:
- 6 个整型字段，自然对齐
- 总大小 24 字节
- 无填充浪费，缓存友好

### 引用计数开销

- `sk_cfp` 的 `retain`/`release` 调用对应 Objective-C 的引用计数操作
- 现代 Apple 设备上引用计数开销极低（原子操作优化）
- 相比手动管理，智能指针开销可忽略

### 存储模式性能影响

选择正确的 `fStorageMode` 对性能至关重要：
- **Shared**: 方便但在 macOS 上有带宽限制
- **Private**: 最快但需要通过 blit 命令传输数据
- **Managed**: macOS 上的平衡选择
- Skia 根据使用场景自动选择最优模式

## 平台相关说明

### iOS/iPadOS

**Metal 支持**:
- iOS 8.0+: 支持 Metal（A7 芯片及以上）
- iOS 13.0+: 模拟器支持 Metal

**存储模式限制**:
- 仅支持 `MTLStorageModeShared` 和 `MTLStorageModePrivate`
- 不支持 `MTLStorageModeManaged`（统一内存架构）

**内存压力**:
- 移动设备内存有限，需要注意纹理大小
- 支持 `MTLStorageModeMemoryless` 用于临时资源

### macOS

**Metal 支持**:
- macOS 10.11+: 支持 Metal
- Intel Mac: 成熟支持
- Apple Silicon (M1+): 原生支持，性能卓越

**存储模式丰富**:
- 支持所有四种存储模式
- 独立显卡 Mac 推荐使用 `MTLStorageModeManaged` 或 `MTLStorageModePrivate`

**UMA vs NUMA**:
- Apple Silicon: 统一内存架构（UMA），Shared 模式性能好
- Intel + 独显: 非统一内存（NUMA），Private 模式性能最优

### tvOS

**Metal 支持**:
- tvOS 9.0+: 支持 Metal
- tvOS 13.0+: 模拟器支持

**特性**:
- 与 iOS 类似，统一内存架构
- 分辨率固定（1080p 或 4K），纹理大小可预测

### 模拟器特殊处理

`SK_API_AVAILABLE_CA_METAL_LAYER` 宏的模拟器分支：
- iOS 模拟器直到 13.0 才支持 CAMetalLayer
- 真机从 iOS 8.0 就支持
- 代码需要根据目标环境选择正确的最低版本

## 相关文件

| 文件 | 关系 |
|------|------|
| include/ports/SkCFObject.h | 提供 sk_cfp 智能指针模板 |
| include/gpu/GpuTypes.h | 定义 skgpu::Protected 枚举 |
| include/gpu/ganesh/mtl/GrMtlBackendContext.h | 使用 GrMTLHandle 类型创建上下文 |
| include/gpu/ganesh/mtl/SkSurfaceMetal.h | 使用 GrMtlSurfaceInfo 创建表面 |
| src/gpu/ganesh/mtl/GrMtlGpu.h | Metal GPU 实现，使用这些类型与 Metal API 交互 |
| src/gpu/ganesh/mtl/GrMtlTexture.h | 使用 GrMtlTextureInfo 管理纹理 |
| src/gpu/ganesh/GrBackendSurface.h | 后端无关的表面抽象，内部存储 GrMtlTextureInfo |

## 使用示例

### 创建纹理信息

```objc
// Objective-C++: 创建 Metal 纹理
id<MTLDevice> device = MTLCreateSystemDefaultDevice();
MTLTextureDescriptor* desc = [MTLTextureDescriptor
    texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
                                 width:512
                                height:512
                             mipmapped:NO];
desc.usage = MTLTextureUsageShaderRead | MTLTextureUsageRenderTarget;
id<MTLTexture> metalTexture = [device newTextureWithDescriptor:desc];

// 包装为 Skia 类型
GrMtlTextureInfo textureInfo;
textureInfo.fTexture.retain((__bridge GrMTLHandle)metalTexture);

// 创建 GrBackendTexture
GrBackendTexture backendTexture(512, 512, skgpu::Mipmapped::kNo, textureInfo);
```

### 配置表面信息

```cpp
// C++: 配置 Metal 表面参数
GrMtlSurfaceInfo surfaceInfo;
surfaceInfo.fSampleCount = 1;  // 无 MSAA
surfaceInfo.fLevelCount = 1;   // 无 mipmap
surfaceInfo.fFormat = 80;      // MTLPixelFormatRGBA8Unorm
surfaceInfo.fUsage = 5;        // ShaderRead | RenderTarget
surfaceInfo.fStorageMode = 0;  // Shared
```

## 最佳实践

### 纹理用途设置

明确设置 `fUsage` 以获得最佳性能：
```cpp
// 仅采样的纹理
fUsage = MTLTextureUsageShaderRead;

// 渲染目标
fUsage = MTLTextureUsageShaderRead | MTLTextureUsageRenderTarget;

// 计算着色器输出
fUsage = MTLTextureUsageShaderWrite;
```

### 存储模式选择

根据访问模式选择存储模式：
```cpp
// CPU 不需要访问
fStorageMode = MTLStorageModePrivate;  // 最快

// CPU 偶尔读取（macOS）
fStorageMode = MTLStorageModeManaged;  // 需要同步

// CPU 频繁读写（iOS/macOS）
fStorageMode = MTLStorageModeShared;   // 方便但慢
```

### 生命周期管理

正确管理纹理生命周期：
```cpp
// 错误示例：悬空指针
GrMtlTextureInfo textureInfo;
{
    id<MTLTexture> tempTexture = [device newTextureWithDescriptor:desc];
    textureInfo.fTexture.retain((__bridge GrMTLHandle)tempTexture);
    // tempTexture 离开作用域被 ARC 释放
}
// textureInfo.fTexture 仍持有引用，安全！

// sk_cfp 会在析构时自动释放引用
```
