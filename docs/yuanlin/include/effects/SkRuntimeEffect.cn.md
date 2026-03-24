# SkRuntimeEffect

> 源文件: `include/effects/SkRuntimeEffect.h`

## 概述

`SkRuntimeEffect` 是 Skia 图形库中用于支持自定义着色器、颜色滤镜和混合器的运行时效果框架。它允许开发者使用 Skia 的着色语言 SkSL（Skia Shading Language）编写自定义的图形处理逻辑，并在运行时编译和执行这些程序。

该模块是 Skia 可编程管线的核心组件，为应用程序提供了超越内置效果的灵活性。通过 `SkRuntimeEffect`，开发者可以：
- 创建自定义的 **SkShader**（着色器），定义每个像素的颜色
- 创建自定义的 **SkColorFilter**（颜色滤镜），变换已有的颜色
- 创建自定义的 **SkBlender**（混合器），定义源色和目标色的混合方式

**注意**: 该 API 仍处于实验阶段，可能会发生变化。

## 架构位置

`SkRuntimeEffect` 位于 Skia 可编程渲染管线的核心位置：

```
应用层 (SkSL 源代码)
  |
  v
SkRuntimeEffect (编译 SkSL, 管理 uniforms/children)
  |
  +---> makeShader()      --> SkShader (自定义着色器)
  +---> makeColorFilter() --> SkColorFilter (自定义颜色滤镜)
  +---> makeBlender()     --> SkBlender (自定义混合器)
  |
  v
SkSL 编译器 (SkSL::Program)
  |
  +---> SkSL::RP::Program (Raster Pipeline 程序, CPU 执行)
  +---> GPU 着色器代码生成 (GLSL / SPIR-V / MSL / WGSL)
```

- **上游调用者**: 需要自定义着色效果的应用程序、Skia 内部的某些高级效果。
- **下游依赖**: SkSL 编译器、Raster Pipeline 执行引擎、GPU 着色器代码生成器、`SkShader`/`SkColorFilter`/`SkBlender` 框架。

## 主要类与结构体

### `SkRuntimeEffect` (类)

运行时效果的核心类，继承自 `SkRefCnt`。负责编译 SkSL 程序、管理 uniform 变量和子效果，并生成可用于绘制的 Shader/ColorFilter/Blender 对象。

### `SkRuntimeEffect::Uniform` (结构体)

描述 SkSL 程序中 `uniform` 变量的反射信息。

| 成员 | 类型 | 说明 |
|------|------|------|
| `name` | `std::string_view` | 变量名称 |
| `offset` | `size_t` | 在 uniform 数据块中的字节偏移量 |
| `type` | `Type` | 变量类型（见下表） |
| `count` | `int` | 数组长度（非数组时为 1） |
| `flags` | `uint32_t` | 标志位组合 |

**Uniform::Type 枚举**:

| 类型 | 说明 |
|------|------|
| `kFloat` | 单精度浮点数 |
| `kFloat2` | 2 维浮点向量 |
| `kFloat3` | 3 维浮点向量 |
| `kFloat4` | 4 维浮点向量 |
| `kFloat2x2` | 2x2 浮点矩阵 |
| `kFloat3x3` | 3x3 浮点矩阵 |
| `kFloat4x4` | 4x4 浮点矩阵 |
| `kInt` | 整数 |
| `kInt2` | 2 维整数向量 |
| `kInt3` | 3 维整数向量 |
| `kInt4` | 4 维整数向量 |

**Uniform::Flags 标志位**:

| 标志 | 值 | 说明 |
|------|------|------|
| `kArray_Flag` | `0x1` | 声明为数组，`count` 包含数组长度 |
| `kColor_Flag` | `0x2` | 使用 `layout(color)` 声明。颜色应以非预乘扩展范围 sRGB 格式提供，会自动转换到工作色彩空间 |
| `kVertex_Flag` | `0x4` | 仅用于 `SkMeshSpecification`，表示 uniform 出现在顶点着色器中 |
| `kFragment_Flag` | `0x8` | 仅用于 `SkMeshSpecification`，表示 uniform 出现在片段着色器中 |
| `kHalfPrecision_Flag` | `0x10` | 表示 SkSL 中使用了中等精度类型（`half` 而非 `float`） |

