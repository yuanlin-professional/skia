# tests/graphite/ - Graphite GPU 后端测试

## 概述

`tests/graphite/` 目录包含 Skia 下一代 GPU 渲染后端 Graphite 的专用单元测试。Graphite 是 Skia 正在开发的现代 GPU 后端，设计目标是更好地利用 Vulkan、Metal 和 Dawn（WebGPU）等现代图形 API 的特性，包括更高效的命令缓冲区管理、更好的多线程支持和更优的 Pipeline 管理。

该目录包含约 50 个测试文件，涵盖 Graphite 后端的核心功能：纹理管理、缓冲区管理、资源缓存、Pipeline 数据缓存、录制器（Recorder）、图集（Atlas）、边界管理、预编译系统等。测试通过 `DEF_GRAPHITE_TEST_FOR_RENDERING_CONTEXTS` 等宏注册，由 DM 运行器在支持的 GPU 上下文中执行。

`precompile/` 子目录是一个重要的子模块，专门测试 Graphite 的 Pipeline 预编译系统。这是 Graphite 的关键特性之一，允许应用程序在绘制之前预编译 GPU Pipeline，避免运行时的卡顿。

测试文件按后端类型分为通用测试（在所有 Graphite 上下文中运行）和平台专用测试（如 `MtlBackendTextureTest.mm` 仅在 Metal 上运行，`DawnBackendTextureTest.cpp` 仅在 Dawn 上运行，`VulkanBackendTextureTest.cpp` 仅在 Vulkan 上运行）。

## 架构图

```
+---------------------------------------------------------------+
|                  DM 测试运行器                                  |
|  RunWithGraphiteTestContexts()                                |
|  +-----------------------------------------------------------+|
|  |  Context Type Filter                                      ||
|  |  +-----------+ +--------+ +---------+ +------+            ||
|  |  | All Ctx   | | Metal  | | Vulkan  | | Dawn |            ||
|  |  +-----------+ +--------+ +---------+ +------+            ||
|  +-----------------------------------------------------------+|
+-----------------------+---------------------------------------+
                        |
          +-------------+-------------+
          |                           |
+---------v---------+     +-----------v-----------+
| tests/graphite/   |     | tests/graphite/       |
| 通用 Graphite 测试 |     | precompile/           |
| ~35 个文件         |     | Pipeline 预编译测试    |
+-------------------+     | ~17 个文件             |
          |               +-----------------------+
          |                           |
          +-------------+-------------+
                        |
          +-------------v--------------+
          | include/gpu/graphite/      |
          | (Graphite 公共 API)         |
          |  Context, Recorder,        |
          |  Recording, TextureInfo... |
          +----------------------------+
                        |
          +-------------v--------------+
          | src/gpu/graphite/          |
          | (Graphite 内部实现)         |
          +----------------------------+
```

## 目录结构

