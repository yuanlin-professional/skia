# src/ports - 平台移植层

## 概述

`src/ports` 目录是 Skia 图形引擎的**平台适配层（Platform Abstraction Layer）**，负责将 Skia 的
核心渲染逻辑与底层操作系统、字体引擎、文件系统和内存管理等平台相关功能进行桥接。该目录是 Skia 实现
跨平台能力的关键基础设施，通过抽象接口和条件编译，使得同一套核心渲染代码可以在 Windows、macOS、
iOS、Android、Linux、Fuchsia 等多个操作系统上运行。

ports 目录中最核心的子系统是**字体管理（Font Management）**，它包含了多个字体后端的完整实现，
包括基于 FreeType 的字体栅格化、基于 Apple Core Text 的 macOS/iOS 字体支持、基于 DirectWrite
的 Windows 字体支持、以及基于 Google Fontations Rust 库的新一代字体后端。每种后端都完整实现了
从字体发现（font enumeration）、字形映射（glyph mapping）、轮廓提取（outline extraction）、
度量信息获取（metrics retrieval）到最终栅格化（rasterization）的全流程。

除字体系统外，该目录还提供了操作系统文件 I/O 操作（POSIX 和 Windows 两套实现）、内存分配策略
（标准 malloc 和 Mozilla 定制分配器）、日志输出（Android logcat、Windows Debug Output、
标准 I/O）以及平台特定的图像解码器等功能模块。这些模块通过 Bazel 构建系统中的 `select()` 条件
编译机制，在不同平台上自动选择正确的实现。

该目录还包含一个重要的子目录 `fontations/`，这是 Skia 与 Google Fontations 项目（基于 Rust
编写的字体解析库）的集成桥梁。通过 CXX（C++/Rust 互操作框架），Fontations 后端实现了完全用
Rust 编写的字体解析和渲染逻辑，代表了 Skia 字体系统的未来发展方向。

从架构角度看，`src/ports` 遵循了经典的**策略模式（Strategy Pattern）**和**工厂模式
（Factory Pattern）**，每种平台实现都是对应抽象接口的具体策略，而 `SkFontMgr` 系列工厂类
则负责根据平台环境创建正确的字体管理器实例。

## 架构图

```
+-----------------------------------------------------------------------+
|                          Skia 核心层 (src/core)                        |
|   SkTypeface  |  SkScalerContext  |  SkFontMgr  |  SkFontScanner     |
+-------+-------+---------+---------+------+------+--------+-----------+
        |                 |                |               |
        v                 v                v               v
+-----------------------------------------------------------------------+
|                    src/ports 平台适配层                                 |
|                                                                       |
|  +-------------------+  +-------------------+  +-------------------+  |
|  | FreeType 后端      |  | Core Text 后端    |  | DirectWrite 后端  |  |
|  | (Linux/Android)   |  | (macOS/iOS)       |  | (Windows)        |  |
|  |                   |  |                   |  |                   |  |
|  | SkTypeface_       |  | SkTypeface_Mac    |  | DWriteFont-      |  |
|  |   FreeType        |  | SkScalerContext_  |  |   Typeface        |  |
|  | SkFontHost_       |  |   mac_ct          |  | SkScalerContext_  |  |
|  |   FreeType        |  | SkFontMgr_        |  |   win_dw          |  |
|  | SkFontMgr_custom  |  |   mac_ct          |  | SkFontMgr_win_dw |  |
|  +-------------------+  +-------------------+  +-------------------+  |
|                                                                       |
|  +-------------------+  +-------------------+  +-------------------+  |
|  | Fontations 后端    |  | Android 字体管理  |  | 代理层            |  |
|  | (跨平台 Rust)     |  |                   |  |                   |  |
|  |                   |  | SkFontMgr_android |  | SkTypeface_proxy  |  |
|  | SkTypeface_       |  | SkFontMgr_        |  | SkScalerContext_  |  |
|  |   Fontations      |  |   android_ndk     |  |   proxy           |  |
|  | fontations/src/   |  | SkFontMgr_        |  |                   |  |
|  |   (Rust FFI)      |  |   android_parser  |  |                   |  |
|  +-------------------+  +-------------------+  +-------------------+  |
|                                                                       |
|  +----------------------+  +-------------------+  +----------------+  |
|  | 文件系统 I/O          |  | 内存管理          |  | 日志系统        |  |
|  | SkOSFile_posix.cpp   |  | SkMemory_malloc   |  | SkLog_stdio    |  |
|  | SkOSFile_win.cpp     |  | SkMemory_mozalloc |  | SkLog_android  |  |
|  | SkOSFile_stdio.cpp   |  |                   |  | SkLog_win      |  |
|  +----------------------+  +-------------------+  +----------------+  |
|                                                                       |
|  +-------------------+  +-------------------+  +-------------------+  |
|  | 图像生成器         |  | Fontconfig 集成   |  | Fuchsia 字体管理 |  |
|  | SkImageGenerator-  |  | SkFontMgr_        |  | SkFontMgr_       |  |
|  |   CG/NDK/WIC      |  |   fontconfig      |  |   fuchsia         |  |
|  +-------------------+  +-------------------+  +-------------------+  |
+-----------------------------------------------------------------------+
        |                 |                |               |
        v                 v                v               v
+-----------------------------------------------------------------------+
|                     操作系统 / 第三方库                                 |
|  FreeType | CoreText | DirectWrite | fontconfig | Fontations(Rust)    |
+-----------------------------------------------------------------------+
```