**Uniform 辅助方法**:
- `isArray()`: 返回是否为数组类型
- `isColor()`: 返回是否使用了 `layout(color)` 标注
- `sizeInBytes()`: 返回此 uniform 变量的总字节大小

### `SkRuntimeEffect::Child` (结构体)

描述 SkSL 程序中子效果（child effect）的反射信息。

| 成员 | 类型 | 说明 |
|------|------|------|
| `name` | `std::string_view` | 子效果名称 |
| `type` | `ChildType` | 子效果类型 |
| `index` | `int` | 在子效果数组中的索引 |

### `SkRuntimeEffect::ChildType` (枚举)

| 值 | 说明 |
|----|------|
| `kShader` | 子着色器 |
| `kColorFilter` | 子颜色滤镜 |
| `kBlender` | 子混合器 |

### `SkRuntimeEffect::Options` (类)

编译选项配置。

| 成员 | 访问级别 | 类型 | 默认值 | 说明 |
|------|----------|------|--------|------|
| `forceUnoptimized` | `public` | `bool` | `false` | 禁用优化和内联（用于测试） |
| `fName` | `public` | `std::string_view` | 空 | 用于标识运行时效果的名称 |
| `allowPrivateAccess` | `private` | `bool` | `false` | 允许访问 Skia 内部函数（如 `sk_FragCoord`、`$rgb_to_hsl`） |
| `fStableKey` | `private` | `uint32_t` | `0` | 稳定的键值，用于缓存和标识已知的运行时效果 |
| `maxVersionAllowed` | `private` | `SkSL::Version` | `k100` (ES2) | 允许的最大 SkSL 版本。默认限制为 ES2，更高版本可能在软件渲染器中不完全支持 |

### `SkRuntimeEffect::Result` (结构体)

编译结果容器。

| 成员 | 类型 | 说明 |
|------|------|------|
| `effect` | `sk_sp<SkRuntimeEffect>` | 编译成功时非空 |
| `errorText` | `SkString` | 编译失败时包含错误信息 |

### `SkRuntimeEffect::ChildPtr` (类)

用于传递子效果的类型安全包装器。可持有 `SkShader`、`SkColorFilter` 或 `SkBlender`。

| 方法 | 说明 |
|------|------|
| 构造函数 | 支持从 `sk_sp<SkShader>`、`sk_sp<SkColorFilter>`、`sk_sp<SkBlender>`、`sk_sp<SkFlattenable>` 隐式构造 |
| `type()` | 返回子效果的类型（`optional<ChildType>`） |
| `shader()` | 获取内部的 SkShader 指针 |
| `colorFilter()` | 获取内部的 SkColorFilter 指针 |
| `blender()` | 获取内部的 SkBlender 指针 |
| `flattenable()` | 获取内部的 SkFlattenable 基类指针 |

### `SkRuntimeEffect::TracedShader` (结构体)

调试追踪着色器的结果容器。

| 成员 | 类型 | 说明 |
|------|------|------|
| `shader` | `sk_sp<SkShader>` | 带调试追踪功能的着色器 |
| `debugTrace` | `sk_sp<SkSL::DebugTrace>` | 执行追踪数据 |

### `SkRuntimeEffectBuilder` (类)

简化 `SkRuntimeEffect` 使用的辅助构建器类，提供命名访问 uniform 变量和子效果的便捷接口。

#### `SkRuntimeEffectBuilder::BuilderUniform` (结构体)

通过名称访问和设置 uniform 变量值的代理对象。

| 方法 | 说明 |
|------|------|
| `operator=(const T& val)` | 将值拷贝到 uniform 变量（要求 `T` 是 trivially copyable 且大小匹配） |
| `operator=(const SkMatrix& val)` | 特化的矩阵赋值，自动进行行主序到列主序的转换 |
| `set(const T val[], int count)` | 设置数组类型的 uniform 值 |

#### `SkRuntimeEffectBuilder::BuilderChild` (结构体)

通过名称访问和设置子效果的代理对象。

| 方法 | 说明 |
|------|------|
| `operator=(sk_sp<T> val)` | 设置子效果（`T` 可为 `SkShader`、`SkColorFilter` 或 `SkBlender`） |
| `operator=(std::nullptr_t)` | 清除子效果 |

