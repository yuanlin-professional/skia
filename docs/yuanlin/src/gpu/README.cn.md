# src/gpu - Skia GPU 共享抽象层

## 概述

`src/gpu` 顶层目录是 Skia 图形库中 GPU 加速渲染的**共享基础设施层**。该目录包含了被 Ganesh（Skia 的传统 GPU 后端）和 Graphite（Skia 的新一代 GPU 后端）共同使用的类型定义、工具函数和抽象接口。这些共享代码位于 `skgpu` 命名空间下，是连接上层渲染 API 与底层图形驱动之间的关键桥梁。

从历史角度来看，Skia 最初仅有 Ganesh 作为 GPU 后端（其代码位于 `src/gpu/ganesh`）。随着 2022 年 Graphite 项目的启动（代码位于 `src/gpu/graphite`），团队将两个后端中通用的混合（Blend）、资源键（ResourceKey）、缓冲区写入（BufferWriter）、矩形装箱（Rectanizer）、通道重排（Swizzle）等基础设施提取到了 `src/gpu` 顶层目录，避免代码重复并确保行为一致性。

该目录中的代码不直接调用任何图形 API（如 OpenGL、Vulkan、Metal、Dawn），而是提供与 API 无关的算法和数据结构。具体的图形 API 绑定由子目录（`ganesh/`、`graphite/`、`vk/`、`mtl/` 等）负责。这种分层设计使得新增或替换图形后端时不需要修改核心渲染算法。

本目录中的代码通过 Bazel 构建系统组织为一个名为 `gpu` 的共享库目标（`skia_cc_library`），同时包含 `tessellate` 子目录的曲面细分代码。该库被 `src/gpu` 的所有子包和 `src/sksl/codegen` 所依赖。

## 架构图

```
+-----------------------------------------------------------------------+
|                        Skia 公共 API 层                                |
|            (include/core, include/gpu)                                 |
+-----------------------------------------------------------------------+
        |                       |                       |
        v                       v                       v
+---------------+     +------------------+     +------------------+
|  src/gpu/     |     |  src/gpu/        |     |  src/gpu/        |
|  ganesh/      |     |  graphite/       |     |  tessellate/     |
|  (传统后端)    |     |  (新一代后端)     |     |  (曲面细分)      |
+-------+-+-----+     +------+-+---------+     +--------+---------+
        | |                   | |                        |
        | +-------------------+ +------------------------+
        |           |
        v           v
+-----------------------------------------------------------------------+
|                  src/gpu/ 顶层共享代码                                  |
|                                                                        |
|  +------------+ +-------------+ +----------+ +-----------+ +--------+ |
|  | Blend      | | ResourceKey | | Swizzle  | | Rectanizer| | Buffer | |
|  | BlendForm. | | KeyBuilder  | | SwizzlePr| | Pow2/Sky. | | Writer | |
|  +------------+ +-------------+ +----------+ +-----------+ +--------+ |
|                                                                        |
|  +------------+ +-------------+ +----------+ +-----------+ +--------+ |
|  | BlurUtils  | | DitherUtils | | DataUtils| | Token     | | GpuRef | |
|  +------------+ +-------------+ +----------+ | TokenTrkr | | Cnt    | |
|                                               +-----------+ +--------+ |
|                                                                        |
|  +-------------------+ +-----------------+ +-------------------+       |
|  | AsyncReadTypes    | | RefCntedCallback| | TiledTextureUtils |       |
|  +-------------------+ +-----------------+ +-------------------+       |
|                                                                        |
|  +-------------------+ +-----------------+ +-------------------+       |
|  | SkSLToBackend     | | ShaderErrHandler| | MutableTexState   |       |
|  +-------------------+ +-----------------+ +-------------------+       |
+-----------------------------------------------------------------------+
        |                       |                       |
        v                       v                       v
+---------------+     +------------------+     +------------------+
|  src/gpu/vk/  |     |  src/gpu/mtl/    |     |  src/gpu/android/|
|  (Vulkan)     |     |  (Metal)         |     |  (Android/HWBuf) |
+---------------+     +------------------+     +------------------+
```

