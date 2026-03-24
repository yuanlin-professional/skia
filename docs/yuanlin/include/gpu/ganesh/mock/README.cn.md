# include/gpu/ganesh/mock - Ganesh Mock 测试后端公共 API

## 概述

`include/gpu/ganesh/mock` 目录包含 Ganesh 渲染引擎中 Mock（模拟）后端的公共 API。Mock 后端
不执行任何实际的 GPU 绘制操作，它主要用于单元测试和 CPU 开销测量。通过 Mock 后端，开发者可以
在没有 GPU 硬件的环境中测试 Ganesh 的 API 调用逻辑和 CPU 端管线。

`GrMockOptions` 允许配置 Mock 后端模拟的 GPU 能力（如最大纹理尺寸、支持的颜色格式、MSAA
支持等），从而可以测试不同硬件能力下的代码路径。`GrMockTextureInfo` 和
`GrMockRenderTargetInfo` 提供了 Mock 纹理和渲染目标的元数据。

Mock 后端的创建非常简单，直接通过 `GrDirectContext::MakeMock()` 即可完成，不需要任何外部
图形 API 的初始化。

## 架构图

```
include/gpu/ganesh/mock/
    |
    +-- GrMockTypes.h               <-- Mock 类型与选项定义
    |       |
    |       +-- GrMockTextureInfo       (Mock 纹理信息)
    |       +-- GrMockRenderTargetInfo  (Mock 渲染目标信息)
    |       +-- GrMockSurfaceInfo       (Mock 表面信息)
    |       +-- GrMockOptions           (Mock 后端能力配置)
    |
    +-- GrMockBackendSurface.h      <-- Mock 后端纹理/渲染目标工厂
    |
    +-- (创建入口在 GrDirectContext::MakeMock())
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `GrMockTypes.h` | Mock 类型定义：`GrMockOptions`、`GrMockTextureInfo`、`GrMockRenderTargetInfo` |
| `GrMockBackendSurface.h` | Mock 后端纹理和渲染目标的创建工厂方法 |

## 关键类与函数

### `GrMockOptions` 结构体

```cpp
struct GrMockOptions {
    struct ConfigOptions {
        enum Renderability { kNo, kNonMSAA, kMSAA };
        Renderability fRenderability = kNo;
        bool fTexturable = false;
    };

    // GrCaps 模拟选项
    bool fMipmapSupport = false;
    bool fDrawInstancedSupport = false;
    int fMaxTextureSize = 2048;
    int fMaxRenderTargetSize = 2048;
    ConfigOptions fConfigOptions[kGrColorTypeCnt];

    // GrShaderCaps 模拟选项
    bool fIntegerSupport = false;
    bool fShaderDerivativeSupport = true;
    bool fDualSourceBlendingSupport = false;

    // GrMockGpu 选项
    bool fFailTextureAllocations = false;
};
```

默认配置：RGBA_8888 和 BGRA_8888 可纹理化和渲染，Alpha8 和 RGB565 可纹理化。

### `GrMockTextureInfo` / `GrMockRenderTargetInfo`

```cpp
struct GrMockTextureInfo {
    GrColorType colorType() const;
    SkTextureCompressionType compressionType() const;
    int id() const;
    skgpu::Protected getProtected() const;
    GrBackendFormat getBackendFormat() const;
};

struct GrMockRenderTargetInfo {
    GrColorType colorType() const;
    skgpu::Protected getProtected() const;
    GrBackendFormat getBackendFormat() const;
};
```

### Mock 上下文创建

```cpp
// 在 GrDirectContext.h 中定义
static sk_sp<GrDirectContext> GrDirectContext::MakeMock(const GrMockOptions*, const GrContextOptions&);
static sk_sp<GrDirectContext> GrDirectContext::MakeMock(const GrMockOptions*);
```

## 依赖关系

- **上游依赖**: `include/gpu/GpuTypes.h`, `include/private/gpu/ganesh/GrTypesPriv.h`
- **无外部 GPU API 依赖**
- **实现代码**: `src/gpu/ganesh/mock/`

## 相关文档与参考

- `include/gpu/ganesh/` - Ganesh 引擎主目录
- `include/gpu/ganesh/GrDirectContext.h` - 包含 `MakeMock()` 方法
- Skia 测试框架: `tests/` 目录中大量使用 Mock 后端