## 目录结构

```
src/ports/
|
|-- BUILD.bazel                          # Bazel 构建规则定义
|
|-- 【FreeType 字体后端】
|   |-- SkFontHost_FreeType.cpp          # FreeType 字形栅格化核心实现
|   |-- SkFontHost_FreeType_common.cpp   # FreeType 公共工具函数
|   |-- SkFontHost_FreeType_common.h     # FreeType 公共头文件
|   |-- SkTypeface_FreeType.h            # FreeType SkTypeface 基类定义
|   |-- SkFontScanner_FreeType_priv.h    # FreeType 字体扫描器私有头文件
|
|-- 【Fontations 字体后端 (Rust)】
|   |-- SkTypeface_fontations.cpp        # Fontations SkTypeface 实现（C++侧）
|   |-- SkTypeface_fontations_priv.h     # Fontations SkTypeface 私有头文件
|   |-- SkTypeface_fontations_factory.h  # Fontations 工厂标识
|   |-- SkFontScanner_fontations.cpp     # Fontations 字体扫描器
|   |-- SkFontScanner_fontations_priv.h  # Fontations 字体扫描器私有头文件
|   |-- SkFontMgr_fontations_empty.cpp   # Fontations 空字体管理器（测试用）
|   |-- fontations/                      # Rust FFI 桥接代码子目录
|       |-- Cargo.toml                   # Rust 项目配置
|       |-- BUILD.bazel                  # Bazel 构建规则
|       |-- src/                         # Rust 源代码
|           |-- ffi.rs                   # CXX 桥接定义入口
|           |-- base.rs                  # 基础字体操作
|           |-- colr.rs                  # COLR 彩色字体支持
|           |-- bitmap.rs               # 位图字体支持（CBDT/sbix）
|           |-- hinting.rs              # 字体微调（hinting）
|           |-- names.rs                # 字体名称表处理
|           |-- verbs_points_pen.rs     # 路径提取（轮廓笔）
|           |-- skpath_bridge.h         # C++ 纯虚接口定义
|
|-- 【macOS/iOS Core Text 后端】
|   |-- SkTypeface_mac_ct.cpp            # Core Text SkTypeface 实现
|   |-- SkTypeface_mac_ct.h              # Core Text SkTypeface 头文件
|   |-- SkScalerContext_mac_ct.cpp       # Core Text 字形缩放上下文
|   |-- SkScalerContext_mac_ct.h         # Core Text ScalerContext 头文件
|   |-- SkFontMgr_mac_ct.cpp            # Core Text 字体管理器
|
|-- 【Windows DirectWrite 后端】
|   |-- SkTypeface_win_dw.cpp            # DirectWrite SkTypeface 实现
|   |-- SkTypeface_win_dw.h              # DirectWrite SkTypeface 头文件
|   |-- SkScalerContext_win_dw.cpp       # DirectWrite 字形缩放上下文
|   |-- SkScalerContext_win_dw.h         # DirectWrite ScalerContext 头文件
|   |-- SkFontMgr_win_dw.cpp            # DirectWrite 字体管理器
|   |-- SkFontHost_win.cpp              # Windows GDI 字体支持（遗留）
|
|-- 【自定义字体管理器（基于 FreeType）】
|   |-- SkFontMgr_custom.cpp             # 自定义字体管理器基类实现
|   |-- SkFontMgr_custom.h               # 自定义字体管理器头文件
|   |-- SkFontMgr_custom_directory.cpp   # 从目录加载字体
|   |-- SkFontMgr_custom_embedded.cpp    # 从嵌入数据加载字体
|   |-- SkFontMgr_custom_empty.cpp       # 空字体集（回退用）
|
|-- 【Android 字体管理】
|   |-- SkFontMgr_android.cpp            # Android 系统字体管理器
|   |-- SkFontMgr_android_ndk.cpp        # Android NDK 字体管理器
|   |-- SkFontMgr_android_parser.cpp     # Android fonts.xml 解析器
|   |-- SkFontMgr_android_parser.h       # Android 字体解析器头文件
|
|-- 【Linux fontconfig 集成】
|   |-- SkFontMgr_fontconfig.cpp         # fontconfig 字体管理器
|   |-- SkFontConfigInterface.cpp        # fontconfig 接口封装
|   |-- SkFontConfigInterface_direct.cpp # fontconfig 直接接口
|   |-- SkFontConfigInterface_direct.h   # fontconfig 直接接口头文件
|   |-- SkFontConfigInterface_direct_factory.cpp  # 工厂函数
|   |-- SkFontConfigTypeface.h           # fontconfig SkTypeface 头文件
|   |-- SkFontMgr_FontConfigInterface.cpp # FontConfig 接口管理器
|
|-- 【代理/间接层】
|   |-- SkTypeface_proxy.cpp             # SkTypeface 代理实现
|   |-- SkTypeface_proxy.h               # SkTypeface 代理头文件
|
|-- 【Fuchsia OS】
|   |-- SkFontMgr_fuchsia.cpp            # Fuchsia 字体管理器
|
|-- 【文件系统 I/O】
|   |-- SkOSFile_posix.cpp               # POSIX 文件操作
|   |-- SkOSFile_win.cpp                 # Windows 文件操作
|   |-- SkOSFile_stdio.cpp               # 标准 I/O 文件操作
|   |-- SkOSFile_ios.h                   # iOS 特殊路径处理
|
|-- 【内存管理】
|   |-- SkMemory_malloc.cpp              # 标准 malloc 内存分配器
|   |-- SkMemory_mozalloc.cpp            # Mozilla 定制内存分配器
|   |-- SkDiscardableMemory_none.cpp     # 无操作可丢弃内存
|
|-- 【日志系统】
|   |-- SkLog_stdio.cpp                  # 标准 I/O 日志（默认）
|   |-- SkLog_android.cpp                # Android logcat 日志
|   |-- SkLog_win.cpp                    # Windows Debug Output 日志
|
|-- 【图像生成器/编码器】
|   |-- SkImageGeneratorCG.cpp           # Core Graphics 图像生成器
|   |-- SkImageGeneratorNDK.cpp          # Android NDK 图像生成器
|   |-- SkImageGeneratorWIC.cpp          # Windows WIC 图像生成器
|   |-- SkImageEncoder_NDK.cpp           # Android NDK 图像编码器
|
|-- 【NDK 工具】
|   |-- SkNDKConversions.cpp             # Android NDK 类型转换
|   |-- SkNDKConversions.h               # Android NDK 转换头文件
|
|-- 【全局初始化】
    |-- SkGlobalInitialization_default.cpp  # 默认全局初始化
```

