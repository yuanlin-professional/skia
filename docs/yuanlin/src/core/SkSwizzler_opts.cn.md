# SkSwizzler_opts

> 源文件: src/core/SkSwizzler_opts.cpp

## 概述

`SkSwizzler_opts.cpp` 是 Skia 图形库中像素格式转换优化系统的中央协调文件。它负责定义默认的像素转换函数指针、在运行时检测 CPU 特性、并根据检测结果选择最优的平台特定实现(SSSE3、AVX2、LASX 等)。该文件通过 `SkOpts` 命名空间提供统一的优化函数接口,实现了 Skia 的跨平台 SIMD 优化框架。

## 架构位置

该文件是像素处理优化框架的核心协调层,连接默认实现和各种平台特定优化。

```
优化框架架构:
  公共 API (SkSwizzle.h)
    ↓
  SkSwizzlePriv.h (函数指针声明)
    ↓
  SkSwizzler_opts.cpp ← 本文件(初始化和选择)
    ├─ 默认实现(总是可用)
    └─ 运行时选择
       ├─ SSSE3 (x86)
       ├─ HSW/AVX2 (x86)
       └─ LASX (LoongArch)
```

## 主要类与结构体

### SkOpts 命名空间

该文件定义了 `SkOpts` 命名空间中的全局函数指针和初始化逻辑。

### 函数指针定义

**32位到32位转换 (Swizzle_8888_u32):**

| 函数指针 | 功能 | 初始值 |
|---------|------|--------|
| `RGBA_to_BGRA` | RGBA ↔ BGRA 交换 | 默认实现 |
| `RGBA_to_rgbA` | 预乘 alpha | 默认实现 |
| `RGBA_to_bgrA` | 交换并预乘 | 默认实现 |
| `rgbA_to_RGBA` | 反预乘 alpha | 默认实现 |
| `rgbA_to_BGRA` | 反预乘并交换 | 默认实现 |
| `inverted_CMYK_to_RGB1` | 反向 CMYK → RGB | 默认实现 |
| `inverted_CMYK_to_BGR1` | 反向 CMYK → BGR | 默认实现 |

**字节到32位转换 (Swizzle_8888_u8):**

| 函数指针 | 功能 | 初始值 |
|---------|------|--------|
| `RGB_to_RGB1` | RGB 字节 → RGBA | 默认实现 |
| `RGB_to_BGR1` | RGB 字节 → BGRA | 默认实现 |
| `gray_to_RGB1` | 灰度 → RGBA | 默认实现 |
| `grayA_to_RGBA` | 灰度+alpha → RGBA | 默认实现 |
| `grayA_to_rgbA` | 灰度+alpha → 预乘 RGBA | 默认实现 |

## 公共 API 函数

### DEFINE_DEFAULT 宏

```cpp
DEFINE_DEFAULT(RGBA_to_BGRA);
DEFINE_DEFAULT(RGBA_to_rgbA);
// ... 等等
```

**功能:**
为每个函数指针定义默认实现,宏展开类似:
```cpp
Swizzle_8888_u32 RGBA_to_BGRA = SK_OPTS_TARGET::RGBA_to_BGRA;
```

其中 `SK_OPTS_TARGET` 在包含 `SkSwizzler_opts.inc` 前定义为默认目标。

### 外部函数声明

```cpp
void Init_Swizzler_ssse3();
void Init_Swizzler_hsw();
void Init_Swizzler_lasx();
```

声明平台特定的初始化函数,这些函数在其他 `.cpp` 文件中定义。

### Init_Swizzler

```cpp
void Init_Swizzler() {
    [[maybe_unused]] static bool gInitialized = init();
}
```

**功能:**
公共初始化入口,内部调用 `init()` 函数并确保只初始化一次。

**调用时机:**
- 在 Skia 全局初始化时调用
- 或在首次使用 swizzle 函数前延迟调用

**线程安全:**
使用静态局部变量的初始化保证(C++11 起保证线程安全)。

## 内部实现细节

### init() 函数

```cpp
static bool init() {
#if defined(SK_ENABLE_OPTIMIZE_SIZE)
    // 所有 Init_foo 函数在优化代码体积时省略
#elif defined(SK_CPU_X86)
    #if SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_SSSE3
        if (SkCpu::Supports(SkCpu::SSSE3)) { Init_Swizzler_ssse3(); }
    #endif

    #if SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_AVX2
        if (SkCpu::Supports(SkCpu::HSW)) { Init_Swizzler_hsw(); }
    #endif
#elif defined(SK_CPU_LOONGARCH)
    #if SK_CPU_LSX_LEVEL < SK_CPU_LSX_LEVEL_LASX
        if (SkCpu::Supports(SkCpu::LOONGARCH_ASX)) { Init_Swizzler_lasx(); }
    #endif
#endif
    return true;
}
```