## 目录结构

### 子目录

| 子目录 | 用途 |
|--------|------|
| `ganesh/` | Ganesh GPU 后端实现（传统的基于 OpenGL/Vulkan/Metal 的渲染后端） |
| `graphite/` | Graphite GPU 后端实现（新一代基于现代图形 API 的渲染后端） |
| `tessellate/` | 共享的 GPU 曲面细分算法，包括 Wang 公式、中点解析、笔画迭代器等 |
| `vk/` | Vulkan 相关的共享工具代码（VulkanInterface、VulkanMemory 等） |
| `mtl/` | Metal 相关的共享工具代码（MtlMemoryAllocator、MtlUtils 等） |
| `android/` | Android 平台特有的 GPU 代码（AHardwareBuffer、Vulkan 内存分配器） |

### 顶层文件列表

| 文件 | 描述 |
|------|------|
| `Blend.h / Blend.cpp` | 混合方程和混合系数的枚举定义及 Porter-Duff 混合常量表 |
| `BlendFormula.h / BlendFormula.cpp` | 封装 Porter-Duff 混合公式的位域优化类 |
| `BlurUtils.h / BlurUtils.cpp` | GPU 模糊效果工具：高斯核计算、圆形/圆角矩形模糊掩码生成 |
| `BufferWriter.h` | GPU 缓冲区写入器：VertexWriter、IndexWriter、TextureUploadWriter |
| `AsyncReadTypes.h` | 异步读取类型：映射缓冲区管理器和异步读取结果模板 |
| `ResourceKey.h / ResourceKey.cpp` | GPU 资源缓存键系统：ScratchKey、UniqueKey、FixedSizeKey |
| `KeyBuilder.h` | 位级别的键构建器，用于生成着色器程序的缓存键 |
| `Swizzle.h / Swizzle.cpp` | RGBA 通道重排工具类，支持串联、求逆、应用到颜色值 |
| `SwizzlePriv.h` | Swizzle 的私有构造访问器 |
| `Rectanizer.h` | 矩形装箱算法的抽象基类接口（用于纹理图集） |
| `RectanizerPow2.h / .cpp` | 基于 2 的幂次量化的矩形装箱实现 |
| `RectanizerSkyline.h / .cpp` | 基于天际线算法的矩形装箱实现（更优的打包率） |
| `GpuRefCnt.h` | 自定义引用计数智能指针 `gr_sp`、`gr_cb`、`gr_rp` |
| `GpuTypesPriv.h` | GPU 类型私有定义：线程安全枚举、纹理压缩类型转换、后端 API 名称 |
| `RefCntedCallback.h` | 引用计数回调封装：AutoCallback（移动语义）和 RefCntedCallback |
| `Token.h` | 通用操作序列令牌及其追踪器，用于 Recorder 中的操作排序 |
| `MaskFormat.h` | 字体缓存掩码格式枚举（A8、A565、ARGB） |
| `TiledTextureUtils.h / .cpp` | 分块纹理绘制工具：判断是否应分块、优化采样区域 |
| `DataUtils.h / .cpp` | 纹理压缩数据工具：计算压缩块数量、行字节、维度等 |
| `DitherUtils.h / .cpp` | 抖动工具：生成抖动查找表、计算抖动范围 |
| `SkSLToBackend.h / .cpp` | SkSL 着色器编译为后端着色器语言的通用包装器 |
| `ShaderErrorHandler.cpp` | 默认着色器编译错误处理器实现 |
| `SkBackingFit.h / .cpp` | 纹理尺寸近似算法：将尺寸映射到 2 的幂次或其中间值 |
| `MutableTextureState.cpp` | 可变纹理状态的实现 |
| `MutableTextureStatePriv.h` | 可变纹理状态的私有接口 |
| `SkRenderEngineAbortf.h` | Android RenderEngine 环境下的错误中止宏 |
| `gpu_workaround_list.txt` | GPU 驱动缺陷/变通方案列表 |
| `BUILD.bazel` | Bazel 构建配置文件 |

