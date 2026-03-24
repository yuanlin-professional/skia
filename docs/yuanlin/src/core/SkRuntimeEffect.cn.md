# SkRuntimeEffect

> 源文件
> - src/core/SkRuntimeEffect.cpp

## 概述

`SkRuntimeEffect` 是 Skia 的动态着色语言 (SkSL) 运行时系统的核心实现。它允许在运行时编译和执行自定义的 SkSL 着色器、颜色滤镜和混合器。该模块负责 SkSL 源码编译、Uniform 变量管理、子效果 (child effects) 绑定、光栅化管线 (Raster Pipeline) 代码生成,以及序列化支持。SkRuntimeEffect 是 Skia 高级特效系统的基石,为开发者提供了 GPU 级别的自定义渲染能力。

## 架构位置

`SkRuntimeEffect` 位于 Skia 核心渲染管线的效果层:
- **使用者**: SkRuntimeShader, SkRuntimeColorFilter, SkRuntimeBlender, SkImageFilters
- **依赖**: SkSL 编译器, SkRasterPipeline, SkCapabilities
- **层级**: 高层效果 API 与底层 SkSL 引擎之间的桥梁

## 主要类与结构体

### SkRuntimeEffect

编译后的 SkSL 程序及其元数据。

**继承关系**:
```
SkRefCnt
  └── SkRuntimeEffect
```

**关键成员变量**:

| 变量 | 类型 | 说明 |
|------|------|------|
| fHash | uint32_t | 源码和选项的哈希值 (用于缓存) |
| fStableKey | uint32_t | 稳定键 (预定义效果标识) |
| fName | std::string_view | 效果名称 (调试用) |
| fBaseProgram | std::unique_ptr&lt;SkSL::Program&gt; | 编译后的 SkSL 程序 |
| fMain | const SkSL::FunctionDefinition& | main 函数定义引用 |
| fUniforms | std::vector&lt;Uniform&gt; | Uniform 变量列表 |
| fChildren | std::vector&lt;Child&gt; | 子效果列表 |
| fSampleUsages | std::vector&lt;SkSL::SampleUsage&gt; | 采样模式分析结果 |
| fFlags | uint32_t | 能力标志 (着色器/颜色滤镜/混合器) |
| fRPProgram | std::unique_ptr&lt;SkSL::RP::Program&gt; | 光栅化管线程序 (延迟编译) |
| fCompileRPProgramOnce | SkOnce | 确保 RP 程序仅编译一次 |

### SkRuntimeEffect::Uniform

Uniform 变量描述符。

**关键成员变量**:

| 变量 | 类型 | 说明 |
|------|------|------|
| name | std::string | 变量名 |
| type | Type | 数据类型 (float, float2, float3, float4, matrix, int, ...) |
| count | int | 数组元素数量 (1 = 非数组) |
| offset | size_t | 在 Uniform 缓冲区中的字节偏移 |
| flags | Flags | 标志 (kArray_Flag, kColor_Flag, kHalfPrecision_Flag) |

**Type 枚举**:
```cpp
enum class Type {
    kFloat, kFloat2, kFloat3, kFloat4,
    kFloat2x2, kFloat3x3, kFloat4x4,
    kInt, kInt2, kInt3, kInt4
};
```

### SkRuntimeEffect::Child

子效果描述符。

**关键成员变量**:

| 变量 | 类型 | 说明 |
|------|------|------|
| name | std::string | 变量名 |
| type | ChildType | 效果类型 (shader/colorfilter/blender) |
| index | int | 在子效果数组中的索引 |

### SkRuntimeEffect::ChildPtr

子效果智能指针包装器。

**支持类型**:
- `SkShader`
- `SkColorFilter`
- `SkBlender`

## 公共 API 函数

### 静态工厂方法

```cpp
static Result MakeForShader(SkString sksl, const Options& options)
static Result MakeForColorFilter(SkString sksl, const Options& options)
static Result MakeForBlender(SkString sksl, const Options& options)
```

编译 SkSL 源码创建对应类型的 SkRuntimeEffect。

**Result 结构**:
```cpp
struct Result {
    sk_sp<SkRuntimeEffect> effect;
    SkString errorText;
};
```

### 创建实例

```cpp
sk_sp<SkShader> makeShader(sk_sp<const SkData> uniforms,
                           SkSpan<const ChildPtr> children,
                           const SkMatrix* localMatrix = nullptr) const
```

从效果创建着色器实例。

```cpp
sk_sp<SkColorFilter> makeColorFilter(sk_sp<const SkData> uniforms,
                                     SkSpan<const ChildPtr> children) const
```

创建颜色滤镜实例。

```cpp
sk_sp<SkBlender> makeBlender(sk_sp<const SkData> uniforms,
                             SkSpan<const ChildPtr> children) const
```