## 关键类与函数

### 1. SkTypeface 层次体系

`SkTypeface` 是 Skia 字体系统的核心抽象，代表一个字体面（font face）。各平台后端都提供了
对应的子类实现：

| 类名 | 文件 | 说明 |
|------|------|------|
| `SkTypeface_FreeType` | `SkTypeface_FreeType.h` | FreeType 后端基类，Linux/Android 平台使用 |
| `SkTypeface_Custom` | `SkFontMgr_custom.h` | 继承自 `SkTypeface_FreeType`，用于自定义字体管理器 |
| `SkTypeface_File` | `SkFontMgr_custom.h` | 从文件系统加载的字体 |
| `SkTypeface_Empty` | `SkFontMgr_custom.h` | 空字体（最后回退手段） |
| `SkTypeface_Fontations` | `SkTypeface_fontations_priv.h` | 基于 Fontations Rust 库的字体实现 |
| `SkTypeface_Mac` (别名) | `SkTypeface_mac_ct.h` | Core Text 后端 |
| `DWriteFontTypeface` | `SkTypeface_win_dw.h` | DirectWrite 后端 |
| `SkTypeface_proxy` | `SkTypeface_proxy.h` | 代理模式封装，代理到真实 Typeface |

**SkTypeface_Fontations** 是最新的字体后端，其关键成员变量：

