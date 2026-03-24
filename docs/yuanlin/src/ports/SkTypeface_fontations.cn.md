# SkTypeface_fontations

> 源文件: include/ports/SkTypeface_fontations.h, src/ports/SkTypeface_fontations.cpp

## 概述

SkTypeface_fontations 是 Skia 图形库基于 Rust Fontations 库实现的字体渲染后端。Fontations 是 Google Fonts 团队开发的纯 Rust 字体解析和渲染引擎，该模块通过 C++ 与 Rust FFI（外部函数接口）桥接，为 Skia 提供现代化的字体支持，包括变体字体（Variable Fonts）、彩色字体（COLRv0/v1）、位图字体（PNG Emoji）、TrueType/CFF 轮廓提示（Hinting）和自动提示（AutoHinting）。相比传统的 FreeType 后端，Fontations 提供更安全的内存管理和更现代的字体特性支持。

## 架构位置

该模块位于 Skia 的平台适配层（ports），作为可选的字体渲染后端：

```
skia/
├── include/ports/
│   └── SkTypeface_fontations.h           # 公共工厂接口
└── src/ports/
    ├── SkTypeface_fontations.cpp         # 实现文件（1709 行）
    ├── SkTypeface_fontations_priv.h      # 私有接口
    └── fontations/
        └── src/skpath_bridge.h           # Rust FFI 桥接
```

该模块通过 Rust CXX 工具生成的 `fontations_ffi` 命名空间与 Rust 代码交互。

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|------|---------|------|
| `SkTypeface_Fontations` | `SkTypeface` | Fontations 后端的 typeface 实现 |
| `SkFontationsScalerContext` | `SkScalerContext` | 字形缩放和渲染上下文 |
| `ColorPainter` | `fontations_ffi::ColorPainter` | 彩色字体渲染器 |
| `BoundsPainter` | `fontations_ffi::ColorPainter` | 边界计算渲染器 |
| `AxisWrapper` | - | 变体轴参数包装器 |

### 关键成员变量

**SkTypeface_Fontations:**
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFontData` | `sk_sp<const SkData>` | 字体文件原始数据 |
| `fTtcIndex` | `uint32_t` | TrueType Collection 索引 |
| `fBridgeFontRef` | `rust::Box<BridgeFontRef>` | Rust 字体引用 |
| `fMappingIndex` | `rust::Box<BridgeMappingIndex>` | 字符到字形映射索引 |
| `fBridgeNormalizedCoords` | `rust::Box<BridgeNormalizedCoords>` | 归一化变体坐标 |
| `fOutlines` | `rust::Box<BridgeOutlineCollection>` | 轮廓数据集合 |
| `fGlyphStyles` | `rust::Box<BridgeGlyphStyles>` | 自动提示样式缓存 |
| `fPalette` | `rust::Vec<uint32_t>` | 彩色字体调色板 |

**SkFontationsScalerContext:**
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fScale` | `SkVector` | 缩放因子 |
| `fRemainingMatrix` | `SkMatrix` | 剩余变换矩阵 |
| `fHintingInstance` | `rust::Box<BridgeHintingInstance>` | 提示实例 |
| `fDoLinearMetrics` | `bool` | 是否使用线性度量 |
| `fPathVerbs` | `rust::Vec<uint8_t>` | 路径操作码缓冲区 |
| `fPathPoints` | `rust::Vec<FfiPoint>` | 路径点缓冲区 |

## 公共 API 函数

### 工厂函数

```cpp
SK_API sk_sp<SkTypeface> SkTypeface_Make_Fontations(
    std::unique_ptr<SkStreamAsset> fontData,
    const SkFontArguments& args
);

SK_API sk_sp<SkTypeface> SkTypeface_Make_Fontations(
    sk_sp<const SkData> fontData,
    const SkFontArguments& args
);
```

从字体数据流或字节数组创建 Fontations typeface，支持以下参数：