```
tests/graphite/
├── precompile/                         # Pipeline 预编译测试子目录
│   ├── PrecompileTestUtils.h / .cpp    # 预编译测试工具
│   ├── PaintOptionsBuilder.h / .cpp    # PaintOptions 构建器
│   ├── PaintParamsTestUtils.h / .cpp   # 绘制参数测试工具
│   ├── AndroidPaintOptions.cpp         # Android 绘制选项测试
│   ├── AndroidPrecompileTest.cpp       # Android 预编译测试
│   ├── AndroidRuntimeEffectManager.h/.cpp # Android 运行时效果管理
│   ├── AndroidYCbCrPrecompileTest.cpp  # Android YCbCr 预编译
│   ├── ChromePrecompileTest.cpp        # Chrome 预编译测试
│   ├── CombinationBuilderTest.cpp      # 组合构建器测试
│   ├── PaintParamsKeyTest.cpp          # 绘制参数键测试
│   ├── PrecompileStatsTest.cpp         # 预编译统计测试
│   ├── ThreadedPrecompileTest.cpp      # 多线程预编译测试
│   └── UserdefinedStableKeyTest.cpp    # 用户定义稳定键测试
│
├── [纹理与后端测试]
│   ├── BackendTextureTest.cpp          # 通用后端纹理测试
│   ├── DawnBackendTextureTest.cpp      # Dawn 后端纹理
│   ├── MtlBackendTextureTest.mm        # Metal 后端纹理
│   ├── VulkanBackendTextureTest.cpp    # Vulkan 后端纹理
│   ├── TextureProxyTest.cpp            # 纹理代理
│   ├── TextureFormatTest.cpp           # 纹理格式数据传输测试
│   ├── UpdateBackendTextureTest.cpp    # 后端纹理更新
│   └── ImageWrapTextureMipmapsTest.cpp # 纹理 Mipmap 包装
│
├── [资源管理测试]
│   ├── GraphiteResourceCacheTest.cpp   # 资源缓存
│   ├── CacheBudgetTest.cpp             # 缓存预算
│   ├── CacheKeyTest.cpp                # 缓存键
│   ├── KeyTest.cpp                     # 通用键测试
│   ├── ProxyCacheTest.cpp              # 代理缓存
│   ├── NotifyInUseTest.cpp             # 使用中通知
│   └── BufferManagerTest.cpp           # 缓冲区管理器
│
├── [录制与提交测试]
│   ├── RecorderTest.cpp                # Recorder 功能测试
│   ├── RecordingOrderTest.cpp          # 录制顺序
│   ├── RecordingSurfacesTest.cpp       # 录制 Surface
│   ├── GraphiteContextRecorderTest.cpp # Context + Recorder 交互
│   └── SubmitWithFinishProcTest.cpp    # 提交完成回调
│
├── [绘制与渲染测试]
│   ├── DeviceTest.cpp                  # Graphite Device
│   ├── DrawAtlasTest.cpp              # 图集绘制
│   ├── MultisampleTest.cpp             # 多采样
│   ├── MutableImagesTest.cpp           # 可变图像
│   ├── ReadWritePixelsGraphiteTest.cpp # 像素读写
│   ├── SwizzleTest.cpp                 # 通道重排
│   ├── VerticesPaddingTest.cpp         # 顶点填充
│   └── InnerFillTest.cpp              # 内部填充
│
├── [图像处理测试]
│   ├── GraphitePromiseImageTest.cpp    # Promise 图像
│   ├── GraphiteYUVAPromiseImageTest.cpp# YUVA Promise 图像
│   ├── ImageProviderTest.cpp           # 图像提供者
│   ├── ImageShaderTest.cpp             # 图像着色器
│   └── ImageOriginTest.cpp            # 图像原点
│
├── [Pipeline 管理测试]
│   ├── PipelineDataCacheTest.cpp       # Pipeline 数据缓存
│   ├── PipelineCallbackTest.cpp        # Pipeline 回调
│   └── PersistentPipelineStorageTest.cpp # 持久化 Pipeline 存储
│
├── [几何与算法测试]
│   ├── BoundsManagerTest.cpp           # 边界管理器
│   ├── IntersectionTreeTest.cpp        # 相交树
│   ├── RectTest.cpp                    # 矩形操作
│   ├── ShapeTest.cpp                   # 形状
│   └── TransformTest.cpp              # 变换
│
├── [Uniform 管理测试]
│   ├── UniformManagerTest.cpp          # Uniform 管理器
│   └── UniformOffsetCalculatorTest.cpp # Uniform 偏移计算
│
├── [运行时效果测试]
│   └── RTEffectTest.cpp                # 运行时效果
│
├── [硬件缓冲区测试]
│   └── AHardwareBufferTest.cpp         # Android HardwareBuffer
│
└── [Vulkan 特定测试]
    ├── VulkanDstReadRenderpassReuseTest.cpp # Vulkan 目标读取渲染通道复用
    └── UploadBufferManagerTest.cpp     # 上传缓冲区管理器
```

## 关键类与函数

### 测试注册宏（来自 Test.h）

| 宏 | 用途 |
|----|------|
| `DEF_GRAPHITE_TEST(name, reporter, cts)` | 注册不需要 GPU 上下文的 Graphite 测试 |
| `DEF_GRAPHITE_TEST_FOR_RENDERING_CONTEXTS(name, reporter, ctx, cts)` | 在所有渲染上下文中运行 |
| `DEF_GRAPHITE_TEST_FOR_ALL_CONTEXTS(name, reporter, ctx, cts)` | 在所有上下文中运行（含 Mock） |
| `DEF_GRAPHITE_TEST_FOR_VULKAN_CONTEXT(name, reporter, ctx, cts)` | 仅在 Vulkan 上运行 |
| `DEF_GRAPHITE_TEST_FOR_METAL_CONTEXT(name, reporter, ctx, testCtx)` | 仅在 Metal 上运行 |
| `DEF_GRAPHITE_TEST_FOR_DAWN_CONTEXT(name, reporter, ctx, testCtx)` | 仅在 Dawn 上运行 |

