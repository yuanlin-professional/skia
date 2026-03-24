# SkComposeColorFilter

> 源文件
> - `src/effects/colorfilters/SkComposeColorFilter.h`
> - `src/effects/colorfilters/SkComposeColorFilter.cpp`

## 概述

`SkComposeColorFilter` 是 Skia 中实现颜色过滤器组合的类。它将两个颜色过滤器按照函数组合的方式串联起来，先应用内层过滤器（inner），再应用外层过滤器（outer）。这种设计遵循数学上的函数组合概念：`f(g(x))`，其中 `g` 是内层过滤器，`f` 是外层过滤器。

通过组合机制，用户可以构建复杂的颜色变换效果，而不需要为每种组合创建新的过滤器类型。例如，可以将灰度过滤器和色调调整过滤器组合，先转为灰度，然后调整色调。

## 架构位置

```
skia/
├── include/
│   └── core/
│       └── SkColorFilter.h               # 颜色过滤器公共接口
├── src/
│   ├── core/
│   │   ├── SkReadBuffer.h                # 反序列化支持
│   │   └── SkWriteBuffer.h               # 序列化支持
│   └── effects/
│       └── colorfilters/
│           ├── SkColorFilterBase.h            # 颜色过滤器基类
│           ├── SkComposeColorFilter.h         # 本模块头文件
│           ├── SkComposeColorFilter.cpp       # 本模块实现
│           ├── SkMatrixColorFilter.cpp        # 可能的子过滤器
│           └── SkRuntimeColorFilter.cpp       # 可能的子过滤器
```

`SkComposeColorFilter` 在 Skia 的颜色过滤器架构中扮演组合器的角色，它是装饰器模式和组合模式的实现，使得任意两个颜色过滤器可以灵活组合。

## 主要类与结构体

### SkComposeColorFilter

组合颜色过滤器类。

```cpp
class SkComposeColorFilter final : public SkColorFilterBase {
public:
    bool onIsAlphaUnchanged() const override;
    bool appendStages(const SkStageRec& rec, bool shaderIsOpaque) const override;

    SkColorFilterBase::Type type() const override {
        return SkColorFilterBase::Type::kCompose;
    }

    // 访问内部过滤器
    sk_sp<SkColorFilterBase> outer() const { return fOuter; }
    sk_sp<SkColorFilterBase> inner() const { return fInner; }

protected:
    void flatten(SkWriteBuffer& buffer) const override;

private:
    SkComposeColorFilter(sk_sp<SkColorFilter> outer,
                        sk_sp<SkColorFilter> inner);

    sk_sp<SkColorFilterBase> fOuter;  // 外层过滤器（后应用）
    sk_sp<SkColorFilterBase> fInner;  // 内层过滤器（先应用）

    friend class SkColorFilter;
};
```

**关键特性**：
- `final` 类，不可被继承
- 持有两个子过滤器的智能指针
- 按照数学函数组合的顺序应用过滤器

## 公共 API 函数

### SkColorFilter::makeComposed

```cpp
sk_sp<SkColorFilter> SkColorFilter::makeComposed(sk_sp<SkColorFilter> inner) const;
```

创建一个组合颜色过滤器，将调用者作为外层过滤器，参数作为内层过滤器。

**参数**：
- `inner` - 内层颜色过滤器（先应用）

**返回值**：组合后的颜色过滤器

**特殊处理**：
```cpp
if (!inner) {
    return sk_ref_sp(this);  // 如果 inner 为空，直接返回外层过滤器
}
```

**使用示例**：
```cpp
// 创建灰度过滤器
auto grayscale = SkColorFilters::Matrix(grayscaleMatrix);

// 创建色调调整过滤器
auto hueAdjust = SkColorFilters::HSLAMatrix(hueMatrix);

// 组合：先转灰度，后调整色调
auto composed = hueAdjust->makeComposed(grayscale);

// 等价于：hueAdjust(grayscale(color))
```

