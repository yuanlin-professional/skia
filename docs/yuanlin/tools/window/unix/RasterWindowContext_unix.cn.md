# RasterWindowContext_unix

> 源文件
> - tools/window/unix/RasterWindowContext_unix.h
> - tools/window/unix/RasterWindowContext_unix.cpp

## 概述

`RasterWindowContext_unix` 是 Skia 在 Unix/Linux 平台上的软件光栅化窗口上下文实现。不同于 GPU 加速的渲染方案（Ganesh/Graphite + OpenGL/Vulkan/Metal），该模块使用 CPU 进行所有渲染计算，然后通过 Xlib 的 `XPutImage` 将渲染结果传输到 X Window。这是一个纯软件实现，不依赖任何 GPU 硬件或驱动，主要用于测试、调试和不支持 GPU 加速的环境。

软件光栅化渲染器的优势在于跨平台一致性、易于调试以及在没有 GPU 或驱动问题的环境中的可靠性。它是 Skia 功能验证的重要基准，确保渲染逻辑的正确性不受硬件差异影响。

## 架构位置

该模块位于 Skia 工具层的 Unix 平台窗口实现中：

```
skia/
├── tools/
│   └── window/
│       ├── RasterWindowContext.h             # 软件光栅化基类
│       └── unix/
│           ├── RasterWindowContext_unix.h         # 本模块头文件
│           ├── RasterWindowContext_unix.cpp       # 本模块实现
│           ├── GaneshGLWindowContext_unix.cpp     # GPU 实现
│           └── XlibWindowInfo.h              # Xlib 窗口信息
├── include/
│   └── core/
│       ├── SkSurface.h                       # Skia 表面抽象
│       └── SkImageInfo.h                     # 图像信息
└── src/
    └── core/                                 # Skia 核心渲染引擎（CPU）
```

该模块的特点：
- **不依赖 GPU**：纯 CPU 渲染路径
- **跨平台一致**：相同代码路径保证一致性
- **调试友好**：易于追踪和验证渲染逻辑

## 主要类与结构体

### RasterWindowContext_xlib

匿名命名空间内的私有实现类，继承自 `RasterWindowContext`。

**主要成员变量：**
- `sk_sp<SkSurface> fBackbufferSurface`：后缓冲区表面（CPU 内存）
- `Display* fDisplay`：X11 显示连接
- `XWindow fWindow`：X Window 窗口句柄
- `GC fGC`：X11 图形上下文（Graphics Context）

**主要成员函数：**

```cpp
RasterWindowContext_xlib(Display*, XWindow, int width, int height,
                        std::unique_ptr<const DisplayParams>)
```
构造函数，创建 X11 图形上下文并初始化表面。

```cpp
sk_sp<SkSurface> getBackbufferSurface() override
```
返回后缓冲区表面供 Skia 渲染。

```cpp
bool isValid() override
```
检查窗口是否有效。

```cpp
void resize(int w, int h) override
```
处理窗口尺寸变化，重新创建表面。

```cpp
void setDisplayParams(std::unique_ptr<const DisplayParams> params) override
```
更新显示参数并调整表面。

```cpp
void onSwapBuffers() override
```
将渲染结果从后缓冲区传输到 X Window。

### XlibWindowInfo

定义在 `XlibWindowInfo.h` 中：
- `Display* fDisplay`：X11 显示连接
- `Window fWindow`：窗口句柄
- `int fWidth`、`int fHeight`：窗口尺寸

## 公共 API 函数

### MakeRasterForXlib

```cpp
namespace skwindow {
std::unique_ptr<WindowContext> MakeRasterForXlib(
    const XlibWindowInfo& info,
    std::unique_ptr<const DisplayParams> params);
}
```

**功能：** 创建 Unix/Linux 平台的软件光栅化窗口上下文。

**参数：**
- `info`：包含 X Window 信息的结构体
- `params`：显示参数配置（颜色类型、颜色空间等）

**返回值：** 成功返回 `WindowContext` 智能指针，失败返回 `nullptr`

