# SkSurfaceMetal - Metal 表面创建接口

> 源文件: `include/gpu/ganesh/mtl/SkSurfaceMetal.h`

## 概述

SkSurfaceMetal.h 提供了在 Apple Metal 环境中创建 Skia 渲染表面的工厂函数。该文件定义了从 CAMetalLayer 和 MTKView 创建 SkSurface 的接口，是 Skia 与 Apple 平台原生显示层集成的关键桥梁，使 Skia 能够直接渲染到屏幕或离屏纹理。

## 架构位置

- **所属子系统**: GPU/Ganesh 渲染后端 - Metal 分支
- **层级**: 高级 API 接口层
- **作用域**: Apple 平台 Metal 后端专用

该文件位于 Skia 表面创建 API 的顶层，为应用开发者提供便捷的 Metal 集成接口。

## 主要类与结构体

本文件不定义类，在 `SkSurfaces` 命名空间中提供工厂函数。

## 公共 API 函数

### `SkSurfaces::WrapCAMetalLayer`

```cpp
SK_API sk_sp<SkSurface> WrapCAMetalLayer(
    GrRecordingContext* context,
    GrMTLHandle layer,
    GrSurfaceOrigin origin,
    int sampleCnt,
    SkColorType colorType,
    sk_sp<SkColorSpace> colorSpace,
    const SkSurfaceProps* surfaceProps,
    GrMTLHandle* drawable
) SK_API_AVAILABLE_CA_METAL_LAYER;
```

**功能**: 从 CAMetalLayer 创建 SkSurface，用于直接渲染到屏幕。

**参数详解**:

| 参数 | 类型 | 说明 |
|------|------|------|
| context | GrRecordingContext* | GPU 上下文（用于管理 GPU 资源） |
| layer | GrMTLHandle | CAMetalLayer* 的不透明句柄 |
| origin | GrSurfaceOrigin | 坐标原点（kBottomLeft 或 kTopLeft） |
| sampleCnt | int | 多重采样数量（0 或 1 表示禁用 MSAA） |
| colorType | SkColorType | 像素颜色类型（如 kRGBA_8888_SkColorType） |
| colorSpace | sk_sp\<SkColorSpace\> | 颜色空间（可为 nullptr 使用默认 sRGB） |
| surfaceProps | const SkSurfaceProps* | 表面属性（如 LCD 文本设置，可为 nullptr） |
| drawable | GrMTLHandle* | 输出参数，返回当前 drawable 的句柄（不可为 nullptr） |

**返回值**:
- 成功时返回 SkSurface 智能指针
- 失败时返回 nullptr（如 layer 无效或无可用 drawable）

**生命周期管理**:
- 返回的 SkSurface 持有 CAMetalLayer 的引用
- SkSurface 销毁时会释放该引用
- `drawable` 参数接收当前帧的 drawable，应用需在渲染完成后 present

**平台可用性**: `SK_API_AVAILABLE_CA_METAL_LAYER` 标注的版本要求
- macOS 10.11+
- iOS 8.0+ (真机) / 13.0+ (模拟器)
- tvOS 9.0+ (真机) / 13.0+ (模拟器)

### `SkSurfaces::WrapMTKView`

```cpp
SK_API sk_sp<SkSurface> WrapMTKView(
    GrRecordingContext* context,
    GrMTLHandle mtkView,
    GrSurfaceOrigin origin,
    int sampleCnt,
    SkColorType colorType,
    sk_sp<SkColorSpace> colorSpace,
    const SkSurfaceProps* surfaceProps
) SK_API_AVAILABLE(macos(10.11), ios(9.0), tvos(9.0));
```

**功能**: 从 MTKView 创建 SkSurface，简化 Metal 渲染循环。

**参数详解**:

| 参数 | 类型 | 说明 |
|------|------|------|
| context | GrRecordingContext* | GPU 上下文 |
| mtkView | GrMTLHandle | MTKView* 的不透明句柄 |
| origin | GrSurfaceOrigin | 坐标原点 |
| sampleCnt | int | 多重采样数量 |
| colorType | SkColorType | 像素颜色类型 |
| colorSpace | sk_sp\<SkColorSpace\> | 颜色空间 |
| surfaceProps | const SkSurfaceProps* | 表面属性 |

**返回值**:
- 成功时返回 SkSurface 智能指针
- 失败时返回 nullptr

**与 WrapCAMetalLayer 的区别**:
- 无 `drawable` 输出参数（MTKView 自动管理 drawable）
- MTKView 提供更高级的抽象，自动处理渲染循环
- 通过 MTKViewDelegate 集成更简单

**生命周期管理**:
- 返回的 SkSurface 持有 MTKView 的引用
- MTKView 的 drawable 由 view 自身管理

**平台可用性**:
- macOS 10.11+
- iOS 9.0+
- tvOS 9.0+