创建混合器实例。

### 元数据查询

```cpp
const std::string& source() const               // 获取 SkSL 源码
size_t uniformSize() const                      // Uniform 数据总大小
SkSpan<const Uniform> uniforms() const          // Uniform 列表
SkSpan<const Child> children() const            // 子效果列表
const Uniform* findUniform(std::string_view name) const
const Child* findChild(std::string_view name) const
```

### 能力查询

```cpp
bool allowShader() const       // 是否可作为着色器
bool allowColorFilter() const  // 是否可作为颜色滤镜
bool allowBlender() const      // 是否可作为混合器
```

### 调试和优化

```cpp
sk_sp<SkRuntimeEffect> makeUnoptimizedClone()   // 创建未优化副本 (用于调试)
static TracedShader MakeTraced(sk_sp<SkShader> shader, const SkIPoint& traceCoord)
```

## 内部实现细节

### MakeFromSource 编译流程

```cpp
Result MakeFromSource(SkString sksl, const Options& options, SkSL::ProgramKind kind)
```

**步骤**:

1. **编译 SkSL**:
```cpp
SkSL::Compiler compiler;
SkSL::ProgramSettings settings = MakeSettings(options);
program = compiler.convertProgram(kind, sksl, settings);
```

2. **查找 main 函数**:
```cpp
const SkSL::FunctionDeclaration* main = program->getFunction("main");
```

3. **分析 sample 坐标使用**:
```cpp
const SkSL::Variable* coordsParam = main->getMainCoordsParameter();
const SkSL::ProgramUsage::VariableCounts usage = program->usage()->get(*coordsParam);
```

4. **设置能力标志**:
```cpp
if (kind == ProgramKind::kRuntimeShader) {
    flags |= kAllowShader_Flag;
}
if (sampleCoordsUsage.fRead || sampleCoordsUsage.fWrite) {
    flags |= kUsesSampleCoords_Flag;
}
if (SkSL::Analysis::ReturnsOpaqueColor(*main->definition())) {
    flags |= kAlwaysOpaque_Flag;
}
```

5. **提取元数据**:
```cpp
for (const SkSL::ProgramElement* elem : program->elements()) {
    if (elem->is<SkSL::GlobalVarDeclaration>()) {
        const SkSL::Variable& var = ...;
        if (var.type().isEffectChild()) {
            children.push_back(VarAsChild(var, children.size()));
        } else if (var.modifierFlags().isUniform()) {
            uniforms.push_back(VarAsUniform(var, ctx, &offset));
        }
    }
}
```

### getRPProgram 延迟编译

```cpp
const SkSL::RP::Program* getRPProgram(SkSL::DebugTracePriv* debugTrace) const
```

**SkOnce 机制**:
```cpp
fCompileRPProgramOnce([&] {
    // 内联优化
    if (!(fFlags & kDisableOptimization_Flag)) {
        compiler.runInliner(*fBaseProgram);
        Transform::EliminateDeadFunctions(*fBaseProgram);
    }
    // 代码生成
    fRPProgram = MakeRasterPipelineProgram(*fBaseProgram, fMain, debugTrace, ...);
});
```

**优点**:
- 避免不必要的编译 (仅 CPU 渲染时需要)
- 线程安全 (SkOnce 保证)

### Uniform 颜色空间转换

```cpp
sk_sp<const SkData> TransformUniforms(SkSpan<const Uniform> uniforms,
                                      sk_sp<const SkData> originalData,
                                      const SkColorSpaceXformSteps& steps)
```

**处理流程**:
```cpp
for (const auto& u : uniforms) {
    if (u.flags & Flags::kColor_Flag) {
        float* color = SkTAddOffset<float>(writableData(), u.offset);
        if (u.type == Type::kFloat4) {
            for (int i = 0; i < u.count; ++i) {
                steps.apply(color);  // RGBA 转换
                color += 4;
            }
        } else {  // Float3
            float rgba[4];
            for (int i = 0; i < u.count; ++i) {
                memcpy(rgba, color, 3 * sizeof(float));
                rgba[3] = 1.0f;
                steps.apply(rgba);
                memcpy(color, rgba, 3 * sizeof(float));
                color += 3;
            }
        }
    }
}
```

### 子效果验证

```cpp
static bool verify_child_effects(const std::vector<Child>& reflected,
                                 SkSpan<const ChildPtr> effectPtrs)
```

**检查项**:
1. 数量匹配: `reflected.size() == effectPtrs.size()`
2. 类型匹配: 每个子效果的类型与声明一致
3. nullptr 允许: 可以传递 null 子效果

### 缓存机制

```cpp
sk_sp<SkRuntimeEffect> SkMakeCachedRuntimeEffect(
    SkRuntimeEffect::Result (*make)(SkString, const Options&),
    SkString sksl)
```

