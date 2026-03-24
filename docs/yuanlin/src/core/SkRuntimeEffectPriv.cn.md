# SkRuntimeEffectPriv

> 源文件: src/core/SkRuntimeEffectPriv.h

## 概述

`SkRuntimeEffectPriv` 提供了 Skia 运行时效果系统的私有扩展 API,用于内部模块访问 `SkRuntimeEffect` 的高级功能。该模块包括延迟 uniform 绑定、稳定键(stable key)管理、uniform 颜色空间转换、子效果序列化、以及光栅管线(Raster Pipeline)回调接口。这些功能主要服务于 Skia 内部的着色器编译、缓存、序列化和 GPU 后端集成。

## 架构位置

`SkRuntimeEffectPriv` 位于 `src/core` 模块,是运行时效果系统的私有接口层:

- **公共层**: `SkRuntimeEffect` 提供用户级 API
- **私有层**: `SkRuntimeEffectPriv` 暴露内部扩展功能
- **编译层**: 与 SkSL 编译器(`src/sksl`)交互
- **后端层**: 为 Ganesh 和 Graphite GPU 后端提供支持
- **缓存层**: 集成全局缓存机制(`SkMakeCachedRuntimeEffect`)

## 主要类与结构体

### SkRuntimeEffectPriv (静态工具类)

| 属性 | 说明 |
|------|------|
| **继承关系** | 无继承关系,纯静态工具类 |
| **核心功能** | 延迟 uniform 回调、稳定键管理、uniform 转换、元数据访问 |

提供访问 `SkRuntimeEffect` 内部状态和功能的静态方法。

### UniformsCallbackContext

| 属性 | 说明 |
|------|------|
| **继承关系** | 独立结构体 |
| **关键成员变量** | `fDstColorSpace`: 目标颜色空间指针 |

传递给 uniform 回调函数的上下文信息。

### RuntimeEffectRPCallbacks

| 属性 | 说明 |
|------|------|
| **继承关系** | 继承自 `SkSL::RP::Callbacks` |
| **关键成员变量** | `fStage`: 光栅管线阶段记录<br>`fMatrix`: 矩阵记录<br>`fChildren`: 子效果数组<br>`fSampleUsages`: 采样使用信息 |

实现光栅管线执行时的回调接口,用于处理子着色器、颜色滤镜和混合器。

## 公共 API 函数

### 延迟 Uniform 绑定

```cpp
// Uniform 回调函数类型
using UniformsCallback = std::function<sk_sp<const SkData>(
    const UniformsCallbackContext&)>;

// 创建使用延迟 uniform 的着色器
static sk_sp<SkShader> MakeDeferredShader(
    const SkRuntimeEffect* effect,
    UniformsCallback uniformsCallback,
    SkSpan<const SkRuntimeEffect::ChildPtr> children,
    const SkMatrix* localMatrix = nullptr);
```

### 稳定键管理

```cpp
// 获取效果的稳定键(用于跨进程识别)
static uint32_t StableKey(const SkRuntimeEffect& effect);

// 设置用户定义的稳定键
static void SetStableKey(SkRuntimeEffect* effect, uint32_t stableKey);

// 设置 Skia 内部稳定键(在 Options 中)
static void SetStableKeyOnOptions(SkRuntimeEffect::Options* options,
                                  uint32_t stableKey);

// 重置稳定键
static void ResetStableKey(SkRuntimeEffect* effect);
```

### 元数据访问

```cpp
// 获取效果的哈希值
static uint32_t Hash(const SkRuntimeEffect& effect);

// 检查效果是否有名称
static bool HasName(const SkRuntimeEffect& effect);

// 获取效果名称
static const char* GetName(const SkRuntimeEffect& effect);

// 获取底层 SkSL 程序对象
static const SkSL::Program& Program(const SkRuntimeEffect& effect);
```

### Uniform 颜色空间转换

