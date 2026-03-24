# SkSL Generated - 预编译的 SkSL 内置模块

## 概述

`src/sksl/generated` 目录存放由 Skia 构建系统自动生成的 SkSL 内置模块代码。这些文件包含了 SkSL 语言的标准库函数声明、GPU 特有的内置函数、混合模式实现以及 Graphite 渲染引擎的片段和顶点着色器基础设施。每个模块以 C++ 字符串常量的形式存储，在编译器初始化时被加载并解析为内置符号表。

该目录的内容不是手工编写的，而是从 `src/sksl/sksl_*.sksl` 源文件自动生成的。每个源模块会生成两个版本：`.minified.sksl`（压缩版，用于生产构建）和 `.unoptimized.sksl`（未优化版，保留格式便于调试）。压缩版通过去除空白、缩短标识符等方式减小体积，在生产构建中减少二进制文件大小和编译器初始化时间。

这些内置模块定义了 SkSL 的核心能力：从基本数学函数（`sin`、`cos`、`sqrt`）到 GPU 采样操作（`sample`、`sampleLod`）、从混合模式实现（Porter-Duff、色彩混合等）到 Graphite 引擎的着色器基础设施（颜色空间转换、裁剪、纹理采样等）。它们是 SkSL 编译器能够识别和处理内置函数的基础。

生成的模块以 `static constexpr char[]` 数组的形式嵌入到 C++ 编译单元中，避免了运行时文件 I/O。编译器在初始化阶段解析这些字符串，构建内置类型和函数的符号表，使用户编写的 SkSL 程序可以直接调用这些内置功能。

## 架构图

```
源文件 (src/sksl/)                生成文件 (src/sksl/generated/)
+-------------------+            +--------------------------------+
| sksl_shared.sksl  | ---------> | sksl_shared.minified.sksl      |
|                   |            | sksl_shared.unoptimized.sksl   |
+-------------------+            +--------------------------------+
| sksl_gpu.sksl     | ---------> | sksl_gpu.minified.sksl         |
|                   |            | sksl_gpu.unoptimized.sksl      |
+-------------------+            +--------------------------------+
| sksl_public.sksl  | ---------> | sksl_public.minified.sksl      |
|                   |            | sksl_public.unoptimized.sksl   |
+-------------------+            +--------------------------------+
| sksl_frag.sksl    | ---------> | sksl_frag.minified.sksl        |
|                   |            | sksl_frag.unoptimized.sksl     |
+-------------------+            +--------------------------------+
| sksl_vert.sksl    | ---------> | sksl_vert.minified.sksl        |
|                   |            | sksl_vert.unoptimized.sksl     |
+-------------------+            +--------------------------------+
| sksl_compute.sksl | ---------> | sksl_compute.minified.sksl     |
|                   |            | sksl_compute.unoptimized.sksl  |
+-------------------+            +--------------------------------+
| sksl_rt_shader    | ---------> | sksl_rt_shader.minified.sksl   |
| .sksl             |            | sksl_rt_shader.unoptimized.sksl|
+-------------------+            +--------------------------------+
| sksl_graphite_    | ---------> | sksl_graphite_frag.minified.sksl|
| frag.sksl         |            | sksl_graphite_frag.unoptimized |
+-------------------+            +--------------------------------+
| sksl_graphite_    | ---------> | sksl_graphite_vert.minified.sksl|
| vert.sksl         |            | sksl_graphite_vert.unoptimized |
+-------------------+            +--------------------------------+

加载过程:
static constexpr char SKSL_MINIFIED_sksl_shared[] = "...";
                |
                v
        SkSL 编译器初始化
                |
                v
        解析为内置符号表
                |
                v
        用户 SkSL 程序可调用内置函数
```

## 目录结构

