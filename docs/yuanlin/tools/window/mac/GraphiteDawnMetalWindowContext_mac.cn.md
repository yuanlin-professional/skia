# GraphiteDawnMetalWindowContext_mac

> 源文件
> - tools/window/mac/GraphiteDawnMetalWindowContext_mac.h
> - tools/window/mac/GraphiteDawnMetalWindowContext_mac.mm

## 概述

`GraphiteDawnMetalWindowContext_mac` 是 Skia 在 macOS 平台上使用 Graphite 渲染引擎配合 Dawn 和 Metal 后端的窗口上下文实现。Graphite 是 Skia 的下一代 GPU 渲染引擎，专注于现代图形 API。Dawn 是 Chromium 项目的 WebGPU 实现，提供了跨平台的 GPU API 抽象层。在 macOS 上，Dawn 将 WebGPU 调用转换为 Metal 调用。

该实现代表了 Skia 最现代化的渲染路径：**Graphite → Dawn → Metal**，充分利用了 Metal 的低开销特性和现代化设计，同时保持了通过 WebGPU API 的跨平台能力。相比传统的 Ganesh + OpenGL 方案，这个组合提供了更好的性能和未来可扩展性。

## 架构位置

该模块位于 Skia 工具层的窗口系统实现中：

```
skia/
├── tools/
│   └── window/
│       ├── GraphiteDawnWindowContext.h          # Graphite Dawn 基类
│       └── mac/
│           ├── GraphiteDawnMetalWindowContext_mac.h   # 本模块头文件
│           ├── GraphiteDawnMetalWindowContext_mac.mm  # 本模块实现
│           ├── GaneshGLWindowContext_mac.mm           # Ganesh OpenGL 实现
│           └── MacWindowInfo.h                  # macOS 窗口信息
├── include/
│   └── gpu/
│       └── graphite/                            # Graphite 公共接口
│           ├── Context.h
│           └── Recorder.h
├── src/
│   └── gpu/
│       └── graphite/                            # Graphite 实现
│           └── dawn/                            # Dawn 后端
└── third_party/
    └── externals/
        └── dawn/                                # Dawn 库
```

该模块的架构层次：
- **应用层**：测试工具、示例程序
- **窗口抽象层**：本模块（平台适配）
- **渲染引擎层**：Graphite（Skia 新渲染引擎）
- **GPU 抽象层**：Dawn（WebGPU 实现）
- **系统图形层**：Metal（Apple 原生 API）

## 主要类与结构体

### GraphiteDawnMetalWindowContext_mac

匿名命名空间内的私有实现类，继承自 `GraphiteDawnWindowContext`。

**主要成员变量：**
- `NSView* fMainView`：macOS 主视图对象
- `CAMetalLayer* fMetalLayer`：Metal 渲染层，作为渲染目标

**主要成员函数：**

```cpp
GraphiteDawnMetalWindowContext_mac(const MacWindowInfo&, std::unique_ptr<const DisplayParams>)
```
构造函数，初始化窗口上下文并计算初始尺寸。

```cpp
~GraphiteDawnMetalWindowContext_mac() override
```
析构函数，销毁上下文和相关资源。

```cpp
bool onInitializeContext() override
```
创建 Dawn 设备、Metal layer 和 WebGPU 表面。

```cpp
void onDestroyContext() override
```
销毁上下文资源（当前为空实现）。

```cpp
void resize(int w, int h) override
```
处理窗口尺寸变化。

```cpp
bool resizeInternal()
```
内部尺寸调整实现，更新 Metal layer 尺寸和缩放。

### MacWindowInfo

定义在 `MacWindowInfo.h` 中：
- `NSView* fMainView`：主渲染视图

### DisplayParams

显示参数配置：
- 垂直同步开关
- 颜色空间
- 其他渲染选项

## 公共 API 函数

### MakeGraphiteDawnMetalForMac

```cpp
namespace skwindow {
std::unique_ptr<WindowContext> MakeGraphiteDawnMetalForMac(
    const MacWindowInfo& info,
    std::unique_ptr<const DisplayParams> params);
}
```

**功能：** 创建使用 Graphite + Dawn + Metal 的 macOS 窗口上下文。

**参数：**
- `info`：包含 `NSView` 指针的窗口信息
- `params`：显示参数配置

**返回值：** 成功返回 `WindowContext` 智能指针，失败返回 `nullptr`

**使用场景：**
- 使用 Graphite 渲染引擎的应用程序
- 需要 WebGPU API 兼容性的场景
- 在 macOS 上获得最佳性能的现代渲染路径

## 内部实现细节

### 构造函数初始化

构造函数执行流程：

```cpp
GraphiteDawnMetalWindowContext_mac::GraphiteDawnMetalWindowContext_mac(
        const MacWindowInfo& info, std::unique_ptr<const DisplayParams> params)
        : GraphiteDawnWindowContext(std::move(params), wgpu::TextureFormat::BGRA8Unorm)
        , fMainView(info.fMainView) {
    CGFloat backingScaleFactor = skwindow::GetBackingScaleFactor(fMainView);
    CGSize backingSize = fMainView.bounds.size;
    this->initializeContext(backingSize.width * backingScaleFactor,
                            backingSize.height * backingScaleFactor);
}
```

