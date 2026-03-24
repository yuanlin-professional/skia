# GrGLAttachment

> 源文件
> - src/gpu/ganesh/gl/GrGLAttachment.h
> - src/gpu/ganesh/gl/GrGLAttachment.cpp

## 概述

`GrGLAttachment` 是 Skia Ganesh 渲染引擎中用于管理 OpenGL Renderbuffer 对象的核心类。它继承自 `GrAttachment`，专门用于创建和管理帧缓冲区（Framebuffer）的附件，包括模板附件（Stencil Attachment）和多重采样颜色附件（MSAA Color Attachment）。该类封装了 OpenGL Renderbuffer 的创建、多重采样配置和资源管理逻辑。

## 架构位置

`GrGLAttachment` 位于 Ganesh GPU 后端的 OpenGL 实现层：

```
src/gpu/ganesh/
├── GrAttachment (抽象基类)
│   └── gl/
│       └── GrGLAttachment (OpenGL 实现)
└── GrGLGpu (OpenGL GPU 管理类)
```

该类是附件资源抽象在 OpenGL 后端的具体实现，主要用于帧缓冲区的配置。

## 主要类与结构体

### GrGLAttachment

**继承关系：**
```
GrResource
  └── GrGpuResource
      └── GrAttachment
          └── GrGLAttachment
```

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFormat` | `GrGLFormat` | OpenGL 内部格式（如 GL_STENCIL_INDEX8） |
| `fRenderbufferID` | `GrGLuint` | OpenGL Renderbuffer 对象 ID，外部 RB 可能为 0 |

## 公共 API 函数

### 创建接口

| 函数 | 功能 |
|------|------|
| `MakeStencil(GrGLGpu*, SkISize, int sampleCnt, GrGLFormat)` | 创建模板附件 |
| `MakeMSAA(GrGLGpu*, SkISize, int sampleCnt, GrGLFormat)` | 创建 MSAA 颜色附件 |
| `MakeWrappedRenderBuffer(...)` | 包装外部 Renderbuffer 对象 |

### 查询接口

| 函数 | 功能 |
|------|------|
| `renderbufferID()` | 获取 OpenGL Renderbuffer ID |
| `format()` | 获取 OpenGL 格式 |
| `backendFormat()` | 获取后端格式表示 |

## 内部实现细节

### 模板附件创建流程

`MakeStencil` 实现步骤：

1. **生成 Renderbuffer**：调用 `glGenRenderbuffers` 创建 RB 对象
2. **绑定 Renderbuffer**：使用 `glBindRenderbuffer(GL_RENDERBUFFER, rbID)` 绑定
3. **分配存储空间**：
   - **多重采样**：调用 `renderbuffer_storage_msaa` 分配 MSAA 存储
   - **单采样**：调用 `glRenderbufferStorage` 分配存储
4. **错误处理**：通过 `GL_ALLOC_CALL` 检查分配是否成功，失败则删除 RB
5. **返回对象**：创建 `GrGLAttachment` 实例，标记为模板附件用途

### MSAA 颜色附件创建

`MakeMSAA` 流程与 `MakeStencil` 类似，但：
- 使用 `getRenderbufferInternalFormat` 获取适合渲染的内部格式
- 标记用途为 `UsageFlags::kColorAttachment`
- 必须使用多重采样存储（`renderbuffer_storage_msaa`）

### 多重采样存储适配

`renderbuffer_storage_msaa` 函数根据 MSAA 扩展类型适配：

| MSAA 类型 | 使用函数 | 平台 |
|----------|---------|------|
| `kStandard_MSFBOType` | `glRenderbufferStorageMultisample` | OpenGL 3.0+, ES 3.0+ |
| `kES_Apple_MSFBOType` | `glRenderbufferStorageMultisampleAPPLE` | Apple 平台扩展 |
| `kES_EXT_MsToTexture_MSFBOType` | `glRenderbufferStorageMultisampleEXT` | IMG/EXT 扩展 |
| `kES_IMG_MsToTexture_MSFBOType` | `glRenderbufferStorageMultisampleIMG` | IMG 扩展 |

### 包装外部 Renderbuffer

`MakeWrappedRenderBuffer` 允许包装已存在的 Renderbuffer：
- 不调用 `glGenRenderbuffers`，直接使用传入的 ID
- 支持指定用途标志（模板或颜色附件）
- 用于与外部 OpenGL 代码互操作

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLGpu` | OpenGL GPU 管理，获取能力信息 |
| `GrGLCaps` | 查询 MSAA 支持类型和格式能力 |
| `GrGLInterface` | OpenGL 函数指针 |
| `GrGLUtil` | 格式转换（`GrGLFormatToEnum`） |
| `GrBackendFormats` | 创建后端格式对象 |
| `SkTraceMemoryDump` | 内存追踪 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `GrGLRenderTarget` | 附加模板和 MSAA 附件到 FBO |
| `GrGLFramebuffer` | 作为 FBO 附件使用 |
| `GrGLGpu` | 在 FBO 配置时创建和管理附件 |

