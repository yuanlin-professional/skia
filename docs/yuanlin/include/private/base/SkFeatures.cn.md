# SkFeatures 平台特性检测模块

> 源文件: `include/private/base/SkFeatures.h`

## 概述
SkFeatures 是 Skia 的平台检测和特性配置模块,通过预处理器宏自动识别目标平台、CPU 架构、字节序、SIMD 指令集支持等信息。该模块为 Skia 的跨平台编译提供统一的特性抽象层。

## 架构位置
位于 Skia 基础设施层 (private/base),是整个库的编译配置基础。几乎所有源文件都会间接依赖此文件,通过 SkLoadUserConfig.h 引入。

## 平台检测

### 支持的平台宏
| 宏名称 | 平台 | 检测条件 |
|--------|------|----------|
| `SK_BUILD_FOR_WIN` | Windows | `_WIN32` 或 `__SYMBIAN32__` |
| `SK_BUILD_FOR_ANDROID` | Android | `ANDROID` 或 `__ANDROID__` |
| `SK_BUILD_FOR_WASM` | WebAssembly | `__EMSCRIPTEN__` |
| `SK_BUILD_FOR_UNIX` | Unix/Linux | `linux`, `__FreeBSD__`, `__OpenBSD__` 等 |
| `SK_BUILD_FOR_IOS` | iOS | `TARGET_OS_IPHONE` 或 `TARGET_IPHONE_SIMULATOR` |
| `SK_BUILD_FOR_MAC` | macOS | 排除法 (非以上平台的 Apple 系统) |

### 检测逻辑
```cpp
#if defined(_WIN32) || defined(__SYMBIAN32__)
    #define SK_BUILD_FOR_WIN
#elif defined(ANDROID) || defined(__ANDROID__)
    #define SK_BUILD_FOR_ANDROID
#elif defined(__EMSCRIPTEN__)
    #define SK_BUILD_FOR_WASM
// ... 更多条件
#endif
```

- **优先级**: Windows > Android > WASM > Unix > iOS > macOS
- **Apple 平台**: 需要包含 `<TargetConditionals.h>` 获取详细信息
- **WebAssembly**: 单独识别,避免误认为 Unix

### Unix 家族识别
支持的 Unix 变体:
- Linux (`linux`, `__linux`)
- FreeBSD (`__FreeBSD__`)
- OpenBSD (`__OpenBSD__`)
- NetBSD (`__NetBSD__`)
- DragonFly BSD (`__DragonFly__`)
- Solaris (`__sun`)
- Fuchsia (`__Fuchsia__`)
- GNU Hurd (`__GNU__`)
- glibc 系统 (`__GLIBC__`)

## CPU 架构检测

### x86 架构
```cpp
#if defined(__i386) || defined(_M_IX86) || defined(__x86_64__) || defined(_M_X64)
  #define SK_CPU_X86 1
#endif
```
- 支持 32 位和 64 位
- 识别 GCC 和 MSVC 的宏

### LoongArch 架构
```cpp
#if defined(__loongarch__) || defined(__loongarch64)
  #define SK_CPU_LOONGARCH 1
#endif
```
中国自主指令集架构。

### PowerPC 架构
```cpp
#if defined(__powerpc__) || defined(__powerpc64__)
  #define SK_CPU_PPC 1
#endif
```

### ARM 架构
```cpp
#if defined(__arm__) && (!defined(__APPLE__) || !TARGET_IPHONE_SIMULATOR)
    #define SK_CPU_ARM32
#elif defined(__aarch64__)
    #define SK_CPU_ARM64
#endif
```
- 区分 32 位和 64 位 ARM
- 排除 iOS 模拟器 (运行在 x86 上)

#### NEON 支持
```cpp
#if !defined(SK_ARM_HAS_NEON) && defined(__ARM_NEON)
    #define SK_ARM_HAS_NEON
#endif
```
- 所有 64 位 ARM 芯片都支持 NEON
- 许多 32 位 ARM 芯片也支持

## 字节序检测

### 大小端宏
```cpp
#if !defined(SK_CPU_BENDIAN) && !defined(SK_CPU_LENDIAN)
    #if defined(__BYTE_ORDER__) && (__BYTE_ORDER__ == __ORDER_BIG_ENDIAN__)
        #define SK_CPU_BENDIAN
    #elif defined(__BYTE_ORDER__) && (__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__)
        #define SK_CPU_LENDIAN
    #elif /* 手动架构检测 */
        #define SK_CPU_BENDIAN
    #else
        #define SK_CPU_LENDIAN  // 默认小端
    #endif
#endif
```

