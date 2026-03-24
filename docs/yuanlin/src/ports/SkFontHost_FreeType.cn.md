# SkFontHost_FreeType

> 源文件: [src/ports/SkFontHost_FreeType.cpp](../../../../src/ports/SkFontHost_FreeType.cpp)

## 概述

本文件是 Skia 中最核心、最庞大的字体渲染实现文件（约 2466 行），基于 FreeType 库提供完整的字体光栅化、度量计算、路径生成和彩色字形渲染能力。它包含了 FreeType 库的生命周期管理、字体面的加载与缓存、`SkScalerContext` 的完整实现（字形度量、图像生成、路径生成、字体度量等），以及 `SkFontScanner_FreeType` 的字体扫描和变体轴计算功能。

## 架构位置

本文件是 Skia 字体渲染管线中从字体数据到像素输出的关键中间层：

```
SkTypeface (字体面抽象)
  └── SkTypeface_FreeType (FreeType 特化)
        ├── FaceRec (FT_Face 生命周期管理)
        └── SkScalerContext_FreeType (本文件核心: 字形光栅化)
              ├── generateMetrics()    — 字形度量
              ├── generateImage()      — 位图渲染
              ├── generatePath()       — 轮廓路径
              ├── generateDrawable()   — COLRv0/v1/SVG 可绘制对象
              └── generateFontMetrics() — 字体级度量

SkFontScanner
  └── SkFontScanner_FreeType (字体扫描 & 变轴计算)
```

## 主要类与结构体

### FreeTypeLibrary

不可拷贝的 FreeType 库封装类。负责:
- 初始化 FT_Library 并添加默认模块
- 设置 LCD 滤波器默认值
- 析构时释放库资源

### SkTypeface_FreeType::FaceRec