## 公共 API 函数

### 编译函数

#### `SkRuntimeEffect::MakeForColorFilter(SkString sksl, const Options&) -> Result`

编译用于颜色滤镜的 SkSL 代码。入口点签名要求：
```sksl
vec4 main(vec4 inColor) { ... }
```

#### `SkRuntimeEffect::MakeForShader(SkString sksl, const Options&) -> Result`

编译用于着色器的 SkSL 代码。入口点签名要求：
```sksl
vec4 main(vec2 inCoords) { ... }
```
返回的颜色应为预乘格式。

#### `SkRuntimeEffect::MakeForBlender(SkString sksl, const Options&) -> Result`

编译用于混合器的 SkSL 代码。入口点签名要求：
```sksl
vec4 main(vec4 srcColor, vec4 dstColor) { ... }
```

以上三个函数均提供无 `Options` 参数的便捷重载版本。

### 实例化函数

#### `makeShader(sk_sp<const SkData> uniforms, SkSpan<const ChildPtr> children, const SkMatrix* localMatrix) -> sk_sp<SkShader>`

使用指定的 uniform 数据和子效果创建着色器。

- **参数**:
  - `uniforms`: uniform 数据块，大小必须等于 `uniformSize()`
  - `children`: 子效果数组
  - `localMatrix`: 可选的局部变换矩阵
- **返回值**: 自定义着色器

另有接受原始 `sk_sp<SkShader>[]` 数组的重载版本。

#### `makeColorFilter(sk_sp<const SkData> uniforms, SkSpan<const ChildPtr> children) -> sk_sp<SkColorFilter>`

使用指定的 uniform 数据和子效果创建颜色滤镜。提供三个重载版本——无子效果版本、原始数组版本和 `SkSpan` 版本。

#### `makeBlender(sk_sp<const SkData> uniforms, SkSpan<const ChildPtr> children) -> sk_sp<SkBlender>`

使用指定的 uniform 数据和子效果创建混合器。`children` 参数默认为空。

### 调试函数

#### `SkRuntimeEffect::MakeTraced(sk_sp<SkShader> shader, const SkIPoint& traceCoord) -> TracedShader`

创建带调试追踪功能的着色器副本，在指定坐标处记录执行轨迹。

- **参数**:
  - `shader`: 原始着色器
  - `traceCoord`: 需要追踪的像素坐标
- **返回值**: 包含追踪着色器和调试追踪对象的 `TracedShader`
- **限制**: 仅支持光栅（非 GPU）画布；颜色滤镜和混合器的追踪尚在开发中

### 查询函数

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `source()` | `const std::string&` | 返回 SkSL 源代码 |
| `uniformSize()` | `size_t` | 所有 uniform 变量的总字节大小 |
| `uniforms()` | `SkSpan<const Uniform>` | 所有 uniform 变量的描述信息 |
| `children()` | `SkSpan<const Child>` | 所有子效果的描述信息 |
| `findUniform(name)` | `const Uniform*` | 按名称查找 uniform 变量，未找到返回 `nullptr` |
| `findChild(name)` | `const Child*` | 按名称查找子效果，未找到返回 `nullptr` |
| `allowShader()` | `bool` | 该效果是否可用作着色器 |
| `allowColorFilter()` | `bool` | 该效果是否可用作颜色滤镜 |
| `allowBlender()` | `bool` | 该效果是否可用作混合器 |

### SkRuntimeEffectBuilder 方法

| 方法 | 说明 |
|------|------|
| `uniform(name)` | 返回 `BuilderUniform` 代理，用于设置命名 uniform 变量的值 |
| `child(name)` | 返回 `BuilderChild` 代理，用于设置命名子效果 |
| `uniforms()` | 获取当前的 uniform 数据 |
| `children()` | 获取当前的子效果数组 |
| `makeShader(localMatrix)` | 构建着色器 |
| `makeColorFilter()` | 构建颜色滤镜 |
| `makeBlender()` | 构建混合器 |

## 内部实现细节

### 编译与执行流程

1. **SkSL 编译**: `MakeForShader`/`MakeForColorFilter`/`MakeForBlender` 调用 SkSL 编译器将源代码解析为 `SkSL::Program` AST。编译器会验证入口点签名是否符合目标类型的要求。

