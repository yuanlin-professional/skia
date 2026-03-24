# PrecompileImageFilterPriv - 图像滤镜预编译内部访问接口

> 源文件: `src/gpu/graphite/precompile/PrecompileImageFilterPriv.h`

## 概述

`PrecompileImageFilterPriv` 是 Skia Graphite 预编译系统中 `PrecompileImageFilter` 类的内部特权访问类。它暴露了两个内部方法：判断该图像滤镜是否为颜色滤镜节点，以及获取输入图像滤镜。这些方法在预编译系统遍历图像滤镜树时使用。

## 架构位置

```
预编译图像滤镜树遍历
  ├── PrecompileImageFilter (公共基类)
  │     └── PrecompileImageFilterPriv (本文件 - 内部访问窗口)
  │           ├── isColorFilterNode() - 颜色滤镜节点识别
  │           └── getInput() - 输入滤镜访问
  └── 具体图像滤镜预编译类
        ├── PrecompileBlurImageFilter
        ├── PrecompileColorFilterImageFilter
        ├── PrecompileDisplacementImageFilter
        └── ...
```

## 主要类与结构体

### `PrecompileImageFilterPriv`

标准 Priv 类模式实现，提供对 `PrecompileImageFilter` 内部方法的访问。

## 公共 API 函数

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `isColorFilterNode()` | `sk_sp<PrecompileColorFilter>` | 如果该滤镜是颜色滤镜包装器，返回内部颜色滤镜 |
| `getInput(int index)` | `const PrecompileImageFilter*` | 获取指定索引的输入图像滤镜 |

### isColorFilterNode

该方法用于识别 `ColorFilterImageFilter`——一种将颜色滤镜包装为图像滤镜的适配器。如果当前 `PrecompileImageFilter` 是此类适配器，返回其包含的 `PrecompileColorFilter`；否则返回 `nullptr`。

### getInput

获取图像滤镜链中指定位置的输入。图像滤镜可以形成有向无环图（DAG），每个节点可有零个或多个输入：
- 索引 0 通常是主输入
- 某些滤镜（如 Displacement）有多个输入

## 内部实现细节

### Priv 访问入口

```cpp
inline PrecompileImageFilterPriv PrecompileImageFilter::priv() {
    return PrecompileImageFilterPriv(this);
}
inline const PrecompileImageFilterPriv PrecompileImageFilter::priv() const {
    return PrecompileImageFilterPriv(const_cast<PrecompileImageFilter*>(this));
}
```

### 颜色滤镜节点优化

识别颜色滤镜节点对预编译优化至关重要。`ColorFilterImageFilter` 不需要中间纹理——它可以直接在片段着色器中应用颜色变换。预编译系统通过 `isColorFilterNode()` 识别这些情况，生成更高效的管线变体。

### 方法委托

两个方法直接委托给 `fPrecompileImageFilter` 的受保护虚方法：
- `isColorFilterNode()` → 基类默认返回 `nullptr`，`ColorFilterImageFilter` 子类重写
- `getInput()` → 由具体子类实现，基于内部输入数组

## 依赖关系

- **include/gpu/graphite/precompile/PrecompileImageFilter.h**: 宿主类定义
- 隐式依赖: `PrecompileColorFilter`

## 设计模式与设计决策

### 树遍历支持

`isColorFilterNode()` 和 `getInput()` 共同支持了图像滤镜树的递归遍历。预编译系统需要遍历整个滤镜树以确定所有需要预编译的管线变体。这与运行时 `SkImageFilter` 的遍历机制对称。

### 返回值语义

`isColorFilterNode()` 返回 `sk_sp`（拥有引用），而 `getInput()` 返回原始指针（非拥有），反映了不同的生命周期需求：
- 颜色滤镜可能需要在调用上下文中持续使用
- 输入滤镜的生命周期由父滤镜管理

## 性能考量

- 两个方法均为虚函数调用（通过宿主对象），有一次间接调用开销
- 颜色滤镜节点的识别避免了不必要的中间纹理管线变体生成
- `getInput()` 为常量时间的数组索引操作

## 相关文件

- `include/gpu/graphite/precompile/PrecompileImageFilter.h` - PrecompileImageFilter 公共 API
- `src/gpu/graphite/precompile/PrecompileImageFiltersPriv.h` - 图像滤镜管线构建
- `src/gpu/graphite/precompile/PrecompileColorFiltersPriv.h` - 颜色滤镜工厂
- `src/gpu/graphite/precompile/PrecompileBasePriv.h` - 基类内部访问
