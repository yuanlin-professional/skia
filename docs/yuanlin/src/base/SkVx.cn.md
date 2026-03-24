# SkVx (skvx::Vec)

> 源文件: `src/base/SkVx.h`

## 概述

SkVx.h 定义了 `skvx::Vec<N, T>` 模板类，这是 Skia 的通用 SIMD 向量抽象库，是早期 `SkNx<N, T>` 的 v1.5 继任者。它提供了一套类型安全、跨平台的固定长度向量类型，支持算术运算、比较运算、位运算、数学函数、类型转换、混洗和交错加载等操作。

`Vec<N, T>` 的设计目标是：
- **简单可预测的内存布局**：始终等价于 `T[N]`，大小为 `N * sizeof(T)`，对齐为 `N * sizeof(T)`
- **跨翻译单元安全**：可以在头文件中自由使用，不会导致 ODR 违规
- **自动 SIMD 优化**：在 Clang/GCC 上利用编译器向量扩展自动生成 SIMD 代码，同时提供可移植的标量回退
- **平台特定特化**：在关键操作上可以插入 SSE、AVX、NEON、WASM SIMD 等平台专用 intrinsics

**与 SkRasterPipeline_opts.h 中 Vec 的区别**：`skvx::Vec` 是结构体，有固定的内存布局（可放入类成员），但不能通过寄存器传递。SkRasterPipeline_opts.h 的 `Vec` 是编译器原生向量类型，可以通过寄存器传递但不适合存储在结构体中。

该文件约 1191 行。

## 架构位置

```
应用层 / Skia 核心代码
    │
    ├── skvx::Vec<N,T>    ← 本文件（通用 SIMD 抽象）
    │   ├── 颜色处理 (RGBA 像素操作)
    │   ├── 几何计算 (点/向量运算)
    │   ├── 半精度浮点转换 (to_half/from_half)
    │   └── 图像处理 (采样、混合)
    │
    ▼
平台 SIMD 后端
    ├── SSE/SSE4.1/AVX/AVX2 (x86)
    ├── NEON (ARM)
    ├── WASM SIMD128 (WebAssembly)
    └── LSX/LASX (LoongArch)
```

`skvx::Vec` 被 Skia 各个子系统广泛使用，包括颜色空间转换、路径几何计算、图像采样、字体渲染等。它是 Skia 内部最基础的数值计算原语之一。

## 主要类与结构体

### Vec<N, T> (通用版本，N > 4)
```cpp
template <int N, typename T>
struct alignas(N*sizeof(T)) Vec {
    Vec<N/2, T> lo, hi;  // 递归二分结构

    Vec() = default;
    Vec(T s);                         // 广播标量到所有通道
    Vec(std::initializer_list<T> xs); // 初始化列表（未指定通道填零）

    T  operator[](int i) const;  // 只读索引
    T& operator[](int i);        // 可写索引

    static Vec Load(const void* ptr);   // 从内存加载
    void store(void* ptr) const;        // 存储到内存
};
```

N 必须是 2 的幂。向量通过递归二分的 `lo`/`hi` 子向量实现，直到基本情况 `Vec<1, T>`。

### Vec<4, T> (4 元素特化)
```cpp
template <typename T>
struct alignas(4*sizeof(T)) Vec<4,T> {
    Vec<2,T> lo, hi;

    // 多种构造函数
    Vec(T x, T y, T z, T w);
    Vec(Vec<2,T> xy, Vec<2,T> zw);
    Vec(Vec<2,T> xy, T z, T w);

    // 具名访问器
    T& x(); T& y(); T& z(); T& w();
    Vec<2,T>& xy(); Vec<2,T>& zw();

    // 混洗操作
    Vec<4,T> yxwz() const;  // shuffle<1,0,3,2>
    Vec<4,T> zwxy() const;  // shuffle<2,3,0,1>
};
```