2. **双重执行路径**:
   - **Raster Pipeline (RP)**: 在 CPU 上执行，SkSL 被编译为 Skia 的 Raster Pipeline 中间表示（`SkSL::RP::Program`）。通过 `getRPProgram()` 获取，使用 `SkOnce` 实现懒编译。
   - **GPU 代码生成**: 在 GPU 上执行时，`fBaseProgram` 被传递给 GPU 后端的着色器代码生成器，转换为 GLSL、SPIR-V、MSL 或 WGSL。

3. **入口点函数**: `fMain` 引用编译后程序中的主入口函数定义（`SkSL::FunctionDefinition`）。

### 标志位系统

内部使用 `fFlags` 位域跟踪编译后程序的特性：

| 标志 | 说明 |
|------|------|
| `kUsesSampleCoords_Flag` | 程序使用了采样坐标 |
| `kAllowColorFilter_Flag` | 可用作颜色滤镜 |
| `kAllowShader_Flag` | 可用作着色器 |
| `kAllowBlender_Flag` | 可用作混合器 |
| `kSamplesOutsideMain_Flag` | 在 `main()` 之外采样子效果 |
| `kUsesColorTransform_Flag` | 使用了颜色空间变换 |
| `kAlwaysOpaque_Flag` | 输出总是不透明 |
| `kAlphaUnchanged_Flag` | Alpha 通道不被修改 |
| `kDisableOptimization_Flag` | 禁用优化 |

### Uniform 数据管理

`SkRuntimeEffectBuilder` 使用写时复制（Copy-on-Write）策略管理 uniform 数据：
- `fUniforms` 是 `sk_sp<SkData>` 共享数据块
- `writableUniformData()` 在数据不唯一时创建副本再修改
- 这允许多个 Builder 共享相同的初始 uniform 数据

### SkMatrix 特殊处理

`BuilderUniform` 为 `SkMatrix` 提供了特化的赋值运算符，自动进行 Skia 的行主序（3x3 SkMatrix 的内部存储格式）到 SkSL 的列主序（GLSL 风格的矩阵存储格式）的转换。

### 友元类访问

以下类作为友元可以访问 `SkRuntimeEffect` 的私有成员：

| 友元类 | 访问内容 |
|--------|----------|
| `GrSkSLFP` | `usesColorTransform()` |
| `SkRuntimeShader` | `fBaseProgram`, `fMain`, `fSampleUsages`, `getRPProgram()` |
| `SkRuntimeBlender` | 同上 |
| `SkRuntimeColorFilter` | 同上 |
| `SkRuntimeEffectPriv` | 全部私有成员 |

## 依赖关系

| 依赖项 | 头文件 | 用途 |
|--------|--------|------|
| `SkBlender` | `include/core/SkBlender.h` | 混合器基类 |
| `SkColorFilter` | `include/core/SkColorFilter.h` | 颜色滤镜基类 |
| `SkData` | `include/core/SkData.h` | uniform 数据容器 |
| `SkFlattenable` | `include/core/SkFlattenable.h` | 序列化基类 |
| `SkMatrix` | `include/core/SkMatrix.h` | 变换矩阵 |
| `SkRefCnt` | `include/core/SkRefCnt.h` | 引用计数基类 |
| `SkShader` | `include/core/SkShader.h` | 着色器基类 |
| `SkSpan` | `include/core/SkSpan.h` | 轻量级数组视图 |
| `SkString` | `include/core/SkString.h` | 字符串类 |
| `SkSLSampleUsage` | `include/private/SkSLSampleUsage.h` | 采样使用分析 |
| `SkOnce` | `include/private/base/SkOnce.h` | 一次性初始化 |
| `SkSLDebugTrace` | `include/sksl/SkSLDebugTrace.h` | 调试追踪接口 |
| `SkSLVersion` | `include/sksl/SkSLVersion.h` | SkSL 版本定义 |
| `SkSL::Program` | - | SkSL 编译后的程序（前向声明） |
| `SkSL::RP::Program` | - | Raster Pipeline 程序（前向声明） |

## 设计模式与设计决策

