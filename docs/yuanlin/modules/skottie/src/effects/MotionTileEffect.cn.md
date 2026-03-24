# MotionTileEffect

> 源文件: modules/skottie/src/effects/MotionTileEffect.cpp

## 概述

MotionTileEffect 模块实现了动态平铺效果,将图层内容映射到可配置的瓦片并在输出区域内重复。支持镜像边缘、相位偏移等高级功能,对应 Adobe After Effects 的 Motion Tile 效果。

## 架构位置

```
modules/skottie/
  └── src/
      └── effects/
          ├── MotionTileEffect.cpp     # 动态平铺实现
          ├── Effects.h                # 效果接口
          └── GaussianBlurEffect.cpp   # 其他图像效果
```

## 主要类与结构体

### TileRenderNode

自定义渲染节点,实现平铺渲染逻辑。

```cpp
class TileRenderNode final : public sksg::CustomRenderNode
```

**核心属性:**
- `fTileCenter` - 瓦片中心点
- `fTileW` / `fTileH` - 瓦片宽度/高度(百分比)
- `fOutputW` / `fOutputH` - 输出宽度/高度(百分比)
- `fPhase` - 相位偏移(度数)
- `fMirrorEdges` - 镜像边缘开关
- `fHorizontalPhase` - 水平相位开关

**缓存成员:**
- `fLayerPicture` - 图层内容的缓存图片
- `fMainPassShader` - 主瓦片着色器
- `fPhasePassShader` - 相位偏移瓦片着色器

### MotionTileAdapter

适配器类,将 JSON 参数绑定到 TileRenderNode。

```cpp
class MotionTileAdapter final : public DiscardableAdapterBase<MotionTileAdapter, TileRenderNode>
```

## 公共 API 函数

### attachMotionTileEffect

```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachMotionTileEffect(
    const skjson::ArrayValue& jprops,
    sk_sp<sksg::RenderNode> layer) const
```

**属性索引:**
```cpp
enum : size_t {
    kTileCenter_Index = 0,            // 瓦片中心
    kTileWidth_Index = 1,             // 瓦片宽度
    kTileHeight_Index = 2,            // 瓦片高度
    kOutputWidth_Index = 3,           // 输出宽度
    kOutputHeight_Index = 4,          // 输出高度
    kMirrorEdges_Index = 5,           // 镜像边缘
    kPhase_Index = 6,                 // 相位偏移
    kHorizontalPhaseShift_Index = 7,  // 水平相位
};
```

## 内部实现细节

### AE Motion Tile 语义

1. **内容映射** - 图层完整内容映射到单个瓦片
2. **重复填充** - 瓦片在输出区域内双向重复
3. **平铺模式** - kRepeat(默认)或 kMirror(镜像边缘=true)
4. **相位偏移** - 交替列/行按指定量偏移

### 图层图片缓存

```cpp
if (!fLayerPicture || this->hasChildrenInval()) {
    const auto& layer = this->children()[0];
    layer->revalidate(ic, ctm);

    SkPictureRecorder recorder;
    layer->render(recorder.beginRecording(fLayerSize.width(), fLayerSize.height()));
    fLayerPicture = recorder.finishRecordingAsPicture();
}
```

仅在图层内容失效时重新录制图片,优化性能。

### 瓦片着色器构建

```cpp
const auto tile = SkRect::MakeXYWH(fTileCenter.fX - 0.5f * tile_size.width(),
                                   fTileCenter.fY - 0.5f * tile_size.height(),
                                   tile_size.width(),
                                   tile_size.height());

const auto layerShaderMatrix = SkMatrix::RectToRectOrIdentity(
            SkRect::MakeWH(fLayerSize.width(), fLayerSize.height()), tile);

const auto tm = fMirrorEdges ? SkTileMode::kMirror : SkTileMode::kRepeat;
auto layer_shader = fLayerPicture->makeShader(tm, tm, SkFilterMode::kLinear,
                                              &layerShaderMatrix, nullptr);
```

### 相位效果实现

相位偏移通过双遍渲染实现:

