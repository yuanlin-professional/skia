# src/gpu/ganesh/gl - Skia Ganesh OpenGL 后端实现

## 概述

`src/gpu/ganesh/gl` 目录是 Skia 图形库中 Ganesh GPU 渲染引擎的 OpenGL 后端核心实现。Ganesh 是 Skia 的 GPU 加速绘制引擎，而本目录负责将 Ganesh 的抽象 GPU 操作转化为实际的 OpenGL/OpenGL ES/WebGL API 调用。它是连接 Skia 高层绘制命令与底层图形硬件之间的关键桥梁。

该目录实现了完整的 OpenGL 后端生命周期管理，包括 GPU 设备抽象（`GrGLGpu`）、能力查询与限制检测（`GrGLCaps`）、上下文信息封装（`GrGLContext`）、资源管理（纹理、渲染目标、缓冲区、附件等）、着色器程序编译与缓存、渲染通道执行，以及跨平台 GL 函数指针加载机制。所有这些组件协同工作，使得 Skia 能够在 Desktop OpenGL、OpenGL ES 和 WebGL 等多种 GL 标准下高效运行。

本目录的设计遵循了"接口隔离"与"平台抽象"的核心原则。通过 `GrGLInterface` 结构体，所有 GL 函数调用都通过函数指针进行，而非直接链接 GL 库。这使得相同的渲染代码可以在不同平台（macOS、Windows、Linux/X11、Android、iOS、WebGL）上透明运行，只需在初始化阶段提供正确的函数指针集合即可。

特别值得注意的是，`GrGLCaps` 中维护了大量针对特定 GPU 厂商和驱动版本的兼容性修正（workaround），这些是多年工程实践中积累的宝贵经验，确保了 Skia 在数千种不同硬件/驱动组合上的稳定运行。该文件超过 260KB，是整个 Skia 代码库中最大的单个源文件之一。

## 架构图

```
+------------------------------------------------------------------+
|                    Skia 上层绘制 API (SkCanvas)                    |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                  Ganesh GPU 引擎 (GrDirectContext)                 |
|                                                                    |
|   GrOpsTask -> GrOpsRenderPass -> GrProgramInfo -> GrPipeline     |
+------------------------------------------------------------------+
                              |
                              v
+==================================================================+
|              src/gpu/ganesh/gl (本目录 - OpenGL 后端)               |
|                                                                    |
|  +--------------------+    +-------------------+                   |
|  |    GrGLGpu         |<-->|   GrGLContext      |                  |
|  | (GPU设备核心抽象)   |    | (GL上下文信息)     |                  |
|  +--------------------+    +-------------------+                   |
|          |                        |                                |
|          v                        v                                |
|  +--------------------+    +-------------------+                   |
|  | GrGLOpsRenderPass  |    |   GrGLCaps        |                  |
|  | (渲染通道执行)      |    | (能力查询/限制)   |                  |
|  +--------------------+    +-------------------+                   |
|          |                                                         |
|          v                                                         |
|  +--------------------+  +---------------+  +------------------+   |
|  | GrGLProgram        |  | GrGLTexture   |  | GrGLRenderTarget |   |
|  | (着色器程序)        |  | (纹理资源)    |  | (渲染目标)       |   |
|  +--------------------+  +---------------+  +------------------+   |
|          |                      |                    |             |
|  +--------------------+  +---------------+  +------------------+   |
|  | GrGLProgramData    |  | GrGLBuffer    |  | GrGLAttachment   |   |
|  | Manager(Uniform管理)|  | (缓冲区)     |  | (模板/MSAA附件)  |   |
|  +--------------------+  +---------------+  +------------------+   |
|          |                                                         |
|          v                                                         |
|  +--------------------+    +--------------------------+            |
|  | builders/          |    | GrGLInterface            |            |
|  | (程序构建器)        |    | (GL函数指针集合)         |            |
|  +--------------------+    +--------------------------+            |
|                                      |                             |
+======================================|=============================+
                                       |
            +---------+---------+------+------+---------+
            |         |         |      |      |         |
            v         v         v      v      v         v
        +------+ +------+ +------+ +-----+ +-----+ +------+
        | mac/ | | win/ | | egl/ | |glx/ | |iOS/ | |webgl/|
        +------+ +------+ +------+ +-----+ +-----+ +------+
            |         |         |      |      |         |
            v         v         v      v      v         v
+------------------------------------------------------------------+
|              底层 OpenGL / OpenGL ES / WebGL 驱动                  |
+------------------------------------------------------------------+
```

