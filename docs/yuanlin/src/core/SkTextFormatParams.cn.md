# SkTextFormatParams

> 源文件: src/core/SkTextFormatParams.h

## 概述

`SkTextFormatParams.h` 定义了 Skia 文本渲染中用于模拟粗体效果的参数。当字体本身不提供粗体变体时,Skia 可以通过增加描边宽度来创建"假粗体"效果。该文件定义了一个插值表,根据字体大小动态计算描边宽度,以保持视觉一致性。

## 架构位置

文本格式参数位于 Skia 核心文本渲染子系统:

- **用途**: 字体样式模拟(假粗体、假斜体)
- **使用者**: `SkScalerContext`、字体合成逻辑
- **范围**: 仅适用于无真实粗体变体的情况

## 主要常量定义

### 插值键

```cpp
static const SkScalar kStdFakeBoldInterpKeys[] = {
    SK_Scalar1*9,   // 9 点
    SK_Scalar1*36,  // 36 点
};
```

定义插值的分段点:
- 9 点及以下使用第一个比例
- 36 点及以上使用第二个比例
- 中间大小线性插值

### 插值值

```cpp
static const SkScalar kStdFakeBoldInterpValues[] = {
    SK_Scalar1/24,  // 文本大小 / 24
    SK_Scalar1/32,  // 文本大小 / 32
};
```

描边宽度比例:
- 小字体(≤9pt): 描边宽度 = 字体大小 / 24
- 大字体(≥36pt): 描边宽度 = 字体大小 / 32
- 中间大小: 线性插值

### 数组长度

```cpp
static const int kStdFakeBoldInterpLength = std::size(kStdFakeBoldInterpKeys);
```

## 内部实现细节

### 假粗体原理

真实粗体和假粗体的区别:

**真实粗体**:
- 字体设计师精心设计的字形
- 笔画粗细均匀
- 保持字形比例和可读性

**假粗体**:
- 在普通字形外围添加描边
- 简单但不够精细
- 可能影响字间距

### 插值计算

使用这些参数的典型代码:

```cpp
SkScalar GetFakeBoldStrokeWidth(SkScalar textSize) {
    if (textSize <= kStdFakeBoldInterpKeys[0]) {
        return textSize * kStdFakeBoldInterpValues[0];
    } else if (textSize >= kStdFakeBoldInterpKeys[1]) {
        return textSize * kStdFakeBoldInterpValues[1];
    } else {
        // 线性插值
        SkScalar t = (textSize - kStdFakeBoldInterpKeys[0]) /
                     (kStdFakeBoldInterpKeys[1] - kStdFakeBoldInterpKeys[0]);
        SkScalar ratio = kStdFakeBoldInterpValues[0] +
                         t * (kStdFakeBoldInterpValues[1] - kStdFakeBoldInterpValues[0]);
        return textSize * ratio;
    }
}
```

### 为什么需要插值?

**固定比例的问题**:
- 小字体: 描边相对笔画太粗,难以阅读
- 大字体: 描边相对笔画太细,效果不明显

**分段比例的优势**:
- 小字体使用较大比例(1/24),确保效果可见
- 大字果使用较小比例(1/32),避免过度加粗
- 平滑过渡,无突变

### 具体示例

| 字体大小 | 插值位置 | 比例 | 描边宽度 |
|---------|---------|------|---------|
| 8 pt | ≤ 9pt | 1/24 | 0.33 pt |
| 9 pt | 边界 | 1/24 | 0.375 pt |
| 22.5 pt | 中点 | 1/28 | 0.804 pt |
| 36 pt | 边界 | 1/32 | 1.125 pt |
| 48 pt | ≥ 36pt | 1/32 | 1.5 pt |

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkScalar` | 标量类型 |
| `<iterator>` | `std::size` 支持 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| `SkScalerContext` | 使用这些参数生成假粗体字形 |
| 字体合成逻辑 | 判断何时应用假粗体 |

## 设计模式与设计决策

### 设计决策

**为什么选择 9pt 和 36pt 作为分段点?**
- 9pt 接近常见小字体阅读大小
- 36pt 是标题/展示文字的典型大小
- 覆盖大多数使用场景

**为什么选择 1/24 和 1/32?**
- 经验值,平衡视觉效果和可读性
- 可能来自排版领域的最佳实践
- 与传统印刷标准对应

**为什么使用线性插值?**
- 简单高效
- 避免突变导致的视觉不连续
- 足够满足平滑过渡需求

**为什么不支持假斜体参数?**
假斜体通过简单的倾斜变换实现,不需要复杂参数:
```cpp
// 假斜体 = 剪切变换
matrix.setSkew(-0.25f, 0);  // 固定倾斜角度
```

## 性能考量

### 优化策略

1. **编译时常量**: 数组在编译时初始化
2. **简单插值**: 线性插值避免复杂计算
3. **查找表替代**: 可考虑预计算表进一步优化

### 性能特性

**计算开销**:
- 比较: 2 次
- 插值(worst case): 3 次减法 + 2 次除法 + 2 次乘法 + 1 次加法
- 总计: ~20-30 个周期

**优化可能**:
```cpp
// 可能的查找表优化
static const SkScalar fakeBoldTable[256];  // 预计算 0-255 pt
SkScalar width = fakeBoldTable[static_cast<int>(textSize)];
```

但当前实现已足够高效,因为:
- 假粗体判断在字形缓存之前
- 计算频率低(每个独特字体大小一次)
- 额外表占用 1KB 内存

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/core/SkScalerContext.cpp` | 使用假粗体参数 |
| `include/core/SkFont.h` | `setEmbolden()` API |
| `include/core/SkFontStyle.h` | 字体粗细定义 |
| `src/core/SkPaint.cpp` | 传统假粗体实现 |
