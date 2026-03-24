# TestEmptyTypeface.h - 空字体测试工具

> 源文件: `tools/fonts/TestEmptyTypeface.h`

## 概述

`TestEmptyTypeface` 是一个测试用的空字体实现,所有方法都返回空值或零值。用于测试 Skia 字体系统在没有实际字体数据时的行为和容错能力。

## 架构位置

属于 Skia 测试工具层,用于单元测试和 GM (Golden Master) 测试中需要空字体的场景。

## 主要类与结构体

- **`TestEmptyTypeface`**: 继承自 `SkTypeface`,所有虚方法返回空/零值
- **`EmptyLocalizedStrings`**: 内部类,空的本地化字符串迭代器

## 公共 API 函数

- **`TestEmptyTypeface::Make()`**: 静态工厂方法,返回空字体实例

## 内部实现细节

所有 `on*` 虚方法提供最小化实现: `onOpenStream` 返回 nullptr,`onCountGlyphs` 返回 0,`onCharsToGlyphs` 将所有字形 ID 清零,`onCreateScalerContext` 使用 `MakeEmpty` 创建空缩放上下文。构造函数将字体标记为固定间距(`isFixedPitch = true`)。

## 依赖关系

- `SkTypeface.h`: 字体基类
- `SkScalerContext.h`: 缩放上下文
- `SkAdvancedTypefaceMetrics.h`: 高级字体度量

## 设计模式与设计决策

空对象模式的标准实现,确保在任何需要字体的场景下都能安全使用而不崩溃。

## 性能考量

所有操作均为 O(1),无实际计算或 I/O。

## 相关文件

- `src/core/SkScalerContext.h`: MakeEmpty 方法
