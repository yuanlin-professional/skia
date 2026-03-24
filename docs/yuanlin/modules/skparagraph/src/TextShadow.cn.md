# TextShadow

> 源文件: modules/skparagraph/src/TextShadow.cpp

## 概述

`TextShadow` 是 Skia 段落排版模块中用于表示文本阴影效果的轻量级值类型。该类封装了阴影的三个核心属性：颜色、偏移量和模糊半径。作为文本样式系统的一部分，`TextShadow` 支持在单个文本样式中叠加多个阴影效果，从而实现复杂的视觉装饰。

该实现提供了构造函数、相等性比较运算符以及检测阴影是否可见的辅助方法。由于阴影渲染是图形密集型操作，`hasShadow()` 方法允许渲染器跳过不可见的阴影，从而优化性能。该类设计为 POD（Plain Old Data）风格，适合高效复制和存储在向量容器中。

## 架构位置

`TextShadow` 在 Skia 文本渲染管线中的位置：

```
Skia 段落排版架构
├── modules/skparagraph/           段落模块
│   ├── include/
│   │   ├── TextShadow.h          阴影类声明（本类）
│   │   ├── TextStyle.h           文本样式（包含阴影向量）
│   │   └── Paragraph.h           段落接口
│   └── src/
│       ├── TextShadow.cpp        本实现文件
│       ├── TextStyle.cpp         文本样式实现
│       ├── TextLine.cpp          文本行渲染（应用阴影）
│       └── ParagraphPainter.cpp  段落绘制器
└── include/core/
    ├── SkColor.h                  颜色定义
    ├── SkPoint.h                  偏移量表示
    └── SkMaskFilter.h             模糊滤镜（用于阴影）
```

**渲染流程中的角色**：
1. **样式配置**：`TextStyle` 存储 `std::vector<TextShadow>`
2. **布局阶段**：阴影参数影响边界计算（考虑模糊扩展）
3. **绘制阶段**：`ParagraphPainter` 根据阴影配置多次绘制文本

## 主要类与结构体

### TextShadow 类

```cpp
class TextShadow {
public:
    SkColor fColor;        // 阴影颜色（包含 alpha 通道）
    SkPoint fOffset;       // 偏移量（x, y）单位为像素
    double fBlurSigma;     // 高斯模糊标准差（sigma）

    // 构造函数
    TextShadow();
    TextShadow(SkColor color, SkPoint offset, double blurSigma);

    // 比较运算符
    bool operator==(const TextShadow& other) const;
    bool operator!=(const TextShadow& other) const;

    // 可见性检测
    bool hasShadow() const;
};
```

**成员说明**：
- `fColor`: 使用 `SkColor` (32位 ARGB) 表示阴影颜色
- `fOffset`: `SkPoint` 类型，`.x` 为水平偏移，`.y` 为垂直偏移（正值向右下）
- `fBlurSigma`: 模糊程度，0 表示无模糊（硬边阴影），值越大越模糊

### 默认值

```cpp
TextShadow::TextShadow() = default;
```

使用编译器生成的默认构造函数，成员初始化为：
- `fColor = 0` (透明黑色)
- `fOffset = {0, 0}` (无偏移)
- `fBlurSigma = 0` (无模糊)

## 公共 API 函数

### 构造函数

```cpp
TextShadow::TextShadow(SkColor color, SkPoint offset, double blurSigma)
    : fColor(color), fOffset(offset), fBlurSigma(blurSigma) {}
```

**参数**：
- `color`: 阴影颜色，通常使用半透明黑色如 `0x80000000`
- `offset`: 偏移向量，例如 `{2, 2}` 表示向右下偏移 2 像素
- `blurSigma`: 模糊半径，通常范围 0-10，值为标准差而非直径

**使用示例**：
```cpp
// 经典下沉阴影
TextShadow dropShadow(0x80000000, {2, 2}, 1.5);

// 外发光效果（无偏移）
TextShadow glow(0x80FF0000, {0, 0}, 5.0);

// 硬边阴影（无模糊）
TextShadow hardShadow(0xFF000000, {1, 1}, 0);
```

### 相等性比较

```cpp
bool TextShadow::operator==(const TextShadow& other) const {
    if (fColor != other.fColor) return false;
    if (fOffset != other.fOffset) return false;
    if (fBlurSigma != other.fBlurSigma) return false;
    return true;
}

bool TextShadow::operator!=(const TextShadow& other) const {
    return !(*this == other);
}
```