1. **遮罩着色器** - 使用阶梯渐变创建交替行/列的遮罩
2. **第一遍** - 原位渲染被遮罩的瓦片
3. **第二遍** - 渲染相位偏移的瓦片(反向遮罩)

```cpp
const auto phase_vec = fHorizontalPhase
        ? SkVector::Make(tile.width(), 0)
        : SkVector::Make(0, tile.height());

const auto phase_shift = SkVector::Make(phase_vec.fX, phase_vec.fY)
                         * std::fmod(fPhase * (1/360.0f), 1);

// 遮罩渐变
static constexpr SkColor4f colors[] = { {1, 1, 1, 1}, {0, 0, 0, 0} };
static constexpr float        pos[] = {       0.5f,       0.5f };

const SkPoint pts[] = {{ tile.x(), tile.y() },
                       { tile.x() + 2 * (tile.width()  - phase_vec.fX),
                         tile.y() + 2 * (tile.height() - phase_vec.fY) }};

auto mask_shader = SkShaders::LinearGradient(pts,
                                             {{colors, pos, SkTileMode::kRepeat}, {}});

// 第一遍: 原位遮罩内容
fMainPassShader  = SkShaders::Blend(SkBlendMode::kSrcIn , mask_shader, layer_shader);
// 第二遍: 相位偏移内容(反向遮罩)
fPhasePassShader = SkShaders::Blend(SkBlendMode::kSrcOut, mask_shader, layer_shader)
                   ->makeWithLocalMatrix(phase_shader_matrix);
```

### 双遍渲染

```cpp
void onRender(SkCanvas* canvas, const RenderContext* ctx) const override {
    SkPaint paint;
    paint.setAntiAlias(true);

    if (ctx) {
        ctx->modulatePaint(canvas->getLocalToDeviceAs3x3(), &paint);
    }

    paint.setShader(fMainPassShader);
    canvas->drawRect(this->bounds(), paint);

    if (fPhasePassShader) {
        paint.setShader(fPhasePassShader);
        canvas->drawRect(this->bounds(), paint);
    }
}
```

## 依赖关系

### Skia 核心依赖
- `SkPicture` / `SkPictureRecorder` - 图片录制
- `SkShader` / `SkShaders` - 着色器
- `SkGradient` - 渐变着色器
- `SkBlendMode` - 混合模式(SrcIn/SrcOut)
- `SkTileMode` - 平铺模式(Repeat/Mirror)

### Scene Graph 依赖
- `sksg::CustomRenderNode` - 自定义渲染节点基类
- `sksg::RenderNode` - 渲染节点
- `sksg::InvalidationController` - 失效控制器

## 设计模式与设计决策

### 自定义渲染节点

继承 `CustomRenderNode` 实现完全自定义的渲染逻辑,绕过标准的 Scene Graph 渲染管线。

### 图片缓存

使用 `SkPicture` 缓存图层渲染结果,避免每帧重复渲染复杂图层。

### 着色器合成

利用 Skia 着色器的混合和变换能力,在 GPU 上高效实现复杂的平铺和相位效果。

### 条件相位

仅在 `fPhase != 0` 时创建相位着色器,节省内存和 GPU 资源。

## 性能考量

### 智能失效

```cpp
if (!fLayerPicture || this->hasChildrenInval())
```

只在必要时重新录制图层图片,大幅减少 CPU 开销。

### GPU 平铺

使用 Skia 的平铺着色器而非 CPU 循环,充分利用 GPU 纹理采样硬件。

### 百分比单位

```cpp
const auto tileW = SkTPin(fTileW, 0.0f, 100.0f) * 0.01f * fLayerSize.width();
```

瓦片和输出尺寸使用图层大小的百分比,简化缩放计算。

### 边界快速退出

```cpp
if (this->bounds().isEmpty() || (fTileW <= 0 && fTileH <= 0)) {
    return;  // 不渲染
}
```

检测退化情况并提前退出,避免无效渲染。

## 相关文件

- `include/core/SkPicture.h` - 图片录制 API
- `include/effects/SkGradient.h` - 渐变着色器
- `modules/sksg/include/SkSGNode.h` - Scene Graph 节点基类
- `modules/skottie/src/effects/Effects.h` - 效果构建器