```cpp
class SkTypeface_Fontations : public SkTypeface {
    sk_sp<const SkData> fFontData;              // 原始字体数据
    uint32_t fTtcIndex;                          // TTC 集合索引
    rust::Box<fontations_ffi::BridgeFontRef> fBridgeFontRef;           // Rust 字体引用
    rust::Box<fontations_ffi::BridgeMappingIndex> fMappingIndex;       // 字符映射索引
    rust::Box<fontations_ffi::BridgeNormalizedCoords> fBridgeNormalizedCoords;  // 归一化变量坐标
    rust::Box<fontations_ffi::BridgeOutlineCollection> fOutlines;      // 轮廓集合
    rust::Box<fontations_ffi::BridgeGlyphStyles> fGlyphStyles;        // 字形样式（自动微调用）
    rust::Vec<uint32_t> fPalette;               // 调色板颜色
};
```

### 2. SkScalerContext 实现

`SkScalerContext` 是字形栅格化的核心引擎，负责将字体轮廓转换为位图或路径：

| 类名 | 文件 | 说明 |
|------|------|------|
| `SkFontationsScalerContext` | `SkTypeface_fontations.cpp` | Fontations 栅格化上下文 |
| （FreeType ScalerContext） | `SkFontHost_FreeType.cpp` | FreeType 栅格化上下文 |
| `SkScalerContext_Mac` | `SkScalerContext_mac_ct.cpp` | Core Text 栅格化上下文 |
| `SkScalerContext_DW` | `SkScalerContext_win_dw.cpp` | DirectWrite 栅格化上下文 |
| `SkScalerContext_proxy` | `SkTypeface_proxy.h` | 代理栅格化上下文 |

`SkFontationsScalerContext` 的关键方法：

```cpp
// 生成字形度量信息（包括前进宽度、边界框等）
GlyphMetrics generateMetrics(const SkGlyph& glyph, SkArenaAlloc*) override;

// 生成字形路径（矢量轮廓）
std::optional<GeneratedPath> generatePath(const SkGlyph& glyph) override;

// 生成字形位图图像
void generateImage(const SkGlyph& glyph, void* imageBuffer) override;

// 生成字体全局度量信息
void generateFontMetrics(SkFontMetrics* out_metrics) override;

// 生成 COLRv0/v1 可绘制对象
sk_sp<SkDrawable> generateDrawable(const SkGlyph& glyph) override;
```

### 3. SkFontMgr 字体管理器

`SkFontMgr` 是字体发现和实例化的入口点：

