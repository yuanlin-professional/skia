# SkPaintDefaults

> 源文件
> - src/core/SkPaintDefaults.h

## 概述

`SkPaintDefaults.h` 是一个轻量级的头文件,定义了 Skia 绘图系统中 `SkPaint` 和字体相关属性的默认值。该文件通过预处理器宏提供了三个核心默认值:文本大小、字体提示(hinting)和斜接限制(miter limit)。这些默认值可以在构建系统中或通过 `SkUserConfig.h` 进行自定义,而无需修改 Skia 源代码本身。

## 架构位置

`SkPaintDefaults` 位于 Skia 核心模块(`src/core`)的配置层,作为编译时配置的一部分。它为以下组件提供默认值:

- `SkPaint`: 绘制属性类
- `SkFont`: 字体属性类
- 构建系统配置接口

该文件不包含任何实现代码,仅定义宏常量,属于 Skia 的配置基础设施。

## 主要类与结构体

该文件不定义任何类或结构体,仅包含预处理器宏定义。

### 宏定义列表

| 宏名称 | 默认值 | 说明 |
|--------|--------|------|
| `SkPaintDefaults_TextSize` | `SkIntToScalar(12)` | 默认文本大小,单位为像素,通常为 12 点 |
| `SkPaintDefaults_Hinting` | `SkFontHinting::kNormal` | 默认字体提示级别,Normal 表示标准提示 |
| `SkPaintDefaults_MiterLimit` | `SkIntToScalar(4)` | 默认斜接限制,控制尖角连接的最大长度 |

## 公共 API 函数

该文件不包含函数定义,仅提供宏定义供其他模块使用。

## 内部实现细节

### 条件编译机制

每个默认值都使用 `#ifndef` 保护,允许外部在包含此头文件前预定义这些宏:

```cpp
#ifndef SkPaintDefaults_TextSize
    #define SkPaintDefaults_TextSize SkIntToScalar(12)
#endif
```

这种模式确保:
1. 如果构建系统或 `SkUserConfig.h` 已定义该宏,使用外部定义的值
2. 否则,使用头文件中的默认值

### 文本大小默认值

`SkIntToScalar(12)` 将整数 12 转换为 Skia 的标量类型。12 点(约 16 像素)是排版中常见的可读性良好的默认文本大小。

### 字体提示默认值

`SkFontHinting::kNormal` 表示使用操作系统的标准字体提示算法,在清晰度和保真度之间取得平衡:

- `kNone`: 无提示,保持字形原始形状
- `kSlight`: 轻微提示
- `kNormal`: 标准提示(默认)
- `kFull`: 完全提示,像素对齐

### 斜接限制默认值

`SkIntToScalar(4)` 定义斜接限制为 4。当两条线段以锐角连接时,如果斜接尖角长度超过笔画宽度的 4 倍,系统会自动切换为斜角(bevel)连接,避免产生过长的尖刺。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkFontTypes.h` | 提供 `SkFontHinting` 枚举定义 |
| `SkScalar` (隐式) | 标量类型转换(`SkIntToScalar`) |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `SkPaint` | 初始化绘制属性默认值 |
| `SkFont` | 初始化字体属性默认值 |
| 构建系统 | 编译时配置定制 |
| `SkUserConfig.h` | 用户级配置覆盖 |

## 设计模式与设计决策

### 配置即代码

将配置以 C 预处理器宏形式嵌入代码,避免外部配置文件的依赖,同时保持灵活性。这是 C/C++ 库常见的配置管理模式。

### 防御性编程

使用 `#ifndef` 保护每个宏定义,防止重复定义错误,同时允许外部覆盖。这是头文件编程的最佳实践。

### 分离关注点

将默认值集中到独立文件,避免在核心实现代码中硬编码魔法数字。这提高了代码的可维护性和可配置性。

### 文档驱动设计

文件顶部的注释明确指出"该文件不应直接编辑",引导开发者通过正确的方式(构建系统或 SkUserConfig.h)进行配置。

## 性能考量

### 编译时决策

所有默认值在编译时确定,不产生运行时开销。使用宏而非变量避免额外的内存分配和读取。

### 常量折叠

编译器可以对这些宏进行常量折叠优化,将它们内联到使用处,进一步减少运行时成本。

### 内存占用

由于使用宏定义而非全局变量,不占用程序的静态存储空间。

## 相关文件

| 文件路径 | 关系 |
|---------|------|
| `include/core/SkPaint.h` | 使用默认值初始化 Paint 属性 |
| `include/core/SkFont.h` | 使用默认值初始化 Font 属性 |
| `include/core/SkFontTypes.h` | 提供 Hinting 枚举定义 |
| `SkUserConfig.h` | 用户级配置覆盖接口 |
| `src/core/SkPaintPriv.h` | Paint 内部实现,可能使用这些默认值 |

## 自定义配置示例

### 通过构建系统定制

在编译命令中添加预定义宏:

```bash
g++ -DSkPaintDefaults_TextSize=SkIntToScalar(14) ...
```

### 通过 SkUserConfig.h 定制

在 `SkUserConfig.h` 中添加:

```cpp
#define SkPaintDefaults_TextSize SkIntToScalar(16)
#define SkPaintDefaults_Hinting SkFontHinting::kFull
#define SkPaintDefaults_MiterLimit SkIntToScalar(5)
```

### 使用场景

- **嵌入式系统**: 可能需要更小的默认文本大小以适应低分辨率屏幕
- **高 DPI 显示**: 可能需要更大的默认文本大小
- **打印系统**: 可能需要不同的斜接限制以优化打印效果
- **特定字体系统**: 可能需要调整 Hinting 策略以匹配系统渲染器

## 历史演化

从注释"This file should not be edited directly"可以看出,该设计旨在避免直接修改 Skia 源代码。这种设计允许:

1. **上游维护**: Skia 库的维护者可以安全更新默认值而不影响下游定制
2. **版本控制友好**: 本地修改不会与上游更新冲突
3. **多配置构建**: 同一份源代码可以针对不同平台/产品构建出不同配置

这是大型开源项目的典型配置管理策略,平衡了灵活性、可维护性和版本控制友好性。
