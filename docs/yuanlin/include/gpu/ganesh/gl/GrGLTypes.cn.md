# GrGLTypes - OpenGL 类型定义与抽象

> 源文件: `include/gpu/ganesh/gl/GrGLTypes.h`

## 概述

GrGLTypes.h 是 Skia Ganesh OpenGL 后端的核心类型定义文件，提供了 OpenGL 标准分类、格式枚举、基础类型别名以及与外部 OpenGL 资源交互的信息结构体。该文件通过编译时宏支持 OpenGL、OpenGL ES 和 WebGL 三种标准，为跨平台 OpenGL 抽象奠定基础。

## 架构位置

- **所属子系统**: GPU/Ganesh 渲染后端
- **层级**: 公共 API 接口层
- **作用域**: OpenGL 系列后端（GL/GLES/WebGL）

该文件位于 Ganesh GPU 后端的 OpenGL 实现模块顶层，是所有 OpenGL 相关代码的类型基础。

## 主要类与结构体

### GrGLStandard 枚举

定义 OpenGL 上下文的标准类型。

**枚举值**:
```cpp
enum GrGLStandard {
    kNone_GrGLStandard,    // 无效/未初始化
    kGL_GrGLStandard,      // 桌面 OpenGL
    kGLES_GrGLStandard,    // OpenGL ES（移动端）
    kWebGL_GrGLStandard    // WebGL（浏览器）
};
```

**编译时优化宏**:
```cpp
GR_IS_GR_GL(standard)      // 检查是否为桌面 GL
GR_IS_GR_GL_ES(standard)   // 检查是否为 GLES
GR_IS_GR_WEBGL(standard)   // 检查是否为 WebGL
```

通过 `SK_ASSUME_GL`, `SK_ASSUME_GL_ES`, `SK_ASSUME_WEBGL` 宏，可在编译时禁用特定标准的代码路径，减小代码体积。

### GrGLFormat 枚举

表示支持的 OpenGL 纹理格式（具体支持情况取决于 GL 版本和扩展）。

**颜色格式（部分列举）**:
- **常用格式**: `kRGBA8`, `kRGB8`, `kBGRA8`, `kRGB565`, `kRGBA16F`
- **单通道**: `kR8`, `kR16`, `kR16F`
- **双通道**: `kRG8`, `kRG16`, `kRG16F`
- **特殊格式**: `kALPHA8`, `kLUMINANCE8`, `kRGB10_A2`, `kSRGB8_ALPHA8`
- **压缩格式**: `kCOMPRESSED_ETC1_RGB8`, `kCOMPRESSED_RGB8_BC1`

**深度/模板格式**:
- `kSTENCIL_INDEX8`, `kSTENCIL_INDEX16`, `kDEPTH24_STENCIL8`

**边界标记**:
- `kLastColorFormat = kLUMINANCE16F`
- `kLast = kDEPTH24_STENCIL8`

### OpenGL 基础类型别名

为避免依赖平台 GL 头文件，定义所有 GL 函数参数类型：

| 类型别名 | 底层类型 | 用途 |
|---------|---------|------|
| GrGLenum | unsigned int | 枚举常量 |
| GrGLboolean | unsigned char | 布尔值 |
| GrGLbitfield | unsigned int | 位标志 |
| GrGLint | int | 有符号整数 |
| GrGLuint | unsigned int | 无符号整数（对象ID） |
| GrGLfloat | float | 单精度浮点 |
| GrGLsizei | int | 尺寸参数 |
| GrGLintptr | signed long [int] | 缓冲区偏移（平台相关） |
| GrGLsizeiptr | signed long [int] | 缓冲区大小（平台相关） |
| GrGLsync | struct __GLsync* | 同步对象 |

**平台差异处理**:
- Windows 64位使用 `long long int` 表示指针大小类型
- 其他平台使用 `long int`

### GrGLDrawArraysIndirectCommand

用于间接绘制的命令结构（对应 `glDrawArraysIndirect`）。

**字段**:
```cpp
struct GrGLDrawArraysIndirectCommand {
    GrGLuint fCount;          // 顶点数量
    GrGLuint fInstanceCount;  // 实例数量
    GrGLuint fFirst;          // 起始顶点索引
    GrGLuint fBaseInstance;   // 基础实例索引（ES需要EXT_base_instance）
};
```
**大小断言**: `static_assert(16 == sizeof(...))`，确保内存布局正确。

### GrGLDrawElementsIndirectCommand

用于索引间接绘制（对应 `glDrawElementsIndirect`）。