### Vec<2, T> (2 元素特化)
```cpp
template <typename T>
struct alignas(2*sizeof(T)) Vec<2,T> {
    Vec<1,T> lo, hi;

    Vec(T x, T y);
    T& x(); T& y();
    Vec<2,T> yx() const;        // shuffle<1,0>
    Vec<4,T> xyxy() const;      // 复制扩展
};
```

### Vec<1, T> (标量基本情况)
```cpp
template <typename T>
struct Vec<1,T> {
    T val = {};

    Vec() = default;
    Vec(T s);
    T  operator[](int i) const;
    T& operator[](int i);
};
```

### Mask<T> 类型映射
```cpp
template <typename T> struct Mask { using type = T; };
template <> struct Mask<float>  { using type = int32_t; };
template <> struct Mask<double> { using type = int64_t; };
template <typename T> using M = typename Mask<T>::type;
```
比较运算返回 `Vec<N, M<T>>` 类型，其中浮点类型的比较结果为对应大小的整数类型（全 0 或全 1 位模式）。

### ScaledDividerU32
```cpp
class ScaledDividerU32 {
    uint32_t fDivisorFactor;  // (1/divisor) * 2^32
    uint32_t fHalf;           // (divisor+1) / 2
public:
    Vec<4, uint32_t> divide(const Vec<4, uint32_t>& numerator) const;
};
```
用于高效整数除法的辅助类，通过预计算的乘法因子将除法转换为乘法和位移，精度在 +/- 1 以内。

## 公共 API 函数

### 算术运算符
全部支持 Vec-Vec 和 Vec-Scalar（双向）运算：
| 运算符 | 说明 |
|--------|------|
| `+`, `-`, `*`, `/` | 四则运算 |
| `^`, `&`, `\|` | 位运算 |
| `!`, `-`(一元), `~` | 逻辑非、取反、位取反 |
| `<<`, `>>` | 位移（右操作数为标量 int） |
| `+=`, `-=`, `*=`, `/=`, `^=`, `&=`, `\|=`, `<<=`, `>>=` | 复合赋值 |

### 比较运算符
返回 `Vec<N, M<T>>` 掩码（全 0 = false，全 1 = true）：
| 运算符 | 说明 |
|--------|------|
| `==`, `!=`, `<`, `>`, `<=`, `>=` | 逐通道比较 |

### 条件选择
| 函数 | 说明 |
|------|------|
| `if_then_else(cond, t, e)` | 根据掩码逐通道选择 t 或 e |
| `naive_if_then_else(cond, t, e)` | 纯位运算版本，编译器更易优化 |

`if_then_else` 在 SSE4.1 上使用 `_mm_blendv_epi8`，在 AVX2 上使用 `_mm256_blendv_epi8`，在 NEON 上使用 `vbslq_u8`，提供平台最优实现。

### 聚合函数
| 函数 | 说明 |
|------|------|
| `any(x)` | 是否有任何通道非零 |
| `all(x)` | 是否所有通道非零 |
| `min(x)` / `max(x)` | 跨通道求最小/最大值 |

`any()` 在 SSE4.1 上使用 `_mm_testz_si128`，在 NEON aarch64 上使用 `vmaxvq_u8`，这些是低延迟的 SIMD 测试指令。

### 数学函数
| 函数 | 说明 |
|------|------|
| `min(x, y)` / `max(x, y)` | 逐通道最小/最大值 |
| `pin(x, lo, hi)` | 逐通道 clamp |
| `ceil(x)` / `floor(x)` / `trunc(x)` / `round(x)` | 取整 |
| `sqrt(x)` / `abs(x)` | 平方根 / 绝对值 |
| `fma(x, y, z)` | 融合乘加 (x*y + z) |
| `lrint(x)` | 浮点到最近整数（使用 SIMD `cvtps_epi32`） |
| `fract(x)` | 小数部分 (x - floor(x)) |
| `dot(a, b)` | 点积 |
| `cross(a, b)` | 2D 叉积 |
| `length(v)` | 向量长度 |
| `normalize(v)` | 单位化 |
| `isfinite(v)` | 检查所有元素是否有限 |