字体面记录，管理 FT_Face 的生命周期:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFace` | `SkUniqueFTFace` | FreeType 字体面（智能指针管理） |
| `fFTStream` | `FT_StreamRec` | FreeType 流记录 |
| `fSkStream` | `unique_ptr<SkStreamAsset>` | Skia 流（保持数据存活） |
| `fFTPaletteEntryCount` | `FT_UShort` | 调色板条目数 |
| `fSkPalette` | `unique_ptr<SkColor[]>` | Skia 格式调色板 |

关键方法:
- `Make()`: 从 typeface 创建 FaceRec，处理流加载、变轴设置和调色板
- `ref_ft_library()` / `unref_ft_library()`: FreeType 库的引用计数管理

### AutoFTAccess

RAII 风格的 FT_Face 访问守卫，在构造时获取互斥锁，析构时释放:
```cpp
AutoFTAccess fta(typeface);
FT_Face face = fta.face();
```

### SkScalerContext_FreeType

`SkScalerContext` 的 FreeType 实现，是字形渲染的核心:

| 成员 | 说明 |
|------|------|
| `fFaceRec` | 借用的 FaceRec 指针 |
| `fFace` | 借用的 FT_Face |
| `fFTSize` | 当前使用的 FT_Size |
| `fStrikeIndex` | 位图 strike 索引 (-1 表示无) |
| `fMatrix22Scalar` / `fMatrix22` | 变换矩阵 (Skia/FreeType 格式) |
| `fScale` | 实际请求的缩放尺寸 |
| `fLoadGlyphFlags` | FT_Load_Glyph 标志位组合 |

### ScalerContextBits

标记字形类型的位标志:
- `COLRv0 = 1`: COLRv0 彩色字形
- `COLRv1 = 2`: COLRv1 彩色字形
- `SVG = 3`: SVG 字形

## 公共 API 函数

### SkTypeface_FreeType 方法

| 方法 | 功能 |
|------|------|
| `onGetAdvancedMetrics()` | 获取高级排版度量（PostScript 名称、嵌入/子集标志等） |
| `getGlyphToUnicodeMap()` | 建立字形 ID 到 Unicode 码点的映射 |
| `getPostScriptGlyphNames()` | 获取所有字形的 PostScript 名称 |
| `onGetPostScriptName()` | 获取字体的 PostScript 名称 |
| `onCreateScalerContext()` | 创建字形缩放上下文 |
| `onFilterRec()` | 过滤和调整缩放器参数 |
| `onGetUPEM()` | 获取字体的 units-per-em |
| `onGetKerningPairAdjustments()` | 获取字距调整值 |
| `onCharsToGlyphs()` | Unicode 到字形 ID 的映射 |
| `onCountGlyphs()` | 获取字形数量 |
| `onGetVariationDesignPosition()` | 获取当前变体坐标 |
| `onGetVariationDesignParameters()` | 获取变体轴参数定义 |
| `onGetTableTags()` / `onGetTableData()` / `onCopyTableData()` | SFNT 表数据访问 |
| `cloneFontData()` | 克隆字体数据并应用新的变体参数 |
| `MakeFromStream()` | 从字体流创建 typeface |

### SkScalerContext_FreeType 方法

| 方法 | 功能 |
|------|------|
| `generateMetrics()` | 计算单个字形的度量信息（边界、advance 等） |
| `generateImage()` | 将字形渲染为位图/ARGB 图像 |
| `generatePath()` | 提取字形的轮廓路径 |
| `generateDrawable()` | 生成可绘制对象 (COLRv0/v1/SVG) |
| `generateFontMetrics()` | 计算字体级度量 (ascent, descent 等) |

### SkFontScanner_FreeType 方法

| 方法 | 功能 |
|------|------|
| `scanFile()` | 扫描文件获取字体面数量 |
| `scanFace()` | 扫描字体面获取命名实例数 |
| `scanInstance()` | 扫描实例获取完整元数据 |
| `computeAxisValues()` | 计算变体轴值（合并默认、当前和请求的坐标） |

## 内部实现细节

### FreeType 库管理

- 全局 FreeType 库 (`gFTLibrary`) 使用引用计数管理
- 全局互斥锁 (`f_t_mutex()`) 保护所有 FreeType 操作（FreeType 在 2.6.0 之前非线程安全）
- 自定义内存分配器 (`sk_ft_alloc/free/realloc`) 将 FreeType 的分配重定向到 Skia 的分配器

### 字形度量生成 (generateMetrics)

复杂的多路径处理:
1. **COLRv1 字形**: 检查 ClipBox，或遍历字形图计算边界
2. **COLRv0 字形**: 遍历所有图层，合并轮廓边界
3. **轮廓字形**: 获取轮廓的 CBox
4. **位图字形**: 使用位图尺寸，处理垂直布局偏移
5. **SVG 字形**: 通过录制绘制获取 cullRect
6. **advance 计算**: 区分线性度量和 hinted 度量，支持水平和垂直布局

### Hinting 策略

在 `onFilterRec()` 中:
- 非 LCD 模式下将 Full hinting 降级为 Normal
- 非轴对齐变换时禁用 hinting
- 支持 FreeType 的 Light/Normal/LCD/LCD_V 多种 hinting 模式

### 变体轴值计算 (computeAxisValues)

三层优先级合并:
1. 轴默认值 (`def`)
2. 当前字体的实际坐标
3. 用户请求的坐标（最高优先级）

从轴值推导字体样式:
- `wght` 轴 -> weight
- `wdth` 轴 -> width (经过 SkFontStyleWidthForWidthAxisValue 转换)
- `slnt`/`ital` 轴 -> slant (复杂的组合逻辑)

### 字符到字形缓存 (onCharsToGlyphs)

使用两级锁优化:
1. 先用共享锁 (`SkAutoSharedMutexShared`) 查询缓存
2. 缓存未命中时升级为独占锁 (`SkAutoSharedMutexExclusive`) 并访问 FreeType
3. 缓存超过 512 条目时重置

### 位图 strike 选择 (chooseBitmapStrike)

选择策略: 找到等于或刚好大于请求尺寸的 strike。精确匹配时直接返回，否则选择最接近的较大 strike。

### 字形加粗 (emboldenIfNeeded)

- 轮廓字形: 使用 `FT_Outline_Embolden()`，加粗强度 = upem * y_scale / 除数
- 位图字形: 使用 `FT_Bitmap_Embolden()`，固定 1/64 像素的加粗量
- Android Framework 上除数为 34 (更轻)，其他平台为 24

## 依赖关系

### Skia 核心依赖
- `SkScalerContext`, `SkGlyph`, `SkFontMetrics`, `SkPath`, `SkBitmap`, `SkCanvas` 等

### FreeType 头文件
- `freetype.h`, `ftcolor.h`, `ftmm.h`, `ftoutln.h`, `ftlcdfil.h`, `tttables.h`, `t1tables.h` 等

### 条件编译依赖
- `FT_COLOR_H` — COLRv0/v1 彩色字形支持
- `TT_SUPPORT_COLRV1` — COLRv1 扩展支持 (需 FreeType >= 2.11.1)
- `FT_CONFIG_OPTION_SVG` — SVG 字形支持
- `SK_FREETYPE_DLOPEN` — 运行时动态加载新特性

## 设计模式与设计决策

1. **互斥锁保护**: 全局 `f_t_mutex()` 序列化所有 FreeType 调用，确保线程安全
2. **引用计数库管理**: FreeType 库在最后一个使用者释放后自动销毁
3. **自定义流 I/O**: 通过 `FT_Stream` 回调将 Skia 的 `SkStreamAsset` 桥接到 FreeType
4. **自定义内存分配**: 将 FreeType 的分配器重定向到 Skia 的 `sk_malloc`/`sk_free`
5. **RAII 访问控制**: `AutoFTAccess` 确保锁的正确获取和释放
6. **版本兼容**: 大量 `#ifdef` 处理不同 FreeType 版本的 API 差异
7. **C2G 缓存读写锁**: 使用共享/独占锁分离读多写少的字符到字形映射缓存

## 性能考量

- **全局互斥锁**: 是主要的并发瓶颈，所有 FreeType 操作序列化执行
- **C2G 缓存**: 使用 `SkCharToGlyphCache` 和读写锁减少 FreeType 调用频率，缓存上限 512 条
- **线性度量**: 可选使用线性度量避免 hinting 的额外开销
- **位图 strike**: 位图字体避免缩放开销，但需要额外的矩阵调整
- **SkOnce 延迟初始化**: `FaceRec` 和 `glyphMaskNeedsCurrentColor` 使用 `SkOnce` 延迟到首次使用
- **FT_LOAD_BITMAP_METRICS_ONLY**: 在仅需度量时避免完整解码位图
- **内存映射优先**: 流有内存基地址时使用 `FT_OPEN_MEMORY` 避免 I/O 回调开销
- **Drawable 缓存为 Picture**: COLRv0/v1/SVG 字形录制为 SkPicture，避免后续绘制时持锁

## 相关文件

- `src/ports/SkTypeface_FreeType.h` — `SkTypeface_FreeType` 类声明
- `src/ports/SkFontHost_FreeType_common.h` — FreeType 通用工具 (SkScalerContextFTUtils)
- `src/ports/SkFontScanner_FreeType_priv.h` — 扫描器声明
- `src/core/SkScalerContext.h` — 缩放上下文基类
- `src/core/SkGlyph.h` — 字形数据结构
- `src/core/SkAdvancedTypefaceMetrics.h` — 高级排版度量
- `src/sfnt/SkOTUtils.h` — OpenType 工具
- `src/sfnt/SkSFNTHeader.h` / `SkTTCFHeader.h` — 字体文件格式头