## 内部实现细节

### CAMetalLayer 集成流程

`WrapCAMetalLayer` 内部执行以下步骤：

1. **验证输入**: 检查 context 和 layer 的有效性
2. **获取 drawable**: 调用 `[layer nextDrawable]` 获取当前帧的 drawable
3. **提取纹理**: 从 drawable 获取 Metal 纹理对象
4. **创建后端纹理**: 包装 Metal 纹理为 `GrBackendRenderTarget`
5. **创建 SkSurface**: 使用 `SkSurface::MakeFromBackendRenderTarget` 创建表面
6. **返回 drawable**: 将 drawable 句柄写入输出参数供 present 使用

**关键代码模式**（实现文件中）:
```objc
CAMetalLayer* metalLayer = (__bridge CAMetalLayer*)layer;
id<CAMetalDrawable> drawable = [metalLayer nextDrawable];
if (!drawable) {
    return nullptr;
}

id<MTLTexture> texture = [drawable texture];
GrMtlTextureInfo textureInfo;
textureInfo.fTexture.retain((__bridge GrMTLHandle)texture);

// 创建 GrBackendRenderTarget 和 SkSurface...
*outDrawable = (__bridge_retained GrMTLHandle)drawable;
```

### MTKView 集成流程

`WrapMTKView` 的实现更简洁：

1. **获取 layer**: 从 MTKView 提取其 underlying CAMetalLayer
2. **获取 drawable**: MTKView 已管理 drawable 生命周期
3. **创建表面**: 与 CAMetalLayer 类似的流程
4. **自动更新**: MTKView 的 draw 回调自动触发新帧

**优势**:
- MTKView 自动处理 drawable 生命周期
- 提供内置的渲染循环（通过 `MTKViewDelegate`）
- 自动处理 Retina 显示缩放

### 坐标原点处理

`GrSurfaceOrigin` 参数影响 Y 轴方向：

**kTopLeft_GrSurfaceOrigin**:
- Y 轴向下增长（标准 UI 坐标系）
- 适合与 UIKit/AppKit 集成
- Skia 内部会翻转渲染

**kBottomLeft_GrSurfaceOrigin**:
- Y 轴向上增长（OpenGL 风格）
- 更符合图形学惯例
- 无需额外翻转

Metal 纹理默认是 top-left origin，Skia 会根据参数自动处理。

### 多重采样处理

`sampleCnt` 参数控制 MSAA（多重采样抗锯齿）：

**值为 0 或 1**: 禁用 MSAA
- 直接渲染到 drawable 的纹理
- 性能最优，适合大多数场景

**值 > 1**: 启用 MSAA
- Skia 创建多重采样纹理作为渲染目标
- 完成后 resolve 到 drawable 纹理
- 提升边缘质量但增加内存和性能开销

### 颜色空间管理

`colorSpace` 参数指定渲染的颜色空间：

**nullptr**: 使用默认 sRGB 颜色空间
**自定义颜色空间**: 如 Display P3、线性 RGB 等
- Metal 支持广色域显示
- Skia 会正确处理颜色空间转换
- 需要确保 layer 的 `pixelFormat` 匹配

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/core/SkRefCnt.h | sk_sp 智能指针 |
| include/core/SkSurface.h | SkSurface 基类 |
| include/gpu/ganesh/GrTypes.h | GrSurfaceOrigin 等类型 |
| include/gpu/ganesh/SkSurfaceGanesh.h | Ganesh 特定表面函数 |
| include/gpu/ganesh/mtl/GrMtlTypes.h | GrMTLHandle 类型定义 |

### 被依赖的模块

- **iOS/macOS 应用层**: 使用这些函数在 view 中集成 Skia 渲染
- **游戏引擎**: 集成 Skia 作为 UI 或 HUD 渲染层
- **自定义渲染器**: 与其他 Metal 渲染代码协同工作

### 系统依赖

- **Metal.framework**: Metal API
- **QuartzCore.framework**: CAMetalLayer
- **MetalKit.framework**: MTKView（可选，仅 `WrapMTKView` 需要）

## 设计模式与设计决策

### 1. 工厂函数模式

使用静态工厂函数而非构造函数：
- **优点**:
  - 可返回 nullptr 表示失败（构造函数不能）
  - 名称清晰表达创建意图（`Wrap*` 表示包装现有资源）
  - 支持复杂的初始化逻辑
- **命名约定**: `Wrap*` 表示包装外部资源，不创建新资源

### 2. 智能指针返回

返回 `sk_sp<SkSurface>` 而非裸指针：
- 自动管理 SkSurface 生命周期
- 防止内存泄漏
- 与 Skia 其他 API 一致

### 3. 句柄而非具体类型

