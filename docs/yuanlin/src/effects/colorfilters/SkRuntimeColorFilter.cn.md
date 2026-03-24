# SkRuntimeColorFilter

> 源文件
> - `src/effects/colorfilters/SkRuntimeColorFilter.h`
> - `src/effects/colorfilters/SkRuntimeColorFilter.cpp`

## 概述

`SkRuntimeColorFilter` 是 Skia 中实现运行时可编程颜色过滤器的类。它基于 `SkRuntimeEffect` 框架，允许用户使用 SkSL（Skia 着色语言）编写自定义的颜色变换逻辑。这提供了极大的灵活性，使得开发者可以在运行时创建任意复杂的颜色效果，而无需修改 Skia 源代码。

运行时颜色过滤器由三部分组成：
1. **SkSL 代码**：定义颜色变换的着色器代码
2. **Uniform 数据**：传递给着色器的参数（如调整强度、颜色值等）
3. **子效果**：可以嵌套其他颜色过滤器或着色器

该机制还被 Skia 内部用于实现多个标准颜色过滤器，如 `SkLumaColorFilter`、`SkOverdrawColorFilter` 和颜色过滤器插值（`Lerp`）等。

## 架构位置

```
skia/
├── include/
│   ├── core/
│   │   ├── SkColorFilter.h           # 颜色过滤器公共接口
│   │   └── SkData.h                  # 数据容器
│   └── effects/
│       ├── SkRuntimeEffect.h         # 运行时效果框架
│       ├── SkLumaColorFilter.h       # 亮度过滤器
│       └── SkOverdrawColorFilter.h   # 过度绘制过滤器
├── src/
│   ├── core/
│   │   ├── SkKnownRuntimeEffects.h   # 预定义的运行时效果
│   │   └── SkRuntimeEffectPriv.h     # 运行时效果私有 API
│   ├── sksl/
│   │   └── codegen/
│   │       └── SkSLRasterPipelineBuilder.h  # SkSL 到光栅管线的编译
│   └── effects/
│       └── colorfilters/
│           ├── SkColorFilterBase.h        # 颜色过滤器基类
│           ├── SkRuntimeColorFilter.h     # 本模块头文件
│           └── SkRuntimeColorFilter.cpp   # 本模块实现
```

`SkRuntimeColorFilter` 是 Skia 效果系统中最灵活的颜色过滤器，它桥接了 SkSL 编译器和颜色过滤器框架。

## 主要类与结构体

### SkRuntimeColorFilter

运行时颜色过滤器类。

```cpp
class SkRuntimeColorFilter : public SkColorFilterBase {
public:
    SkRuntimeColorFilter(sk_sp<SkRuntimeEffect> effect,
                         sk_sp<const SkData> uniforms,
                         SkSpan<const SkRuntimeEffect::ChildPtr> children);

    bool appendStages(const SkStageRec& rec, bool) const override;
    bool onIsAlphaUnchanged() const override;
    void flatten(SkWriteBuffer& buffer) const override;

    SkRuntimeEffect* asRuntimeEffect() const override;

    SkColorFilterBase::Type type() const override {
        return SkColorFilterBase::Type::kRuntime;
    }

    // 访问器
    sk_sp<SkRuntimeEffect> effect() const { return fEffect; }
    sk_sp<const SkData> uniforms() const { return fUniforms; }
    SkSpan<const SkRuntimeEffect::ChildPtr> children() const { return fChildren; }

private:
    sk_sp<SkRuntimeEffect> fEffect;                    // SkSL 编译后的效果
    sk_sp<const SkData> fUniforms;                     // Uniform 参数数据
    std::vector<SkRuntimeEffect::ChildPtr> fChildren;  // 子效果
};
```

**组件说明**：
- `fEffect` - 包含编译后的 SkSL 代码和元数据
- `fUniforms` - 二进制形式的参数数据（如浮点数、颜色等）
- `fChildren` - 可以引用其他颜色过滤器或着色器

## 公共 API 函数

### SkRuntimeEffect::makeColorFilter