- **Collection Index**: TTC 文件中的字体索引（包含命名实例）
- **Variation Position**: 变体轴坐标
- **Palette**: 彩色字体调色板索引和覆盖

### SkTypeface 接口实现

```cpp
// 字体属性
int onGetUPEM() const override;
void onGetFamilyName(SkString* familyName) const override;
bool onGetPostScriptName(SkString* postscriptName) const override;
bool onGlyphMaskNeedsCurrentColor() const override;

// 字形操作
void onCharsToGlyphs(SkSpan<const SkUnichar> chars, SkSpan<SkGlyphID> glyphs) const override;
int onCountGlyphs() const override;
void getGlyphToUnicodeMap(SkSpan<SkUnichar> codepointForGlyphMap) const override;

// 字体元数据
std::unique_ptr<SkAdvancedTypefaceMetrics> onGetAdvancedMetrics() const override;
int onGetVariationDesignPosition(SkSpan<...> coordinates) const override;
int onGetVariationDesignParameters(SkSpan<...> parameters) const override;
```

## 内部实现细节

### Rust FFI 桥接

通过 CXX 库实现 C++ 和 Rust 的双向调用：

1. **类型对齐**: 使用 `static_assert` 确保 C++ 和 Rust 结构体布局一致
   ```cpp
   static_assert(sizeof(fontations_ffi::SkiaDesignCoordinate) ==
                 sizeof(SkFontArguments::VariationPosition::Coordinate));
   ```

2. **Rust Box 包装**: Rust 对象通过 `rust::Box` 跨越语言边界，自动管理生命周期
3. **Slice 传递**: 使用 `rust::Slice` 实现零拷贝数据传递

### 命名实例处理

支持 FreeType 兼容的命名实例编码（集合索引高 16 位）：

```cpp
if (args.getCollectionIndex() & 0xFFFF0000) {
    // 从命名实例提取变体坐标
    size_t numCoords = fontations_ffi::coordinates_for_shifted_named_instance_index(
        *bridgeFontRef, args.getCollectionIndex(), targetSlice);
    // 与用户坐标合并，用户坐标可覆盖命名实例值
    for (int i = 0; i < variationPosition.coordinateCount; ++i) {
        concatenatedCoords[numNamedInstanceCoords + i] = variationPosition.coordinates[i];
    }
}
```

### 提示策略选择

`SkFontationsScalerContext` 构造函数实现复杂的提示决策逻辑：

```cpp
// 1. 检测提示依赖字体（必须启用提示）
if (fontations_ffi::hinting_reliant(fOutlines)) {
    fHintingInstance = fontations_ffi::make_mono_hinting_instance(...);
    fDoLinearMetrics = false;
}
// 2. 黑白模式
else if (SkMask::kBW_Format == fRec.fMaskFormat) {
    if (fRec.getHinting() == SkFontHinting::kNone) {
        fHintingInstance = fontations_ffi::no_hinting_instance();
    } else {
        fHintingInstance = fontations_ffi::make_mono_hinting_instance(...);
    }
}
// 3. 抗锯齿模式
else {
    switch (fRec.getHinting()) {
        case SkFontHinting::kNone: /* 无提示 */
        case SkFontHinting::kSlight: /* 轻提示 + 自动提示 */
        case SkFontHinting::kNormal: /* 标准提示 */
        case SkFontHinting::kFull: /* 完整提示 + LCD 抗锯齿 */
    }
}
```

提示参数：
- `do_light_hinting`: kSlight 模式启用
- `do_lcd_antialiasing`: kFull 模式且 LCD 格式启用
- `lcd_orientation_vertical`: LCD 垂直方向标志
- `autoHintingControl`: 自动提示策略（ForceForGlyfAndCff、Fallback、ForceOff）

### 彩色字体渲染

#### COLRv0/v1 支持

`drawCOLRGlyph` 实现完整的 COLR 表渲染：

