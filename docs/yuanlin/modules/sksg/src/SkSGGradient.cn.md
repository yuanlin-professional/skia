# SkSGGradient - 场景图渐变着色器节点

> 源文件: `modules/sksg/src/SkSGGradient.cpp`

## 概述

`SkSGGradient.cpp` 实现了 Skia 场景图 (sksg) 中的渐变着色器节点，包括基类 `Gradient` 以及两个具体实现 `LinearGradient`（线性渐变）和 `RadialGradient`（径向渐变/双点锥形渐变）。这些类将动态可变的渐变参数（颜色停靠点、位置、端点等）封装为场景图节点，支持动画驱动的渐变效果变化。

## 架构位置

渐变节点位于 sksg 模块的着色器节点层，作为场景图中的叶子节点或中间节点，为 `PaintNode` 等绘制节点提供 `SkShader`。在 Skottie (Lottie) 渲染管线中，渐变节点用于实现 After Effects 中的渐变填充和渐变描边效果。

## 主要类与结构体

### `Gradient` (基类)
提供通用的渐变颜色停靠点处理和着色器重新验证逻辑。

### `LinearGradient`
```cpp
sk_sp<SkShader> LinearGradient::onMakeShader(const std::vector<SkColor4f>& colors,
                                             const std::vector<SkScalar>& positions) const;
```
- 持有 `fStartPoint` 和 `fEndPoint` 定义线性渐变方向

### `RadialGradient`
```cpp
sk_sp<SkShader> RadialGradient::onMakeShader(const std::vector<SkColor4f>& colors,
                                             const std::vector<SkScalar>& positions) const;
```
- 持有 `fStartCenter`、`fStartRadius`、`fEndCenter`、`fEndRadius`
- 智能选择简单径向渐变或双点锥形渐变

## 公共 API 函数

| 方法 | 说明 |
|------|------|
| `Gradient::onRevalidateShader()` | 处理颜色停靠点并委托给子类创建着色器 |
| `LinearGradient::onMakeShader(colors, positions)` | 创建线性渐变 `SkShader` |
| `RadialGradient::onMakeShader(colors, positions)` | 创建径向或双点锥形渐变 `SkShader` |

## 内部实现细节

### 颜色停靠点处理 (`onRevalidateShader`)
```cpp
sk_sp<SkShader> Gradient::onRevalidateShader() {
    if (fColorStops.empty()) return nullptr;
    // 提取颜色和位置，确保位置单调递增
    SkScalar position = 0;
    for (const auto& stop : fColorStops) {
        colors.push_back(stop.fColor);
        position = SkTPin(stop.fPosition, position, 1.0f);
        positions.push_back(position);
    }
    return this->onMakeShader(colors, positions);
}
```

关键点：
- 使用 `SkTPin` 确保停靠点位置单调递增且在 [0, 1] 范围内
- 使用 `SkColor4f` 进行高精度颜色处理
- 空停靠点列表直接返回 `nullptr`

### 径向渐变的智能选择
```cpp
return (fStartRadius <= 0 && fStartCenter == fEndCenter)
    ? SkShaders::RadialGradient(...)        // 简单径向渐变
    : SkShaders::TwoPointConicalGradient(...) // 双点锥形渐变
```

当起始半径为 0 且两个中心点重合时，使用更简单的 `RadialGradient`；否则使用更通用的 `TwoPointConicalGradient`。

## 依赖关系

- **直接依赖**: `SkSGGradient.h`、`SkShader.h`、`SkGradient.h`、`SkColorSpace.h`
- **工具依赖**: `SkTPin.h`（值范围钳制）、`SkTo.h`（类型安全转换）
- **被使用**: Skottie 模块中的渐变填充/描边动画

## 设计模式与设计决策

- **模板方法模式**: `Gradient` 基类在 `onRevalidateShader()` 中处理通用逻辑（颜色/位置提取），然后调用子类的 `onMakeShader()` 创建具体着色器
- **位置单调性保证**: 通过 `SkTPin` 强制位置值单调递增，防止无效输入导致的渐变渲染错误
- **自动退化检测**: `RadialGradient` 自动检测是否可以使用更简单的渐变类型，这是一种性能优化策略

## 性能考量

- **按需创建着色器**: 着色器仅在重新验证 (revalidation) 时创建，动画帧之间如果渐变参数未变化则复用之前的着色器
- **简单渐变优先**: 当条件允许时选择 `RadialGradient` 而非 `TwoPointConicalGradient`，前者在 GPU 上的实现通常更高效
- **TODO 注释**: 代码中提到可以检测均匀分布的停靠点并传 `null` 给 positions，这可能启用着色器的快速路径

## 相关文件

- `modules/sksg/include/SkSGGradient.h` — 类声明、`ColorStop` 结构体和属性定义
- `include/effects/SkGradient.h` — Skia 核心渐变着色器工厂函数
- `include/core/SkShader.h` — `SkShader` 基类
- `modules/skottie/src/effects/` — Skottie 中使用渐变节点的代码
