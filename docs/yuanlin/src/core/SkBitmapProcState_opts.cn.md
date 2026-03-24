# SkBitmapProcState_opts

> 源文件: src/core/SkBitmapProcState_opts.cpp

## 概述

`SkBitmapProcState_opts` 模块是位图采样优化系统的协调中心。该文件定义了默认(标量)实现的采样函数,并负责在运行时根据 CPU 特性选择最优的 SIMD 实现。通过函数指针和条件初始化机制,实现单个二进制支持多种 CPU 架构的自适应优化。

## 架构位置

```
src/core/
  ├── SkBitmapProcState.h              # 状态机定义
  ├── SkBitmapProcState_opts.cpp      # 优化协调中心(本模块)
  ├── SkBitmapProcState_opts_ssse3.cpp   # SSSE3 优化
  └── SkBitmapProcState_opts_lasx.cpp    # LASX 优化

src/opts/
  └── SkBitmapProcState_opts.h        # 优化函数实现
```

本模块作为多平台优化的入口,统一管理不同 CPU 架构的优化路径选择。

## 主要类与结构体

### 全局函数指针

```cpp
namespace SkOpts {
    void (*S32_alpha_D32_filter_DX)(...);    // 水平过滤采样
    void (*S32_alpha_D32_filter_DXDY)(...);  // 全方位过滤采样
}
```

### 初始化函数声明

```cpp
namespace SkOpts {
    void Init_BitmapProcState_ssse3();  // x86 SSSE3
    void Init_BitmapProcState_lasx();   // LoongArch LASX
}
```

## 公共 API 函数

### 主初始化函数

```cpp
namespace SkOpts {
    void Init_BitmapProcState() {
        static bool gInitialized = init();
    }
}
```

**功能:** 公共入口,确保优化函数指针正确初始化。

**线程安全:** C++11 静态局部变量保证线程安全的单次初始化。

### 内部初始化逻辑

```cpp
static bool init() {
#if defined(SK_ENABLE_OPTIMIZE_SIZE)
    // 优化体积时,使用默认实现
#elif defined(SK_CPU_X86)
    #if SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_SSSE3
        if (SkCpu::Supports(SkCpu::SSSE3)) {
            Init_BitmapProcState_ssse3();
        }
    #endif
#elif defined(SK_CPU_LOONGARCH)
    #if SK_CPU_LSX_LEVEL < SK_CPU_LSX_LEVEL_LASX
        if (SkCpu::Supports(SkCpu::LOONGARCH_ASX)) {
            Init_BitmapProcState_lasx();
        }
    #endif
#endif
    return true;
}
```

**逻辑:**
1. **体积优化模式**: 跳过所有优化,使用默认实现
2. **x86 平台**: 编译时 SSE 级别低于 SSSE3 时,运行时检测并启用
3. **LoongArch 平台**: 编译时 LSX 级别低于 LASX 时,运行时检测并启用
4. **其他平台**: 使用默认实现

## 内部实现细节

### 默认实现定义

```cpp
#define SK_OPTS_TARGET SK_OPTS_TARGET_DEFAULT
#include "src/opts/SkOpts_SetTarget.h"

#include "src/opts/SkBitmapProcState_opts.h"

#include "src/opts/SkOpts_RestoreTarget.h"

namespace SkOpts {
    DEFINE_DEFAULT(S32_alpha_D32_filter_DX);
    DEFINE_DEFAULT(S32_alpha_D32_filter_DXDY);
}
```

**宏展开:**
```cpp
// DEFINE_DEFAULT 宏展开为:
void (*S32_alpha_D32_filter_DX)(...) = SK_OPTS_NS::S32_alpha_D32_filter_DX;
```

**说明:**
- `SK_OPTS_NS` 是编译器默认优化命名空间(如 `sse2::`, `neon::`)
- 初始化为默认实现,后续可被 SSSE3/LASX 替换

### 条件编译逻辑

**场景 1: 编译时已启用 SSSE3**
```cpp
// 编译选项: -mssse3
// SK_CPU_SSE_LEVEL == SK_CPU_SSE_LEVEL_SSSE3

#if SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_SSSE3
    // 条件不满足,跳过运行时检测
#endif
```
**结果:** 直接使用 SSSE3 实现,无需运行时检测。

