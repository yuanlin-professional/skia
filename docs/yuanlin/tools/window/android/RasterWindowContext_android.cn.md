# RasterWindowContext_android

> 源文件: tools/window/android/RasterWindowContext_android.cpp

## 概述

`RasterWindowContext_android` 是 Skia 在 Android 平台上的软件光栅化窗口上下文实现。该文件提供了不依赖 GPU 硬件加速的纯 CPU 软件渲染能力，通过直接操作 Android 原生窗口的像素缓冲区来绘制图形内容。

该实现是最轻量级的渲染方案，适用于不支持 GPU 加速的设备、调试场景、或需要像素精确控制的特殊应用。虽然性能不如硬件加速方案，但提供了最高的兼容性和可预测性。

## 架构位置

该文件位于 Skia 工具层的 Android 平台窗口实现中：

```
skia/
  tools/
    window/
      android/
        RasterWindowContext_android.cpp     # 本文件
        WindowContextFactory_android.h      # Android 窗口工厂
      RasterWindowContext.h                 # 软件渲染基类
      DisplayParams.h                       # 显示参数配置
  include/
    core/
      SkSurface.h                           # Surface 接口
      SkTypes.h                             # 核心类型定义
```

在 Skia 架构层次：
- **平台层**: 直接与 Android NDK 的 ANativeWindow 像素缓冲区交互
- **窗口系统层**: 实现跨平台窗口上下文接口
- **渲染层**: 使用 Skia CPU 渲染器（不涉及 GPU）

## 主要类与结构体

### RasterWindowContext_android

继承自 `skwindow::internal::RasterWindowContext` 的 Android 平台实现类。

**核心成员变量**:
```cpp
sk_sp<SkSurface> fBackbufferSurface;  // 后缓冲 Surface（包装窗口像素）
ANativeWindow* fNativeWindow;         // Android 原生窗口句柄
ANativeWindow_Buffer fBuffer;         // 窗口像素缓冲区
ARect fBounds;                        // 窗口边界矩形
```

**核心方法**:
- `RasterWindowContext_android()`: 构造函数，初始化窗口参数
- `getBackbufferSurface()`: 获取后缓冲 Surface，延迟锁定窗口
- `isValid()`: 检查窗口是否有效
- `resize(int w, int h)`: 调整窗口尺寸
- `setDisplayParams()`: 更新显示参数
- `setBuffersGeometry()`: 配置窗口缓冲区格式和尺寸
- `onSwapBuffers()`: 解锁并提交后缓冲到屏幕

## 公共 API 函数

### MakeRasterForAndroid

```cpp
std::unique_ptr<WindowContext> MakeRasterForAndroid(
    ANativeWindow* window,
    std::unique_ptr<const DisplayParams> params)
```

**功能**: 创建 Android 平台的软件光栅化窗口上下文。

**参数**:
- `window`: Android 原生窗口指针
- `params`: 显示参数配置（主要使用颜色类型和色彩空间）

**返回值**:
- 成功返回有效的 `WindowContext` 智能指针
- 失败返回 `nullptr`

**使用场景**:
- 不支持 GPU 的设备
- 调试和测试
- 需要精确像素控制的场景
- 低功耗模式

## 内部实现细节

### 构造函数流程

```cpp
RasterWindowContext_android::RasterWindowContext_android(
        ANativeWindow* window, std::unique_ptr<const DisplayParams> params)
        : RasterWindowContext(std::move(params)) {
    fNativeWindow = window;
    fWidth = ANativeWindow_getWidth(fNativeWindow);
    fHeight = ANativeWindow_getHeight(fNativeWindow);
    this->setBuffersGeometry();
}
```

1. 保存窗口句柄
2. 获取窗口尺寸
3. 配置缓冲区格式

### 缓冲区格式配置

```cpp
void RasterWindowContext_android::setBuffersGeometry() {
    int32_t format = 0;
    switch (fDisplayParams->colorType()) {
        case kRGBA_8888_SkColorType:
            format = WINDOW_FORMAT_RGBA_8888;
            break;
        case kRGB_565_SkColorType:
            format = WINDOW_FORMAT_RGB_565;
            break;
        default:
            SK_ABORT("Unsupported Android color type");
    }
    ANativeWindow_setBuffersGeometry(fNativeWindow, fWidth, fHeight, format);
}
```

