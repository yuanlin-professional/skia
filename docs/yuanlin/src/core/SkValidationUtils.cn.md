# SkValidationUtils

> 源文件: src/core/SkValidationUtils.h

## 概述

`SkValidationUtils.h` 提供了一组内联验证函数,用于检查 Skia 核心类型的有效性。这些工具函数主要用于断言检查和输入验证,帮助在反序列化、参数检查等场景中提前发现无效数据,防止程序崩溃或产生未定义行为。

## 架构位置

验证工具位于 Skia 核心基础设施层:

- **用途**: 输入验证、反序列化检查、防御性编程
- **使用者**: 序列化系统、API 边界、调试代码
- **特点**: 头文件内联函数,零运行时开销

## 公共 API 函数

### SkIsValidMode

```cpp
static inline bool SkIsValidMode(SkBlendMode mode)
```

**功能**: 检查混合模式是否有效

**实现**:
```cpp
return (unsigned)mode <= (unsigned)SkBlendMode::kLastMode;
```

**验证条件**:
- 枚举值在有效范围内
- 0 ≤ mode ≤ kLastMode

**使用场景**:
```cpp
bool deserializeBlendMode(SkReadBuffer& buffer) {
    int modeValue = buffer.readInt();
    if (!SkIsValidMode(static_cast<SkBlendMode>(modeValue))) {
        return false;  // 无效数据
    }
    fBlendMode = static_cast<SkBlendMode>(modeValue);
    return true;
}
```

### SkIsValidIRect

```cpp
static inline bool SkIsValidIRect(const SkIRect& rect)
```

**功能**: 检查整数矩形是否有效

**实现**:
```cpp
return rect.width() >= 0 && rect.height() >= 0;
```

**验证条件**:
- 宽度 ≥ 0 (即 right ≥ left)
- 高度 ≥ 0 (即 bottom ≥ top)

**允许的情况**:
- 空矩形 (width = 0 或 height = 0)
- 点 (width = 0 且 height = 0)
- 正常矩形

**不允许的情况**:
- 翻转矩形 (right < left 或 bottom < top)
- 维度溢出 INT_MAX

**使用场景**:
```cpp
bool setClipRect(const SkIRect& rect) {
    if (!SkIsValidIRect(rect)) {
        SkASSERT(false);  // 调试模式下断言
        return false;
    }
    fClipRect = rect;
    return true;
}
```

### SkIsValidRect

```cpp
static inline bool SkIsValidRect(const SkRect& rect)
```

**功能**: 检查浮点矩形是否有效

**实现**:
```cpp
return (rect.fLeft <= rect.fRight) &&
       (rect.fTop <= rect.fBottom) &&
       SkIsFinite(rect.width(), rect.height());
```

**验证条件**:
1. 左 ≤ 右
2. 上 ≤ 下
3. 宽度和高度都是有限数值

**允许的情况**:
- 空矩形
- 正常矩形
- 极大但有限的矩形

**不允许的情况**:
- 翻转矩形
- 包含 NaN 的矩形
- 包含无穷大的矩形

**特殊处理**:
- 使用 `SkIsFinite(width, height)` 而非单独检查四个坐标
- 优化检查次数

**使用场景**:
```cpp
bool drawRect(const SkRect& rect) {
    if (!SkIsValidRect(rect)) {
        // 跳过绘制或使用空矩形
        return false;
    }
    // 安全地进行绘制
    return true;
}
```

## 内部实现细节

### 类型转换技巧

**SkIsValidMode**:
```cpp
(unsigned)mode <= (unsigned)SkBlendMode::kLastMode
```

- 将有符号枚举转换为无符号数
- 负值变为大整数,自动失败
- 单次比较检查上下界

### 坐标完整性

**SkIsValidIRect**:
```cpp
rect.width() >= 0 && rect.height() >= 0
```

等价于:
```cpp
(rect.fRight >= rect.fLeft) && (rect.fBottom >= rect.fTop)
```

