# SkCTFontCreateExactCopy - CoreText 字体精确拷贝

> 源文件:
> - `src/utils/mac/SkCTFontCreateExactCopy.h`
> - `src/utils/mac/SkCTFontCreateExactCopy.cpp`

## 概述

SkCTFontCreateExactCopy 提供了一个在 macOS/iOS 上安全地调整 CTFont 大小的函数。直接使用 CoreText API 调整字体大小可能会无意间改变光学大小 (optical size)、字形度量或底层字体数据。此函数通过精心设置 CTFontDescriptor 属性来避免这些副作用。

## 架构位置

```
Skia Apple 字体后端
├── SkTypeface_mac_ct / SkScalerContext_mac_ct
│   └── SkCTFontCreateExactCopy (本模块 - 安全的字体大小调整)
│       ├── 光学大小 (opsz) 属性控制
│       └── 字距追踪 (trak) 属性控制
└── CoreText API
```

## 主要类与结构体

### `OpszVariation` (前向声明)
- 定义在 `SkTypeface_mac_ct.h` 中。
- 包含 `isSet` (bool) 和 `value` (double) 字段，用于指定光学大小变化轴的值。

## 公共 API 函数

### `SkCTFontCreateExactCopy`
```cpp
SkUniqueCFRef<CTFontRef> SkCTFontCreateExactCopy(CTFontRef baseFont,
                                                  CGFloat textSize,
                                                  OpszVariation opsz);
```
- **功能**: 创建指定大小的字体副本，同时保持光学大小和其他属性的一致性。
- **参数**:
  - `baseFont`: 原始字体。
  - `textSize`: 目标字体大小。
  - `opsz`: 光学大小变化轴设置。
- **返回值**: 新的 CTFont 引用（RAII 包装）。

## 内部实现细节

### 光学大小处理 (`add_opsz_attr`)
```cpp
static void add_opsz_attr(CFMutableDictionaryRef attr, double opsz);
```
- 使用未文档化的 `NSCTFontOpticalSizeAttribute` 属性设置光学大小。
- 此属性在 macOS 10.15+ 的 opsz 优先级中排第一，确保了最高的控制力。

**macOS 的 opsz 优先级** (从高到低):
1. CTFontDescriptor 中的 `kCTFontOpticalSizeAttribute` (未文档化)
2. opsz 轴默认值（当属性为 'none' 时）
3. CGFont 上的 opsz 变化
4. CTFontDescriptor 中的 `kCTFontVariationAttribute` (10.10 崩溃)
5. 请求的字体大小

### 字距追踪禁用 (`add_notrak_attr`)
```cpp
static void add_notrak_attr(CFMutableDictionaryRef attr);
```
- 设置未文档化的 `NSCTFontUnscaledTrackingAttribute` 为 0。
- 禁用 'trak' 表对字距的调整，确保字形排版精确。

### opsz 保持策略
当 `opsz.isSet` 为 false 时：
1. 尝试从原始字体获取当前的 `NSCTFontOpticalSizeAttribute` 值。
2. 如果获取失败（值为 null、非数字或 <= 0），使用原始字体大小作为 opsz 值。
3. 这保证了在调整大小时不会改变光学大小，维护字形 ID 的稳定性。

### macOS 版本兼容性
- **10.10-10.14**: 系统字体 SFNSText/SFNSDisplay 由两个不同字体组成，光学大小 < 20 使用 SFNSText，否则使用 SFNSDisplay。字形 ID 在这两者之间不可互换。
- **10.15+**: 使用带 opsz 轴的可变字体替代了双字体方案。
- 代码的设计目标是在所有版本上都保持字形 ID 的稳定性。

## 依赖关系

- `src/ports/SkTypeface_mac_ct.h`: `OpszVariation` 结构体定义。
- `src/utils/mac/SkUniqueCFRef.h`: Core Foundation 对象 RAII 包装。
- CoreText / CoreFoundation (系统框架)。

## 设计模式与设计决策

1. **属性保持策略**: 该函数的核心设计目标是"只改变大小，不改变其他任何东西"。通过显式设置 opsz 和 trak 属性来防止 CoreText 的自动调整。
2. **未文档化 API 使用**: 使用 `NSCTFontOpticalSizeAttribute` 和 `NSCTFontUnscaledTrackingAttribute` 这两个未文档化的属性，因为 CoreText 的公共 API 不提供足够的控制力。
3. **防御性编码**: 对 opsz 值获取的多重 null 检查和类型检查，防止 CoreText 返回意外数据。

## 性能考量

- 每次调用都创建临时的 CFMutableDictionary 和 CTFontDescriptor，开销较小。
- `CTFontCreateCopyWithAttributes` 是底层的字体创建操作，性能取决于 CoreText 实现。

## 相关文件

- `src/utils/mac/SkCTFont.h/.cpp`: CoreText 字体检测工具。
- `src/utils/mac/SkUniqueCFRef.h`: CF 对象 RAII 包装。
- `src/ports/SkTypeface_mac_ct.h/.cpp`: macOS 字体接口实现，调用本函数。
