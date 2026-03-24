# DawnTexture

> 源文件:
> - `src/gpu/graphite/dawn/DawnTexture.h`
> - `src/gpu/graphite/dawn/DawnTexture.cpp`

## 概述

`DawnTexture` 是 Skia Graphite 渲染引擎 Dawn (WebGPU) 后端的纹理实现。它继承自 `Texture` 基类，封装了 `wgpu::Texture` 及其纹理视图（`wgpu::TextureView`）的创建和管理。该类支持自有纹理创建和外部纹理包装两种模式，并为采样和渲染分别维护独立的纹理视图。

## 架构位置

```
Graphite 渲染引擎
  └── Texture (平台无关基类)
        └── DawnTexture (Dawn/WebGPU 后端)
              ├── wgpu::Texture (底层 GPU 纹理对象)
              ├── fSampleTextureView (用于着色器采样)
              └── fRenderTextureView (用于渲染目标附件)
```

## 主要类与结构体

### `DawnTexture`
- 继承自 `Texture`，是 Dawn 后端的纹理封装。
- 持有三个 Dawn 对象：
  - `fTexture`：底层 `wgpu::Texture` 对象。对于包装的纹理视图可能为空。
  - `fSampleTextureView`：用于着色器中纹理采样的视图，包含所有 mip 级别。
  - `fRenderTextureView`：用于作为渲染目标的视图。对于有 mipmap 的纹理，仅包含第 0 级 mip；对于无 mipmap 的纹理，与采样视图相同。

## 公共 API 函数

### 工厂方法
- **`static MakeDawnTexture(const DawnSharedContext*, SkISize, const TextureInfo&) -> wgpu::Texture`**：创建底层 Dawn 纹理对象。执行尺寸、可纹理化、可渲染、可存储等能力验证。支持 mipmap 级别计算和 YCbCr 格式验证。
- **`static Make(const DawnSharedContext*, SkISize, const TextureInfo&, std::string_view) -> sk_sp<Texture>`**：创建完整的 DawnTexture，包括纹理和视图。Ownership 为 `kOwned`。
- **`static MakeWrapped(... wgpu::Texture ...) -> sk_sp<Texture>`**：包装外部 `wgpu::Texture`，创建关联的纹理视图。Ownership 为 `kWrapped`。
- **`static MakeWrapped(... wgpu::TextureView ...) -> sk_sp<Texture>`**：包装外部 `wgpu::TextureView`。不持有 `wgpu::Texture`，采样和渲染视图均指向同一个传入的视图。

### 访问器
- **`dawnTexture()`**：返回底层 `wgpu::Texture` 引用。
- **`sampleTextureView()`**：返回采样用纹理视图。
- **`renderTextureView()`**：返回渲染用纹理视图。
- **`dawnTextureInfo()`**：返回 `DawnTextureInfo` 结构体引用，包含 Dawn 特有的纹理信息。

## 内部实现细节

### 纹理创建验证
`MakeDawnTexture()` 执行以下验证：
1. 尺寸不超过 `maxTextureSize()`。
2. 带 `TextureBinding` 用途的纹理必须可纹理化（`isTexturable`）。
3. 带 `RenderAttachment` 用途的纹理必须可渲染（`isRenderable`）。
4. 带 `StorageBinding` 用途的纹理必须支持存储（`isStorage`）。
5. 非 Emscripten 环境下，YCbCr 描述符有效时，`vkFormat` 或 `externalFormat` 必须非零。

### 纹理视图创建
`CreateTextureViews()` 根据 `DawnTextureInfo::fAspect` 分两种情况：
- **`wgpu::TextureAspect::All`**：创建 2D 视图。对于有 mipmap 的纹理，采样视图包含所有 mip 级别，渲染视图仅包含 mip 0；对于无 mipmap 的纹理，两者共享同一视图。支持 YCbCr 采样描述符链接。
- **平面视图**（`Plane0Only`、`Plane1Only`、`Plane2Only`）：仅在非 Emscripten 环境下支持，创建指定平面的纹理视图，使用 `fViewFormat` 作为格式，采样和渲染视图相同。

### 资源释放
`freeGpuData()` 中：
- 自有纹理（非包装）调用 `fTexture.Destroy()` 显式销毁，即使仍有 BindGroup 或视图引用。
- 所有情况下将三个 Dawn 对象置空。

### 瞬态附件支持
构造函数通过 `has_transient_usage()` 检查纹理是否具有 `wgpu::TextureUsage::TransientAttachment` 标志（仅非 Emscripten 环境），标记为瞬态纹理（memoryless）。

### 后端标签
`setBackendLabel()` 在支持标签的设备上为纹理和视图设置调试标签。如果采样视图和渲染视图是同一个对象，仅设置一次带 `_TextureView` 后缀的标签；否则分别设置 `_SampleTextureView` 和 `_RenderTextureView`。

## 依赖关系

- **基类**: `Texture`
- **Dawn 后端类**: `DawnSharedContext`、`DawnCaps`
- **Graphite 核心**: `TextureInfo`、`TextureInfoPriv`
- **Skia 核心**: `SkMipmap`（mip 级别计算）、`SkTraceMemoryDump`
- **WebGPU API**: `wgpu::Texture`、`wgpu::TextureView`、`wgpu::TextureDescriptor`

## 设计模式与设计决策

1. **双视图设计**：为采样和渲染分别维护独立的纹理视图，确保 mipmap 纹理的渲染目标正确指向 mip 0，而采样可以访问所有 mip 级别。
2. **所有权模型**：区分自有（`kOwned`）和包装（`kWrapped`）纹理。自有纹理在释放时显式调用 `Destroy()`；包装纹理不销毁底层对象。
3. **工厂方法模式**：提供多个静态工厂函数适应不同的创建场景（自有、包装纹理、包装视图）。
4. **平台适配**：通过 `__EMSCRIPTEN__` 宏禁用 WebAssembly 环境不支持的功能（TransientAttachment、YCbCr、平面纹理视图）。

## 性能考量

- **视图复用**：无 mipmap 纹理的采样和渲染视图共享同一个对象，减少 GPU 资源创建。
- **瞬态附件**：支持 `TransientAttachment` 标志的纹理可以使用 memoryless 存储，在 tile-based GPU 上节省内存带宽。
- **显式销毁**：自有纹理调用 `Destroy()` 而非依赖引用计数和垃圾回收，确保 GPU 内存及时释放。
- **能力前置验证**：在创建纹理前验证所有能力需求，避免无效的 GPU 资源分配。

## 相关文件

- `src/gpu/graphite/Texture.h` - 基类定义
- `src/gpu/graphite/dawn/DawnSharedContext.h` - Dawn 共享上下文
- `src/gpu/graphite/dawn/DawnCaps.h` - Dawn 能力查询
- `src/gpu/graphite/TextureInfoPriv.h` - 纹理信息私有访问
- `include/gpu/graphite/dawn/DawnGraphiteTypes.h` - Dawn 类型定义（DawnTextureInfo）
- `src/gpu/graphite/dawn/DawnGraphiteUtils.h` - Dawn 工具函数
