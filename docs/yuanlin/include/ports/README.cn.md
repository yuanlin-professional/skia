# ports - 平台移植 API

## 概述

`include/ports` 目录定义了 Skia 平台移植层（porting layer）的公共 API。该层提供了
Skia 核心功能在不同操作系统和平台上的适配接口，主要涵盖字体管理器（FontMgr）、
字体扫描器（FontScanner）、字体类型（Typeface）和图像生成器（ImageGenerator）
等与平台紧密相关的功能。

字体管理器是移植层中最重要的组件。Skia 提供了针对不同平台的字体管理器实现：
macOS/iOS 使用 Core Text 框架（`SkFontMgr_mac_ct.h`），Linux 使用 fontconfig
库（`SkFontMgr_fontconfig.h`），Android 提供了基于 NDK 的字体管理器
（`SkFontMgr_android_ndk.h`）和旧版管理器（`SkFontMgr_android.h`），Windows
通过 `SkTypeface_win.h` 提供系统字体支持。此外还有跨平台的字体管理器：
`SkFontMgr_data` 基于内存中的字体数据，`SkFontMgr_directory` 基于文件系统目录，
`SkFontMgr_empty` 提供空实现。

Fontations 是 Skia 正在推进的基于 Rust 的字体后端，通过 `SkFontMgr_Fontations`
和 `SkTypeface_fontations` 提供支持。这是一个重要的现代化方向，用 Rust 实现的字体
解析和渲染代替传统的 FreeType，以获得更好的内存安全性。

图像生成器部分提供了不同平台的原生图像解码能力：macOS/iOS 使用 Core Graphics
（`SkImageGeneratorCG`）、Android 使用 NDK（`SkImageGeneratorNDK`）、Windows
使用 WIC（`SkImageGeneratorWIC`）。

`SkCFObject.h` 提供了 Apple Core Foundation 对象的 RAII 包装，而
`SkFontConfigInterface` 定义了与 fontconfig 交互的抽象接口。

## 架构图

```
+------------------------------------------------------------------+
|                      Skia 核心 API                                 |
|  SkFontMgr / SkTypeface / SkImageGenerator                       |
+------------------------------------------------------------------+
         |
         v (平台适配层)
+-----------------------------------------------------------+
|              字体管理器 (SkFontMgr)                          |
+-----------------------------------------------------------+
|                    |                    |                   |
v                    v                    v                   v
+-----------+  +-------------+  +--------------+  +---------+
| Apple     |  | Linux       |  | Android      |  | 通用     |
| CoreText  |  | fontconfig  |  | NDK / Legacy |  |          |
+-----------+  +-------------+  +--------------+  +---------+
| mac_ct    |  | fontconfig  |  | android_ndk  |  | data    |
|           |  | FontConfig  |  | android      |  | directory|
|           |  |  Interface  |  |              |  | empty   |
+-----------+  +-------------+  +--------------+  +---------+
                                                       |
+-----------------------------------------------------------+
|              字体后端                                        |
+-----------------------------------------------------------+
|           |              |              |                   |
v           v              v              v                   |
+--------+ +-----------+  +----------+  +-----------+        |
| Free   | | Fontations|  | CoreText |  | DirectWrite|       |
| Type   | | (Rust)    |  | (Apple)  |  | (Windows) |        |
+--------+ +-----------+  +----------+  +-----------+        |
           | SkFontScanner_Fontations                        |
           | SkFontScanner_FreeType                          |
           | SkTypeface_fontations                           |
           | SkTypeface_mac                                  |
           | SkTypeface_win                                  |
+-----------------------------------------------------------+
|              图像生成器 (SkImageGenerator)                    |
+-----------------------------------------------------------+
|           |              |                                  |
v           v              v                                  |
+--------+ +-----------+  +-----------+                      |
| CG     | | NDK       |  | WIC       |                     |
| Apple  | | Android   |  | Windows   |                     |
+--------+ +-----------+  +-----------+                      |
```

## 目录结构