```cpp
sk_sp<SkColorFilter> SkRuntimeEffect::makeColorFilter(
    sk_sp<const SkData> uniforms,
    SkSpan<const ChildPtr> children = {});
```

使用运行时效果创建颜色过滤器。

**参数**：
- `uniforms` - Uniform 参数数据
- `children` - 子效果数组

**返回值**：颜色过滤器智能指针

**使用示例**：
```cpp
// SkSL 代码：增强对比度
const char* sksl = R"(
    uniform float contrast;

    half4 main(half4 color) {
        color.rgb = (color.rgb - 0.5) * contrast + 0.5;
        return color;
    }
)";

auto effect = SkRuntimeEffect::MakeForColorFilter(SkString(sksl)).effect;
float contrast = 1.5f;
auto uniforms = SkData::MakeWithCopy(&contrast, sizeof(contrast));
auto filter = effect->makeColorFilter(uniforms);
```

### SkColorFilters::Lerp

```cpp
sk_sp<SkColorFilter> SkColorFilters::Lerp(
    float weight,
    sk_sp<SkColorFilter> cf0,
    sk_sp<SkColorFilter> cf1);
```

创建两个颜色过滤器之间的线性插值过滤器。

**参数**：
- `weight` - 插值权重（0.0 = cf0, 1.0 = cf1）
- `cf0` - 第一个颜色过滤器
- `cf1` - 第二个颜色过滤器

**返回值**：插值后的颜色过滤器

**特殊处理**：
- `weight <= 0`：返回 cf0
- `weight >= 1`：返回 cf1
- `cf0 == cf1`：返回 cf0
- `isNaN(weight)`：返回 nullptr

### SkLumaColorFilter::Make

```cpp
sk_sp<SkColorFilter> SkLumaColorFilter::Make();
```

创建亮度颜色过滤器，将颜色转换为其亮度值（灰度）。

**实现**：使用预定义的运行时效果 `StableKey::kLuma`

### SkOverdrawColorFilter::MakeWithSkColors

```cpp
sk_sp<SkColorFilter> SkOverdrawColorFilter::MakeWithSkColors(
    const SkColor colors[kNumColors]);
```

创建过度绘制可视化颜色过滤器，用于调试渲染性能。

**参数**：
- `colors` - 6 个颜色值，分别对应不同的过度绘制层数

**实现**：使用预定义的运行时效果 `StableKey::kOverdraw`

## 内部实现细节

### 构造函数

```cpp
SkRuntimeColorFilter::SkRuntimeColorFilter(
    sk_sp<SkRuntimeEffect> effect,
    sk_sp<const SkData> uniforms,
    SkSpan<const SkRuntimeEffect::ChildPtr> children)
        : fEffect(std::move(effect))
        , fUniforms(std::move(uniforms))
        , fChildren(children.begin(), children.end()) {}
```

**设计要点**：
- 使用移动语义避免不必要的引用计数操作
- `fChildren` 从 span 复制到 vector 以拥有数据

### 管线构建

```cpp
bool SkRuntimeColorFilter::appendStages(const SkStageRec& rec, bool) const {
    // 1. 检查是否可以在 SkRP 后端执行
    if (!SkRuntimeEffectPriv::CanDraw(SkCapabilities::RasterBackend().get(),
                                     fEffect.get())) {
        return false;  // 不支持某些高级 SkSL 特性
    }

    // 2. 获取编译后的光栅管线程序
    if (const SkSL::RP::Program* program = fEffect->getRPProgram(nullptr)) {
        // 3. 准备 uniform 数据
        SkSpan<const float> uniforms =
                SkRuntimeEffectPriv::UniformsAsSpan(fEffect->uniforms(),
                                                    fUniforms,
                                                    false,
                                                    rec.fDstCS,
                                                    rec.fAlloc);

        // 4. 准备矩阵和子效果回调
        SkShaders::MatrixRec matrix(SkMatrix::I());
        matrix.markCTMApplied();
        RuntimeEffectRPCallbacks callbacks(rec, matrix, fChildren,
                                          fEffect->fSampleUsages);

        // 5. 将 SkSL 程序的阶段追加到管线
        bool success = program->appendStages(rec.fPipeline, rec.fAlloc,
                                            &callbacks, uniforms);
        return success;
    }

    return false;
}
```

