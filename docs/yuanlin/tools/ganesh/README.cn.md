# tools/ganesh - Ganesh GPU 后端测试工具集

## 概述

`tools/ganesh` 目录包含了 Skia Ganesh GPU 后端的测试基础设施和辅助工具。Ganesh 是 Skia 的传统 GPU 渲染后端，支持 OpenGL、Vulkan、Metal、Direct3D 以及 Mock 等多种图形 API。本目录提供了统一的测试上下文管理框架，使得 Skia 开发者能够在不同的 GPU 后端之间无缝切换并执行测试。

核心功能围绕 `GrContextFactory` 和 `TestContext` 两个关键类展开。`GrContextFactory` 是一个工厂类，负责创建和管理不同类型的 GPU 上下文（如 GL、Vulkan、Metal 等），并维护它们的生命周期。`TestContext` 则是所有平台特定 GPU 测试上下文的抽象基类，定义了上下文切换、GPU 计时和同步等核心接口。

此外，本目录还包含了大量的测试辅助工具，包括内存缓存模拟（`MemoryCache`）、延迟显示列表（DDL）支持工具（`DDLPromiseImageHelper`、`DDLTileHelper`）、纹理代理工具（`ProxyUtils`）、Atlas 纹理管理工具（`GrAtlasTools`）以及测试用的渲染操作（`TestOps`）等。这些工具共同构成了 Ganesh 后端的完整测试生态。

本目录下的子目录按照各个图形 API 后端进行组织，分别为 `gl/`（OpenGL）、`vk/`（Vulkan）、`mtl/`（Metal）、`d3d/`（Direct3D）和 `mock/`（模拟后端），每个子目录实现了对应后端的 `TestContext` 具体子类。

## 目录结构

```
tools/ganesh/
├── BUILD.bazel                    # Bazel 构建配置
├── GrContextFactory.h/.cpp        # GPU 上下文工厂，管理多后端上下文创建
├── TestContext.h/.cpp              # 测试上下文抽象基类
├── MemoryCache.h/.cpp             # 内存着色器缓存实现
├── DDLPromiseImageHelper.h/.cpp   # DDL Promise 图像辅助类
├── DDLTileHelper.h/.cpp           # DDL 瓦片渲染辅助类
├── TestOps.h/.cpp                 # 测试用 GPU 绘制操作
├── ProxyUtils.h/.cpp              # 纹理代理工具函数
├── TestCanvas.h/.cpp              # 测试画布（支持 Slug 渲染）
├── GrAtlasTools.h/.cpp            # Atlas 纹理管理调试工具
├── AtlasTextOpTools.h/.cpp        # Atlas 文本操作测试工具
├── GpuTimer.h                     # GPU 计时器抽象接口
├── GrTest.cpp                     # 通用测试辅助函数
├── ProtectedUtils_Ganesh.cpp      # 受保护内容（DRM）测试工具
├── gl/                            # OpenGL 后端（含多个子目录）
├── vk/                            # Vulkan 后端
├── mtl/                           # Metal 后端
├── d3d/                           # Direct3D 后端
└── mock/                          # Mock 模拟后端
```

## 关键类与函数

### GrContextFactory
- **命名空间**: `sk_gpu_test`
- **功能**: 创建和管理不同 GPU 后端的 `GrDirectContext` 实例
- **核心方法**:
  - `getContextInfo(ContextType, ContextOverrides)` - 获取指定类型的上下文信息
  - `getSharedContextInfo(GrDirectContext*, uint32_t)` - 获取共享上下文组中的上下文
  - `destroyContexts()` - 按逆序销毁所有上下文
  - `abandonContexts()` - 放弃所有上下文（模拟 GPU 丢失）
- **上下文覆盖选项**: `kAvoidStencilBuffers`、`kFakeGLESVersionAs2`、`kReducedShaders`