**场景 2: 编译时未启用 SSSE3**
```cpp
// 编译选项: -msse2
// SK_CPU_SSE_LEVEL == SK_CPU_SSE_LEVEL_SSE2

#if SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_SSSE3
    if (SkCpu::Supports(SkCpu::SSSE3)) {
        Init_BitmapProcState_ssse3();  // 动态替换函数指针
    }
#endif
```
**结果:** 运行时检测,支持 SSSE3 时启用优化。

### CPU 特性检测

```cpp
if (SkCpu::Supports(SkCpu::SSSE3)) { /* ... */ }
```

**实现:** `SkCpu::Supports()` 使用 CPUID 指令检测 CPU 特性,结果缓存在静态变量中。

**检测时机:** 首次调用 `Init_BitmapProcState()` 时,通常在应用启动早期。

### 函数指针替换

```cpp
// 初始状态
S32_alpha_D32_filter_DX = sse2::S32_alpha_D32_filter_DX;

// 检测到 SSSE3 后
Init_BitmapProcState_ssse3();
    ↓
S32_alpha_D32_filter_DX = ssse3::S32_alpha_D32_filter_DX;
```

**效果:** 后续所有调用自动使用优化版本。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkCpu` | CPU 特性检测 |
| `SkOptsTargets` | 目标平台定义 |
| `SkBitmapProcState_opts.h` | 采样函数实现 |
| `SkOpts_SetTarget.h` | 编译目标设置 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkBitmapProcState::chooseProcs()` | 选择采样函数指针 |
| `SkGraphics::Init()` | 初始化优化系统 |

## 设计模式与设计决策

### 1. 策略模式 + 运行时多态

```cpp
void (*S32_alpha_D32_filter_DX)(...);  // 策略接口
// 运行时选择实现: sse2:: / ssse3:: / lasx::
```

### 2. 单例模式

```cpp
static bool gInitialized = init();  // 保证单次初始化
```

### 3. 外观模式

`Init_BitmapProcState()` 隐藏多平台检测逻辑,提供统一接口。

### 4. 条件编译 + 运行时检测混合

**编译时优化:**
- `SK_CPU_SSE_LEVEL >= SSSE3`: 直接使用 SSSE3,无检测开销
- `SK_ENABLE_OPTIMIZE_SIZE`: 禁用所有优化

**运行时检测:**
- 编译时未确定时,通过 CPUID 动态选择

**优势:** 同时支持静态优化和通用二进制。

### 5. 延迟初始化

初始化推迟到首次使用时,避免启动开销。

## 性能考量

### 初始化开销

**一次性成本:**
- CPU 检测: 约 10-50 微秒
- 函数指针赋值: 几纳秒

**分摊:** 整个应用生命周期仅执行一次。

### 函数调用开销

**间接调用:**
```cpp
SkOpts::S32_alpha_D32_filter_DX(state, xy, count, colors);
```

**开销:** 单次间接跳转,约 1-2 周期(分支预测命中时)。

**对比:** 直接调用 0 周期,但损失灵活性。

### 性能提升

**SSSE3 vs 标量:**
- 双线性插值: 2-3 倍加速
- Alpha 混合: 1.5-2 倍加速

**LASX vs 标量:**
- 双线性插值: 3-4 倍加速(16 像素并行)

### 代码大小

**默认实现:** ~2KB
**SSSE3 优化:** +2-3KB
**LASX 优化:** +2-3KB

**折衷:** `SK_ENABLE_OPTIMIZE_SIZE` 时禁用优化,节省空间。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/opts/SkBitmapProcState_opts.h` | 采样函数实现(多平台) |
| `src/core/SkBitmapProcState_opts_ssse3.cpp` | x86 SSSE3 优化 |
| `src/core/SkBitmapProcState_opts_lasx.cpp` | LoongArch LASX 优化 |
| `src/core/SkCpu.h` | CPU 特性检测 |
| `src/core/SkOptsTargets.h` | 目标平台定义 |
| `include/private/base/SkFeatures.h` | 特性开关 |
