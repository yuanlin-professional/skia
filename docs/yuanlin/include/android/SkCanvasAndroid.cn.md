# SkCanvasAndroid

> 源文件: `include/android/SkCanvasAndroid.h`

## 概述

SkCanvasAndroid 提供了 Android 平台特定的 SkCanvas 扩展功能,用于访问 Canvas 的顶层绘制表面信息。该模块是 Android Framework 与 Skia 深度集成的接口,允许 Android 系统获取底层渲染目标的详细信息,支持高级图形功能如硬件加速、窗口合成等。

## 架构位置

该模块位于 Skia 的 Android 平台适配层,专门为 Android Framework(特别是 libhwui 硬件加速渲染库)设计。它通过 `skgpu::ganesh` 命名空间暴露 GPU 后端的内部信息,是 Android 系统图形栈与 Skia GPU 层的桥梁。

## 命名空间

模块使用 `skgpu::ganesh` 命名空间,表明这些功能专属于 Skia 的 Ganesh GPU 后端。

```cpp
namespace skgpu::ganesh {
    // Android 特定扩展
}
```

**命名空间说明**:
- `skgpu`: Skia GPU 功能的根命名空间
- `ganesh`: Skia 的传统 GPU 后端(相对于新的 Graphite 后端)

## 核心函数

### `TopLayerBounds`

获取 Canvas 顶层绘制表面的边界矩形。

```cpp
SkIRect TopLayerBounds(const SkCanvas* canvas)
```

**参数**:
- `canvas`: 目标画布指针

**返回值**:
- `SkIRect`: 顶层表面的边界矩形(整数坐标)

**功能说明**:
- 返回当前 Canvas 最上层渲染目标的像素边界
- 对于多层 Canvas(如包含 saveLayer 的场景),仅返回最顶层信息
- 坐标为设备坐标系(未经过变换矩阵)

**典型用途**:
```cpp
SkIRect bounds = skgpu::ganesh::TopLayerBounds(canvas);
// bounds = {x: 0, y: 0, width: 1920, height: 1080}
// 可用于裁剪、区域检测等
```

**使用场景**:
- Android SurfaceFlinger 需要知道渲染区域进行窗口合成
- 确定脏区域(Dirty Region)优化重绘
- 硬件覆盖层(Hardware Overlay)的放置决策

### `TopLayerBackendRenderTarget`

获取 Canvas 顶层表面的后端渲染目标。

```cpp
GrBackendRenderTarget TopLayerBackendRenderTarget(const SkCanvas* canvas)
```

**参数**:
- `canvas`: 目标画布指针

**返回值**:
- `GrBackendRenderTarget`: GPU 后端渲染目标对象

**功能说明**:
- 返回底层 GPU 渲染目标的句柄和元数据
- 包含 OpenGL FBO ID、Vulkan Image Handle 等后端特定信息
- 允许外部代码直接操作底层 GPU 资源

**后端渲染目标包含的信息**:
- **OpenGL**: Framebuffer Object ID, 格式, 采样数
- **Vulkan**: VkImage, VkImageLayout, VkFormat
- **Metal**: MTLTexture 引用

**安全性警告**:
- 此函数暴露底层 GPU 资源,使用不当可能破坏 Skia 状态
- 仅供 Android Framework 等受信任代码使用
- 一般应用开发不应直接调用

**典型用途**:
```cpp
GrBackendRenderTarget rt = skgpu::ganesh::TopLayerBackendRenderTarget(canvas);

#ifdef SK_VULKAN
    GrVkImageInfo vkInfo;
    if (rt.getVkImageInfo(&vkInfo)) {
        VkImage image = vkInfo.fImage;
        // 可直接使用 Vulkan Image 进行操作
        // 例如:传递给视频编码器、执行自定义 Compute Shader 等
    }
#endif

#ifdef SK_GL
    GrGLFramebufferInfo glInfo;
    if (rt.getGLFramebufferInfo(&glInfo)) {
        GLuint fbo = glInfo.fFBOID;
        // 可使用 OpenGL FBO ID
    }
#endif
```

**使用场景**:
- Android MediaCodec 需要访问渲染表面进行视频编码
- 自定义 GPU 计算(如机器学习推理)需要访问渲染结果
- 与第三方图形库(如 Unity、Unreal Engine)集成