### TestContext
- **命名空间**: `sk_gpu_test`
- **功能**: 离屏 3D 上下文的抽象基类
- **核心方法**:
  - `makeCurrent()` / `makeNotCurrent()` - 上下文切换
  - `makeCurrentAndAutoRestore()` - RAII 风格的上下文切换
  - `makeContext(const GrContextOptions&)` - 创建 GrDirectContext
  - `flushAndWaitOnSync(GrDirectContext*)` - 刷新并等待 GPU 同步

### MemoryCache
- 实现 `GrContextOptions::PersistentCache` 接口
- 提供内存中的着色器程序缓存，支持缓存命中统计和磁盘导出

### DDLPromiseImageHelper / DDLTileHelper
- 支持延迟显示列表（DDL）的多线程渲染测试
- `DDLPromiseImageHelper`: 管理 Promise 图像的创建和 GPU 上传
- `DDLTileHelper`: 管理瓦片化 DDL 渲染流程

### TestOps (sk_gpu_test::test_ops)
- `MakeRect()` - 创建带有自定义局部坐标和局部矩阵的矩形绘制操作
- 支持多种重载：接受 `GrPaint`、`GrFragmentProcessor` 或简化的矩形参数
- 主要用于测试几何处理器（GP）的局部矩阵功能

### GrAtlasTools / AtlasTextOpTools
- `GrAtlasManagerTools::Dump()` - 转储 Atlas 管理器状态信息
- `GrAtlasManagerTools::SetAtlasDimensionsToMinimum()` - 将 Atlas 尺寸设为最小值（测试用）
- `GrDrawOpAtlasTools::NumAllocated()` - 查询已分配的 Atlas 页面数量
- `AtlasTextOpTools::CreateOp()` - 创建用于测试的 Atlas 文本绘制操作

### ProxyUtils
- `GetTextureImageProxy()` - 获取纹理后备图像的代理对象
- `MakeTextureProxyViewFromData()` - 从像素数据创建纹理代理视图
- `CreateProgramInfo()` - 创建用于测试的 GPU 程序信息对象

### TestCanvas (skiatest)
- `TestCanvas<SkSlugTestKey>` - 使用 Slug 渲染替代文本 Blob 渲染的测试画布
- `TestCanvas<SkSerializeSlugTestKey>` - 测试 Slug 序列化/反序列化的画布
- `TestCanvas<SkRemoteSlugTestKey>` - 测试远程 Slug 渲染的画布（含 StrikeServer/Client）

### GpuTimer
- 平台无关的 GPU 计时接口
- 支持 disjoint 检测（检测 GPU 操作是否被中断）
- 提供 `QueryStatus` 枚举：`kInvalid`、`kPending`、`kDisjoint`、`kAccurate`

### ProtectedUtils (Ganesh)
- `CreateProtectedSkSurface()` - 创建受保护的 SkSurface（用于 DRM 内容测试）
- `CreateProtectedSkImage()` - 创建受保护的 SkImage
- `CheckImageBEProtection()` - 验证后端纹理的保护状态

## 依赖关系

- **上游依赖**: `include/gpu/ganesh/`（GrDirectContext、GrContextOptions）、`src/gpu/ganesh/`（内部 GPU 实现）
- **同级依赖**: `tools/gpu/`（ContextType 定义、BackendSurfaceFactory）
- **下游依赖**: `tests/`（GPU 单元测试）、`bench/`（GPU 性能测试）、`dm/`（测试驱动）
- **条件依赖**: 各后端子目录通过编译宏（`SK_GL`、`SK_VULKAN`、`SK_METAL`、`SK_DIRECT3D`）条件编译

## 相关文档与参考

- `tools/ganesh/gl/` - OpenGL 测试上下文及其平台实现
- `tools/ganesh/vk/` - Vulkan 测试上下文
- `tools/ganesh/mtl/` - Metal 测试上下文
- `tools/ganesh/d3d/` - Direct3D 测试上下文
- `tools/ganesh/mock/` - Mock 模拟测试上下文
- `tools/gpu/ContextType.h` - 上下文类型枚举定义
- `include/gpu/ganesh/GrDirectContext.h` - Ganesh 直接上下文公共 API
- `include/gpu/ganesh/GrContextOptions.h` - 上下文配置选项
