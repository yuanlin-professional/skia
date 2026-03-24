# SkMemset_opts

> 源文件: src/core/SkMemset_opts.cpp

## 概述

`SkMemset_opts` 是 Skia 内存填充优化系统的中央调度模块,负责定义默认实现、检测 CPU 特性并初始化全局函数指针。该模块实现了运行时 CPU 特性检测和多级优化策略,根据处理器能力选择最优的内存填充实现(默认/AVX/ERMS)。

该文件是 SkOpts 框架的典型应用,通过条件编译和运行时检测,在不同平台上自动选择最适合的优化代码路径,无需用户干预即可获得最佳性能。

## 架构位置

`SkMemset_opts` 是优化系统的核心调度器:

```
src/core/
├── SkMemset.h              # 函数指针声明(extern)
├── SkMemset_opts.cpp       # 默认实现定义 + 初始化逻辑(本模块)
├── SkMemset_opts_avx.cpp   # AVX 优化实现
└── SkMemset_opts_erms.cpp  # ERMS 优化实现

src/opts/
├── SkMemset_opts.h         # 跨平台优化实现代码
├── SkOpts_SetTarget.h      # 编译目标设置宏
└── SkOpts_RestoreTarget.h  # 恢复默认编译目标

调用链:
SkMemset.h(声明) → SkMemset_opts.cpp(定义+初始化) → SkMemset_opts.h(实现)
                                    ↓
                        SkMemset_opts_avx.cpp(AVX 覆盖)
                                    ↓
                        SkMemset_opts_erms.cpp(ERMS 覆盖)
```

## 主要功能

| 功能模块 | 说明 |
|---------|------|
| 默认实现定义 | 通过 `DEFINE_DEFAULT` 宏定义初始函数指针 |
| CPU 特性检测 | 检测 AVX 和 ERMS 支持 |
| 优化层级切换 | 依次调用 `Init_Memset_avx/erms()` 覆盖函数指针 |
| 单次初始化保证 | 通过静态变量确保仅初始化一次 |

## 公共 API 函数

### Init_Memset

```cpp
void SkOpts::Init_Memset()
```

**功能**: 初始化内存填充函数指针,根据 CPU 特性选择最优实现。

**实现代码**:
```cpp
void Init_Memset() {
    [[maybe_unused]] static bool gInitialized = init();
}
```

**调用时机**: 由 Skia 全局初始化系统调用,通常在:
- `SkGraphics::Init()`
- 首次使用 SkOpts 函数时(延迟初始化)

**线程安全**: C++11 静态局部变量初始化保证线程安全。

### init (内部函数)

```cpp
static bool init()
```

**功能**: 实际执行初始化逻辑,返回 `true` 标记完成。

**实现逻辑**:
```cpp
static bool init() {
#if defined(SK_ENABLE_OPTIMIZE_SIZE)
    // 优化体积模式:跳过所有优化,使用默认实现
#elif defined(SK_CPU_X86)
    #if SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_AVX
        if (SkCpu::Supports(SkCpu::AVX)) {
            Init_Memset_avx();  // 覆盖为 AVX 实现
        }
    #endif

    if (SkCpu::Supports(SkCpu::ERMS)) {
        Init_Memset_erms();     // 进一步覆盖为 ERMS 实现
    }
#endif
    return true;
}
```

**优化层级**:
1. **默认实现**(通过 `DEFINE_DEFAULT` 定义)
2. **AVX 实现**(如果支持 AVX 且编译时未启用 AVX)
3. **ERMS 实现**(如果支持 ERMS,最高优先级)

## 内部实现细节

### DEFINE_DEFAULT 宏

```cpp
DEFINE_DEFAULT(memset16);
DEFINE_DEFAULT(memset32);
DEFINE_DEFAULT(memset64);
DEFINE_DEFAULT(rect_memset16);
DEFINE_DEFAULT(rect_memset32);
DEFINE_DEFAULT(rect_memset64);
```

**宏展开**(推测):
```cpp
#define DEFINE_DEFAULT(name) \
    void (*name)(...) = SK_OPTS_NS::name;
```

其中 `SK_OPTS_NS` 为默认命名空间,通常指向 SSE2 或 NEON 实现。

### 编译目标控制

```cpp
#define SK_OPTS_TARGET SK_OPTS_TARGET_DEFAULT
#include "src/opts/SkOpts_SetTarget.h"

#include "src/opts/SkMemset_opts.h"  // 实际实现

#include "src/opts/SkOpts_RestoreTarget.h"
```

**流程**:
1. 设置编译目标为默认(SSE2/NEON)
2. 包含实现头文件,编译为默认版本
3. 恢复编译器设置

### 平台条件编译

```cpp
#if defined(SK_ENABLE_OPTIMIZE_SIZE)
    // 所有优化被禁用
#elif defined(SK_CPU_X86)
    // x86/x86_64 平台优化
    #if SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_AVX
        // 编译时未启用 AVX,运行时检测
    #endif
#endif
```

**编译时优化启用**:
- 若编译时指定 `-march=avx`,则 `SK_CPU_SSE_LEVEL >= SK_CPU_SSE_LEVEL_AVX`,跳过运行时检测
- 否则编译基础版本,运行时检测并切换

### 函数指针覆盖机制