## 内部实现细节

### Canvas 层级结构
SkCanvas 可能包含多层渲染目标:
```
SkCanvas
├── Base Layer (窗口表面)
└── saveLayer 1 (离屏缓冲)
    └── saveLayer 2 (嵌套离屏缓冲)
```

`TopLayerBounds` 和 `TopLayerBackendRenderTarget` 始终返回当前激活的最顶层信息。

### GPU 设备获取
函数内部通过以下步骤获取 GPU 信息:
```cpp
// 简化的内部逻辑
SkBaseDevice* device = canvas->topDevice();
GrRenderTargetProxy* rtProxy = device->asGpuRenderTargetProxy();
GrRenderTarget* rt = rtProxy->peekRenderTarget();
return rt->getBackendRenderTarget();
```

### 非 GPU Canvas 的处理
如果 Canvas 不是 GPU 加速(如纯 CPU 栅格化):
- `TopLayerBounds` 返回空矩形或 Canvas 设备边界
- `TopLayerBackendRenderTarget` 返回无效的后端目标

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkCanvas | 画布基类 |
| SkIRect | 整数矩形类型 |
| GrBackendRenderTarget | GPU 后端渲染目标抽象 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| Android Framework(libhwui) | 使用这些函数获取渲染表面信息 |
| Android SurfaceFlinger | 窗口合成和显示管理 |
| Android MediaCodec | 视频编码需要访问渲染目标 |

## 设计模式与设计决策

### 命名空间隔离
使用 `skgpu::ganesh` 命名空间而非全局或 `SkCanvasAndroid` 类:
- 明确表达这些功能依赖 GPU 后端
- 避免与 CPU Canvas 的概念混淆
- 为未来的 Graphite 后端预留命名空间(`skgpu::graphite`)

### 只读访问设计
这些函数仅提供信息查询,不修改 Canvas 状态:
- 避免破坏 Skia 内部状态一致性
- 调用者需要自行管理底层资源的使用

### 平台特定性
该头文件仅在 Android 平台有意义:
- 非 Android 平台编译时可能为空实现
- Android Framework 代码可安全包含此头文件

## 性能考量

### 零开销抽象
- 函数调用几乎无开销(通常内联)
- 仅访问已存在的数据结构,无额外计算
- 无内存分配或系统调用

### 缓存建议
```cpp
// 避免在热循环中重复调用
SkIRect bounds = skgpu::ganesh::TopLayerBounds(canvas);
for (int i = 0; i < N; ++i) {
    // 使用缓存的 bounds
    if (objectBounds.intersects(bounds)) {
        // ...
    }
}
```

## 典型使用场景

### 场景 1: SurfaceFlinger 窗口合成
```cpp
// Android SurfaceFlinger 中的伪代码
void compositeWindow(SkCanvas* canvas) {
    // 获取窗口渲染区域
    SkIRect windowBounds = skgpu::ganesh::TopLayerBounds(canvas);

    // 确定是否与其他窗口重叠
    if (overlapsWithOtherWindow(windowBounds)) {
        // 使用 GPU 合成
    } else {
        // 可以使用硬件覆盖层优化
    }
}
```

### 场景 2: 视频编码集成
```cpp
// MediaCodec 编码器使用渲染表面
void encodeFrame(SkCanvas* canvas) {
    GrBackendRenderTarget rt = skgpu::ganesh::TopLayerBackendRenderTarget(canvas);

    #ifdef SK_VULKAN
    GrVkImageInfo vkInfo;
    if (rt.getVkImageInfo(&vkInfo)) {
        // 将 Vulkan Image 传递给视频编码器
        videoEncoder->encodeVulkanImage(vkInfo.fImage);
    }
    #endif
}
```

### 场景 3: 自定义 GPU 后处理
```cpp
// 在渲染完成后应用自定义 Shader
void applyPostProcessing(SkCanvas* canvas) {
    GrBackendRenderTarget rt = skgpu::ganesh::TopLayerBackendRenderTarget(canvas);

    // 使用自定义 Compute Shader 进行后处理
    customGPUFilter->apply(rt);
}
```

## 安全性考虑

