# include/gpu/graphite/dawn - Graphite Dawn/WebGPU 后端公共 API

## 概述

`include/gpu/graphite/dawn` 目录包含 Graphite 渲染引擎中 Dawn/WebGPU 后端的公共 API。
Dawn 是 Google 开发的 WebGPU 标准的 C++ 实现，它可以在原生平台上运行（通过 Vulkan、
Metal 或 D3D12 后端），也可以在浏览器中通过 WebGPU API 运行。这使得 Skia 的 Graphite
引擎能够同时支持原生应用和 Web 应用。

`DawnBackendContext` 结构体封装了 Dawn/WebGPU 的核心对象：`wgpu::Instance`、`wgpu::Device`
和 `wgpu::Queue`。此外，它还包含一个可选的 `DawnTickFunction` 回调，用于处理 GPU 进度检测。

在原生 Dawn 环境下，`DawnTickFunction` 默认使用 `wgpu::Instance::ProcessEvents`。
在 WebGPU/Emscripten 环境下，由于不存在此函数，默认为 `nullptr`（非让步模式），
客户端可以通过 ASYNCIFY 提供自己的让步函数。非让步模式下有一些限制：不能使用
`SyncToCpu::kYes`，且必须确保 GPU 工作完成后才能销毁 Context。

`DawnTextureInfo` 继承自 `TextureInfo::Data`，封装了 `wgpu::TextureFormat`、
`wgpu::TextureUsage`、`wgpu::TextureAspect` 等 Dawn 特有的纹理属性。在非 Emscripten
构建中还支持 `wgpu::YCbCrVkDescriptor` 用于 Android 上的 YCbCr 采样。

## 架构图

```
include/gpu/graphite/dawn/
    |
    +-- DawnBackendContext.h       <-- Dawn 后端上下文 + 工厂方法
    |       |
    |       +-- DawnBackendContext      (wgpu::Instance, Device, Queue)
    |       +-- DawnTickFunction        (GPU 进度回调)
    |       +-- ContextFactory::MakeDawn()
    |
    +-- DawnGraphiteTypes.h        <-- Dawn 纹理类型信息
    |       |
    |       +-- DawnTextureInfo         (纹理格式、用途、切面等)
    |
    +-- DawnTypes.h                <-- (已弃用，重定向到 DawnGraphiteTypes.h)
    +-- DawnUtils.h                <-- (已弃用，重定向到 DawnBackendContext.h)
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `DawnBackendContext.h` | `DawnBackendContext` 结构体和 `ContextFactory::MakeDawn()` |
| `DawnGraphiteTypes.h` | `DawnTextureInfo`、后端纹理/信号量工厂方法 |
| `DawnTypes.h` | 已弃用，重定向到 `DawnGraphiteTypes.h` |
| `DawnUtils.h` | 已弃用，重定向到 `DawnBackendContext.h` |

## 关键类与函数

### `DawnBackendContext` 结构体

```cpp
struct DawnBackendContext {
    wgpu::Instance fInstance;
    wgpu::Device   fDevice;
    wgpu::Queue    fQueue;
    DawnTickFunction* fTick;  // 原生 Dawn 默认使用 ProcessEvents
};
```

### `DawnTickFunction` 类型

```cpp
using DawnTickFunction = void(const wgpu::Instance& device);

// 原生 Dawn 默认实现
inline void DawnNativeProcessEventsFunction(const wgpu::Instance& instance) {
    instance.ProcessEvents();
}
```

### `DawnTextureInfo` 类

```cpp
class DawnTextureInfo final : public TextureInfo::Data {
    wgpu::TextureFormat fFormat;
    wgpu::TextureFormat fViewFormat;   // 多平面格式的视图格式
    wgpu::TextureUsage  fUsage;
    wgpu::TextureAspect fAspect;
    uint32_t            fSlice;
#if !defined(__EMSCRIPTEN__)
    wgpu::YCbCrVkDescriptor fYcbcrVkDescriptor;  // Android Vulkan YCbCr
#endif
};
```

### 上下文创建

```cpp
namespace skgpu::graphite::ContextFactory {
    std::unique_ptr<Context> MakeDawn(const DawnBackendContext&, const ContextOptions&);
}
```

### 后端纹理和信号量工厂

```cpp
namespace skgpu::graphite::BackendTextures {
    BackendTexture MakeDawn(WGPUTexture);
    BackendTexture MakeDawn(SkISize, const DawnTextureInfo&, WGPUTexture);
}

namespace skgpu::graphite::BackendSemaphores {
    BackendSemaphore MakeDawn(/* Dawn 特有参数 */);
}
```

## 依赖关系

- **上游依赖**: `include/gpu/graphite/Context.h`, `include/gpu/graphite/TextureInfo.h`
- **外部依赖**: Dawn/WebGPU 头文件 (`webgpu/webgpu_cpp.h`)
- **条件编译**: `__EMSCRIPTEN__` 用于区分原生和 Web 环境
- **实现代码**: `src/gpu/graphite/dawn/`

## 相关文档与参考

- `include/gpu/graphite/` - Graphite 引擎主目录
- `include/gpu/graphite/vk/` - Vulkan 后端（Dawn 可基于 Vulkan 运行）
- Dawn 项目: https://dawn.googlesource.com/dawn
- WebGPU 规范: https://www.w3.org/TR/webgpu/