### 类型转换
| 函数 | 说明 |
|------|------|
| `cast<D>(src)` | 逐通道类型转换（如 float→int） |
| `to_half(x)` | float→half (uint16_t) 转换，支持去规格化 |
| `from_half(x)` | half→float 转换，保留 NaN 和无穷 |

`to_half` 和 `from_half` 在 ARM64 上使用硬件指令 `vcvt_f16_f32` / `vcvt_f32_f16`，其他平台使用精心优化的软件实现，与 skcms 库保持位精确一致。

### 混洗与重排
| 函数 | 说明 |
|------|------|
| `shuffle<Ix...>(x)` | 按索引重新排列通道 |
| `join(lo, hi)` | 连接两个 Vec<N> 为 Vec<2N> |

```cpp
// 示例
Vec<4,float> rgba = {R,G,B,A};
shuffle<2,1,0,3>(rgba);  // → {B,G,R,A}
shuffle<3,3,3,3>(rgba);  // → {A,A,A,A}
shuffle<2,1>(rgba);       // → {B,G}     （缩短）
```

在 Clang 上使用 `__builtin_shufflevector` 编译为单条 SIMD 混洗指令。

### 像素操作
| 函数 | 说明 |
|------|------|
| `div255(x)` | 精确的除以 255（`(x+127)/255`） |
| `approx_scale(x, y)` | 近似的 `div255(x*y)`，在 x/y=0/255 时精确 |
| `saturated_add(x, y)` | 饱和加法（上溢时 clamp 到最大值） |
| `mull(x, y)` | 扩展乘法（u8*u8→u16, u16*u16→u32） |
| `mulhi(x, y)` | 高位乘法（u16*u16 的高 16 位） |

### 交错加载/存储
| 函数 | 说明 |
|------|------|
| `strided_load4(ptr, a, b, c, d)` | 4 路解交错加载（如 RGBA→R, G, B, A） |
| `strided_load2(ptr, a, b)` | 2 路解交错加载 |

在 NEON 上使用 `vld4_u32` / `vld2_u16` 等硬件交错加载指令。在 SSE 上使用 `_MM_TRANSPOSE4_PS` 转置实现。

### map 函数
```cpp
template <typename Fn, int N, typename T, typename... Rest>
auto map(Fn&& fn, const Vec<N,T>& first, const Rest&... rest);
```
对向量的每个通道应用标量函数。`ceil`、`floor`、`sqrt` 等数学函数通过 `map` 在标量函数上构建。

## 内部实现细节

### 三种实现策略
1. **编译器向量扩展**（Clang/GCC + SIMD 可用）：将 `Vec<N,T>` 转换为 `VExt<N,T>`（即 `__attribute__((ext_vector_type(N)))`），利用编译器自动生成 SIMD 指令
2. **map 函数**：通过 `std::index_sequence` 展开将标量函数应用到每个通道
3. **递归 lo/hi 分解**：将 `Vec<N>` 操作分解为两个 `Vec<N/2>` 操作，递归到 `Vec<1>` 标量实现

策略 1 用于所有基本运算符（加减乘除、位运算、比较）。策略 2 用于数学函数。策略 3 用于特殊操作（如 `if_then_else`、`any`、`all`）的默认实现。

### 平台特化插入点
通过 `if constexpr` 检查 `N*sizeof(T)` 的大小来匹配 SIMD 寄存器宽度：
```cpp
SINT Vec<N,T> if_then_else(const Vec<N,M<T>>& cond, ...) {
    if constexpr (N*sizeof(T) == 32) {
        return _mm256_blendv_epi8(...);  // AVX2: 256-bit
    }
    if constexpr (N*sizeof(T) == 16) {
        return _mm_blendv_epi8(...);     // SSE4.1: 128-bit
    }
    // 递归回退
    return join(if_then_else(cond.lo, t.lo, e.lo),
                if_then_else(cond.hi, t.hi, e.hi));
}
```

