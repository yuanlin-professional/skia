# include/private/chromium - Chromium 专用私有头文件

## 概述

`include/private/chromium` 目录包含专为 Chromium 浏览器设计的 Skia 私有接口。这些头文件暴露了 Skia 的内部功能，仅供 Chromium 项目使用，不属于 Skia 的公共 API。Chromium 需要直接引用这些头文件以实现其渲染架构中的特定需求。

该目录的核心功能围绕以下几个方面展开：延迟显示列表（Deferred Display List, DDL）机制、远程字形缓存（Remote Glyph Cache）系统、Promise Image 纹理管理、Vulkan 二级命令缓冲区绘制以及预乘颜色工具。DDL 系统允许 Chromium 在不同线程上预录制 GPU 操作，然后在 GPU 线程上回放，这是 Chromium 合成器（Compositor）架构的关键组成部分。

远程字形缓存系统（`SkStrikeServer`/`SkStrikeClient`）用于支持 Chromium 的进程间字形渲染流水线。渲染进程通过分析画布操作收集字形信息，然后将序列化的字形数据发送给 GPU 进程进行实际渲染。这种设计使得 Chromium 能够在安全沙箱内进行文本布局，同时将 GPU 操作隔离在专用进程中。

Slug（文本橡皮图章）机制是 Chromium 文本渲染管线的另一核心组件，它将 `SkTextBlob` 在特定位置和画笔设置下"固化"为可序列化和重放的对象。

## 目录结构

```
include/private/chromium/
├── GrDeferredDisplayList.h          # 延迟显示列表 - 预处理的 GPU 操作集合
├── GrDeferredDisplayListRecorder.h  # DDL 录制器 - 录制 GPU 操作到 DDL
├── GrPromiseImageTexture.h          # Promise Image 纹理 - 延迟纹理绑定
├── GrSurfaceCharacterization.h      # 渲染表面特征描述
├── GrVkSecondaryCBDrawContext.h     # Vulkan 二级命令缓冲区绘制上下文
├── SkChromeRemoteGlyphCache.h       # 远程字形缓存（服务端/客户端）
├── SkCodecsICCProfileChromium.h     # Chromium ICC 配置文件解析接口
├── SkDiscardableMemory.h            # 可丢弃内存接口
├── SkImageChromium.h                # Chromium 专用图像创建函数
├── SkPMColor.h                      # 预乘颜色工具函数
├── Slug.h                           # 文本 Slug（文本橡皮图章）
└── BUILD.bazel                      # Bazel 构建配置
```

## 关键类与函数

### 延迟显示列表 (DDL)
- **`GrDeferredDisplayList`**: 存储预处理的 GPU 操作。通过 `ProgramIterator` 可以提前编译着色器程序，减少渲染时的延迟。继承自 `SkNVRefCnt`。
- **`GrDeferredDisplayListRecorder`**: DDL 的录制器。使用流程为：创建 `GrSurfaceCharacterization` -> 实例化录制器 -> 获取画布 `getCanvas()` -> 绘制操作 -> 调用 `detach()` 获取 DDL。线程安全，可并行录制。
- **`GrSurfaceCharacterization`**: 描述目标渲染表面的所有特征，包括尺寸、颜色类型、采样数、Mipmap 状态、是否可作为纹理、是否使用 GL FBO0、Vulkan 输入附件支持等。

### 远程字形缓存
- **`SkStrikeServer`**: 字形缓存服务端，通过 `makeAnalysisCanvas()` 创建分析画布收集字形信息，然后通过 `writeStrikeData()` 序列化数据。内部使用 `DiscardableHandleManager` 管理远程端的缓存生命周期。支持 DFT（Distance Field Text）渲染模式和透视 DFT。
- **`SkStrikeServer::DiscardableHandleManager`**: 服务端需实现的接口，提供 `createHandle()`（创建锁定句柄）、`lockHandle()`（锁定句柄防止丢弃）和 `isHandleDeleted()`（检查句柄是否已被远程端删除）方法。
- **`SkStrikeClient`**: 字形缓存客户端，反序列化服务端发送的字形数据，使用 `DiscardableHandleManager` 管理本地缓存的锁定和丢弃。
- **`SkStrikeClient::DiscardableHandleManager`**: 客户端需实现的接口，提供 `deleteHandle()`（删除句柄）和 `readStrikeData()`（读取字形数据）方法。

### Promise Image 与纹理
- **`GrPromiseImageTexture`**: 封装 `GrBackendTexture`，用于 Promise Image 的纹理履行（fulfillment）。在 `PromiseImageTextureFulfillProc` 回调中返回。
- **`SkImages::PromiseImageTextureOfFulfill()`**（在 `SkImageChromium.h` 中）: 创建由延迟纹理支持的 GPU 图像，允许在非 GPU 线程上创建图像。

