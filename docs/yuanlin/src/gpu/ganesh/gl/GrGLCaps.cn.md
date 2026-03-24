# GrGLCaps

> 源文件
> - src/gpu/ganesh/gl/GrGLCaps.h
> - src/gpu/ganesh/gl/GrGLCaps.cpp

## 概述

`GrGLCaps` 是 Skia Ganesh 渲染引擎中最复杂的能力查询类之一，负责检测和管理 OpenGL/OpenGL ES/WebGL 上下文的所有能力、扩展和限制。该类继承自 `GrCaps`，在初始化时通过查询 OpenGL 状态、版本字符串和扩展列表，构建出一个完整的能力描述，供整个 Ganesh 渲染管线使用。该类还包含大量驱动 bug 修复逻辑和平台特定优化。

## 架构位置

`GrGLCaps` 位于 Ganesh GPU 后端的 OpenGL 能力查询层：

```
src/gpu/ganesh/
├── GrCaps (抽象基类)
│   └── gl/
│       └── GrGLCaps (OpenGL 能力实现)
├── GrGLGpu (使用 GrGLCaps 进行能力查询)
└── GrDirectContext (创建时初始化 GrGLCaps)
```

该类是所有 OpenGL 渲染决策的基础，几乎被 Ganesh 的每个模块使用。

## 主要类与结构体

### GrGLCaps

**继承关系：**
```
GrCaps (抽象基类)
  └── GrGLCaps (OpenGL 实现)
```

