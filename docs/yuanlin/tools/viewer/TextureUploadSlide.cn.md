# TextureUploadSlide

> 源文件: tools/viewer/TextureUploadSlide.cpp

## 概述

`TextureUploadSlide` 是一个用于测试和演示大量纹理上传性能的 Skia Viewer 幻灯片。它模拟平铺渲染场景,每帧创建多个纹理并上传 CPU 内存中的像素数据到 GPU,用于评估纹理上传带宽和性能瓶颈。该幻灯片特别适用于测试类似网页平铺渲染的高频纹理更新场景。

## 架构位置

`TextureUploadSlide` 位于 `tools/viewer` 目录,仅在启用 Ganesh GPU 后端时编译(`SK_GANESH` 宏)。它展示了 GPU 纹理管理和数据传输的性能特征。

```
tools/viewer/
├── Slide (基类)
└── TextureUploadSlide
    ├── RenderTargetTexture (纹理封装)
    ├── 平铺布局 (最多64个瓦片)
    └── CPU -> GPU 数据传输
```

## 主要类与结构体

### TextureUploadSlide 类

```cpp
class TextureUploadSlide : public Slide {
public:
    TextureUploadSlide() { fName = "TextureUpload"; }

    bool onChar(SkUnichar uni) override;
    SkISize getDimensions() const override { return {1024, 1024}; }
    void draw(SkCanvas* canvas) override;
    bool animate(double nanos) override;

private:
    class RenderTargetTexture;

    bool fDrawTexturesToScreen = true;
    int fTileSize = 256;
    int fTileRows = 8;
    int fTileCols = 8;
    sk_sp<SkSurface> fBlueSurface;
    sk_sp<SkSurface> fGraySurface;
    TArray<sk_sp<RenderTargetTexture>> fTextures;
    GrDirectContext* fCachedContext = nullptr;
    SkScalar fActiveTileIndex = 0;
};
```

### RenderTargetTexture 嵌套类

```cpp
class RenderTargetTexture : public SkRefCnt {
public:
    RenderTargetTexture(GrDirectContext* direct, int size);
    sk_sp<SkImage> getImage();
    void uploadRasterSurface(sk_sp<SkSurface> rasterSurface);
private:
    sk_sp<SkSurface> fSurface;
};
```

## 公共 API 函数

### 键盘交互

**bool onChar(SkUnichar uni)**
- `'m'`: 切换是否将纹理绘制到屏幕(测试纯上传 vs 上传+渲染性能)
- `'>'`: 增大瓦片尺寸(翻倍,最大 2048)
- `'<'`: 减小瓦片尺寸(减半,最小 128)
- 改变瓦片尺寸会清除缓存的上下文,触发纹理重新初始化

### 尺寸查询

**SkISize getDimensions() const**
- 返回固定的 1024×1024 画布尺寸

### 绘制与动画

**void draw(SkCanvas* canvas)**
- 检查并初始化纹理(如果 GPU 上下文改变)
- 为所有纹理上传新的像素数据
- 将活动瓦片设置为蓝色,其余为灰色
- 如果 `fDrawTexturesToScreen` 为 true,将纹理绘制到画布
- 应用 0.25 倍缩放以适应显示

**bool animate(double nanos)**
- 计算当前活动瓦片索引
- 在 16 秒内循环遍历所有瓦片
- 返回 true 持续动画

## 内部实现细节

### 纹理初始化

```cpp
void initializeTextures(GrDirectContext* direct) {
    fTextures.clear();
    int textureCount = fTileRows * fTileCols;
    for (int i = 0; i < textureCount; i++) {
        fTextures.emplace_back(new RenderTargetTexture(direct, fTileSize));
    }
    fBlueSurface = getFilledRasterSurface(SK_ColorBLUE, fTileSize);
    fGraySurface = getFilledRasterSurface(SK_ColorGRAY, fTileSize);
}
```

- 创建平铺网格的所有纹理对象
- 创建两个 CPU 端的 raster surface(蓝色和灰色)作为上传源

### 纹理上传流程

每帧在 `draw()` 中执行:

```cpp
for (int i = 0; i < textureCount; i++) {
    fTextures[i]->uploadRasterSurface(
        i == fActiveTileIndex ? fBlueSurface : fGraySurface
    );
}
```

`uploadRasterSurface()` 实现:

```cpp
void uploadRasterSurface(sk_sp<SkSurface> rasterSurface) {
    SkPixmap pixmap;
    rasterSurface->peekPixels(&pixmap);
    fSurface->writePixels(pixmap, 0, 0);
}
```

- 从 raster surface 获取 pixmap
- 使用 `writePixels()` 将像素数据上传到 GPU 纹理

### 瓦片配置

- **默认配置**: 8×8 网格,每个瓦片 256×256 像素
- **可调范围**: 瓦片大小 128 - 2048,网格大小自动调整
- **最大纹理数**: 2048×2048 总面积 / 瓦片面积
- **显示缩放**: 0.25 倍缩放以适应屏幕

### RenderTargetTexture 实现

```cpp
RenderTargetTexture(GrDirectContext* direct, int size) {
    SkSurfaceProps surfaceProps(0, kRGB_H_SkPixelGeometry);
    SkImageInfo imageInfo = SkImageInfo::Make(
        size, size, kRGBA_8888_SkColorType, kPremul_SkAlphaType
    );
    fSurface = SkSurfaces::RenderTarget(
        direct, skgpu::Budgeted::kNo, imageInfo, 0, &surfaceProps
    );
}
```

- 创建非预算的 GPU render target
- 使用 RGBA_8888 颜色格式
- 无 MSAA(采样数为 0)

## 依赖关系

### 直接依赖

- **Skia 核心**: `SkCanvas`, `SkSurface`, `SkImage`, `SkImageInfo`, `SkPixmap`
- **Ganesh**: `GrDirectContext`, `SkSurfaceGanesh`
- **时间工具**: `TimeUtils::Scaled()` 用于动画计时
- **容器**: `skia_private::TArray`

### 条件依赖

- 需要 `SK_GANESH` 宏定义
- 需要有效的 GPU 上下文

## 设计模式与设计决策

### 设计模式

1. **Facade Pattern**: `RenderTargetTexture` 封装 GPU 纹理和上传操作
2. **Lazy Initialization**: 纹理在首次绘制时初始化,而非构造时
3. **Object Pool**: 纹理数组作为对象池,避免频繁创建销毁

### 设计决策

1. **模拟真实场景**: 平铺布局模拟网页渲染器的常见用例
2. **每帧全部上传**: 测试最坏情况的上传带宽
3. **双缓冲源数据**: 使用预先填充的 blue/gray surface 避免重复填充开销
4. **可选渲染**: 通过 'm' 键可以测试纯上传性能,排除渲染开销
5. **动画高亮**: 蓝色瓦片循环移动,便于视觉确认上传是否成功
6. **上下文感知**: 缓存 GPU 上下文指针,检测上下文切换并重新初始化

## 性能考量

### 性能瓶颈

1. **内存带宽**: CPU → GPU 数据传输是主要瓶颈
2. **上传开销**: 每帧上传 64 × 256² × 4 字节 = 16 MB 数据(默认配置)
3. **同步开销**: `writePixels()` 可能导致 CPU-GPU 同步点
4. **纹理切换**: 多个小纹理可能增加 GPU 状态切换开销

### 优化机会

- 使用 `SkSurface::asyncRescaleAndReadPixels()` 异步上传
- 批量上传操作
- 使用纹理图集减少绑定次数
- PBO(Pixel Buffer Object)加速传输

### 测试场景

- **大瓦片少数量**: 2048×2048,1个瓦片,测试单次大数据传输
- **小瓦片大数量**: 128×128,256个瓦片,测试状态切换开销
- **中等配置**: 256×256,64个瓦片,平衡测试

## 相关文件

- **tools/viewer/Slide.h**: 幻灯片基类
- **include/gpu/ganesh/GrDirectContext.h**: Ganesh GPU 上下文
- **include/core/SkSurface.h**: Surface 接口
- **tools/timer/TimeUtils.h**: 时间工具函数
- **include/gpu/ganesh/SkSurfaceGanesh.h**: Ganesh Surface 工厂
