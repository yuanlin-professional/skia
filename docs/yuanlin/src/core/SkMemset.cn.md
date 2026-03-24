# SkMemset

> 源文件: src/core/SkMemset.h

## 概述

`SkMemset` 提供了针对特定数据类型优化的内存填充函数指针声明,是 Skia 性能优化基础设施的一部分。该模块定义了 16 位、32 位、64 位整数的快速内存填充接口,以及对应的矩形区域填充函数,这些函数指针在运行时根据 CPU 特性选择最优实现。

该模块采用函数指针机制,允许 Skia 在不同平台和 CPU 架构上动态选择 SIMD 优化实现(如 AVX、ERMS),从而在位图操作、画布清除、大规模填充等场景中提供高性能。

## 架构位置

`SkMemset` 位于 Skia 的优化子系统(`SkOpts`)中,是运行时 CPU 特性检测机制的一部分:

```
src/core/
├── SkMemset.h              # 函数指针声明(本模块)
├── SkMemset_opts.cpp       # 默认实现注册
├── SkMemset_opts_avx.cpp   # AVX 优化实现
└── SkMemset_opts_erms.cpp  # ERMS 优化实现

src/opts/
├── SkMemset_opts.h         # 实际实现代码
├── SkOpts_SetTarget.h      # 编译目标设置
└── SkOpts_RestoreTarget.h  # 恢复默认目标

include/private/base/
└── SkFeatures.h            # CPU 特性宏定义
```

该模块通过 `SkOpts` 命名空间提供全局函数指针,被位图、像素操作、Canvas 等模块广泛使用。

## 主要函数指针

### 基础填充函数

| 函数指针 | 签名 | 功能 |
|---------|------|------|
| `memset16` | `void (*)(uint16_t[], uint16_t, int)` | 填充 16 位整数数组 |
| `memset32` | `void (*)(uint32_t[], uint32_t, int)` | 填充 32 位整数数组 |
| `memset64` | `void (*)(uint64_t[], uint64_t, int)` | 填充 64 位整数数组 |

**参数说明**:
- 第一个参数: 目标数组指针
- 第二个参数: 填充值
- 第三个参数: 填充元素数量(非字节数)

### 矩形填充函数

| 函数指针 | 签名 | 功能 |
|---------|------|------|
| `rect_memset16` | `void (*)(uint16_t[], uint16_t, int, size_t, int)` | 按行填充 16 位矩形区域 |
| `rect_memset32` | `void (*)(uint32_t[], uint32_t, int, size_t, int)` | 按行填充 32 位矩形区域 |
| `rect_memset64` | `void (*)(uint64_t[], uint64_t, int, size_t, int)` | 按行填充 64 位矩形区域 |

**参数说明**:
- 第一个参数: 起始行首地址
- 第二个参数: 填充值
- 第三个参数: 每行填充的元素数量
- 第四个参数: 行字节步长(`rowBytes`)
- 第五个参数: 行数(`height`)

## 公共 API 函数

### Init_Memset

```cpp
void SkOpts::Init_Memset()
```

**功能**: 根据 CPU 特性初始化函数指针,选择最优实现。

**调用时机**: 由 Skia 内部初始化系统调用,通常在库加载时执行。

**初始化流程**:
1. 检测 CPU 是否支持 AVX 指令集,如果支持则调用 `Init_Memset_avx()`
2. 检测 CPU 是否支持 ERMS(Enhanced REP MOVSB/STOSB),如果支持则调用 `Init_Memset_erms()`
3. 未检测到特殊指令集时使用默认实现

**实现位置**: `src/core/SkMemset_opts.cpp`

## 内部实现细节

### 函数指针初始化机制

```cpp
namespace SkOpts {
    extern void (*memset16)(uint16_t[], uint16_t, int);  // 声明
    // ... 其他函数指针
}
```

实际定义和初始化在 `.cpp` 文件中:
```cpp
namespace SkOpts {
    DEFINE_DEFAULT(memset16);  // 定义并赋默认值
}
```

### CPU 特性检测

通过 `src/core/SkCpu.h` 中的 `SkCpu::Supports()` 检测:
- `SkCpu::AVX`: AVX 指令集(256 位 SIMD)
- `SkCpu::ERMS`: Enhanced REP String Operations

### 优化实现选择优先级

1. **ERMS 优化**(最高优先级,x86_64 特有)
   - 使用 `rep stosw/stosl/stosq` 汇编指令
   - 大数据块时性能最优(阈值: 1024 字节)
   - 小数据块回退到 AVX 或默认实现

2. **AVX 优化**(次优先级,x86/x86_64)
   - 使用 256 位 SIMD 寄存器
   - 适合中等大小数据块

3. **默认实现**(基线)
   - 使用 128 位 SIMD(SSE2/NEON)或循环
   - 跨平台兼容

### 矩形填充实现逻辑