```cpp
bool drawCOLRGlyph(const SkGlyph& glyph, SkColor foregroundColor, SkCanvas* canvas) {
    // 1. 计算缩放矩阵 (UPEM -> 像素)
    SkMatrix scalerMatrix = fRec.getSingleMatrix();
    SkMatrix upemToPpem = SkMatrix::Scale(1.f / upem, 1.f / upem);
    scalerMatrix.preConcat(upemToPpem);

    // 2. 创建 ColorPainter 执行渲染
    ColorPainter colorPainter(*this, *canvas, fPalette, foregroundColor, ...);

    // 3. 调用 Rust 侧绘制逻辑
    return fontations_ffi::draw_colr_glyph(
        fBridgeFontRef, fBridgeNormalizedCoords, glyph.getGlyphID(), colorPainter);
}
```

`ColorPainter` 实现回调接口：
- `push_transform` / `pop_transform`: 变换栈管理
- `push_clip_glyph` / `push_clip_rectangle` / `pop_clip`: 裁剪管理
- `fill_solid` / `fill_glyph_solid`: 纯色填充
- `fill_linear` / `fill_glyph_linear`: 线性渐变
- `fill_radial` / `fill_glyph_radial`: 径向渐变（处理负半径情况）
- `fill_sweep` / `fill_glyph_sweep`: 扫描渐变
- `push_layer` / `pop_layer`: 合成模式（支持 27 种 COLR 合成模式）

#### 位图字体支持

`generatePngImage` 处理 sbix、CBDT 等 PNG 位图字形：

```cpp
void generatePngImage(const SkGlyph& glyph, void* imageBuffer) {
    // 1. 从 Rust 获取 PNG 数据
    rust::cxxbridge1::Box<fontations_ffi::BridgeBitmapGlyph> bitmap_glyph =
        fontations_ffi::bitmap_glyph(fBridgeFontRef, glyph.getGlyphID(), fScale.y());
    rust::cxxbridge1::Slice<const uint8_t> png_data = fontations_ffi::png_data(*bitmap_glyph);

    // 2. 解码 PNG（需要注册 PNG 编解码器）
    sk_sp<SkImage> glyph_image = SkImages::DeferredFromEncodedData(...);

    // 3. 应用缩放和偏移
    float imageToSize = fScale.y() / bitmapMetrics.ppem_y;
    canvas.translate(bitmapMetrics.bearing_x * fontUnitsToSize, ...);
    canvas.scale(imageToSize, imageToSize);

    // 4. 绘制到目标缓冲区
    canvas.drawImage(glyph_image, 0, 0, sampling);
}
```

### 路径提取优化

使用持久化缓冲区减少分配开销：

```cpp
std::optional<SkPath> generatePathForGlyphId(...) {
    SkAutoMutexExclusive l(fPathMutex);  // 线程安全保护
    SK_AT_SCOPE_EXIT(fontations_ffi::shrink_verbs_points_if_needed(fPathVerbs, fPathPoints));

    // Rust 侧直接写入 C++ 缓冲区
    fontations_ffi::get_path_verbs_points(fOutlines, glyphId, yScale, ...
                                          fPathVerbs, fPathPoints, scalerMetrics);

    // 零拷贝构造 SkPath
    return SkPath::Make({reinterpret_cast<const SkPoint*>(fPathPoints.data()),
                         fPathPoints.size()},
                        fPathVerbs, {}, SkPathFillType::kWinding);
}
```

### 调色板处理

支持 CPAL 表和用户覆盖：

```cpp
rust::Slice<const fontations_ffi::PaletteOverride> paletteOverrides(
    reinterpret_cast<const ::fontations_ffi::PaletteOverride*>(args.getPalette().overrides),
    args.getPalette().overrideCount);
rust::Vec<uint32_t> palette = resolve_palette(
    *bridgeFontRef, args.getPalette().index, paletteOverrides);
```

