# GrMtlUtil

> 源文件
> - src/gpu/ganesh/mtl/GrMtlUtil.h
> - src/gpu/ganesh/mtl/GrMtlUtil.mm

## 概述

`GrMtlUtil` 提供 Metal 后端的工具函数集合，包括 Objective-C 桥接辅助、着色器编译、纹理描述符创建、格式转换、错误处理等功能。这些工具函数封装 Metal API 的复杂性，提供类型安全的 C++ 接口，并实现编译超时保护、异步预编译等高级特性。该文件是 Metal 后端与底层 Metal 框架交互的关键桥梁。

## 架构位置

- **模块层级**：`src/gpu/ganesh/mtl/` - Ganesh Metal 后端
- **作用**：工具函数库和 Metal API 封装
- **使用者**：所有 Metal 后端组件

## 主要函数

### Objective-C 桥接

**GrGetMTLTexture**：
```cpp
SK_ALWAYS_INLINE id<MTLTexture> GrGetMTLTexture(const void* mtlTexture)
```
将 `void*` 转换为 `id<MTLTexture>`，处理 ARC 和非 ARC 编译模式。

**GrGetPtrFromId**：
```cpp
SK_ALWAYS_INLINE const void* GrGetPtrFromId(id idObject)
```
将 Objective-C 对象转换为 `void*` 指针。

**GrRetainPtrFromId**：
```cpp
SK_ALWAYS_INLINE CF_RETURNS_RETAINED const void* GrRetainPtrFromId(id idObject)
```
转换并增加引用计数（通过 `CFBridgingRetain`）。

### 着色器编译

**GrCompileMtlShaderLibrary**：
```cpp
id<MTLLibrary> GrCompileMtlShaderLibrary(
    const GrMtlGpu* gpu,
    const SkSL::NativeShader& msl,
    GrContextOptions::ShaderErrorHandler* errorHandler)
```
同步编译 MSL 着色器，处理错误回调。

**GrPrecompileMtlShaderLibrary**：
```cpp
void GrPrecompileMtlShaderLibrary(const GrMtlGpu* gpu, const SkSL::NativeShader& msl)
```
异步预编译着色器，结果缓存在 Apple 着色器缓存中，不关心返回值。

**GrMtlNewLibraryWithSource**：
```cpp
id<MTLLibrary> GrMtlNewLibraryWithSource(
    id<MTLDevice>, NSString* mslCode,
    MTLCompileOptions*, NSError**)
```
带超时保护的 `newLibraryWithSource` 替代版本。

**GrMtlNewRenderPipelineStateWithDescriptor**：
```cpp
id<MTLRenderPipelineState> GrMtlNewRenderPipelineStateWithDescriptor(
    id<MTLDevice>, MTLRenderPipelineDescriptor*, NSError**)
```
带超时保护的渲染管线状态创建。

### 纹理工具

**GrGetMTLTextureDescriptor**：
```cpp
MTLTextureDescriptor* GrGetMTLTextureDescriptor(id<MTLTexture> mtlTexture)
```
从现有纹理创建描述符，用于创建相同格式的纹理副本。

### 错误处理

**GrCreateMtlError**：
```cpp
NSError* GrCreateMtlError(NSString* description, GrMtlErrorCode errorCode)
```
创建自定义 Metal 错误对象。

**GrMtlErrorCode 枚举**：
```cpp
enum class GrMtlErrorCode {
    kTimeout = 1,
};
```
定义超时错误码。

## 内部实现细节

### ARC 兼容桥接

使用预处理宏 `__has_feature(objc_arc)` 检测 ARC 模式，条件编译不同的桥接代码：
- **ARC 模式**：使用 `__bridge` 转换
- **非 ARC 模式**：直接强制转换

### 超时保护

`GrMtlNewLibraryWithSource` 和 `GrMtlNewRenderPipelineStateWithDescriptor` 实现超时机制，防止编译卡死：
- 使用 `dispatch_semaphore` 和 `dispatch_time` 实现超时
- 默认超时时间（通常 10 秒）
- 超时后返回 `nil` 并创建超时错误

### 异步预编译

`GrPrecompileMtlShaderLibrary` 在后台线程编译着色器：
- 不阻塞主线程
- 失败静默忽略
- 利用 Apple 着色器缓存加速后续编译

## 设计模式与设计决策

### 内联辅助函数

桥接函数标记 `SK_ALWAYS_INLINE`，编译器内联优化，零运行时开销。

### 超时保护机制

防止 Metal 编译器 Bug 或复杂着色器导致的无限等待，提高稳定性。

### 异步编译优化

预编译不关心结果，仅为预热缓存，减少首次使用时的延迟。

### 错误标准化

封装 `NSError` 创建，统一错误处理流程。

## 性能考量

### 内联桥接

桥接函数内联后无函数调用开销，编译器优化为直接类型转换。

### 着色器缓存

利用 Apple 系统级着色器缓存，避免重复编译相同着色器。

### 异步预编译

后台预编译减少主线程阻塞，改善用户体验。

## 相关文件

- `src/gpu/ganesh/mtl/GrMtlGpu.h` - Metal GPU 实现
- `src/gpu/ganesh/mtl/GrMtlTypesPriv.h` - Metal 内部类型
- `include/gpu/ganesh/mtl/GrMtlBackendSurface.h` - Metal 后端表面
- `src/sksl/codegen/SkSLNativeShader.h` - 本地着色器表示
