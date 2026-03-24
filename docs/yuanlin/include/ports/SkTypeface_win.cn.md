# SkTypeface_win

> 源文件: `include/ports/SkTypeface_win.h`

## 概述

`SkTypeface_win` 是 Skia 在 Windows 平台上的字体管理接口，提供与 Windows 原生字体系统(GDI 和 DirectWrite)的互操作能力。它允许从 Windows `LOGFONT` 结构创建 Skia 字体面对象，反向提取 `LOGFONT` 信息，以及创建基于 GDI 或 DirectWrite 的字体管理器。该接口是 Skia 跨平台字体抽象在 Windows 平台的具体实现。

## 架构位置

该头文件位于 `include/ports/` 目录，属于 Skia 的平台移植层(Ports Layer)。它是 Windows 平台字体子系统的公开接口，与 macOS 的 `SkTypeface_mac.h` 对应，提供平台特定的字体创建和查询功能。

## 条件编译

整个接口仅在 Windows 平台可用：
```cpp
#ifdef SK_BUILD_FOR_WIN
// 所有 API 定义
#endif
```

## Windows 字体系统互操作

### LOGFONT 类型定义

根据项目的 Unicode 配置，自动选择正确的 `LOGFONT` 类型：
```cpp
#ifdef UNICODE
typedef struct tagLOGFONTW LOGFONTW;
typedef LOGFONTW LOGFONT;
#else
typedef struct tagLOGFONTA LOGFONTA;
typedef LOGFONTA LOGFONT;
#endif
```

这确保与项目的字符集配置保持一致(ANSI 或 Unicode)。

## 公共 API 函数

### `SkCreateTypefaceFromLOGFONT`

```cpp
SK_API sk_sp<SkTypeface> SkCreateTypefaceFromLOGFONT(const LOGFONT&);
```

- **功能**: 从 Windows `LOGFONT` 结构创建 Skia 字体面对象
- **参数**: `LOGFONT` 结构的常量引用，包含字体族名、样式、权重等信息
- **返回值**: `sk_sp<SkTypeface>` 智能指针，调用者负责管理生命周期(通过引用计数)
- **行为特征**:
  - 查找系统中匹配 `LOGFONT` 的字体
  - 如果找不到精确匹配，可能返回最接近的字体
  - 使用 `LOGFONT` 的所有样式信息(粗体、斜体、删除线、下划线等)
- **注意事项**: `LOGFONT.lfHeight` 字段(字体大小)通常被忽略，因为 `SkTypeface` 不包含尺寸信息(尺寸由 `SkFont` 管理)

### `SkLOGFONTFromTypeface`

```cpp
SK_API void SkLOGFONTFromTypeface(const SkTypeface* typeface, LOGFONT* lf);
```

- **功能**: 从 Skia 字体面对象提取对应的 Windows `LOGFONT` 结构
- **参数**:
  - `typeface`: Skia 字体面对象指针(可以为 `nullptr`，此时返回默认字体的 `LOGFONT`)
  - `lf`: 输出参数，用于接收 `LOGFONT` 结构
- **行为特征**:
  - 填充 `LOGFONT` 的所有字段(除了 `lfHeight`)
  - `lfHeight` 字段需要调用者根据需要的字体大小手动设置
  - 如果 `typeface` 为 `nullptr`，返回系统默认字体的 `LOGFONT`
- **使用场景**: 与 Windows API 交互(如创建 HFONT 句柄、调用 GDI 文本函数)

### `SkTypeface_SetEnsureLOGFONTAccessibleProc`

```cpp
SK_API void SkTypeface_SetEnsureLOGFONTAccessibleProc(void (*)(const LOGFONT&));
```

- **功能**: 设置可选的回调函数，用于确保 `LOGFONT` 对应的字体数据可访问
- **参数**: 函数指针，接受 `LOGFONT` 引用，无返回值
- **使用场景**:
  - **远程字体**: 字体数据存储在远程服务器，需要按需下载
  - **延迟加载**: 字体数据未立即可用，需要触发加载逻辑
  - **错误恢复**: Skia 访问字体失败时，调用此回调重试加载
