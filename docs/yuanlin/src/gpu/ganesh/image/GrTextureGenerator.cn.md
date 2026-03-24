# GrTextureGenerator

> 源文件
> - src/gpu/ganesh/image/GrTextureGenerator.cpp

## 概述

`GrTextureGenerator` 是 Skia Ganesh GPU 后端中用于延迟生成纹理的抽象基类。它继承自 `SkImageGenerator`，为 GPU 纹理的按需生成提供了统一接口。该类的主要目的是支持"Promise Image"和外部纹理生成器（如 Android 的 AHardwareBuffer），允许纹理在真正需要时才被创建或导入。

`GrExternalTextureGenerator` 是其具体实现之一，专门处理外部纹理源（如硬件缓冲区）的导入和生命周期管理。

## 架构位置

```
SkImageGenerator (CPU 图像生成器基类)
  └── GrTextureGenerator (GPU 纹理生成器)
      └── GrExternalTextureGenerator (外部纹理生成器)
          └── GrAHardwareBufferImageGenerator (Android 硬件缓冲区)
```

位于图像生成器层次结构中，是 CPU 图像生成器到 GPU 纹理生成器的桥梁。

## 主要类与结构体

### GrTextureGenerator

**继承关系**:
- 继承自: `SkImageGenerator`
- 被继承: `GrExternalTextureGenerator`

**构造函数**:
```cpp
GrTextureGenerator(const SkImageInfo& info, uint32_t uniqueID = 0);
```

### GrExternalTextureGenerator

**继承关系**:
- 继承自: `GrTextureGenerator`
- 被继承: `GrAHardwareBufferImageGenerator` 等平台特定实现

**构造函数**:
```cpp
GrExternalTextureGenerator(const SkImageInfo& info);
```

## 公共 API 函数

### GrTextureGenerator

```cpp
GrSurfaceProxyView generateTexture(
    GrRecordingContext* ctx,
    const SkImageInfo& info,
    skgpu::Mipmapped mipmapped,
    GrImageTexGenPolicy texGenPolicy);
```
生成纹理的主入口，验证参数并委托给虚函数实现。

**参数说明**:
- `ctx`: GPU 录制上下文
- `info`: 目标图像信息
- `mipmapped`: 是否需要 mipmap
- `texGenPolicy`: 纹理生成策略

**虚函数接口**:

```cpp
virtual GrSurfaceProxyView onGenerateTexture(
    GrRecordingContext* ctx,
    const SkImageInfo& info,
    skgpu::Mipmapped mipmapped,
    GrImageTexGenPolicy texGenPolicy) = 0;
```
子类必须实现的纹理生成逻辑。

```cpp
virtual GrSurfaceOrigin origin() const = 0;
```
返回纹理的原点方向。

```cpp
bool isTextureGenerator() const final { return true; }
```
标识这是一个纹理生成器。

### GrExternalTextureGenerator

```cpp
virtual std::unique_ptr<GrExternalTexture> generateExternalTexture(
    GrRecordingContext* ctx,
    skgpu::Mipmapped mipmapped) = 0;
```
子类实现此方法以生成外部纹理对象。

```cpp
GrSurfaceProxyView onGenerateTexture(
    GrRecordingContext* ctx,
    const SkImageInfo& info,
    skgpu::Mipmapped mipmapped,
    GrImageTexGenPolicy texGenPolicy) override;
```
实现了通用的外部纹理包装逻辑。

## 内部实现细节

### 尺寸验证

`generateTexture` 方法中的断言确保尺寸匹配：

```cpp
SkASSERT_RELEASE(fInfo.dimensions() == info.dimensions());
```

这保证了生成的纹理尺寸与预期一致，避免尺寸不匹配导致的渲染错误。

### 上下文有效性检查

```cpp
if (!ctx || ctx->abandoned()) {
    return {};
}
```

在生成纹理前检查上下文的有效性，避免在无效上下文上操作。

### 外部纹理生命周期管理

`dispose_external_texture` 回调函数负责清理外部纹理：

```cpp
static void dispose_external_texture(void *context) {
    auto texture = std::unique_ptr<GrExternalTexture>(
        reinterpret_cast<GrExternalTexture *>(context));
    texture->dispose();
}
```

通过 `std::unique_ptr` 确保异常安全，并调用纹理的 `dispose` 方法。

### 外部纹理包装流程

`GrExternalTextureGenerator::onGenerateTexture` 的实现步骤：

1. **生成外部纹理**: 调用 `generateExternalTexture`
2. **获取后端纹理**: `backendTexture = externalTexture->getBackendTexture()`
3. **验证格式兼容性**: 检查颜色类型与后端格式的兼容性
4. **创建清理回调**: 包装 `dispose_external_texture` 为引用计数回调
5. **包装为纹理代理**: 使用 `wrapBackendTexture` 创建代理
6. **生成视图**: 计算 swizzle 并创建 `GrSurfaceProxyView`

### 颜色类型兼容性验证

