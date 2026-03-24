# skcms_internals - skcms 内部工具与配置

> 源文件: `modules/skcms/src/skcms_internals.h`

## 概述

skcms_internals.h 是 skcms 颜色管理库的内部头文件，提供跨平台的辅助宏定义、编译器特性检测、ICC 配置文件标签访问接口、可移植数学函数以及 SIMD 指令集的启用/禁用控制。该文件是 skcms 内部实现和测试工具共享的基础设施层。

## 架构位置

该文件位于 skcms 库的最底层工具层，被 skcms_Transform.h、Transform_inl.h 以及 skcms 的测试代码所依赖。它定义的宏和函数影响整个 skcms 库的编译行为和运行时特性。

## 主要类与结构体

### `skcms_ICCTag`（结构体）
ICC 配置文件标签数据结构：
- `signature`: 4 字节标签签名
- `type`: 标签类型
- `size`: 数据大小
- `buf`: 指向标签数据的指针

### 类型前向声明
- `skcms_ICCProfile` - ICC 配置文件
- `skcms_TransferFunction` - 传输函数
- `skcms_Curve` - 曲线（联合类型）

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `skcms_GetTagByIndex(profile, idx, tag)` | 按索引获取 ICC 标签 |
| `skcms_GetTagBySignature(profile, sig, tag)` | 按签名获取 ICC 标签 |
| `skcms_MaxRoundtripError(curve, inv_tf)` | 计算曲线与逆传输函数之间的最大往返误差 |
| `floorf_(float)` | 可移植的向下取整函数 |
| `fabsf_(float)` | 可移植的绝对值函数 |
| `powf_(float, float)` | 可移植的幂函数 |

## 内部实现细节

### 编译器特性宏

#### `SKCMS_FALLTHROUGH`
C++ `[[fallthrough]]` 属性的跨编译器封装，支持 Clang 和 GCC 的不同属性语法。

#### `SKCMS_HAS_MUSTTAIL`
控制是否使用 `[[clang::musttail]]` 尾调用优化。默认禁用的平台包括：
- 启用了 ASan/MSan 的构建（会破坏指针）
- WebAssembly（尾调用支持有限）
- ARMv7/Android（ICE 崩溃）
- RISC-V（编译器 bug）
- PowerPC 和 LoongArch
- Windows（生成错误代码）

#### `SKCMS_MAYBE_UNUSED`
跨编译器的 `unused` 属性封装（Clang/GCC/MSVC）。

### 安全的大小计算宏

| 宏 | 说明 |
|----|------|
| `SAFE_SIZEOF(x)` | 将 `sizeof` 结果强制为 `uint64_t`，确保 32/64 位平台行为一致 |
| `SAFE_FIXED_SIZE(type)` | 安全计算含变长数组结构体的固定部分大小 |
| `ARRAY_COUNT(arr)` | 数组元素计数 |

### 可移植模式（`SKCMS_PORTABLE`）
当编译器不是 Clang、GCC 或支持 SIMD 的 Emscripten 时，自动启用可移植模式，禁用所有 SIMD 优化。

### HSW/SKX 指令集控制
在可移植模式、非 x86-64 平台或 Android 上自动禁用 HSW（AVX2）和 SKX（AVX-512）指令集。提供 `SKCMS_DISABLE_HSW` 和 `SKCMS_DISABLE_SKX` 宏。

### 可移植数学函数
- `floorf_`: 通过整数截断实现向下取整，处理负数修正
- `fabsf_`: 简单的条件取反实现
- `powf_`: 声明但未在此文件中定义（实现在 .c 文件中）

### 测试用随机字节数组
`skcms_252_random_bytes[252]`: 252 个随机字节的固定数组，252 可被 3 和 4 整除，用于 ICC 配置文件等价性测试。

## 依赖关系

- **stdbool.h / stdint.h**: C 标准整数和布尔类型
- **skcms_public.h**: ICC 配置文件和传输函数的类型定义（间接依赖）

## 设计模式与设计决策