## 文件分类索引

### 1. 核心 GL 实现 — GPU/Context/Caps

| 文件 | 说明 |
|------|------|
| GrGLGpu.h / GrGLGpu.cpp | GL GPU 设备抽象核心类（约 190KB 实现） |
| GrGLCaps.h / GrGLCaps.cpp | GL 能力查询与驱动兼容性（约 260KB 实现） |
| GrGLContext.h / GrGLContext.cpp | GL 上下文信息封装 |
| GrGLDirectContext.cpp | GL DirectContext 创建 |
| GrGLDefines.h | GL 常量定义（GR_GL_ 前缀） |

### 2. 接口组装 — GL Function Pointer Loading

| 文件 | 说明 |
|------|------|
| GrGLAssembleInterface.cpp | 通用接口组装 |
| GrGLAssembleGLInterfaceAutogen.cpp | Desktop GL 函数自动装配 |
| GrGLAssembleGLESInterfaceAutogen.cpp | GL ES 函数自动装配 |
| GrGLAssembleWebGLInterfaceAutogen.cpp | WebGL 函数自动装配 |
| GrGLAssembleHelpers.cpp | 装配辅助函数 |
| GrGLInterfaceAutogen.cpp | 接口验证自动生成代码 |
| GrGLCoreFunctions.h | 核心 GL 函数声明宏 |
| GrGLExtensions.cpp | GL 扩展管理 |
| GrGLMakeNativeInterface_none.cpp | 无原生接口的空实现 |

### 3. 能力/工具 — Caps & Utilities

| 文件 | 说明 |
|------|------|
| GrGLUtil.h / GrGLUtil.cpp | GL 版本/厂商/格式工具函数 |
| GrGLGLSL.h / GrGLGLSL.cpp | GLSL 版本检测 |
| GrGLTypesPriv.h / GrGLTypesPriv.cpp | GL 类型私有定义 |

### 4. 资源/纹理 — Texture/Buffer/Attachment

| 文件 | 说明 |
|------|------|
| GrGLTexture.h / GrGLTexture.cpp | GL 纹理资源封装 |
| GrGLRenderTarget.h / GrGLRenderTarget.cpp | GL 渲染目标（FBO 管理） |
| GrGLTextureRenderTarget.h / GrGLTextureRenderTarget.cpp | 同时作为纹理和渲染目标的资源 |
| GrGLBuffer.h / GrGLBuffer.cpp | GL 缓冲区对象封装 |
| GrGLAttachment.h / GrGLAttachment.cpp | 模板缓冲和 MSAA 渲染缓冲附件 |
| GrGLVertexArray.h / GrGLVertexArray.cpp | 顶点数组对象（VAO）管理 |

### 5. 程序/渲染 — Program/RenderPass

| 文件 | 说明 |
|------|------|
| GrGLProgram.h / GrGLProgram.cpp | GL 着色器程序管理 |
| GrGLGpuProgramCache.cpp | GPU 程序 LRU 缓存 |
| GrGLOpsRenderPass.h / GrGLOpsRenderPass.cpp | GL 渲染通道（直接传递给 GPU） |
| GrGLFinishCallbacks.h / GrGLFinishCallbacks.cpp | GPU 完成回调机制 |
| GrGLSemaphore.h / GrGLSemaphore.cpp | GL 同步信号量（glFenceSync） |

### 6. Uniform/Varying — 着色器变量管理

| 文件 | 说明 |
|------|------|
| GrGLProgramDataManager.h / GrGLProgramDataManager.cpp | Uniform 变量数据管理 |
| GrGLUniformHandler.h / GrGLUniformHandler.cpp | Uniform 声明与定位 |
| GrGLVaryingHandler.h | Varying 变量处理 |

