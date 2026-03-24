# GrTessellationShader

> 源文件
> - `src/gpu/ganesh/tessellate/GrTessellationShader.h`
> - `src/gpu/ganesh/tessellate/GrTessellationShader.cpp`

## 概述

`GrTessellationShader` 是 Ganesh GPU 细分曲面(Tessellation)渲染系统中所有着色器的公共基类,继承自 `GrGeometryProcessor`。该类提供统一的管线创建、程序构建接口,以及 Wang's Formula(王氏公式)的 SkSL 实现,用于计算曲线细分所需的段数。它封装了视图矩阵、颜色、图元类型等通用属性,为路径和笔画的细分曲面渲染提供基础设施。

## 架构位置

`GrTessellationShader` 位于 Ganesh 细分曲面渲染管线的着色器基础层:

```
Skia GPU 渲染架构
├── 通用几何处理器
│   └── GrGeometryProcessor (基类)
├── 细分曲面着色器层
│   ├── GrTessellationShader (细分着色器基类) ← 当前类
│   ├── PathTessellationShader (路径细分着色器)
│   └── StrokeTessellationShader (笔画细分着色器)
├── 细分器层
│   ├── PathTessellator (路径细分器)
│   └── StrokeTessellator (笔画细分器)
└── 管线管理层
    ├── GrPipeline (渲染管线)
    └── GrProgramInfo (程序信息)
```

该类为所有细分曲面着色器提供通用框架和工具函数。

## 主要类与结构体

### 继承关系

| 类名 | 关系 | 说明 |
|------|------|------|
| `GrGeometryProcessor` | 父类 | Ganesh 几何处理器基类 |
| `GrTessellationShader` | 当前类 | 细分着色器公共基类 |
| `PathTessellationShader` | 派生类 | 路径细分着色器(未在本文件) |
| `StrokeTessellationShader` | 派生类 | 笔画细分着色器(未在本文件) |

### 嵌套结构体

#### ProgramArgs

封装程序创建所需的所有参数:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fArena` | `SkArenaAlloc*` | Arena 内存分配器 |
| `fWriteView` | `const GrSurfaceProxyView&` | 写入目标视图 |
| `fUsesMSAASurface` | `bool` | 是否使用 MSAA 表面 |
| `fDstProxyView` | `const GrDstProxyView*` | 目标代理视图(用于混合) |
| `fXferBarrierFlags` | `GrXferBarrierFlags` | 传输屏障标志 |
| `fColorLoadOp` | `GrLoadOp` | 颜色加载操作 |
| `fCaps` | `const GrCaps*` | GPU 能力查询接口 |

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPrimitiveType` | `GrPrimitiveType` | 图元类型(三角形、三角带等) |
| `fViewMatrix` | `SkMatrix` | 视图变换矩阵 |
| `fColor` | `SkPMColor4f` | 预乘 Alpha 颜色 |

## 公共 API 函数

### 构造函数

```cpp
GrTessellationShader(ClassID classID,
                     GrPrimitiveType primitiveType,
                     const SkMatrix& viewMatrix,
                     const SkPMColor4f& color);
```
初始化细分着色器基类,设置图元类型、视图矩阵和颜色。

### 访问器

```cpp
GrPrimitiveType primitiveType() const;
const SkMatrix& viewMatrix() const;
const SkPMColor4f& color() const;
```
获取着色器的基本属性。

### 管线创建

```cpp
static const GrPipeline* MakePipeline(const ProgramArgs&,
                                      GrAAType,
                                      GrAppliedClip&&,
                                      GrProcessorSet&&);
```
静态工厂函数,创建渲染管线。

**实现:**
```cpp
GrPipeline::InitArgs pipelineArgs;
pipelineArgs.fCaps = args.fCaps;
pipelineArgs.fDstProxyView = *args.fDstProxyView;
pipelineArgs.fWriteSwizzle = args.fWriteView.swizzle();

return args.fArena->make<GrPipeline>(pipelineArgs,
                                     std::move(processors),
                                     std::move(appliedClip));
```

### 程序创建