### 大端架构识别
通过 CPU 架构推断:
- SPARC (`__sparc`, `__sparc__`)
- PowerPC (`_POWER`, `__powerpc__`, `__ppc__`)
- PA-RISC (`__hppa`)
- MIPS Big Endian (`_MIPSEB`)
- ARM Big Endian (`__ARMEB__`)
- s390 (`__s390__`)
- 大端 SH (`__sh__` + `__BIG_ENDIAN__`)
- 大端 IA-64 (`__ia64` + `__BIG_ENDIAN__`)

### 大端支持警告
```cpp
#if defined(SK_CPU_BENDIAN) && !defined(I_ACKNOWLEDGE_SKIA_DOES_NOT_SUPPORT_BIG_ENDIAN)
    #error "The Skia team is not endian-savvy enough to support big-endian CPUs."
    #error "If you still want to use Skia,"
    #error "please define I_ACKNOWLEDGE_SKIA_DOES_NOT_SUPPORT_BIG_ENDIAN."
#endif
```
Skia 明确声明不支持大端系统,需要用户显式确认才能编译。

## SIMD 指令集检测

### SSE 级别定义
```cpp
#define SK_CPU_SSE_LEVEL_SSE1     10
#define SK_CPU_SSE_LEVEL_SSE2     20
#define SK_CPU_SSE_LEVEL_SSE3     30
#define SK_CPU_SSE_LEVEL_SSSE3    31
#define SK_CPU_SSE_LEVEL_SSE41    41
#define SK_CPU_SSE_LEVEL_SSE42    42
#define SK_CPU_SSE_LEVEL_AVX      51
#define SK_CPU_SSE_LEVEL_AVX2     52
#define SK_CPU_SSE_LEVEL_SKX      60  // AVX-512
```

### GCC/Clang 检测
```cpp
#if defined(__AVX512F__) && defined(__AVX512DQ__) && /* ... */
    #define SK_CPU_SSE_LEVEL SK_CPU_SSE_LEVEL_SKX
#elif defined(__AVX2__)
    #define SK_CPU_SSE_LEVEL SK_CPU_SSE_LEVEL_AVX2
#elif defined(__AVX__)
    #define SK_CPU_SSE_LEVEL SK_CPU_SSE_LEVEL_AVX
// ... 逐级降级检测
#endif
```
- 按从高到低顺序检测
- 确保设置最高可用级别

### MSVC 检测
```cpp
#if defined(__AVX512F__) && /* ... */
    #define SK_CPU_SSE_LEVEL SK_CPU_SSE_LEVEL_SKX
#elif defined(__AVX2__)
    #define SK_CPU_SSE_LEVEL SK_CPU_SSE_LEVEL_AVX2
#elif defined(_M_X64) || defined(_M_AMD64)
    #define SK_CPU_SSE_LEVEL SK_CPU_SSE_LEVEL_SSE2  // 64位保证SSE2
#elif defined(_M_IX86_FP)
    #if _M_IX86_FP >= 2
        #define SK_CPU_SSE_LEVEL SK_CPU_SSE_LEVEL_SSE2
    #elif _M_IX86_FP == 1
        #define SK_CPU_SSE_LEVEL SK_CPU_SSE_LEVEL_SSE1
    #endif
#endif
```

### LSX (LoongArch SIMD)
```cpp
#define SK_CPU_LSX_LEVEL_LSX      70
#define SK_CPU_LSX_LEVEL_LASX     80

#if defined(__loongarch_asx)
    #define SK_CPU_LSX_LEVEL SK_CPU_LSX_LEVEL_LASX
#elif defined(__loongarch_sx)
    #define SK_CPU_LSX_LEVEL SK_CPU_LSX_LEVEL_LSX
#endif
```

## 编译器特性

### SK_RESTRICT 宏
```cpp
#if defined(SK_BUILD_FOR_WIN) && !defined(__clang__)
    #define SK_RESTRICT __restrict
#else
    #define SK_RESTRICT __restrict__
#endif
```
- Windows MSVC: `__restrict`
- 其他编译器: `__restrict__`
- 用于指针别名优化

## 内部实现细节

### 条件编译层次
```cpp
#if !defined(SK_BUILD_FOR_*) && !defined(SK_BUILD_FOR_*)
    // 仅当用户未预定义时才自动检测
    #if defined(_WIN32)
        #define SK_BUILD_FOR_WIN
    // ...
    #endif
#endif
```
允许用户在编译命令行中强制指定平台。