**关键步骤**：
1. **能力检查**：确保当前后端支持所需的 SkSL 特性
2. **程序获取**：从效果中获取编译后的光栅管线程序
3. **Uniform 处理**：将二进制数据转换为浮点数 span，处理色彩空间
4. **回调设置**：处理子效果的采样和调用
5. **阶段追加**：将 SkSL 代码转换为的管线阶段添加到执行管线

### Alpha 不变性

```cpp
bool SkRuntimeColorFilter::onIsAlphaUnchanged() const {
    return fEffect->isAlphaUnchanged();
}
```

**机制**：
- 由 SkSL 编译器分析代码确定
- 如果着色器代码不修改 alpha 通道，返回 true
- 用于优化预乘/反预乘操作

### 序列化

```cpp
void SkRuntimeColorFilter::flatten(SkWriteBuffer& buffer) const {
    // 1. 如果是 Skia 内部预定义效果，只序列化稳定键
    if (SkKnownRuntimeEffects::IsSkiaKnownRuntimeEffect(fEffect->fStableKey)) {
        buffer.write32(fEffect->fStableKey);
    } else {
        // 2. 否则序列化完整的 SkSL 源代码
        buffer.write32(0);
        buffer.writeString(fEffect->source().c_str());
    }

    // 3. 序列化 uniform 数据
    buffer.writeDataAsByteArray(fUniforms.get());

    // 4. 序列化子效果
    SkRuntimeEffectPriv::WriteChildEffects(buffer, fChildren);
}
```

**优化策略**：
- 预定义效果只存储稳定键（4 字节）
- 自定义效果存储完整源代码
- 减少序列化大小和反序列化时的编译开销

### 反序列化

```cpp
sk_sp<SkFlattenable> SkRuntimeColorFilter::CreateProc(SkReadBuffer& buffer) {
    // 1. 检查是否允许 SkSL
    if (!buffer.validate(buffer.allowSkSL())) {
        return nullptr;
    }

    sk_sp<SkRuntimeEffect> effect;

    // 2. 尝试读取稳定键
    if (!buffer.isVersionLT(SkPicturePriv::kSerializeStableKeys)) {
        uint32_t candidateStableKey = buffer.readUInt();
        effect = SkKnownRuntimeEffects::MaybeGetKnownRuntimeEffect(candidateStableKey);
        if (!effect && !buffer.validate(candidateStableKey == 0)) {
            return nullptr;
        }
    }

    // 3. 如果没有稳定键，读取并编译 SkSL 源代码
    if (!effect) {
        SkString sksl;
        buffer.readString(&sksl);
        effect = SkMakeCachedRuntimeEffect(SkRuntimeEffect::MakeForColorFilter,
                                          std::move(sksl));
    }

    // 4. 读取 uniforms 和子效果
    sk_sp<SkData> uniforms = buffer.readByteArrayAsData();
    skia_private::STArray<4, SkRuntimeEffect::ChildPtr> children;
    if (!SkRuntimeEffectPriv::ReadChildEffects(buffer, effect.get(), &children)) {
        return nullptr;
    }

    // 5. 创建过滤器
    return effect->makeColorFilter(std::move(uniforms), SkSpan(children));
}
```

**容错机制**：
- 在调试器构建中，SkSL 编译失败时输出警告但不崩溃
- 验证稳定键的有效性
- 支持旧版本的序列化格式

## 依赖关系

### 内部依赖

| 组件 | 用途 |
|-----|------|
| `SkRuntimeEffect` | SkSL 编译和管理 |
| `SkKnownRuntimeEffects` | 预定义的运行时效果 |
| `SkRuntimeEffectPriv` | 运行时效果私有 API |
| `SkSL::RP::Program` | 编译后的光栅管线程序 |
| `SkColorFilterBase` | 颜色过滤器基类 |