### VExt 与 Vec 的转换
```cpp
SINT VExt<N,T> to_vext(const Vec<N,T>& v) { return sk_bit_cast<VExt<N,T>>(v); }
SINT Vec<N,T>  to_vec(const VExt<N,T>& v) { return sk_bit_cast<Vec<N,T>>(v); }
```
由于 `Vec<N,T>` 和 `VExt<N,T>` 具有相同的大小和对齐，可以通过 `sk_bit_cast` 零开销转换。

## 依赖关系

- `include/private/base/SkFeatures.h` — CPU 特性检测宏
- `src/base/SkUtils.h` — `sk_unaligned_load`, `sk_bit_cast` 等工具
- 平台 SIMD 头文件：`immintrin.h`（SSE/AVX）、`arm_neon.h`（NEON）、`wasm_simd128.h`（WASM）、`lsxintrin.h`/`lasxintrin.h`（LoongArch）

## 设计模式与设计决策

### 递归二分
向量通过 `lo`/`hi` 递归二分直到标量。这使得任意长度的操作可以自动分解为平台最优的 SIMD 宽度，无需手动编写每种组合。

### ODR 安全设计
所有独立函数声明为 `static inline`（通过 `SI` 宏），所有成员函数标记 `__attribute__((always_inline))`（通过 `SKVX_ALWAYS_INLINE` 宏），确保不同翻译单元中相同函数的实例不会冲突。

### 广播构造语义
`Vec(T s)` 广播标量到所有通道，`Vec{x}` 初始化列表只设置第一个元素（其余为零）。这两种构造语义的区分对颜色操作很有用。

### 隐式标量提升
通过 SFINAE 模板（`SINTU`），任何可转换为 `T` 的标量 `U` 都可以参与 Vec 运算（先广播为 Vec 再运算），使得 `vec + 1.0f` 等表达式自然可用。

## 性能考量

1. **零开销抽象**：在 Clang/GCC 上，`Vec<4,float>` 的加法编译为单条 `addps` 指令
2. **强制内联**：`SKVX_ALWAYS_INLINE` 确保所有方法内联，消除函数调用开销
3. **`naive_if_then_else` 优化**：Clang 的优化器对纯位运算形式的推理能力更强，可以在 `min`/`max` 中消除整个条件选择
4. **NEON 交错加载**：`strided_load4` 在 NEON 上编译为单条 `vld4` 指令，完成 4 路解交错
5. **半精度转换**：`to_half`/`from_half` 在 ARM64 上使用硬件 F16 转换指令，零额外开销
6. **饱和加法**：在 SSE/NEON 上使用 `_mm_adds_epu8`/`vqaddq_u8` 硬件饱和指令
7. **`any()` 的低延迟实现**：SSE4.1 使用 `_mm_testz_si128`（2 cycle），而非 `movemask` + 比较
8. **`lrint` 优化**：在 SSE/AVX 上使用 `_mm_cvtps_epi32` 硬件舍入，比逐标量 `lrintf` 快数倍

## 相关文件

- `/Users/yuanlin/workspace/skia/src/base/SkVx.h` — 本文件
- `/Users/yuanlin/workspace/skia/src/base/SkUtils.h` — 未对齐内存操作和位转换工具
- `/Users/yuanlin/workspace/skia/include/private/base/SkFeatures.h` — CPU 特性检测
- `/Users/yuanlin/workspace/skia/src/opts/SkRasterPipeline_opts.h` — 管线阶段中的替代 Vec 实现
- `/Users/yuanlin/workspace/skia/include/core/SkColor.h` — 使用 skvx 进行颜色运算
- `/Users/yuanlin/workspace/skia/include/core/SkM44.h` — 使用 skvx 进行矩阵运算
