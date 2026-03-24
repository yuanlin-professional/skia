# SkTypeface_mac

> 源文件: `include/ports/SkTypeface_mac.h`

## 概述

`SkTypeface_mac` 是 Skia 在 macOS 和 iOS 平台上的字体管理接口，提供与 Apple CoreText 框架的互操作能力。它允许从 CoreText 的 `CTFontRef` 创建 Skia 字体面对象，以及反向获取底层的 `CTFontRef` 句柄。该接口是 Skia 跨平台字体抽象在 Apple 平台的具体实现。

## 架构位置

该头文件位于 `include/ports/` 目录，属于 Skia 的平台移植层(Ports Layer)。它是 macOS 和 iOS 平台字体子系统的公开接口，与 Windows 的 `SkTypeface_win.h` 对应，提供平台特定的字体创建和查询功能。

## 条件编译

接口仅在 Apple 平台可用：
```cpp
#if defined(SK_BUILD_FOR_MAC) || defined(SK_BUILD_FOR_IOS)
// 所有 API 定义
#endif
```

根据平台引入不同的框架：
- **macOS**: 引入 `ApplicationServices/ApplicationServices.h`(包含 CoreText)
- **iOS**: 引入 `CoreText/CoreText.h`(iOS 上 ApplicationServices 不可用)

## 公共 API 函数

### `SkMakeTypefaceFromCTFont`

```cpp
SK_API extern sk_sp<SkTypeface> SkMakeTypefaceFromCTFont(CTFontRef);
```

- **功能**: 从 CoreText 字体引用创建 Skia 字体面对象
- **参数**: `CTFontRef` - CoreText 字体对象句柄
- **返回值**: `sk_sp<SkTypeface>` 智能指针，持有新创建的字体面对象
- **所有权**:
  - 返回新的引用(Skia 使用引用计数管理生命周期)
  - CoreText 的 `CTFontRef` 也是引用计数的，Skia 会持有自己的引用
  - 调用者可以在调用后释放原始 `CTFontRef`(如果不再需要)
- **行为特征**:
  - 提取字体的元数据(族名、样式、权重、倾斜度)
  - 创建与 `CTFontRef` 完全对应的 `SkTypeface`
  - 字体大小信息不存储在 `SkTypeface` 中(由 `SkFont` 管理)

### `SkTypeface_GetCTFontRef`

```cpp
SK_API extern CTFontRef SkTypeface_GetCTFontRef(const SkTypeface* face);
```

- **功能**: 从 Skia 字体面对象获取底层的 CoreText 字体引用
- **参数**: `face` - Skia 字体面对象指针
- **返回值**: `CTFontRef` - CoreText 字体对象句柄
- **所有权**:
  - **关键**: 返回的 `CTFontRef` 在源 `SkTypeface` 销毁时失效
  - 调用者不应该手动 `CFRelease` 返回的句柄
  - 如需长期持有，应调用 `CFRetain`
- **弃用状态**: 该方法已标记为弃用(deprecated)
- **限制使用场景**:
  - 仅供 Blink(Chrome 渲染引擎) macOS 遗留代码使用
  - 特殊情况: AAT 字体文本整形、剪贴板处理、字体回退
  - 参考 Skia Issue #3408
- **警告**: 新代码不应使用此方法，应通过 Skia 的高层 API 完成所有操作

## 内部实现细节

### CTFontRef 到 SkTypeface 映射

`SkMakeTypefaceFromCTFont` 内部步骤：
1. **提取字体属性**: 调用 CoreText API 获取字体族名、样式名称
   - `CTFontCopyFamilyName()`
   - `CTFontCopyName(kCTFontStyleNameKey)`
2. **样式分析**: 解析字体特征(`CTFontDescriptor`)
   - 权重(weight): 100-900 → `SkFontStyle::Weight`
   - 倾斜度(slant): 正常/斜体 → `SkFontStyle::Slant`
   - 宽度(width): 正常/窄/宽 → `SkFontStyle::Width`
3. **创建 SkTypeface**: 使用提取的信息构造 Skia 字体对象
4. **持有引用**: 内部 `CFRetain(CTFontRef)` 以保持字体有效

### SkTypeface 到 CTFontRef 反向查找

`SkTypeface_GetCTFontRef` 实现：
- **直接存储**: `SkTypeface` 内部存储原始 `CTFontRef`(如果由 `SkMakeTypefaceFromCTFont` 创建)
- **重建**: 如果 `SkTypeface` 是通过其他方式创建(如字体管理器匹配)，可能需要重建 `CTFontRef`
- **生命周期绑定**: 返回的 `CTFontRef` 生命周期与 `SkTypeface` 绑定

### CoreText 集成

CoreText 是 Apple 的高级文本渲染框架：
- **字体加载**: 支持系统字体、用户安装字体、应用捆绑字体
- **文本整形**: 处理复杂文本布局(阿拉伯文、印地文等)
- **字形渲染**: 高质量抗锯齿渲染

Skia 在 Apple 平台使用 CoreText 作为字体后端，而非直接使用 FreeType。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `SkTypeface` | 字体面基类 |
| CoreFoundation | Apple 基础框架(引用计数、字符串等) |
| CoreText | Apple 文本渲染框架(字体管理和渲染) |
| ApplicationServices (macOS) | macOS 图形和文本服务 |

### 被依赖的模块