使用 `GrMTLHandle`（`const void*`）而非 Objective-C 指针：
- 允许在纯 C++ 头文件中声明
- 避免 Objective-C 语法污染
- 使用时通过 `__bridge` 转换

### 4. 输出参数设计

`WrapCAMetalLayer` 的 `drawable` 参数为输出参数：
- **必需性**: 不可为 nullptr，确保调用者获取 drawable
- **原因**: 渲染完成后需要调用 `[drawable present]` 显示内容
- **替代方案**: MTKView 自动管理，无需此参数

### 5. 命名空间组织

使用 `SkSurfaces` 命名空间：
- 避免全局命名空间污染
- 与其他后端的表面创建函数并列（`SkSurfaces::RasterDirect` 等）
- 清晰表达函数归属

## 性能考量

### Drawable 获取延迟

`[layer nextDrawable]` 调用可能阻塞：
- **原因**: 如果所有 drawable 都在使用中（通常有 3 个）
- **优化**: 尽快 present 上一帧释放 drawable
- **最佳实践**: 使用三重缓冲（Metal 默认）

### MSAA 开销

启用 MSAA 的性能影响：
- **内存**: 多重采样纹理占用额外内存
- **带宽**: resolve 操作需要额外带宽
- **建议**: 移动设备上谨慎使用，桌面端可适当启用

### 颜色空间转换

使用非 sRGB 颜色空间的开销：
- **转换成本**: 着色器中额外的颜色空间转换
- **精度**: 某些颜色空间需要更高精度格式（如 RGBA16F）
- **建议**: 仅在需要广色域时使用

### Retina 显示缩放

在 Retina 显示器上：
- **像素倍数**: 2x 或 3x 物理像素
- **性能影响**: 渲染像素数增加 4-9 倍
- **优化**: 考虑使用 `contentsScale` 调整渲染分辨率

## 平台相关说明

### iOS/iPadOS

**CAMetalLayer 集成**:
```objc
// UIView 子类
- (instancetype)initWithFrame:(CGRect)frame {
    if (self = [super initWithFrame:frame]) {
        CAMetalLayer* metalLayer = (CAMetalLayer*)self.layer;
        metalLayer.device = MTLCreateSystemDefaultDevice();
        metalLayer.pixelFormat = MTLPixelFormatBGRA8Unorm;
        metalLayer.framebufferOnly = YES;  // 优化性能
    }
    return self;
}

+ (Class)layerClass {
    return [CAMetalLayer class];
}
```

**MTKView 集成**:
```objc
MTKView* mtkView = [[MTKView alloc] initWithFrame:frame device:device];
mtkView.colorPixelFormat = MTLPixelFormatBGRA8Unorm;
mtkView.delegate = self;  // 实现 MTKViewDelegate

- (void)drawInMTKView:(MTKView*)view {
    sk_sp<SkSurface> surface = SkSurfaces::WrapMTKView(
        context, (__bridge GrMTLHandle)view,
        kTopLeft_GrSurfaceOrigin, 1,
        kBGRA_8888_SkColorType, nullptr, nullptr);

    SkCanvas* canvas = surface->getCanvas();
    // 绘制...
    context->flush();
}
```

### macOS

**NSView 集成**:
```objc
@interface SkiaMetalView : NSView
@property (nonatomic) CAMetalLayer* metalLayer;
@end

@implementation SkiaMetalView

- (instancetype)initWithFrame:(NSRect)frame {
    if (self = [super initWithFrame:frame]) {
        self.wantsLayer = YES;
        self.metalLayer = [CAMetalLayer layer];
        self.metalLayer.device = MTLCreateSystemDefaultDevice();
        self.layer = self.metalLayer;
    }
    return self;
}

- (void)drawRect:(NSRect)dirtyRect {
    id<CAMetalDrawable> drawable;
    sk_sp<SkSurface> surface = SkSurfaces::WrapCAMetalLayer(
        context, (__bridge GrMTLHandle)self.metalLayer,
        kTopLeft_GrSurfaceOrigin, 1,
        kBGRA_8888_SkColorType, nullptr, nullptr,
        (GrMTLHandle*)&drawable);

    SkCanvas* canvas = surface->getCanvas();
    // 绘制...
    context->flush();
    [drawable present];
}

@end
```

**Retina 支持**:
```objc
// 启用 Retina 渲染
self.metalLayer.contentsScale = [[NSScreen mainScreen] backingScaleFactor];
```

### tvOS

与 iOS 类似，但有特定考虑：
- **固定分辨率**: 1080p 或 4K
- **电视优化**: 考虑过扫描区域（safe area）
- **性能**: Apple TV 性能介于 iPhone 和 iPad 之间

## 使用示例

### 完整的 iOS 渲染循环

