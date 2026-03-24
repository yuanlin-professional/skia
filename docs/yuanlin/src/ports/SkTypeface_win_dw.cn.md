# DWriteFontTypeface - Windows DirectWrite 字体类型

> 源文件:
> - `src/ports/SkTypeface_win_dw.h`
> - `src/ports/SkTypeface_win_dw.cpp`

## 概述

`DWriteFontTypeface` 是 Skia 在 Windows 平台上基于 DirectWrite 框架实现的字体类型类。它封装了多个版本的 `IDWriteFontFace` 接口（从 1 到 7），提供了字体元数据访问、字形映射、变体轴支持、调色板管理以及序列化/反序列化功能。

该实现处理了 DirectWrite 各版本 API 的渐进式可用性，通过 COM `QueryInterface` 按需获取新版接口，并在运行时优雅降级。

## 架构位置

```
SkTypeface (include/core/)
  |
  v
DWriteFontTypeface (src/ports/)        // 本类
  |
  +-- IDWriteFontFace / 1-7            // DirectWrite 字体面接口
  +-- IDWriteFactory / 2               // DirectWrite 工厂
  +-- SkScalerContext_DW               // 字形缩放上下文
  +-- Loaders (内部结构体)              // 自定义字体加载器
```

## 主要类与结构体

### `DWriteFontTypeface::Loaders`

管理自定义字体文件和集合加载器的生命周期。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFactory` | `IDWriteFactory*` | 注册加载器的工厂 |
| `fDWriteFontFileLoader` | `IDWriteFontFileLoader*` | 字体文件加载器 |
| `fDWriteFontCollectionLoader` | `IDWriteFontCollectionLoader*` | 字体集合加载器 |

析构函数负责从工厂注销加载器。

### `DWriteFontTypeface`

继承自 `SkTypeface`。

**DirectWrite 接口成员：**

| 成员 | 说明 |
|------|------|
| `fFactory` / `fFactory2` | DWrite 工厂接口 |
| `fDWriteFontFamily` | 字体族 |
| `fDWriteFont` | 字体对象 |
| `fDWriteFontFace` / 1-5 / 7 | 字体面接口（各版本） |
| `fIsColorFont` | 是否为彩色字体 |

**调色板相关成员：**

| 成员 | 说明 |
|------|------|
| `fRequestedPalette` | 请求的调色板参数 |
| `fPaletteEntryCount` | 调色板条目数 |
| `fPalette` | SkColor 格式调色板 |
| `fDWPalette` | DWRITE_COLOR_F 格式调色板 |

## 公共 API 函数

### `DWriteFontTypeface::Make()`

```cpp
static sk_sp<DWriteFontTypeface> Make(
    IDWriteFactory* factory, IDWriteFontFace* fontFace,
    IDWriteFont* font, IDWriteFontFamily* fontFamily,
    sk_sp<Loaders> loaders, const SkFontArguments::Palette& palette);
```

### `DWriteFontTypeface::GetStyle()`

```cpp
static SkFontStyle GetStyle(IDWriteFont* font, IDWriteFontFace* fontFace);
```

从 DirectWrite 字体对象提取样式。对于变体字体，直接读取 weight/width/slant 轴的值而非使用 `IDWriteFont::GetWeight()` 等方法。

### `MakeFromStream()`

```cpp
static sk_sp<SkTypeface> MakeFromStream(std::unique_ptr<SkStreamAsset>,
                                         const SkFontArguments&);