**使用场景：**
- GPU 不可用或驱动有问题的环境
- 渲染结果验证和回归测试
- 调试和性能分析
- 远程 X11 会话

## 内部实现细节

### 构造函数初始化

```cpp
RasterWindowContext_xlib::RasterWindowContext_xlib(Display* display,
                                                   XWindow window,
                                                   int width,
                                                   int height,
                                                   std::unique_ptr<const DisplayParams> params)
        : RasterWindowContext(std::move(params)), fDisplay(display), fWindow(window) {
    fGC = XCreateGC(fDisplay, fWindow, 0, nullptr);
    this->resize(width, height);
    fWidth = width;
    fHeight = height;
}
```

**初始化步骤：**
1. 调用基类构造函数
2. 保存 Display 和 Window 引用
3. 创建 X11 图形上下文（`GC`）
4. 调用 `resize()` 创建后缓冲区表面

### 表面创建与调整

```cpp
void RasterWindowContext_xlib::resize(int w, int h) {
    SkImageInfo info = SkImageInfo::Make(
            w, h,
            fDisplayParams->colorType(),
            kPremul_SkAlphaType,
            fDisplayParams->colorSpace());
    fBackbufferSurface = SkSurfaces::Raster(info, &fDisplayParams->surfaceProps());
}
```

**关键点：**
- 使用 `SkSurfaces::Raster()` 创建 CPU 内存支持的表面
- 根据 `DisplayParams` 配置颜色类型和颜色空间
- Alpha 类型设置为预乘（`kPremul_SkAlphaType`）
- 表面属性包含渲染质量设置

### 缓冲区交换实现

`onSwapBuffers()` 是核心方法，将渲染结果传输到屏幕：

```cpp
void RasterWindowContext_xlib::onSwapBuffers() {
    SkPixmap pm;
    if (!fBackbufferSurface->peekPixels(&pm)) {
        return;
    }

    // 1. 配置 XImage 结构
    int bitsPerPixel = pm.info().bytesPerPixel() * 8;
    XImage image;
    memset(&image, 0, sizeof(image));
    image.width = pm.width();
    image.height = pm.height();
    image.format = ZPixmap;  // 像素图格式
    image.data = (char*) pm.writable_addr();
    image.byte_order = LSBFirst;
    image.bitmap_unit = bitsPerPixel;
    image.bitmap_bit_order = LSBFirst;
    image.bitmap_pad = bitsPerPixel;
    image.depth = 24;
    image.bytes_per_line = pm.rowBytes() - pm.width() * pm.info().bytesPerPixel();
    image.bits_per_pixel = bitsPerPixel;

    // 2. 初始化 XImage
    if (!XInitImage(&image)) {
        return;
    }

    // 3. 传输像素数据到窗口
    XPutImage(fDisplay, fWindow, fGC, &image, 0, 0, 0, 0, pm.width(), pm.height());
}
```

**实现细节：**

1. **获取像素数据**
   - `peekPixels()` 获取表面的像素内存地址
   - 避免像素复制，直接访问内存

2. **配置 XImage**
   - `ZPixmap`：像素图格式，每个像素完整存储
   - `LSBFirst`：小端字节序（x86/x64）
   - `depth = 24`：24 位颜色深度
   - `bytes_per_line`：行间距（可能包含填充）

3. **XPutImage 传输**
   - 将像素数据从客户端内存复制到 X Server
   - 涉及进程间通信（本地 Unix socket 或网络）
   - 这是主要的性能瓶颈

### 显示参数更新

```cpp
void RasterWindowContext_xlib::setDisplayParams(std::unique_ptr<const DisplayParams> params) {
    fDisplayParams = std::move(params);
    XWindowAttributes attrs;
    XGetWindowAttributes(fDisplay, fWindow, &attrs);
    this->resize(attrs.width, attrs.height);
}
```

更新显示参数时，查询当前窗口尺寸并重新创建表面。

## 依赖关系

### 外部依赖

**Skia 核心组件：**
- `SkSurface`：绘图表面抽象
- `SkSurfaces::Raster()`：创建软件表面
- `SkPixmap`：像素内存访问
- `SkImageInfo`：图像格式描述

