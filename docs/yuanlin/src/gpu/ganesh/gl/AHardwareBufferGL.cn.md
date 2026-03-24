# AHardwareBufferGL

> 源文件
> - src/gpu/ganesh/gl/AHardwareBufferGL.cpp

## 概述

`AHardwareBufferGL.cpp` 实现了 Android 平台上 `AHardwareBuffer` 与 OpenGL ES 的互操作功能。该文件属于 Skia Ganesh 渲染引擎的 Android 特定代码，允许 Skia 直接使用 Android 系统提供的硬件缓冲区作为 OpenGL 纹理，从而实现零拷贝的高效图像共享。该实现仅在 Android API 26（Android 8.0）及以上版本编译。

## 架构位置

该文件位于 Ganesh OpenGL 后端的 Android 平台扩展层：

```
src/gpu/ganesh/
├── gl/
│   └── AHardwareBufferGL.cpp (Android HardwareBuffer 支持)
└── GrDirectContext (使用 AHardwareBuffer)

include/android/
└── GrAHardwareBufferUtils.h (公共接口)
```

该文件实现了 `GrAHardwareBufferUtils` 命名空间中的 OpenGL 特定函数。

## 主要类与结构体

### GLTextureHelper

**功能**：管理 OpenGL 纹理和 EGL 图像的生命周期

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTexID` | `GrGLuint` | OpenGL 纹理对象 ID |
| `fImage` | `EGLImageKHR` | EGL 图像对象（持有 AHardwareBuffer 引用） |
| `fDisplay` | `EGLDisplay` | EGL 显示连接 |
| `fTexTarget` | `GrGLuint` | 纹理目标（`GL_TEXTURE_2D` 或 `GL_TEXTURE_EXTERNAL_OES`） |

**方法：**
- `rebind(GrDirectContext*)`：重新绑定纹理到 EGL 图像
- `~GLTextureHelper()`：析构时清理 OpenGL 和 EGL 资源

## 公共 API 函数

### GetGLBackendFormat

```cpp
GrBackendFormat GetGLBackendFormat(GrDirectContext* dContext,
                                   uint32_t bufferFormat,
                                   bool requireKnownFormat)
```

**功能**：将 Android `AHardwareBuffer` 格式映射到 OpenGL 后端格式

**参数：**
- `dContext`：Direct Context（必须是 OpenGL 后端）
- `bufferFormat`：Android 硬件缓冲区格式（如 `AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM`）
- `requireKnownFormat`：是否要求已知格式，否则返回外部纹理格式

**返回值：**
- 成功：对应的 `GrBackendFormat`
- 失败：无效的 `GrBackendFormat`

**支持的格式映射：**

| AHardwareBuffer 格式 | OpenGL 格式 | API 级别 |
|---------------------|------------|---------|
| `R8G8B8A8_UNORM` | `GL_RGBA8` | 26+ |
| `R8G8B8X8_UNORM` | 外部纹理 | 26+ |
| `R16G16B16A16_FLOAT` | `GL_RGBA16F` | 26+ |
| `R5G6B5_UNORM` | `GL_RGB565` | 26+ |
| `R10G10B10A2_UNORM` | `GL_RGB10_A2` | 26+ |
| `R8G8B8_UNORM` | `GL_RGB8` | 26+ |
| `R8_UNORM` | `GL_R8` | 33+ |
| `R10G10B10A10_UNORM` | 外部纹理 | 34+ |
| 未知格式 | 外部纹理（如果允许） | - |

### MakeGLBackendTexture

```cpp
GrBackendTexture MakeGLBackendTexture(GrDirectContext* dContext,
                                      AHardwareBuffer* hardwareBuffer,
                                      int width, int height,
                                      DeleteImageProc* deleteProc,
                                      UpdateImageProc* updateProc,
                                      TexImageCtx* imageCtx,
                                      bool isProtectedContent,
                                      const GrBackendFormat& backendFormat,
                                      bool isRenderable)