**字段**:
```cpp
struct GrGLDrawElementsIndirectCommand {
    GrGLuint fCount;          // 索引数量
    GrGLuint fInstanceCount;  // 实例数量
    GrGLuint fFirstIndex;     // 起始索引偏移
    GrGLuint fBaseVertex;     // 基础顶点偏移
    GrGLuint fBaseInstance;   // 基础实例索引
};
```
**大小断言**: `static_assert(20 == sizeof(...))`。

### GRGLDEBUGPROC 函数指针

KHR_debug 扩展的回调函数类型：
```cpp
typedef void (GR_GL_FUNCTION_TYPE* GRGLDEBUGPROC)(
    GrGLenum source,     // 消息来源
    GrGLenum type,       // 消息类型
    GrGLuint id,         // 消息ID
    GrGLenum severity,   // 严重程度
    GrGLsizei length,    // 消息长度
    const GrGLchar* message,  // 消息内容
    const void* userParam     // 用户参数
);
```

### EGL 类型别名

用于 EGL 互操作（如共享外部图像）：
```cpp
typedef void* GrEGLImage;
typedef void* GrEGLDisplay;
typedef void* GrEGLContext;
typedef void* GrEGLClientBuffer;
typedef unsigned int GrEGLenum;
typedef int32_t GrEGLint;
typedef unsigned int GrEGLBoolean;
```

### GrGLTextureInfo

封装外部 OpenGL 纹理信息，用于 `GrBackendTexture` 包装。

**关键成员**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fTarget | GrGLenum | 纹理目标（GL_TEXTURE_2D等） |
| fID | GrGLuint | OpenGL 纹理对象ID |
| fFormat | GrGLenum | 内部格式（sized format） |
| fProtected | skgpu::Protected | 受保护内存标志 |

**成员函数**:
- `operator==`: 比较所有字段
- `isProtected()`: 检查是否为受保护纹理

### GrGLFramebufferInfo

封装 OpenGL 帧缓冲对象信息。

**关键成员**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fFBOID | GrGLuint | 帧缓冲对象ID（0表示默认帧缓冲） |
| fFormat | GrGLenum | 颜色附件格式 |
| fProtected | skgpu::Protected | 受保护内存标志 |

**成员函数**: 同 `GrGLTextureInfo`。

### GrGLSurfaceInfo

描述 OpenGL 表面的创建参数。

**关键成员**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fSampleCount | uint32_t | 多重采样数量 |
| fLevelCount | uint32_t | Mipmap 层级数 |
| fProtected | skgpu::Protected | 受保护内存标志 |
| fTarget | GrGLenum | 纹理目标 |
| fFormat | GrGLenum | 像素格式 |

## 公共 API 函数

该文件主要提供类型定义和结构体，不包含函数实现。结构体的成员函数包括：

### `GrGLTextureInfo::operator==` / `GrGLFramebufferInfo::operator==`
```cpp
bool operator==(const GrGLTextureInfo& that) const
```
- **功能**: 比较两个 GL 对象信息是否相同
- **比较内容**: 所有成员字段逐一比较
- **用途**: 资源去重、缓存查找

### `isProtected()`
```cpp
bool isProtected() const
```
- **功能**: 检查资源是否使用受保护内存
- **返回值**: 如果 `fProtected == skgpu::Protected::kYes` 返回 true
- **用途**: Android 平台的 DRM 内容保护

## 内部实现细节

### 编译时标准选择机制

通过三个互斥宏实现编译时优化：
```cpp
#if SK_ASSUME_GL_ES
    #define GR_IS_GR_GL(standard) false  // 编译时常量
    #define SK_DISABLE_GL_INTERFACE 1    // 禁用桌面GL代码
#elif SK_ASSUME_GL
    #define GR_IS_GR_GL_ES(standard) false
    #define SK_DISABLE_GL_ES_INTERFACE 1
#elif SK_ASSUME_WEBGL
    // 禁用 GL 和 GLES 接口
#else
    #define GR_IS_GR_GL(standard) (kGL_GrGLStandard == standard)  // 运行时检查
#endif
```

**优化效果**:
- 编译器可消除死代码分支
- 减小二进制体积（移动端尤其重要）
- 避免运行时分支判断开销

### 间接绘制命令结构布局

`static_assert` 确保结构体无填充，可直接用于 GPU：
- `GrGLDrawArraysIndirectCommand`: 16 字节（4×4 字节整数）
- `GrGLDrawElementsIndirectCommand`: 20 字节（5×4 字节整数）

这些结构体直接映射 OpenGL 规范定义的内存布局，可安全地：
1. 写入缓冲区对象
2. 通过 `glDrawArraysIndirect` 等函数使用

### Sized Format 策略