### 7. 后端表面/平台互操作 — Backend Surface

| 文件 | 说明 |
|------|------|
| GrGLBackendSurface.cpp / GrGLBackendSurfacePriv.h | 后端表面 GL 特化实现 |
| AHardwareBufferGL.cpp | Android HardwareBuffer GL 互操作 |

## 关键类与函数

### GrGLGpu (GrGLGpu.h / GrGLGpu.cpp)

`GrGLGpu` 是 OpenGL 后端的核心类，继承自 `GrGpu`。它是所有 GL 操作的入口点，管理整个 GL 状态机。

**关键职责：**
- **资源创建：** `onCreateTexture()`, `onCreateBuffer()`, `onCreateBackendTexture()` 等方法创建各种 GPU 资源
- **状态管理：** 通过 `fHW*` 前缀的成员变量跟踪 GL 硬件状态，避免冗余的 GL 调用
- **绘制执行：** `flushGLState()` 将 Skia 的渲染状态转换为 GL 状态，`prepareToDraw()` 准备绘制命令
- **表面操作：** `onReadPixels()`, `onWritePixels()`, `onCopySurface()` 实现像素读写和表面拷贝
- **同步机制：** `insertSync()`, `testSync()`, `deleteSync()` 管理 GL fence 同步
- **程序缓存：** 内部 `ProgramCache` 类使用 LRU 策略缓存编译好的着色器程序

**关键静态方法：**
```cpp
static std::unique_ptr<GrGpu> Make(sk_sp<const GrGLInterface>,
                                    const GrContextOptions&,
                                    GrDirectContext*);
```

**状态跟踪机制：**
`GrGLGpu` 维护了大量硬件状态缓存（`fHW` 前缀成员），包括：
- `fHWActiveTextureUnitIdx` -- 当前活动纹理单元
- `fHWProgramID` / `fHWProgram` -- 当前绑定的着色器程序
- `fHWScissorSettings` -- 裁剪矩形状态
- `fHWBlendState` -- 混合状态
- `fHWStencilSettings` -- 模板测试状态
- `fHWBufferState[]` -- 各类缓冲区绑定状态
- `fHWTextureUnitBindings` -- 纹理单元绑定状态
- `fHWBoundRenderTargetUniqueID` -- 当前绑定的渲染目标

### GrGLCaps (GrGLCaps.h / GrGLCaps.cpp)

`GrGLCaps` 继承自 `GrCaps`，存储当前 GL 上下文的能力信息和驱动特定的行为修正。

**关键枚举类型：**
- `MSFBOType` -- MSAA FBO 支持类型（标准/Apple/IMG/EXT）
- `BlitFramebufferFlags` -- glBlitFramebuffer 的限制标志
- `MapBufferType` -- 缓冲区映射支持类型
- `TransferBufferType` -- 像素传输缓冲支持类型
- `FenceType` -- GL fence 实现类型
- `MultiDrawType` -- 多重绘制支持类型
- `TimerQueryType` -- GPU计时查询支持类型

**关键方法：**
```cpp
bool isFormatTexturable(GrGLFormat) const;
bool isFormatRenderable(GrGLFormat format, int sampleCount) const;
int getRenderTargetSampleCount(int requestedCount, GrGLFormat) const;
GrGLenum getTexImageOrStorageInternalFormat(GrGLFormat format) const;
```

**驱动兼容性修正：** `GrGLCaps` 维护了数十个布尔标志用于处理特定GPU/驱动的问题：
- `fClearToBoundaryValuesIsBroken` -- 某些Intel Mac GPU的clear问题
- `fDrawArraysBaseVertexIsBroken` -- Adreno GPU的baseVertex问题
- `fNeverDisableColorWrites` -- PowerVR GPU的颜色写入问题
- `fMustResetBlendFuncBetweenDualSourceAndDisable` -- 双源混合重置问题
- `fFlushBeforeWritePixels` -- 特定驱动需要在写像素前flush

### GrGLContext / GrGLContextInfo (GrGLContext.h)