```
include/ports/
  BUILD.bazel                    # Bazel 构建配置
  SkCFObject.h                   # Apple Core Foundation 对象 RAII 包装
  SkFontConfigInterface.h        # fontconfig 抽象接口
  SkFontMgr_android.h            # Android 字体管理器（旧版）
  SkFontMgr_android_ndk.h        # Android NDK 字体管理器
  SkFontMgr_data.h               # 基于内存数据的字体管理器
  SkFontMgr_directory.h          # 基于目录的字体管理器
  SkFontMgr_empty.h              # 空字体管理器
  SkFontMgr_Fontations.h         # Fontations (Rust) 字体管理器
  SkFontMgr_fontconfig.h         # fontconfig 字体管理器 (Linux)
  SkFontMgr_FontConfigInterface.h# fontconfig 接口字体管理器
  SkFontMgr_fuchsia.h            # Fuchsia OS 字体管理器
  SkFontMgr_mac_ct.h             # Core Text 字体管理器 (macOS/iOS)
  SkFontScanner_Fontations.h     # Fontations 字体扫描器
  SkFontScanner_FreeType.h       # FreeType 字体扫描器
  SkImageGeneratorCG.h           # Core Graphics 图像生成器 (Apple)
  SkImageGeneratorNDK.h          # NDK 图像生成器 (Android)
  SkImageGeneratorWIC.h          # WIC 图像生成器 (Windows)
  SkTypeface_fontations.h        # Fontations 字体类型
  SkTypeface_mac.h               # macOS 字体类型
  SkTypeface_win.h               # Windows 字体类型
```

## 关键类与函数

### 字体管理器工厂函数

每个平台都有对应的工厂函数创建字体管理器：

- `SkFontMgr_New_CoreText(CTFontCollectionRef)` - macOS/iOS Core Text
- `SkFontMgr_New_FontConfig(FcConfig*, std::unique_ptr<SkFontScanner>)` - Linux fontconfig
- `SkFontMgr_New_Custom_Data(SkSpan<sk_sp<SkData>>)` - 从内存数据创建
- `SkFontMgr_New_Fontations_Empty()` - Fontations Rust 后端（仅实例化，不匹配）
- 以及 Android、Fuchsia、Directory、Empty 等平台的工厂函数

### SkTypeface_Make_Fontations - Fontations 字体创建

```cpp
sk_sp<SkTypeface> SkTypeface_Make_Fontations(
    std::unique_ptr<SkStreamAsset> fontData,
    const SkFontArguments& args);

sk_sp<SkTypeface> SkTypeface_Make_Fontations(
    sk_sp<const SkData> fontData,
    const SkFontArguments& args);
```

使用 Rust Fontations 后端从字体数据创建 SkTypeface。支持可变字体参数设置。

### SkFontConfigInterface - fontconfig 接口

为基于 fontconfig 的字体匹配提供抽象层：
- 分离了字体扫描器与字体管理器，允许灵活组合

### 图像生成器

- `SkImageGeneratorCG` - 使用 Apple Core Graphics 解码图像
- `SkImageGeneratorNDK` - 使用 Android NDK 解码图像
- `SkImageGeneratorWIC` - 使用 Windows Imaging Component 解码图像

### SkCFObject - Core Foundation 包装

为 Apple Core Foundation 引用计数对象提供 C++ RAII 模式的生命周期管理。

## 依赖关系

- **内部依赖**：`include/core`（SkFontMgr、SkTypeface、SkImageGenerator 等基类）
- **平台依赖**：
  - Apple：CoreText、CoreGraphics
  - Linux：fontconfig、FreeType
  - Android：NDK
  - Windows：DirectWrite、WIC
  - Rust：Fontations crate

## 相关文档与参考

- Apple Core Text 文档
- fontconfig 文档：https://www.freedesktop.org/wiki/Software/fontconfig/
- FreeType 文档：https://freetype.org/
- Fontations (Rust)：https://github.com/googlefonts/fontations
- 源码实现位于 `src/ports/` 目录