```cpp
// 转换 uniform 数据中的颜色值到目标颜色空间
static sk_sp<const SkData> TransformUniforms(
    SkSpan<const SkRuntimeEffect::Uniform> uniforms,
    sk_sp<const SkData> originalData,
    const SkColorSpaceXformSteps&);

static sk_sp<const SkData> TransformUniforms(
    SkSpan<const SkRuntimeEffect::Uniform> uniforms,
    sk_sp<const SkData> originalData,
    const SkColorSpace* dstCS);

// 将 uniform 数据转换为 float 数组(可选颜色空间转换)
static SkSpan<const float> UniformsAsSpan(
    SkSpan<const SkRuntimeEffect::Uniform> uniforms,
    sk_sp<const SkData> originalData,
    bool alwaysCopyIntoAlloc,
    const SkColorSpace* destColorSpace,
    SkArenaAlloc* alloc);
```

### 子效果序列化

```cpp
// 从缓冲区读取子效果数组
static bool ReadChildEffects(
    SkReadBuffer& buffer,
    const SkRuntimeEffect* effect,
    skia_private::TArray<SkRuntimeEffect::ChildPtr>* children);

// 将子效果数组写入缓冲区
static void WriteChildEffects(
    SkWriteBuffer& buffer,
    SkSpan<const SkRuntimeEffect::ChildPtr> children);
```

### 能力检查

```cpp
// 检查设备是否支持运行该效果
static bool CanDraw(const SkCapabilities*, const SkSL::Program*);
static bool CanDraw(const SkCapabilities*, const SkRuntimeEffect*);

// 检查是否支持常量输出优化(GrFragmentProcessor 用)
static bool SupportsConstantOutputForConstantInput(
    const SkRuntimeEffect* effect);

// 检查是否使用颜色空间转换
static bool UsesColorTransform(const SkRuntimeEffect* effect);

// 获取子效果的采样使用信息
static SkSL::SampleUsage ChildSampleUsage(const SkRuntimeEffect* effect,
                                          int child);
```

### Options 配置

```cpp
// 创建 ES3 选项(允许 GLSL ES 3.0 特性)
static SkRuntimeEffect::Options ES3Options();

// 允许访问私有 SkSL 功能
static void AllowPrivateAccess(SkRuntimeEffect::Options* options);
```

### 变量转换

```cpp
// 将 SkSL 变量转换为 Uniform 描述
static SkRuntimeEffect::Uniform VarAsUniform(const SkSL::Variable&,
                                             const SkSL::Context&,
                                             size_t* offset);

// 将 SkSL 变量转换为 Child 描述
static SkRuntimeEffect::Child VarAsChild(const SkSL::Variable& var,
                                        int index);

// 将 Child 类型转换为字符串
static const char* ChildTypeToStr(SkRuntimeEffect::ChildType type);
```

## 内部实现细节

### 延迟 Uniform 回调机制

`MakeDeferredShader` 创建的着色器行为:
1. **构造时**: 存储回调函数和子效果,不立即求值 uniform
2. **绘制时**: 在实际绘制前调用回调,传入目标颜色空间信息
3. **序列化时**: 立即调用回调并记录结果的 uniform 数据

用途:
- 根据目标颜色空间动态生成 uniform(如颜色值)
- 延迟昂贵的 uniform 计算到实际需要时
- 支持跨线程共享着色器(回调在绘制线程执行)

### 稳定键(Stable Key)机制

稳定键是一个 32 位整数,用于跨进程识别运行时效果:
- **Skia 内部效果**: 使用 `SkKnownRuntimeEffects` 预定义的键
- **用户定义效果**: 可选择性注册稳定键
- **用途**: 序列化、远程渲染、效果识别

设计约束:
- 通过 `SkKnownRuntimeEffects::IsViableUserDefinedKnownRuntimeEffect` 验证用户键
- 通过 `SkKnownRuntimeEffects::IsSkiaKnownRuntimeEffect` 验证内部键
- 防止键冲突和误用

### Uniform 颜色空间转换

处理 `layout(color)` 修饰的 uniform:
1. **检测**: 遍历 uniform 列表,识别颜色类型
2. **转换**: 应用 `SkColorSpaceXformSteps` 进行颜色空间转换
3. **拷贝**: 如果有颜色 uniform,分配新的 `SkData`;否则返回原数据
4. **优化**: 仅在需要时执行转换,避免不必要的拷贝

