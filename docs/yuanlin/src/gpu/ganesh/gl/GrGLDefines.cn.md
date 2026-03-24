# GrGLDefines

> 源文件: src/gpu/ganesh/gl/GrGLDefines.h

## 概述

`GrGLDefines.h` 是 Skia 图形库 Ganesh OpenGL 后端的核心常量定义文件,包含超过 1100 行的 OpenGL/OpenGL ES/WebGL 常量宏定义。该文件统一定义了所有 Skia OpenGL 后端需要使用的 GL 常量,包括纹理格式、混合模式、帧缓冲参数、着色器类型、查询对象等,是整个 OpenGL 后端代码的基础依赖。

该文件的设计目标是提供跨平台的 OpenGL 常量定义,使 Skia 代码能够在不同的 OpenGL 实现(桌面 GL、GLES、WebGL)之间保持一致性,并支持各种扩展功能。

## 架构位置

`GrGLDefines.h` 位于 Skia GPU 渲染架构的 OpenGL 基础层:

```
skia/
└── src/gpu/ganesh/gl/
    ├── GrGLDefines.h          <- 本模块
    ├── GrGLTypes.h            <- OpenGL 类型定义
    ├── GrGLInterface.h        <- OpenGL 函数接口
    ├── GrGLGpu.h/cpp          <- 使用这些常量
    └── GrGLUtil.h             <- OpenGL 工具函数
```

该文件被几乎所有 OpenGL 后端模块包含,是最底层的基础定义文件。

## 主要常量分类

### 1. 上下文与配置 (Context Profile)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_CONTEXT_PROFILE_MASK` | 0x9126 | 上下文配置掩码 |
| `GR_GL_CONTEXT_CORE_PROFILE_BIT` | 0x00000001 | 核心配置位 |
| `GR_GL_CONTEXT_COMPATIBILITY_PROFILE_BIT` | 0x00000002 | 兼容配置位 |
| `GR_GL_CONTEXT_FLAGS` | 0x821E | 上下文标志 |
| `GR_GL_CONTEXT_FLAG_DEBUG_BIT` | 0x00000002 | 调试标志位 |
| `GR_GL_CONTEXT_FLAG_PROTECTED_CONTENT_BIT_EXT` | 0x00000010 | 受保护内容位 |

### 2. 缓冲区常量 (Buffer Bits)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_DEPTH_BUFFER_BIT` | 0x00000100 | 深度缓冲位 |
| `GR_GL_STENCIL_BUFFER_BIT` | 0x00000400 | 模板缓冲位 |
| `GR_GL_COLOR_BUFFER_BIT` | 0x00004000 | 颜色缓冲位 |

### 3. 基本类型 (Boolean & Primitive Types)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_FALSE` | 0 | 布尔假值 |
| `GR_GL_TRUE` | 1 | 布尔真值 |
| `GR_GL_POINTS` | 0x0000 | 点图元 |
| `GR_GL_LINES` | 0x0001 | 线图元 |
| `GR_GL_LINE_STRIP` | 0x0003 | 线带 |
| `GR_GL_TRIANGLES` | 0x0004 | 三角形 |
| `GR_GL_TRIANGLE_STRIP` | 0x0005 | 三角带 |
| `GR_GL_TRIANGLE_FAN` | 0x0006 | 三角扇 |
| `GR_GL_PATCHES` | 0x000E | 细分面片 |

### 4. 混合方程 (Blend Equations)

包括基本混合和高级混合(KHR_blend_equation_advanced):

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_FUNC_ADD` | 0x8006 | 加法混合 |
| `GR_GL_FUNC_SUBTRACT` | 0x800A | 减法混合 |
| `GR_GL_FUNC_REVERSE_SUBTRACT` | 0x800B | 反向减法 |
| `GR_GL_SCREEN` | 0x9295 | 屏幕混合 |
| `GR_GL_OVERLAY` | 0x9296 | 叠加混合 |
| `GR_GL_MULTIPLY` | 0x9294 | 正片叠底 |
| `GR_GL_HSL_HUE` | 0x92AD | HSL 色相混合 |
| `GR_GL_HSL_LUMINOSITY` | 0x92B0 | HSL 亮度混合 |

### 5. 混合因子 (Blend Factors)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_ZERO` | 0 | 零因子 |
| `GR_GL_ONE` | 1 | 一因子 |
| `GR_GL_SRC_COLOR` | 0x0300 | 源颜色 |
| `GR_GL_ONE_MINUS_SRC_COLOR` | 0x0301 | 1-源颜色 |
| `GR_GL_SRC_ALPHA` | 0x0302 | 源 Alpha |
| `GR_GL_ONE_MINUS_SRC_ALPHA` | 0x0303 | 1-源 Alpha |
| `GR_GL_DST_COLOR` | 0x0306 | 目标颜色 |
| `GR_GL_CONSTANT_COLOR` | 0x8001 | 常量颜色 |

