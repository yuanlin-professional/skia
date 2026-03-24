# GrContextFactory

> 源文件: `tools/ganesh/GrContextFactory.h`, `tools/ganesh/GrContextFactory.cpp`

## 概述

GrContextFactory 是 Skia 测试基础设施中用于创建和管理多种 GPU 后端 GrDirectContext 的工厂类。它支持 OpenGL、OpenGL ES、ANGLE（多种后端）、Vulkan、Metal、Direct3D 和 Mock 后端，为测试应用提供统一的接口来获取不同类型的 GPU 上下文。工厂管理上下文的整个生命周期，包括创建、共享组管理、放弃和销毁。

## 架构位置

```
测试基础设施
  +-- GrContextFactory (上下文工厂) <-- 本文件
       +-- TestContext (测试上下文基类)
            +-- GLTestContext
            +-- VkTestContext
            +-- MtlTestContext
            +-- D3DTestContext
            +-- MockTestContext
       +-- ContextInfo (上下文信息封装)
```

## 主要类与结构体

### `GrContextFactory`
- **不可拷贝**: 继承 `SkNoncopyable`
- **成员**:
  - `fContexts`: 上下文数组（`TArray<Context>`）
  - `fSentinelGLContext`: GL 哨兵上下文（防止 Vulkan 卡顿）
  - `fGlobalOptions`: 全局 GrContextOptions

### `GrContextFactory::Context`（私有结构体）
- `fType`, `fOverrides`, `fOptions`, `fBackend`
- `fTestContext`, `fGrContext`
- `fShareContext`, `fShareIndex`
- `fAbandoned`

### `GrContextFactory::ContextOverrides`（位域枚举）
- `kNone`: 无覆盖
- `kAvoidStencilBuffers`: 避免模板缓冲
- `kFakeGLESVersionAs2`: 伪装 GLES 2.0
- `kReducedShaders`: 简化着色器变体

### `ContextInfo`
上下文信息的公共封装，提供类型、后端、GrDirectContext、TestContext 和选项的访问。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `GrContextFactory(opts)` / `GrContextFactory()` | 构造函数 |
| `~GrContextFactory()` | 析构函数，销毁所有上下文 |
| `destroyContexts()` | 按逆序销毁所有上下文 |
| `abandonContexts()` | 按逆序放弃所有上下文 |
| `releaseResourcesAndAbandonContexts()` | 释放资源并放弃 |
| `getContextInfo(type, overrides)` | 获取指定类型的上下文信息 |
| `getSharedContextInfo(shareContext, shareIndex)` | 获取共享组中的上下文 |
| `get(type, overrides)` | 获取 GrDirectContext（简化接口） |
| `getGlobalOptions()` | 获取全局选项 |

## 内部实现细节

### 上下文创建（getContextInfoInternal）
1. 先查找已有匹配上下文（类型+覆盖+共享上下文+索引）
2. 若需共享，查找主上下文
3. 根据后端类型创建 TestContext：
   - **OpenGL**: `CreatePlatformGLTestContext`，支持 GL 和 GLES
   - **ANGLE**: `MakeANGLETestContext`，支持 D3D9/D3D11/OpenGL/Metal 后端，ES2/ES3 版本
   - **Vulkan**: `CreatePlatformVkTestContext`
   - **Metal**: `CreatePlatformMtlTestContext`
   - **Direct3D**: `CreatePlatformD3DTestContext`
   - **Mock**: `CreateMockTestContext`
4. 应用 ContextOverrides（模板缓冲、GLES 版本伪装、简化着色器）
5. 通过 `testCtx->makeContext(grOptions)` 创建 GrDirectContext

### 逆序销毁/放弃
所有销毁操作都按逆序执行，确保子上下文在父上下文之前处理。这是因为创建时子上下文总是追加到数组末尾。

### Vulkan 特殊处理
- **GL 哨兵上下文**: 创建 Vulkan 上下文时同时维护一个 GL 上下文，防止 NVIDIA GPU 上重复加载/卸载驱动导致的性能问题和 TSAN 报告
- **提前放弃**: Vulkan 需要在销毁 TestContext 之前先放弃 GrContext

### ANGLE D3D9 NVIDIA 过滤
ANGLE D3D9 在近期 NVIDIA 驱动上出现着色器链接失败，检测到 NVIDIA 时直接返回空。

### Windows 独立 GPU 选择
通过导出 `NvOptimusEnablement` 和 `AmdPowerXpressRequestHighPerformance` 符号，在双 GPU 笔记本上强制使用独立 GPU。

## 依赖关系

- **Ganesh**: `GrDirectContext`, `GrContextOptions`, `GrCaps`
- **测试上下文**: `GLTestContext`, `VkTestContext`, `MtlTestContext`, `D3DTestContext`, `MockTestContext`
- **ANGLE（条件编译）**: `GLTestContext_angle`
- **上下文类型**: `skgpu::ContextType`

## 设计模式与设计决策

1. **工厂模式**: 统一接口创建多种后端的 GPU 上下文
2. **上下文缓存**: 已创建的上下文被缓存复用，避免重复创建
3. **共享组支持**: 通过 `shareContext` 和 `shareIndex` 支持上下文共享组
4. **覆盖机制**: ContextOverrides 允许在全局选项基础上对特定上下文进行定制
5. **生命周期严格管理**: 逆序销毁保证依赖关系安全

## 性能考量

- 上下文缓存避免重复创建/销毁的开销
- GL 哨兵上下文是一个为性能而做的变通方案（NVIDIA Vulkan 驱动问题）
- `ContextOverrides::kReducedShaders` 可减少着色器编译时间

## 相关文件

- `tools/ganesh/TestContext.h` - 测试上下文基类
- `tools/gpu/ContextType.h` - 上下文类型枚举
- `tools/ganesh/gl/GLTestContext.h` - GL 测试上下文
- `tools/ganesh/vk/VkTestContext.h` - Vulkan 测试上下文