```
src/sksl/generated/
|
|-- sksl_shared.minified.sksl          # 共享内置函数（压缩版，~12.7KB）
|-- sksl_shared.unoptimized.sksl       # 共享内置函数（完整版，~15.1KB）
|
|-- sksl_gpu.minified.sksl             # GPU 专用函数和混合模式（压缩版，~6.6KB）
|-- sksl_gpu.unoptimized.sksl          # GPU 专用函数和混合模式（完整版，~8.5KB）
|
|-- sksl_public.minified.sksl          # 公共 API 函数（压缩版，~219B）
|-- sksl_public.unoptimized.sksl       # 公共 API 函数（完整版，~258B）
|
|-- sksl_frag.minified.sksl            # 片段着色器专用函数（压缩版，~414B）
|-- sksl_frag.unoptimized.sksl         # 片段着色器专用函数（完整版，~414B）
|
|-- sksl_vert.minified.sksl            # 顶点着色器专用函数（压缩版，~227B）
|-- sksl_vert.unoptimized.sksl         # 顶点着色器专用函数（完整版，~227B）
|
|-- sksl_compute.minified.sksl         # 计算着色器专用函数（压缩版，~581B）
|-- sksl_compute.unoptimized.sksl      # 计算着色器专用函数（完整版，~603B）
|
|-- sksl_rt_shader.minified.sksl       # 运行时着色器函数（压缩版，~3.6KB）
|-- sksl_rt_shader.unoptimized.sksl    # 运行时着色器函数（完整版，~6.1KB）
|
|-- sksl_graphite_frag.minified.sksl   # Graphite 片段着色器（压缩版，~20.9KB）
|-- sksl_graphite_frag.unoptimized.sksl # Graphite 片段着色器（完整版，~39.4KB，最大文件）
|
|-- sksl_graphite_vert.minified.sksl   # Graphite 顶点着色器（压缩版，~10.3KB）
|-- sksl_graphite_vert.unoptimized.sksl # Graphite 顶点着色器（完整版，~20.4KB）
```

## 关键类与函数

### sksl_shared - 共享数学内置函数

这是最基础的内置模块，包含所有着色器类型共享的标准数学函数。存储为 C++ 字符串常量：

```cpp
static constexpr char SKSL_MINIFIED_sksl_shared[] = "...";
```

主要函数类别：

**三角函数**:
- `radians()`, `degrees()` - 角度/弧度转换
- `sin()`, `cos()`, `tan()` - 基本三角函数
- `asin()`, `acos()`, `atan()` - 反三角函数
- `sinh()`, `cosh()`, `tanh()` (ES3) - 双曲函数
- `asinh()`, `acosh()`, `atanh()` (ES3) - 反双曲函数

**指数函数**:
- `pow()`, `exp()`, `log()`, `exp2()`, `log2()`, `sqrt()`, `inversesqrt()`

**常用数学函数**:
- `abs()`, `sign()`, `floor()`, `ceil()`, `fract()`
- `mod()`, `min()`, `max()`, `clamp()`, `saturate()`
- `mix()`, `step()`, `smoothstep()`

**ES3 扩展函数**:
- `trunc()`, `round()`, `roundEven()`
- `floatBitsToInt()`, `floatBitsToUint()`, `intBitsToFloat()`, `uintBitsToFloat()`

所有函数都支持 `$genType`（float 泛型）和 `$genHType`（half 精度泛型）两种参数类型，并使用 `$pure` 注解标记为纯函数（无副作用，可被编译器优化）。

### sksl_gpu - GPU 特有函数和混合模式

该模块包含仅在 GPU 着色器中可用的函数：

**高级数学函数**:
- `fma()` - 融合乘加
- `frexp()`, `ldexp()` - 浮点分解/组装
- `bitCount()`, `findLSB()`, `findMSB()` - 位操作函数
- `packSnorm2x16()`, `packUnorm4x8()`, `unpackHalf2x16()` 等 - 打包/解包函数

**纹理采样函数**:
- `sample(sampler2D, float2)` - 2D 纹理采样
- `sample(samplerExternalOES, float2)` - 外部纹理采样
- `sample(sampler2DRect, float2)` - 矩形纹理采样
- `sampleLod(sampler2D, float2, float)` - LOD 采样
- `sampleGrad(sampler2D, float2, float2, float2)` - 梯度采样
- `subpassLoad()` - 子通道输入读取（Vulkan）

**原子操作**:
- `atomicLoad()`, `atomicStore()`, `atomicAdd()` - 原子操作

**混合模式实现** (Porter-Duff 及高级模式):
- `blend_clear()`, `blend_src()`, `blend_dst()` - 基本混合
- `blend_src_over()`, `blend_dst_over()` - SrcOver/DstOver
- `blend_src_in()`, `blend_dst_in()`, `blend_src_out()`, `blend_dst_out()` - In/Out
- `blend_src_atop()`, `blend_dst_atop()`, `blend_xor()` - Atop/Xor
- `blend_porter_duff()` - 通用 Porter-Duff 混合
- `blend_plus()`, `blend_modulate()`, `blend_screen()` - 加法/调制/滤色
- `blend_overlay()`, `blend_darken()`, `blend_lighten()` - 叠加/变暗/变亮
- `blend_color_dodge()`, `blend_color_burn()` - 颜色减淡/加深
- `blend_hard_light()`, `blend_soft_light()` - 强光/柔光
- `blend_difference()`, `blend_exclusion()` - 差值/排除
- `blend_hslc()` - HSL 色彩/色相/饱和度/亮度混合

