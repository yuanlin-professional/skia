# SkTypeface_proxy - 代理字体类型

> 源文件:
> - `src/ports/SkTypeface_proxy.h`
> - `src/ports/SkTypeface_proxy.cpp`

## 概述

`SkTypeface_proxy` 和 `SkScalerContext_proxy` 实现了字体类型和缩放上下文的代理模式。它们包装一个真实的 `SkTypeface` 和 `SkScalerContext`，将所有方法调用转发给被包装的对象，同时允许在转发链中插入额外的处理逻辑。

这种代理机制主要用于需要在不修改原始字体行为的情况下拦截或包装字体操作的场景，例如跨进程字体渲染、字体监控或测试。

## 架构位置

```
SkTypeface (include/core/)
  |
  v
SkTypeface_proxy (src/ports/)      // 本类
  |
  v
任意 SkTypeface 子类               // 被代理的真实字体

SkScalerContext (src/core/)
  |
  v
SkScalerContext_proxy              // 代理缩放上下文
  |
  v
任意 SkScalerContext 子类          // 被代理的真实上下文
```

## 主要类与结构体

### `SkScalerContext_proxy`

继承自 `SkScalerContext`，代理缩放上下文。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fRealScalerContext` | `unique_ptr<SkScalerContext>` | 被代理的真实缩放上下文 |

### `SkTypeface_proxy`

继承自 `SkTypeface`，代理字体类型。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fRealTypeface` | `sk_sp<SkTypeface>` | 被代理的真实字体 |

构造函数接受真实字体引用、样式和等宽标志。使用 `SkASSERT_RELEASE` 确保真实字体不为空。

## 公共 API 函数

### SkTypeface_proxy 方法（全部转发）

所有 `SkTypeface` 的虚函数重写均直接转发到 `fRealTypeface`：

| 方法 | 转发目标 |
|------|---------|
| `onGetUPEM()` | `fRealTypeface->getUnitsPerEm()` |
| `onOpenStream()` | `fRealTypeface->onOpenStream()` |
| `onMakeClone()` | `fRealTypeface->onMakeClone()` |
| `onGlyphMaskNeedsCurrentColor()` | `fRealTypeface->glyphMaskNeedsCurrentColor()` |
| `onGetVariationDesignPosition()` | `fRealTypeface->onGetVariationDesignPosition()` |
| `onGetVariationDesignParameters()` | `fRealTypeface->onGetVariationDesignParameters()` |
| `onGetFontStyle()` | `fRealTypeface->onGetFontStyle()` |
| `onGetFixedPitch()` | `fRealTypeface->onGetFixedPitch()` |
| `onGetFamilyName()` | `fRealTypeface->onGetFamilyName()` |
| `onGetPostScriptName()` | `fRealTypeface->getPostScriptName()` |
| `onGetResourceName()` | `fRealTypeface->getResourceName()` |
| `onCreateFamilyNameIterator()` | `fRealTypeface->createFamilyNameIterator()` |
| `onGetTableTags()` | `fRealTypeface->readTableTags()` |
| `onGetTableData()` | `fRealTypeface->getTableData()` |
| `onFilterRec()` | `fRealTypeface->onFilterRec()` |
| `onGetFontDescriptor()` | `fRealTypeface->onGetFontDescriptor()` |
| `getGlyphToUnicodeMap()` | `fRealTypeface->getGlyphToUnicodeMap()` |
| `getPostScriptGlyphNames()` | `fRealTypeface->getPostScriptGlyphNames()` |
| `onGetAdvancedMetrics()` | `fRealTypeface->onGetAdvancedMetrics()` |
| `onCharsToGlyphs()` | `fRealTypeface->unicharsToGlyphs()` |
| `onCountGlyphs()` | `fRealTypeface->countGlyphs()` |
| `onGetCTFontRef()` | `fRealTypeface->onGetCTFontRef()` |
| `onGetKerningPairAdjustments()` | `fRealTypeface->onGetKerningPairAdjustments()` |

### `onCreateScalerContext()`

特殊处理：通过 `fRealTypeface->onCreateScalerContextAsProxyTypeface()` 创建真实的缩放上下文，然后包装在 `SkScalerContext_proxy` 中。