### Apple 平台的特殊处理
```cpp
#ifdef __APPLE__
    #include <TargetConditionals.h>
#endif

#if TARGET_OS_IPHONE || TARGET_IPHONE_SIMULATOR
    #define SK_BUILD_FOR_IOS
#else
    #define SK_BUILD_FOR_MAC
#endif
```
需要 Apple 的条件宏区分 iOS 和 macOS。

### WebAssembly 的识别
```cpp
#elif defined(__EMSCRIPTEN__)
    // WASM toolchains expose a Unix-like compilation environment, but it is
    // not Unix (e.g. posix signals are not supported).
    #define SK_BUILD_FOR_WASM
```
虽然 Emscripten 暴露类 Unix 环境,但需要单独处理。

## 依赖关系

### 依赖的模块
- `<TargetConditionals.h>` (仅 Apple 平台)

### 被依赖的模块
几乎所有 Skia 源文件:
- 平台特定代码路径
- SIMD 优化代码
- 字节序相关操作
- 系统 API 调用

## 设计模式与设计决策

### 自动检测优先
优先使用编译器定义的宏自动检测,仅在必要时要求用户干预。

### 保护性宏定义
```cpp
#if !defined(SK_CPU_LENDIAN) && !defined(SK_CPU_BENDIAN)
    // 检测逻辑
#endif
```
允许外部预定义覆盖自动检测。

### 降级检测策略
SIMD 指令集从高到低检测,确保使用最优版本。

### 明确的不支持声明
对于不支持的配置 (如大端),通过编译错误明确告知,避免潜在错误。

## 性能考量

### 编译期决策
所有检测在编译期完成,无运行时开销。

### SIMD 优化路径选择
```cpp
#if SK_CPU_SSE_LEVEL >= SK_CPU_SSE_LEVEL_SSE42
    // 使用 SSE4.2 优化代码
#elif SK_CPU_SSE_LEVEL >= SK_CPU_SSE_LEVEL_SSE2
    // 使用 SSE2 优化代码
#else
    // 标量代码
#endif
```
根据目标平台编译最优代码路径。

### 指针别名优化
`SK_RESTRICT` 提示编译器进行指针别名分析优化。

## 平台相关说明

### Android NDK
自动识别 `ANDROID` 或 `__ANDROID__` 宏。

### iOS 模拟器
特殊处理避免错误识别为 ARM:
```cpp
defined(__arm__) && (!defined(__APPLE__) || !TARGET_IPHONE_SIMULATOR)
```

### Windows on ARM
MSVC 定义的 ARM 宏会被正确识别。

### 交叉编译
编译器的目标架构宏反映目标平台,而非主机平台。

## 使用示例

### 平台特定代码
```cpp
#if defined(SK_BUILD_FOR_WIN)
    #include <windows.h>
    void PlatformSpecificFunc() { /* Windows 实现 */ }
#elif defined(SK_BUILD_FOR_ANDROID)
    #include <android/log.h>
    void PlatformSpecificFunc() { /* Android 实现 */ }
#else
    void PlatformSpecificFunc() { /* 通用实现 */ }
#endif
```

### SIMD 优化
```cpp
#if SK_CPU_SSE_LEVEL >= SK_CPU_SSE_LEVEL_AVX2
    #include <immintrin.h>
    __m256i ProcessAVX2(const __m256i* data) { /* AVX2 代码 */ }
#elif SK_CPU_SSE_LEVEL >= SK_CPU_SSE_LEVEL_SSE2
    #include <emmintrin.h>
    __m128i ProcessSSE2(const __m128i* data) { /* SSE2 代码 */ }
#endif
```

### 字节序处理
```cpp
uint32_t ReadU32(const uint8_t* buf) {
#if defined(SK_CPU_LENDIAN)
    return *(const uint32_t*)buf;
#else
    return (buf[0] << 24) | (buf[1] << 16) | (buf[2] << 8) | buf[3];
#endif
}
```

### NEON 优化
```cpp
#if defined(SK_ARM_HAS_NEON)
    #include <arm_neon.h>
    void ProcessNEON(const uint8_t* src, uint8_t* dst, size_t count) {
        // NEON intrinsics
    }
#endif
```

## 相关文件
| 文件 | 关系 |
|------|------|
| `SkLoadUserConfig.h` | 首先包含此文件 |
| `SkUserConfig.h` | 用户自定义配置 |
| SIMD 实现文件 | 使用指令集宏选择代码 |
| 平台特定实现 | 使用平台宏条件编译 |

## 历史与演进
- 2022 年统一整理,集中平台检测逻辑
- 持续添加新平台支持 (如 LoongArch)
- 改进 SIMD 检测逻辑
- 明确大端不支持声明