## 关键类与函数

### BlendEquation / BlendCoeff / BlendInfo
- **文件**: `Blend.h` / `Blend.cpp`
- **职责**: 定义 GPU 混合操作的基本类型。`BlendEquation` 枚举涵盖基础混合方程（Add、Subtract、ReverseSubtract）以及 SVG/PDF 规范中定义的高级混合方程（Screen、Overlay、Darken 等共 14 种）。`BlendCoeff` 枚举涵盖 17 种混合系数（Zero、One、SrcColor、DstAlpha 等）。`BlendInfo` 结构体聚合了完整的混合状态信息。
- **关键函数**:
  - `BlendFuncName(SkBlendMode)` - 返回对应混合模式的 SkSL 内建函数名
  - `GetPorterDuffBlendConstants(SkBlendMode)` - 返回 Porter-Duff 混合的 4 个浮点常量
  - `GetReducedBlendModeInfo(SkBlendMode)` - 返回优化后的混合函数名 + uniform 数据
  - `BlendEquationIsAdvanced()` - 判断是否为高级混合方程
  - `BlendAllowsCoverageAsAlpha()` - 判断是否允许将覆盖率折叠到 Alpha 通道
  - `BlendModifiesDst()` - 判断混合是否修改目标像素
  - `BlendShouldDisable()` - 判断混合是否可以被禁用（优化场景）

### BlendFormula
- **文件**: `BlendFormula.h` / `BlendFormula.cpp`
- **职责**: 封装带覆盖率（coverage）的 Porter-Duff 混合公式的完整状态。使用位域将主输出类型、次输出类型、混合方程、源系数和目标系数压缩到仅 4 字节中。这是性能关键路径上的核心类型。
- **关键方法**:
  - `hasSecondaryOutput()` - 是否需要双源混合
  - `modifiesDst()` - 是否修改目标颜色
  - `unaffectedByDst()` / `unaffectedByDstIfOpaque()` - 是否不受目标颜色影响
  - `usesInputColor()` - 是否使用输入颜色
  - `canTweakAlphaForCoverage()` - 是否可以通过调整 Alpha 来实现覆盖率
  - `GetBlendFormula(isOpaque, hasCoverage, xfermode)` - 查表获取混合公式
  - `GetLCDBlendFormula(xfermode)` - 获取 LCD 亚像素渲染的混合公式

### ResourceKey / ScratchKey / UniqueKey / FixedSizeKey
- **文件**: `ResourceKey.h` / `ResourceKey.cpp`
- **职责**: GPU 资源缓存键系统的核心。`ResourceKey` 是所有键类型的基类，内部使用 `uint32_t` 数组存储键数据，包含哈希值和域标识元数据。
  - `ScratchKey` - 临时资源键，多个资源可共享同一 ScratchKey；资源被引用时不会从缓存返回
  - `UniqueKey` - 唯一资源键，同一时刻只有一个资源持有某个 UniqueKey；即使被引用也可从缓存返回
  - `FixedSizeKey<N>` - 编译期固定大小的键，无需动态分配，适用于专用缓存
- **关键方法**:
  - `ResourceKey::Builder` - 用于构建键的 RAII 工具，析构时自动计算哈希
  - `ResourceKeyHash()` - 计算键数据的哈希值
  - `UniqueKey::GenerateDomain()` - 生成唯一域标识
  - `ScratchKey::GenerateResourceType()` - 生成唯一资源类型标识
  - `UniqueKeyInvalidatedMessage` - 键失效消息，通过消息总线通知缓存清理