**支持的格式**:
- `RGBA_8888`: 32 位真彩色，8 位 Alpha（标准格式）
- `RGB_565`: 16 位高彩色，无 Alpha（性能优化格式）

### 延迟锁定策略

```cpp
sk_sp<SkSurface> RasterWindowContext_android::getBackbufferSurface() {
    if (nullptr == fBackbufferSurface) {
        ANativeWindow_lock(fNativeWindow, &fBuffer, &fBounds);
        const int bytePerPixel = fBuffer.format == WINDOW_FORMAT_RGB_565 ? 2 : 4;
        SkImageInfo info = SkImageInfo::Make(fWidth, fHeight,
                                             fDisplayParams->colorType(),
                                             kPremul_SkAlphaType,
                                             fDisplayParams->colorSpace());
        fBackbufferSurface = SkSurfaces::WrapPixels(info, fBuffer.bits,
                                                     fBuffer.stride * bytePerPixel,
                                                     nullptr);
    }
    return fBackbufferSurface;
}
```

**关键设计**:
- **延迟锁定**: 仅在第一次获取 Surface 时锁定窗口
- **包装像素**: 使用 `SkSurfaces::WrapPixels` 直接包装窗口内存
- **零拷贝**: 直接在窗口缓冲区中渲染
- **步幅计算**: 根据格式计算每行字节数

### 缓冲区交换

```cpp
void RasterWindowContext_android::onSwapBuffers() {
    ANativeWindow_unlockAndPost(fNativeWindow);
    fBackbufferSurface.reset(nullptr);
}
```

**关键操作**:
1. 解锁窗口并提交后缓冲到屏幕（等价于缓冲区交换）
2. 重置 Surface 指针，强制下一帧重新锁定

### 尺寸调整

```cpp
void RasterWindowContext_android::resize(int w, int h) {
    fWidth = w;
    fHeight = h;
    this->setBuffersGeometry();
}
```

更新尺寸并重新配置缓冲区格式。

### 显示参数更新

```cpp
void RasterWindowContext_android::setDisplayParams(std::unique_ptr<const DisplayParams> params) {
    fDisplayParams = std::move(params);
    this->setBuffersGeometry();
}
```

更新参数（如颜色类型、色彩空间）并重新配置缓冲区。

## 依赖关系

**直接依赖**:
- `include/core/SkSurface.h`: Skia Surface 接口
- `include/core/SkTypes.h`: 核心类型定义
- `tools/window/DisplayParams.h`: 显示参数配置
- `tools/window/RasterWindowContext.h`: 软件渲染基类
- `tools/window/android/WindowContextFactory_android.h`: Android 工厂
- Android NDK: `ANativeWindow` API

**间接依赖**:
- Skia CPU 渲染器
- `SkImageInfo`: 图像信息描述
- `SkColorSpace`: 色彩空间管理

**依赖图**:
```
Android App
    ↓
MakeRasterForAndroid
    ↓
RasterWindowContext_android
    ↓
ANativeWindow_lock → 窗口像素缓冲区
    ↓
SkSurfaces::WrapPixels → SkSurface
    ↓
Skia CPU 渲染器 → CPU
```

## 设计模式与设计决策

### 设计模式

1. **工厂模式**: `MakeRasterForAndroid` 封装创建逻辑
2. **延迟初始化**: Surface 在首次使用时创建
3. **RAII 模式**: Surface 通过智能指针管理
4. **包装器模式**: 包装窗口像素为 SkSurface

### 设计决策

**1. 延迟锁定窗口**:
- 仅在实际渲染时锁定，减少锁定时间
- 避免长时间持有窗口锁

**2. 每帧重新锁定**:
```cpp
fBackbufferSurface.reset(nullptr);  // 强制下一帧重新锁定
```
- 确保每帧获得最新的窗口缓冲区
- 支持窗口系统的缓冲区轮换