## 内部实现细节

### 构造函数

```cpp
SkComposeColorFilter::SkComposeColorFilter(sk_sp<SkColorFilter> outer,
                                           sk_sp<SkColorFilter> inner)
        : fOuter(as_CFB_sp(std::move(outer))),
          fInner(as_CFB_sp(std::move(inner))) {
    SkASSERT(fOuter && fInner);  // 两者都不能为空
}
```

**设计要点**：
- 使用 `as_CFB_sp` 将公共接口类型转换为基类类型
- 使用 `std::move` 避免不必要的引用计数操作
- 断言确保两个子过滤器都有效

### Alpha 不变性判断

```cpp
bool SkComposeColorFilter::onIsAlphaUnchanged() const {
    // 只有当两个代理都支持 alpha 不变时，才声明 alpha 不变
    return fOuter->isAlphaUnchanged() && fInner->isAlphaUnchanged();
}
```

**逻辑**：
- Alpha 不变性需要两个过滤器都保持 alpha 不变
- 如果任一过滤器改变 alpha，组合后的过滤器也会改变 alpha
- 这是逻辑与（AND）关系

### 管线构建

```cpp
bool SkComposeColorFilter::appendStages(const SkStageRec& rec,
                                        bool shaderIsOpaque) const {
    bool innerIsOpaque = shaderIsOpaque;

    // 如果内层过滤器改变 alpha，则输出不再是不透明的
    if (!fInner->isAlphaUnchanged()) {
        innerIsOpaque = false;
    }

    // 按顺序应用：先内层，后外层
    return fInner->appendStages(rec, shaderIsOpaque) &&
           fOuter->appendStages(rec, innerIsOpaque);
}
```

**不透明性传播**：
1. 如果输入是不透明的（`shaderIsOpaque = true`）
2. 内层过滤器可能改变不透明性
3. 外层过滤器接收内层的输出不透明性
4. 这确保了每个过滤器都能基于正确的不透明性假设进行优化

**短路求值**：
- 如果内层过滤器失败（返回 `false`），不会尝试外层过滤器
- 这保证了错误能够正确传播

### 序列化

```cpp
void SkComposeColorFilter::flatten(SkWriteBuffer& buffer) const {
    buffer.writeFlattenable(fOuter.get());
    buffer.writeFlattenable(fInner.get());
}

sk_sp<SkFlattenable> SkComposeColorFilter::CreateProc(SkReadBuffer& buffer) {
    sk_sp<SkColorFilter> outer(buffer.readColorFilter());
    sk_sp<SkColorFilter> inner(buffer.readColorFilter());

    // 如果 outer 存在，创建组合；否则只返回 inner
    return outer ? outer->makeComposed(std::move(inner)) : inner;
}
```

**反序列化容错**：
- 如果 `outer` 为 nullptr，只返回 `inner`
- 这处理了部分反序列化失败的情况
- 保证了向后兼容性

## 依赖关系

### 内部依赖

| 组件 | 用途 |
|-----|------|
| `SkColorFilterBase` | 颜色过滤器基类，提供核心接口 |
| `SkReadBuffer` | 反序列化支持 |
| `SkWriteBuffer` | 序列化支持 |

### 外部依赖

| 组件 | 用途 |
|-----|------|
| `SkColorFilter` | 公共颜色过滤器接口 |
| `SkRefCnt` | 智能指针和引用计数 |

### 可组合的过滤器

`SkComposeColorFilter` 可以组合任何 `SkColorFilter` 的实现：

| 过滤器类型 | 组合效果示例 |
|----------|------------|
| `SkMatrixColorFilter` | 串联多个矩阵变换 |
| `SkRuntimeColorFilter` | 在自定义着色器前后应用标准变换 |
| `SkWorkingFormatColorFilter` | 在特定色彩空间中应用其他过滤器 |
| `SkComposeColorFilter` | 嵌套组合，创建多层过滤器链 |

