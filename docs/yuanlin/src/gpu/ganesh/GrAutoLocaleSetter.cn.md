# GrAutoLocaleSetter — 自动区域设置管理器

> 源文件: `src/gpu/ganesh/GrAutoLocaleSetter.h`

## 概述

`GrAutoLocaleSetter` 是一个 RAII（资源获取即初始化）辅助类，用于在着色器编译期间临时切换线程的区域设置 (locale)。这对于确保着色器代码生成中浮点数格式化使用 "C" 区域设置至关重要——因为某些区域设置会将小数点 `.` 替换为逗号 `,`，从而导致生成的 GLSL/HLSL 代码语法错误。对象在构造时设置新区域，在析构时自动恢复原始区域设置。

## 架构位置

```
着色器编译管线
    └── GrGLSLShaderBuilder / GrGLSLUniformHandler
        └── GrAutoLocaleSetter (本文件 - 区域设置保护)
            ├── Windows: setlocale + _configthreadlocale
            ├── macOS/iOS: newlocale + uselocale (xlocale)
            ├── Linux: newlocale + uselocale (locale_t)
            └── Android: 无操作（NDK 不支持 locale）
```

## 主要类与结构体

### GrAutoLocaleSetter

继承自 `SkNoncopyable`，不可拷贝。

| 平台 | 成员变量 | 描述 |
|------|----------|------|
| Windows | `fOldPerThreadLocale` (int) | 旧的线程区域配置模式 |
| Windows | `fShouldRestoreLocale` (bool) | 是否需要恢复旧区域 |
| Windows | `fOldLocale` (SkString) | 旧区域设置名称字符串 |
| POSIX (locale_t) | `fOldLocale` (locale_t) | 旧的区域设置句柄 |
| POSIX (locale_t) | `fLocale` (locale_t) | 新创建的区域设置句柄 |
| Android | (无成员) | 完全空操作 |

## 公共 API 函数

### 构造函数

```cpp
GrAutoLocaleSetter(const char* name);
```

设置当前线程的区域为 `name`（通常为 `"C"`）。行为因平台而异：

- **Windows**: 先通过 `_configthreadlocale(_ENABLE_PER_THREAD_LOCALE)` 启用每线程区域设置，然后调用 `setlocale(LC_ALL, name)` 切换。
- **macOS/iOS (xlocale)**: 若 `name` 为 `"C"`，将其转换为 `nullptr`（xlocale 中 nullptr 表示 C 区域）。通过 `newlocale()` 创建新区域，`uselocale()` 应用到当前线程。
- **Linux 等 POSIX**: 直接使用 `newlocale()` + `uselocale()`。
- **Android**: 无操作（NDK 不支持区域 API）。

### 析构函数

```cpp
~GrAutoLocaleSetter();
```

恢复构造时保存的原始区域设置：

- **Windows**: 恢复旧区域字符串和线程区域配置模式。
- **POSIX (locale_t)**: 调用 `uselocale(fOldLocale)` 恢复，然后 `freelocale(fLocale)` 释放。
- **Android**: 无操作。

## 内部实现细节

1. **平台条件编译宏**:
   - `HAVE_XLOCALE`: macOS/iOS 使用 `<xlocale.h>`（Apple 特有的线程安全区域设置 API）。
   - `HAVE_LOCALE_T`: 判断平台是否支持 `locale_t` 类型。Android、uClibc、Newlib 不支持。
   - 两个宏在文件末尾通过 `#undef` 清理，避免泄漏到其他头文件。

2. **Windows 线程安全**: 通过 `_configthreadlocale(_ENABLE_PER_THREAD_LOCALE)` 将区域设置限制在当前线程，避免影响其他线程的格式化行为。

3. **错误处理**: 若 `setlocale()` 或 `newlocale()` 失败（返回 null），析构函数中不会尝试恢复，避免无效操作。

4. **xlocale 特殊处理**: macOS 的 `newlocale()` 要求用 `nullptr` 而非 `"C"` 来表示 C 区域，因此进行了字符串比较和转换。

## 依赖关系

- **`include/core/SkTypes.h`**: 平台检测宏 (`SK_BUILD_FOR_WIN`, `SK_BUILD_FOR_MAC` 等)
- **`include/private/base/SkNoncopyable.h`**: 不可拷贝基类
- **`include/core/SkString.h`**: Windows 平台存储旧区域字符串
- **`<locale.h>`**: POSIX 区域设置 API (非 Android)
- **`<xlocale.h>`**: Apple 平台线程安全区域 API
- **`<cstring>`**: `strcmp` 用于 xlocale "C" 检测

## 设计模式与设计决策

1. **RAII 模式**: 典型的 RAII 使用——构造获取资源（设置区域），析构释放资源（恢复区域）。即使在异常或提前返回情况下也能正确恢复。

2. **不可拷贝**: 继承 `SkNoncopyable` 防止拷贝，因为区域设置状态恢复必须严格配对，拷贝会导致双重恢复。

3. **Android 空操作设计**: Android NDK 不提供 locale API，但由于 Android 默认使用类似 C 的区域设置，不修改区域在实践中是安全的。

4. **线程安全考量**: 所有平台路径均使用线程局部的区域设置 API（Windows 的 per-thread locale、POSIX 的 `uselocale()`），避免影响其他线程。

## 性能考量

- 区域设置切换涉及系统调用，但仅在着色器编译时使用，不在渲染热路径上。
- Windows 路径包含字符串拷贝（`SkString` 存储旧区域名），有少量堆分配开销。
- POSIX 路径使用 `newlocale()` 创建新区域对象，涉及少量内存分配，在析构时通过 `freelocale()` 释放。
- 着色器编译通常发生在首次使用时或程序初始化阶段，区域切换开销可忽略。

## 相关文件

- `src/gpu/ganesh/glsl/GrGLSLShaderBuilder.cpp` — 着色器构建器，使用此类保护区域设置
- `src/sksl/SkSLGLSLCodeGenerator.cpp` — GLSL 代码生成器
- `include/private/base/SkNoncopyable.h` — 不可拷贝基类