**关键步骤：**
1. 调用基类构造函数，指定纹理格式为 `BGRA8Unorm`（Metal 优化格式）
2. 保存主视图引用
3. 获取 Retina 缩放因子
4. 计算实际像素尺寸
5. 调用基类的 `initializeContext()` 完成初始化

### 上下文初始化

`onInitializeContext()` 实现了完整的初始化流程：

```cpp
bool GraphiteDawnMetalWindowContext_mac::onInitializeContext() {
    SkASSERT(nil != fMainView);

    // 1. 创建 Dawn Metal 设备
    auto device = createDevice(wgpu::BackendType::Metal);
    if (!device) {
        return false;
    }

    // 2. 创建并配置 CAMetalLayer
    fMetalLayer = [CAMetalLayer layer];
    BOOL useVsync = fDisplayParams->disableVsync() ? NO : YES;
    fMetalLayer.displaySyncEnabled = useVsync;
    fMainView.wantsLayer = YES;
    fMainView.layer = fMetalLayer;

    // 3. 调整 layer 尺寸
    this->resizeInternal();

    // 4. 创建 WebGPU 表面
    wgpu::SurfaceSourceMetalLayer surfaceChainedDesc;
    surfaceChainedDesc.layer = fMetalLayer;
    wgpu::SurfaceDescriptor surfaceDesc;
    surfaceDesc.nextInChain = &surfaceChainedDesc;

    auto surface = wgpu::Instance(fInstance->Get()).CreateSurface(&surfaceDesc);
    if (!surface) {
        return false;
    }

    // 5. 保存设备和表面，配置表面
    fDevice = std::move(device);
    fSurface = std::move(surface);
    configureSurface();

    return true;
}
```

**技术要点：**

1. **Dawn 设备创建**
   - `createDevice(wgpu::BackendType::Metal)` 创建 Metal 后端设备
   - Dawn 处理 WebGPU 到 Metal 的映射

2. **CAMetalLayer 配置**
   - `CAMetalLayer` 是 Metal 的专用渲染层
   - `displaySyncEnabled` 控制垂直同步
   - 直接将 layer 设置为 view 的 backing layer

3. **WebGPU 表面创建**
   - 使用链式描述符模式（`nextInChain`）
   - `SurfaceSourceMetalLayer` 指定 Metal layer 作为表面源
   - Dawn 将 WebGPU 渲染输出到此表面

### 尺寸调整逻辑

`resizeInternal()` 处理窗口尺寸变化：

```cpp
bool GraphiteDawnMetalWindowContext_mac::resizeInternal() {
    CGFloat backingScaleFactor = skwindow::GetBackingScaleFactor(fMainView);
    CGSize backingSize = fMainView.bounds.size;
    backingSize.width *= backingScaleFactor;
    backingSize.height *= backingScaleFactor;

    fMetalLayer.drawableSize = backingSize;
    fMetalLayer.contentsScale = backingScaleFactor;

    if (fWidth == backingSize.width && fHeight == backingSize.height) {
        return false;  // 尺寸未变化
    }

    fWidth = backingSize.width;
    fHeight = backingSize.height;
    configureSurface();

    return true;
}
```

**关键点：**
- `drawableSize`：Metal layer 的可绘制区域尺寸（像素）
- `contentsScale`：内容缩放因子，用于 Retina 显示
- 仅在尺寸实际变化时重新配置表面，避免不必要开销

### 垂直同步控制

```cpp
BOOL useVsync = fDisplayParams->disableVsync() ? NO : YES;
fMetalLayer.displaySyncEnabled = useVsync;
```

通过 `CAMetalLayer` 的 `displaySyncEnabled` 属性控制：
- `YES`：渲染与屏幕刷新同步（通常 60Hz 或更高）
- `NO`：不等待垂直同步，最大帧率渲染

### 资源管理

析构函数调用 `destroyContext()`，由基类处理：
- Dawn 设备自动管理
- WebGPU 表面自动清理
- `CAMetalLayer` 由 Objective-C ARC 管理（在 ARC 环境下）

## 依赖关系

### 外部依赖

**Skia Graphite 组件：**
- `GraphiteDawnWindowContext`：Graphite Dawn 窗口上下文基类
- `skgpu::graphite::Context`：Graphite 渲染上下文
- `skgpu::graphite::Recorder`：命令记录器

**Dawn（WebGPU）组件：**
- `wgpu::Device`：WebGPU 设备抽象
- `wgpu::Surface`：渲染表面
- `wgpu::Instance`：WebGPU 实例
- `wgpu::BackendType::Metal`：Metal 后端类型

**平台工具：**
- `MacWindowInfo`：窗口信息结构
- `GetBackingScaleFactor()`：获取 Retina 缩放因子

