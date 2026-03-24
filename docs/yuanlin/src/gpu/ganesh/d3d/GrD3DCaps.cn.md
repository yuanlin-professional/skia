# GrD3DCaps

> 源文件: src/gpu/ganesh/d3d/GrD3DCaps.h, src/gpu/ganesh/d3d/GrD3DCaps.cpp

## 概述

`GrD3DCaps` 是 Skia Ganesh Direct3D 12 后端的能力查询类,负责检测和存储 D3D12 GPU 的硬件能力信息。它查询支持的纹理格式、MSAA 采样数、着色器特性、复制能力等,为上层渲染代码提供统一的能力查询接口,确保代码在不同 GPU 上正确运行。

## 架构位置

`GrD3DCaps` 位于 D3D12 后端的能力抽象层:
- **基类**: `GrCaps` (跨平台能力抽象)
- **初始化**: 在 `GrD3DGpu` 创建时初始化
- **使用**: 整个 Ganesh D3D12 后端查询 GPU 能力

## 主要类与结构体

### GrD3DCaps 类
```cpp
class GrD3DCaps : public GrCaps {
public:
    GrD3DCaps(const GrContextOptions&, IDXGIAdapter1*, ID3D12Device*);

    // 格式查询
    bool isFormatTexturable(DXGI_FORMAT) const;
    bool isFormatRenderable(DXGI_FORMAT, int sampleCount) const;
    bool isFormatUnorderedAccessible(DXGI_FORMAT) const;
    int getRenderTargetSampleCount(int requestedCount, DXGI_FORMAT) const;
    int maxRenderTargetSampleCount(DXGI_FORMAT) const;

    // 模板格式
    DXGI_FORMAT preferredStencilFormat() const;

    // 拷贝能力
    bool canCopyTexture(DXGI_FORMAT dst, int dstSampleCnt,
                        DXGI_FORMAT src, int srcSamplecnt) const;
    bool canCopyAsResolve(DXGI_FORMAT dst, int dstSampleCnt,
                          DXGI_FORMAT src, int srcSamplecnt) const;

    // D3D12 特性
    bool resolveSubresourceRegionSupport() const;
    bool standardSwizzleLayoutSupport() const;
};
```

**继承关系**:
- 基类: `GrCaps` -> GPU 能力抽象基类

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFormatTable` | `FormatInfo[kNumDxgiFormats]` | 格式能力表 |
| `fColorTypeToFormatTable` | `DXGI_FORMAT[]` | 颜色类型到 D3D12 格式映射 |
| `fPreferredStencilFormat` | `DXGI_FORMAT` | 首选模板格式 |
| `fResolveSubresourceRegionSupport` | `bool` | 是否支持部分 MSAA resolve |
| `fStandardSwizzleLayoutSupport` | `bool` | 是否支持标准 swizzle 布局 |

### FormatInfo 结构体
```cpp
struct FormatInfo {
    uint16_t fFlags;  // kTexturable_Flag, kRenderable_Flag, 等
    SkTDArray<int> fColorSampleCounts;  // 支持的 MSAA 采样数
    GrColorType fFormatColorType;  // 格式对应的颜色类型
    std::unique_ptr<ColorTypeInfo[]> fColorTypeInfos;  // 颜色类型信息数组
    int fColorTypeInfoCount;
};
```

### ColorTypeInfo 结构体
```cpp
struct ColorTypeInfo {
    GrColorType fColorType;
    uint32_t fFlags;  // kUploadData_Flag, kRenderable_Flag, kWrappedOnly_Flag
    skgpu::Swizzle fReadSwizzle;  // 读取时的通道重排
    skgpu::Swizzle fWriteSwizzle;  // 写入时的通道重排
};
```

## 公共 API 函数

### 格式能力查询

**isFormatTexturable**
```cpp
bool isFormatTexturable(const GrBackendFormat&) const override;
bool isFormatTexturable(DXGI_FORMAT) const;
```
查询格式是否可作为纹理采样。

**isFormatRenderable**
```cpp
bool isFormatRenderable(const GrBackendFormat&, int sampleCount) const override;
bool isFormatRenderable(DXGI_FORMAT, int sampleCount) const;
```
查询格式是否可作为渲染目标,支持指定的采样数。

**isFormatUnorderedAccessible**
```cpp
bool isFormatUnorderedAccessible(DXGI_FORMAT) const;
```
查询格式是否支持 UAV (Unordered Access View),用于计算着色器。

### MSAA 支持查询

**getRenderTargetSampleCount**
```cpp
int getRenderTargetSampleCount(int requestedCount, const GrBackendFormat&) const override;
int getRenderTargetSampleCount(int requestedCount, DXGI_FORMAT) const;
```
返回最接近请求采样数的实际支持的采样数。如果不支持则返回 0。

**maxRenderTargetSampleCount**
```cpp
int maxRenderTargetSampleCount(const GrBackendFormat&) const override;
int maxRenderTargetSampleCount(DXGI_FORMAT) const;
```
返回格式支持的最大 MSAA 采样数。

### 像素传输支持

**supportedWritePixelsColorType**
```cpp
SupportedWrite supportedWritePixelsColorType(GrColorType surfaceColorType,
                                              const GrBackendFormat&,
                                              GrColorType srcColorType) const override;
