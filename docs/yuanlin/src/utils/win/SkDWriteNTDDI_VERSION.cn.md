# SkDWriteNTDDI_VERSION

> 源文件: src/utils/win/SkDWriteNTDDI_VERSION.h

## 概述

`SkDWriteNTDDI_VERSION.h` 是 Skia 图形库中用于控制 DirectWrite API 版本可见性的头文件。该文件通过重置 Windows SDK 的版本宏(`NTDDI_VERSION`)来确保 Skia 可以访问所有 DirectWrite API,而不受构建系统预定义版本号的限制。

这是一个特殊的头文件,必须在任何 Windows 或 DirectWrite 头文件之前包含,以确保版本控制生效。

## 架构位置

```
src/utils/win/
  ├── SkDWriteNTDDI_VERSION.h  # 版本控制(本文件)
  ├── SkObjBase.h
  └── SkTScopedComPtr.h
```

该文件被 Skia 的 DirectWrite 字体渲染模块使用。

## 主要类与结构体

该文件不包含类、结构体或函数,仅包含预处理器指令。

## 公共 API 函数

无,该文件纯粹是预处理器级别的配置。

## 内部实现细节

### 问题背景

DirectWrite 3.0 的头文件 `dwrite_3.h` 使用 `NTDDI_VERSION` 宏来保护某些 API:

```cpp
// dwrite_3.h 示例
#if NTDDI_VERSION >= NTDDI_WIN10_RS1
    // Windows 10 RS1+ 的API
    interface IDWriteFontFaceReference;
#endif
```

**问题**:
- 如果构建系统设置了较低的 `NTDDI_VERSION`,新 API 会被隐藏
- Skia 需要访问所有 DirectWrite API(运行时检测可用性)
- 但又不想影响其他代码的版本控制

### 解决方案

该文件重置版本宏:

```cpp
#if defined(NTDDI_VERSION)
#  undef NTDDI_VERSION
#  if defined(_WIN32_WINNT)
#    undef _WIN32_WINNT
#  endif
#  if defined(WINVER)
#    undef WINVER
#  endif
#endif
```

**效果**:
- 取消构建系统定义的版本号
- DirectWrite 头文件将使用默认值(最新版本)
- Skia 代码可以访问所有 DirectWrite API

### 为何需要重置三个宏

Windows 版本控制涉及多个相关宏:

1. **NTDDI_VERSION**: 最详细的版本号(包括 Service Pack)
2. **_WIN32_WINNT**: Windows 主版本号
3. **WINVER**: 旧版 Windows 版本号

这些宏相互关联,必须保持一致性,因此全部重置。

### 包含顺序要求

```cpp
#if defined(_WINDOWS_) || defined(DWRITE_3_H_INCLUDED)
#error Must include SkDWriteNTDDI_VERSION.h before any Windows or DWrite headers.
#endif
```

**检查机制**:
- `_WINDOWS_`: 由 `<windows.h>` 定义
- `DWRITE_3_H_INCLUDED`: 由 `<dwrite_3.h>` 定义

如果这些宏已定义,说明 Windows 头文件已被包含,版本重置无效。

### DirectWrite API 的不变性

注释中提到:
> "it is not clear this is correct since these are all immutable"

**关键观点**:
- DirectWrite API 一旦发布就是不可变的(COM 接口契约)
- 使用 `NTDDI_VERSION` 保护可能不正确
- API 应该在运行时检测,而不是编译时隐藏

## 依赖关系

### 无依赖

该文件不包含任何头文件,只使用预处理器指令。

### 被依赖

所有使用 DirectWrite 的 Skia 源文件都应包含此头文件:

```cpp
// 正确的包含顺序
#include "src/utils/win/SkDWriteNTDDI_VERSION.h"  // 第一个
#include <dwrite.h>
#include <dwrite_3.h>
// ...其他Windows头文件
```

## 设计模式与设计决策

### 1. 头文件保护哨兵

使用 `#error` 指令强制执行包含顺序:

```cpp
#if defined(_WINDOWS_) || defined(DWRITE_3_H_INCLUDED)
#error Must include SkDWriteNTDDI_VERSION.h before any Windows or DWrite headers.
#endif
```

**优点**:
- 编译时错误检测
- 清晰的错误消息
- 防止隐式错误

### 2. 条件重置策略

只有在宏已定义时才重置:

```cpp
#if defined(NTDDI_VERSION)
#  undef NTDDI_VERSION
#endif
```