**系统框架：**
- `Cocoa.framework`：macOS 窗口系统
- `QuartzCore.framework`：Core Animation
  - `CAMetalLayer`：Metal 专用渲染层
  - `CAConstraintLayoutManager`
- `Metal.framework`：通过 Dawn 间接使用

### 被依赖关系

该模块被以下组件使用：
- Graphite 测试工具
- 使用 Graphite 的示例应用
- 性能基准测试

## 设计模式与设计决策

### 设计模式

1. **工厂模式**
   - `MakeGraphiteDawnMetalForMac()` 创建平台实现
   - 隐藏具体类型

2. **模板方法模式**
   - 继承 `GraphiteDawnWindowContext`
   - 实现平台相关虚函数
   - 基类控制初始化流程

3. **桥接模式**
   - Dawn 作为 WebGPU 和 Metal 之间的桥接
   - Graphite 与底层 API 解耦

### 设计决策

1. **选择 BGRA8Unorm 格式**
   ```cpp
   GraphiteDawnWindowContext(std::move(params), wgpu::TextureFormat::BGRA8Unorm)
   ```
   - Metal 和 macOS 原生优化此格式
   - 避免格式转换开销
   - 与 Core Animation 兼容

2. **使用 CAMetalLayer**
   - Metal 的官方渲染目标
   - 硬件加速合成
   - 支持 HDR 和宽色域

3. **Dawn 作为抽象层**
   - 提供跨平台 WebGPU API
   - 隔离平台差异
   - 未来可切换到其他后端（Vulkan、D3D12）

4. **匿名命名空间**
   - 隐藏实现细节
   - 防止符号冲突

5. **条件性重新配置**
   ```cpp
   if (fWidth == backingSize.width && fHeight == backingSize.height) {
       return false;
   }
   ```
   - 避免不必要的表面重建
   - 优化性能

6. **Retina 自动适配**
   - 自动处理缩放因子
   - 确保清晰渲染
   - 无需手动计算

## 性能考量

### 优势

1. **现代化渲染管线**
   - Graphite 专为现代 GPU 设计
   - 更好的多线程支持
   - 更低的 CPU 开销

2. **Metal 原生性能**
   - Metal 是 Apple 优化的低开销 API
   - 直接访问 GPU 硬件
   - 最小化驱动开销

3. **Dawn 优化**
   - Chromium 团队持续优化
   - 高效的状态管理
   - 批处理和缓存优化

4. **CAMetalLayer 硬件加速**
   - 零拷贝显示
   - Core Animation 硬件合成
   - 支持异步提交

### 性能优化

1. **避免不必要的重配置**
   - `resizeInternal()` 检查尺寸变化
   - 仅在需要时调用 `configureSurface()`

2. **垂直同步可选**
   - 基准测试时禁用垂直同步
   - 生产环境启用以减少撕裂

3. **BGRA 格式优化**
   - 避免像素格式转换
   - Metal 原生支持

### 潜在瓶颈

1. **抽象层开销**
   - Graphite → Dawn → Metal 多层调用
   - 比直接使用 Metal API 略慢
   - 但换来跨平台能力

2. **表面配置开销**
   - `configureSurface()` 可能涉及资源重建
   - 应避免频繁调用

3. **Retina 显示像素数**
   - 实际渲染像素是逻辑尺寸的 4-9 倍
   - 对 GPU 填充率要求高

### 内存管理

- Dawn 设备和表面由智能指针管理
- Objective-C 对象依赖 ARC 或手动管理
- Metal 纹理由 Dawn 池化管理

## 相关文件

**同平台其他实现：**
- `tools/window/mac/GaneshGLWindowContext_mac.mm`：Ganesh OpenGL 实现
- `tools/window/mac/GaneshANGLEWindowContext_mac.mm`：Ganesh ANGLE 实现
- `tools/window/mac/RasterWindowContext_mac.mm`：软件光栅化

**基类和工具：**
- `tools/window/GraphiteDawnWindowContext.h`：Graphite Dawn 基类
- `tools/window/WindowContext.h`：窗口上下文抽象
- `tools/window/mac/MacWindowInfo.h`：macOS 窗口信息

**其他平台 Graphite Dawn 实现：**
- `tools/window/unix/GraphiteDawnXlibWindowContext_unix.cpp`：Unix/X11 实现
- `tools/window/win/GraphiteDawnD3D12WindowContext_win.cpp`：Windows D3D12 实现

**Graphite 核心：**
- `include/gpu/graphite/Context.h`：Graphite 上下文接口
- `src/gpu/graphite/dawn/DawnGraphiteUtils.h`：Dawn 工具函数
- `src/gpu/graphite/ContextPriv.h`：上下文内部接口

**Dawn 相关：**
- `third_party/externals/dawn/`：Dawn WebGPU 实现
- `dawn/webgpu_cpp.h`：WebGPU C++ 绑定

**测试和应用：**
- `tools/viewer/Viewer.cpp`：可视化测试工具
- `tools/graphite/dawn/GraphiteDawnTestContext.h`：测试上下文