```
查询写入像素时支持的颜色类型转换。

**surfaceSupportsReadPixels**
```cpp
SurfaceReadPixelsSupport surfaceSupportsReadPixels(const GrSurface*) const override;
```
查询表面是否支持读取像素(某些表面可能是 framebuffer-only)。

### 模板格式

**preferredStencilFormat**
```cpp
DXGI_FORMAT preferredStencilFormat() const;
```
返回首选的模板格式(如 `DXGI_FORMAT_D24_UNORM_S8_UINT`)。

**GetStencilFormatTotalBitCount**
```cpp
static int GetStencilFormatTotalBitCount(DXGI_FORMAT format);
```
返回模板格式的总位数(包括深度、模板和填充位)。

### 拷贝能力

**canCopyTexture**
```cpp
bool canCopyTexture(DXGI_FORMAT dstFormat, int dstSampleCnt,
                    DXGI_FORMAT srcFormat, int srcSamplecnt) const;
```
查询是否可以在两个纹理间拷贝。

**canCopyAsResolve**
```cpp
bool canCopyAsResolve(DXGI_FORMAT dstFormat, int dstSampleCnt,
                      DXGI_FORMAT srcFormat, int srcSamplecnt) const;
```
查询是否可以作为 MSAA resolve 拷贝(多采样到单采样)。

### Swizzle 和格式转换

**getReadSwizzle** / **getWriteSwizzle**
```cpp
skgpu::Swizzle getReadSwizzle(const GrBackendFormat&, GrColorType) const override;
skgpu::Swizzle getWriteSwizzle(const GrBackendFormat&, GrColorType) const override;
```
获取读取/写入时的通道重排方式(如 BGRA -> RGBA)。

**getFormatFromColorType**
```cpp
DXGI_FORMAT getFormatFromColorType(GrColorType colorType) const;
```
从 Skia 颜色类型获取对应的 D3D12 格式。

**getFormatColorType**
```cpp
GrColorType getFormatColorType(DXGI_FORMAT) const;
```
从 D3D12 格式获取对应的颜色类型。

## 内部实现细节

### 初始化流程

```cpp
void init(const GrContextOptions& contextOptions, IDXGIAdapter1* adapter, ID3D12Device* device) {
    initGrCaps(...);        // 通用 GPU 能力
    initShaderCaps(...);    // 着色器能力
    initFormatTable(...);   // 格式支持表
    initStencilFormat(...); // 模板格式
    applyDriverCorrectnessWorkarounds(...);  // 驱动 bug 修正
}
```

### 格式表初始化

`initFormatTable` 查询每个 D3D12 格式的支持情况:
```cpp
D3D12_FEATURE_DATA_FORMAT_SUPPORT formatSupport = {
    .Format = format
};
device->CheckFeatureSupport(D3D12_FEATURE_FORMAT_SUPPORT,
                             &formatSupport, sizeof(formatSupport));