1. **C 兼容性**: 使用 `extern "C"` 包装确保 C/C++ 双向兼容，skcms 的核心接口保持 C ABI。
2. **保守的尾调用策略**: 大量注释记录了 `[[clang::musttail]]` 在各平台的已知问题，采用白名单策略而非盲目启用，体现了对可靠性的重视。
3. **安全的大小操作**: 强制使用 `uint64_t` 的 `SAFE_SIZEOF` 避免 32 位平台上的溢出，这是因为 skcms 在 64 位测试更充分。
4. **渐进式 SIMD 降级**: 从 AVX-512 -> AVX2 -> SSE/NEON -> 标量，自动根据平台能力选择最优路径。

## 性能考量

- **尾调用优化**: `SKCMS_HAS_MUSTTAIL` 在支持的平台上可显著提升转换管线性能，但为了正确性在多个平台禁用
- **SIMD 指令集选择**: 编译时决定可用指令集，避免运行时分支开销
- **可移植数学函数**: `floorf_` 等实现避免了 libc 调用的开销，适合内联

## 相关文件

- `modules/skcms/src/skcms_Transform.h` - 操作枚举和向量类型
- `modules/skcms/src/Transform_inl.h` - 操作的 SIMD 实现
- `modules/skcms/src/skcms_public.h` - 公共 API 和类型定义

## 使用注意事项

1. 该头文件仅供 skcms 内部和测试工具使用，外部代码不应包含
2. `SKCMS_HAS_MUSTTAIL` 的设置影响整个转换管线的执行模式
3. 使用 `SAFE_SIZEOF` 代替 `sizeof` 以确保 32/64 位行为一致
4. `SKCMS_PORTABLE` 模式会禁用所有 SIMD 优化，显著降低性能
5. `floorf_` 和 `fabsf_` 不处理特殊浮点值（NaN、Inf）的边界情况
6. `skcms_252_random_bytes` 是固定的，不应在安全敏感场景中使用
7. `SKCMS_FALLTHROUGH` 应在 switch-case 的穿透处使用以避免编译器警告

### 平台兼容性矩阵

| 平台 | SIMD | HSW | SKX | musttail |
|------|------|-----|-----|----------|
| x86-64 Linux (Clang) | SSE | 可用 | 可用 | 可用 |
| x86-64 Linux (GCC) | SSE | 可用 | 可用 | 依赖版本 |
| x86-64 Windows | SSE | 可用 | 可用 | 禁用 |
| x86-64 Android | SSE | 禁用 | 禁用 | 依赖配置 |
| ARM64 | NEON | 禁用 | 禁用 | 可用 |
| ARMv7 | NEON | 禁用 | 禁用 | 禁用 |
| WASM | 可选 | 禁用 | 禁用 | 禁用 |
| RISC-V | 标量 | 禁用 | 禁用 | 禁用 |
| LoongArch | LSX | 禁用 | 禁用 | 禁用 |

### SKCMS_HAS_MUSTTAIL 决策树
```
Clang?
  ├── 是 -> 检查 sanitizer/平台排除列表
  │         ├── 通过 -> SKCMS_HAS_MUSTTAIL = 1
  │         └── 排除 -> SKCMS_HAS_MUSTTAIL = 0
  └── 否 -> GCC?
            ├── 是 -> 检查 RISC-V 排除
            │         ├── 非 RISC-V 且有 musttail -> 1
            │         └── 其他 -> 0
            └── 否 -> 检查 __has_cpp_attribute
                      ├── 有 -> 1
                      └── 无 -> 0
默认值: 0
```

### powf_ 说明
`powf_(float, float)` 在此头文件中仅声明，实际实现在 skcms.cc 中。它提供了一个不依赖 libm 的幂函数实现，用于 ICC 配置文件的传输函数拟合。

### skcms_ICCTag 使用场景
ICC 标签结构体主要用于：
- 按签名查找特定标签（如 'rTRC' 表示红色传输响应曲线）
- 按索引遍历配置文件中的所有标签
- `buf` 指针直接指向原始配置文件缓冲区中的数据，无需复制
- 标签数据的生命周期由外部配置文件缓冲区管理