### sksl_public - 公共 API 函数

最小的模块，定义了用户可以在运行时着色器中使用的公共函数：

```
$pure half3 toLinearSrgb(half3 color);     // 转换到线性 sRGB
$pure half3 fromLinearSrgb(half3 color);   // 从线性 sRGB 转换
half4 $eval(float2 coords, shader s);      // 评估子着色器
half4 $eval(half4 color, colorFilter f);   // 评估颜色过滤器
half4 $eval(half4 src, half4 dst, blender b); // 评估混合器
```

### sksl_frag / sksl_vert / sksl_compute - 阶段特定函数

这些小模块定义了各着色器阶段特有的内置变量和函数：

- **sksl_frag**: 片段着色器特有的内置（如 `sk_FragCoord`）
- **sksl_vert**: 顶点着色器特有的内置（如 `sk_Position`）
- **sksl_compute**: 计算着色器特有的内置（如 `sk_GlobalInvocationID`、工作组相关变量）

### sksl_rt_shader - 运行时着色器函数

为 `SkRuntimeShaderBuilder`/`SkRuntimeEffect` 提供的内置函数集合，包含运行时着色器特有的辅助函数。

### sksl_graphite_frag - Graphite 片段着色器基础设施

这是最大的模块（未优化版约 39KB），包含 Graphite 新一代渲染引擎的片段着色器基础设施：

**颜色空间转换**:
- `sk_color_space_transform()` - 完整的颜色空间转换（含 OOTF、Gamut 映射）
- `sk_color_space_transform_srgb()` - sRGB 专用的快速路径
- `sk_color_space_transform_premul()` - 预乘 Alpha 转换
- `$apply_srgb_xfer_fn()` - sRGB 传输函数应用
- `$apply_pq_xfer_fn()` - PQ (HDR) 传输函数应用
- `$apply_hlg_xfer_fn()` - HLG 传输函数应用

**裁剪**:
- `sk_analytic_clip()` - 解析裁剪（矩形 + 圆角）
- `sk_analytic_and_atlas_clip()` - 解析 + 图集蒙版裁剪

**错误和直通**:
- `sk_error()` - 返回红色（错误指示）
- `sk_passthrough()` - 颜色直通
- `sk_rgb_opaque()` - RGB 不透明
- `sk_alpha_only()` - 仅 Alpha

**常量定义**:
- `$kTileModeClamp`, `$kTileModeRepeat`, `$kTileModeDecal` - 纹理平铺模式
- `$kFilterModeNearest`, `$kFilterModeLinear` - 纹理过滤模式
- `$kMaskFormatA8` - 蒙版格式

### sksl_graphite_vert - Graphite 顶点着色器基础设施

为 Graphite 顶点着色阶段提供的内置函数（约 20KB），包含顶点变换、实例化渲染等基础设施。

## 依赖关系

```
生成流程:
+-----------------------------------+
| 源文件 (src/sksl/sksl_*.sksl)     |
| - 手工编写的 SkSL 内置函数定义    |
+----------------+------------------+
                 |
                 v  构建时工具处理
+----------------+------------------+
| 构建系统 (GN / Bazel)            |
| - 压缩/保留格式                   |
| - 包装为 C++ 字符串常量           |
+----------------+------------------+
                 |
                 v
+----------------+------------------+
| src/sksl/generated/              |
| - *.minified.sksl  (生产用)      |
| - *.unoptimized.sksl (调试用)    |
+----------------+------------------+
                 |
                 v  编译器初始化时加载
+----------------+------------------+
| SkSL 编译器                       |
| - 解析字符串为 IR                 |
| - 构建内置符号表                   |
+-----------------------------------+

模块层次关系:
sksl_shared (基础数学)
   |
   +---> sksl_gpu (GPU 特有 + 混合模式)
   |       |
   |       +---> sksl_graphite_frag (Graphite 片段)
   |       +---> sksl_graphite_vert (Graphite 顶点)
   |
   +---> sksl_public (公共 API)
   +---> sksl_frag (片段阶段)
   +---> sksl_vert (顶点阶段)
   +---> sksl_compute (计算阶段)
   +---> sksl_rt_shader (运行时着色器)
```

## 设计模式分析

### 1. 代码生成模式 (Code Generation Pattern)

所有文件都是通过构建系统自动生成的，体现了代码生成模式。源文件（`.sksl`）是规范定义，生成的文件（`.minified.sksl` / `.unoptimized.sksl`）是派生产物。这种方法确保了内置函数定义的单一真相源（single source of truth）。

### 2. 嵌入式资源模式 (Embedded Resource Pattern)