// 根据返回的标志设置能力
if (formatSupport.Support1 & D3D12_FORMAT_SUPPORT1_SHADER_SAMPLE) {
    fFlags |= kTexturable_Flag;
}
if (formatSupport.Support1 & D3D12_FORMAT_SUPPORT1_RENDER_TARGET) {
    fFlags |= kRenderable_Flag;
}
// ...
```

### MSAA 采样数初始化

```cpp
void initSampleCounts(IDXGIAdapter1* adapter, ID3D12Device* device, DXGI_FORMAT format) {
    for (int sampleCount : {1, 2, 4, 8, 16}) {
        D3D12_FEATURE_DATA_MULTISAMPLE_QUALITY_LEVELS msqLevels = {
            .Format = format,
            .SampleCount = sampleCount
        };
        HRESULT hr = device->CheckFeatureSupport(D3D12_FEATURE_MULTISAMPLE_QUALITY_LEVELS,
                                                  &msqLevels, sizeof(msqLevels));
        if (SUCCEEDED(hr) && msqLevels.NumQualityLevels > 0) {
            fColorSampleCounts.push_back(sampleCount);
        }
    }
}
```

### 支持的格式

`kNumDxgiFormats = 15`,包含:
- **颜色格式**: RGBA8, BGRA8, RGB10A2, RGBA16F, RGBA32F, R8, RG88, 等
- **压缩格式**: BC1(DXT1), ETC1
- **深度/模板**: D24S8, D32FS8

### Vendor 特定优化

```cpp
enum D3DVendor {
    kAMD_D3DVendor = 0x1002,
    kARM_D3DVendor = 0x13B5,
    kIntel_D3DVendor = 0x8086,
    kNVIDIA_D3DVendor = 0x10DE,
    kQualcomm_D3DVendor = 0x5143,
    // ...
};

void applyDriverCorrectnessWorkarounds(int vendorID) {
    // 针对特定 GPU 供应商的 bug 修正
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrCaps` | 基类,跨平台能力抽象 |
| `ID3D12Device` | D3D12 设备,查询硬件能力 |
| `IDXGIAdapter1` | DXGI 适配器,获取 GPU 信息 |
| `GrColorType` | Skia 颜色类型 |
| `DXGI_FORMAT` | D3D12 格式枚举 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `GrD3DGpu` | 使用 `GrD3DCaps` 查询能力 |
| 整个 Ganesh D3D12 后端 | 通过 `GrCaps` 接口查询能力 |

## 设计模式与设计决策

### 设计模式

1. **外观模式**: 封装复杂的 D3D12 能力查询
2. **策略模式**: 根据 GPU 能力选择不同的渲染路径
3. **单例风格**: 每个 GPU 上下文一个 Caps 对象

### 设计决策

**为什么需要 FormatInfo 表?**
- D3D12 有 100+ 种格式,逐次查询性能差
- 初始化时一次性查询所有格式并缓存
- 运行时查询变为简单的数组访问

**ColorTypeInfo 数组的意义**
- 同一个 D3D12 格式可以对应多个 Skia 颜色类型
- 例如 `DXGI_FORMAT_R8G8B8A8_UNORM` 可以是 RGBA 或 BGRA
- 不同颜色类型可能需要不同的 swizzle

**为什么区分 Texturable 和 Renderable?**
- 某些格式只能作为纹理(如某些压缩格式)
- 某些格式只能作为渲染目标
- 分别查询减少无效尝试

**Vendor workarounds 的必要性**
- GPU 驱动存在 bug 或性能问题
- 针对特定 vendor 应用修正
- 确保在所有硬件上正确运行

**ResolveSubresourceRegion 的意义**
- 标准 MSAA resolve 总是全表面
- `ResolveSubresourceRegion` 允许部分 resolve
- 减少带宽,提高性能

## 性能考量

### 优化策略

1. **能力缓存**: 初始化时查询并缓存所有能力
2. **快速查找**: 使用数组而非逐次查询
3. **格式选择**: 优先选择硬件原生支持的格式
4. **采样数选择**: 使用硬件支持的采样数,避免模拟

### 性能陷阱

- **不支持的格式**: 导致软件回退或失败
- **过高的 MSAA**: 某些 GPU 不支持 16x
- **格式转换**: CPU 端转换比 GPU 端慢
- **忽略 swizzle**: 导致错误的颜色通道顺序

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrCaps.h/.cpp` | 基类 | 跨平台能力抽象 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h` | 使用者 | GPU 实现 |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | 依赖 | D3D12 类型 |
| `src/gpu/ganesh/TestFormatColorTypeCombination.h` | 相关 | 测试用格式组合 |