### SkScalerContext_proxy 方法（全部转发）

| 方法 | 转发目标 |
|------|---------|
| `generateMetrics()` | `fRealScalerContext->generateMetrics()` |
| `generateImage()` | `fRealScalerContext->generateImage()` |
| `generatePath()` | `fRealScalerContext->generatePath()` |
| `generateDrawable()` | `fRealScalerContext->generateDrawable()` |
| `generateFontMetrics()` | `fRealScalerContext->generateFontMetrics()` |

## 内部实现细节

### 公共/内部 API 差异

注意转发中混合使用了公共 API 和内部 `on` 前缀方法：
- 部分调用使用公共 API（如 `getUnitsPerEm()`、`countGlyphs()`）
- 部分调用直接使用内部方法（如 `onGetFontStyle()`、`onOpenStream()`）

这是因为代理需要绕过某些公共 API 中的额外逻辑，直接访问底层实现。

### 缩放上下文创建

`onCreateScalerContext()` 使用 `onCreateScalerContextAsProxyTypeface()` 方法，该方法允许真实字体创建缩放上下文时使用代理作为关联的字体类型，确保缩放上下文内部引用的是代理而非真实字体。

## 依赖关系

- `SkTypeface`：基类
- `SkScalerContext`：缩放上下文基类
- `SkAdvancedTypefaceMetrics`：高级度量类型
- `SkStream`：流接口
- `SkString`：字符串

## 设计模式与设计决策

1. **代理模式**：完整实现代理模式，所有方法透明转发
2. **所有权语义**：`fRealTypeface` 使用 `sk_sp` 共享所有权；`fRealScalerContext` 使用 `unique_ptr` 独占所有权
3. **构造时断言**：使用 `SkASSERT_RELEASE` 确保真实字体非空（在 release 版中也会触发）
4. **`const_cast` 使用**：`onCreateScalerContext()` 中使用 `const_cast` 将 const this 传递为可变引用

## 性能考量

1. **零开销代理**：所有方法直接转发，无额外计算开销
2. **虚函数调用**：每次访问增加一层虚函数调用（代理层 + 真实层）
3. **无缓存**：代理不缓存任何结果，每次调用都转发

### 公共 API 与内部 API 调用差异

代理层在转发时有意混用了公共 API 和内部（`on` 前缀）方法。具体对比：

| 代理方法 | 调用的真实方法 | 说明 |
|---------|--------------|------|
| `onGetUPEM()` | `getUnitsPerEm()` | 公共 API |
| `onOpenStream()` | `onOpenStream()` | 内部方法 |
| `onMakeClone()` | `onMakeClone()` | 内部方法 |
| `onGetPostScriptName()` | `getPostScriptName()` | 公共 API |
| `onGetResourceName()` | `getResourceName()` | 公共 API |
| `onGetTableTags()` | `readTableTags()` | 公共 API |
| `onCountGlyphs()` | `countGlyphs()` | 公共 API |
| `onCharsToGlyphs()` | `unicharsToGlyphs()` | 公共 API |

使用公共 API 的方法会经过基类的额外逻辑（如参数验证），而直接调用 `on` 方法则绕过这些检查。

### 缩放上下文创建流程

```
SkTypeface_proxy::onCreateScalerContext()
  |
  v
fRealTypeface->onCreateScalerContextAsProxyTypeface(effects, desc, this)
  |  // 真实字体创建缩放上下文，但关联到代理字体
  v
SkScalerContext_proxy(realContext, proxyTypeface, effects, desc)
  |  // 包装真实上下文，设置代理作为关联字体
  v
返回 SkScalerContext_proxy
```

关键点：`onCreateScalerContextAsProxyTypeface` 确保真实字体创建的缩放上下文在内部引用代理字体而非真实字体，维护了代理链的完整性。

## 相关文件

- `src/core/SkScalerContext.h` - 缩放上下文基类
- `include/core/SkTypeface.h` - 字体类型基类
- `src/core/SkAdvancedTypefaceMetrics.h` - 高级度量
- `include/core/SkFontArguments.h` - 字体参数
- `include/core/SkFontParameters.h` - 字体变体参数