| 类名 | 文件 | 说明 |
|------|------|------|
| `SkFontMgr_Custom` | `SkFontMgr_custom.h/.cpp` | FreeType 自定义字体管理器基类 |
| `SkFontMgr_Fontations_Empty` | `SkFontMgr_fontations_empty.cpp` | Fontations 空字体管理器 |
| （Core Text FontMgr） | `SkFontMgr_mac_ct.cpp` | macOS/iOS 字体管理器 |
| （DirectWrite FontMgr） | `SkFontMgr_win_dw.cpp` | Windows 字体管理器 |
| （Android FontMgr） | `SkFontMgr_android.cpp` | Android 系统字体管理器 |
| （Fontconfig FontMgr） | `SkFontMgr_fontconfig.cpp` | Linux fontconfig 管理器 |

### 4. ColorPainter 彩色字体绘制

Fontations 后端实现了完整的 COLR（彩色字体表）渲染支持：

```cpp
namespace sk_fontations {

// 实际绘制彩色字形到 SkCanvas
class ColorPainter : public fontations_ffi::ColorPainterWrapper {
    void push_transform(const fontations_ffi::Transform&);
    void fill_solid(uint16_t palette_index, float alpha);
    void fill_linear(...);        // 线性渐变填充
    void fill_radial(...);        // 径向渐变填充
    void fill_sweep(...);         // 扫描渐变填充
    void fill_glyph_solid(...);   // 优化的字形实色填充
    void push_layer(uint8_t compositeMode);  // 合成图层
};

// 仅计算边界框，不实际绘制
class BoundsPainter : public fontations_ffi::ColorPainterWrapper {
    SkRect getBoundingBox();
};

}  // namespace sk_fontations
```

### 5. 关键工厂与全局函数

```cpp
// Fontations 字体创建入口
sk_sp<SkTypeface> SkTypeface_Make_Fontations(std::unique_ptr<SkStreamAsset>, const SkFontArguments&);
sk_sp<SkTypeface> SkTypeface_Make_Fontations(sk_sp<const SkData>, const SkFontArguments&);

// 空 Fontations 字体管理器工厂
sk_sp<SkFontMgr> SkFontMgr_New_Fontations_Empty();

// FreeType SkTypeface 静态创建方法
static sk_sp<SkTypeface> SkTypeface_FreeType::MakeFromStream(
    std::unique_ptr<SkStreamAsset>, const SkFontArguments&);
```

## 依赖关系

### 外部依赖

| 依赖库 | 用途 | 使用平台 |
|--------|------|----------|
| **FreeType** (`@freetype`) | 字体解析与栅格化 | Linux, Android |
| **Fontations** (Rust crates) | 字体解析与栅格化 | 全平台 |
| - `read-fonts` 0.34 | 底层字体表读取 | |
| - `font-types` 0.9 | 字体类型定义 | |
| - `skrifa` 0.36 | 高层字体操作 API | |
| - `bytemuck` 1.16 | 安全类型转换 | |
| - `cxx` 1.0 | C++/Rust 互操作 | |
| **Core Text** | 字体管理与栅格化 | macOS, iOS |
| **DirectWrite** (dwrite.h) | 字体管理与栅格化 | Windows |
| **fontconfig** | 字体发现与匹配 | Linux |
| **expat** (`@expat`) | XML 解析（Android fonts.xml） | Android |

### Skia 内部依赖

```
src/ports 依赖:
  --> //:core                    (Skia 核心库)
  --> //:pathops                 (路径运算)
  --> //src/base                 (基础工具)
  --> //src/core:core_priv       (核心私有接口)
  --> //src/codec:any_decoder    (图像解码器，Fontations 后端)
  --> //src/utils:char_to_glyphcache  (字符到字形缓存)
  --> //src/sfnt                 (SFNT 字体表工具)
  --> //src/utils/mac            (macOS 工具)
```

### 构建定义宏