调色板在 `onMakeClone` 时比较以决定是否需要创建新实例。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| Rust Fontations (fontations_ffi) | 字体解析、轮廓提取、提示、彩色字体 |
| CXX 库 | C++/Rust FFI 桥接 |
| `SkFontDescriptor` | 字体描述符序列化 |
| `SkScalerContext` | 字形缩放框架 |
| `SkCanvas` / `SkPaint` | 彩色字体渲染 |
| `SkCodec` | PNG 位图字形解码 |
| `SkGradient` | 渐变着色器 |

### 被依赖的模块

该模块通过 SkFontMgr 被字体管理系统使用，可作为 FreeType 的替代后端。

## 设计模式与设计决策

### 设计模式

1. **工厂模式**: `SkTypeface_Make_Fontations` 工厂函数
2. **桥接模式**: C++ 与 Rust 通过 FFI 桥接
3. **策略模式**: 多种提示策略动态选择
4. **访问者模式**: ColorPainter 回调接口
5. **缓存模式**: 路径缓冲区复用

### 设计决策

1. **Rust 实现**: 利用 Rust 的内存安全特性，避免缓冲区溢出等安全问题
2. **FreeType 兼容**: 匹配 FreeType 的渲染质量和行为
3. **自动提示**: 支持 Skrifa 的自动提示算法，改进无提示指令字体的渲染
4. **COLRv1 优先**: 彩色字形优先使用矢量 COLRv1，回退到 v0 或位图
5. **线程安全**: 路径提取使用互斥锁保护（COLRv1 可多线程调用）
6. **零拷贝**: 尽可能使用 Slice 和直接缓冲区写入

### 平台特定行为

#### Android Framework
```cpp
#ifdef SK_BUILD_FOR_ANDROID_FRAMEWORK
if (!forceAutoHinting)
    autoHintingControl = AutoHinting::ForceOff;  // 禁用自动提示除非强制
#endif
```

#### 像素几何处理
```cpp
// 匹配 FreeType 行为：未知像素几何时忽略 LCD 到 A8 的降级
rec->fFlags &= ~SkScalerContext::kGenA8FromLCD_Flag;
```

## 性能考量

### 性能优势

1. **Rust 优化**: LLVM 编译器对 Rust 的优化效果通常优于 C（FreeType）
2. **缓冲区复用**: 路径缓冲区跨字形复用，减少分配
3. **零拷贝数据传递**: Slice 和直接缓冲区操作
4. **并行潜力**: Rust 的安全并发模型支持未来并行化
5. **SIMD**: Fontations 可利用自动向量化

### 内存优化

- **共享字体数据**: `fFontData` 引用计数共享
- **Rust Box**: 自动释放 Rust 对象，无内存泄漏
- **延迟解析**: 仅在需要时解析字体表

### 潜在瓶颈

1. **FFI 开销**: 频繁跨语言调用有小幅开销
2. **路径锁竞争**: `fPathMutex` 在多线程场景可能成为瓶颈
3. **PNG 解码**: 位图字形需要解码 PNG，比矢量慢
4. **COLRv1 复杂度**: 复杂的 COLRv1 字形有较高渲染成本

### 优化建议

- 缓存常用字形的渲染结果
- 批量字形查询减少 FFI 调用
- 使用 Drawable 延迟 COLR 渲染

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/ports/SkTypeface_fontations.h` | 公共工厂接口 |
| `src/ports/SkTypeface_fontations.cpp` | 主实现文件（1709 行）|
| `src/ports/SkTypeface_fontations_priv.h` | 私有接口和辅助类 |
| `src/ports/fontations/src/skpath_bridge.h` | Rust FFI 桥接头文件 |
| `include/core/SkTypeface.h` | Typeface 抽象基类 |
| `src/core/SkScalerContext.h` | 字形缩放上下文 |
| `include/core/SkFontArguments.h` | 字体参数（变体、调色板）|
| `include/effects/SkGradient.h` | 渐变着色器 |