```cpp
static GrProgramInfo* MakeProgram(const ProgramArgs& args,
                                  const GrTessellationShader* shader,
                                  const GrPipeline* pipeline,
                                  const GrUserStencilSettings* stencil);
```
静态工厂函数,创建完整的程序信息对象。

**实现:**
```cpp
return args.fArena->make<GrProgramInfo>(
    *args.fCaps, args.fWriteView, args.fUsesMSAASurface,
    pipeline, stencil, shader, shader->fPrimitiveType,
    args.fXferBarrierFlags, args.fColorLoadOp);
```

### Wang's Formula SkSL

```cpp
static const char* WangsFormulaSkSL();
```
返回 Wang's Formula 的 SkSL 实现代码,用于计算曲线细分段数。

## 内部实现细节

### Wang's Formula SkSL 实现

提供多个 SkSL 函数用于计算细分段数:

#### 1. 三次贝塞尔曲线最大前向差分

```glsl
float wangs_formula_max_fdiff_p2(float2 p0, float2 p1, float2 p2, float2 p3,
                                  float2x2 matrix) {
    float2 d0 = matrix * (fma(float2(-2), p1, p2) + p0);
    float2 d1 = matrix * (fma(float2(-2), p2, p3) + p1);
    return max(dot(d0,d0), dot(d1,d1));
}
```
计算三次曲线的最大前向差分平方。

#### 2. 三次曲线段数(线性)

```glsl
float wangs_formula_cubic(float _precision_, float2 p0, float2 p1, float2 p2, float2 p3,
                          float2x2 matrix) {
    float m = wangs_formula_max_fdiff_p2(p0, p1, p2, p3, matrix);
    return max(ceil(sqrt(0.75 * _precision_ * sqrt(m))), 1.0);
}
```
公式: `n = ceil(sqrt(0.75 * precision * sqrt(max_fdiff^2)))`

#### 3. 三次曲线段数(对数)

```glsl
float wangs_formula_cubic_log2(float _precision_, float2 p0, float2 p1, float2 p2, float2 p3,
                               float2x2 matrix) {
    float m = wangs_formula_max_fdiff_p2(p0, p1, p2, p3, matrix);
    return ceil(log2(max(0.5625 * _precision_ * _precision_ * m, 1.0)) * .25);
}
```
返回 log2(段数),用于二进制细分策略。常量 `0.5625 = 0.75^2`。

#### 4. 圆锥曲线段数平方

```glsl
float wangs_formula_conic_p2(float _precision_, float2 p0, float2 p1, float2 p2, float w) {
    // 将边界框中心平移到原点
    float2 C = (min(min(p0, p1), p2) + max(max(p0, p1), p2)) * 0.5;
    p0 -= C;
    p1 -= C;
    p2 -= C;

    // 计算最大长度
    float m = sqrt(max(max(dot(p0,p0), dot(p1,p1)), dot(p2,p2)));

    // 计算前向差分
    float2 dp = fma(float2(-2.0 * w), p1, p0) + p2;
    float dw = abs(fma(-2.0, w, 2.0));

    // 计算参数步长的分子和分母
    float rp_minus_1 = max(0.0, fma(m, _precision_, -1.0));
    float numer = length(dp) * _precision_ + rp_minus_1 * dw;
    float denom = 4 * min(w, 1.0);

    return numer/denom;
}
```

#### 5. 圆锥曲线段数

```glsl
float wangs_formula_conic(float _precision_, float2 p0, float2 p1, float2 p2, float w) {
    float n2 = wangs_formula_conic_p2(_precision_, p0, p1, p2, w);
    return max(ceil(sqrt(n2)), 1.0);
}
```

#### 6. 圆锥曲线段数(对数)

```glsl
float wangs_formula_conic_log2(float _precision_, float2 p0, float2 p1, float2 p2, float w) {
    float n2 = wangs_formula_conic_p2(_precision_, p0, p1, p2, w);
    return ceil(log2(max(n2, 1.0)) * .5);
}
```

### 静态断言验证