- **macOS 应用**: 所有在 macOS 上使用 Skia 的应用
- **iOS 应用**: 所有在 iOS 上使用 Skia 的应用
- **跨平台框架**: Chromium、Flutter、Electron 等
- **遗留集成**: Blink 渲染引擎的 macOS 特定代码

## 设计模式与设计决策

### 平台原生集成

与 Windows 的 GDI/DirectWrite 不同，Apple 平台只有一个官方字体 API:
- **单一路径**: 所有字体操作通过 CoreText
- **系统一致性**: 渲染效果与系统应用完全一致
- **简化设计**: 不需要多个字体后端(如 Windows 的 GDI vs DirectWrite)

### 弃用 GetCTFontRef

`SkTypeface_GetCTFontRef` 被标记为弃用的原因：
- **抽象泄漏**: 暴露平台特定类型破坏了 Skia 的跨平台抽象
- **维护负担**: 需要维护内部 `CTFontRef` 与 `SkTypeface` 的同步
- **历史遗留**: 最初为解决 Blink 的特殊需求而添加
- **现代替代**: Skia 的高层 API 现在可以处理绝大多数场景

### 引用计数互操作

Skia 和 CoreFoundation 都使用引用计数，但语义不同：
- **CoreFoundation**: 手动 `CFRetain`/`CFRelease`
- **Skia**: 智能指针 `sk_sp<T>` 自动管理
- **桥接**: `SkMakeTypefaceFromCTFont` 自动处理引用计数转换

## 性能考量

### 字体创建开销

- **SkMakeTypefaceFromCTFont**: 轻量级操作(~0.1 毫秒)，主要是元数据提取
- **系统查找**: 如果 `CTFontRef` 本身是通过查找创建的，开销在 CoreText 层
- **缓存建议**: 应用应缓存 `SkTypeface` 对象，避免重复创建

### CoreText 性能特征

- **字形缓存**: CoreText 内部缓存渲染的字形
- **子像素抗锯齿**: macOS 支持子像素渲染(retina 显示器上自动优化)
- **硬件加速**: 某些操作可能使用 GPU 加速

### 与其他平台对比

| 平台 | 字体后端 | 渲染质量 | 性能 |
|------|---------|---------|------|
| macOS/iOS | CoreText | 优秀 | 快 |
| Windows | DirectWrite | 优秀 | 快 |
| Windows | GDI | 一般 | 慢 |
| Linux | FreeType | 良好 | 中 |

## 平台相关说明

### macOS vs iOS 差异

- **框架引入**: macOS 使用 `ApplicationServices`，iOS 使用 `CoreText` 直接引入
- **字体可用性**: iOS 内置字体较少，部分 macOS 字体不可用
- **沙盒限制**: iOS 应用无法访问系统字体目录，只能通过 CoreText API

### Retina 显示器

- **自动处理**: CoreText 自动适配 Retina 显示器的高 DPI
- **缩放因子**: Skia 通过 CoreText 获得正确的字形，无需手动处理
- **清晰度**: 在 Retina 屏幕上文本渲染非常清晰

### AAT 字体特性

Apple Advanced Typography (AAT) 是 macOS 专有的字体技术：
- **高级排版**: 支持复杂连字、上下文替换
- **Blink 需求**: 这是 `SkTypeface_GetCTFontRef` 仍被保留的主要原因之一
- **OpenType 兼容**: 现代字体更多使用 OpenType，AAT 较少使用

## 使用示例

### 从 CTFontRef 创建 Skia 字体

```cpp
// 获取系统字体
CTFontRef ctFont = CTFontCreateWithName(CFSTR("Helvetica"), 16.0, nullptr);

// 转换为 Skia 字体
sk_sp<SkTypeface> typeface = SkMakeTypefaceFromCTFont(ctFont);

// 使用 Skia 字体
SkFont font(typeface, 16.0f);
canvas->drawString("Hello", 0, 0, font, paint);

// 释放 CoreText 字体(Skia 已持有自己的引用)
CFRelease(ctFont);
```

### 反向获取 CTFontRef(不推荐)

```cpp
sk_sp<SkTypeface> typeface = /* ... */;

// 获取底层 CTFontRef(弃用 API)
CTFontRef ctFont = SkTypeface_GetCTFontRef(typeface.get());

// 如需长期持有，必须 retain
CFRetain(ctFont);  // 保持引用

// 使用 CoreText API
CFStringRef familyName = CTFontCopyFamilyName(ctFont);
// ...

// 释放
CFRelease(ctFont);
CFRelease(familyName);
```

### 推荐的现代方式

```cpp
// 不直接使用 CTFontRef，通过 Skia API 完成所有操作
sk_sp<SkFontMgr> fontMgr = SkFontMgr::RefDefault();  // macOS 上是 CoreText 后端
sk_sp<SkTypeface> typeface = fontMgr->matchFamilyStyle("Helvetica", SkFontStyle::Normal());
SkFont font(typeface, 16.0f);
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkTypeface.h` | 字体面基类定义 |
| `include/core/SkFontMgr.h` | 字体管理器基类 |
| `include/ports/SkTypeface_win.h` | Windows 平台对应接口 |
| `src/ports/SkFontHost_mac.cpp` | macOS 字体实现(CoreText) |
| `src/ports/SkFontMgr_mac_ct.cpp` | CoreText 字体管理器实现 |
| `include/core/SkFont.h` | 高层字体 API |