```cpp
// 初始状态(默认实现)
memset32 → default_memset32

// 调用 Init_Memset_avx()
memset32 → avx::memset32
g_memset32_prev → default_memset32  // ERMS 需要

// 调用 Init_Memset_erms()
memset32 → erms::memset32
g_memset32_prev → avx::memset32  // 用于小块回退
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `src/core/SkMemset.h` | 函数指针声明 |
| `src/core/SkCpu.h` | CPU 特性检测 |
| `src/opts/SkMemset_opts.h` | 跨平台实现代码 |
| `include/private/base/SkFeatures.h` | 平台和编译特性宏 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `SkGraphics` | 调用 `SkOpts::Init_Memset()` |
| 所有使用 `SkOpts::memset*` 的模块 | 使用初始化后的函数指针 |

### 调用的外部函数

| 函数 | 定义位置 |
|------|----------|
| `Init_Memset_avx()` | `src/core/SkMemset_opts_avx.cpp` |
| `Init_Memset_erms()` | `src/core/SkMemset_opts_erms.cpp` |

## 设计模式与设计决策

### 策略模式

函数指针实现策略模式:
- **Context**: `SkOpts` 命名空间
- **Strategy**: 不同优化实现(default/avx/erms)
- **运行时选择**: 通过 `Init_Memset()` 确定

### 单例初始化

```cpp
static bool gInitialized = init();
```

C++11 静态局部变量保证:
- 仅初始化一次
- 线程安全
- 延迟初始化(首次调用时)

### 编译时和运行时优化结合

```cpp
#if SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_AVX
    if (SkCpu::Supports(SkCpu::AVX)) { ... }
#endif
```

- **编译时已知 AVX**: 直接编译 AVX 代码,跳过运行时检测
- **编译时未知**: 编译基础代码 + 运行时检测切换

### 体积优先模式

```cpp
#if defined(SK_ENABLE_OPTIMIZE_SIZE)
    // 跳过所有优化
#endif
```

嵌入式设备或对代码体积敏感的场景可禁用所有优化。

## 性能考量

### 初始化开销

- **时间成本**: 几微秒(CPU 特性检测 + 函数指针赋值)
- **空间成本**: 每个函数指针 8 字节(x64)
- **调用开销**: 初始化后为零(直接函数指针调用)

### 运行时检测 vs 编译时启用

**场景 1: 编译时启用 AVX**
```bash
clang++ -mavx ...
```
- 优点: 无运行时检测开销,代码体积略小
- 缺点: 不兼容旧 CPU,发布二进制需多版本

**场景 2: 运行时检测**
```bash
clang++ -msse2 ...  # 基础版本
```
- 优点: 单一二进制适配多代 CPU
- 缺点: 代码体积略大(包含多个版本)

### 函数指针调用成本

```cpp
SkOpts::memset32(ptr, val, count);
```

现代 CPU 上:
- 间接跳转延迟: ~5 周期
- 分支预测准确率: 接近 100%(指针不变)
- 实际开销: 可忽略(< 0.1%)

## 使用示例

### 自动初始化

```cpp
#include "include/core/SkGraphics.h"

int main() {
    SkGraphics::Init();  // 内部调用 SkOpts::Init_Memset()

    uint32_t buffer[1000];
    SkOpts::memset32(buffer, 0, 1000);  // 自动使用最优实现
}
```

### 无需显式调用

```cpp
// 首次使用时自动初始化(如果 SkGraphics::Init() 未调用)
SkOpts::memset16(data, value, count);
```

### 调试优化选择

```cpp
#include "src/core/SkCpu.h"

void DebugPrintOptLevel() {
    if (SkCpu::Supports(SkCpu::ERMS)) {
        printf("Using ERMS\n");
    } else if (SkCpu::Supports(SkCpu::AVX)) {
        printf("Using AVX\n");
    } else {
        printf("Using default\n");
    }
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkMemset.h` | 接口 | 函数指针声明 |
| `src/core/SkMemset_opts_avx.cpp` | 协作 | AVX 优化层 |
| `src/core/SkMemset_opts_erms.cpp` | 协作 | ERMS 优化层 |
| `src/opts/SkMemset_opts.h` | 实现 | 跨平台优化代码 |
| `src/core/SkCpu.h` | 依赖 | CPU 特性检测 |
| `src/core/SkOpts.h` | 同级 | 其他优化函数集合 |

## 注意事项

1. **初始化时机**: 虽然有延迟初始化,最好在主函数开始时调用 `SkGraphics::Init()`
2. **线程安全**: 初始化本身线程安全,但初始化期间调用优化函数可能有竞态
3. **体积模式**: `SK_ENABLE_OPTIMIZE_SIZE` 会禁用所有优化,仅保留默认实现
4. **编译时优化**: 若编译时启用高级指令集,部分运行时检测会被优化掉
5. **旧 CPU 兼容性**: 运行时检测确保在不支持 AVX/ERMS 的 CPU 上回退到默认实现
6. **多次调用无害**: `Init_Memset()` 可安全多次调用,静态变量保证仅初始化一次
7. **跨模块共享**: 函数指针为全局变量,所有链接到 Skia 的模块共享同一实现
8. **符号可见性**: 函数指针在 `SkOpts` 命名空间中,外部通过 `SkOpts::memset*` 访问

## 初始化流程图

```
程序启动
    ↓
SkGraphics::Init()
    ↓
SkOpts::Init_Memset()
    ↓
static bool gInitialized = init();
    ↓
初始状态: 默认实现(SSE2/NEON)
    ↓
检测 CPU 特性
    ├── 支持 AVX? → Yes → Init_Memset_avx() → 函数指针 → avx::memset*
    │                                                        ↓
    ├── 支持 ERMS? → Yes → Init_Memset_erms() → 函数指针 → erms::memset*
    │                                                        ↓
    └── 否则 → 保持默认实现
                ↓
        初始化完成,后续调用直接使用最优实现
```

该模块是 Skia 优化框架的典范,展示了如何通过编译时和运行时技术结合,在不牺牲兼容性的前提下提供最优性能。其设计思想可应用于其他需要跨平台优化的 C++ 项目。