### 6. 缓冲区对象 (Buffer Objects)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_ARRAY_BUFFER` | 0x8892 | 顶点数据缓冲 |
| `GR_GL_ELEMENT_ARRAY_BUFFER` | 0x8893 | 索引缓冲 |
| `GR_GL_DRAW_INDIRECT_BUFFER` | 0x8F3F | 间接绘制缓冲 |
| `GR_GL_PIXEL_PACK_BUFFER` | 0x88EB | 像素打包缓冲 |
| `GR_GL_PIXEL_UNPACK_BUFFER` | 0x88EC | 像素解包缓冲 |
| `GR_GL_TEXTURE_BUFFER` | 0x8C2A | 纹理缓冲 |

### 7. 缓冲区使用模式 (Buffer Usage)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_STREAM_DRAW` | 0x88E0 | 流式绘制 |
| `GR_GL_STATIC_DRAW` | 0x88E4 | 静态绘制 |
| `GR_GL_DYNAMIC_DRAW` | 0x88E8 | 动态绘制 |

### 8. 纹理格式 (Texture Formats)

#### 无符号格式

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_RGB` | 0x1907 | RGB 格式 |
| `GR_GL_RGBA` | 0x1908 | RGBA 格式 |
| `GR_GL_BGRA` | 0x80E1 | BGRA 格式 |
| `GR_GL_RED` | 0x1903 | 单通道红色 |
| `GR_GL_RG` | 0x8227 | 双通道 RG |
| `GR_GL_ALPHA` | 0x1906 | Alpha 通道 |
| `GR_GL_LUMINANCE` | 0x1909 | 亮度 |

#### 大小格式 (Sized Formats)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_R8` | 0x8229 | 8 位红色 |
| `GR_GL_R16F` | 0x822D | 16 位浮点红色 |
| `GR_GL_RG8` | 0x822B | 8 位 RG |
| `GR_GL_RGB8` | 0x8051 | 8 位 RGB |
| `GR_GL_RGBA8` | 0x8058 | 8 位 RGBA |
| `GR_GL_RGBA16F` | 0x881A | 16 位浮点 RGBA |
| `GR_GL_RGB10_A2` | 0x8059 | 10 位 RGB + 2 位 Alpha |
| `GR_GL_SRGB8_ALPHA8` | 0x8C43 | sRGB 8 位 RGBA |

### 9. 压缩纹理格式 (Compressed Formats)

#### DXT/S3TC 格式

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_COMPRESSED_RGB_S3TC_DXT1_EXT` | 0x83F0 | DXT1 RGB |
| `GR_GL_COMPRESSED_RGBA_S3TC_DXT5_EXT` | 0x83F3 | DXT5 RGBA |

#### ETC2 格式

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_COMPRESSED_RGB8_ETC2` | 0x9274 | ETC2 RGB8 |
| `GR_GL_COMPRESSED_RGBA8_ETC2_EAC` | 0x9278 | ETC2 RGBA8 |

#### ASTC 格式

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_COMPRESSED_RGBA_ASTC_4x4` | 0x93B0 | ASTC 4x4 块 |
| `GR_GL_COMPRESSED_RGBA_ASTC_8x8` | 0x93B7 | ASTC 8x8 块 |

### 10. 数据类型 (Data Types)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_BYTE` | 0x1400 | 有符号字节 |
| `GR_GL_UNSIGNED_BYTE` | 0x1401 | 无符号字节 |
| `GR_GL_SHORT` | 0x1402 | 短整型 |
| `GR_GL_UNSIGNED_SHORT` | 0x1403 | 无符号短整型 |
| `GR_GL_INT` | 0x1404 | 整型 |
| `GR_GL_UNSIGNED_INT` | 0x1405 | 无符号整型 |
| `GR_GL_FLOAT` | 0x1406 | 浮点型 |
| `GR_GL_HALF_FLOAT` | 0x140B | 半精度浮点 |

### 11. 着色器相关 (Shaders)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_FRAGMENT_SHADER` | 0x8B30 | 片段着色器 |
| `GR_GL_VERTEX_SHADER` | 0x8B31 | 顶点着色器 |
| `GR_GL_TESS_CONTROL_SHADER` | 0x8E88 | 细分控制着色器 |
| `GR_GL_TESS_EVALUATION_SHADER` | 0x8E87 | 细分求值着色器 |
| `GR_GL_COMPILE_STATUS` | 0x8B81 | 编译状态 |
| `GR_GL_LINK_STATUS` | 0x8B82 | 链接状态 |

