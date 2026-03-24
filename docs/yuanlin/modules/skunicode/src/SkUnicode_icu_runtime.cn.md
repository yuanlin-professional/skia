# SkUnicode_icu_runtime

> 源文件: modules/skunicode/src/SkUnicode_icu_runtime.cpp

## 概述

`SkUnicode_icu_runtime.cpp` 实现了运行时动态加载 ICU 库的功能。该文件通过 dlopen/dlsym 等系统调用在运行时查找和加载 ICU 共享库,解析需要的符号,并填充 `SkICULib` 结构体。这种动态加载机制允许 Skia 在没有编译时 ICU 依赖的情况下使用 ICU 功能,适用于需要灵活部署或支持多个 ICU 版本的场景。

运行时加载的主要优势是可以适应系统上安装的不同 ICU 版本,通过符号名称中的版本后缀自动检测并使用可用的 ICU 版本。

## 架构位置

```
skia/
└── modules/
    └── skunicode/
        └── src/
            ├── SkUnicode_icupriv.h       # ICU 接口定义
            ├── SkUnicode_icu_runtime.cpp # 本文件:运行时加载
            └── SkUnicode_icu_builtin.cpp # 编译时链接
```

## 主要函数

### SkLoadICULib

唯一的公共函数,加载 ICU 库并返回函数表:

```cpp
std::unique_ptr<SkICULib> SkLoadICULib();
```

**实现流程:**

1. **打开共享库**
   ```cpp
   static constexpr char const* gLibPaths[] = { SK_RUNTIME_ICU_PATHS };
   void* dlhnd = nullptr;
   for (const auto path : gLibPaths) {
       dlhnd = dlopen(path, RTLD_LAZY);
       if (dlhnd) break;
   }
   ```

2. **解析符号**
   ```cpp
   auto resolve_sym = [&](void* hnd, const char name[], bool required) -> void* {
       // 从 kMinVer 到 kMaxVer 搜索版本化的符号
       for (;;) {
           const auto sym = SkStringPrintf("%s_%d", name, icu_ver);
           if (auto* addr = dlsym(dlhnd, sym.c_str())) {
               return addr;
           }
           if (icu_ver == search_to) break;
           icu_ver++;
       }
       return nullptr;
   };
   ```

3. **填充函数指针**
   ```cpp
   SkICULib lib {};
   #define SKICU_FUNC(fname) *(void**)(&lib.f_##fname) = resolve_sym(dlhnd, #fname, true);
   SKICU_EMIT_FUNCS
   ```

4. **处理特殊函数**
   ```cpp
   *(void**)(&lib.f_ubrk_clone_) = resolve_sym(dlhnd, "ubrk_clone");
   *(void**)(&lib.f_ubrk_safeClone_) = resolve_sym(dlhnd, "ubrk_safeClone");
   *(void**)(&lib.f_ubrk_getLocaleByType) = resolve_sym(dlhnd, "ubrk_getLocaleByType");
   ```

## 内部实现细节

### ICU 版本检测

ICU 符号名称包含版本后缀,如 `u_errorName_44`, `u_errorName_45` 等:

```cpp
static constexpr int kMinVer = 44,
                     kMaxVer = 100;

const auto sym = SkStringPrintf("%s_%d", name, icu_ver);
```

**检测策略:**
- 首次调用时从 kMinVer 搜索到 kMaxVer
- 找到第一个可用符号后记录版本号
- 后续调用都使用相同版本号

### 符号解析辅助函数

```cpp
auto resolve_sym = [&](void* hnd, const char name[], bool required = false) -> void* {
    static constexpr int kMinVer = 44, kMaxVer = 100;
    const auto search_to = icu_ver > 0 ? icu_ver : kMaxVer;
    icu_ver = icu_ver > 0 ? icu_ver : kMinVer;

    for (;;) {
        const auto sym = SkStringPrintf("%s_%d", name, icu_ver);
        if (auto* addr = dlsym(dlhnd, sym.c_str())) {
            return addr;
        }
        if (icu_ver == search_to) break;
        icu_ver++;
    }

    if (required) {
        resolved_required_syms = false;
    }
    return nullptr;
};
```

**参数:**
- `hnd` - 库句柄
- `name` - 函数名称(无版本后缀)
- `required` - 是否必需

### 函数指针赋值技巧

使用类型双关转换赋值函数指针:

```cpp
*(void**)(&lib.f_##fname) = resolve_sym(dlhnd, #fname, true);
```

**原因:**
- POSIX 标准不保证 `void*` 和函数指针可互换
- 但实践中在 POSIX 系统上安全
- Clang 尚未实现 DR573,不能使用 `reinterpret_cast`

### 错误处理

```cpp
if (!dlhnd) {
    SkDEBUGF("ICU loader: failed to open libicuuc.\n");
    return nullptr;
}

if (!resolved_required_syms || (!lib.f_ubrk_clone_ && !lib.f_ubrk_safeClone_)) {
    SkDEBUGF("ICU loader: failed to resolve required symbols.");
    dlclose(dlhnd);
    return nullptr;
}
```

**失败情况:**
- 无法打开共享库
- 必需符号未解析
- 克隆函数都不可用

## 依赖关系

**系统依赖:**
- `<dlfcn.h>` - 动态链接接口(dlopen, dlsym, dlclose)

**Skia 依赖:**
- `include/core/SkString.h` - 字符串格式化
- `include/core/SkTypes.h` - 基础类型
- `modules/skunicode/src/SkUnicode_icupriv.h` - ICU 接口

**编译时配置:**
- `SK_RUNTIME_ICU_PATHS` - ICU 库路径列表

## 设计模式与设计决策

### 懒加载

只在第一次调用 `SkGetICULib()` 时加载:

```cpp
const SkICULib* SkGetICULib() {
    static const auto gICU = SkLoadICULib();
    return gICU.get();
}
```

### 版本自适应

自动检测可用的 ICU 版本,无需手动配置:
- 支持 ICU 44 到 100 的所有版本
- 向后兼容旧版本
- 向前兼容未来版本

### 可选符号

某些符号是可选的:

```cpp
*(void**)(&lib.f_ubrk_clone_) = resolve_sym(dlhnd, "ubrk_clone");
*(void**)(&lib.f_ubrk_safeClone_) = resolve_sym(dlhnd, "ubrk_safeClone");
```

只要其中一个可用即可。

### 全有或全无

如果必需符号缺失,整个加载失败:

```cpp
if (!resolved_required_syms) {
    dlclose(dlhnd);
    return nullptr;
}
```

这确保了库的一致性。

## 性能考量

### 加载时间

首次加载包括:
- 打开共享库
- 解析 30+ 个符号
- 每个符号可能尝试多个版本

**优化:**
- 使用 RTLD_LAZY 延迟符号解析
- 首次解析后缓存版本号
- 只加载一次(单例)

### 运行时开销

加载后,函数调用通过指针:
- 一次额外的内存访问
- 轻微的性能影响
- 但避免了重新加载

### 内存占用

- 共享库保持加载(不调用 dlclose)
- 函数指针表约 240 字节
- 总体开销很小

## 相关文件

**接口:**
- `/modules/skunicode/src/SkUnicode_icupriv.h` - ICU 接口定义

**替代实现:**
- `/modules/skunicode/src/SkUnicode_icu_builtin.cpp` - 编译时链接

**使用者:**
- `/modules/skunicode/src/SkUnicode_icu.cpp` - ICU Unicode 实现