`GrGLContextInfo` 封装了 OpenGL 上下文的元信息，包括 GL 标准类型、版本、GLSL 版本、GPU 厂商、渲染器和驱动信息。`GrGLContext` 扩展了 `GrGLContextInfo`，额外提供对 `GrGLInterface` 的访问。

**关键查询方法：**
```cpp
GrGLStandard standard() const;    // GL / GLES / WebGL
GrGLVersion version() const;       // GL版本号
GrGLVendor vendor() const;         // GPU厂商 (考虑ANGLE透传)
GrGLRenderer renderer() const;     // GPU渲染器
GrGLDriver driver() const;         // 驱动类型
GrGLANGLEBackend angleBackend() const;  // ANGLE后端类型
```

### GrGLInterface (include/gpu/ganesh/gl/GrGLInterface.h)

`GrGLInterface` 是一个包含所有 GL 函数指针的结构体。它通过 `GrGLFunction<>` 模板存储各个 GL 函数的指针，支持超过 150 个 GL 函数调用。

**核心设计：** 不直接链接 GL 库，而是在运行时通过平台特定的函数指针加载机制（`dlsym`、`wglGetProcAddress`、`eglGetProcAddress` 等）填充函数指针。

### GrGLTexture (GrGLTexture.h)

GL 纹理资源的封装，继承自 `GrTexture`。

**内部描述符 `Desc`：**
```cpp
struct Desc {
    SkISize fSize;
    GrGLenum fTarget;      // GL_TEXTURE_2D, GL_TEXTURE_RECTANGLE 等
    GrGLuint fID;          // GL纹理对象ID
    GrGLFormat fFormat;    // 内部格式
    GrBackendObjectOwnership fOwnership;
};
```

### GrGLRenderTarget (GrGLRenderTarget.h)

GL 渲染目标（FBO）的封装，继承自 `GrRenderTarget`。支持单采样和多采样 FBO 的管理和解析。

**关键成员：**
- `fMultisampleFBOID` -- 多采样FBO ID
- `fSingleSampleFBOID` -- 单采样FBO ID
- `fMSColorRenderbufferID` -- MSAA颜色渲染缓冲ID
- `ResolveDirection` -- 解析方向（单采样到MSAA或反向）

### GrGLProgram (GrGLProgram.h)

管理一个编译链接好的 GL 着色器程序，包含顶点属性布局和 Uniform 变量管理。

**关键方法：**
```cpp
void updateUniforms(const GrRenderTarget*, const GrProgramInfo&);
void bindTextures(const GrGeometryProcessor&,
                  const GrSurfaceProxy* const geomProcTextures[],
                  const GrPipeline&);
```

### GrGLOpsRenderPass (GrGLOpsRenderPass.h)

GL 渲染通道的实现，继承自 `GrOpsRenderPass`。**注意：** 该类不做任何缓冲，所有绘制命令直接传递给 `GrGLGpu` 执行。这与 Vulkan 等后端的命令缓冲模式不同。

### GrGLBuffer (GrGLBuffer.h)

GL 缓冲区对象的封装，支持顶点缓冲、索引缓冲、Uniform缓冲和传输缓冲等类型。

### GrGLAttachment (GrGLAttachment.h)

GL 渲染缓冲附件（Renderbuffer），用于模板缓冲和 MSAA 颜色附件。

**工厂方法：**
```cpp
static sk_sp<GrGLAttachment> MakeStencil(...);  // 创建模板附件
static sk_sp<GrGLAttachment> MakeMSAA(...);      // 创建MSAA颜色附件
static sk_sp<GrGLAttachment> MakeWrappedRenderBuffer(...);  // 包装外部RBO
```

### GrGLVertexArray / GrGLAttribArrayState (GrGLVertexArray.h)

管理 OpenGL 顶点数组对象（VAO）和顶点属性数组状态。`GrGLAttribArrayState` 跟踪每个属性的绑定状态以避免冗余调用。

## 依赖关系

### 上游依赖 (本目录被谁使用)