```

**功能**：从 `AHardwareBuffer` 创建 OpenGL 后端纹理

**参数：**
- `dContext`：必须是 OpenGL 后端的 Direct Context
- `hardwareBuffer`：Android 硬件缓冲区指针
- `width`, `height`：纹理尺寸
- `deleteProc`：返回的删除回调函数指针
- `updateProc`：返回的更新回调函数指针
- `imageCtx`：返回的上下文对象（`GLTextureHelper`）
- `isProtectedContent`：是否为受保护内容
- `backendFormat`：后端格式
- `isRenderable`：是否需要可渲染

**返回值：**
- 成功：有效的 `GrBackendTexture`
- 失败：无效的 `GrBackendTexture`

**回调函数：**
- `delete_gl_texture(void* context)`：清理 OpenGL 资源
- `update_gl_texture(void* context, GrDirectContext*)`：重新绑定纹理

## 内部实现细节

### EGL 图像创建流程

`make_gl_backend_texture` 实现步骤：

1. **清理 GL 错误状态**：
   ```cpp
   while (GL_NO_ERROR != glGetError()) {}
   ```

2. **检查纹理类型**：
   ```cpp
   auto textureType = backendFormat.textureType();
   if (textureType != GrTextureType::k2D && textureType != GrTextureType::kExternal) {
       return GrBackendTexture();  // 只支持 2D 和外部纹理
   }
   ```

3. **获取 EGL 客户端缓冲区**：
   ```cpp
   EGLClientBuffer clientBuffer = eglGetNativeClientBufferANDROID(hardwareBuffer);
   ```

4. **创建 EGL 图像**：
   ```cpp
   EGLint attribs[] = {
       EGL_IMAGE_PRESERVED_KHR, EGL_TRUE,
       isProtectedContent ? EGL_PROTECTED_CONTENT_EXT : EGL_NONE,
       isProtectedContent ? EGL_TRUE : EGL_NONE,
       EGL_NONE
   };
   EGLImageKHR image = eglCreateImageKHR(display, EGL_NO_CONTEXT,
                                         EGL_NATIVE_BUFFER_ANDROID,
                                         clientBuffer, attribs);
   ```

5. **生成并绑定 OpenGL 纹理**：
   ```cpp
   GrGLuint texID;
   glGenTextures(1, &texID);
   GrGLuint target = (textureType == GrTextureType::kExternal)
                     ? GR_GL_TEXTURE_EXTERNAL : GR_GL_TEXTURE_2D;
   glBindTexture(target, texID);
   ```

6. **关联纹理与 EGL 图像**：
   ```cpp
   glEGLImageTargetTexture2DOES(target, image);
   ```

7. **创建 Helper 对象和回调**：
   ```cpp
   *deleteProc = delete_gl_texture;
   *updateProc = update_gl_texture;
   *imageCtx = new GLTextureHelper(texID, image, display, target);
   ```

### 受保护内容支持检测

```cpp
static bool can_import_protected_content_eglimpl() {
    EGLDisplay dpy = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    const char* exts = eglQueryString(dpy, EGL_EXTENSIONS);
    // 检查 "EGL_EXT_protected_content" 是否存在
    // 支持四种位置：单独出现、开头、结尾、中间
}
```

使用静态变量缓存查询结果：
```cpp
static bool can_import_protected_content(GrDirectContext* dContext) {
    static bool hasIt = can_import_protected_content_eglimpl();
    return hasIt;
}
```

### RenderDoc 兼容性处理

针对 RenderDoc fork 的特殊处理：
```cpp
if (!dContext->priv().caps()->shaderCaps()->fExternalTextureSupport &&
    textureType == GrTextureType::kExternal) {
    // RenderDoc 支持 OES_EGL_image 但不支持 OES_EGL_image_external
    target = GR_GL_TEXTURE_2D;
}
```

### GLTextureHelper 更新机制

`rebind` 方法用于重新建立纹理-图像关联：
```cpp
void GLTextureHelper::rebind(GrDirectContext* dContext) {
    glBindTexture(fTexTarget, fTexID);
    glEGLImageTargetTexture2DOES(fTexTarget, fImage);
    dContext->resetContext(kTextureBinding_GrGLBackendState);
}
```

**应用场景**：当底层 `AHardwareBuffer` 内容更新时调用

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrDirectContext` | GPU 上下文管理 |
| `GrBackendSurface` | 后端表面抽象 |
| `GrGLBackendSurface` | OpenGL 后端表面创建 |
| `GrGLTypes` | OpenGL 类型定义 |
| `GrGLDefines` | OpenGL 常量定义 |
| `GrGLUtil` | OpenGL 工具函数 |
| `EGL` | EGL 图像创建和管理 |
| `Android NDK` | `AHardwareBuffer` API |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `SkImage_Ganesh` | 从 AHardwareBuffer 创建 Skia 图像 |
| `GrDirectContext` | 通过 `makeFromAHardwareBuffer` 使用 |
| `GrGLGpu` | 管理从 AHardwareBuffer 创建的纹理 |