### BufferWriter / VertexWriter / IndexWriter / TextureUploadWriter
- **文件**: `BufferWriter.h`
- **职责**: 提供类型安全的 GPU 缓冲区写入接口。`BufferWriter` 是基类，使用 `Mark` 标记位置并在 Debug 模式下进行边界检查。
  - `VertexWriter` - 顶点数据写入器，支持流式 `<<` 运算符、条件写入、数组写入、四角写入（TriStrip/TriFan）
  - `IndexWriter` - 索引数据写入器，专门用于 `uint16_t` 索引
  - `TextureUploadWriter` - 纹理上传数据写入器，支持行拷贝、格式转换、RGB888x 到 RGB888 的转换
- **关键方法**:
  - `VertexWriter::writeQuad()` - 一次写入四个顶点的数据，支持 TriStrip 和 TriFan 布局
  - `VertexWriter::If()` - 条件性写入数据
  - `VertexWriter::Array()` / `VertexWriter::Repeat()` - 批量写入辅助
  - `VertexColor` - 支持 4 字节或 16 字节（宽色域）颜色写入
  - `TextureUploadWriter::writeRGBFromRGBx()` - RGB888x 到 RGB888 的像素格式转换

### Swizzle
- **文件**: `Swizzle.h` / `Swizzle.cpp` / `SwizzlePriv.h`
- **职责**: 表示 RGBA 通道重新排列，使用 16 位紧凑编码存储 4 个通道索引。支持的通道值包括 r、g、b、a、0（常量零）和 1（常量一）。
- **关键方法**:
  - `Swizzle::Concat(a, b)` - 串联两个 Swizzle，结果等效于先应用 a 再应用 b
  - `Swizzle::invert()` - 计算近似逆 Swizzle
  - `Swizzle::applyTo(color)` - 将 Swizzle 应用于颜色值
  - `Swizzle::selectChannelInR(i)` - 将第 i 个通道提取到 R 通道，其余置零
  - `Swizzle::asKey()` - 返回紧凑的 16 位键值，适合用作哈希表键
  - 预定义常量：`RGBA()`、`BGRA()`、`RRRA()`、`RGB1()`

### Rectanizer / RectanizerPow2 / RectanizerSkyline
- **文件**: `Rectanizer.h`、`RectanizerPow2.h/.cpp`、`RectanizerSkyline.h/.cpp`
- **职责**: 矩形装箱（bin packing）算法，主要用于纹理图集（Texture Atlas）的空间分配。在字体渲染中，需要将大量小的字形位图打包到少量大纹理中，这些算法负责高效地分配矩形区域。
- **实现策略**:
  - `RectanizerPow2` - 将输入矩形量化到 2 的幂次高度，每个高度等级最多有一个活跃行。简单但浪费空间。
  - `RectanizerSkyline` - 基于天际线轮廓算法（参考 Jukka Jylanki 的工作），追踪当前顶部轮廓线来寻找最佳放置位置。几乎总是提供更好的打包效果。
- **关键方法**:
  - `addRect(width, height, loc)` - 尝试分配矩形区域
  - `addPaddedRect()` - 带内边距的矩形分配
  - `percentFull()` - 返回已使用面积百分比
  - `Factory()` - 工厂方法，返回当前首选的子类实例

### TClientMappedBufferManager / TAsyncReadResult
- **文件**: `AsyncReadTypes.h`
- **职责**: 管理异步 GPU 读回操作中的映射缓冲区生命周期。当客户端在另一个线程消费映射缓冲区数据时，该模板管理缓冲区的注册、消息轮询和取消映射。`TAsyncReadResult` 实现了 `SkImage::AsyncReadResult` 接口，支持多平面数据（如 YUV 格式）。
- **关键方法**:
  - `insert(buffer)` - 注册一个即将交给客户端的映射缓冲区
  - `process()` - 轮询消息并取消映射已完成的缓冲区
  - `abandon()` - 通知管理器上下文已被放弃
  - `TAsyncReadResult::addTransferResult()` - 添加传输结果，支持可选的像素格式转换

