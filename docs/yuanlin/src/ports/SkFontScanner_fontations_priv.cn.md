# SkFontScanner_fontations_priv

> 源文件: [src/ports/SkFontScanner_fontations_priv.h](../../../../src/ports/SkFontScanner_fontations_priv.h)

## 概述

本头文件声明了 `SkFontScanner_Fontations` 类，它是 `SkFontScanner` 接口的 Fontations (Rust) 后端实现。Fontations 是 Google 基于 Rust 语言开发的字体解析库，本类封装了通过 Fontations FFI 接口扫描字体文件、字体面（face）和字体实例（instance）的功能。

## 架构位置

在 Skia 字体架构中，`SkFontScanner_Fontations` 是两个字体扫描后端之一（另一个是基于 FreeType 的 `SkFontScanner_FreeType`）。它位于端口层，负责解析字体文件的元数据。

```
SkFontScanner (纯虚接口)
  ├── SkFontScanner_FreeType  (FreeType 后端)
  └── SkFontScanner_Fontations (Fontations/Rust 后端, 本文件)
```

## 主要类与结构体

### SkFontScanner_Fontations

继承自 `SkFontScanner`，实现了所有纯虚方法。

| 成员 | 类型 | 说明 |
|------|------|------|
| 构造函数 | `SkFontScanner_Fontations()` | 默认构造 |
| 析构函数 | `~SkFontScanner_Fontations()` | 虚析构，允许多态删除 |

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `bool scanFile(SkStreamAsset* stream, int* numFaces) const` | 扫描字体文件，获取包含的字体面数量 |
| `bool scanFace(SkStreamAsset* stream, int faceIndex, int* numInstances) const` | 扫描指定字体面，获取命名实例数量 |
| `bool scanInstance(SkStreamAsset* stream, int faceIndex, int instanceIndex, SkString* name, SkFontStyle* style, bool* isFixedPitch, AxisDefinitions* axes, VariationPosition* position) const` | 扫描指定字体实例，获取名称、样式、可变轴等完整元数据 |
| `sk_sp<SkTypeface> MakeFromStream(std::unique_ptr<SkStreamAsset>, const SkFontArguments&) const` | 从流数据创建 `SkTypeface` 对象 |
| `SkFourByteTag getFactoryId() const` | 返回此扫描器对应的工厂标识 |

## 内部实现细节

- 类体中 `private:` 部分为空，表明当前实现无需私有成员变量
- 所有具体实现位于对应的 `.cpp` 文件中，通过 Fontations FFI (Rust-C++ 互操作) 调用 Rust 代码
- `scanInstance()` 方法参数丰富，可一次性获取字体的名称、样式、等宽属性、可变轴定义和变体位置

## 依赖关系

- **`include/core/SkFontScanner.h`** — 基类 `SkFontScanner` 定义
- **`include/core/SkSpan.h`** — 用于安全的数组切片
- **`include/core/SkTypeface.h`** — 字体面抽象
- **`include/core/SkTypes.h`** — 基础类型定义
- **前向声明**: `SkAdvancedTypefaceMetrics`, `SkFontDescriptor`, `SkFontData`

## 设计模式与设计决策

1. **策略模式**: `SkFontScanner` 接口允许在运行时选择 Fontations 或 FreeType 作为字体扫描后端。
2. **Rust-C++ FFI**: 利用 CXX 桥接机制，将 Rust 的 Fontations 库暴露给 C++ 代码使用。
3. **接口隔离**: 通过 `_priv.h` 后缀命名表明这是内部头文件，不属于公共 API。

## 性能考量

- Fontations 作为 Rust 实现，提供内存安全保证，减少了因字体解析导致的安全漏洞风险
- 每次扫描操作都需要通过 FFI 边界，可能带来少量开销
- 类不持有可变状态（私有部分为空），因此 `const` 方法可以安全地在多线程中调用
- `scanInstance` 是最重的操作，涉及多次 FFI 调用来获取名称、样式、轴和位置信息
- Rust 端的字体解析通常在内存中完成，无需额外的文件 I/O

## 使用场景

该扫描器在以下场景中使用:
- 字体管理器枚举系统字体时，通过扫描器获取每个字体的元数据
- 从字体文件创建 `SkTypeface` 时，先扫描确定字体属性
- 处理可变字体 (Variable Fonts) 时获取轴定义和命名实例

## 相关文件

- `src/ports/SkFontScanner_fontations.cpp` — 本类的实现文件
- `src/ports/SkTypeface_fontations_priv.h` — Fontations 字体面实现
- `src/ports/SkFontScanner_FreeType_priv.h` — FreeType 对应的扫描器声明
- `include/core/SkFontScanner.h` — 基类接口