```

## 内部实现细节

### 构造函数接口查询

构造函数依次通过 `QueryInterface` 获取 `IDWriteFontFace1` 到 `IDWriteFontFace7`。失败时确保指针为 nullptr。`IDWriteFontFace7` 因 WDK 版本限制使用裸指针而非智能指针。

### 调色板初始化

`initializePalette()` 处理 COLR 字体的调色板：
1. 使用基础调色板索引读取调色板条目
2. 将 `DWRITE_COLOR_F` 转换为 `SkColor`
3. 应用用户请求的条目覆盖
4. 超范围的调色板索引被视为 0（遵循 CSS Fonts 4 规范）

### 变体轴支持

- `onGetVariationDesignPosition()`：通过 `IDWriteFontFace5` 获取当前变体位置，过滤仅返回可变轴
- `onGetVariationDesignParameters()`：获取轴的范围和默认值信息
- `onMakeClone()`：创建具有新变体参数的字体克隆

### 字体描述符

`onGetFontDescriptor()` 序列化以下信息：
- 字体族名称
- 字体样式
- 调色板索引和覆盖
- 合成粗体/斜体状态
- 工厂 ID（`'dwrt'`）

### 资源名称

`onGetResourceName()` 通过 `IDWriteLocalFontFileLoader` 获取本地字体文件路径。

## 依赖关系

### DirectWrite 接口

- `IDWriteFontFace` 到 `IDWriteFontFace7`
- `IDWriteFontFace5::HasVariations()`、`GetFontAxisValues()` 等
- `IDWriteFontResource`：字体资源（轴属性查询）

### Skia 内部

- `SkTypeface`：基类
- `SkScalerContext_DW`：缩放上下文
- `SkAdvancedTypefaceMetrics`：高级度量
- sfnt 表工具：`SkOTTable_OS_2`、`SkOTTable_fvar`、`SkOTTable_head` 等

## 设计模式与设计决策

1. **渐进式接口发现**：通过 `QueryInterface` 逐版本查询，运行时优雅降级
2. **Loaders 生命周期管理**：使用引用计数的 `Loaders` 结构体管理自定义加载器
3. **`IDWriteFontFace7` 裸指针**：因 WDK/NTDDI_VERSION 兼容性限制，使用裸指针而非智能指针
4. **`weak_dispose()` 重写**：在弱引用释放时清理 `fLoaders`
5. **调色板覆盖**：完全遵循 CSS Fonts 4 规范的调色板处理语义

## 性能考量

1. **接口查询缓存**：所有 `IDWriteFontFace` 版本在构造时一次性查询并缓存
2. **变体轴过滤**：`onGetVariationDesignPosition` 仅返回可变轴，跳过固定轴
3. **调色板初始化延迟**：仅彩色字体执行调色板初始化
4. **等宽字体检测**：构造时通过 `IDWriteFontFace1::IsMonospacedFont()` 设置

### COM 接口查询链

构造函数中的接口查询顺序：

```
IDWriteFontFace (基础接口)
  |
  +-- QueryInterface -> IDWriteFontFace1 (等宽检测)
  +-- QueryInterface -> IDWriteFontFace2 (彩色字体、调色板)
  +-- QueryInterface -> IDWriteFontFace3 (字体族名、信息字符串)
  +-- QueryInterface -> IDWriteFontFace4 (线程安全判断)
  +-- QueryInterface -> IDWriteFontFace5 (变体轴、HasVariations)
  +-- QueryInterface -> IDWriteFontFace7 (COLRv1, 裸指针)

IDWriteFactory
  |
  +-- QueryInterface -> IDWriteFactory2 (灰度抗锯齿)
```

每个查询失败后对应的智能指针被断言为 nullptr，后续代码通过检查指针是否非空来决定功能可用性。

### 变体轴过滤逻辑

`onGetVariationDesignPosition()` 不返回所有轴，而是仅返回 "可变" 轴：

```cpp
for (UINT32 i = 0; i < fontAxisCount; ++i) {
    if (fontResource->GetFontAxisAttributes(i) & DWRITE_FONT_AXIS_ATTRIBUTES_VARIABLE) {
        ++variableAxisCount;
    }
}
```

固定轴（如某些字体中的 ital 轴只有 0 和 1 两个值）被排除在外。

### 字体样式获取（变体字体特殊处理）

`GetStyle()` 对变体字体使用轴值而非字体对象的属性：

- `DWRITE_FONT_AXIS_TAG_WEIGHT` -> SkFontStyle weight
- `DWRITE_FONT_AXIS_TAG_WIDTH` -> 通过 `SkFontStyleWidthForWidthAxisValue()` 转换
- `DWRITE_FONT_AXIS_TAG_SLANT` -> Oblique（非零值）或 Upright（零值），但不覆盖已知的 Italic

### Loaders 注销

`Loaders::~Loaders()` 负责注销自定义加载器，即使某个注销失败也会继续处理其余注销操作，以最大程度释放资源。

### FactoryId 常量

```cpp
static constexpr SkTypeface::FactoryId FactoryId = SkSetFourByteTag('d','w','r','t');
```

`'dwrt'` 标识 DirectWrite 来源的字体。

## 相关文件

- `src/ports/SkScalerContext_win_dw.h` - DirectWrite 缩放上下文
- `src/utils/win/SkDWrite.h` - DirectWrite 工具函数
- `src/utils/win/SkTScopedComPtr.h` - COM 智能指针
- `src/utils/win/SkDWriteFontFileStream.h` - 字体文件流
- `src/core/SkFontDescriptor.h` - 字体描述符
- `src/sfnt/SkOTTable_fvar.h` - fvar（字体变体）表
- `src/sfnt/SkOTTable_OS_2.h` - OS/2 度量表
