# PrecompileRuntimeEffect

> 源文件
> - include/gpu/graphite/precompile/PrecompileRuntimeEffect.h
> - src/gpu/graphite/precompile/PrecompileRuntimeEffect.cpp

## 概述

`PrecompileRuntimeEffect` 提供了对 Skia 运行时效果（Runtime Effect）的预编译支持。运行时效果允许开发者使用 SkSL 着色语言编写自定义着色器、颜色滤镜和混合器，极大扩展了 Skia 的渲染能力。PrecompileRuntimeEffect 通过工厂函数接受 `SkRuntimeEffect` 对象和子效果选项，生成对应的预编译对象。

该模块的核心是 `PrecompileRTEffect` 模板类，它能够针对着色器、颜色滤镜和混合器三种类型生成统一的预编译实现。运行时效果的 uniform 值在预编译阶段被抽象掉，只关注子效果的组合结构。

## 架构位置

```
skgpu::graphite
├── precompile/
│   ├── PrecompileBase (基类)
│   ├── PrecompileRuntimeEffect (当前组件)
│   ├── PrecompileShader
│   ├── PrecompileColorFilter
│   └── PrecompileBlender
├── KeyContext (密钥上下文)
├── RuntimeEffectBlock (运行时效果代码块)
└── PaintParamsKey (绘制参数密钥)
```

PrecompileRuntimeEffect 是 Skia 预编译系统的扩展点，允许自定义效果无缝集成到预编译管线中。它使用相同的密钥生成机制，确保自定义效果和内置效果的一致性。

## 主要类与结构体

### PrecompileRTEffect&lt;T&gt;

**继承关系**
- 模板参数 T: `PrecompileShader`、`PrecompileColorFilter` 或 `PrecompileBlender`
- 基类: T（即对应的预编译类型）

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fEffect | sk_sp&lt;SkRuntimeEffect&gt; | 运行时效果对象 |
| fChildOptions | std::vector&lt;std::vector&lt;sk_sp&lt;PrecompileBase&gt;&gt;&gt; | 子效果选项的二维数组 |
| fNumSlotCombinations | TArray&lt;int&gt; | 每个子效果槽位的组合数 |
| fNumChildCombinations | int | 所有子效果组合的总数（笛卡尔积） |

PrecompileRTEffect 是一个模板类，通过 CRTP（奇异递归模板模式）的变体实现代码复用，同时保持类型安全。

### PrecompileChildOptions

```cpp
using PrecompileChildOptions = SkSpan<const sk_sp<PrecompileBase>>;
```

PrecompileChildOptions 是一个类型别名，表示单个子效果槽位的所有可能选项。使用 SkSpan 避免不必要的容器分配。

## 公共 API 函数

### PrecompileRuntimeEffects 命名空间工厂函数

```cpp
sk_sp<PrecompileShader> MakePrecompileShader(
    sk_sp<SkRuntimeEffect> effect,
    SkSpan<const PrecompileChildOptions> childOptions = {});
```
创建运行时效果着色器的预编译对象。参数：
- `effect`: SkRuntimeEffect 对象，必须允许作为着色器使用（allowShader()）
- `childOptions`: 每个子效果槽位的选项列表，数量必须匹配 effect->children().size()

返回 nullptr 如果效果无效或子选项不匹配。

```cpp
sk_sp<PrecompileColorFilter> MakePrecompileColorFilter(
    sk_sp<SkRuntimeEffect> effect,
    SkSpan<const PrecompileChildOptions> childOptions = {});
```
创建运行时效果颜色滤镜的预编译对象。要求 effect->allowColorFilter() 为 true。

```cpp
sk_sp<PrecompileBlender> MakePrecompileBlender(
    sk_sp<SkRuntimeEffect> effect,
    SkSpan<const PrecompileChildOptions> childOptions = {});
```
创建运行时效果混合器的预编译对象。要求 effect->allowBlender() 为 true。

## 内部实现细节

### 子效果验证

在创建预编译对象前，需要验证提供的子效果选项与运行时效果定义匹配：

```cpp
bool children_are_valid(SkRuntimeEffect* effect,
                        SkSpan<const PrecompileChildOptions> childOptions) {
    SkSpan<const SkRuntimeEffect::Child> childInfo = effect->children();
    if (childOptions.size() != childInfo.size()) {
        return false;  // 数量不匹配
    }

    for (size_t i = 0; i < childInfo.size(); ++i) {
        const PrecompileBase::Type expectedType = to_precompile_type(childInfo[i].type);
        for (const sk_sp<PrecompileBase>& childOption : childOptions[i]) {
            if (childOption && expectedType != childOption->type()) {
                return false;  // 类型不匹配
            }
        }
    }
    return true;
}
```