**实现**:
```cpp
static SkLRUCache<uint64_t, sk_sp<SkRuntimeEffect>> cache(11);
uint64_t key = SkChecksum::Hash64(sksl.c_str(), sksl.size());

{
    SkAutoMutexExclusive _(mutex);
    if (sk_sp<SkRuntimeEffect>* found = cache->find(key)) {
        return *found;
    }
}

auto [effect, err] = make(std::move(sksl), options);
cache->insert_or_update(key, effect);
```

### RuntimeEffectRPCallbacks

光栅化管线回调实现,处理子效果采样。

**关键方法**:

```cpp
bool appendShader(int index)          // 采样子着色器
bool appendColorFilter(int index)     // 应用子颜色滤镜
bool appendBlender(int index)         // 应用子混合器
void toLinearSrgb(const void* color)  // 颜色空间转换 to linear sRGB
void fromLinearSrgb(const void* color)  // 颜色空间转换 from linear sRGB
```

**PassThrough 优化**:
```cpp
if (fSampleUsages[index].isPassThrough()) {
    // 保持 total-matrix 有效
    return as_SB(shader)->appendStages(fStage, fMatrix);
} else {
    // 标记 total-matrix 无效
    SkShaders::MatrixRec nonPassthroughMatrix = fMatrix;
    nonPassthroughMatrix.markTotalMatrixInvalid();
    return as_SB(shader)->appendStages(fStage, nonPassthroughMatrix);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkSL::Compiler | SkSL 编译器 |
| SkSL::RP::Program | 光栅化管线程序 |
| SkRasterPipeline | CPU 执行引擎 |
| SkCapabilities | 后端能力查询 |
| SkColorSpaceXformSteps | 颜色空间转换 |
| SkLRUCache | 编译结果缓存 |
| SkChecksum | 哈希计算 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkRuntimeShader | 着色器实现 |
| SkRuntimeColorFilter | 颜色滤镜实现 |
| SkRuntimeBlender | 混合器实现 |
| SkImageFilters | 图像滤镜 |

## 设计模式与设计决策

### 工厂方法模式

```cpp
MakeForShader() / MakeForColorFilter() / MakeForBlender()
```

根据类型创建不同 ProgramKind 的效果。

### 延迟初始化模式

**RP 程序编译**:
- 使用 `SkOnce` 延迟到首次需要
- 避免 GPU 路径的编译开销

### 不可变对象模式

**SkRuntimeEffect 创建后不可修改**:
- 线程安全
- 可共享和缓存

### 桥接模式

**SkRuntimeEffect 作为桥梁**:
- **抽象**: 高层 API (makeShader/makeColorFilter/makeBlender)
- **实现**: 底层 SkSL 编译器和 RasterPipeline

### 设计权衡

1. **编译成本 vs 运行性能**:
   - 编译时内联和优化
   - 缓存编译结果

2. **通用性 vs 安全性**:
   - 限制 SkSL 版本 (colorFilter 仅支持 v100)
   - 验证子效果类型

3. **内存 vs 速度**:
   - 不使用节点池 (`settings.fUseMemoryPool = false`)
   - 长生命周期效果优先节省内存

## 性能考量

### 编译优化

**内联优化**:
```cpp
settings.fInlineThreshold = SkSL::kDefaultInlineThreshold;
compiler.runInliner(*program);
Transform::EliminateDeadFunctions(*program);
```

**优化等级**:
- **forceUnoptimized=false**: 完全优化 (默认)
- **forceUnoptimized=true**: 禁用优化 (调试用)

### 运行时优化

**Uniform 转换**:
- 仅在颜色空间转换需要时复制数据
- 直接返回原始指针 (无转换时)

**子效果采样**:
- PassThrough 模式避免矩阵失效
- null 子效果快速返回默认值

### 缓存策略

**LRU 缓存**:
- 容量: 11 个效果 (经验值)
- 键: 源码哈希
- 线程安全: SkMutex 保护

### 内存效率

**引用计数**:
- SkSL::Program 共享
- 子效果指针共享

**Copy-on-Write**:
- Uniform 数据在转换时才复制

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/effects/SkRuntimeEffect.h | 公共 API 头文件 |
| src/core/SkRuntimeEffectPriv.h | 私有辅助函数 |
| src/shaders/SkRuntimeShader.h | 着色器实现 |
| src/effects/colorfilters/SkRuntimeColorFilter.h | 颜色滤镜实现 |
| src/core/SkRuntimeBlender.h | 混合器实现 |
| src/sksl/SkSLCompiler.h | SkSL 编译器 |
| src/sksl/codegen/SkSLRasterPipelineCodeGenerator.h | RP 代码生成 |
| src/core/SkKnownRuntimeEffects.h | 预定义效果 |
| src/core/SkLRUCache.h | LRU 缓存 |