## 设计模式与设计决策

### 工厂模式

提供三个静态工厂方法而非公共构造函数：
- **MakeStencil**：专用于创建模板附件，明确语义
- **MakeMSAA**：专用于创建 MSAA 附件，避免混淆
- **MakeWrappedRenderBuffer**：支持外部资源包装
- 允许在创建失败时返回 `nullptr`

### 用途标志设计

通过 `UsageFlags` 明确附件用途：
- `kStencilAttachment`：用于深度/模板测试
- `kColorAttachment`：用于颜色渲染（MSAA）
- 构造函数断言只允许这两种用途

### 后端格式抽象

`backendFormat()` 方法：
- 将 `GrGLFormat` 转换为跨平台的 `GrBackendFormat`
- 对于附件，纹理目标统一使用 `GL_TEXTURE_NONE`
- 支持跨后端的格式查询

### 资源标签支持

`onSetLabel` 实现：
- 通过 `GL_KHR_debug` 设置 Renderbuffer 标签
- 前缀 `_Skia_` 标识 Skia 创建的对象
- **注意**：实现中使用了 `GL_TEXTURE` 而非 `GL_RENDERBUFFER`（可能是 bug）

### 外部 Renderbuffer 支持

允许 Renderbuffer ID 为 0：
- 用于某些平台的外部模板缓冲区（注释提到）
- 客户端只需告知模板位数，无需提供 ID
- 释放和废弃时需检查 ID 是否为 0

## 性能考量

### MSAA 存储优化

根据 GPU 能力选择最优 MSAA 路径：
- **桌面 OpenGL**：使用标准 `glRenderbufferStorageMultisample`
- **Apple 设备**：使用 Apple 扩展优化路径
- **IMG GPU**：支持 MsToTexture 扩展（无需 MSAA RB）
- **EXT 扩展**：兼容更多 ES 设备

### 内存分配检查

使用 `GL_ALLOC_CALL` 宏：
- 在 `skipErrorChecks` 模式下跳过错误查询
- 否则调用 `getErrorAndCheckForOOM` 检测 OOM
- 分配失败立即删除 Renderbuffer，避免资源泄漏

### 格式适配

模板和颜色附件使用不同的格式获取逻辑：
- **模板**：直接使用 `GrGLFormatToEnum(format)`
- **颜色**：使用 `getRenderbufferInternalFormat(format)` 可能返回不同格式
- 适配不同 OpenGL 版本的格式要求

### 内存追踪

`setMemoryBacking` 实现：
- 将 Renderbuffer ID 转换为字符串作为后端标识
- 使用 `"gl_renderbuffer"` 作为类型标识符
- 支持 Chrome 内存分析工具

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `GrAttachment.h/cpp` | 基类 | 定义附件抽象接口 |
| `GrGLRenderTarget.h/cpp` | 使用者 | 附加附件到 FBO |
| `GrGLFramebuffer.h/cpp` | 使用者 | FBO 配置和管理 |
| `GrGLGpu.h/cpp` | 创建者 | 创建和管理附件资源 |
| `GrGLCaps.h/cpp` | 配置提供者 | 查询 MSAA 和格式支持 |
| `GrGLDefines.h` | 常量定义 | OpenGL 常量定义 |
| `GrGLUtil.h` | 工具函数 | 格式转换和调用包装 |
| `GrGLTypesPriv.h` | 类型定义 | OpenGL 后端类型定义 |
