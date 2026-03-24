# SkUnicode_icupriv

> 源文件: modules/skunicode/src/SkUnicode_icupriv.h

## 概述

`SkUnicode_icupriv.h` 定义了 Skia ICU Unicode 实现的私有接口,包括 ICU 函数指针结构体和动态加载 ICU 库的接口。该文件的主要目的是支持运行时或编译时链接 ICU 库,允许在不同平台和配置下灵活使用 ICU 功能。通过函数指针表的方式,Skia 可以动态加载 ICU 库,或使用编译时链接的 ICU 函数。

这种设计使得 Skia 能够适应不同的部署场景:系统 ICU、捆绑 ICU、动态加载 ICU 等,同时保持代码的统一性。

## 架构位置

```
skia/
└── modules/
    └── skunicode/
        └── src/
            ├── SkUnicode_icupriv.h       # 本文件:ICU 私有接口
            ├── SkUnicode_icu.cpp         # ICU Unicode 实现
            ├── SkUnicode_icu_runtime.cpp # 运行时 ICU 加载
            └── SkUnicode_icu_builtin.cpp # 编译时 ICU 链接
```

## 主要类与结构体

### SkICULib 结构体

封装所有需要的 ICU 函数指针:

```cpp
struct SkICULib {
    // 使用宏定义所有函数指针
    SKICU_EMIT_FUNCS

    // 版本兼容的克隆函数
    UBreakIterator* (*f_ubrk_clone_)(const UBreakIterator*, UErrorCode*);
    UBreakIterator* (*f_ubrk_safeClone_)(const UBreakIterator*, void*, int32_t*, UErrorCode*);

    // Android 不暴露的函数
    const char* (*f_ubrk_getLocaleByType)(const UBreakIterator*, ULocDataLocaleType, UErrorCode*);
};
```

### SKICU_EMIT_FUNCS 宏

定义所有必需的 ICU 函数:

```cpp
#define SKICU_EMIT_FUNCS              \
    SKICU_FUNC(u_errorName)           \
    SKICU_FUNC(u_hasBinaryProperty)   \
    SKICU_FUNC(u_getIntPropertyValue) \
    SKICU_FUNC(u_iscntrl)             \
    SKICU_FUNC(u_isspace)             \
    SKICU_FUNC(u_isWhitespace)        \
    SKICU_FUNC(u_strToUpper)          \
    SKICU_FUNC(ubidi_close)           \
    SKICU_FUNC(ubidi_getDirection)    \
    SKICU_FUNC(ubidi_getLength)       \
    SKICU_FUNC(ubidi_getLevelAt)      \
    SKICU_FUNC(ubidi_openSized)       \
    SKICU_FUNC(ubidi_reorderVisual)   \
    SKICU_FUNC(ubidi_setPara)         \
    SKICU_FUNC(ubrk_close)            \
    SKICU_FUNC(ubrk_current)          \
    SKICU_FUNC(ubrk_first)            \
    SKICU_FUNC(ubrk_following)        \
    SKICU_FUNC(ubrk_getRuleStatus)    \
    SKICU_FUNC(ubrk_next)             \
    SKICU_FUNC(ubrk_open)             \
    SKICU_FUNC(ubrk_preceding)        \
    SKICU_FUNC(ubrk_setText)          \
    SKICU_FUNC(ubrk_setUText)         \
    SKICU_FUNC(uloc_forLanguageTag)   \
    SKICU_FUNC(uloc_getDefault)       \
    SKICU_FUNC(uscript_getScript)     \
    SKICU_FUNC(utext_close)           \
    SKICU_FUNC(utext_openUChars)      \
    SKICU_FUNC(utext_openUTF8)
```

## 公共 API 函数

### SkLoadICULib

加载 ICU 库并创建函数指针表:

```cpp
std::unique_ptr<SkICULib> SkLoadICULib();
```

**实现:**
- `SkUnicode_icu_runtime.cpp` - 动态加载实现
- `SkUnicode_icu_builtin.cpp` - 编译时链接实现

### SkGetICULib

获取已加载的 ICU 库(单例):

```cpp
const SkICULib* SkGetICULib();
```