1. **编译与实例化分离**: SkSL 源码编译（`MakeForShader` 等）与效果实例化（`makeShader` 等）是两个独立步骤。一次编译可以多次实例化不同的 uniform 值和子效果组合，避免重复编译开销。

2. **反射式 API**: 通过 `uniforms()` 和 `children()` 提供编译后的反射信息，允许调用者在运行时发现和操作 uniform 变量，实现数据驱动的效果配置。

3. **类型安全的 ChildPtr**: `ChildPtr` 使用 `SkFlattenable` 基类内部存储，但提供类型安全的构造函数和访问方法，避免运行时类型错误。

4. **Builder 模式**: `SkRuntimeEffectBuilder` 提供了更友好的命名访问接口，通过 `uniform("name") = value` 的语法糖简化了 uniform 设置过程，比直接操作原始字节数据更安全、更易读。

5. **写时复制 uniform 数据**: Builder 中的 uniform 数据使用 COW 策略，允许高效的拷贝和共享。

6. **Result 模式**: 编译结果使用 `Result` 结构体返回，包含成功时的 effect 和失败时的错误信息，避免了异常机制的使用，符合 Skia 的无异常编码风格。

7. **类型别名兼容**: `SkRuntimeShaderBuilder`、`SkRuntimeColorFilterBuilder`、`SkRuntimeBlendBuilder` 现在都是 `SkRuntimeEffectBuilder` 的类型别名，简化了之前按类型分离的 Builder 子类设计。

8. **ES2 默认限制**: 默认限制 SkSL 版本为 ES2（`SkSL::Version::k100`），确保在所有后端（包括软件渲染器）上的兼容性。更高版本的 SkSL 特性需要显式启用。

## 性能考量

1. **编译缓存**: SkSL 编译是相对昂贵的操作。`SkRuntimeEffect` 对象应被缓存和复用，避免相同源码的重复编译。`fHash` 和 `fStableKey` 支持基于键的缓存查找。

2. **懒编译 RP 程序**: Raster Pipeline 程序通过 `SkOnce` 实现延迟编译——只有在实际需要 CPU 执行时才编译 RP 程序，避免了 GPU-only 场景下的不必要开销。

3. **优化控制**: `Options::forceUnoptimized` 和 `kDisableOptimization_Flag` 允许在测试时禁用优化，但生产环境应保持优化开启以获得最佳性能。

4. **Uniform 数据对齐**: uniform 变量的 `offset` 和 `sizeInBytes()` 确保了内存布局的正确对齐，这对 GPU 后端的 uniform buffer 传输至关重要。

5. **子效果采样分析**: `fSampleUsages` 记录了每个子效果的采样模式（如仅在 `main` 中采样 vs. 任意位置采样），GPU 后端可利用此信息进行优化（如是否需要完整的纹理 mipmap）。

6. **调试追踪的性能代价**: `MakeTraced` 生成的着色器会在指定坐标处记录完整的执行轨迹，这会显著降低性能，仅应在调试时使用，且仅支持光栅画布。

7. **Alpha 和不透明性分析**: `kAlwaysOpaque_Flag` 和 `kAlphaUnchanged_Flag` 允许渲染管线跳过不必要的 alpha 混合操作，这是重要的性能优化。

## 相关文件

- `include/core/SkShader.h` - 着色器基类
- `include/core/SkColorFilter.h` - 颜色滤镜基类
- `include/core/SkBlender.h` - 混合器基类
- `include/core/SkData.h` - 数据容器（用于 uniform 数据块）
- `include/core/SkFlattenable.h` - 序列化框架
- `include/sksl/SkSLDebugTrace.h` - 调试追踪接口
- `include/sksl/SkSLVersion.h` - SkSL 语言版本定义
- `include/private/SkSLSampleUsage.h` - 子效果采样模式分析
- `src/core/SkRuntimeEffect.cpp` - 核心实现（编译、实例化）
- `src/core/SkRuntimeShader.cpp` - 运行时着色器实现
- `src/core/SkRuntimeColorFilter.cpp` - 运行时颜色滤镜实现
- `src/core/SkRuntimeBlender.cpp` - 运行时混合器实现
- `src/sksl/SkSLCompiler.h` - SkSL 编译器
- `src/sksl/codegen/SkSLRasterPipelineCodeGenerator.h` - RP 代码生成器
