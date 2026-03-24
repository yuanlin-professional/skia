# DawnTextureInfo - Dawn/WebGPU 纹理信息

> 源文件: `src/gpu/graphite/dawn/DawnTextureInfo.cpp`

## 概述

DawnTextureInfo.cpp 实现了 Skia Graphite Dawn 后端的纹理信息类 `DawnTextureInfo` 的核心方法以及 `TextureInfos` 命名空间中的工厂函数。Dawn 是 Google 的 WebGPU 实现，DawnTextureInfo 封装了 WebGPU 纹理的关键属性，包括纹理格式、用途、方面（aspect）和切片索引等。

该文件还处理了 YCbCr 纹理的特殊情况（通过 Vulkan 描述符），以及 Emscripten（WASM）环境下的条件编译差异。

## 架构位置

```
Graphite 纹理信息抽象层
  -> TextureInfo (跨后端纹理信息接口)
    -> DawnTextureInfo (Dawn/WebGPU 实现)
      -> wgpu::TextureFormat, wgpu::TextureUsage 等
```

DawnTextureInfo 是 Graphite 跨后端纹理信息系统的 Dawn 特定实现。

## 主要类与结构体

### `DawnTextureInfo`
- **职责**: 存储和查询 Dawn/WebGPU 纹理的属性
- **成员**（从源码推断）:
  - `fFormat`: `wgpu::TextureFormat` 纹理格式
  - `fUsage`: `wgpu::TextureUsage` 使用标志
  - `fAspect`: `wgpu::TextureAspect` 纹理方面
  - `fSlice`: 切片索引
  - `fYcbcrVkDescriptor`: YCbCr Vulkan 描述符（非 Emscripten 环境）

## 公共 API 函数

| 函数 | 命名空间 | 说明 |
|------|----------|------|
| `DawnTextureInfo(WGPUTexture)` | - | 从 WebGPU 纹理对象构造 |
| `viewFormat()` | - | 返回跨后端的 TextureFormat |
| `toBackendString()` | - | 序列化为人可读字符串 |
| `isCompatible(TextureInfo, bool)` | - | 兼容性检查 |
| `MakeDawn(const DawnTextureInfo&)` | `TextureInfos` | 从 DawnTextureInfo 创建 TextureInfo |
| `GetDawnTextureInfo(TextureInfo, DawnTextureInfo*)` | `TextureInfos` | 提取 Dawn 纹理信息 |

## 内部实现细节

### 从 WGPUTexture 构造
使用委托构造函数调用完整参数版本的构造函数，从 `WGPUTexture` 句柄读取：
- `wgpuTextureGetSampleCount` -> 采样数
- `wgpuTextureGetMipLevelCount` -> mipmap
- `wgpuTextureGetFormat` -> 格式（用于 format 和 viewFormat）
- `wgpuTextureGetUsage` -> 用途
- 默认 `TextureAspect::All` 和 `slice=0`

### viewFormat 的 YCbCr 处理
在非 Emscripten 环境下，如果 `fYcbcrVkDescriptor.externalFormat != 0`，返回 `TextureFormat::kExternal`。否则通过 `DawnFormatToTextureFormat` 将 WebGPU 格式转换为 Skia 的通用格式。

### 兼容性检查
`isCompatible` 检查以下条件：
1. view format 必须匹配
2. usage 的当前值必须是目标 usage 的子集
3. YCbCr 描述符必须等价（非 Emscripten）
4. aspect 必须匹配，或者 `!requireExact` 时允许 `All` 与具体 aspect 匹配

### Emscripten 条件编译
使用 `#if !defined(__EMSCRIPTEN__)` 来排除 YCbCr 相关代码，因为 WebAssembly 环境下不支持 Vulkan 互操作。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `src/gpu/graphite/TextureInfoPriv.h` | TextureInfo 私有构造和访问接口 |
| `include/gpu/graphite/dawn/DawnGraphiteTypes.h` | DawnTextureInfo 类型声明 |
| `src/gpu/graphite/dawn/DawnGraphiteUtils.h` | Dawn 工具函数（DawnFormatToTextureFormat 等） |
| `include/core/SkString.h` | SkStringPrintf 字符串格式化 |

## 设计模式与设计决策

1. **与 MtlTextureInfo 对称设计**: DawnTextureInfo 和 MtlTextureInfo 遵循完全相同的接口模式（viewFormat、toBackendString、isCompatible），体现了 Graphite 的跨后端统一架构。

2. **Aspect 的灵活匹配**: 在非精确模式下允许 `All` aspect 与任何具体 aspect 匹配，简化了多平面纹理的资源复用逻辑。

3. **C API 桥接**: 构造函数使用 WebGPU 的 C API（`wgpuTextureGet*`），而非 C++ 封装（`wgpu::Texture`），保持与 Dawn 底层接口的兼容性。

## 性能考量

1. **构造开销**: 从 `WGPUTexture` 构造需要多次 WebGPU C API 调用，但通常只在纹理创建时执行一次。
2. **字符串格式化**: `toBackendString` 使用 `SkStringPrintf`，仅在调试和日志输出时调用。

## 相关文件

- `include/gpu/graphite/dawn/DawnGraphiteTypes.h` - DawnTextureInfo 的声明
- `src/gpu/graphite/TextureInfoPriv.h` - TextureInfo 私有接口
- `src/gpu/graphite/dawn/DawnGraphiteUtils.h` - Dawn 工具函数
- `src/gpu/graphite/mtl/MtlTextureInfo.mm` - Metal 对应实现（对称设计）