**平台组件：**
- `RasterWindowContext`：软件光栅化基类
- `XlibWindowInfo`：Xlib 窗口信息

**系统库：**
- `X11`：X Window System
  - `Display`：显示连接
  - `Window`：窗口句柄
  - `GC`：图形上下文
  - `XImage`：图像数据结构
  - `XPutImage()`：像素传输函数
  - `XGetWindowAttributes()`：查询窗口属性

### 被依赖关系

该模块被以下组件使用：
- 测试工具（需要 CPU 渲染路径）
- CI/CD 环境（可能没有 GPU）
- 回归测试（确保一致性）
- 调试工具

## 设计模式与设计决策

### 设计模式

1. **工厂模式**
   - `MakeRasterForXlib()` 创建实例
   - 隐藏实现细节

2. **模板方法模式**
   - 继承 `RasterWindowContext`
   - 实现平台相关的虚函数

### 设计决策

1. **直接内存访问**
   ```cpp
   image.data = (char*) pm.writable_addr();
   ```
   - 避免像素复制
   - 提高性能

2. **ZPixmap 格式**
   - 每个像素完整存储
   - 与 Skia 内存布局兼容
   - 无需格式转换

3. **24 位颜色深度**
   - 标准 RGB 颜色
   - 兼容大多数显示器

4. **LSBFirst 字节序**
   - 匹配 x86/x64 架构
   - 避免字节序转换

5. **GC 资源管理**
   - 构造时创建 `GC`
   - 未显式销毁（依赖析构）
   - 应考虑添加 `XFreeGC()`

## 性能考量

### 优势

1. **无 GPU 依赖**
   - 可在任何环境运行
   - 不受驱动问题影响

2. **确定性渲染**
   - 一致的渲染结果
   - 易于回归测试

3. **零内存复制**
   - 直接访问 SkSurface 内存
   - 避免额外复制

### 劣势

1. **CPU 渲染瓶颈**
   - 所有渲染计算在 CPU 上
   - 无法利用 GPU 并行性
   - 大分辨率下性能低

2. **XPutImage 传输开销**
   - 进程间通信成本
   - 网络 X11 延迟更高
   - 需要序列化像素数据

3. **无硬件加速**
   - 滤镜、混合等操作慢
   - 无法利用专用硬件

### 性能优化

1. **减少传输频率**
   - 仅在需要时调用 `swapBuffers()`
   - 避免不必要的刷新

2. **使用 MIT-SHM 扩展**
   - 共享内存传输（本地 X11）
   - 避免数据复制
   - 需要额外实现

3. **优化渲染尺寸**
   - 使用合适的分辨率
   - 避免过大的后缓冲区

## 相关文件

**同平台其他实现：**
- `tools/window/unix/GaneshGLWindowContext_unix.cpp`：OpenGL GPU 加速
- `tools/window/unix/GaneshVulkanWindowContext_unix.cpp`：Vulkan GPU 加速
- `tools/window/unix/GraphiteNativeVulkanWindowContext_unix.cpp`：Graphite Vulkan
- `tools/window/unix/GraphiteDawnXlibWindowContext_unix.cpp`：Graphite Dawn

**基类和工具：**
- `tools/window/RasterWindowContext.h`：软件光栅化基类
- `tools/window/WindowContext.h`：窗口上下文抽象
- `tools/window/unix/XlibWindowInfo.h`：Xlib 窗口信息

**其他平台软件光栅化：**
- `tools/window/mac/RasterWindowContext_mac.mm`：macOS 实现
- `tools/window/win/RasterWindowContext_win.cpp`：Windows 实现
- `tools/window/android/RasterWindowContext_android.cpp`：Android 实现

**Skia 核心：**
- `include/core/SkSurface.h`：表面接口
- `src/core/SkRasterPipeline.h`：软件光栅化管线
- `src/core/SkDraw.h`：绘图实现

**应用示例：**
- `tools/viewer/Viewer.cpp`：测试工具（支持软件渲染模式）
- `dm/DM.cpp`：测试框架
