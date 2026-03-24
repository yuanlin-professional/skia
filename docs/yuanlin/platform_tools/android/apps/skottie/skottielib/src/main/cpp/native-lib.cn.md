# Skottie Android JNI 原生库

> 源文件: `platform_tools/android/apps/skottie/skottielib/src/main/cpp/native-lib.cpp`

## 概述

此文件实现了 Skottie（Skia 的 Lottie 动画渲染器）在 Android 平台上的 JNI（Java Native Interface）桥接层。它将 Skottie 动画引擎的核心功能暴露给 Java/Kotlin 层，实现了 Bodymovin/Lottie 动画在 Android 上通过 GPU 加速渲染的完整链路。

## 架构位置

位于 Android 应用层 (`platform_tools/android/apps/skottie/`)，是 Skottie Android SDK 的原生组件。在架构中处于 Java 应用层和 Skia C++ 渲染引擎之间的桥接位置。

## 主要类与结构体

### `SkottieRunner`
- 持有 `GrDirectContext` 的智能指针，代表一个 GPU 渲染上下文
- 作为全局渲染管理器，可被多个动画实例共享

### `SkottieAnimation`
- `mRunner` - 指向 SkottieRunner 的原始指针
- `mStream` - 动画数据流
- `mAnimation` - Skottie 动画对象 (`sk_sp<skottie::Animation>`)
- `mTimeBase` - 时间基准（用于动画播放控制）
- `mDuration` - 动画总时长（毫秒）

## 公共 API 函数

### Runner 管理
- `Java_org_skia_skottie_SkottieRunner_nCreateProxy` - 创建 OpenGL ES 上下文和 GrDirectContext
- `Java_org_skia_skottie_SkottieRunner_nDeleteProxy` - 释放 GPU 资源并销毁 Runner
- `Java_org_skia_skottie_SkottieRunner_nSetMaxCacheSize` - 设置 GPU 资源缓存上限

### Animation 管理
- `Java_org_skia_skottie_SkottieAnimation_nCreateProxy` - 从 Java DirectByteBuffer 解析并创建 Skottie 动画
- `Java_org_skia_skottie_SkottieAnimation_nDeleteProxy` - 销毁动画对象
- `Java_org_skia_skottie_SkottieAnimation_nDrawFrame` - 在当前 OpenGL 帧缓冲区上渲染指定进度的动画帧
- `Java_org_skia_skottie_SkottieAnimation_nGetDuration` - 获取动画时长

## 内部实现细节

- 使用 `GrGLInterfaces::MakeEGL()` 创建 EGL 接口，适配 Android 的 OpenGL ES 环境
- 通过 `GrContextOptions::fDisableDistanceFieldPaths = true` 禁用距离场路径以优化移动端性能
- `release_global_jni_ref` 回调函数用于在 SkData 释放时清理 JNI 全局引用，避免内存泄漏
- 使用 `SkData::MakeWithProc` 实现零拷贝数据传递，直接使用 Java DirectByteBuffer 的内存
- 支持宽色域渲染：当 `wideColorGamut` 为 true 时使用 `GL_RGBA16F` 和 `kRGBA_F16_SkColorType`
- 动画构建使用 `DataURIResourceProviderProxy` 仅支持 base64 编码的图片和字体资源
- 通过 `sksg::InvalidationController` 实现增量渲染：仅在动画内容发生变化时重绘
- 注册了 PNG、GIF、JPEG 解码器用于处理动画中嵌入的图片资源
- 使用 HarfBuzz 进行文本塑形

## 依赖关系

- Skia 核心库：`SkCanvas`, `SkSurface`, `SkBitmap`, `SkColorSpace` 等
- Ganesh GPU 后端：`GrDirectContext`, `GrBackendSurface`, `GrGLInterface`
- EGL 集成：`GrGLMakeEGLInterface`
- Skottie 模块：`skottie::Animation`
- SkResources 模块：`DataURIResourceProviderProxy`
- SkSG 模块：`InvalidationController`
- 图像编解码器：`SkCodec`, `SkPngDecoder`, `SkGifDecoder`, `SkJpegDecoder`
- JNI：`<jni.h>`
- OpenGL ES：`<GLES2/gl2.h>`, `<GLES3/gl3.h>`

## 设计模式与设计决策

- **代理模式（Proxy Pattern）**：Java 层的 SkottieRunner 和 SkottieAnimation 通过 `nativeProxy`（jlong 类型的指针）引用原生对象
- **零拷贝设计**：通过 JNI DirectByteBuffer 和 SkData::MakeWithProc 避免数据复制
- **JNI 全局引用管理**：使用回调机制确保 Java 对象在原生数据使用期间保持存活
- **分离创建与渲染**：Runner（上下文）和 Animation（动画）分离，允许多动画共享同一 GPU 上下文

## 性能考量

- 使用 `GrSyncCpu::kNo`（隐式）进行异步 GPU 提交
- 通过 `InvalidationController` 避免不必要的重绘
- 使用 stencil buffer (8位) 支持复杂路径裁剪
- 缓存大小可通过 `nSetMaxCacheSize` 动态调整以适配不同设备的内存约束
- `fDisableDistanceFieldPaths` 关闭距离场路径渲染以降低 GPU 负载

## 相关文件

- `modules/skottie/include/Skottie.h`
- `modules/skresources/include/SkResources.h`
- `modules/sksg/include/SkSGInvalidationController.h`
- `include/gpu/ganesh/GrDirectContext.h`