**实现细节**：
- 逐成员精确比较（包括浮点数 `fBlurSigma`）
- 不进行近似比较，确保缓存键的准确性
- 支持 `std::vector<TextShadow>` 的相等性检查

### 可见性检测

```cpp
bool TextShadow::hasShadow() const {
    if (!fOffset.isZero()) return true;
    if (fBlurSigma != 0.0) return true;
    return false;
}
```

**判断逻辑**：
1. **有偏移**：即使无模糊，阴影也可见（平移的副本）
2. **有模糊**：即使无偏移，阴影也可见（外发光效果）
3. **两者皆无**：阴影不可见（即使颜色不透明）

**特殊情况**：
- 不检查颜色 alpha：即使完全透明的阴影也被视为"有阴影"
- 设计理由：将可见性判断推迟到渲染时，简化逻辑

## 内部实现细节

### 模糊半径的含义

`fBlurSigma` 使用高斯模糊的标准差（σ）而非半径：

```
高斯函数：G(x) = (1 / √(2πσ²)) * e^(-x² / (2σ²))
```

**实际模糊范围**：通常取 `3σ` 作为有效半径，因为 99.7% 的影响在此范围内。

**渲染实现**（伪代码）：
```cpp
SkPaint shadowPaint;
shadowPaint.setColor(shadow.fColor);
shadowPaint.setMaskFilter(SkMaskFilter::MakeBlur(kNormal_SkBlurStyle, shadow.fBlurSigma));

canvas->save();
canvas->translate(shadow.fOffset.x(), shadow.fOffset.y());
canvas->drawText(text, shadowPaint);  // 绘制阴影层
canvas->restore();
canvas->drawText(text, textPaint);    // 绘制文本层
```

### 偏移坐标系

`fOffset` 的坐标系遵循 Skia 画布坐标系：

```
      X 轴正向 →
    ┌──────────────
Y   │
轴  │  (0,0)    (+x, 0)
正  │
向  │
↓   │  (0,+y)   (+x,+y)
```

**常见偏移模式**：
- `{0, 2}`: 下落阴影（文本下方）
- `{0, -2}`: 上浮阴影（文本上方）
- `{2, 0}`: 右侧阴影
- `{-1, -1}`: 左上阴影（浮雕效果）

### 多阴影叠加

`TextStyle` 支持阴影数组：

```cpp
TextStyle style;
style.addShadow(TextShadow(0x40000000, {0, 2}, 2));   // 软阴影
style.addShadow(TextShadow(0x80000000, {0, 1}, 0));   // 硬边框
```

**渲染顺序**：从后向前绘制，最后添加的阴影在最上层。

### 边界扩展计算

阴影影响文本的绘制边界：

```cpp
SkRect textBounds = calculateTextBounds(text);
for (const TextShadow& shadow : shadows) {
    if (shadow.hasShadow()) {
        SkScalar expansion = 3 * shadow.fBlurSigma;  // 3σ 规则
        SkRect shadowBounds = textBounds.makeOffset(shadow.fOffset.x(), shadow.fOffset.y());
        shadowBounds.outset(expansion, expansion);
        textBounds.join(shadowBounds);
    }
}
```

这确保阴影不会被裁剪。

## 依赖关系

### 直接依赖

```cpp
#include "include/core/SkColor.h"                   // SkColor 类型
#include "modules/skparagraph/include/TextShadow.h" // 类声明
```

**Skia 核心类型**：
- `SkColor` - 32位 ARGB 颜色
- `SkPoint` - 二维点/向量
- `SkScalar` - Skia 浮点类型（通常为 float）

### 被依赖关系

```
TextShadow.cpp 被以下模块使用：
├── TextStyle.cpp              存储阴影配置
├── ParagraphPainter.cpp       渲染阴影效果
├── TextLine.cpp               计算包含阴影的边界
└── ParagraphCache.cpp         作为样式哈希的一部分
```

### 标准库依赖

无直接标准库依赖，完全基于 Skia 类型。

## 设计模式与设计决策

### POD 类型设计

`TextShadow` 采用简单数据结构设计：

```cpp
class TextShadow {
    SkColor fColor;
    SkPoint fOffset;
    double fBlurSigma;
};
```