将 SkSL 源码作为 C++ 字符串常量嵌入到二进制文件中，避免了运行时文件系统依赖。这是嵌入式系统和库开发中常见的资源管理方式：

```cpp
static constexpr char SKSL_MINIFIED_sksl_shared[] = "$pure $genType radians...";
```

### 3. 双版本发布模式

每个模块提供两个版本：
- **minified（压缩版）**: 用于生产构建，减小二进制体积
- **unoptimized（未优化版）**: 用于开发和调试，保留完整的函数名和格式

这类似于 JavaScript 生态中的 `.min.js` / `.js` 双版本发布模式。

### 4. 模块化设计

内置函数按功能和着色器阶段分为多个模块，编译器只加载程序实际需要的模块。这减少了不必要的解析开销，例如顶点着色器不需要加载片段着色器的内置函数。

### 5. 内部注解系统

SkSL 使用 `$` 前缀的注解来标记内置函数的特殊属性：
- `$pure` - 纯函数，可被编译器优化（消除冗余调用、常量折叠）
- `$es3` - 需要 ES3 特性级别
- `$export` - 导出到模块外部
- `$genType` / `$genHType` - 泛型类型参数，支持标量/向量/矩阵多态

## 数据流

```
=== 构建时 ===

src/sksl/sksl_shared.sksl (原始 SkSL 源码)
   |
   +---> 压缩处理器
   |        |
   |        v  去除注释和多余空白
   |     sksl_shared.minified.sksl
   |     (SKSL_MINIFIED_sksl_shared[])
   |
   +---> 格式保留处理器
            |
            v  保留原始格式
         sksl_shared.unoptimized.sksl
         (SKSL_MINIFIED_sksl_shared[])  // 注意：变量名相同，内容不同

=== 编译器初始化 ===

SKSL_MINIFIED_sksl_shared[]
   |
   v  Compiler::moduleForProgramKind()
   |
   +---> 根据程序类型选择需要加载的模块:
   |        - Fragment: shared + gpu + frag
   |        - Vertex: shared + gpu + vert
   |        - Compute: shared + gpu + compute
   |        - RuntimeShader: shared + public + rt_shader
   |        - GraphiteFragment: shared + gpu + graphite_frag
   |
   v  解析字符串为 SkSL IR
   |
   +---> 内置类型注册 (float, half, int, vec2, mat4, sampler2D...)
   +---> 内置函数注册 (sin, cos, mix, sample, blend_*...)
   +---> 内置变量注册 (sk_FragCoord, sk_Position...)
   |
   v  构建符号表
Module {
    fSymbols: SymbolTable*  // 所有内置符号
    fElements: vector<ProgramElement>  // 内置函数定义
}

=== 用户程序编译 ===

用户 SkSL 代码: "half4 main() { return mix(c1, c2, 0.5); }"
   |
   v  词法分析 + 语法分析
   |
   +---> 查找 "mix" -> 在内置符号表中找到
   +---> 类型检查: mix(half4, half4, float) -> 匹配
   +---> 生成函数调用 IR 节点
   |
   v  代码生成
   |
   +---> GLSL: "mix(c1, c2, 0.5)"
   +---> Metal: "mix(c1, c2, 0.5)"
   +---> SPIRV: OpExtInst %GLSLstd450 FMix ...
```

## 相关文档与参考

- **SkSL 源模块**: `src/sksl/sksl_shared.sksl`, `src/sksl/sksl_gpu.sksl` 等是生成这些文件的原始源文件。
- **SkSL 编译器**: `src/sksl/SkSLCompiler.cpp` 中包含模块加载和初始化逻辑。
- **Graphite 渲染引擎**: `src/gpu/graphite/` 使用 `sksl_graphite_*` 模块定义的着色器基础设施。
- **运行时效果**: `include/effects/SkRuntimeEffect.h` 使用 `sksl_public` 和 `sksl_rt_shader` 模块。
- **混合模式规范**: Porter-Duff 混合和高级混合模式的实现遵循 W3C Compositing and Blending Level 1 规范。
- **颜色空间标准**: Graphite 的颜色空间转换支持 sRGB、PQ (Perceptual Quantizer, HDR10) 和 HLG (Hybrid Log-Gamma) 传输函数。
- **相关目录**:
  - `src/sksl/` - SkSL 编译器主目录（包含原始 `.sksl` 源文件）
  - `src/sksl/codegen/` - 代码生成后端
  - `src/sksl/ir/` - 中间表示
  - `src/gpu/graphite/` - Graphite 渲染引擎
  - `include/effects/` - 运行时效果公共 API