```cpp
static_assert(skgpu::wangs_formula::length_term<3>(1) == 0.75);
static_assert(skgpu::wangs_formula::length_term_p2<3>(1) == 0.5625);
```
编译时验证 Wang's Formula 常量的正确性。

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `GrGeometryProcessor` | 继承 | 几何处理器基类 |
| `GrPipeline` | 使用 | 渲染管线对象 |
| `GrProgramInfo` | 使用 | 程序信息封装 |
| `skgpu::wangs_formula` | 工具 | Wang's Formula C++ 实现(用于验证) |
| `GrCaps` | 依赖 | GPU 能力查询 |
| `SkMatrix` | 类型 | 矩阵变换 |
| `SkPMColor4f` | 类型 | 预乘颜色 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| PathTessellationShader | 继承 GrTessellationShader |
| StrokeTessellationShader | 继承 GrTessellationShader |
| PathTessellator | 使用着色器进行路径细分 |
| StrokeTessellator | 使用着色器进行笔画细分 |

## 设计模式与设计决策

### 模板方法模式

基类提供统一的管线和程序创建方法,派生类专注于特定的着色器实现:
```cpp
static GrProgramInfo* MakeProgram(..., const GrTessellationShader* shader, ...);
```
派生类传入自身指针,基类负责组装完整的程序。

### 静态工厂方法

所有创建方法都是静态的,避免虚函数开销:
```cpp
static const GrPipeline* MakePipeline(...);
static GrProgramInfo* MakeProgram(...);
```

### 内联 SkSL 代码

Wang's Formula 作为字符串字面量内联在 C++ 代码中:
```cpp
return "float wangs_formula_cubic(...) { ... }";
```
优点:
- 编译时字符串常量,无运行时开销
- 易于维护和版本控制
- 支持多个着色器共享相同代码

### 常量验证

使用 `static_assert` 在编译时验证数学常量:
```cpp
static_assert(skgpu::wangs_formula::length_term<3>(1) == 0.75);
```
确保 SkSL 和 C++ 实现的一致性。

### 对数变体优化

提供 `_log2` 变体函数,返回对数段数:
```cpp
wangs_formula_cubic_log2(...)  // 返回 log2(段数)
```
用于硬件二进制细分,避免运行时对数计算。

## 性能考量

### 数学优化

**FMA 指令**:
```glsl
float2 d0 = matrix * (fma(float2(-2), p1, p2) + p0);
```
使用融合乘加(Fused Multiply-Add)减少舍入误差并提升性能。

**展开计算**:
```glsl
float2 d1 = matrix * (fma(float2(-2), p2, p3) + p1);
```
避免循环,直接计算两个前向差分。

### 平方根优化

**避免双重平方根**:
```glsl
// 原始公式: n = sqrt(0.75 * precision * sqrt(m))
// 简化为: n2 = 0.75 * precision * sqrt(m)
// 仅在最后取平方根
return max(ceil(sqrt(0.75 * _precision_ * sqrt(m))), 1.0);
```

**对数变体**:
```glsl
// 对数域计算,避免平方根
return ceil(log2(max(0.5625 * _precision_ * _precision_ * m, 1.0)) * .25);
```

### 圆锥曲线优化

**边界框中心化**:
```glsl
float2 C = (min(min(p0, p1), p2) + max(max(p0, p1), p2)) * 0.5;
p0 -= C;
```
平移到原点,提升数值稳定性,减少浮点误差。

### Arena 分配

```cpp
return args.fArena->make<GrPipeline>(...);
```
使用 Arena 分配管线和程序对象,批量释放,无单个对象析构开销。

### 最小段数保证

```glsl
return max(ceil(...), 1.0);
```
确保至少 1 段,避免退化情况。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrGeometryProcessor.h` | 父类 | 几何处理器基类 |
| `src/gpu/ganesh/GrPipeline.h` | 依赖 | 渲染管线 |
| `src/gpu/ganesh/GrProgramInfo.h` | 依赖 | 程序信息 |
| `src/gpu/tessellate/WangsFormula.h` | 工具 | Wang's Formula C++ 实现 |
| `src/gpu/tessellate/PathTessellator.h` | 使用者 | 路径细分器 |
| `src/gpu/tessellate/StrokeTessellator.h` | 使用者 | 笔画细分器 |
| `src/gpu/ganesh/GrCaps.h` | 依赖 | GPU 能力查询 |
| `src/gpu/Swizzle.h` | 工具 | 颜色 swizzle |
