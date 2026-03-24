# DawnGraphiteUtils -- Dawn/WebGPU 后端工具函数

> 源文件:
> - `src/gpu/graphite/dawn/DawnGraphiteUtils.h`
> - `src/gpu/graphite/dawn/DawnGraphiteUtils.cpp`

## 概述

DawnGraphiteUtils 是 Skia Graphite Dawn/WebGPU 后端的核心工具模块,提供 WGSL 着色器编译、纹理格式转换、YCbCr 描述符处理以及 Dawn Context 创建等功能。它同时支持原生 Dawn（桌面端）和 Emscripten WebGPU（Web 端）两种构建目标。

## 架构位置

```
Context (上层接口)
  -> DawnSharedContext (Dawn 共享上下文)
    -> DawnGraphiteUtils (工具函数)  <-- 本模块
       -> wgpu::Device (WebGPU 设备)
```

## 主要类与结构体

本模块不定义类,包含以下功能组:

### SkSLToWGSL

```cpp
inline bool SkSLToWGSL(const SkSL::ShaderCaps*, const std::string& sksl,
    SkSL::ProgramKind, const SkSL::ProgramSettings*,
    SkSL::NativeShader* wgsl, SkSL::ProgramInterface*, ShaderErrorHandler*);
```
内联函数,将 SkSL 编译为 WGSL,封装 `SkSLToBackend` 调用。

### BackendTextures 命名空间

```cpp
WGPUTexture GetDawnTexturePtr(const BackendTexture&);
WGPUTextureView GetDawnTextureViewPtr(const BackendTexture&);
```

## 公共 API 函数

### DawnCompileWGSLShaderModule

```cpp
bool DawnCompileWGSLShaderModule(const DawnSharedContext*, const char* label,
    const SkSL::NativeShader& wgsl, wgpu::ShaderModule*, ShaderErrorHandler*);
```
将 WGSL 代码编译为 `wgpu::ShaderModule`,通过回调检查编译错误。

### 纹理格式转换

```cpp
TextureFormat DawnFormatToTextureFormat(wgpu::TextureFormat);
wgpu::TextureFormat TextureFormatToDawnFormat(TextureFormat);
SkTextureCompressionType DawnFormatToCompressionType(wgpu::TextureFormat);
```

### YCbCr 描述符操作（非 Emscripten）

```cpp
bool DawnDescriptorIsValid(const wgpu::YCbCrVkDescriptor&);
bool DawnDescriptorUsesExternalFormat(const wgpu::YCbCrVkDescriptor&);
bool DawnDescriptorsAreEquivalent(const wgpu::YCbCrVkDescriptor&, const wgpu::YCbCrVkDescriptor&);
ImmutableSamplerInfo DawnDescriptorToImmutableSamplerInfo(const wgpu::YCbCrVkDescriptor&);
wgpu::YCbCrVkDescriptor DawnDescriptorFromImmutableSamplerInfo(ImmutableSamplerInfo);
```

## 内部实现细节

### 着色器编译验证

`check_shader_module` 通过 `GetCompilationInfo` API 异步获取编译结果:
- **Emscripten 旧版**（< 3.1.51）: 跳过检查直接返回 true
- **Emscripten 新版**: 使用废弃的回调 API
- **原生 Dawn**: 使用新的 `CallbackMode::WaitAnyOnly` API,通过 `instance.WaitAny` 同步等待

编译消息中只要有 `Error` 类型即认为失败,收集所有消息通过 `ShaderErrorHandler` 报告。

### 格式映射

使用双层 X-Macro:
- `DAWN_FORMAT_MAPPING` -- 所有平台通用格式
- `DAWN_FORMAT_MAPPING_NATIVE_ONLY` -- 仅原生 Dawn 支持的格式

原生特有格式包括:
- R16/RG16/RGBA16 Unorm
- YUV 双平面/三平面格式
- 外部格式（`OpaqueYCbCrAndroid`）

### YCbCr 信息压缩

将 `wgpu::YCbCrVkDescriptor` 的多个字段压缩到 32 位整数和 64 位格式值:

```
[位布局] usesExtFmt(1) | model(3) | range(1) | xChroma(1) | yChroma(1) |
         chromaFilter(2) | forceExplicit(1) | R(3) | G(3) | B(3) | A(3) = 22 位
```

反向提取使用移位和掩码操作。这用于管线缓存键和不可变采样器标识。

### Context 工厂

```cpp
namespace ContextFactory {
std::unique_ptr<Context> MakeDawn(const DawnBackendContext&, const ContextOptions&);
}
```

## 依赖关系

### 上游依赖
- `webgpu/webgpu_cpp.h` -- WebGPU C++ API
- `src/gpu/graphite/TextureFormat.h` -- 格式枚举
- `src/gpu/SkSLToBackend.h` -- 着色器编译框架
- `src/sksl/codegen/SkSLWGSLCodeGenerator.h` -- WGSL 代码生成

### 下游被依赖
- `DawnGraphicsPipeline` -- 着色器编译和格式转换
- `DawnTexture` -- 格式映射
- `DawnSampler` -- YCbCr 描述符处理

## 设计模式与设计决策

1. **平台抽象**: 通过 `__EMSCRIPTEN__` 宏隔离原生 Dawn 和 Web 端差异,同一接口适配两种运行环境。
2. **位压缩**: YCbCr 描述符的位压缩允许高效的键比较和缓存查找,同时保留完整的重建能力。
3. **双层格式映射**: 原生特有格式单独定义,Emscripten 构建时为空,避免编译错误。

## 性能考量

- WGSL 着色器描述符使用 `ShaderSourceWGSL`（原生）或 `ShaderModuleWGSLDescriptor`（Emscripten）,两者语义相同但 API 不同。
- 编译检查在原生 Dawn 上通过 `WaitAny` 同步等待,可能阻塞直到编译完成。
- 格式转换为 O(1) switch 查找。
- YCbCr 位操作全部为简单的移位/掩码,无分支。

## 相关文件

- `src/gpu/graphite/dawn/DawnSharedContext.h` -- Dawn 共享上下文
- `src/gpu/graphite/dawn/DawnQueueManager.h` -- Dawn 队列管理
- `src/gpu/graphite/dawn/DawnGraphicsPipeline.h` -- Dawn 图形管线
- `src/gpu/graphite/dawn/DawnSampler.h` -- Dawn 采样器
- `src/gpu/graphite/TextureFormat.h` -- 跨后端格式定义
- `include/gpu/graphite/dawn/DawnGraphiteTypes.h` -- Dawn 类型
