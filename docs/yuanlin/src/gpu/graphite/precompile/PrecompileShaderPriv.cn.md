# PrecompileShaderPriv - 着色器预编译内部访问接口

> 源文件: `src/gpu/graphite/precompile/PrecompileShaderPriv.h`

## 概述

`PrecompileShaderPriv` 是 Skia Graphite 预编译系统中 `PrecompileShader` 类的内部特权访问类。它在 `PrecompileBasePriv` 的基础上增加了着色器特有的内部方法——常量着色器检测和 LocalMatrix 着色器识别。这两个方法在管线键构建过程中用于优化和特殊处理。

## 架构位置

```
预编译 Priv 类层次
  ├── PrecompileBasePriv (基类 Priv)
  │     ├── numChildCombinations(), numCombinations(), addToKey()
  │     └── PrecompileShaderPriv (本文件 - 着色器特化 Priv)
  │           ├── isConstant() - 常量着色器检测
  │           ├── isALocalMatrixShader() - LocalMatrix 识别
  │           └── 继承 Base 的全部方法
  └── PrecompileBlenderPriv (混合器特化 Priv)
```

## 主要类与结构体

### `PrecompileShaderPriv`

标准 Priv 类，持有 `PrecompileShader*` 指针。除着色器特有方法外，还复制了 `PrecompileBasePriv` 的方法（`numChildCombinations`, `numCombinations`, `addToKey`），使其可作为 `PrecompileBasePriv` 的完全替代。

## 公共 API 函数

### 着色器特有方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `isConstant(int desiredCombination)` | `bool` | 指定组合是否为常量着色器 |
| `isALocalMatrixShader()` | `bool` | 是否为 LocalMatrix 着色器包装器 |

### 继承自 PrecompileBase 的方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `numChildCombinations()` | `int` | 子组合数量 |
| `numCombinations()` | `int` | 总组合数量 |
| `addToKey(const KeyContext&, int)` | `void` | 添加到管线键 |

## 内部实现细节

### isConstant

```cpp
bool isConstant(int desiredCombination) const {
    return fPrecompileShader->isConstant(desiredCombination);
}
```

常量着色器（如纯色着色器 `SkShaders::Color()`）在所有像素位置返回相同的值。识别常量着色器允许管线键省略坐标变换等不必要的步骤。`desiredCombination` 参数允许同一预编译对象中某些组合是常量的而其他不是。

### isALocalMatrixShader

```cpp
bool isALocalMatrixShader() const {
    return fPrecompileShader->isALocalMatrixShader();
}
```

`LocalMatrix` 着色器是包装另一个着色器并应用局部变换矩阵的包装器。识别它在预编译键构建中用于确定是否需要额外的矩阵变换块。

### PrecompileBasePriv 兼容性

注释明确指出复制基类方法是为了使 `PrecompileShaderPriv` 成为 `PrecompileBasePriv` 的"可行替代品"（viable standin）。这种设计避免了虚继承或菱形继承的复杂性——Priv 类不参与继承链，它们是各自宿主类的独立窗口。

## 依赖关系

- **include/gpu/graphite/precompile/PrecompileShader.h**: 宿主类定义

## 设计模式与设计决策

### 替代品模式（Standin Pattern）

`PrecompileShaderPriv` 不继承自 `PrecompileBasePriv`，而是复制其方法。这是因为 Priv 类是非虚的轻量包装器，继承会引入不必要的复杂性。通过复制方法，调用代码可以统一使用 `PrecompileShaderPriv` 而无需区分基类和派生类的 Priv。

### 组合感知的常量检测

`isConstant()` 接受 `desiredCombination` 参数，这意味着一个预编译着色器对象可以同时代表常量和非常量变体。例如，`PrecompileShaders::Color()` 的所有组合都是常量，而 `PrecompileShaders::LocalMatrix(inner)` 取决于 `inner` 是否常量。

## 性能考量

- 所有方法为单步委托，编译器内联后无额外开销
- 常量着色器的检测可减少管线键中的变换块，降低管线变体数量
- LocalMatrix 检测避免了不必要的矩阵 Uniform 空间分配

## 相关文件

- `include/gpu/graphite/precompile/PrecompileShader.h` - PrecompileShader 公共 API
- `src/gpu/graphite/precompile/PrecompileBasePriv.h` - 基类 Priv
- `src/gpu/graphite/precompile/PrecompileImageShader.h` - 图像着色器（具体实现）
- `src/gpu/graphite/precompile/PrecompileShadersPriv.h` - 内部着色器工厂
- `src/gpu/graphite/precompile/PrecompileBlenderPriv.h` - 混合器 Priv（类似结构）