## 设计模式与设计决策

### RAII 资源管理

`GLTextureHelper` 使用 RAII 模式：
- 构造时持有 OpenGL 纹理和 EGL 图像
- 析构时自动调用 `glDeleteTextures` 和 `eglDestroyImageKHR`
- 确保资源不泄漏，即使发生异常

### 回调函数模式

使用 C 风格回调而非虚函数：
- `DeleteImageProc`：用于清理资源
- `UpdateImageProc`：用于重新绑定
- 便于跨模块边界传递（C ABI 兼容）

### 单例模式

受保护内容支持检测使用静态变量缓存：
- 避免重复查询 EGL 扩展
- 首次调用时初始化（懒加载）
- 线程安全（C++11 静态局部变量初始化保证）

### 格式映射策略

对于未知格式：
- `requireKnownFormat = true`：返回无效格式（严格模式）
- `requireKnownFormat = false`：返回外部纹理格式（兼容模式）

### 纹理目标适配

根据格式和能力选择目标：
- **标准情况**：`GrTextureType::k2D` → `GL_TEXTURE_2D`
- **外部纹理**：`GrTextureType::kExternal` → `GL_TEXTURE_EXTERNAL_OES`
- **RenderDoc 模式**：强制使用 `GL_TEXTURE_2D`

## 性能考量

### 零拷贝纹理共享

通过 EGL 图像扩展实现零拷贝：
- `AHardwareBuffer` 直接映射到 OpenGL 纹理
- 避免 CPU 侧内存拷贝
- 支持跨进程共享（如相机预览到 GPU）

### 图像保留标志

使用 `EGL_IMAGE_PRESERVED_KHR`：
- 确保图像内容在 EGL 图像创建后保留
- 避免内容丢失，但可能增加内存开销

### 受保护内容路径

受保护内容支持检测仅执行一次：
- 使用静态变量缓存结果
- 后续调用直接返回缓存值
- 避免重复的字符串查找

### RenderDoc 优化

检测并适配 RenderDoc 工具：
- 允许在调试环境下使用 `GL_TEXTURE_2D` 替代外部纹理
- 牺牲一些兼容性换取调试能力

### 错误处理开销

在关键路径前清理 GL 错误：
```cpp
while (GL_NO_ERROR != glGetError()) {}
```
确保后续错误检测准确，避免误判。

## Android API 级别支持

| API 级别 | Android 版本 | 新增特性 |
|---------|-------------|---------|
| 26 | Android 8.0 | 基础 AHardwareBuffer 支持 |
| 33 | Android 13 | `R8_UNORM` 格式支持 |
| 34 | Android 14 | `R10G10B10A10_UNORM` 格式支持 |

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `GrAHardwareBufferUtils.h` | 公共接口 | 跨平台 AHardwareBuffer 工具函数 |
| `GrDirectContext.h/cpp` | 使用者 | 创建 AHardwareBuffer 图像 |
| `GrGLGpu.h/cpp` | 管理者 | 管理 OpenGL 纹理资源 |
| `GrGLBackendSurface.h` | 工具 | OpenGL 后端表面工具 |
| `SkImage_Ganesh.cpp` | 使用者 | 从 AHardwareBuffer 创建 SkImage |
| `GrGLDefines.h` | 常量 | OpenGL 常量定义 |
| `GrGLUtil.h` | 工具 | OpenGL 工具函数 |