## 设计模式与设计决策

### 1. 组合模式（Composite Pattern）

`SkComposeColorFilter` 将两个颜色过滤器组合成一个新的过滤器，对外提供相同的接口：
- 客户端代码无需知道过滤器是简单的还是组合的
- 可以递归组合，创建任意深度的过滤器树

### 2. 装饰器模式（Decorator Pattern）

每个过滤器都可以被视为对另一个过滤器的装饰：
- 内层过滤器提供基础功能
- 外层过滤器添加额外的变换
- 可以动态添加和组合功能

### 3. 函数组合（Function Composition）

数学上的函数组合 `f ∘ g` 表示 `f(g(x))`：
```cpp
// outer(inner(color))
auto composed = outer->makeComposed(inner);
```

这种设计使得颜色变换具有代数结构，可以进行组合和优化。

### 4. 空对象处理（Null Object Handling）

在 `makeComposed` 中：
```cpp
if (!inner) {
    return sk_ref_sp(this);  // inner 为空时，返回自身
}
```

在 `CreateProc` 中：
```cpp
return outer ? outer->makeComposed(std::move(inner)) : inner;
```

这种设计避免了创建无效的组合，简化了客户端代码。

### 5. 不透明性追踪

通过追踪每个阶段的不透明性，优化渲染管线：
```cpp
bool innerIsOpaque = shaderIsOpaque;
if (!fInner->isAlphaUnchanged()) {
    innerIsOpaque = false;
}
```

这允许外层过滤器基于内层的输出特性进行优化。

## 性能考量

### 1. 引用计数优化

使用 `std::move` 避免不必要的引用计数操作：
```cpp
fOuter(as_CFB_sp(std::move(outer))),
fInner(as_CFB_sp(std::move(inner)))
```

**节省**：
- 避免原子操作（引用计数的增减）
- 减少缓存一致性开销

### 2. 管线内联

`appendStages` 直接将两个过滤器的管线阶段串联：
```cpp
return fInner->appendStages(rec, shaderIsOpaque) &&
       fOuter->appendStages(rec, innerIsOpaque);
```

**优势**：
- 不需要中间缓冲区
- 管线可以整体优化（例如合并相邻的矩阵操作）
- 支持向量化和并行执行

### 3. 短路优化

Alpha 不变性检查使用短路求值：
```cpp
return fOuter->isAlphaUnchanged() && fInner->isAlphaUnchanged();
```

如果 `fOuter` 改变 alpha，不需要检查 `fInner`。

### 4. 组合深度限制

理论上可以无限嵌套组合，但实践中：
- 过深的嵌套会增加管线复杂度
- 可能影响缓存效率
- 建议限制在 3-5 层以内

### 5. 组合优化机会

某些组合可以优化：
```cpp
// 两个矩阵可以预乘合并
MatrixA ∘ MatrixB → MatrixAB

// 恒等变换可以消除
Identity ∘ F → F
F ∘ Identity → F
```

当前实现没有进行这些优化，但未来版本可以在构造时检测和优化这些情况。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkColorFilter.h` | 颜色过滤器公共接口，包含 `makeComposed` 方法 |
| `src/effects/colorfilters/SkColorFilterBase.h` | 颜色过滤器基类 |
| `src/effects/colorfilters/SkMatrixColorFilter.cpp` | 矩阵颜色过滤器，常用的组合对象 |
| `src/effects/colorfilters/SkRuntimeColorFilter.cpp` | 运行时颜色过滤器，支持自定义着色器 |
| `src/effects/colorfilters/SkWorkingFormatColorFilter.cpp` | 工作格式过滤器，可包装其他过滤器 |
| `src/core/SkReadBuffer.h` | 反序列化支持 |
| `src/core/SkWriteBuffer.h` | 序列化支持 |
| `src/core/SkRasterPipeline.h` | 光栅化管线，执行组合后的操作 |