- **默认行为**: 默认为 `nullptr`，即不执行任何回调
- **线程安全**: 回调可能在任意线程中调用，需要保证线程安全

## 字体管理器工厂函数

### `SkFontMgr_New_GDI`

```cpp
SK_API sk_sp<SkFontMgr> SkFontMgr_New_GDI();
```

- **功能**: 创建基于 Windows GDI(Graphics Device Interface)的字体管理器
- **返回值**: `sk_sp<SkFontMgr>` 智能指针
- **特点**:
  - 使用 GDI 枚举和匹配系统字体
  - 字体渲染通过 GDI(较旧的 API)
  - 兼容性好，支持所有 Windows 版本
  - 性能较 DirectWrite 低，字形质量一般

### `SkFontMgr_New_DirectWrite` (基础版本)

```cpp
SK_API sk_sp<SkFontMgr> SkFontMgr_New_DirectWrite(
    IDWriteFactory* factory = nullptr,
    IDWriteFontCollection* collection = nullptr
);
```

- **功能**: 创建基于 DirectWrite 的现代字体管理器
- **参数**:
  - `factory`: DirectWrite 工厂对象(可选，传 `nullptr` 时自动创建)
  - `collection`: 字体集合(可选，传 `nullptr` 时使用系统字体集合)
- **返回值**: `sk_sp<SkFontMgr>` 智能指针
- **特点**:
  - 现代 Windows 字体 API(Vista 及以上)
  - 高质量字形渲染(ClearType 子像素抗锯齿)
  - 支持 OpenType 高级特性
  - 性能优于 GDI

### `SkFontMgr_New_DirectWrite` (高级版本)

```cpp
SK_API sk_sp<SkFontMgr> SkFontMgr_New_DirectWrite(
    IDWriteFactory* factory,
    IDWriteFontCollection* collection,
    IDWriteFontFallback* fallback
);
```

- **功能**: 创建支持字体回退的 DirectWrite 字体管理器
- **参数**:
  - `fallback`: 字体回退对象，用于处理字符不存在于当前字体时的回退逻辑
- **特点**:
  - 支持复杂文本渲染(如 CJK、阿拉伯文、emoji)
  - 自动字体回退，确保所有字符都能渲染
  - 适用于国际化应用

## 内部实现细节

### GDI 字体枚举

`SkFontMgr_New_GDI()` 内部调用 Windows API:
- `EnumFontFamiliesEx()`: 枚举系统安装的字体
- `GetOutlineTextMetrics()`: 获取字体度量信息
- `GetGlyphOutline()`: 提取字形轮廓数据

### DirectWrite 集成

DirectWrite 管理器使用 COM 接口：
- **工厂对象**: `IDWriteFactory` 是 DirectWrite 的入口点
- **字体集合**: `IDWriteFontCollection` 管理字体族和字体文件
- **字体回退**: `IDWriteFontFallback` 处理多语言字符的回退

### LOGFONT 映射

`LOGFONT` 到 `SkFontStyle` 的转换：
- **权重**: `lfWeight` (100-900) → `SkFontStyle::Weight`
- **斜体**: `lfItalic` → `SkFontStyle::Slant::kItalic_Slant`
- **字符集**: `lfCharSet` → 用于字体匹配
- **修饰**: `lfUnderline`, `lfStrikeOut` → Skia 不在 `SkTypeface` 中存储，需通过 `SkPaint` 设置

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `SkTypeface` | 字体面基类 |
| `SkRefCnt` | 引用计数管理 |
| Windows GDI | 传统字体 API |
| DirectWrite | 现代字体 API |
| COM 库 | DirectWrite 接口交互 |

### 被依赖的模块

- **Windows 应用**: 所有在 Windows 上使用 Skia 的应用
- **跨平台应用**: 需要访问系统字体的应用
- **文本编辑器**: 需要匹配用户指定的字体
- **浏览器引擎**: Chrome/Edge 的字体渲染

## 设计模式与设计决策

### 平台抽象