### KeyBuilder / StringKeyBuilder
- **文件**: `KeyBuilder.h`
- **职责**: 按位级别构建缓存键。`KeyBuilder` 将任意位数（1-32 位）的值打包到 `uint32_t` 数组中，自动处理跨字边界的溢出。`StringKeyBuilder` 继承它并额外生成人类可读的描述字符串，用于调试。
- **关键方法**:
  - `addBits(numBits, val, label)` - 添加指定位数的值
  - `addBool(b, label)` - 添加 1 位布尔值
  - `add32(v, label)` - 添加完整的 32 位值
  - `addBytes(numBytes, data, label)` - 逐字节添加数据
  - `flush()` - 引入字边界，在使用键之前必须调用

### gr_sp / gr_cb / gr_rp
- **文件**: `GpuRefCnt.h`
- **职责**: GPU 特有的智能指针模板。`gr_sp<T, Ref, Unref>` 是核心模板，通过 auto 模板参数支持自定义的引用/取消引用方法。
  - `gr_cb<T>` - 跟踪 GPU 命令缓冲区引用的智能指针，调用 `refCommandBuffer()`/`unrefCommandBuffer()`。允许临时资源在 GPU 使用期间被复用。
  - `gr_rp<T>` - 调用 `recycle()` 而非 `unref()` 的智能指针，用于对象池复用。
- **关键特性**: 支持从 `sk_sp` 转换构造，支持移动语义，零开销抽象

### Token / TokenTracker
- **文件**: `Token.h`
- **职责**: 用于在 Recorder 中对操作进行排序的通用序列令牌。`Token` 是一个基于 `uint64_t` 序列号的不透明值类型，`TokenTracker` 管理绘制令牌和刷新令牌的递增分发。
- **关键方法**:
  - `Token::inInterval(start, end)` - 判断令牌是否在指定区间内
  - `TokenTracker::nextFlushToken()` - 获取当前正在录制的批次的令牌
  - `TokenTracker::nextDrawToken()` - 获取下一个绘制令牌
  - `TokenTracker::issueDrawToken()` / `issueFlushToken()` - 发放令牌（仅限友元类调用）

### RefCntedCallback / AutoCallback
- **文件**: `RefCntedCallback.h`
- **职责**: 回调机制的封装。`AutoCallback` 是一个仅支持移动语义的类型，在析构时调用回调函数。支持四种回调变体：基本回调、带 GPU 统计的回调、带结果的回调、带结果和统计的回调。`RefCntedCallback` 是它的引用计数包装器。
- **关键方法**:
  - `setFailureResult()` - 标记操作失败
  - `setStats(stats)` - 设置 GPU 统计数据
  - `RefCntedCallback::Make()` - 工厂方法，返回 `sk_sp<RefCntedCallback>`

### MaskFormat
- **文件**: `MaskFormat.h`
- **职责**: 定义字体缓存中使用的掩码格式枚举。
  - `kA8` - 单字节灰度掩码
  - `kA565` - 双字节 RGB565 格式，用于 LCD 亚像素渲染的三通道覆盖率
  - `kARGB` - 四字节彩色格式
- **关键函数**:
  - `MaskFormatBytesPerPixel()` - 返回每像素字节数
  - `MaskFormatToColorType()` - 转换为对应的 `SkColorType`

### SkSLToBackend
- **文件**: `SkSLToBackend.h` / `SkSLToBackend.cpp`
- **职责**: SkSL 着色器编译为特定后端着色器语言的通用包装器。它封装了 SkSL 编译器的调用流程，包含错误处理、调试输出和程序接口提取。
- **关键参数**:
  - `caps` - 着色器能力描述
  - `toBackend` - 后端特定的转换回调函数
  - `errorHandler` - 编译错误处理器
  - 支持输出文本格式（GLSL/MSL/WGSL）和二进制格式（SPIR-V）

### TiledTextureUtils
- **文件**: `TiledTextureUtils.h` / `TiledTextureUtils.cpp`
- **职责**: 处理超大纹理的分块绘制策略。当图像超过 GPU 纹理尺寸限制时，自动将其拆分为多个较小的瓦片进行绘制。
- **关键方法**:
  - `ShouldTileImage()` - 根据裁剪区域、矩阵变换和纹理限制判断是否需要分块
  - `OptimizeSampleArea()` - 优化采样区域以减少不必要的纹理传输
  - `DrawAsTiledImageRect()` - 执行分块绘制
  - `CanDisableMipmap()` - 判断是否可以跳过 mipmap 生成