### Vulkan 集成
- **`GrVkSecondaryCBDrawContext`**: 允许 Chromium 导入外部 Vulkan 二级命令缓冲区并向其中绘制。该类继承自 `SkRefCnt`，通过静态工厂方法 `Make()` 创建实例。
  - **使用限制**: 不支持需要 dst 拷贝的混合操作、文本绘制（可能需要中间纹理上传）、读写像素操作和模板操作。如需这些功能，应先绘制到离屏 Surface 再绘制到此上下文。
  - **生命周期管理**: 使用后必须调用 `flush()` 将绘制命令写入二级命令缓冲区，然后在 GPU 完成所有工作后调用 `releaseResources()` 清理 Skia 内部资源。
  - **信号量支持**: 通过 `wait()` 方法可添加 GPU 信号量等待，确保绘制操作在依赖的 GPU 工作完成后执行。

### 文本渲染
- **`sktext::gpu::Slug`**: 将 `SkTextBlob` 在特定原点和画笔下"固化"的对象，支持序列化/反序列化。可以理解为文本的"橡皮图章"，继承自 `SkRefCnt`。
  - `ConvertBlob()`: 从 SkCanvas、SkTextBlob、原点和画笔创建 Slug。如果文本优化后不需要绘制则返回 nullptr。
  - `serialize()`/`Deserialize()`: 序列化和反序列化支持，可选地使用 `SkStrikeClient` 进行字体 ID 转换。
  - `draw()`: 在画布上绘制 Slug，遵循画布的变换和剪裁设置。
  - `AddDeserialProcs()`: 将 Slug 反序列化处理器注册到 `SkDeserialProcs`，使 SkPicture 可以包含 Slug 数据。
  - `sourceBounds()`/`sourceBoundsWithOrigin()`: 获取 Slug 的源边界矩形。

### 颜色与编解码器
- **`SkPMColorSetARGB()`/`SkPMColorGetA()`/`SkPMColorGetR()`/`SkPMColorGetG()`/`SkPMColorGetB()`**: 预乘颜色的组件设置和获取工具函数，跨平台处理不同的颜色通道排列顺序。
- **`SkCodecs::ICCProfileChromium`**: 允许 Chromium 中不使用 SkCodec 的代码解析 ICC 配置文件。
  - `ForceSkcms()`: 全局设置，强制使用 skcms 解析器而非默认的 moxcms。用作 Chromium 的回退开关，需在进程启动早期调用。
  - `Make()`: 从 ICC 配置文件数据创建解析实例。
  - `GetProfile()`: 获取已解析的 `skcms_ICCProfile` 结构。
- **`SkDiscardableMemory`**: 可由操作系统丢弃的内存接口，嵌入者需实现 `lock()`/`unlock()`/`data()` 方法。还提供 `Factory` 子类用于创建可丢弃内存实例。

## 依赖关系

- **上游依赖**: `include/core/`（SkRefCnt、SkCanvas、SkImage 等）、`include/gpu/ganesh/`（GrBackendSurface、GrTypes 等）、`include/private/base/`（SkTArray、SkAPI 等）
- **下游消费者**: Chromium 的 `cc/`（合成器层）、`gpu/`（GPU 进程）和 `content/`（渲染进程）模块
- **内部依赖**: `src/gpu/ganesh/`（DDL 和字形缓存实现）、`src/text/gpu/`（Slug 实现）

## 相关文档与参考

- [Chromium 合成器架构](https://chromium.googlesource.com/chromium/src/+/HEAD/docs/how_cc_works.md) - DDL 在合成器中的使用
- [Skia DDL 设计文档](https://skia.org/docs/user/api/skcanvas_overview/) - 延迟显示列表概述
- [Chromium GPU 进程](https://chromium.googlesource.com/chromium/src/+/HEAD/docs/gpu/) - GPU 架构文档
- `include/gpu/ganesh/` - Ganesh GPU 后端公共 API
- `include/private/gpu/ganesh/` - Ganesh GPU 私有类型
- `include/private/base/` - 基础设施头文件
- `src/text/gpu/Slug.cpp` - Slug 的具体实现

## 使用注意事项

### DDL 工作流程
典型的 DDL 使用流程如下：
```
1. 获取目标 SkSurface 的 GrSurfaceCharacterization
2. 在工作线程上创建 GrDeferredDisplayListRecorder
3. 获取 Canvas 并执行绘制操作
4. 调用 detach() 获取 GrDeferredDisplayList
5. 在 GPU 线程上调用 skgpu::ganesh::DrawDDL() 回放
```

### 远程字形缓存工作流程
```
渲染进程（服务端）:
1. 创建 SkStrikeServer
2. 使用 makeAnalysisCanvas() 获取分析画布
3. 在分析画布上执行包含文本的绘制操作
4. 调用 writeStrikeData() 序列化字形数据
5. 通过 IPC 发送序列化数据到 GPU 进程

GPU 进程（客户端）:
1. 创建 SkStrikeClient
2. 接收序列化数据并调用 readStrikeData()
3. 反序列化 Slug 并在 GPU 画布上绘制
```

### 版本兼容性
这些接口专门为 Chromium 设计，Skia 团队会与 Chromium 团队协调接口变更。但由于是私有 API，不提供正式的弃用周期。其他项目不应使用这些接口。