**实现在 `SkUnicode_icu.cpp`:**
```cpp
const SkICULib* SkGetICULib() {
    static const auto gICU = SkLoadICULib();
    return gICU.get();
}
```

## 内部实现细节

### 函数指针定义

使用宏展开函数指针:

```cpp
#define SKICU_FUNC(funcname) decltype(funcname)* f_##funcname;
struct SkICULib {
    SKICU_EMIT_FUNCS
    // ...
};
#undef SKICU_FUNC
```

展开后相当于:

```cpp
struct SkICULib {
    decltype(u_errorName)* f_u_errorName;
    decltype(u_hasBinaryProperty)* f_u_hasBinaryProperty;
    // ...
};
```

### 版本兼容性处理

**ubrk_clone vs ubrk_safeClone:**

- `ubrk_clone` 在 ICU69 中作为草案添加,Android API 31 引入
- `ubrk_safeClone` 在 ICU69 中废弃,Android 不暴露
- 需要同时支持两个版本

**ubrk_getLocaleByType:**

- ICU 自版本 2.8 就存在
- 但 Android NDK 不包含
- 使用可选指针,允许 nullptr

### ICU 函数分类

**字符属性:**
- `u_hasBinaryProperty`, `u_getIntPropertyValue`
- `u_iscntrl`, `u_isspace`, `u_isWhitespace`

**双向文本:**
- `ubidi_*` 系列函数

**文本分割:**
- `ubrk_*` 系列函数

**文本转换:**
- `u_strToUpper`

**区域设置:**
- `uloc_*` 系列函数

**文本容器:**
- `utext_*` 系列函数

## 依赖关系

**ICU 头文件:**
- `<unicode/ubidi.h>` - 双向文本
- `<unicode/ubrk.h>` - 文本分割
- `<unicode/uchar.h>` - 字符属性
- `<unicode/uloc.h>` - 区域设置
- `<unicode/uscript.h>` - 脚本识别
- `<unicode/ustring.h>` - 字符串操作
- `<unicode/utext.h>` - 文本抽象
- `<unicode/utypes.h>` - 基础类型

**使用者:**
- `SkUnicode_icu.cpp` - ICU Unicode 实现
- `SkUnicode_icu_runtime.cpp` - 动态加载
- `SkUnicode_icu_builtin.cpp` - 静态链接

## 设计模式与设计决策

### 函数指针表模式

使用结构体存储函数指针,而非直接调用:

**优点:**
- 支持动态加载 ICU
- 支持多个 ICU 版本
- 可在运行时选择实现
- 便于测试和模拟

**缺点:**
- 轻微的性能开销(间接调用)
- 需要版本检测和符号解析

### 宏驱动的代码生成

使用 `SKICU_EMIT_FUNCS` 宏定义函数列表:

**优点:**
- 避免代码重复
- 易于添加新函数
- 保持一致性

**使用场景:**
- 定义函数指针
- 解析符号
- 包装函数

### 平台抽象

不同平台使用不同的 `SkLoadICULib` 实现:
- **运行时加载:** 使用 dlopen/LoadLibrary
- **编译时链接:** 直接使用函数地址

### 单例模式

`SkGetICULib()` 返回单例:

```cpp
static const auto gICU = SkLoadICULib();
```

确保只加载一次 ICU 库。

## 性能考量

### 函数调用开销

间接函数调用比直接调用慢:
- 需要额外的内存访问
- 可能影响分支预测
- 但影响通常很小(<5%)

### 加载时间

动态加载 ICU 库有一次性开销:
- 符号解析
- 版本检测
- 依赖加载

但只在初始化时发生一次。

### 内存占用

函数指针表占用空间:
- 约 30 个函数指针
- 每个指针 8 字节(64位)
- 总计约 240 字节

非常小的开销。

## 相关文件

**实现:**
- `/modules/skunicode/src/SkUnicode_icu.cpp` - 使用 ICU 库
- `/modules/skunicode/src/SkUnicode_icu_runtime.cpp` - 动态加载
- `/modules/skunicode/src/SkUnicode_icu_builtin.cpp` - 静态链接

**BiDi 实现:**
- `/modules/skunicode/src/SkBidiFactory_icu_full.h` - 完整 ICU BiDi