### BlurUtils
- **文件**: `BlurUtils.h` / `BlurUtils.cpp`
- **职责**: GPU 模糊效果的各种工具函数。主要封装了 `SkShaderBlurAlgorithm` 和 `SkBlurEngine` 的功能，同时提供了用于缓存纹理生成的积分表和圆形剖面图。
- **关键函数**:
  - `Compute2DBlurKernel()` / `Compute1DBlurKernel()` - 计算高斯模糊卷积核
  - `Compute1DBlurLinearKernel()` - 计算利用线性纹理采样优化的模糊核
  - `CreateIntegralTable()` - 创建用于解析矩形模糊的积分表
  - `CreateCircleProfile()` / `CreateHalfPlaneProfile()` - 创建圆形模糊剖面图
  - `CreateRRectBlurMask()` - 生成圆角矩形的模糊掩码位图

## 依赖关系

### 上游依赖（本模块依赖的模块）

| 模块 | 用途 |
|------|------|
| `//:core` (include/core) | SkRefCnt、SkData、SkBlendMode、SkColorType、SkRect、SkString 等核心类型 |
| `//src/base` | SkMathPriv（数学工具）、SkRectMemcpy（矩形内存拷贝） |
| `//src/core:core_priv` | SkColorData、SkConvertPixels、SkMessageBus、SkBlurEngine 等内部实现 |
| `//src/utils:shader_utils` | SkShaderUtils（着色器格式化、打印工具） |
| `include/gpu/GpuTypes.h` | BackendApi、Mipmapped、CallbackResult、GpuStats 等公共 GPU 类型 |
| `include/gpu/ShaderErrorHandler.h` | ShaderErrorHandler 抽象接口 |
| `include/gpu/MutableTextureState.h` | MutableTextureState 公共接口 |
| `src/sksl/` | SkSL 编译器及代码生成（用于 SkSLToBackend） |

### 下游被依赖（依赖本模块的模块）

| 模块 | 依赖的组件 |
|------|-----------|
| `src/gpu/ganesh/` | Blend、BlendFormula、ResourceKey、BufferWriter、Swizzle、Rectanizer、Token 等全部共享类型 |
| `src/gpu/graphite/` | Blend、BlendFormula、ResourceKey、BufferWriter、Swizzle、Rectanizer、Token 等全部共享类型 |
| `src/gpu/vk/` | MutableTextureState、GpuTypesPriv |
| `src/gpu/mtl/` | MutableTextureState |
| `src/sksl/codegen/` | SkSLToBackend（着色器编译通用封装） |

### 外部依赖（第三方库）

本顶层目录不直接依赖任何第三方库。所有外部依赖（如 Vulkan SDK、Metal Framework、Dawn）均由子目录（`vk/`、`mtl/`、`ganesh/`、`graphite/`）各自管理。

## 设计模式分析

### 策略模式（Strategy Pattern）

`Rectanizer` 体系采用了经典的策略模式。`Rectanizer` 基类定义了 `addRect()` 和 `percentFull()` 的纯虚接口，`RectanizerPow2` 和 `RectanizerSkyline` 分别实现了不同的装箱策略。`Rectanizer::Factory()` 工厂方法返回当前首选的策略实现（通常是 Skyline）。

### 工厂模式（Factory Pattern）

多处使用了工厂模式：
- `Rectanizer::Factory()` - 根据需求创建合适的矩形装箱算法实例
- `RefCntedCallback::Make()` - 重载的静态工厂方法，根据不同的回调签名创建对应的实例
- `UniqueKey::GenerateDomain()` 和 `ScratchKey::GenerateResourceType()` - 生成全局唯一的域/类型标识

### Builder 模式（Builder Pattern）