**优势**：
- 可平凡复制（trivially copyable）
- 适合存储在连续内存（`std::vector`）
- 缓存友好，提升遍历性能

### 显式命名构造

提供默认构造和参数构造：

```cpp
TextShadow();                                           // 无效阴影
TextShadow(SkColor color, SkPoint offset, double blur); // 完整阴影
```

而非使用默认参数：
```cpp
// 不采用的设计
TextShadow(SkColor c = 0, SkPoint o = {0,0}, double b = 0);
```

这使构造意图更明确，避免误用。

### 可见性优化

`hasShadow()` 方法体现了性能优先的设计：

```cpp
if (!fOffset.isZero()) return true;  // 快速路径
if (fBlurSigma != 0.0) return true;
return false;
```

**权衡**：
- 不检查颜色透明度（避免额外条件）
- 假设渲染器会处理透明阴影（最终不可见但仍绘制）
- 优先考虑简单性而非极致优化

### 不变性约定

虽然成员是公共的，但按惯例应视为不可变：

```cpp
TextShadow shadow(color, offset, blur);
// 不推荐：shadow.fColor = newColor;
// 推荐：创建新的 TextShadow 对象
```

这与值语义设计一致，简化并发安全性。

## 性能考量

### 内存占用

```cpp
sizeof(TextShadow) = sizeof(SkColor) + sizeof(SkPoint) + sizeof(double)
                   = 4 + 8 + 8 = 20 字节（可能因对齐为 24 字节）
```

**影响**：
- 单个阴影占用小，支持大量阴影效果
- 向量存储效率高，迭代开销低

### 渲染开销

阴影是昂贵操作：

1. **模糊滤镜**：O(n²) 复杂度的卷积操作（可通过 GPU 加速）
2. **多次绘制**：每个阴影需要额外的绘制调用
3. **边界扩展**：增大需要光栅化的区域

**优化策略**：
```cpp
// 渲染器中的优化
if (!shadow.hasShadow()) continue;  // 跳过无效阴影

if (shadow.fBlurSigma < 0.5) {
    // 使用快速路径（无模糊）
    drawWithoutBlur(shadow);
} else {
    // 使用完整模糊管线
    drawWithBlur(shadow);
}
```

### 比较开销

相等性比较是轻量级的：

```cpp
bool operator==(const TextShadow& other) const {
    return fColor == other.fColor &&        // 整数比较
           fOffset == other.fOffset &&      // 两次浮点比较
           fBlurSigma == other.fBlurSigma;  // 一次浮点比较
}
```

**应用**：用于文本样式缓存的键比较，高频调用场景。

### 缓存友好性

`std::vector<TextShadow>` 的内存布局：

```
[Shadow1][Shadow2][Shadow3]...  连续存储
```

CPU 可以高效预取，适合遍历：
```cpp
for (const TextShadow& shadow : textStyle.getShadows()) {
    if (shadow.hasShadow()) { renderShadow(shadow); }
}
```

## 相关文件

### 接口定义
- `/Users/yuanlin/workspace/skia/modules/skparagraph/include/TextShadow.h` - 类声明

### 核心使用
- `/Users/yuanlin/workspace/skia/modules/skparagraph/include/TextStyle.h` - 文本样式包含阴影向量
- `/Users/yuanlin/workspace/skia/modules/skparagraph/src/TextStyle.cpp` - 阴影比较和管理
- `/Users/yuanlin/workspace/skia/modules/skparagraph/src/ParagraphPainterImpl.cpp` - 阴影渲染实现

### 底层依赖
- `/Users/yuanlin/workspace/skia/include/core/SkColor.h` - 颜色类型
- `/Users/yuanlin/workspace/skia/include/core/SkPoint.h` - 点和向量
- `/Users/yuanlin/workspace/skia/include/core/SkMaskFilter.h` - 模糊滤镜（渲染时使用）

### 测试文件
- `/Users/yuanlin/workspace/skia/modules/skparagraph/tests/ParagraphTest.cpp` - 段落测试
- `/Users/yuanlin/workspace/skia/tests/BlurTest.cpp` - 模糊效果测试

### 相关效果
- `/Users/yuanlin/workspace/skia/include/effects/SkBlurMaskFilter.h` - 模糊效果实现