但前者语义更清晰。

### 浮点数特殊值处理

**SkIsValidRect**:
```cpp
SkIsFinite(rect.width(), rect.height())
```

**为什么检查宽高而非坐标?**
- 减少比较次数
- `width = right - left`, 如果差是 NaN,则坐标无效
- `infinity - infinity = NaN`, 自动捕获

**边界情况**:
```cpp
SkRect r1 = {-INFINITY, 0, INFINITY, 100};  // 无效(宽度 = NaN)
SkRect r2 = {0, 0, INFINITY, INFINITY};     // 无效(无穷宽高)
SkRect r3 = {0, 0, NaN, 100};               // 无效(包含 NaN)
SkRect r4 = {0, 0, SK_ScalarMax, 100};      // 有效(大但有限)
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkBitmap` | 位图类型(头文件引用) |
| `SkBlendMode` | 混合模式枚举 |
| `SkRect`/`SkIRect` | 矩形类型 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| `SkReadBuffer` | 反序列化验证 |
| `SkPaint` | 参数验证 |
| `SkCanvas` | 输入检查 |
| 各种效果类 | 构造函数验证 |

## 设计模式与设计决策

### 设计决策

**为什么使用内联函数而非宏?**
- 类型安全
- 作用域限制
- 支持调试器单步
- 零运行时开销(内联后与宏相同)

**为什么这些函数是静态的?**
```cpp
static inline bool ...
```
- 避免链接冲突
- 每个翻译单元独立副本
- 现代编译器优化可消除重复

**为什么不使用异常?**
Skia 不使用 C++ 异常:
- 代码库广泛使用,禁用异常可减小二进制大小
- 返回布尔值更明确
- 调用者可选择处理方式(断言/降级/返回错误)

**为什么验证函数如此简单?**
- 仅检查基本不变式
- 不涉及复杂业务逻辑
- 保持高性能
- 深度验证由具体类负责

**为什么包含 SkBitmap.h?**
```cpp
#include "include/core/SkBitmap.h"
```
- 虽然当前未使用,可能预留给未来的 `SkIsValidBitmap()`
- 或历史遗留依赖

## 性能考量

### 优化策略

1. **内联**: 函数体小,完全内联
2. **简单比较**: 仅基本算术和逻辑
3. **短路求值**: 使用 `&&` 避免不必要的检查

### 性能特性

**SkIsValidMode**:
```
1 次转型 + 1 次比较 = ~2 周期
```

**SkIsValidIRect**:
```
2 次减法 + 2 次比较 + 1 次逻辑与 = ~5 周期
```

**SkIsValidRect**:
```
4 次比较 + 2 次减法 + 2 次有限性检查 + 逻辑与 = ~10-15 周期
```

所有函数在发布版本中几乎零开销。

### 使用场景

**序列化**:
```cpp
sk_sp<SkImageFilter> SkImageFilter::Deserialize(SkReadBuffer& buffer) {
    int mode = buffer.readInt();
    if (!SkIsValidMode(static_cast<SkBlendMode>(mode))) {
        buffer.validate(false);
        return nullptr;
    }
    // ...
}
```

**防御性编程**:
```cpp
void SkCanvas::clipRect(const SkRect& rect) {
    if (!SkIsValidRect(rect)) {
        // 降级处理:使用空矩形或跳过
        return;
    }
    // 正常裁剪逻辑
}
```

**调试断言**:
```cpp
void setRect(const SkIRect& rect) {
    SkASSERT(SkIsValidIRect(rect));  // 调试版本检查
    fRect = rect;
}
```

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkBlendMode.h` | 混合模式定义 |
| `include/core/SkRect.h` | 矩形类型 |
| `src/core/SkReadBuffer.cpp` | 使用验证函数 |
| `src/core/SkPaint.cpp` | 参数验证 |
| `include/core/SkScalar.h` | `SkIsFinite()` 定义 |
