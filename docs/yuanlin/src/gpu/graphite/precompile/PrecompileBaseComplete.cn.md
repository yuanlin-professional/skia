# PrecompileBaseComplete - PrecompileBase 模板方法完整实现

> 源文件: `src/gpu/graphite/precompile/PrecompileBaseComplete.h`

## 概述

`PrecompileBaseComplete.h` 提供了 `PrecompileBase` 类中 `SelectOption` 和 `AddToKey` 两个模板方法的完整实现。由于这些是模板函数，其实现不能放在 `.cpp` 文件中，但也不适合放在公共头文件 `PrecompileBase.h` 中（避免暴露内部依赖）。因此该文件作为内部完整版头文件，在 Skia 内部代码中替代 `PrecompileBase.h` 使用。

## 架构位置

```
预编译类头文件层次
  ├── PrecompileBase.h (公共头文件 - 声明但不定义模板方法)
  │     └── PrecompileBaseComplete.h (本文件 - 提供模板方法实现)
  └── 内部代码 (应包含本文件而非 PrecompileBase.h)
```

这种分层设计将公共 API 与内部实现分离，同时满足 C++ 模板实例化的要求。

## 主要类与结构体

本文件不定义新类，而是为 `PrecompileBase` 提供模板方法实现。

## 公共 API 函数

### `PrecompileBase::SelectOption<T>`

```cpp
template<typename T>
std::pair<sk_sp<T>, int> PrecompileBase::SelectOption(
    SkSpan<const sk_sp<T>> options,
    int desiredOption);
```

从选项列表中选择特定组合编号对应的选项：
- 遍历 `options` 列表，累减 `desiredOption`
- 对于 `nullptr` 选项，贡献 1 个组合（代表"无此效果"）
- 返回 `{选中的选项, 剩余的组合编号}`
- 如果 `desiredOption` 超出范围，返回 `{nullptr, 0}`

### `PrecompileBase::AddToKey<T>`

```cpp
template<typename T>
void PrecompileBase::AddToKey(
    const KeyContext& keyContext,
    SkSpan<const sk_sp<T>> options,
    int desiredOption);
```

将选项列表中指定组合编号的配置添加到管线键：
1. 调用 `SelectOption()` 定位目标选项
2. 如果选项非空，调用其 `priv().addToKey()` 方法

## 内部实现细节

### 组合编号映射算法

`SelectOption` 实现了一种扁平化的组合索引映射：

```
假设 options = [A(3种), nullptr(1种), B(2种)]
desiredOption 0-2 → 选择 A, childOption = 0/1/2
desiredOption 3   → 选择 nullptr
desiredOption 4-5 → 选择 B, childOption = 0/1
```

每个选项贡献其 `numCombinations()` 个组合编号，`nullptr` 贡献 1 个。这种线性映射避免了显式的组合列表，只需一个整数即可唯一标识任何组合。

### nullptr 的语义

`nullptr` 选项表示"不使用此效果"，例如在着色器列表中包含 `nullptr` 表示某些绘制不需要着色器。这在组合枚举中计为一个有效选择。

### 与 PrecompileBasePriv 的关系

`AddToKey()` 内部通过 `option->priv().addToKey()` 调用，依赖 `PrecompileBasePriv` 的 `addToKey()` 方法。这就是为什么该文件需要在内部使用——它隐式依赖了 Priv 类。

## 依赖关系

- **include/gpu/graphite/precompile/PrecompileBase.h**: 宿主类声明

## 设计模式与设计决策

### 头文件分层模式

将模板实现放在单独的"Complete"头文件中是 Skia 处理以下矛盾的方案：
1. 模板方法必须对实例化点可见（C++ 模板实例化规则）
2. 公共头文件不应包含内部依赖
3. 内部代码需要完整的模板实现

### 递归组合选择

`SelectOption` + `AddToKey` 实现了递归的组合选择机制。每层 `PrecompileBase` 选择自己的选项，然后将剩余的 `childOptions` 编号传递给子对象。这种递归结构自然支持任意深度的预编译对象树。

## 性能考量

- `SelectOption()` 遍历是 O(n)，n 为选项数量（通常很小）
- 模板实例化允许编译器针对每种类型 T 生成优化代码
- 无堆分配——选择结果以 `std::pair` 值类型返回

## 相关文件

- `include/gpu/graphite/precompile/PrecompileBase.h` - PrecompileBase 公共声明
- `src/gpu/graphite/precompile/PrecompileBasePriv.h` - PrecompileBase 内部访问
- `src/gpu/graphite/precompile/PaintOptionsPriv.h` - PaintOptions 内部（调用 addToKey）