### 初始化流程

**1. 默认实现(编译时):**
```cpp
#define SK_OPTS_TARGET SK_OPTS_TARGET_DEFAULT
#include "src/opts/SkOpts_SetTarget.h"
#include "src/opts/SkSwizzler_opts.inc"
#include "src/opts/SkOpts_RestoreTarget.h"
```

所有函数指针初始化为默认实现。

**2. 运行时检测和覆盖:**
```
init() 被调用
  ↓
检测 CPU 特性
  ↓
如果支持 SSSE3 → 调用 Init_Swizzler_ssse3()
  → 覆盖函数指针为 SSSE3 版本
  ↓
如果支持 AVX2 → 调用 Init_Swizzler_hsw()
  → 再次覆盖为 AVX2 版本(最优)
```

**3. 最终结果:**
函数指针指向 CPU 支持的最优实现。

### 条件编译逻辑

**SK_ENABLE_OPTIMIZE_SIZE:**
```cpp
#if defined(SK_ENABLE_OPTIMIZE_SIZE)
    // 跳过所有优化版本,只使用默认实现
#endif
```

**权衡:**
- 减少二进制大小(节省约 10-20 KB)
- 损失性能(约 2-8 倍慢)

**SK_CPU_SSE_LEVEL:**
```cpp
#if SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_AVX2
    // 只有基准编译低于 AVX2 才检测和加载 AVX2 版本
#endif
```

**原因:**
如果基准编译已经是 AVX2,所有代码已经使用 AVX2,无需运行时选择。

### CPU 特性检测

**检测时机:**
- 第一次调用 `Init_Swizzler()` 时
- 通常在程序启动早期

**检测方法(x86):**
```cpp
bool SkCpu::Supports(SkCpu::SSSE3) {
    static uint32_t features = detect_features();
    return (features & kSSSE3_Bit) != 0;
}
```

使用 CPUID 指令查询 CPU 特性位。

**缓存:**
检测结果缓存在静态变量中,避免重复检测开销。

### 默认实现的编译目标

```cpp
#define SK_OPTS_TARGET SK_OPTS_TARGET_DEFAULT
```

`SK_OPTS_TARGET_DEFAULT` 根据平台定义:
- **x86**: 通常是 SSE2(最低要求)
- **ARM**: 可能是 NEON 或普通 ARM
- **LoongArch**: 可能是 LSX 或基础指令
- **其他**: 便携式 C++ 实现

### DEFINE_DEFAULT 宏的实现

```cpp
// 在 SkSwizzlePriv.h 或 SkOptsTargets.h 中定义
#define DEFINE_DEFAULT(name) \
    Swizzle_8888_u32 name = SK_OPTS_TARGET::name
```