```objc
@interface SkiaViewController : UIViewController
@property (nonatomic) sk_sp<GrDirectContext> skiaContext;
@property (nonatomic) CAMetalLayer* metalLayer;
@property (nonatomic) CADisplayLink* displayLink;
@end

@implementation SkiaViewController

- (void)viewDidLoad {
    [super viewDidLoad];

    // 创建 Metal device 和 context
    id<MTLDevice> device = MTLCreateSystemDefaultDevice();
    id<MTLCommandQueue> queue = [device newCommandQueue];

    GrMtlBackendContext backendContext;
    backendContext.fDevice.retain((__bridge GrMTLHandle)device);
    backendContext.fQueue.retain((__bridge GrMTLHandle)queue);
    self.skiaContext = GrDirectContext::MakeMetal(backendContext);

    // 配置 Metal layer
    self.metalLayer = [CAMetalLayer layer];
    self.metalLayer.device = device;
    self.metalLayer.pixelFormat = MTLPixelFormatBGRA8Unorm;
    self.metalLayer.framebufferOnly = YES;
    [self.view.layer addSublayer:self.metalLayer];

    // 设置渲染循环
    self.displayLink = [CADisplayLink displayLinkWithTarget:self
                                                   selector:@selector(render)];
    [self.displayLink addToRunLoop:[NSRunLoop mainRunLoop]
                           forMode:NSRunLoopCommonModes];
}

- (void)render {
    id<CAMetalDrawable> drawable;
    sk_sp<SkSurface> surface = SkSurfaces::WrapCAMetalLayer(
        self.skiaContext.get(),
        (__bridge GrMTLHandle)self.metalLayer,
        kTopLeft_GrSurfaceOrigin,
        1,  // 无 MSAA
        kBGRA_8888_SkColorType,
        nullptr,
        nullptr,
        (GrMTLHandle*)&drawable);

    if (!surface) {
        NSLog(@"Failed to create surface");
        return;
    }

    SkCanvas* canvas = surface->getCanvas();
    canvas->clear(SK_ColorWHITE);

    // 自定义绘制...
    SkPaint paint;
    paint.setColor(SK_ColorBLUE);
    canvas->drawCircle(100, 100, 50, paint);

    // 提交渲染
    self.skiaContext->flush();
    [drawable present];
}

- (void)viewDidLayoutSubviews {
    [super viewDidLayoutSubviews];
    self.metalLayer.frame = self.view.bounds;
    self.metalLayer.contentsScale = [[UIScreen mainScreen] scale];
}

@end
```

### 使用 MTKView 简化代码

```objc
@interface SkiaMTKViewController : UIViewController <MTKViewDelegate>
@property (nonatomic) sk_sp<GrDirectContext> skiaContext;
@property (nonatomic) MTKView* mtkView;
@end

@implementation SkiaMTKViewController

- (void)viewDidLoad {
    [super viewDidLoad];

    // 创建 Metal context
    id<MTLDevice> device = MTLCreateSystemDefaultDevice();
    id<MTLCommandQueue> queue = [device newCommandQueue];

    GrMtlBackendContext backendContext;
    backendContext.fDevice.retain((__bridge GrMTLHandle)device);
    backendContext.fQueue.retain((__bridge GrMTLHandle)queue);
    self.skiaContext = GrDirectContext::MakeMetal(backendContext);

    // 创建 MTKView
    self.mtkView = [[MTKView alloc] initWithFrame:self.view.bounds device:device];
    self.mtkView.colorPixelFormat = MTLPixelFormatBGRA8Unorm;
    self.mtkView.delegate = self;
    [self.view addSubview:self.mtkView];
}

- (void)drawInMTKView:(MTKView*)view {
    sk_sp<SkSurface> surface = SkSurfaces::WrapMTKView(
        self.skiaContext.get(),
        (__bridge GrMTLHandle)view,
        kTopLeft_GrSurfaceOrigin,
        1,
        kBGRA_8888_SkColorType,
        nullptr,
        nullptr);

    if (surface) {
        SkCanvas* canvas = surface->getCanvas();
        canvas->clear(SK_ColorWHITE);
        // 绘制...
        self.skiaContext->flush();
    }
}

- (void)mtkView:(MTKView*)view drawableSizeWillChange:(CGSize)size {
    // 处理尺寸变化
}

@end
```

## 相关文件

| 文件 | 关系 |
|------|------|
| include/gpu/ganesh/mtl/GrMtlTypes.h | 定义 GrMTLHandle 和 GrMtlSurfaceInfo |
| include/gpu/ganesh/mtl/GrMtlBackendContext.h | 创建 Metal 上下文所需的结构体 |
| include/core/SkSurface.h | SkSurface 基类定义 |
| include/gpu/ganesh/SkSurfaceGanesh.h | Ganesh 通用表面函数 |
| src/gpu/ganesh/mtl/GrMtlGpu.h | Metal GPU 实现 |
| src/image/SkSurface_Gpu.h | GPU 表面内部实现 |
