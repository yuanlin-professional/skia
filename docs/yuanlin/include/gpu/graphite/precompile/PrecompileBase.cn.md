# PrecompileBase

> 源文件: `include/gpu/graphite/precompile/PrecompileBase.h`

## 概述
PrecompileBase 是 Skia Graphite 预编译系统中所有可附加到 `PaintOptions` 的对象的抽象基类。它定义了着色器、颜色滤镜、图像滤镜、遮罩滤镜和混合器的统一接口,通过组合模式管理预编译配置的复杂性,支持递归计算配置组合数。

## 架构位置
该文件位于 Skia Graphite GPU 后端的预编译系统核心层,属于 `skgpu::graphite` 命名空间。它是所有预编译对象的基类,位于类型层次结构的顶端,为 `PrecompileShader`、`PrecompileColorFilter` 等派生类提供公共接口。

## 主要类与结构体

### PrecompileBase
所有预编译对象的抽象基类,使用引用计数管理生命周期。

**继承关系**: `SkRefCnt` → `PrecompileBase` → 派生类 (如 PrecompileShader)

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fType | Type | 对象类型标识 (私有成员) |

**类型枚举 Type**:
```cpp
enum class Type {
    kBlender,      // 混合器 (如自定义混合模式)
    kColorFilter,  // 颜色滤镜 (如色调调整)
    kImageFilter,  // 图像滤镜 (如模糊、阴影)
    kMaskFilter,   // 遮罩滤镜 (如模糊边缘)
    kShader,       // 着色器 (如渐变、图像)
};
```

## 公共 API 函数

### `type()`
```cpp
Type type() const { return fType; }
```
- **功能**: 获取预编译对象的类型标识
- **返回值**: Type 枚举值
- **用途**: 运行时类型识别 (RTTI),用于安全的向下转型

### `priv()`
```cpp
PrecompileBasePriv priv();
const PrecompileBasePriv priv() const;
```
- **功能**: 提供访问私有 API 的友元接口
- **返回值**: `PrecompileBasePriv` 辅助类实例
- **用途**: 为内部实现提供额外功能,不暴露给公共 API
- **注意**: 第二个重载标记为 `NOLINT(readability-const-return-type)`,忽略"按值返回 const" 的警告

## 保护成员函数 (派生类接口)

### 构造函数
```cpp
protected:
    PrecompileBase(Type type) : fType(type) {}
```
- **功能**: 受保护的构造函数,初始化类型标识
- **参数**: `type` - 派生类的类型枚举值
- **设计**: 防止直接实例化基类,强制通过派生类创建

### `numIntrinsicCombinations()`
```cpp
virtual int numIntrinsicCombinations() const { return 1; }
```
- **功能**: 返回对象自身的配置组合数 (不包括子对象)
- **默认值**: 1 (单一配置)
- **示例**:
  - 固定颜色着色器: 1
  - 线性/径向渐变选项: 2

### `numChildCombinations()`
```cpp
virtual int numChildCombinations() const { return 1; }
```
- **功能**: 返回所有子对象的配置组合数乘积
- **默认值**: 1 (无子对象或固定子对象)
- **计算**: `child1.numCombinations() × child2.numCombinations() × ...`

### `numCombinations()`
```cpp
int numCombinations() const {
    return this->numIntrinsicCombinations() * this->numChildCombinations();
}
```
- **功能**: 计算对象及其所有子对象的总配置组合数
- **公式**: 本体组合数 × 子对象组合数
- **用途**: 预编译前估算需要生成的管线数量

### `addToKey()`
```cpp
virtual void addToKey(const KeyContext&, int desiredCombination) const = 0;
```
- **功能**: 将指定组合的配置添加到管线键 (Pipeline Key)
- **参数**:
  - `KeyContext`: 键构建上下文,包含设备能力等信息
  - `desiredCombination`: 目标组合索引 (0 到 `numCombinations()-1`)
- **职责**: 纯虚函数,派生类必须实现具体的键生成逻辑

### 辅助模板方法

#### `SelectOption`
```cpp
template<typename T>
static std::pair<sk_sp<T>, int> SelectOption(
    SkSpan<const sk_sp<T>> options,
    int desiredOption);
```
- **功能**: 从选项数组中选择指定索引的对象及其嵌套组合索引
- **返回值**: `{选中的对象, 该对象内的组合索引}`
- **示例**:
  ```cpp
  // 假设 options = [A(3组合), B(2组合), C(1组合)]
  // desiredOption = 4 时:
  // 返回 {B, 1} (跳过 A 的 3 个组合,B 的第 2 个组合)
  ```

