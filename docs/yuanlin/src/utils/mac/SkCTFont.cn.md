# SkCTFont - macOS/iOS CoreText 字体工具

> 源文件:
> - `src/utils/mac/SkCTFont.h`
> - `src/utils/mac/SkCTFont.cpp`

## 概述

SkCTFont 是 Skia 在 macOS 和 iOS 平台上与 Apple CoreText 字体系统交互的工具模块。它提供了三个核心功能：检测系统字体平滑行为 (`SkCTFontGetSmoothBehavior`)、获取系统字体的 CSS 权重到 CoreText 权重的映射表 (`SkCTFontGetNSFontWeightMapping`)，以及获取数据字体（从字体数据创建的字体）的权重映射表 (`SkCTFontGetDataFontWeightMapping`)。

## 架构位置

```
Skia Apple 字体后端
├── SkTypeface_mac_ct (macOS/iOS 字体接口)
│   └── SkCTFont (本模块 - CoreText 字体工具)
│       ├── 字体平滑行为检测
│       └── 字体权重映射
├── SkCTFontCreateExactCopy (精确字体拷贝)
├── SkScalerContext_mac_ct (字形渲染)
└── CoreText / CoreGraphics (系统层)
```

## 主要类与结构体

### `SkCTFontSmoothBehavior` 枚举
```cpp
enum class SkCTFontSmoothBehavior {
    none,      // SmoothFonts 无效果
    some,      // SmoothFonts 有效果，但无子像素覆盖
    subpixel,  // SmoothFonts 有效果且提供子像素覆盖
};
```
- 描述系统字体平滑功能的三种行为模式。

### `SkCTFontWeightMapping` 类型别名
```cpp
using SkCTFontWeightMapping = const CGFloat[11];
```
- 11 个元素的数组，对应 CSS 权重 0, 100, 200, ..., 1000 到 CoreText [-1, 1] 权重范围的映射。

## 公共 API 函数

### `SkCTFontGetSmoothBehavior`
```cpp
SkCTFontSmoothBehavior SkCTFontGetSmoothBehavior();
```
- **功能**: 检测当前系统的字体平滑行为。
- **结果缓存**: 使用静态变量缓存结果，仅首次调用时执行检测。
- **检测方法**: 创建一个嵌入的测试字体 (SpiderSymbol TrueType)，分别在开启和关闭平滑的两个位图上下文中渲染相同字形，然后比较像素差异。

### `SkCTFontGetNSFontWeightMapping`
```cpp
SkCTFontWeightMapping& SkCTFontGetNSFontWeightMapping();
```
- **功能**: 返回系统字体的 CSS 权重到 CoreText 权重的映射表。
- **实现**: 使用 `dlsym` 动态查找 NSFontWeight 常量 (如 `NSFontWeightRegular`, `NSFontWeightBold` 等)。
- **回退**: 如果动态查找失败，使用硬编码的默认映射值。
- **平台差异**: macOS 使用 `NS` 前缀，iOS 使用 `UI` 前缀。

### `SkCTFontGetDataFontWeightMapping`
```cpp
SkCTFontWeightMapping& SkCTFontGetDataFontWeightMapping();
```
- **功能**: 返回从数据创建的字体的 CSS 权重到 CoreText 权重映射表。
- **实现**: 使用嵌入的测试字体，修改其 OS/2 表的 `usWeightClass` 字段，然后查询 CoreText 返回的权重值。

## 内部实现细节

### 字体平滑检测算法
1. 创建两个 16x16 的 RGBA 位图上下文。
2. 从嵌入的 SpiderSymbol TrueType 字体数据创建 CTFont。
3. 在两个上下文中分别关闭和开启字体平滑后渲染同一字形。
4. 逐像素比较：
   - 如果 R != G 或 R != B，说明存在子像素颜色差异，返回 `subpixel`。
   - 如果两个位图的像素不同但通道间相等，返回 `some`。
   - 如果完全相同，返回 `none`。

### 数据字体权重映射探测
1. 使用嵌入的 SpiderSymbol 字体数据。
2. 解析 SFNT 头部，定位 OS/2 表。
3. 循环设置 `usWeightClass` 为 11, 100, 200, ..., 1000。
4. 使用修改后的数据创建 CTFont，查询其 `kCTFontWeightTrait`。
5. 验证权重值严格单调递增。
6. 特殊处理 `usWeightClass=0` 的情况：macOS 15.0+ 会将其钉到 1，因此使用 11 作为最低探测值，然后线性外推到 0。

### 嵌入测试字体
模块内嵌了一个完整的 TrueType 字体文件 (`kSpiderSymbol_ttf`)，这是一个在 FontForge 中绘制的蜘蛛符号字体。该字体被用于平滑行为检测和权重映射探测，以确保测试的一致性和可重复性。

### 系统版本适配
代码中包含大量对不同 macOS 版本行为差异的处理：
- macOS 10.9-10.11: NSFontWeight 常量的可用性变化。
- macOS 10.14 及更早: CFDataGetBytePtr 缓存问题，需要每次创建数据的新副本。
- macOS 10.14 及更早: CTFontDescriptor 不完整，需要通过创建 CTFont 再获取 Descriptor。
- macOS 15.0+: usWeightClass=0 被钉到 1 的行为变化。

## 依赖关系

- `include/core/SkData.h`: 数据包装。
- `include/core/SkRefCnt.h`: 引用计数。
- `include/private/base/SkOnce.h`: 线程安全的一次性初始化。
- `src/sfnt/SkOTTable_OS_2.h`: OpenType OS/2 表定义。
- `src/sfnt/SkSFNTHeader.h`: SFNT 文件头解析。
- `src/utils/mac/SkUniqueCFRef.h`: Core Foundation 对象的 RAII 包装。
- CoreText / CoreGraphics / CoreFoundation (系统框架)。
- `<dlfcn.h>`: 动态符号查找 (`dlsym`)。

## 设计模式与设计决策

1. **运行时检测**: 使用实际渲染比较来检测字体平滑行为，而非依赖版本号判断，因为该行为可能因系统设置而改变。
2. **经验性探测**: 权重映射通过实际修改字体数据并查询系统返回值来获取，而非硬编码，以适应 Apple 可能的静默更改。
3. **惰性初始化**: 所有三个函数都使用静态变量和 `SkOnce` 进行惰性初始化，避免不必要的开销。
4. **版本兼容策略**: 代码中大量的版本特定处理体现了对 Apple 平台 API 行为不稳定性的适应。

## 性能考量

1. **一次性开销**: 三个函数的检测/探测逻辑都只在首次调用时执行一次，后续调用直接返回缓存值。
2. **多次字体创建**: `SkCTFontGetDataFontWeightMapping` 需要创建 11 个临时字体来探测权重值，首次调用时有一定开销。
3. **位图渲染开销**: 平滑行为检测需要渲染两个小位图并逐像素比较，但仅 16x16 像素，开销很小。

## 相关文件

- `src/utils/mac/SkCTFontCreateExactCopy.h/.cpp`: 字体精确拷贝。
- `src/utils/mac/SkUniqueCFRef.h`: Core Foundation 对象 RAII 包装。
- `src/ports/SkTypeface_mac_ct.h/.cpp`: macOS CoreText 字体接口。
- `src/sfnt/SkOTTable_OS_2.h`: OpenType OS/2 表结构定义。