| 模块 | 说明 |
|------|------|
| `src/gpu/ganesh/GrDirectContext.cpp` | 通过 `GrGLGpu::Make()` 创建GL GPU实例 |
| `src/gpu/ganesh/GrGpu.h` | `GrGLGpu` 的基类 |
| `src/gpu/ganesh/GrCaps.h` | `GrGLCaps` 的基类 |
| `src/gpu/ganesh/GrOpsRenderPass.h` | `GrGLOpsRenderPass` 的基类 |
| `src/gpu/ganesh/GrTexture.h` | `GrGLTexture` 的基类 |
| `src/gpu/ganesh/GrRenderTarget.h` | `GrGLRenderTarget` 的基类 |
| `include/gpu/ganesh/gl/` | 公共API头文件目录 |

### 下游依赖 (本目录使用了谁)

| 模块 | 说明 |
|------|------|
| `include/gpu/ganesh/gl/GrGLInterface.h` | GL函数指针接口定义 |
| `include/gpu/ganesh/gl/GrGLTypes.h` | GL类型定义 |
| `include/gpu/ganesh/gl/GrGLFunctions.h` | GL函数类型定义 |
| `include/gpu/ganesh/gl/GrGLExtensions.h` | GL扩展管理 |
| `src/gpu/ganesh/glsl/` | GLSL着色器语言处理 |
| `src/sksl/` | SkSL着色器编译器 |
| `src/gpu/Blend.h` | GPU混合操作 |
| `src/gpu/Swizzle.h` | 颜色通道重排 |

### 外部依赖

| 依赖 | 说明 |
|------|------|
| OpenGL / OpenGL ES / WebGL | 底层图形API（通过函数指针间接调用） |
| EGL | 嵌入式平台GL上下文管理 |
| GLX | X Window系统GL上下文管理 |
| WGL | Windows平台GL上下文管理 |
| CGL / EAGL | Apple平台GL上下文管理 |
| libepoxy | GL函数加载封装库 |

## 设计模式分析

### 1. 抽象工厂模式 (Abstract Factory)

`GrGLGpu::Make()` 作为工厂方法，根据 `GrGLInterface` 和 `GrContextOptions` 创建完整配置的 GPU 实例。各平台子目录中的 `GrGLInterfaces::MakeXxx()` 函数族则构成了一组抽象工厂，负责为不同平台组装正确的 GL 函数指针集合。

### 2. 策略模式 (Strategy)

`GrGLCaps` 中的多种枚举（如 `MSFBOType`、`MapBufferType`、`TransferBufferType`）实际上选择了不同的 GL 操作策略。例如，根据 `MSFBOType` 的不同值，MSAA 解析的实现路径会完全不同：
- `kStandard_MSFBOType` -- 使用标准 `glBlitFramebuffer`
- `kES_Apple_MSFBOType` -- 使用 Apple 专有的 `glResolveMultisampleFramebufferAPPLE`
- `kES_IMG_MsToTexture_MSFBOType` -- 使用自动解析的多采样纹理

### 3. 状态缓存模式 (State Caching / Dirty Flag)

`GrGLGpu` 中的 `fHW*` 成员变量实现了完整的 GL 状态缓存。在设置任何 GL 状态之前，都会先检查缓存的值是否与目标值一致。这避免了大量冗余的 GL 状态切换调用，是重要的性能优化手段。`TriState` 枚举（`kNo/kYes/kUnknown`）用于跟踪布尔类型的 GL 状态。

### 4. 命令传递模式 (Pass-through)

`GrGLOpsRenderPass` 采用直接传递模式，不像 Vulkan 后端那样先缓冲命令再批量提交。所有绘制命令立即通过 `GrGLGpu` 发送给 GL 驱动。这简化了实现，但也意味着无法利用命令缓冲进行优化。

### 5. 适配器模式 (Adapter)

`GrGLInterface` 本身就是一个适配器，它将各平台原生的 GL 函数调用方式统一为一致的函数指针接口。各平台子目录中的 `MakeNativeInterface` 函数负责填充这些函数指针。

### 6. LRU 缓存模式

`GrGLGpu::ProgramCache` 使用 `SkLRUCache` 实现着色器程序的 LRU 缓存策略，避免反复编译相同的着色器。程序通过 `GrProgramDesc` 作为键进行索引。

