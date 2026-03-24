# DawnSampler -- Dawn/WebGPU 采样器

> 源文件:
> - `src/gpu/graphite/dawn/DawnSampler.h`
> - `src/gpu/graphite/dawn/DawnSampler.cpp`

## 概述

DawnSampler 是 Graphite Dawn/WebGPU 后端的采样器实现,继承自 `Sampler` 基类。它将 Skia 的采样选项转换为 WebGPU 的 `wgpu::Sampler` 对象,并支持 YCbCr 不可变采样器（仅原生 Dawn）。

## 架构位置

```
Sampler (抽象基类)
  -> DawnSampler  <-- 本模块
       -> wgpu::Sampler (WebGPU 采样器)
       -> SamplerDesc (采样器描述)
```

## 主要类与结构体

### DawnSampler

```cpp
class DawnSampler : public Sampler {
    wgpu::Sampler fSampler;
    SamplerDesc fSamplerDesc;
};
```

与其他后端不同,DawnSampler 保留 `SamplerDesc` 以支持后续查询。

## 公共 API 函数

### Make

```cpp
static sk_sp<DawnSampler> Make(const DawnSharedContext*, SamplerDesc);
```
接受完整的 `SamplerDesc`（而非分散参数），因为 Dawn 需要额外的不可变采样器信息。

### 访问器

```cpp
SamplerDesc samplerDesc() const;
const wgpu::Sampler& dawnSampler() const;
```

## 内部实现细节

### 过滤模式映射

| Skia 模式 | Dawn 模式 |
|-----------|-----------|
| `SkFilterMode::kNearest` | `wgpu::FilterMode::Nearest` |
| `SkFilterMode::kLinear` | `wgpu::FilterMode::Linear` |
| `SkMipmapMode::kNone` | `wgpu::MipmapFilterMode::Nearest`（lodMaxClamp=0 禁用） |
| `SkMipmapMode::kNearest` | `wgpu::MipmapFilterMode::Nearest` |
| `SkMipmapMode::kLinear` | `wgpu::MipmapFilterMode::Linear` |

Dawn 没有 "None" Mipmap 过滤模式,通过 `lodMaxClamp=0` 实现等效效果。

### 平铺模式映射

| SkTileMode | wgpu::AddressMode |
|------------|-------------------|
| kClamp | ClampToEdge |
| kRepeat | Repeat |
| kMirror | MirrorRepeat |
| kDecal | 不支持（触发 assert） |

Dawn/WebGPU 不原生支持 Decal 模式,需要着色器级别的回退。

### YCbCr 不可变采样器（原生 Dawn）

```cpp
#if !defined(__EMSCRIPTEN__)
wgpu::YCbCrVkDescriptor ycbcrDescriptor;
if (samplerDesc.isImmutable()) {
    ycbcrDescriptor = DawnDescriptorFromImmutableSamplerInfo(samplerDesc.immutableSamplerInfo());
    desc.nextInChain = &ycbcrDescriptor;
}
#endif
```

通过 `DawnDescriptorFromImmutableSamplerInfo` 从压缩表示重建 `wgpu::YCbCrVkDescriptor`,链接到采样器描述符的 `nextInChain`。

### 调试标签

当 `caps()->setBackendLabels()` 为真时生成描述性标签:
- 基本格式: `"XClampYRepeatLinearMipNearest"`
- YCbCr 扩展: 添加模型、范围、分量交换、色度偏移等详细信息

## 依赖关系

- `Sampler` -- 基类
- `DawnSharedContext` -- 设备和能力
- `DawnCaps` -- 能力查询
- `DawnGraphiteUtils` -- YCbCr 描述符转换
- `SamplerDesc` -- 采样器参数封装

## 设计模式与设计决策

1. **SamplerDesc 保留**: 与 Metal/Vulkan 后端不同,DawnSampler 保留完整的 `SamplerDesc`,因为 Dawn 的不可变采样器信息需要在后续操作中访问。

2. **Mipmap 禁用策略**: 使用 `lodMaxClamp=0` 而非特殊过滤模式禁用 Mipmap,这是 WebGPU 的标准做法。

3. **Decal 不支持**: WebGPU 规范不包含 ClampToBorder 地址模式,Decal 模式必须在着色器中实现。

4. **平台条件编译**: YCbCr 支持仅在原生 Dawn 下可用,Emscripten 构建完全跳过相关代码。

## 性能考量

- 采样器创建是轻量操作,但 Graphite 仍通过全局缓存避免重复创建。
- 调试标签生成仅在启用标签时执行,字符串构建使用 `std::string::append` 减少内存分配。
- YCbCr 描述符解压为简单的位操作,无额外分配。
- `freeGpuData` 仅置空采样器引用,WebGPU 运行时处理实际释放。

## 相关文件

- `src/gpu/graphite/Sampler.h` -- 采样器基类
- `src/gpu/graphite/SamplerDesc.h` -- 采样器描述
- `src/gpu/graphite/dawn/DawnSharedContext.h` -- Dawn 共享上下文
- `src/gpu/graphite/dawn/DawnGraphiteUtils.h` -- YCbCr 工具函数
- `src/gpu/graphite/dawn/DawnCaps.h` -- Dawn 能力