通过工厂函数返回统一的 `SkFontMgr` 接口：
- **跨平台代码**: 应用层代码不需要知道底层是 GDI 还是 DirectWrite
- **灵活切换**: 可以在运行时选择不同的字体后端

### LOGFONT 兼容性

保留 `LOGFONT` 互操作性：
- **历史原因**: 许多 Windows 应用使用 `LOGFONT` 配置字体
- **互操作性**: 与 MFC、Win32 GUI 框架集成
- **弃用路径**: 新代码推荐使用 DirectWrite API

### 可选回调

`SkTypeface_SetEnsureLOGFONTAccessibleProc` 设计：
- **解耦**: 核心字体逻辑不依赖远程加载机制
- **灵活性**: 应用可选择性启用字体按需加载
- **单例行为**: 全局回调，所有字体共享

## 性能考量

### GDI vs DirectWrite

| 方面 | GDI | DirectWrite |
|------|-----|-------------|
| 渲染质量 | 一般 | 高(ClearType) |
| 性能 | 较慢 | 较快 |
| 内存占用 | 低 | 中 |
| 兼容性 | 所有 Windows | Vista 及以上 |
| OpenType 支持 | 有限 | 完整 |

### 字体缓存

- **Typeface 缓存**: 应用应缓存 `SkTypeface` 对象，避免重复创建
- **LOGFONT 查找**: 从 `LOGFONT` 创建字体涉及系统查询，有明显开销
- **DirectWrite 优化**: DirectWrite 内部有字体缓存，性能优于 GDI

### 推荐实践

现代 Windows 应用应优先使用 DirectWrite：
```cpp
// 推荐
sk_sp<SkFontMgr> fontMgr = SkFontMgr_New_DirectWrite();

// 不推荐(除非需要兼容老系统)
sk_sp<SkFontMgr> fontMgr = SkFontMgr_New_GDI();
```

## 平台相关说明

### Windows 版本支持

- **GDI**: Windows 95 及所有后续版本
- **DirectWrite**: Windows Vista / Windows Server 2008 及以上
- **DirectWrite 回退**: Windows 8.1 及以上(更完善的 API)

### 字符集处理

- **Unicode 构建**: 推荐使用 `LOGFONTW`(UTF-16)
- **ANSI 构建**: 使用 `LOGFONTA`，受当前代码页限制
- **现代应用**: 应使用 Unicode 构建以支持国际化

## 使用示例

### 从 LOGFONT 创建字体

```cpp
LOGFONT lf = {};
lf.lfHeight = -16;  // 16 像素(负值表示像素高度)
wcscpy_s(lf.lfFaceName, L"Arial");
lf.lfWeight = FW_BOLD;
lf.lfItalic = TRUE;

sk_sp<SkTypeface> typeface = SkCreateTypefaceFromLOGFONT(lf);
SkFont font(typeface, 16.0f);
```

### 导出 LOGFONT

```cpp
sk_sp<SkTypeface> typeface = /* ... */;
LOGFONT lf;
SkLOGFONTFromTypeface(typeface.get(), &lf);

// 现在可以使用 lf 创建 Windows HFONT
lf.lfHeight = -MulDiv(pointSize, GetDeviceCaps(hdc, LOGPIXELSY), 72);
HFONT hfont = CreateFontIndirect(&lf);
```

### 创建 DirectWrite 管理器

```cpp
sk_sp<SkFontMgr> fontMgr = SkFontMgr_New_DirectWrite();
sk_sp<SkTypeface> typeface = fontMgr->matchFamilyStyle("Segoe UI", SkFontStyle::Normal());
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkTypeface.h` | 字体面基类定义 |
| `include/core/SkFontMgr.h` | 字体管理器基类 |
| `include/ports/SkTypeface_mac.h` | macOS 平台对应接口 |
| `src/ports/SkFontHost_win.cpp` | Windows 字体实现(GDI) |
| `src/ports/SkFontMgr_win_dw.cpp` | DirectWrite 实现 |
| `include/core/SkFont.h` | 高层字体 API |