#### `AddToKey`
```cpp
template<typename T>
static void AddToKey(
    const KeyContext& context,
    SkSpan<const sk_sp<T>> options,
    int desiredOption);
```
- **功能**: 选择对象后调用其 `addToKey` 方法添加到键
- **参数**:
  - `context`: 键构建上下文
  - `options`: 候选选项数组
  - `desiredOption`: 全局组合索引
- **流程**:
  1. 调用 `SelectOption` 选择对象和嵌套索引
  2. 调用 `object->addToKey(context, nestedIndex)`

## 内部实现细节

### 组合索引映射
组合索引到具体配置的映射算法 (伪代码):
```cpp
int SelectOption(options, desiredOption):
    remainingIndex = desiredOption
    for (option : options):
        numCombos = option->numCombinations()
        if (remainingIndex < numCombos):
            return {option, remainingIndex}
        remainingIndex -= numCombos
    // 超出范围,返回最后一个
    return {options.back(), 0}
```

### 递归组合计算
对于嵌套对象 (如带滤镜的着色器):
```cpp
// 着色器有 2 种变体,每种配合 3 种颜色滤镜
PrecompileShader:
    numIntrinsicCombinations() = 2      // 渐变类型
    numChildCombinations() = 3          // 颜色滤镜选项
    numCombinations() = 2 × 3 = 6       // 总组合
```

### 友元访问模式
`PrecompileBasePriv` 类作为友元提供受保护成员的访问:
```cpp
class PrecompileBasePriv {
    explicit PrecompileBasePriv(PrecompileBase* base) : fBase(base) {}
    int numCombinations() const { return fBase->numCombinations(); }
private:
    PrecompileBase* fBase;
    friend class PrecompileBase;
};
```

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkRefCnt.h | 引用计数基类 |
| include/core/SkSpan.h | 轻量级数组视图 |
| KeyContext (前向声明) | 管线键构建上下文 |
| PaintParamsKeyBuilder (前向声明) | 键构建器 |

### 被依赖的模块
- `PrecompileShader`: 着色器预编译
- `PrecompileColorFilter`: 颜色滤镜预编译
- `PrecompileImageFilter`: 图像滤镜预编译
- `PrecompileMaskFilter`: 遮罩滤镜预编译
- `PrecompileBlender`: 混合器预编译
- `PaintOptions`: 管理多个预编译对象的组合

## 设计模式与设计决策

### 组合模式 (Composite Pattern)
`PrecompileBase` 使用组合模式管理嵌套结构:
- **叶子节点**: 简单对象 (如纯色着色器),`numChildCombinations() = 1`
- **组合节点**: 复杂对象 (如带滤镜的着色器),递归计算子节点组合
- **统一接口**: `numCombinations()` 对所有节点一致

### 模板方法模式 (Template Method)
`numCombinations()` 定义算法骨架:
```cpp
int numCombinations() const {
    return numIntrinsicCombinations() * numChildCombinations();
}
```
派生类重写 `numIntrinsicCombinations` 和 `numChildCombinations` 定制行为。

### 策略模式 (Strategy Pattern)
不同的 `Type` 代表不同的预编译策略:
- `kShader`: 着色器生成策略
- `kColorFilter`: 颜色变换策略
- `kBlender`: 混合策略

### 类型安全的向下转型
通过 `type()` 方法实现安全的类型转换:
```cpp
if (base->type() == PrecompileBase::Type::kShader) {
    auto* shader = static_cast<PrecompileShader*>(base.get());
}
```

## 性能考量

### 组合数爆炸控制
对于复杂的绘制配置,组合数可能指数增长:
```
PaintOptions:
    shaders: 5 种 (每种 3 个组合) = 15
    colorFilters: 4 种 (每种 2 个组合) = 8
    blendModes: 3 种 = 3
    总组合 = 15 × 8 × 3 = 360
```

**缓解策略**:
- 选择性预编译: 只组合常用配置
- 延迟计算: 按需生成组合,而非提前枚举
- 缓存命中: 相同键的管线复用

### 虚函数开销
所有核心方法都是虚函数:
- **运行时开销**: 虚函数调用比直接调用慢 5-10%
- **可接受性**: 预编译在后台执行,开销相对 GPU 编译可忽略
- **替代方案**: 模板特化 (会增加代码复杂度)

### 内存效率
使用 `SkSpan` 而非 `std::vector`:
- 避免不必要的拷贝
- 轻量级视图,仅存储指针和大小
- 支持栈数组和堆数组