### 子效果序列化

序列化格式:
- 写入子效果数量
- 依次序列化每个子效果(着色器/颜色滤镜/混合器)
- 使用 `SkFlattenable` 机制实现多态序列化

反序列化:
- 验证子效果数量与预期匹配
- 依次反序列化并类型检查
- 失败时返回 false,调用者可拒绝使用该效果

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/effects/SkRuntimeEffect.h | 公共 API 定义 |
| src/sksl/SkSLContext.h | SkSL 编译器上下文 |
| src/sksl/ir/SkSLVariable.h | SkSL 变量表示 |
| src/sksl/codegen/SkSLRasterPipelineBuilder.h | 光栅管线代码生成 |
| src/core/SkKnownRuntimeEffects.h | 预定义效果管理 |
| src/core/SkEffectPriv.h | 效果工具函数 |
| include/core/SkColorSpace.h | 颜色空间管理 |
| src/core/SkReadBuffer.h | 反序列化 |
| src/core/SkWriteBuffer.h | 序列化 |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| GPU 后端(Ganesh/Graphite) | 使用私有 API 进行效果编译和绑定 |
| SkRuntimeBlender/Shader/ColorFilter | 实现类使用私有方法 |
| 远程渲染(SkRemote*) | 使用稳定键和序列化功能 |
| SkCanvas/SkPaint | 间接通过公共 API 使用 |

## 设计模式与设计决策

### 友元类模式

通过私有方法限制访问:
- 公共 API 保持简洁
- 内部功能仅对 Skia 内部可见
- 防止用户依赖不稳定的实现细节

### 回调函数模式

`UniformsCallback` 使用 `std::function`:
- 支持 lambda 和函数对象
- 允许捕获上下文信息
- 延迟执行提高灵活性

### 静态工具类设计

`SkRuntimeEffectPriv` 无实例:
- 所有方法为静态
- 无状态,纯粹的函数集合
- 作为 `SkRuntimeEffect` 的"友元命名空间"

### 能力查询模式

`CanDraw` 和 `SupportsConstantOutputForConstantInput`:
- 在使用前检查设备能力
- 避免运行时错误
- 支持优雅降级

### 缓存集成

`SkMakeCachedRuntimeEffect` 函数:
- 封装全局缓存逻辑
- 避免重复编译相同的 SkSL
- 使用 SkSL 字符串作为键

## 性能考量

### 延迟 Uniform 计算

`MakeDeferredShader` 的性能优势:
- 避免在不需要时计算 uniform
- 支持跨线程共享着色器对象
- 颜色空间转换仅在实际绘制时执行

### 全局效果缓存

`SkMakeCachedRuntimeEffect` 缓存策略:
- 使用字符串哈希作为键
- 线程安全的全局缓存
- 避免重复的 SkSL 解析和编译

### Uniform 转换优化

`TransformUniforms` 优化:
- 仅在存在颜色 uniform 时分配新内存
- 无颜色 uniform 时直接返回原数据
- 减少不必要的拷贝和转换

### 内联回调

`RuntimeEffectRPCallbacks` 方法设计为可内联:
- 减少虚函数调用开销
- 编译器可优化调用栈
- 提高光栅管线执行效率

### 序列化缓冲复用

子效果序列化复用 `SkWriteBuffer`:
- 避免多次内存分配
- 批量写入提高 I/O 效率
- 与 Skia 序列化框架一致

## 相关文件

| 文件 | 关系 |
|------|------|
| include/effects/SkRuntimeEffect.h | 公共 API 定义 |
| src/core/SkRuntimeEffect.cpp | 运行时效果实现 |
| src/core/SkKnownRuntimeEffects.h | 预定义效果管理 |
| src/sksl/SkSLCompiler.h | SkSL 编译器 |
| src/gpu/ganesh/GrFragmentProcessor.h | Ganesh 片段处理器 |
| src/gpu/graphite/RuntimeEffectDictionary.h | Graphite 效果字典 |
| src/shaders/SkRuntimeShader.cpp | 运行时着色器实现 |
| src/core/SkColorSpaceXformSteps.h | 颜色空间转换 |