**理由**:
- 避免在未定义时取消定义(某些编译器会警告)
- 允许构建系统不设置版本号
- 更好的构建系统兼容性

### 3. 宽容策略(Permissive Strategy)

通过移除版本限制,允许代码**看到所有API**:
- 编译时:访问所有DirectWrite API声明
- 运行时:通过 `QueryInterface` 检测实际可用性

```cpp
// 编译时可见
IDWriteFontFaceReference* ref;

// 运行时检测
if (SUCCEEDED(fontFace->QueryInterface(&ref))) {
    // Windows 10 RS1+,API可用
} else {
    // 旧系统,降级处理
}
```

## 性能考量

### 编译时影响

- **零运行时开销**: 纯预处理器指令
- **编译器友好**: 不增加编译时间
- **头文件大小**: 对编译速度无显著影响

### 运行时考虑

该文件本身不影响运行时,但策略影响:
- **优点**: 代码可以访问新API,在新系统上获得更好性能
- **缺点**: 需要运行时检测,增加少量分支开销(通常可忽略)

## 相关文件

### DirectWrite 版本演进

| Windows版本 | DirectWrite版本 | NTDDI_VERSION | 新增功能 |
|-------------|----------------|---------------|----------|
| Windows 7 | DWrite 1.0 | NTDDI_WIN7 | 基础文本渲染 |
| Windows 8 | DWrite 1.1 | NTDDI_WIN8 | 自定义字体集 |
| Windows 8.1 | DWrite 2.0 | NTDDI_WINBLUE | 彩色字体 |
| Windows 10 | DWrite 3.0 | NTDDI_WIN10 | 字体下载 |
| Windows 10 RS1 | DWrite 3.1 | NTDDI_WIN10_RS1 | 字体变体 |

### Skia DirectWrite 集成

使用该头文件的 Skia 文件:
- `src/ports/SkTypeface_win_dw.cpp`: DirectWrite 字体实现
- `src/ports/SkScalerContext_win_dw.cpp`: 字形渲染
- `src/ports/SkFontMgr_win_dw.cpp`: 字体管理器

### 使用示例

#### 正确用法

```cpp
// SkTypeface_win_dw.cpp
#include "src/utils/win/SkDWriteNTDDI_VERSION.h"  // 第一个!
#include <dwrite_3.h>
#include "src/utils/win/SkTScopedComPtr.h"

void UseDirectWrite() {
    SkTScopedComPtr<IDWriteFactory> factory;
    // ...
}
```

#### 错误用法

```cpp
// 错误:顺序颠倒
#include <dwrite_3.h>  // 错误!
#include "src/utils/win/SkDWriteNTDDI_VERSION.h"  // 太晚了

// 编译错误:
// error: Must include SkDWriteNTDDI_VERSION.h before any Windows or DWrite headers.
```

### 构建系统集成

在 GN 构建文件中:

```gn
# 不需要特殊配置
# 该头文件自动处理版本控制

skia_sources += [
  "src/ports/SkTypeface_win_dw.cpp",
  # 自动包含 SkDWriteNTDDI_VERSION.h
]
```

## 替代方案

### 方案1: 定义最高版本

```cpp
#define NTDDI_VERSION NTDDI_WIN10_RS5
#include <dwrite_3.h>
```

**缺点**:
- 假设特定Windows版本
- 未来新版本需要更新
- 可能与构建系统冲突

### 方案2: 不使用版本保护

等待 DirectWrite 团队移除版本保护。

**缺点**:
- 需要 Windows SDK 更新
- 不在 Skia 控制范围内

### 当前方案优势

- 完全在 Skia 控制内
- 兼容所有构建配置
- 自动支持未来 DirectWrite 版本

## 安全性与兼容性

### 向后兼容性

代码必须处理 API 可能不可用的情况:

```cpp
SkTScopedComPtr<IDWriteFontFaceReference> fontFaceRef;
if (SUCCEEDED(fontFace->QueryInterface(&fontFaceRef))) {
    // 使用新API
} else {
    // 降级到旧API
}
```

### 编译器警告

某些编译器可能警告未使用的接口定义:
- 通常可以安全忽略
- Skia 的代码审查会确保正确使用

该文件展示了 Skia 在处理 Windows SDK 版本控制方面的创新思路,通过简单但有效的预处理器技巧,确保了对 DirectWrite API 的完全访问,同时保持了向后兼容性和构建系统的灵活性。