## 数据流

### 绘制命令执行流程

```
1. SkCanvas::drawRect() / drawPath() / etc.
   |
2. GrOpsTask 收集并排序绘制操作 (Ops)
   |
3. GrOpsTask::execute()
   |
4. GrGLOpsRenderPass::onBegin()
   |-- GrGLGpu::beginCommandBuffer() 绑定FBO并设置Load操作
   |
5. GrGLOpsRenderPass::onBindPipeline()
   |-- GrGLGpu::flushGLState()
   |   |-- 查找/编译着色器程序 (ProgramCache)
   |   |-- 绑定程序 (glUseProgram)
   |   |-- 刷新混合状态 (flushBlendAndColorWrite)
   |   |-- 刷新模板状态 (flushStencil)
   |   |-- 刷新裁剪状态 (flushScissor)
   |   |-- 刷新视口 (flushViewport)
   |
6. GrGLOpsRenderPass::onBindTextures()
   |-- GrGLGpu::bindTexture() 绑定纹理到采样单元
   |
7. GrGLOpsRenderPass::onBindBuffers()
   |-- GrGLGpu::bindBuffer() 绑定顶点/索引缓冲
   |-- 设置顶点属性 (GrGLAttribArrayState::set)
   |
8. GrGLOpsRenderPass::onDraw() / onDrawIndexed() / onDrawInstanced()
   |-- glDrawArrays() / glDrawElements() / glDrawArraysInstanced()
   |
9. GrGLOpsRenderPass::onEnd()
   |-- GrGLGpu::endCommandBuffer() 执行Store操作和MSAA解析
```

### 纹理上传流程

```
1. GrGLGpu::onWritePixels()
   |
2. 解绑传输缓冲 (unbindXferBuffer)
   |
3. 绑定目标纹理到 "scratch" 纹理单元
   |
4. uploadColorTypeTexData()
   |-- 确定外部格式和类型 (getTexSubImageExternalFormatAndType)
   |-- uploadTexData()
   |   |-- glPixelStorei() 设置像素存储参数
   |   |-- glTexSubImage2D() 上传纹理数据
   |   |-- 或 glTexImage2D() (首次完整上传)
   |
5. 如果需要Mipmap: onRegenerateMipMapLevels()
```

### GL 接口初始化流程

```
1. 平台特定代码调用 GrGLInterfaces::MakeXxx()
   |-- 例如 MakeMac() / MakeWin() / MakeEGL() / MakeGLX() / MakeWebGL()
   |
2. 获取 GL 函数加载器 (dlsym / wglGetProcAddress / eglGetProcAddress)
   |
3. GrGLMakeAssembledGLInterface() 或 GrGLMakeAssembledGLESInterface()
   |-- 根据GL标准类型组装函数指针
   |-- 自动生成的代码填充 GrGLInterface::Functions 结构体
   |
4. GrGLInterface::validate() 验证必要的函数指针已填充
   |
5. GrGLContext::Make() 创建上下文
   |-- 检测驱动信息 (GrGLDriverInfo)
   |-- 检测GLSL版本 (GrGLGetGLSLGeneration)
   |-- 创建 GrGLCaps 并初始化能力查询
   |
6. GrGLGpu::Make() 创建GPU实例
```

## 平台特定说明

### macOS (mac/)

通过 `dlopen` 加载 `/System/Library/Frameworks/OpenGL.framework/.../libGL.dylib`，使用 `dlsym` 获取函数指针。组装的是 Desktop GL（非GLES）接口。入口函数为 `GrGLInterfaces::MakeMac()`。

### Windows (win/)

通过 `LoadLibraryExA("opengl32.dll")` 加载 GL 库，结合 `GetProcAddress` 和 `wglGetProcAddress` 获取函数指针。支持自动检测 GL/GLES 标准。注意 ARM64 Windows 不支持 OpenGL。入口函数为 `GrGLInterfaces::MakeWin()`。

### iOS (iOS/)

类似macOS使用 `dlopen/dlsym`，但组装的是 GL ES 接口（`GrGLMakeAssembledGLESInterface`）。入口函数为 `GrGLInterfaces::MakeIOS()`。