## 使用示例

### 实现自定义预编译对象
```cpp
class PrecompileCustomShader : public PrecompileBase {
public:
    PrecompileCustomShader()
        : PrecompileBase(Type::kShader)
        , fVariants({createVariant1(), createVariant2()}) {}

protected:
    int numIntrinsicCombinations() const override {
        return fVariants.size();  // 2 种变体
    }

    int numChildCombinations() const override {
        // 假设每个变体有不同的子着色器
        int total = 1;
        for (const auto& child : fChildren) {
            total *= child->numCombinations();
        }
        return total;
    }

    void addToKey(const KeyContext& context, int desiredCombination) const override {
        // 分解组合索引
        int intrinsic = desiredCombination % numIntrinsicCombinations();
        int child = desiredCombination / numIntrinsicCombinations();

        // 添加本体键
        context.keyBuilder()->addInt(fVariants[intrinsic].id());

        // 添加子对象键
        AddToKey(context, SkSpan(fChildren), child);
    }

private:
    std::vector<Variant> fVariants;
    std::vector<sk_sp<PrecompileBase>> fChildren;
};
```

### 遍历所有组合
```cpp
void enumerateCombinations(const PrecompileBase* base) {
    int total = base->priv().numCombinations();
    for (int i = 0; i < total; ++i) {
        KeyContext context = /* ... */;
        base->priv().addToKey(context, i);
        // 使用生成的键创建管线
    }
}
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/graphite/precompile/Precompile.h | 顶层预编译 API |
| include/gpu/graphite/precompile/PaintOptions.h | 使用 PrecompileBase 组合配置 |
| src/gpu/graphite/precompile/PrecompileShader.h | 着色器派生类 |
| src/gpu/graphite/precompile/PrecompileColorFilter.h | 颜色滤镜派生类 |
| src/gpu/graphite/KeyContext.h | 键构建上下文 |
| src/gpu/graphite/PaintParamsKeyBuilder.h | 管线键构建器 |

## 扩展点

### 支持新的对象类型
1. 在 `Type` 枚举中添加新类型
2. 创建继承自 `PrecompileBase` 的派生类
3. 实现 `addToKey` 方法生成唯一键
4. 在 `PaintOptions` 中添加对应的设置方法

### 优化组合计算
对于特殊情况可重写 `numCombinations`:
```cpp
class PrecompileFixedPipeline : public PrecompileBase {
protected:
    // 跳过乘法,直接返回固定值
    int numCombinations() const override {
        return 1;  // 无变体
    }
};
```

## 最佳实践

1. **最小化本体组合数**: 将可选变体控制在合理范围 (通常 < 10)
2. **惰性计算子组合**: 只在需要时递归计算 `numChildCombinations`
3. **使用 SkSpan 传递选项**: 避免数组拷贝
4. **缓存组合数**: 如果计算昂贵,缓存 `numCombinations` 结果
5. **测试边界情况**: 确保索引 0 和 `numCombinations()-1` 都有效

## 调试技巧

### 打印组合树
```cpp
void printCombinations(const PrecompileBase* base, int indent = 0) {
    std::string prefix(indent * 2, ' ');
    printf("%sType: %d, Intrinsic: %d, Child: %d, Total: %d\n",
           prefix.c_str(),
           static_cast<int>(base->type()),
           base->priv().numIntrinsicCombinations(),
           base->priv().numChildCombinations(),
           base->priv().numCombinations());
}
```

### 验证键的唯一性
```cpp
std::set<uint64_t> uniqueKeys;
for (int i = 0; i < base->numCombinations(); ++i) {
    KeyBuilder builder;
    base->addToKey(context, i);
    uint64_t hash = builder.hash();
    assert(uniqueKeys.insert(hash).second);  // 确保唯一
}
```

## 常见陷阱

1. **组合数溢出**: 大量嵌套对象可能导致组合数超过 `int` 范围
2. **索引越界**: `addToKey` 实现必须正确处理 `desiredCombination` 范围
3. **子对象生命周期**: 确保子对象在父对象销毁前保持有效
4. **键冲突**: 不同配置生成相同键会导致管线复用错误

## 总结
PrecompileBase 通过组合模式和模板方法模式优雅地解决了 GPU 管线预编译中的配置组合爆炸问题,为 Graphite 预编译系统提供了灵活且高效的抽象基础。理解其设计对于扩展预编译系统或优化预编译性能至关重要。