`GrGLTextureInfo::fFormat` 应使用 sized internal format（如 `GL_RGBA8`）：
- **优先使用**: 如果 GL 上下文支持则直接使用
- **降级方案**: 否则内部回退到 base format（如 `GL_RGBA`）
- **原因**: Sized format 明确指定精度，避免驱动实现差异

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/core/SkRefCnt.h | 智能指针类型（某些衍生类需要） |
| include/gpu/GpuTypes.h | skgpu::Protected 枚举 |
| include/gpu/ganesh/gl/GrGLConfig.h | GL 配置宏 |

### 被依赖的模块

- **GrGLInterface**: 使用类型别名声明函数指针
- **GrGLGpu**: OpenGL GPU 实现使用这些类型与驱动交互
- **GrGLTexture/GrGLRenderTarget**: 使用信息结构体管理资源
- **GrBackendSurface**: 后端无关表面抽象存储 GL 信息

## 设计模式与设计决策

### 1. 避免直接依赖 GL 头文件

通过 typedef 重新定义所有 GL 类型：
- **优点**:
  - 避免平台头文件冲突（不同平台 GL 头文件路径不同）
  - 加快编译速度（不解析庞大的 GL 头文件）
  - 方便单元测试（可 mock 所有类型）
- **代价**:
  - 需要手动同步类型定义
  - 必须确保 ABI 兼容性

### 2. 编译时多标准支持

通过宏开关支持三种 GL 标准：
- **灵活性**: 单一代码库支持所有平台
- **性能**: 编译时优化消除无用代码
- **维护性**: 条件编译集中在此文件

### 3. 统一的外部资源接口

`GrGLTextureInfo` 和 `GrGLFramebufferInfo` 提供标准化接口：
- 支持与其他 GL 应用共享资源
- 明确所需信息（Target, ID, Format）
- 通过 `operator==` 支持资源去重

### 4. C++14 兼容性考虑

注释指出 "static_asserts must have messages"：
- 因为此文件被 C++14 客户端代码包含
- C++17 之前 `static_assert` 需要消息参数
- 保持向后兼容性

## 性能考量

### 1. 内存对齐与结构体大小

所有结构体成员自然对齐，避免填充：
- `GrGLTextureInfo`: 约 16 字节（取决于指针大小）
- `GrGLFramebufferInfo`: 约 16 字节
- 适合按值传递或嵌入其他结构体

### 2. 编译时优化

`SK_ASSUME_*` 宏配合 `GR_IS_GR_*` 宏：
- 消除运行时标准检查（热路径中常见）
- 减少指令缓存压力
- 示例：
  ```cpp
  if (GR_IS_GR_GL_ES(standard)) {  // 在 SK_ASSUME_GL_ES 时为 true
      // 仅 GLES 代码
  }
  ```

### 3. 间接绘制优化

间接绘制命令结构减少 CPU-GPU 通信：
- 批量提交多个绘制调用
- 支持 GPU 驱动的渲染（compute shader 生成绘制命令）
- 适用于大型场景渲染

## 平台相关说明

### Windows 64位
`GrGLintptr` 和 `GrGLsizeiptr` 使用 `long long int`：
- 因为 Windows 64位 ABI 中 `long` 仍是 32 位
- 需要 64 位类型表示指针大小的偏移和大小

### 移动平台（OpenGL ES）
- 使用 `SK_ASSUME_GL_ES` 排除桌面 GL 代码
- `fBaseInstance` 字段需要 `EXT_base_instance` 扩展支持
- 压缩纹理格式（ETC, BC1）常用于减少内存

### WebGL
- 使用 `SK_ASSUME_WEBGL` 排除原生 GL/GLES 代码
- 通过 Emscripten 编译到 WebAssembly
- 某些扩展支持受浏览器限制

### Apple 平台
macOS 和 iOS 使用 Core OpenGL/OpenGL ES 框架：
- 已弃用但仍可用
- 新应用推荐使用 Metal 后端

## 相关文件

| 文件 | 关系 |
|------|------|
| include/gpu/ganesh/gl/GrGLInterface.h | 定义 GL 函数指针接口，使用本文件的类型 |
| include/gpu/ganesh/gl/GrGLConfig.h | 提供 GL 配置宏 |
| src/gpu/ganesh/gl/GrGLGpu.h | GL GPU 实现，使用这些类型与驱动交互 |
| src/gpu/ganesh/gl/GrGLUtil.h | GL 工具函数，依赖这些类型定义 |
| include/gpu/GpuTypes.h | 定义跨后端通用类型（如 Protected） |
| src/gpu/ganesh/GrBackendSurface.h | 使用 GrGLTextureInfo 存储 GL 纹理信息 |