### 资源生命周期
```cpp
// 错误示例:保存后端目标引用
GrBackendRenderTarget savedRT = skgpu::ganesh::TopLayerBackendRenderTarget(canvas);
canvas->restore(); // Canvas 层级变化
// savedRT 现在可能指向已销毁的资源!

// 正确示例:即用即取
void processCanvas(SkCanvas* canvas) {
    GrBackendRenderTarget rt = skgpu::ganesh::TopLayerBackendRenderTarget(canvas);
    // 立即使用 rt
    useRenderTarget(rt);
    // 函数结束后不保留引用
}
```

### 状态管理
```cpp
// 如果直接操作后端渲染目标,需要恢复 Skia 状态
GrBackendRenderTarget rt = skgpu::ganesh::TopLayerBackendRenderTarget(canvas);

#ifdef SK_GL
GrGLFramebufferInfo glInfo;
if (rt.getGLFramebufferInfo(&glInfo)) {
    // 保存当前 OpenGL 状态
    GLint oldFBO;
    glGetIntegerv(GL_FRAMEBUFFER_BINDING, &oldFBO);

    // 自定义操作
    glBindFramebuffer(GL_FRAMEBUFFER, glInfo.fFBOID);
    // ... 执行自定义渲染 ...

    // 恢复状态
    glBindFramebuffer(GL_FRAMEBUFFER, oldFBO);

    // 通知 Skia 状态可能已改变
    canvas->flush();
}
#endif
```

## 平台相关说明

### Android 版本支持
- **最低**: Android 4.4(KitKat),引入硬件加速 Canvas
- **推荐**: Android 7.0+,Vulkan 后端支持
- **最新**: Android 12+,优化的 GPU 调度和内存管理

### GPU 后端支持
- **OpenGL ES**: 所有 Android 设备支持
- **Vulkan**: Android 7.0+ 高端设备支持
- **未来**: Skia 的 Graphite 后端将使用 `skgpu::graphite` 命名空间

## 限制与注意事项

### 仅限 GPU Canvas
- 对于 CPU 栅格化的 Canvas,函数行为未定义或返回无效值
- 调用前应确认 Canvas 是 GPU 加速的

### 不支持 saveLayer
```cpp
canvas->saveLayer(nullptr, nullptr);
// TopLayerBounds 现在返回离屏缓冲的边界,而非窗口边界
canvas->restore();
// TopLayerBounds 恢复为窗口边界
```

### 跨进程限制
- 后端渲染目标的句柄(如 VkImage)通常不能跨进程传递
- 需要使用 AHardwareBuffer 等跨进程共享机制

## 相关文件

| 文件 | 关系 |
|------|------|
| include/core/SkCanvas.h | 画布基类定义 |
| include/gpu/GrBackendSurface.h | GrBackendRenderTarget 定义 |
| src/gpu/ganesh/GrRenderTarget.h | GPU 渲染目标实现 |
| frameworks/base/libs/hwui | Android Framework 使用这些 API |

## 最佳实践

### 权限检查
```cpp
// 确认 Canvas 是 GPU 加速的
SkBaseDevice* device = canvas->topDevice();
if (device->asGpuRenderTargetProxy()) {
    // 安全调用 Android 扩展函数
    GrBackendRenderTarget rt = skgpu::ganesh::TopLayerBackendRenderTarget(canvas);
}
```

### 错误处理
```cpp
GrBackendRenderTarget rt = skgpu::ganesh::TopLayerBackendRenderTarget(canvas);
if (!rt.isValid()) {
    // Canvas 不是 GPU 加速或层级栈为空
    return;
}
```

### 线程安全
- 这些函数不是线程安全的
- 必须在拥有 Canvas 的线程中调用
- 与所有 SkCanvas 操作一样,需要外部同步

## 未来展望

### Graphite 后端
Skia 新的 Graphite GPU 后端将提供类似功能:
```cpp
namespace skgpu::graphite {
    SkIRect TopLayerBounds(const SkCanvas*);
    // Graphite 特定的后端目标类型
}
```

### 更丰富的元数据
未来可能扩展返回更多信息:
- 渲染目标的采样数(MSAA)
- 色彩空间信息
- 渲染通道(Render Pass)状态