### 外部依赖

| 组件 | 用途 |
|-----|------|
| `SkData` | 存储 uniform 数据 |
| `SkReadBuffer` / `SkWriteBuffer` | 序列化支持 |
| `SkCapabilities` | 查询后端能力 |

## 设计模式与设计决策

### 1. 策略模式（Strategy Pattern）

通过 SkSL 代码定义颜色变换策略：
- 不同的 SkSL 代码实现不同的效果
- 运行时可以动态加载新策略
- 策略之间可以通过子效果组合

### 2. 编译器模式（Compiler Pattern）

SkSL 到光栅管线的编译流程：
```
SkSL 源代码 → 解析 → AST → 优化 → SkSL::RP::Program → 光栅管线阶段
```

编译结果被缓存以提高性能。

### 3. 享元模式（Flyweight Pattern）

通过稳定键共享预定义效果：
```cpp
const SkRuntimeEffect* lerpEffect = GetKnownRuntimeEffect(StableKey::kLerp);
```

所有使用相同预定义效果的过滤器共享同一个 `SkRuntimeEffect` 实例。

### 4. 组合模式（Composite Pattern）

通过子效果支持嵌套：
```cpp
std::vector<SkRuntimeEffect::ChildPtr> fChildren;
```

子效果可以是其他颜色过滤器或着色器，形成效果树。

## 性能考量

### 1. SkSL 编译缓存

```cpp
effect = SkMakeCachedRuntimeEffect(SkRuntimeEffect::MakeForColorFilter,
                                  std::move(sksl));
```

**优化**：
- 相同的 SkSL 代码只编译一次
- 编译结果在全局缓存中共享
- 避免重复的昂贵编译操作

### 2. 预定义效果优化

```cpp
if (SkKnownRuntimeEffects::IsSkiaKnownRuntimeEffect(fEffect->fStableKey)) {
    buffer.write32(fEffect->fStableKey);  // 只写入 4 字节
}
```

**优势**：
- 序列化大小极小
- 反序列化时无需编译
- 预定义效果可以有手写的优化实现

### 3. Uniform 数据处理

```cpp
SkSpan<const float> uniforms =
        SkRuntimeEffectPriv::UniformsAsSpan(fEffect->uniforms(),
                                            fUniforms,
                                            false,  // alwaysCopyIntoAlloc
                                            rec.fDstCS,
                                            rec.fAlloc);
```

**优化点**：
- 尽可能直接使用原始数据（避免复制）
- 仅在需要时进行色彩空间转换
- 使用栈分配器减少堆分配

### 4. 能力检查

```cpp
if (!SkRuntimeEffectPriv::CanDraw(SkCapabilities::RasterBackend().get(),
                                 fEffect.get())) {
    return false;
}
```

**早期退出**：
- 避免在不支持的后端上尝试执行
- 防止运行时错误

### 5. 与其他过滤器的比较

| 过滤器类型 | 灵活性 | 性能 | 编译开销 |
|----------|--------|-----|---------|
| `SkMatrixColorFilter` | 低（线性变换） | 非常高 | 无 |
| `SkTableColorFilter` | 中（查找表） | 高 | 无 |
| `SkRuntimeColorFilter` | 极高（任意代码） | 中到高 | 有（首次） |

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/effects/SkRuntimeEffect.h` | 运行时效果公共接口 |
| `src/core/SkKnownRuntimeEffects.h` | 预定义的运行时效果 |
| `src/sksl/codegen/SkSLRasterPipelineBuilder.h` | SkSL 编译器 |
| `include/effects/SkLumaColorFilter.h` | 亮度过滤器（使用运行时效果） |
| `include/effects/SkOverdrawColorFilter.h` | 过度绘制过滤器 |
| `src/effects/colorfilters/SkColorFilterBase.h` | 颜色过滤器基类 |
| `src/core/SkRuntimeEffectPriv.h` | 运行时效果私有 API |
| `src/core/SkCapabilities.h` | 后端能力查询 |
