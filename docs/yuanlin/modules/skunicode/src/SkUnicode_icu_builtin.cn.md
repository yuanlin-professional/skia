# SkUnicode_icu_builtin

> 源文件: modules/skunicode/src/SkUnicode_icu_builtin.cpp

## 概述

`SkUnicode_icu_builtin.cpp` 实现了编译时链接 ICU 库的功能,通过直接使用 ICU 函数地址填充 `SkICULib` 结构体。与运行时动态加载不同,该实现在编译时就确定了 ICU 函数的地址,适用于静态链接 ICU 或使用系统提供的 ICU 头文件的场景。该实现使用模板元编程和 SFINAE 技术处理不同 ICU 版本的 API 差异。

## 架构位置

```
skia/modules/skunicode/src/
├── SkUnicode_icupriv.h         # ICU 接口
├── SkUnicode_icu_builtin.cpp   # 本文件
└── SkUnicode_icu_runtime.cpp   # 运行时加载
```

## 主要实现

### SkLoadICULib 函数

```cpp
std::unique_ptr<SkICULib> SkLoadICULib() {
    return std::make_unique<SkICULib>(SkICULib{
        SKICU_EMIT_FUNCS  // 展开为所有 ICU 函数地址
        &SkUbrkClone<const UBreakIterator*>::clone,
        nullptr,
        &SkUbrkGetLocaleByType<const UBreakIterator*>::getLocaleByType,
    });
}
```

### 版本兼容性模板

**ubrk_clone vs ubrk_safeClone:**

```cpp
template<typename T, typename = void>
struct SkUbrkClone {
    static UBreakIterator* clone(T bi, UErrorCode* status) {
        return ubrk_safeClone(bi, nullptr, nullptr, status);
    }
};

template<typename T>
struct SkUbrkClone<T, std::void_t<decltype(ubrk_clone(std::declval<T>(), nullptr))>> {
    static UBreakIterator* clone(T bi, UErrorCode* status) {
        return ubrk_clone(bi, status);
    }
};
```

**ubrk_getLocaleByType:**

```cpp
template<typename T, typename = void>
struct SkUbrkGetLocaleByType {
    static const char* getLocaleByType(T bi, ULocDataLocaleType type, UErrorCode* status) {
        *status = U_UNSUPPORTED_ERROR;
        return nullptr;
    }
};

template<typename T>
struct SkUbrkGetLocaleByType<T, std::void_t<decltype(ubrk_getLocaleByType(...))>> {
    static const char* getLocaleByType(T bi, ULocDataLocaleType type, UErrorCode* status) {
        return ubrk_getLocaleByType(bi, type, status);
    }
};
```

## 设计模式

### SFINAE (Substitution Failure Is Not An Error)

使用 `std::void_t` 检测函数是否存在:
- 如果函数存在,使用特化版本
- 如果函数不存在,使用默认版本

### 策略模式

通过模板特化选择不同的实现策略。

## 性能考量

- 直接函数调用,无间接开销
- 编译时确定地址,无运行时查找
- 最优性能

## 相关文件

- `/modules/skunicode/src/SkUnicode_icupriv.h`
- `/modules/skunicode/src/SkUnicode_icu.cpp`
