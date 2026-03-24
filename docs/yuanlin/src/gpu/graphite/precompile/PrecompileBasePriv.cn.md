# PrecompileBasePriv - 预编译基类内部访问接口

> 源文件: `src/gpu/graphite/precompile/PrecompileBasePriv.h`

## 概述

`PrecompileBasePriv` 是 Skia Graphite 预编译（Precompile）子系统中 `PrecompileBase` 类的内部特权访问类。`PrecompileBase` 是所有预编译对象的基类，而 `PrecompileBasePriv` 暴露了组合计数和键构建等内部方法，这些方法在管线预编译流程中被 Skia 内部代码使用。

## 架构位置

```
Graphite 预编译子系统
  ├── PrecompileBase (公共基类)
  │     └── PrecompileBasePriv (本文件 - 内部访问窗口)
  ├── PrecompileShader (着色器预编译)
  ├── PrecompileColorFilter (颜色滤镜预编译)
  ├── PrecompileBlender (混合器预编译)
  └── PaintOptions (绘制选项组合器)
```

预编译系统允许应用程序提前指定可能的绘制配置组合，Skia 据此预先编译 GPU 管线，避免首帧卡顿。

## 主要类与结构体

### `PrecompileBasePriv`

标准 Priv 类模式实现，提供对 `PrecompileBase` 内部方法的访问：

- 无额外数据成员或虚方法
- 禁止赋值和取地址操作
- 仅持有 `PrecompileBase*` 指针

## 公共 API 函数

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `numChildCombinations()` | `int` | 子选项的组合数量 |
| `numCombinations()` | `int` | 总组合数量（含子选项的组合） |
| `addToKey(const KeyContext&, int)` | `void` | 将指定组合编号添加到管线键 |

### 访问入口

```cpp
inline PrecompileBasePriv PrecompileBase::priv() { return PrecompileBasePriv(this); }
inline const PrecompileBasePriv PrecompileBase::priv() const {
    return PrecompileBasePriv(const_cast<PrecompileBase*>(this));
}
```

## 内部实现细节

### 组合枚举机制

预编译系统的核心是组合枚举：
1. `numCombinations()` 返回该预编译对象表示的所有可能管线配置数量
2. `addToKey()` 接受一个组合编号（0 到 numCombinations()-1），将对应的配置写入管线键
3. `numChildCombinations()` 返回子对象的组合数，用于递归计算总组合数

### 委托模式

所有方法直接委托给 `fPrecompileBase` 的同名方法，编译器会将这些调用完全内联。

## 依赖关系

- **src/gpu/graphite/PrecompileInternal.h**: 内部预编译类型定义

## 设计模式与设计决策

### Priv 类继承体系

`PrecompileBasePriv` 是预编译 Priv 类家族的根。派生的 Priv 类（如 `PrecompileShaderPriv`、`PrecompileBlenderPriv`）扩展了额外的特化方法（如 `isConstant()`、`asBlendMode()`），同时也包含与 `PrecompileBasePriv` 相同的基础方法，使得它们可以作为基类 Priv 的替代品使用。

### 组合遍历与键构建分离

`numCombinations()` 和 `addToKey()` 的分离允许调用者先查询组合数量，然后按需构建特定组合的键。这种设计支持了批量预编译和优先级调度。

## 性能考量

- 所有方法为单步委托，编译器内联后无额外开销
- 组合枚举是线性的，总预编译时间与组合数成正比
- `addToKey()` 直接向键上下文追加数据，无中间缓冲

## 相关文件

- `include/gpu/graphite/precompile/PrecompileBase.h` - PrecompileBase 公共 API
- `src/gpu/graphite/precompile/PrecompileBaseComplete.h` - 模板方法完整实现
- `src/gpu/graphite/precompile/PrecompileShaderPriv.h` - Shader Priv 特化
- `src/gpu/graphite/precompile/PrecompileBlenderPriv.h` - Blender Priv 特化
- `src/gpu/graphite/precompile/PaintOptionsPriv.h` - PaintOptions 内部访问
- `src/gpu/graphite/PrecompileInternal.h` - 内部预编译类型