类型转换映射：
```cpp
PrecompileBase::Type to_precompile_type(SkRuntimeEffect::ChildType childType) {
    switch(childType) {
        case SkRuntimeEffect::ChildType::kShader:      return PrecompileBase::Type::kShader;
        case SkRuntimeEffect::ChildType::kColorFilter: return PrecompileBase::Type::kColorFilter;
        case SkRuntimeEffect::ChildType::kBlender:     return PrecompileBase::Type::kBlender;
    }
}
```

### 组合数量计算

```cpp
int num_options_in_set(const SkSpan<const sk_sp<PrecompileBase>>& optionSet) {
    int numOptions = 0;
    for (const sk_sp<PrecompileBase>& childOption : optionSet) {
        if (childOption) {
            numOptions += childOption->priv().numCombinations();
        } else {
            ++numOptions;  // nullptr 代表一个 passthrough 选项
        }
    }
    return numOptions;
}
```

总组合数是所有槽位组合数的乘积：
```cpp
fNumChildCombinations = 1;
for (const std::vector<sk_sp<PrecompileBase>>& optionSet : fChildOptions) {
    fNumSlotCombinations.push_back(num_options_in_set(optionSet));
    fNumChildCombinations *= fNumSlotCombinations.back();
}
```

**示例**: 如果一个运行时效果有 2 个子效果槽位：
- 第一个槽位有 3 个选项（每个选项 1 个组合）→ 3 个组合
- 第二个槽位有 2 个选项（一个 2 个组合，一个 1 个组合）→ 3 个组合
- 总组合数 = 3 × 3 = 9

### 组合索引解码

`addToKey` 方法需要将单个 desiredCombination 索引解码为每个槽位的具体选项：

```cpp
int remainingCombinations = desiredCombination;

for (size_t rowIndex = 0; rowIndex < fChildOptions.size(); ++rowIndex) {
    int numSlotCombinations = fNumSlotCombinations[rowIndex];

    // 当前槽位的选项索引
    const int slotOption = remainingCombinations % numSlotCombinations;
    remainingCombinations /= numSlotCombinations;

    // 选择具体的子效果和其组合索引
    auto [option, childOptions] = PrecompileBase::SelectOption(
        SkSpan(fChildOptions[rowIndex]), slotOption);

    // ... 处理选中的子效果
}
```

这是一个标准的进制转换算法，将一维索引映射到多维空间。

### 密钥生成流程

```cpp
void addToKey(const KeyContext& keyContext, int desiredCombination) const override {
    SkSpan<const SkRuntimeEffect::Child> childInfo = fEffect->children();

    if (!RuntimeEffectBlock::BeginBlock(keyContext, { fEffect })) {
        RuntimeEffectBlock::AddNoOpEffect(keyContext, fEffect.get());
        return;
    }

    // 解码并处理每个子效果
    for (size_t rowIndex = 0; rowIndex < fChildOptions.size(); ++rowIndex) {
        auto [option, childOptions] = SelectOption(...);
        KeyContext childContext = keyContext.forRuntimeEffect(fEffect.get(), rowIndex);

        if (option) {
            option->priv().addToKey(childContext, childOptions);
        } else {
            // 添加 no-op 替代
            AddNoOpChild(childContext, childInfo[rowIndex].type);
        }
    }

    RuntimeEffectBlock::HandleIntrinsics(keyContext, fEffect.get());
    keyContext.paintParamsKeyBuilder()->endBlock();
}
```

### 缺失子效果的处理

当子效果选项为 nullptr 时，需要插入默认的"无操作"效果：

```cpp
switch (childInfo[rowIndex].type) {
    case SkRuntimeEffect::ChildType::kShader:
        // 返回透明黑色
        SolidColorShaderBlock::AddBlock(childContext, SK_PMColor4fTRANSPARENT);
        break;

    case SkRuntimeEffect::ChildType::kColorFilter:
        // 直通，返回输入颜色
        keyContext.paintParamsKeyBuilder()->addBlock(
            BuiltInCodeSnippetID::kPriorOutput);
        break;

    case SkRuntimeEffect::ChildType::kBlender:
        // 默认 SrcOver 混合
        AddFixedBlendMode(childContext, SkBlendMode::kSrcOver);
        break;
}
```

这些默认行为与运行时 SkRuntimeEffect 的行为一致。

### 内置函数处理

运行时效果可能使用 Skia 的内置函数（intrinsics），这些需要特殊处理：

```cpp
RuntimeEffectBlock::HandleIntrinsics(keyContext, fEffect.get());
```