### 12. Uniform 类型 (Uniform Types)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_FLOAT_VEC2` | 0x8B50 | 2D 浮点向量 |
| `GR_GL_FLOAT_VEC3` | 0x8B51 | 3D 浮点向量 |
| `GR_GL_FLOAT_VEC4` | 0x8B52 | 4D 浮点向量 |
| `GR_GL_FLOAT_MAT2` | 0x8B5A | 2x2 浮点矩阵 |
| `GR_GL_FLOAT_MAT3` | 0x8B5B | 3x3 浮点矩阵 |
| `GR_GL_FLOAT_MAT4` | 0x8B5C | 4x4 浮点矩阵 |
| `GR_GL_SAMPLER_2D` | 0x8B5E | 2D 纹理采样器 |
| `GR_GL_SAMPLER_CUBE` | 0x8B60 | 立方体贴图采样器 |

### 13. 纹理参数 (Texture Parameters)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_TEXTURE_2D` | 0x0DE1 | 2D 纹理 |
| `GR_GL_TEXTURE_CUBE_MAP` | 0x8513 | 立方体贴图 |
| `GR_GL_TEXTURE_RECTANGLE` | 0x84F5 | 矩形纹理 |
| `GR_GL_TEXTURE_EXTERNAL` | 0x8D65 | 外部纹理(Android) |
| `GR_GL_TEXTURE_MIN_FILTER` | 0x2801 | 缩小滤波 |
| `GR_GL_TEXTURE_MAG_FILTER` | 0x2800 | 放大滤波 |
| `GR_GL_TEXTURE_WRAP_S` | 0x2802 | S 方向包裹模式 |
| `GR_GL_TEXTURE_WRAP_T` | 0x2803 | T 方向包裹模式 |

### 14. 纹理滤波模式 (Texture Filtering)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_NEAREST` | 0x2600 | 最近邻滤波 |
| `GR_GL_LINEAR` | 0x2601 | 线性滤波 |
| `GR_GL_NEAREST_MIPMAP_NEAREST` | 0x2700 | 最近邻 mipmap |
| `GR_GL_LINEAR_MIPMAP_LINEAR` | 0x2703 | 三线性滤波 |

### 15. 帧缓冲对象 (Framebuffer Objects)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_FRAMEBUFFER` | 0x8D40 | 帧缓冲 |
| `GR_GL_READ_FRAMEBUFFER` | 0x8CA8 | 读帧缓冲 |
| `GR_GL_DRAW_FRAMEBUFFER` | 0x8CA9 | 写帧缓冲 |
| `GR_GL_RENDERBUFFER` | 0x8D41 | 渲染缓冲 |
| `GR_GL_COLOR_ATTACHMENT0` | 0x8CE0 | 颜色附件 0 |
| `GR_GL_DEPTH_ATTACHMENT` | 0x8D00 | 深度附件 |
| `GR_GL_STENCIL_ATTACHMENT` | 0x8D20 | 模板附件 |

### 16. 查询对象 (Query Objects)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_TIME_ELAPSED` | 0x88BF | 经过时间查询 |
| `GR_GL_TIMESTAMP` | 0x8E28 | 时间戳查询 |
| `GR_GL_SAMPLES_PASSED` | 0x8914 | 样本通过查询 |
| `GR_GL_ANY_SAMPLES_PASSED` | 0x8C2F | 任意样本通过查询 |

### 17. 同步对象 (Sync Objects)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_SYNC_GPU_COMMANDS_COMPLETE` | 0x9117 | GPU 命令完成 |
| `GR_GL_ALREADY_SIGNALED` | 0x911A | 已触发 |
| `GR_GL_TIMEOUT_EXPIRED` | 0x911B | 超时 |
| `GR_GL_CONDITION_SATISFIED` | 0x911C | 条件满足 |
| `GR_GL_WAIT_FAILED` | 0x911D | 等待失败 |
| `GR_GL_TIMEOUT_IGNORED` | 0xFFFFFFFFFFFFFFFFull | 忽略超时 |

### 18. 调试扩展 (Debug Extension - KHR_debug)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_DEBUG_OUTPUT` | 0x92E0 | 调试输出 |
| `GR_GL_DEBUG_OUTPUT_SYNCHRONOUS` | 0x8242 | 同步调试输出 |
| `GR_GL_DEBUG_SEVERITY_HIGH` | 0x9146 | 高严重性 |
| `GR_GL_DEBUG_TYPE_ERROR` | 0x824C | 错误类型 |
| `GR_GL_DEBUG_TYPE_PERFORMANCE` | 0x8250 | 性能类型 |

