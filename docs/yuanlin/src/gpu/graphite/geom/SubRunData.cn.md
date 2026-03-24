# SubRunData - 图集子运行数据

> 源文件: `src/gpu/graphite/geom/SubRunData.h`

## 概述

SubRunData 是 Skia Graphite 渲染后端中用于表示文本字形图集子运行（Atlas SubRun Subspan）的几何类型。它封装了来自持久化字形图集纹理的逐像素覆盖率数据，代表一个 `AtlasSubRun` 的一个子跨度。

与 `CoverageMaskShape`（处理非字形的覆盖率遮罩）不同，SubRunData 专门用于字体渲染管线。它存储了字形索引范围、亮度颜色、距离场表参数、像素几何等文本渲染特有的属性，并持有对 Recorder 和底层文本数据的引用。

## 架构位置

```
Graphite 文本渲染管线
  -> Geometry (几何容器)
    -> SubRunData (图集子运行数据)
      -> AtlasSubRun (文本子运行引用)
      -> Recorder (录制器引用)
      -> RendererData (渲染器数据)
```

SubRunData 连接了 Skia 的文本管线（`sktext::gpu`）和 Graphite 的几何系统，是文本绘制操作在 Graphite 中的内部表示。

## 主要类与结构体

### `SubRunData`
- **职责**: 封装文本图集子运行的所有绘制参数
- **禁用的操作**: 默认构造函数和移动操作被删除，强制通过完整构造函数初始化
- **坐标空间**: bounds() 代表整个 AtlasSubRun 的边界，不直接映射到子跨度的局部坐标

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `SubRunData(subRun, keepAlive, bounds, ...)` | 完整构造函数（11 个参数） |
| `bounds()` | 返回原始 AtlasSubRun 的设备空间边界 |
| `deviceToLocal()` | 返回设备到局部空间的逆矩阵 |
| `subRun()` | 获取 AtlasSubRun 的原始指针 |
| `startGlyphIndex()` | 子跨度的起始字形索引 |
| `glyphCount()` | 子跨度中的字形数量 |
| `luminanceColor()` | 亮度颜色（用于 SDF 文本渲染） |
| `useGammaCorrectDistanceTable()` | 是否使用 gamma 校正距离表 |
| `pixelGeometry()` | 像素几何（子像素排列方式） |
| `recorder()` | 关联的 Recorder 实例 |
| `rendererData()` | 渲染器特定数据 |

## 内部实现细节

### 坐标空间分解
SubRunData 的坐标空间经过分解。AtlasSubRun 将 local-to-device 矩阵分解为两部分：
1. 子跨度的尺寸和偏移定义在部分变换后的中间坐标空间
2. 绘制的变换（DrawParams 中的 local-to-device）是剩余的分解变换（通常仅为平移）

着色时的局部坐标通过将最终设备坐标与 `deviceToLocal` 逆矩阵相乘获得。

### 支持数据的生命周期管理
`fSupportDataKeepAlive` 是一个 `sk_sp<SkRefCnt>` 智能指针，用于保持 TextBlob 或 Slug 在 Geometry 使用期间存活。这确保了 `fSubRun` 原始指针始终指向有效内存。

### 成员数据用途分类
- **通用**: `fSubRun`, `fBounds`, `fDeviceToLocal`, `fStartGlyphIndex`, `fGlyphCount`, `fRecorder`, `fRendererData`
- **SDF 专用**: `fLuminanceColor`, `fUseGammaCorrectDistanceTable`（仅 SDFTextRenderStep 使用）
- **LCD SDF 专用**: `fPixelGeometry`（仅 SDFTextLCDRenderStep 使用）

### Recorder 绑定
`fRecorder` 指针表示此 SubRunData 只能与特定 Recorder 的图集关联，防止跨 Recorder 共享图集数据。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `src/text/gpu/SubRunContainer.h` | AtlasSubRun 和 RendererData 类型 |
| `src/gpu/graphite/geom/Rect.h` | 边界矩形 |
| `include/core/SkM44.h` | 4x4 变换矩阵 |
| `include/core/SkColor.h` | SkColor 类型（亮度颜色） |
| `include/core/SkSurfaceProps.h` | SkPixelGeometry 类型 |
| `include/core/SkRefCnt.h` | sk_sp 智能指针 |

## 设计模式与设计决策

1. **值语义**: 支持拷贝构造和拷贝赋值，但禁用移动操作和默认构造，与其他几何类型保持一致的约定。

2. **原始指针 + 生命周期守卫**: `fSubRun` 使用原始指针以避免额外的引用计数开销，通过 `fSupportDataKeepAlive` 确保底层对象不被过早释放。

3. **参数分类存储**: 虽然某些参数仅在特定渲染步骤中使用（如 SDF 相关参数），但统一存储在 SubRunData 中，避免了运行时多态的复杂性。

## 性能考量

1. **对象大小**: SubRunData 包含较多成员（SkM44 为 64 字节、Rect 为 16 字节等），总大小约 150+ 字节。由于文本绘制操作通常数量有限，这不构成显著内存压力。
2. **拷贝开销**: 拷贝 SubRunData 会拷贝 SkM44（64 字节）和 sk_sp（引用计数操作），但这些操作发生频率较低。
3. **Recorder 指针**: 直接存储原始指针避免了引用计数开销，假设 Recorder 的生命周期长于 SubRunData。

## 相关文件

- `src/gpu/graphite/geom/Geometry.h` - 包含 SubRunData 的几何容器
- `src/gpu/graphite/geom/CoverageMaskShape.h` - 类似的覆盖率遮罩机制（非字形）
- `src/text/gpu/SubRunContainer.h` - 文本子运行容器和 AtlasSubRun 定义
- `src/gpu/graphite/Recorder.h` - 与 SubRunData 关联的录制器
- `src/gpu/graphite/Device.h` - 创建文本绘制操作