### Graphite 核心测试类型

| 测试领域 | 关键 Graphite 类 | 测试文件 |
|----------|------------------|----------|
| 上下文管理 | `Context`, `Recorder` | `GraphiteContextRecorderTest.cpp` |
| 纹理管理 | `TextureProxy`, `BackendTexture` | `TextureProxyTest.cpp`, `BackendTextureTest.cpp` |
| 缓冲区管理 | `BufferManager`, `UploadBufferManager` | `BufferManagerTest.cpp`, `UploadBufferManagerTest.cpp` |
| 资源缓存 | `ResourceCache`, `ProxyCache` | `GraphiteResourceCacheTest.cpp`, `ProxyCacheTest.cpp` |
| Pipeline | `PipelineDataCache`, `PersistentPipelineStorage` | `PipelineDataCacheTest.cpp`, `PersistentPipelineStorageTest.cpp` |
| 几何处理 | `BoundsManager`, `IntersectionTree` | `BoundsManagerTest.cpp`, `IntersectionTreeTest.cpp` |
| 图像处理 | `PromiseImage`, `ImageProvider` | `GraphitePromiseImageTest.cpp`, `ImageProviderTest.cpp` |

## 依赖关系

```
tests/graphite/ 依赖:
├── tests/Test.h                          (测试框架)
├── include/gpu/graphite/Context.h        (Graphite 上下文)
├── include/gpu/graphite/Recorder.h       (录制器)
├── include/gpu/graphite/Recording.h      (录制结果)
├── include/gpu/graphite/TextureInfo.h    (纹理信息)
├── include/gpu/graphite/BackendTexture.h (后端纹理)
├── include/gpu/graphite/Surface.h        (Graphite Surface)
├── include/gpu/graphite/precompile/      (预编译 API)
├── src/gpu/graphite/                      (Graphite 内部实现)
└── tools/graphite/                        (Graphite 测试工具)
```

## 设计模式分析

### 1. 上下文迭代模式

通过 `RunWithGraphiteTestContexts` 函数，同一个测试自动在所有可用的 GPU 上下文（Metal、Vulkan、Dawn）中执行。这消除了为每个后端编写重复测试代码的需要。

### 2. Promise 模式

`GraphitePromiseImageTest.cpp` 测试了 Graphite 的延迟纹理机制。`PromiseImage` 允许应用程序先创建图像占位符，后续在 GPU 需要时才提供实际纹理数据，适用于流式加载场景。

### 3. 回调监控模式

`PipelineCallbackTest.cpp` 和 `SubmitWithFinishProcTest.cpp` 测试了 Graphite 的异步回调机制。GPU 工作完成后通过回调通知应用程序，这对于帧节奏控制和资源回收至关重要。

## 数据流

```
Graphite 测试执行流程:

DEF_GRAPHITE_TEST_FOR_RENDERING_CONTEXTS 注册测试
          |
          v
DM 运行器调用 RunWithGraphiteTestContexts
          |
          v
为每个可用后端创建 Context + GraphiteTestContext
          |
          +-- Metal Context ----+
          +-- Vulkan Context ---+
          +-- Dawn Context -----+
          |
          v
测试函数接收 (Reporter*, Context*, GraphiteTestContext*, TestOptions&)
          |
          v
创建 Recorder -> 执行绘制操作 -> 创建 Recording
          |
          v
Context->insertRecording() -> Context->submit()
          |
          v
验证结果 (像素比较 / 状态检查)
          |
          v
Reporter 报告通过/失败
```

## 相关文档与参考

- `tests/Test.h` - `DEF_GRAPHITE_TEST_*` 宏定义
- `include/gpu/graphite/` - Graphite 公共 API 头文件
- `src/gpu/graphite/` - Graphite 内部实现
- `tools/graphite/TestOptions.h` - Graphite 测试选项
- `tools/graphite/ContextFactory.h` - Graphite 上下文工厂
- `tests/graphite/precompile/` - Pipeline 预编译测试子目录