**关键成员变量（部分）：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fStandard` | `GrGLStandard` | OpenGL 标准类型（GL/GLES/WebGL） |
| `fMSFBOType` | `MSFBOType` | MSAA 帧缓冲区类型 |
| `fInvalidateFBType` | `InvalidateFBType` | 帧缓冲区失效方式 |
| `fMapBufferType` | `MapBufferType` | 缓冲区映射类型 |
| `fTransferBufferType` | `TransferBufferType` | 传输缓冲区类型 |
| `fFormatTable` | `FormatInfo[kGrGLColorFormatCount]` | 格式信息表 |
| `fStencilFormats` | `TArray<GrGLFormat>` | 支持的模板格式列表 |
| `fMaxFragmentUniformVectors` | `int` | 最大片段着色器 uniform 向量数 |
| `fBlitFramebufferFlags` | `uint32_t` | Blit 操作限制标志 |

### MSFBOType（多重采样帧缓冲区类型）

| 枚举值 | 说明 |
|-------|------|
| `kNone_MSFBOType` | 不支持 MSAA |
| `kStandard_MSFBOType` | 标准 MSAA（OpenGL 3.0+, ES 3.0+） |
| `kES_Apple_MSFBOType` | Apple 的 MSAA 扩展 |
| `kES_IMG_MsToTexture_MSFBOType` | IMG 渲染到纹理 MSAA |
| `kES_EXT_MsToTexture_MSFBOType` | EXT 渲染到纹理 MSAA |

### InvalidateFBType（帧缓冲区失效类型）

| 枚举值 | 说明 |
|-------|------|
| `kNone_InvalidateFBType` | 不支持失效操作 |
| `kDiscard_InvalidateFBType` | 使用 `glDiscardFramebuffer` |
| `kInvalidate_InvalidateFBType` | 使用 `glInvalidateFramebuffer` |

### MapBufferType（缓冲区映射类型）

| 枚举值 | 说明 |
|-------|------|
| `kNone_MapBufferType` | 不支持映射 |
| `kMapBuffer_MapBufferType` | 使用 `glMapBuffer` |
| `kMapBufferRange_MapBufferType` | 使用 `glMapBufferRange` |
| `kChromium_MapBufferType` | Chromium 特定映射 |

## 公共 API 函数

### 核心能力查询

| 函数 | 功能 |
|------|------|
| `isFormatTexturable(GrGLFormat)` | 查询格式是否可纹理化 |
| `isFormatRenderable(GrGLFormat, int sampleCnt)` | 查询格式是否可渲染 |
| `getRenderTargetSampleCount(int, GrGLFormat)` | 获取支持的采样数 |
| `maxRenderTargetSampleCount(GrGLFormat)` | 获取最大采样数 |
| `canFormatBeFBOColorAttachment(GrGLFormat)` | 查询格式是否可作为 FBO 颜色附件 |

### 格式查询

| 函数 | 功能 |
|------|------|
| `getFormatFromColorType(GrColorType)` | 从颜色类型获取 OpenGL 格式 |
| `getTexImageOrStorageInternalFormat(GrGLFormat)` | 获取纹理内部格式 |
| `getRenderbufferInternalFormat(GrGLFormat)` | 获取 Renderbuffer 内部格式 |
| `getTexImageExternalFormatAndType(...)` | 获取纹理上传的外部格式和类型 |

### MSAA 能力

| 函数 | 功能 |
|------|------|
| `msFBOType()` | 获取 MSAA 类型 |
| `usesMSAARenderBuffers()` | 是否使用 MSAA Renderbuffer |
| `usesImplicitMSAAResolve()` | 是否使用隐式 MSAA resolve |
| `framebufferResolvesMustBeFullSize()` | resolve 是否必须全尺寸 |

### 特性查询

| 函数 | 功能 |
|------|------|
| `textureSwizzleSupport()` | 纹理 swizzle 支持 |
| `samplerObjectSupport()` | 采样器对象支持 |
| `programBinarySupport()` | 程序二进制支持 |
| `debugSupport()` | 调试扩展支持 |
| `fenceSyncSupport()` | Fence 同步支持 |

## 内部实现细节

### 初始化流程

`init` 方法执行顺序：

1. **版本和标准检测**：解析 `GL_VERSION` 字符串
2. **基础能力查询**：
   - Uniform 向量数量
   - 顶点属性数量
   - 核心 Profile 检测（OpenGL 3.2+）
3. **读写像素支持检测**：
   - `GL_PACK_ROW_LENGTH` 支持
   - `GL_UNPACK_ROW_LENGTH` 支持
4. **扩展初始化**：
   - 查询所有可用扩展
   - 初始化 `GrGLExtensions` 对象
5. **特性支持检测**：
   - 纹理屏障
   - VAO 支持
   - 实例化绘制
   - 帧缓冲区 Blit
   - 缓冲区映射
   - 传输缓冲区
6. **MSAA 支持初始化**：`initFSAASupport`
7. **模板支持初始化**：`initStencilSupport`
8. **格式表初始化**：`initFormatTable`
9. **驱动修正应用**：`applyDriverCorrectnessWorkarounds`
10. **着色器能力初始化**：`initGLSL`

### 格式表结构

`FormatInfo` 结构体包含每种 OpenGL 格式的完整信息：

```cpp
struct FormatInfo {
    uint32_t fFlags;                              // 能力标志
    FormatType fFormatType;                       // 格式类型（浮点/定点）
    GrGLenum fInternalFormatForTexImageOrStorage; // 纹理内部格式
    GrGLenum fInternalFormatForRenderbuffer;      // Renderbuffer 内部格式
    GrGLenum fDefaultExternalFormat;              // 默认外部格式
    GrGLenum fDefaultExternalType;                // 默认外部类型
    int fStencilFormatIndex;                      // 模板格式索引
    SkTDArray<int> fColorSampleCounts;            // 支持的采样数数组
    std::unique_ptr<ColorTypeInfo[]> fColorTypeInfos; // 颜色类型信息
};
```

### ColorTypeInfo 结构

针对每种 `(GrGLFormat, GrColorType)` 组合：

```cpp
struct ColorTypeInfo {
    GrColorType fColorType;        // 颜色类型
    uint32_t fFlags;               // 支持的操作标志
    skgpu::Swizzle fReadSwizzle;   // 读取时的 swizzle
    skgpu::Swizzle fWriteSwizzle;  // 写入时的 swizzle
    ExternalIOFormats fExternalIOFormats[]; // 外部 I/O 格式数组
};
```

### MSAA 支持检测

`initFSAASupport` 检测多种 MSAA 实现：

1. **标准 MSAA**（OpenGL 3.0+, ES 3.0+）：
   - `GL_ARB_framebuffer_object`
   - `GL_CHROMIUM_framebuffer_multisample`
   - `GL_ANGLE_framebuffer_multisample`

2. **Apple MSAA**（iOS）：
   - `GL_APPLE_framebuffer_multisample`

3. **IMG 渲染到纹理**：
   - `GL_IMG_multisampled_render_to_texture`
   - 无需 MSAA Renderbuffer

4. **EXT 渲染到纹理**：
   - `GL_EXT_multisampled_render_to_texture`

### 驱动 Bug 修正

`applyDriverCorrectnessWorkarounds` 包含数百个特定驱动的 bug 修复：

**示例 1：Intel Mac 边界值清除 Bug**
```cpp
if (kIntel_GrGLVendor == ctxInfo.vendor() && kMac_GrGLDriver == ctxInfo.driver()) {
    fClearToBoundaryValuesIsBroken = true;
}
```

**示例 2：Adreno 基础顶点 Bug**
```cpp
if (kQualcomm_GrGLVendor == ctxInfo.vendor()) {
    fDrawArraysBaseVertexIsBroken = true;
}
```

**示例 3：Mali 动态 MSAA 禁用**
```cpp
if (kARM_GrGLVendor == ctxInfo.vendor()) {
    fDisallowDynamicMSAA = true;
}
```

### 格式初始化逻辑

`initFormatTable` 为每种格式设置能力：

```cpp
FormatInfo& info = fFormatTable[static_cast<int>(GrGLFormat::kRGBA8)];
info.fFormatType = FormatType::kNormalizedFixedPoint;
info.fInternalFormatForTexImageOrStorage = GR_GL_RGBA8;
info.fInternalFormatForRenderbuffer = GR_GL_RGBA8;
info.fDefaultExternalFormat = GR_GL_RGBA;
info.fDefaultExternalType = GR_GL_UNSIGNED_BYTE;
info.fFlags = FormatInfo::kTexturable_Flag |
              FormatInfo::kFBOColorAttachment_Flag |
              FormatInfo::kTransfers_Flag;
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrCaps` | 基类，提供通用能力接口 |
| `GrGLContextInfo` | OpenGL 上下文信息（版本、扩展、厂商） |
| `GrGLInterface` | OpenGL 函数指针表 |
| `GrGLUtil` | OpenGL 工具函数 |
| `GrShaderCaps` | 着色器能力管理 |
| `GrContextOptions` | 上下文创建选项 |
| `GrDriverBugWorkarounds` | 驱动 bug 修正配置 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `GrGLGpu` | 使用能力信息决定渲染路径 |
| `GrGLTexture` | 查询纹理格式支持 |
| `GrGLRenderTarget` | 查询渲染目标能力 |
| `GrGLOpsRenderPass` | 决定绘制调用参数 |
| `GrGLProgramBuilder` | 根据能力生成着色器代码 |

## 设计模式与设计决策

### 单例模式（隐式）

每个 `GrDirectContext` 持有一个 `GrGLCaps` 实例：
- 在上下文创建时初始化一次
- 整个上下文生命周期内不变
- 避免重复查询 OpenGL 状态

### 策略模式

通过枚举类型选择不同的实现策略：
- `MSFBOType`：MSAA 实现策略
- `MapBufferType`：缓冲区映射策略
- `InvalidateFBType`：失效操作策略

### 查表法优化

使用数组存储格式信息：
```cpp
FormatInfo fFormatTable[kGrGLColorFormatCount];
```
- O(1) 查询复杂度
- 紧凑的内存布局
- 缓存友好

### 能力继承

从 `GrCaps` 继承通用能力：
- 纹理大小限制
- 采样数限制
- 混合模式支持
- 压缩纹理支持

### Workaround 集中管理

所有驱动 bug 修正集中在一个方法中：
- 便于维护和审查
- 条件清晰，易于调试
- 支持通过 `GrContextOptions` 禁用

## 性能考量

### 初始化开销

`GrGLCaps` 初始化涉及大量 OpenGL 查询：
- 查询约 50+ OpenGL 状态
- 解析扩展字符串（可能包含数百个扩展）
- 初始化格式表（约 30+ 格式）
- **优化**：只在上下文创建时执行一次

### 查询性能

格式信息查询：
- 直接数组索引：O(1)
- 无需遍历或哈希查找
- 支持编译器内联优化

### 缓存策略

多种缓存机制：
- 格式表：预计算所有格式能力
- 采样数数组：预计算支持的采样数
- 扩展集合：哈希表查询

### 内存占用

`GrGLCaps` 对象大小约 100+ KB：
- 格式表占主要部分
- 每个 `FormatInfo` 包含多个 `ColorTypeInfo`
- 每个 `ColorTypeInfo` 包含多个 `ExternalIOFormats`

## 平台差异处理

### 桌面 OpenGL vs OpenGL ES

| 特性 | 桌面 GL | OpenGL ES |
|------|---------|-----------|
| 最低版本 | 2.0 | 2.0 |
| VAO | 3.0 核心或扩展 | 3.0 核心或 OES 扩展 |
| 实例化 | 3.1 核心或扩展 | 3.0 核心或扩展 |
| MRT | 2.0 核心 | 3.0 核心或扩展 |
| 整数纹理 | 3.0 核心 | 3.0 核心 |
| 采样器对象 | 3.3 核心或扩展 | 3.0 核心 |

### WebGL 特殊处理

WebGL 的限制：
- 没有客户端侧数组
- 没有 `glMapBuffer`
- 没有 `DrawBuffer` 和 `PolygonMode`
- 错误检查开销高（默认跳过）
- 需要初始化纹理以避免浏览器警告

### 厂商特定优化

**ARM Mali**：
- 平铺渲染架构
- 优先使用全屏清除
- 禁用客户端缓冲区
- 限制最大渲染目标尺寸为 4096

**Qualcomm Adreno**：
- 平铺渲染架构
- `DrawArraysBaseVertex` bug
- 支持 QCOM 特定扩展

**Intel**：
- 边界值清除 bug（Mac）
- BGRA 纹理存储问题（Windows ES）

**PowerVR**：
- 禁用颜色写入会导致采样掩码失效
- 特定设备禁用抖动

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `GrCaps.h/cpp` | 基类 | 通用能力抽象 |
| `GrGLContextInfo.h/cpp` | 输入 | OpenGL 上下文信息 |
| `GrGLInterface.h` | 依赖 | OpenGL 函数指针 |
| `GrGLUtil.h/cpp` | 工具 | OpenGL 工具函数 |
| `GrGLGpu.h/cpp` | 使用者 | OpenGL GPU 实现 |
| `GrShaderCaps.h/cpp` | 子组件 | 着色器能力管理 |
| `GrGLFormatTable.cpp` | 可能的拆分 | 格式表初始化逻辑 |
| `GrContextOptions.h` | 配置 | 上下文创建选项 |
| `GrDriverBugWorkarounds.h` | 配置 | 驱动 bug 修正选项 |
| `GrProgramDesc.h` | 使用者 | 着色器程序描述生成 |