`ResourceKey::Builder`、`ScratchKey::Builder`、`UniqueKey::Builder` 和 `FixedSizeKey::Builder` 使用了 Builder 模式来构造键对象。Builder 在其析构函数中自动调用 `finish()` 来计算哈希值，确保键的完整性。`KeyBuilder` 本身也是一个 Builder，提供位级别的键数据构建。

### RAII 模式（Resource Acquisition Is Initialization）

- `AutoCallback` - 析构时自动调用回调函数，确保资源释放通知不被遗漏
- `ResourceKey::Builder` - 析构时自动完成哈希计算
- `TClientMappedBufferManager` - 析构时清理所有未取消映射的缓冲区

### 模板方法模式（Template Method Pattern）

`gr_sp<T, Ref, Unref>` 通过 C++ 模板参数（auto 非类型模板参数）实现了引用计数策略的参数化。不同的 `Ref`/`Unref` 函数指针产生了 `gr_cb`（命令缓冲区引用）和 `gr_rp`（回收引用）两种具体行为，而核心逻辑保持不变。

### 消息总线模式（Message Bus Pattern）

`TClientMappedBufferManager` 使用 `SkMessageBus` 实现了跨线程的缓冲区完成通知。`UniqueKeyInvalidatedMessage` 和 `UniqueKeyInvalidatedMsg_Graphite` 通过消息总线通知缓存系统进行资源清理。

## 数据流

### 混合公式查询流程

```
SkBlendMode (来自 SkPaint)
    |
    v
GetBlendFormula(isOpaque, hasCoverage, mode)  [BlendFormula.cpp]
    |
    v
BlendFormula (4 字节位域)
    |
    +---> equation(), srcCoeff(), dstCoeff()  --> 硬件混合状态
    +---> primaryOutput(), secondaryOutput()  --> 着色器输出配置
    +---> canTweakAlphaForCoverage()          --> 覆盖率优化决策
```

### 着色器编译流程

```
SkSL 源代码 (std::string)
    |
    v
SkSLToBackend()  [SkSLToBackend.cpp]
    |
    +-- SkSL::Compiler::convertProgram()  --> SkSL::Program（中间表示）
    |
    +-- toBackend() 回调                   --> 后端特定代码（GLSL/MSL/SPIR-V/WGSL）
    |
    +-- ShaderErrorHandler                 --> 编译错误处理
    |
    v
SkSL::NativeShader (fText 或 fBinary)
```

### 纹理图集分配流程

```
字形渲染请求 (width, height)
    |
    v
Rectanizer::addRect()  或  addPaddedRect()
    |
    +-- RectanizerSkyline::rectangleFits()  --> 检查天际线间隙
    +-- RectanizerSkyline::addSkylineLevel() --> 更新天际线轮廓
    |
    v
SkIPoint16 loc (分配到的位置坐标)
    |
    v
TextureUploadWriter::write()  --> 将字形位图上传到图集纹理
```

### 异步读回流程

```
GPU 渲染完成
    |
    v
TClientMappedBufferManager::insert(buffer)  --> 注册映射缓冲区
    |
    v
TAsyncReadResult::addTransferResult()  --> 映射缓冲区数据并添加到结果
    |
    v
客户端线程消费数据 (data(), rowBytes())
    |
    v
BufferFinishedMessage 通过 SkMessageBus 发送
    |
    v
TClientMappedBufferManager::process()  --> 取消映射已完成的缓冲区
```

### 资源缓存键构建流程

```
资源参数 (纹理尺寸、格式、mipmap 等)
    |
    v
UniqueKey::Builder / ScratchKey::Builder
    |
    +-- builder[0] = param1
    +-- builder[1] = param2
    +-- ...
    |
    v
Builder::finish()  --> ResourceKeyHash() 计算哈希值
    |
    v
ResourceKey (hash + domain + data[])
    |
    v
缓存查找/插入
```

## 平台特定说明

### Android 平台