**3. 零拷贝渲染**:
- 直接在窗口缓冲区绘制，无中间缓冲
- 最小化内存占用和拷贝开销

**4. 格式灵活性**:
- 支持 RGBA8888（质量）和 RGB565（性能）
- 通过 `setBuffersGeometry` 动态配置

**5. 有效性检查**:
```cpp
bool isValid() override { return SkToBool(fNativeWindow); }
```
- 简单但足够：窗口非空即有效

**6. 预乘 Alpha**:
```cpp
kPremul_SkAlphaType
```
- 使用预乘 Alpha 格式，与 Android 默认格式一致

### 与硬件加速方案对比

| 特性 | Raster | OpenGL ES | Vulkan |
|------|--------|-----------|--------|
| GPU 需求 | 无 | 需要 | 需要 |
| 性能 | 低 | 高 | 极高 |
| 功耗 | 低 | 中 | 中高 |
| 兼容性 | 100% | >95% | >80% |
| 复杂度 | 最低 | 中等 | 高 |

## 性能考量

### 优化策略

1. **零拷贝架构**: 直接在窗口缓冲区渲染
2. **延迟锁定**: 减少窗口锁定时间
3. **格式选择**: RGB565 比 RGBA8888 快约 2 倍（但失去 Alpha）
4. **步幅对齐**: 使用 `fBuffer.stride` 确保正确的内存对齐

### 性能特征

- **初始化时间**: 极快（无 GPU 初始化）
- **帧率**: 低到中等（取决于分辨率和 CPU 性能）
- **内存占用**: 极低（仅窗口缓冲区，无 GPU 资源）
- **功耗**: 低（CPU 渲染，无 GPU 功耗）

### 性能瓶颈

1. **CPU 填充率**: 大分辨率下软件渲染很慢
2. **内存带宽**: 频繁写入内存受带宽限制
3. **缓存效率**: 大尺寸 Surface 易导致缓存失效

### 性能对比

| 分辨率 | RGBA8888 FPS | RGB565 FPS |
|--------|-------------|-----------|
| 720p | ~20-30 | ~40-60 |
| 1080p | ~10-15 | ~20-30 |
| 1440p | ~5-10 | ~10-15 |

（估算值，实际取决于 CPU 性能和渲染内容复杂度）

### 适用场景

**适合**:
- 低端设备（无 GPU）
- 调试和测试
- 简单 UI（低分辨率）
- 低功耗需求
- 像素精确控制

**不适合**:
- 高分辨率游戏
- 复杂动画
- 实时视频处理
- 高帧率需求

## 相关文件

### 同目录文件
- `tools/window/android/GLWindowContext_android.cpp`: OpenGL ES 实现
- `tools/window/android/VulkanWindowContext_android.cpp`: Ganesh Vulkan 实现
- `tools/window/android/GraphiteVulkanWindowContext_android.cpp`: Graphite Vulkan 实现
- `tools/window/android/GraphiteDawnWindowContext_android.cpp`: Graphite Dawn 实现
- `tools/window/android/WindowContextFactory_android.h`: Android 窗口工厂

### 基类与工具
- `tools/window/RasterWindowContext.h`: 软件渲染基类
- `tools/window/DisplayParams.h`: 显示参数配置
- `tools/window/WindowContext.h`: 窗口上下文接口

### 核心 Skia 接口
- `include/core/SkSurface.h`: Surface 接口
- `include/core/SkCanvas.h`: 绘图画布
- `include/core/SkImageInfo.h`: 图像信息
- `include/core/SkColorSpace.h`: 色彩空间

### 其他平台 Raster 实现
- `tools/window/mac/RasterWindowContext_mac.mm`: macOS 实现
- `tools/window/win/RasterWindowContext_win.cpp`: Windows 实现
- `tools/window/unix/RasterWindowContext_unix.cpp`: Linux 实现

### Android NDK 相关
- `<android/native_window_jni.h>`: ANativeWindow API
- Android 系统框架的 Surface 实现