**作用:**
1. 声明并定义全局函数指针
2. 初始化为默认实现
3. 允许后续覆盖

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkFeatures.h` | CPU 架构宏定义 |
| `SkCpu.h` | CPU 特性检测 |
| `SkOptsTargets.h` | 优化目标宏定义 |
| `SkSwizzlePriv.h` | 函数指针类型声明 |
| `SkOpts_SetTarget.h` | 编译器标志控制 |
| `SkSwizzler_opts.inc` | SIMD 实现代码 |
| `SkOpts_RestoreTarget.h` | 恢复编译器设置 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `SkSwizzle.cpp` | 调用函数指针 |
| `SkColorSpaceXform` | 颜色空间转换 |
| `SkRasterPipeline` | 光栅化管线 |
| 图像编解码器 | 像素格式转换 |
| GPU 后端 | 纹理数据转换 |

## 设计模式与设计决策

### 设计模式

1. **策略模式**: 函数指针实现可替换的算法
2. **单例初始化**: `Init_Swizzler()` 确保只初始化一次
3. **工厂模式**: `init()` 根据 CPU 特性选择实现
4. **门面模式**: 统一的 `SkOpts` 命名空间隐藏复杂性

### 设计决策

**1. 为何使用全局函数指针?**
- **性能**: 避免虚函数调用开销
- **简单**: 调用方无需管理对象
- **灵活**: 运行时可以改变实现(虽然通常不需要)

**2. 为何是渐进式覆盖?**
```cpp
// 默认 → SSSE3 → AVX2 (逐步覆盖到最优)
```
- 简化逻辑:不需要复杂的优先级判断
- 正确性:后续检测的总是更优
- 扩展性:易于添加新的优化层级

**3. 为何需要 maybe_unused 属性?**
```cpp
[[maybe_unused]] static bool gInitialized = init();
```
- `gInitialized` 的值未被使用,只是触发初始化
- 避免编译器警告
- C++17 标准属性

**4. 为何默认实现也编译为优化代码?**
- 在不支持高级指令集的 CPU 上仍有基础优化
- 例如,默认可能是 SSE2(对于 x86),已经比纯 C++ 快

**5. 为何不使用 C++ 多态(虚函数)?**
- 性能敏感:像素处理是热路径
- 函数调用频繁:每个像素块都调用
- 函数指针更轻量:无对象创建和管理开销

**6. 为何没有 ARM NEON 版本?**
- NEON 通常编译为基准(大部分 ARM 设备都有)
- 或者在其他文件中处理
- x86 需要多版本是因为指令集碎片化严重

## 性能考量

### 初始化开销

**一次性开销:**
- CPU 特性检测: ~100 ns (已缓存)
- 函数指针覆盖: ~10 ns 每个指针
- **总计**: ~200 ns (程序生命周期只发生一次)

**权衡:**
初始化开销微不足道,换取运行时的显著性能提升(2-8 倍)。

### 函数指针调用开销

**直接调用:**
```cpp
SkOpts::RGBA_to_BGRA(dst, src, count);
```

**开销分析:**
- 函数指针解引用: ~1-2 CPU 周期
- 间接跳转: ~5-10 周期(分支预测失败时)
- 实际函数执行: 数千周期(处理像素)

**结论:**
函数指针调用开销占总时间的 < 0.1%,完全可以忽略。

### 内联可能性

函数指针调用**不能内联**,但这不是问题:
- 实际函数体较大(SIMD 循环)
- 内联收益有限
- 调用开销相比计算可以忽略

### 代码缓存

多个版本的代码不会同时在指令缓存中:
- 运行时只使用一个版本
- 其他版本的代码不会被执行
- 对指令缓存影响最小

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkSwizzle.h` | 公共 API |
| `src/core/SkSwizzlePriv.h` | 私有函数指针声明 |
| `src/core/SkSwizzle.cpp` | 公共 API 实现 |
| `src/core/SkSwizzler_opts_ssse3.cpp` | SSSE3 优化 |
| `src/core/SkSwizzler_opts_hsw.cpp` | AVX2 优化 |
| `src/core/SkSwizzler_opts_lasx.cpp` | LoongArch 优化 |
| `src/opts/SkSwizzler_opts.inc` | 共享 SIMD 实现 |
| `src/core/SkCpu.h` | CPU 特性检测 |
| `src/core/SkOptsTargets.h` | 优化目标定义 |

## 使用示例

### 初始化

```cpp
// 在 Skia 初始化时调用(通常自动)
SkOpts::Init_Swizzler();

// 之后所有调用自动使用最优实现
uint32_t pixels[100];
SkSwapRB(pixels, pixels, 100);  // 内部调用 SkOpts::RGBA_to_BGRA
```

### 添加新优化平台

**步骤:**
1. 创建新文件:`SkSwizzler_opts_platform.cpp`
2. 定义 `Init_Swizzler_platform()` 函数
3. 在本文件中添加声明和调用逻辑:
```cpp
#elif defined(SK_CPU_NEWPLATFORM)
    void Init_Swizzler_newplatform();
    if (SkCpu::Supports(SkCpu::NEWPLATFORM_FEATURE)) {
        Init_Swizzler_newplatform();
    }
#endif
```

### 调试技巧

**查看使用的实现:**
```cpp
// 在调试器中检查函数指针地址
(gdb) p SkOpts::RGBA_to_BGRA
// 地址范围可以告诉你是哪个版本(默认/SSSE3/AVX2)
```

**强制使用特定实现(测试):**
```cpp
// 编译时定义
-DSK_ENABLE_OPTIMIZE_SIZE  // 强制默认实现

// 或编译时设置基准指令集
-DSK_CPU_SSE_LEVEL=SK_CPU_SSE_LEVEL_AVX2  // 所有代码使用 AVX2
```

## 扩展性和维护

### 添加新函数

**步骤:**
1. 在 `SkSwizzlePriv.h` 中声明函数指针
2. 在本文件中使用 `DEFINE_DEFAULT()` 定义
3. 在 `SkSwizzler_opts.inc` 中实现 SIMD 版本
4. 在平台特定文件的 `Init_*` 函数中添加初始化

### 代码共享

通过 `.inc` 文件共享实现:
- **优势**: 一份代码,多个编译版本
- **挑战**: 必须使用条件编译处理平台差异
- **最佳实践**: 使用 Skia 的抽象层(`SkVx`)

### 测试策略

**单元测试:**
- 测试每个函数的正确性
- 对比不同实现的结果(应完全一致)

**性能测试:**
- 基准测试各个实现的性能
- 验证优化确实带来提升

**集成测试:**
- 在完整的 Skia 工作流中测试
- 确保不同 CPU 上都能正常工作
