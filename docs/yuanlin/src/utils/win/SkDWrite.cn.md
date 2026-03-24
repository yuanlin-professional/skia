# SkDWrite - DirectWrite 集成工具

> 源文件:
> - `src/utils/win/SkDWrite.h`
> - `src/utils/win/SkDWrite.cpp`

## 概述

SkDWrite 是 Skia 在 Windows 平台上与 Microsoft DirectWrite 文本渲染系统交互的桥接模块。它提供了 DirectWrite 工厂的单例获取、UTF-8 与 WCHAR 之间的字符串转换、区域设置字符串获取以及字体表数据访问等功能。该模块是 Skia Windows 字体后端的基础设施。

## 架构位置

```
Skia Windows 字体后端
├── SkTypeface_win_dw (Windows 字体接口)
│   └── SkDWrite (本模块 - DirectWrite 工具层)
│       ├── IDWriteFactory 单例管理
│       ├── 字符串编码转换
│       ├── 区域设置处理
│       └── 字体表数据访问
├── SkDWriteGeometrySink (路径转换)
├── SkDWriteFontFileStream (字体流适配)
└── DirectWrite API (系统层)
```

## 主要类与结构体

### `AutoDWriteTable`
- 封装 DirectWrite 字体表数据的 RAII 类。
- 通过 `TryGetFontTable()` 获取表数据，析构时调用 `ReleaseFontTable()` 释放。
- **成员**: `fData` (数据指针)、`fSize` (数据大小)、`fExists` (表是否存在)。

### `AutoTDWriteTable<T>`
- 模板化的类型安全字体表访问类，继承自 `AutoDWriteTable`。
- 使用 `DWRITE_MAKE_OPENTYPE_TAG` 从类型参数 `T` 的 TAG 常量构造标签。
- 提供 `get()` 和 `operator->()` 方法，返回强类型指针。

### `DWriteStyle`
- 将 Skia 的 `SkFontStyle` 转换为 DirectWrite 的字体样式参数。
- 映射关系：
  - `SkFontStyle::weight()` -> `DWRITE_FONT_WEIGHT`
  - `SkFontStyle::width()` -> `DWRITE_FONT_STRETCH`
  - `SkFontStyle::slant()` -> `DWRITE_FONT_STYLE` (Upright/Italic/Oblique)

### `SkSMallocWCHAR`
- 类型别名: `skia_private::AutoSTMalloc<16, WCHAR>`。
- 短字符串优化的 WCHAR 分配器，栈上预分配 16 个 WCHAR。

## 公共 API 函数

### `sk_get_dwrite_factory`
```cpp
IDWriteFactory* sk_get_dwrite_factory();
```
- **功能**: 获取全局共享的 IDWriteFactory 单例。
- **线程安全**: 使用 `SkOnce` 确保只初始化一次。
- **DLL 加载策略**: 优先尝试加载 `DWriteCore.dll`（项目 Reunion），失败后回退到 `dwrite.dll`。
- **生命周期**: 通过 `atexit()` 注册释放函数，在进程退出时释放。

### `sk_cstring_to_wchar`
```cpp
HRESULT sk_cstring_to_wchar(const char* skname, SkSMallocWCHAR* name);
```
- **功能**: 将 UTF-8 C 字符串转换为 WCHAR (UTF-16) 字符串。
- **实现**: 两次调用 `MultiByteToWideChar`：第一次获取所需长度，第二次执行转换。

### `sk_wchar_to_skstring`
```cpp
HRESULT sk_wchar_to_skstring(WCHAR* name, int nameLen, SkString* skname);
```
- **功能**: 将 WCHAR 字符串转换为 UTF-8 SkString。
- **实现**: 两次调用 `WideCharToMultiByte`。

### `sk_get_locale_string`
```cpp
HRESULT sk_get_locale_string(IDWriteLocalizedStrings* names,
                             const WCHAR* preferedLocale, SkString* skname);
```
- **功能**: 从 DirectWrite 的本地化字符串集合中获取指定区域设置的字符串。如果首选区域不存在，回退到索引 0。

### `SkGetGetUserDefaultLocaleNameProc`
```cpp
HRESULT SkGetGetUserDefaultLocaleNameProc(SkGetUserDefaultLocaleNameProc* proc);
```
- **功能**: 动态加载 `GetUserDefaultLocaleName` 函数指针。
- **实现**: 从 `Kernel32.dll` 中查找该函数。

## 内部实现细节

### 工厂创建策略
`create_dwrite_factory` 函数实现了一个降级加载策略：
1. 尝试加载 `DWriteCore.dll` 并获取 `DWriteCoreCreateFactory` 函数。
2. 如果失败，尝试加载 `dwrite.dll` 并获取 `DWriteCreateFactory` 函数。
3. 使用 `DWRITE_FACTORY_TYPE_SHARED` 创建共享工厂实例。
4. 注册 `atexit` 回调释放全局工厂指针。

### Clang 编译器兼容性
使用 `#pragma clang diagnostic` 抑制 `-Wcast-function-type` 警告，因为 `GetProcAddress` 返回的 `FARPROC` 需要强制转换为具体函数指针类型。

## 依赖关系

- `<dwrite.h>`: DirectWrite API。
- `<winsdkver.h>`: Windows SDK 版本。
- `include/core/SkFontStyle.h`: Skia 字体样式。
- `include/core/SkString.h`: Skia 字符串。
- `include/private/base/SkOnce.h`: 线程安全的一次性初始化。
- `include/private/base/SkTemplates.h`: `AutoSTMalloc` 模板。
- `src/utils/win/SkHRESULT.h`: HRESULT 错误处理宏。

## 设计模式与设计决策

1. **单例模式**: DirectWrite 工厂使用全局单例，通过 `SkOnce` 保证线程安全的延迟初始化。
2. **RAII 模式**: `AutoDWriteTable` 使用 RAII 管理字体表数据的锁定和释放。
3. **优雅降级**: DLL 加载策略先尝试较新的 DWriteCore，再回退到经典 dwrite。
4. **类型安全**: `AutoTDWriteTable<T>` 通过模板参数实现编译时类型安全的字体表访问。

## 性能考量

1. **字符串转换的两次调用**: UTF-8/WCHAR 转换需要两次系统调用（先查长度再转换），这是 Windows API 的标准使用模式。
2. **工厂单例**: 避免重复创建 DirectWrite 工厂的高开销。
3. **短字符串优化**: `SkSMallocWCHAR` 在栈上预分配 16 个 WCHAR，避免大多数短名称的堆分配。

## 相关文件

- `src/utils/win/SkDWriteGeometrySink.h/.cpp`: DirectWrite 几何体到 SkPath 的转换。
- `src/utils/win/SkDWriteFontFileStream.h/.cpp`: 字体文件流适配。
- `src/utils/win/SkHRESULT.h/.cpp`: HRESULT 错误处理。
- `src/ports/SkTypeface_win_dw.h/.cpp`: Windows DirectWrite 字体接口实现。