内置函数可能包括：
- 颜色空间转换
- 矩阵变换
- 特殊数学函数

具体处理逻辑在 RuntimeEffectBlock 中实现。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| PrecompileBase | 基类，提供预编译接口 |
| PrecompileShader | 着色器预编译类型 |
| PrecompileColorFilter | 颜色滤镜预编译类型 |
| PrecompileBlender | 混合器预编译类型 |
| SkRuntimeEffect | 运行时效果定义 |
| SkRuntimeEffectPriv | 运行时效果私有接口 |
| KeyContext | 密钥生成上下文 |
| RuntimeEffectBlock | 运行时效果代码块 |
| PaintParamsKey | 绘制参数密钥 |
| BuiltInCodeSnippetID | 内置代码片段 ID |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| PaintOptions | 可以包含运行时效果着色器/颜色滤镜/混合器 |
| 用户代码 | 通过公共 API 创建自定义效果的预编译对象 |

## 设计模式与设计决策

### 模板方法模式 (Template Method Pattern)

PrecompileRTEffect 通过模板参数 T 实现多态，避免虚函数开销：
```cpp
template<typename T>
class PrecompileRTEffect : public T {
    // 统一实现，T 可以是 PrecompileShader/ColorFilter/Blender
};
```

### 策略模式 (Strategy Pattern)

通过子效果选项列表，允许用户指定不同的组合策略。每个槽位可以有多个选项，系统会生成笛卡尔积。

### 类型安全设计

使用类型别名和验证函数确保编译时和运行时类型安全：
```cpp
using PrecompileChildOptions = SkSpan<const sk_sp<PrecompileBase>>;

bool children_are_valid(...) {
    // 验证类型匹配
}
```

### 设计决策

1. **抽象 Uniform 值**: 预编译阶段完全忽略 uniform 值，因为它们不影响着色器代码结构。这大大简化了 API 和实现。

2. **支持 nullptr 子效果**: 允许子效果选项为 nullptr，代表使用默认行为。这与运行时 API 一致，且简化了用户代码。

3. **统一的工厂接口**: 三个工厂函数（Shader、ColorFilter、Blender）提供一致的 API，只是类型不同。内部使用同一个模板类实现。

4. **严格的验证**: 在创建预编译对象时进行严格的子效果验证，早期发现错误，避免后续难以调试的问题。

5. **笛卡尔积组合**: 自动生成所有子效果组合的笛卡尔积，用户不需要手动枚举每个组合。这是预编译系统的核心优势。

6. **内置函数支持**: 通过 HandleIntrinsics 正确处理运行时效果使用的 Skia 内置函数，确保生成的着色器代码完整。

7. **KeyContext 传播**: 为每个子效果创建专门的 KeyContext（通过 forRuntimeEffect），确保子效果代码生成在正确的上下文中。

## 性能考量

### 组合爆炸控制

用户需要谨慎选择子效果选项数量，因为总组合数是乘法关系。例如：
- 4 个槽位，每个 3 个选项 → 81 个组合
- 3 个槽位，一个 2 选项，两个 3 选项 → 18 个组合

建议只包含实际需要的选项。

### 内存占用

- fChildOptions 使用嵌套 vector，对于大量选项可能有一定内存开销
- fNumSlotCombinations 使用 TArray，小规模时栈分配

### 编译时间

运行时效果的编译时间取决于：
- SkSL 代码复杂度
- 子效果数量和复杂度
- 内置函数使用情况

复杂的运行时效果可能显著增加总编译时间。

### 缓存效率

RuntimeEffectBlock 可能会缓存运行时效果的编译结果，减少重复编译开销。具体实现在 RuntimeEffectBlock 中。

### 调试支持

在 SK_DEBUG 模式下，有额外的验证检查：
```cpp
#ifdef SK_DEBUG
bool precompilebase_is_valid_as_child(const PrecompileBase *child) {
    // 验证子效果类型有效性
}
#endif
```

这有助于开发时发现问题，但在发布版本中被移除以提高性能。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/gpu/graphite/precompile/PrecompileRuntimeEffect.h | 公共头文件 |
| src/gpu/graphite/precompile/PrecompileRuntimeEffect.cpp | 实现文件 |
| include/effects/SkRuntimeEffect.h | 对应的运行时 API |
| src/core/SkRuntimeEffectPriv.h | 运行时效果私有接口 |
| src/gpu/graphite/RuntimeEffectBlock.h | 运行时效果代码块 |
| src/gpu/graphite/KeyHelpers.h | 密钥构建辅助函数 |
| include/gpu/graphite/precompile/PrecompileBase.h | 预编译基类 |