| 宏定义 | 含义 |
|--------|------|
| `SK_TYPEFACE_FACTORY_FREETYPE` | 启用 FreeType 字体工厂 |
| `SK_TYPEFACE_FACTORY_FONTATIONS` | 启用 Fontations 字体工厂 |
| `SK_TYPEFACE_FACTORY_CORETEXT` | 启用 Core Text 字体工厂 |
| `SK_FONTMGR_ANDROID_AVAILABLE` | 启用 Android 字体管理器 |
| `SK_FONTMGR_ANDROID_NDK_AVAILABLE` | 启用 Android NDK 字体管理器 |
| `SK_FONTMGR_CORETEXT_AVAILABLE` | 启用 Core Text 字体管理器 |
| `SK_FONTMGR_FONTCONFIG_AVAILABLE` | 启用 fontconfig 字体管理器 |
| `SK_FONTMGR_FONTATIONS_AVAILABLE` | 启用 Fontations 字体管理器 |
| `SK_FONTMGR_FREETYPE_DATA_AVAILABLE` | 启用 FreeType 嵌入数据管理器 |
| `SK_FONTMGR_FREETYPE_DIRECTORY_AVAILABLE` | 启用 FreeType 目录管理器 |
| `SK_FONTMGR_FREETYPE_EMPTY_AVAILABLE` | 启用 FreeType 空管理器 |

## 设计模式分析

### 1. 策略模式（Strategy Pattern）

字体系统的核心架构基于策略模式。`SkTypeface` 定义了字体操作的统一接口（`onCountGlyphs()`、
`onCharsToGlyphs()`、`onGetFamilyName()` 等），而各平台后端（FreeType、Core Text、
DirectWrite、Fontations）作为具体策略提供不同的实现。这使得上层渲染代码可以完全不关心底层
使用的字体引擎。

### 2. 工厂模式（Factory Pattern）

`SkFontMgr` 及其子类使用工厂模式来创建 `SkTypeface` 实例。每种字体管理器都知道如何从不同来源
（文件路径、内存数据、流）创建对应的 Typeface 对象。`FactoryId` 机制允许在序列化/反序列化时
正确重建 Typeface：

```cpp
// 各后端注册不同的 FactoryId
static constexpr SkTypeface::FactoryId FactoryId = SkSetFourByteTag('f','r','e','e');  // FreeType
static constexpr SkTypeface::FactoryId FactoryId = SkSetFourByteTag('d','w','r','t');  // DirectWrite
static constexpr SkTypeface::FactoryId FactoryId = SkTypefaces::Fontations::FactoryId; // Fontations
```

### 3. 代理模式（Proxy Pattern）

`SkTypeface_proxy` 和 `SkScalerContext_proxy` 实现了代理模式，它们包装一个真实的
Typeface/ScalerContext，将所有调用委托给被代理对象。这在 Android 字体管理中被使用，
允许在不暴露底层实现细节的情况下对字体行为进行拦截和修改：

```cpp
class SkTypeface_proxy : public SkTypeface {
    sk_sp<SkTypeface> fRealTypeface;  // 被代理的真实 Typeface
    // 所有虚方法委托到 fRealTypeface
};
```

### 4. 桥接模式（Bridge Pattern） - Fontations FFI

Fontations 后端使用了桥接模式，通过 CXX 框架在 C++ 和 Rust 之间建立桥梁。C++ 侧定义了
纯虚接口（`AxisWrapper`、`ColorPainterWrapper`），Rust 侧通过回调这些接口将解析结果
传回 C++：

```
C++ 侧:                          Rust 侧:
ColorPainter ----实现----> ColorPainterWrapper <---调用---- ColorPainterImpl
(具体绘制)        (纯虚接口)        (skpath_bridge.h)       (colr.rs)
```

### 5. 模板方法模式（Template Method Pattern）

`SkScalerContext` 基类定义了字形生成的算法骨架（`generateMetrics` -> `generatePath`/
`generateImage` -> `generateFontMetrics`），各平台子类覆盖这些虚方法以提供具体实现。
`SkFontationsScalerContext` 中的 `generateMetrics()` 方法根据字形类型（PATH、COLRv0、
COLRv1、BITMAP）分派到不同的处理逻辑。