- `src/gpu/android/` 包含 `AHardwareBufferUtils.cpp`，用于与 Android 硬件缓冲区（AHardwareBuffer）的互操作
- `SkRenderEngineAbortf.h` 提供了 Android RenderEngine 环境下的特殊错误处理宏：
  - 在 RenderEngine 环境中使用 `SK_ABORT()` 强制中止
  - 在一般 Android 构建中降级为 `SkDebugf()` 仅打印信息
  - 在其他平台上为空操作

### GPU 驱动变通方案

`gpu_workaround_list.txt` 列出了已知的 GPU 驱动缺陷及其变通方案标识符，包括：

| 变通方案 | 描述 |
|---------|------|
| `add_and_true_to_loop_condition` | 为循环条件添加 `&& true` 以规避驱动编译器 bug |
| `disable_blend_equation_advanced` | 禁用高级混合方程（某些驱动不正确实现） |
| `disable_discard_framebuffer` | 禁用帧缓冲区丢弃操作 |
| `disable_texture_storage` | 禁用纹理存储 API |
| `disallow_large_instanced_draw` | 限制大规模实例化绘制 |
| `emulate_abs_int_function` | 模拟整数 abs() 函数 |
| `gl_clear_broken` | GL clear 操作存在问题 |
| `max_msaa_sample_count_4` | 限制 MSAA 最大采样数为 4 |
| `remove_pow_with_constant_exponent` | 移除常量指数的 pow() 调用 |
| `rewrite_do_while_loops` | 重写 do-while 循环 |
| `disable_dual_source_blending_support` | 禁用双源混合 |

### Metal 平台

`src/gpu/mtl/` 提供 Metal 特定的内存分配器实现（`MtlMemoryAllocatorImpl`）和工具函数。

### Vulkan 平台

`src/gpu/vk/` 提供 Vulkan 接口封装（`VulkanInterface`）、内存管理（`VulkanMemory`）、可变纹理状态（`VulkanMutableTextureState`）和首选特性查询（`VulkanPreferredFeatures`）。

## 相关文档与参考

### 内部相关目录

- `src/gpu/ganesh/` - Ganesh GPU 后端（传统后端，支持 OpenGL/Vulkan/Metal/Dawn）
- `src/gpu/graphite/` - Graphite GPU 后端（新一代后端，仅支持现代 API）
- `src/gpu/tessellate/` - 共享的曲面细分算法（Wang 公式、PatchWriter 等）
- `src/sksl/` - SkSL 着色器语言编译器
- `include/gpu/` - GPU 模块的公共头文件（GpuTypes.h、ShaderErrorHandler.h、MutableTextureState.h）

### 外部参考

- [Skia 官方文档](https://skia.org/) - Skia 项目主页
- [Skia GPU 架构概述](https://skia.org/docs/dev/design/) - 官方设计文档
- [Porter-Duff 混合模式](https://en.wikipedia.org/wiki/Alpha_compositing) - Alpha 合成与混合理论基础
- [矩形装箱问题](http://clb.demon.fi/projects/rectangle-bin-packing) - Jukka Jylanki 的矩形装箱算法参考
- [SkSL 着色器语言](https://skia.org/docs/user/sksl/) - Skia 的着色器语言文档
- [Texture Atlas 技术](https://en.wikipedia.org/wiki/Texture_atlas) - 纹理图集技术背景

### 构建配置

该模块的 Bazel 构建目标定义在 `src/gpu/BUILD.bazel` 中：
```python
skia_cc_library(
    name = "gpu",
    srcs = [":shared_srcs", "//src/gpu/tessellate:tessellate_srcs"],
    hdrs = [":shared_hdrs", "//include/gpu:shared_gpu_hdrs",
            "//src/gpu/tessellate:tessellate_hdrs",
            "//src/sksl/codegen:codegen_shared_exported"],
    visibility = ["//src/gpu:__subpackages__", "//src/sksl/codegen:__pkg__"],
    deps = ["//:core", "//src/base", "//src/core:core_priv", "//src/utils:shader_utils"],
)
```