```cpp
const GrColorType colorType = SkColorTypeToGrColorType(info.colorType());
if (!ctx->priv().caps()->areColorTypeAndFormatCompatible(colorType, format)) {
    return {};
}
```

确保请求的颜色类型在当前 GPU 上与后端格式兼容。

### 纹理包装参数

外部纹理始终以特定参数包装：

```cpp
proxy = ctx->priv().proxyProvider()->wrapBackendTexture(
    backendTexture,
    kBorrow_GrWrapOwnership,  // 借用所有权，不负责销毁
    GrWrapCacheable::kYes,    // 可缓存
    kRead_GrIOType,           // 只读访问
    std::move(cleanupCallback));
```

### Swizzle 计算

根据后端格式和颜色类型计算正确的通道重排：

```cpp
skgpu::Swizzle swizzle = ctx->priv().caps()->getReadSwizzle(format, colorType);
```

### 固定原点

外部纹理生成器使用固定的 `kTopLeft_GrSurfaceOrigin`：

```cpp
static constexpr auto kOrigin = kTopLeft_GrSurfaceOrigin;
```

这是一个常见的约定，简化了外部纹理的处理。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkImageGenerator` | 图像生成器基类 |
| `GrRecordingContext` | GPU 录制上下文 |
| `GrExternalTexture` | 外部纹理抽象 |
| `GrBackendTexture` | 后端纹理封装 |
| `GrProxyProvider` | 纹理代理创建 |
| `skgpu::RefCntedCallback` | 资源释放回调 |
| `GrCaps` | GPU 能力查询 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `SkImage_Lazy` | 通过 `isTextureGenerator()` 检测 |
| `GrImageUtils::LockTextureProxyView` | 调用 `generateTexture` |
| `GrAHardwareBufferImageGenerator` | Android 硬件缓冲区实现 |
| Promise Image 系统 | 延迟纹理生成 |

## 设计模式与设计决策

### 模板方法模式

`GrTextureGenerator` 定义了纹理生成的算法骨架：

- **公共接口**: `generateTexture` 执行通用逻辑
- **可扩展点**: `onGenerateTexture` 由子类实现

### 策略模式

通过虚函数 `generateExternalTexture` 允许不同的外部纹理生成策略：

- **Android**: `GrAHardwareBufferImageGenerator` 处理 AHardwareBuffer
- **其他平台**: 可以实现自己的外部纹理生成器

### RAII 资源管理

外部纹理通过 RAII 和智能指针管理：

```cpp
auto texture = std::unique_ptr<GrExternalTexture>(...);
texture->dispose();
```

确保异常安全和资源及时释放。

### 借用语义

外部纹理使用 `kBorrow_GrWrapOwnership`，表示 Skia 不拥有底层纹理：

- **生命周期**: 由外部代码（如 Android 系统）管理
- **清理责任**: 通过回调通知外部代码释放资源

### 延迟生成设计

纹理生成器支持延迟实例化：

- **按需创建**: 只在需要时才调用 `generateTexture`
- **缓存支持**: 生成的代理可以被缓存和重用
- **灵活性**: 支持跨上下文共享（通过 Promise Image）

## 性能考量

### 零拷贝导入

外部纹理生成器通常实现零拷贝导入：

- **直接映射**: 将外部内存映射为 GPU 纹理
- **避免复制**: 不需要将数据复制到 Skia 的纹理中
- **硬件加速**: 利用平台特定的硬件缓冲区机制

### 缓存策略

外部纹理标记为可缓存 (`GrWrapCacheable::kYes`)：

- **避免重复导入**: 同一外部纹理可以被多次使用
- **代理重用**: 代理对象可以被缓存和共享

### 只读访问

外部纹理通常标记为只读 (`kRead_GrIOType`)：

- **安全性**: 防止意外修改外部数据
- **优化**: GPU 可以进行只读优化

### 引用计数清理

使用 `skgpu::RefCntedCallback` 管理清理回调：

- **延迟清理**: 只在所有引用都释放后才清理
- **线程安全**: 引用计数是线程安全的
- **异常安全**: 自动处理异常情况

### 尺寸断言

使用 `SkASSERT_RELEASE` 在发布版本中检查尺寸：

- **防御性编程**: 捕获尺寸不匹配错误
- **性能影响小**: 简单的比较操作

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/private/gpu/ganesh/GrTextureGenerator.h` | 纹理生成器头文件 |
| `include/gpu/ganesh/GrExternalTextureGenerator.h` | 外部纹理生成器头文件 |
| `src/gpu/ganesh/GrAHardwareBufferImageGenerator.h` | Android 硬件缓冲区生成器 |
| `src/gpu/ganesh/image/SkImage_Lazy.h` | 懒加载图像 |
| `src/gpu/ganesh/image/GrImageUtils.h` | 图像工具函数 |
| `src/gpu/ganesh/GrProxyProvider.h` | 纹理代理提供者 |
| `include/core/SkImageGenerator.h` | 图像生成器基类 |