## 数据流

### 字体加载数据流

```
1. 字体数据输入
   SkData / SkStreamAsset (原始字体二进制)
          |
          v
2. 字体管理器创建 Typeface
   SkFontMgr::makeFromStream/makeFromData
          |
          v
3. 字体解析（以 Fontations 为例）
   SkTypeface_Fontations::MakeFromData()
     |-- make_bridge_font_ref()        --> Rust: fontations_ffi::make_font_ref()
     |-- make_mapping_index()          --> Rust: fontations_ffi::make_mapping_index()
     |-- make_normalized_coords()      --> Rust: fontations_ffi::resolve_into_normalized_coords()
     |-- get_outline_collection()      --> Rust: fontations_ffi::get_outline_collection()
     |-- get_bridge_glyph_styles()     --> Rust: fontations_ffi::get_bridge_glyph_styles()
     |-- resolve_palette()             --> Rust: fontations_ffi::resolve_palette()
          |
          v
4. 返回 sk_sp<SkTypeface> 给调用方
```

### 字形渲染数据流

```
1. 文本布局请求某个字形
   SkFont::measureText() / SkTextBlob
          |
          v
2. ScalerContext 生成度量
   SkFontationsScalerContext::generateMetrics()
     |-- 检查字形类型: PATH / COLRv0 / COLRv1 / BITMAP
     |-- 获取前进宽度: fontations_ffi::unhinted_advance_width_or_zero()
     |-- 获取路径（含微调）: generatePathForGlyphId()
     |     |-- fontations_ffi::get_path_verbs_points() --> Rust 侧轮廓提取
     |     |-- 构建 SkPath
     |-- 获取 COLR 裁剪框: fontations_ffi::get_colrv1_clip_box()
     |-- 获取位图度量: fontations_ffi::bitmap_glyph()
          |
          v
3. ScalerContext 生成图像
   generateImage()
     |-- PATH: generateImageFromPath() --> 路径栅格化
     |-- COLRv0/v1: drawCOLRGlyph()
     |     |-- sk_fontations::ColorPainter --> SkCanvas 绘制
     |     |-- fontations_ffi::draw_colr_glyph() --> Rust COLR 遍历
     |-- BITMAP: generatePngImage()
     |     |-- fontations_ffi::png_data() --> 获取 PNG 数据
     |     |-- SkImages::DeferredFromEncodedData() --> 解码
          |
          v
4. 字形缓存 SkGlyphCache 存储结果
```

### Hinting（字体微调）数据流

```
ScalerContext 构造函数
  |
  |-- 检查 hinting_reliant (字体是否依赖微调指令)
  |-- 根据 SkFontHinting 级别创建 HintingInstance:
  |     |-- kNone:   no_hinting_instance()
  |     |-- kSlight: make_hinting_instance(do_light_hinting=true)
  |     |-- kNormal: make_hinting_instance(do_light_hinting=false)
  |     |-- kFull:   make_hinting_instance(do_lcd_antialiasing=...)
  |     |-- BW模式:  make_mono_hinting_instance()
  |
  v
get_path_verbs_points() 使用 HintingInstance 生成微调后的轮廓
```

## 平台特定说明

### macOS / iOS (Core Text)

- 使用 `CoreText.framework`、`CoreGraphics.framework`、`CoreFoundation.framework`
- macOS 还使用 `ApplicationServices.framework` 作为统一入口
- `SkTypeface_Mac::Make()` 是 Core Text 后端的入口点
- 通过 `CTFontCreateWithFontDescriptor` 创建字体引用
- 支持 Weight、Width、Slant 三维度的字体样式匹配
- `SkFontMgr_mac_ct.cpp` 中使用 `SkCTFontCTWeightForCSSWeight()` 进行 CSS
  权重到 Core Text 权重的精确映射
- iOS 使用 `MobileCoreServices` 框架进行图像类型识别

### Windows (DirectWrite)