### EGL (egl/)

适用于 Android 和部分 Linux 环境。使用 `eglGetProcAddress` 获取扩展函数，核心函数通过 `GR_GL_CORE_FUNCTIONS_EACH` 宏直接引用编译时链接的符号。入口函数为 `GrGLInterfaces::MakeEGL()`。

### GLX (glx/)

适用于 Linux/X11 环境。使用 `glXGetProcAddress` 获取函数指针。需要有活跃的 GLX 上下文。特别处理了 EGL 函数名的过滤（避免 GLX 返回无效指针）。入口函数为 `GrGLInterfaces::MakeGLX()`。

### WebGL (webgl/)

适用于 Emscripten/WebAssembly 环境。不使用 `GetProcAddress` 类机制，而是直接使用 Emscripten 提供的头文件中的函数指针，以减少代码大小。组装的是 WebGL 专用接口。入口函数为 `GrGLInterfaces::MakeWebGL()`。

### Android (android/)

直接包含 EGL 目录中的实现文件，复用 EGL 的函数加载逻辑。

### Epoxy (epoxy/)

使用 `libepoxy` 库封装的 EGL 接口。通过 `epoxy_eglGetProcAddress` 获取扩展函数，核心函数通过 `epoxy_` 前缀的包装函数获取。入口函数为 `GrGLInterfaces::MakeEpoxyEGL()`。

## 相关文档与参考

### Skia 内部相关目录

- `include/gpu/ganesh/gl/` -- OpenGL 后端的公共API头文件（`GrGLInterface.h`、`GrGLTypes.h` 等）
- `src/gpu/ganesh/glsl/` -- GLSL 着色器语言处理（`GrGLSLProgramBuilder`、`GrGLSLFragmentShaderBuilder` 等）
- `src/gpu/ganesh/` -- Ganesh GPU 引擎核心（`GrGpu`、`GrCaps`、`GrTexture` 等基类）
- `src/sksl/` -- SkSL 着色器编译器，将 Skia 的着色器语言编译为 GLSL
- `src/gpu/ganesh/vk/` -- Vulkan 后端，与 GL 后端平行的实现
- `src/gpu/ganesh/d3d/` -- Direct3D 后端
- `src/gpu/ganesh/mtl/` -- Metal 后端

### 外部参考

- OpenGL 规范: https://www.khronos.org/opengl/
- OpenGL ES 规范: https://www.khronos.org/opengles/
- WebGL 规范: https://www.khronos.org/webgl/
- GLSL 规范: https://www.khronos.org/opengl/wiki/OpenGL_Shading_Language
- EGL 规范: https://www.khronos.org/egl/
- ANGLE 项目: https://chromium.googlesource.com/angle/angle
- Skia 官方文档: https://skia.org/docs/
- libepoxy: https://github.com/anholt/libepoxy

### 关键设计决策说明

1. **函数指针而非直接链接：** Skia 不直接链接 OpenGL 库，而是通过 `GrGLInterface` 中的函数指针间接调用。这使得同一份代码可以在运行时适配不同版本的 GL 实现，也方便了测试（可注入mock接口）。

2. **海量驱动兼容修正：** `GrGLCaps.cpp` 中积累了大量针对特定GPU/驱动的workaround。这些修正来自 Chrome 浏览器和其他 Skia 用户在数百万设备上的实际运行经验。修正覆盖了 NVIDIA、AMD、Intel、Qualcomm Adreno、ARM Mali、Imagination PowerVR 等几乎所有主流 GPU 厂商。

3. **GL 状态追踪：** `GrGLGpu` 维护了一套完整的 GL 状态影子副本，在每次状态切换前先比对缓存值。这是 GL 后端性能优化的核心机制，因为 GL 状态切换通常涉及内核态/用户态切换，开销较大。

4. **非缓冲渲染通道：** 与 Vulkan/Metal 后端不同，GL 后端的 `GrGLOpsRenderPass` 不缓冲任何命令。所有绘制调用立即发送给 GL 驱动。这是 GL API 设计本身的限制所导致的。