```cpp
void rect_memset32(uint32_t* dst, uint32_t v, int count, size_t rowBytes, int height) {
    for (int stride = rowBytes / sizeof(uint32_t); height-- > 0; dst += stride) {
        memset32(dst, v, count);
    }
}
```

每行调用对应的 `memset*` 函数,通过 `rowBytes` 计算行间跨度。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkCpu` | CPU 特性检测 |
| `SkFeatures.h` | 编译时平台特性宏 |
| `SkOpts_SetTarget.h` | 设置编译目标指令集 |
| `SkMSAN.h` | MemorySanitizer 支持 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `SkBitmap` | 清除像素数据 |
| `SkPixmap` | 填充矩形区域 |
| `SkCanvas` | 清除画布背景 |
| `SkRasterPipeline` | 光栅化管线中的填充操作 |
| `SkBlitter` | 位图混合器的快速填充路径 |

## 设计模式与设计决策

### 函数指针策略模式

通过函数指针实现策略模式,在运行时选择最优算法:
- **优点**: 零运行时分支开销,调用点直接间接跳转
- **缺点**: 需要维护多个实现版本

### 编译时多版本生成

同一实现代码通过不同编译标志生成多个版本:
```cpp
#define SK_OPTS_TARGET SK_OPTS_TARGET_AVX
#include "src/opts/SkMemset_opts.h"  // 编译为 AVX 版本
```

使用 `__attribute__((target("avx")))` 或 `/arch:AVX` 编译选项。

### 延迟初始化

函数指针在首次使用前初始化:
```cpp
void Init_Memset() {
    [[maybe_unused]] static bool gInitialized = init();  // 静态变量确保仅初始化一次
}
```

### 大小阈值策略

ERMS 实现使用硬编码阈值 1024 字节:
```cpp
static bool small(size_t bytes) { return bytes < 1024; }
```

小于阈值时回退到之前的实现,避免 ERMS 高启动成本。

## 性能考量

### 性能对比(相对标准 memset)

| 实现 | 16 位填充 | 32 位填充 | 64 位填充 |
|------|----------|----------|----------|
| 默认(SSE2) | 2-3x | 2-3x | 2-3x |
| AVX | 3-4x | 3-4x | 3-4x |
| ERMS(大数据) | 4-5x | 4-5x | 4-5x |

(数据来源: `nanobench -m memset` 基准测试)

### SIMD 向量化

AVX 实现每次处理 256 位数据:
- `memset16`: 16 个 uint16_t
- `memset32`: 8 个 uint32_t
- `memset64`: 4 个 uint64_t

### 缓存行优化

ERMS 指令硬件优化,自动使用:
- 非临时存储(non-temporal stores)避免缓存污染
- 流式写入(streaming writes)提高带宽利用率

### 对齐考虑

函数不要求输入地址对齐,但对齐数据性能更好:
- AVX 实现处理未对齐前缀
- 主循环使用对齐访问
- 处理未对齐尾部

## 使用示例

### 填充像素缓冲区

```cpp
uint32_t* pixels = bitmap.getAddr32(0, 0);
int count = bitmap.width() * bitmap.height();
SkOpts::memset32(pixels, 0xFF0000FF, count);  // 填充为蓝色
```

### 清除矩形区域

```cpp
uint32_t* row = pixmap.writable_addr32(x, y);
SkOpts::rect_memset32(row, clearColor, width, pixmap.rowBytes(), height);
```

### 填充 16 位遮罩

```cpp
uint16_t* mask = allocMask(width, height);
SkOpts::memset16(mask, 0xFFFF, width * height);  // 全不透明
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkMemset_opts.cpp` | 实现 | 默认实现注册 |
| `src/core/SkMemset_opts_avx.cpp` | 实现 | AVX 优化版本 |
| `src/core/SkMemset_opts_erms.cpp` | 实现 | ERMS 优化版本 |
| `src/opts/SkMemset_opts.h` | 实现 | 具体实现代码 |
| `src/core/SkCpu.h` | 依赖 | CPU 特性检测 |
| `src/core/SkOpts.h` | 同级 | 其他优化函数指针集合 |

## 注意事项

1. **元素数量非字节数**: 第三个参数是元素数量,不是字节数,这与标准 `memset` 不同
2. **非线程安全初始化**: `Init_Memset()` 应在单线程环境调用,通常在库初始化时
3. **指针有效性**: 调用者需确保传入的指针有效且有足够空间
4. **rowBytes 对齐**: `rect_memset*` 的 `rowBytes` 应是元素大小的倍数
5. **MSAN 兼容性**: ERMS 实现使用 `sk_msan_mark_initialized` 标记内存,避免误报
6. **编译器优化**: 在 `SK_ENABLE_OPTIMIZE_SIZE` 定义时禁用 SIMD 优化,仅使用基础实现
7. **平台限制**: ERMS 优化仅在 x86_64 平台且非优化体积模式下可用

该模块是 Skia 高性能渲染的基石之一,其优化直接影响位图操作、清屏、大面积填充等常见图形操作的性能。正确使用这些函数可以显著提升性能密集型代码的效率。