- 使用 `dwrite.h` 到 `dwrite_3.h` 的 DirectWrite API
- `DWriteFontTypeface` 管理 `IDWriteFontFace` 系列接口
- 支持 `IDWriteFontFace4`、`IDWriteFontFace5`、`IDWriteFontFace7` 等较新接口
- 使用 COM 引用计数（`SkTScopedComPtr`）管理 DirectWrite 对象生命周期
- `Loaders` 内部类管理 `IDWriteFontFileLoader` 和 `IDWriteFontCollectionLoader`
- Windows 日志通过 `OutputDebugString` 输出

### Android

- `SkFontMgr_android.cpp` 解析系统 `fonts.xml` 配置文件
- 使用 `expat` XML 解析库处理 Android 字体配置
- `SkFontMgr_android_ndk.cpp` 使用 Android NDK 的 `AFont*` API
- 两种管理器都使用 `SkTypeface_proxy` 进行间接访问
- Android Framework 构建时会禁用自动微调（除非显式强制开启）：
  ```cpp
  #ifdef SK_BUILD_FOR_ANDROID_FRAMEWORK
      if (!forceAutoHinting)
          autoHintingControl = AutoHinting::ForceOff;
  #endif
  ```
- Android 日志通过 `__android_log_print` 输出到 logcat

### Linux (fontconfig)

- `SkFontMgr_fontconfig.cpp` 集成 `libfontconfig` 进行字体发现
- 仅在 `@platforms//os:linux` 上可用
- `SkFontConfigInterface_direct.cpp` 提供直接操作 fontconfig API 的实现
- 使用 `SkTypeface_proxy` 进行间接访问

### Fuchsia

- `SkFontMgr_fuchsia.cpp` 提供 Fuchsia OS 专用的字体管理实现
- 作为独立的 filegroup 构建

### 跨平台注意事项

- 文件 I/O 在 POSIX 系统（Linux、macOS、Android）使用 `SkOSFile_posix.cpp`
- Windows 使用 `SkOSFile_win.cpp`
- iOS 有特殊的 bundle 路径处理（`SkOSFile_ios.h`）
- 内存分配默认使用 `SkMemory_malloc.cpp`（标准 malloc/free/realloc）
- Mozilla Firefox 使用 `SkMemory_mozalloc.cpp`（与 Firefox 内存管理集成）

## 相关文档与参考

### Skia 内部相关目录

| 路径 | 说明 |
|------|------|
| `include/core/SkTypeface.h` | SkTypeface 公开接口定义 |
| `include/core/SkFontMgr.h` | SkFontMgr 公开接口定义 |
| `include/core/SkFontScanner.h` | SkFontScanner 公开接口定义 |
| `include/ports/` | 各平台特定的公开头文件 |
| `include/ports/SkTypeface_fontations.h` | Fontations 公开 API |
| `include/ports/SkFontMgr_Fontations.h` | Fontations FontMgr 公开 API |
| `include/ports/SkFontMgr_mac_ct.h` | Core Text FontMgr 公开 API |
| `include/ports/SkFontScanner_FreeType.h` | FreeType 字体扫描器公开 API |
| `src/core/SkScalerContext.h` | ScalerContext 基类定义 |
| `src/core/SkFontDescriptor.h` | 字体描述符（序列化用） |
| `src/core/SkAdvancedTypefaceMetrics.h` | 高级字体度量信息 |

### 外部参考

- [FreeType 官方文档](https://freetype.org/freetype2/docs/)
- [Apple Core Text 文档](https://developer.apple.com/documentation/coretext)
- [Microsoft DirectWrite 文档](https://learn.microsoft.com/en-us/windows/win32/directwrite/direct-write-portal)
- [OpenType COLR 表规范](https://learn.microsoft.com/en-us/typography/opentype/spec/colr)
- [Google Fontations 项目](https://github.com/googlefonts/fontations)
- [CXX - C++/Rust 互操作框架](https://cxx.rs/)
- [Skrifa 文档](https://docs.rs/skrifa/)
- [fontconfig 文档](https://www.freedesktop.org/wiki/Software/fontconfig/)