### 19. 内存屏障 (Memory Barriers)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_GL_TEXTURE_FETCH_BARRIER_BIT` | 0x0008 | 纹理获取屏障 |
| `GR_GL_SHADER_IMAGE_ACCESS_BARRIER_BIT` | 0x0020 | 着色器图像访问屏障 |
| `GR_GL_FRAMEBUFFER_BARRIER_BIT` | 0x0400 | 帧缓冲屏障 |
| `GR_GL_ALL_BARRIER_BITS` | 0xffffffff | 所有屏障 |

### 20. EGL 常量 (EGL Defines)

| 常量名 | 值 | 说明 |
|--------|---|------|
| `GR_EGL_NO_DISPLAY` | `((GrEGLDisplay)nullptr)` | 无显示 |
| `GR_EGL_EXTENSIONS` | 0x3055 | EGL 扩展 |
| `GR_EGL_GL_TEXTURE_2D` | 0x30B1 | GL 2D 纹理 |
| `GR_EGL_IMAGE_PRESERVED` | 0x30D2 | 图像保留 |
| `GR_EGL_NO_IMAGE` | `((GrEGLImage)nullptr)` | 无图像 |

## 依赖关系

### 依赖的模块

该文件为纯定义文件,不依赖其他模块。

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrGLGpu.cpp` | 使用几乎所有常量 |
| `GrGLInterface.h` | 使用类型常量 |
| `GrGLCaps.cpp` | 使用格式和扩展常量 |
| `GrGLTexture.cpp` | 使用纹理相关常量 |
| `GrGLRenderTarget.cpp` | 使用帧缓冲常量 |
| `GrGLProgram.cpp` | 使用着色器和 uniform 常量 |
| `GrGLBuffer.cpp` | 使用缓冲区常量 |

## 设计模式与设计决策

### 1. 宏定义而非枚举

选择使用 `#define` 而非 `enum`:

**优点**:
- 与 OpenGL 官方头文件保持一致
- 避免类型转换问题
- 编译器可完全优化为常量

**权衡**: 失去类型安全,但 OpenGL API 本身就是弱类型的。

### 2. GR_ 前缀命名

所有常量使用 `GR_GL_` 前缀:

**目的**:
- 避免与系统 OpenGL 头文件冲突
- 明确标识为 Skia 内部定义
- 支持头文件隔离(不依赖系统 GL 头文件)

### 3. 完整常量集合

定义所有可能用到的常量,即使当前未使用:

**设计理念**: 提供完整的 API 覆盖,方便未来扩展。

### 4. 分类注释

使用注释将常量按功能分组:

```cpp
/* BlendingFactorDest */
/* TextureParameterName */
/* Framebuffer Object */
```

**优点**: 提高可读性,便于查找和维护。

### 5. 保留标准值

对于有多个别名的常量,保留所有定义:

```cpp
#define GR_GL_ZERO 0
/*      GL_ZERO */  // 在其他分类中引用
```

**目的**: 保持与 OpenGL 规范的完整对应关系。

## 性能考量

### 1. 编译时常量

所有定义都是编译时常量:

```cpp
#define GR_GL_TEXTURE_2D 0x0DE1
```

**优势**: 零运行时成本,编译器可完全内联。

### 2. 头文件保护

使用标准头文件保护:

```cpp
#ifndef GrGLDefines_DEFINED
#define GrGLDefines_DEFINED
// ...
#endif
```

**优点**: 避免重复包含的编译开销。

### 3. 无函数定义

该文件仅包含宏定义,无函数或变量定义:

**优势**: 不会增加二进制大小,不影响链接时间。

### 4. 整数常量优化

使用十六进制整数常量:

```cpp
#define GR_GL_RGBA8 0x8058
```

**优点**: 编译器可直接嵌入机器码,无需查表或计算。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/gpu/ganesh/gl/GrGLTypes.h` | OpenGL 类型定义 |
| `include/gpu/ganesh/gl/GrGLFunctions.h` | OpenGL 函数声明 |
| `src/gpu/ganesh/gl/GrGLGpu.h` | 主要使用者 |
| `src/gpu/ganesh/gl/GrGLInterface.h` | OpenGL 接口 |
| `src/gpu/ganesh/gl/GrGLUtil.h` | 工具函数 |
| `src/gpu/ganesh/gl/GrGLCaps.h` | 功能查询 |
