# Skottie.h

> 源文件: `modules/skottie/include/Skottie.h`

## 概述

`Skottie.h` 是 Skottie 模块的主要公共头文件，定义了 Skia 的 Lottie 动画播放引擎的核心 API。该文件包含了 `Animation` 类（动画对象）、`Animation::Builder`（动画构建器）、`Logger`（日志记录器）、`ExpressionManager`（表达式管理器）、`MarkerObserver`（标记观察者）等关键类型。Skottie 能够解析 Lottie/Bodymovin JSON 格式的动画文件，构建内部场景图，并在任意时间点将动画帧渲染到 Skia 画布上。

## 架构位置

该文件位于 `modules/skottie/include/` 目录下，是 Skottie 模块的顶层公共 API 入口。在 Skia 的模块架构中，Skottie 依赖于多个其他模块：

```
应用层
  |
Skottie (modules/skottie) -- Lottie 动画引擎
  |-- skresources (modules/skresources) -- 资源加载
  |-- sksg (modules/sksg) -- 场景图
  |-- skshaper (modules/skshaper) -- 文本排版
  |-- skunicode (modules/skunicode) -- Unicode 支持
  |
Skia Core (include/core, src/core)
```

## 主要类与结构体

### `Animation`
```cpp
class SK_API Animation : public SkNVRefCnt<Animation>
```
- **继承**: `SkNVRefCnt<Animation>`（非虚引用计数）
- **职责**: 表示一个已解析的 Lottie 动画，提供帧跳转（seek）和渲染（render）能力。
- **关键成员**:
  - `fSceneRoot`: 场景图根节点
  - `fAnimators`: 动画器集合
  - `fVersion`: 动画版本字符串
  - `fSize`: 动画尺寸
  - `fInPoint`/`fOutPoint`: 入点/出点（帧索引）
  - `fDuration`: 持续时间（秒）
  - `fFPS`: 帧率

### `Animation::Builder`
```cpp
class SK_API Builder final
```
- **职责**: 动画构建器，通过流式接口配置各种选项（资源提供者、字体管理器、日志器等），然后从 JSON 数据构建 `Animation` 对象。
- **Flags**: `kDeferImageLoading`（延迟图片加载）、`kPreferEmbeddedFonts`（优先使用嵌入字体）
- **Stats**: 构建统计信息（加载时间、JSON 解析时间、场景图构建时间等）

### `Logger`
```cpp
class SK_API Logger : public SkRefCnt
```
- **职责**: 日志记录接口，接收动画解析过程中的错误和警告消息。
- **Level**: `kWarning`, `kError`

### `ExpressionEvaluator<T>` / `ExpressionManager`
```cpp
template <class T>
class SK_API ExpressionEvaluator : public SkRefCnt
class SK_API ExpressionManager : public SkRefCnt
```
- **职责**: After Effects 表达式求值系统。`ExpressionManager` 创建针对不同类型（数值、字符串、数组）的 `ExpressionEvaluator`。

### `MarkerObserver`
```cpp
class SK_API MarkerObserver : public SkRefCnt
```
- **职责**: AE 合成标记（marker）接收接口，在动画构建时接收标记的名称和时间范围。

### `LayerInfo`
```cpp
struct LayerInfo
```
- **成员**: 图层名称（`fName`）、尺寸（`fSize`）、入点（`fInPoint`）、出点（`fOutPoint`）。

## 公共 API 函数

### Animation 静态工厂方法
- `Make(const char* data, size_t length)`: 从内存数据创建动画
- `Make(SkStream*)`: 从流创建动画
- `MakeFromFile(const char path[])`: 从文件创建动画

### Animation::Builder 配置方法（流式接口）
- `setResourceProvider(sk_sp<ResourceProvider>)`: 设置外部资源加载器
- `setFontManager(sk_sp<SkFontMgr>)`: 设置字体管理器
- `setPropertyObserver(sk_sp<PropertyObserver>)`: 设置属性观察者
- `setLogger(sk_sp<Logger>)`: 设置日志记录器
- `setMarkerObserver(sk_sp<MarkerObserver>)`: 设置标记观察者
- `setPrecompInterceptor(sk_sp<PrecompInterceptor>)`: 设置预合成拦截器
- `setExpressionManager(sk_sp<ExpressionManager>)`: 设置表达式管理器
- `setTextShapingFactory(sk_sp<SkShapers::Factory>)`: 设置文本排版工厂

### Animation::Builder 构建方法
- `make(SkStream*)`: 从流构建动画
- `make(const char* data, size_t length)`: 从数据构建动画
- `makeFromFile(const char path[])`: 从文件构建动画

### Animation::Builder 查询方法
- `getStats() const -> const Stats&`: 获取构建统计
- `getSlotManager() const -> const sk_sp<SlotManager>&`: 获取插槽管理器
- `getLayerInfo() const -> SkSpan<const LayerInfo>`: 获取图层信息

### Animation 渲染方法
- `render(SkCanvas*, const SkRect* dst = nullptr) const`: 渲染当前帧
- `render(SkCanvas*, const SkRect* dst, RenderFlags) const`: 带标志的渲染

### Animation 帧跳转方法
- `seek(SkScalar t, ...)`: [已废弃] 归一化时间跳转（0=第一帧，1=最后一帧）
- `seekFrame(double t, ...)`: 按帧索引跳转（支持小数帧）
- `seekFrameTime(double t, ...)`: 按时间跳转（秒）

### Animation 属性查询
- `duration() const -> double`: 动画时长（秒）
- `fps() const -> double`: 帧率
- `inPoint() const -> double`: 入点帧索引
- `outPoint() const -> double`: 出点帧索引
- `version() const -> const SkString&`: 动画版本
- `size() const -> const SkSize&`: 动画尺寸

### RenderFlag 枚举
- `kSkipTopLevelIsolation`: 在已知透明缓冲区中跳过顶层隔离
- `kDisableTopLevelClipping`: 禁用内容裁剪到动画边界

## 内部实现细节

- **非虚引用计数**: `Animation` 使用 `SkNVRefCnt` 而非 `SkRefCnt`，避免虚函数表开销。
- **场景图渲染**: `render()` 方法将动画内容委托给 `fSceneRoot->render(canvas)` 执行。
- **顶层隔离**: 当动画使用了非平凡混合模式（`kRequiresTopLevelIsolation`），渲染时需要额外的 `saveLayer` 来保证混合正确性。
- **帧跳转语义**: `seekFrame` 将帧索引转换为合成时间（`fInPoint + t`），然后 `SkTPin` 到有效范围，`outPoint` 是排除的（exclusive）。

## 依赖关系

- **Skia 核心**: `SkRefCnt`, `SkScalar`, `SkSize`, `SkSpan`, `SkString`, `SkTypes`, `SkCanvas`, `SkStream`, `SkRect`, `SkFontMgr`
- **`modules/skresources`**: `ResourceProvider`, `ImageAsset`
- **`modules/skottie/include/ExternalLayer.h`**: `PrecompInterceptor`
- **`modules/skottie/include/SkottieProperty.h`**: `PropertyObserver`
- **`modules/skottie/include/SlotManager.h`**: `SlotManager`
- **`modules/sksg`**: `InvalidationController`, `RenderNode`
- **`modules/skshaper`**: `SkShapers::Factory`

## 设计模式与设计决策

- **Builder 模式**: `Animation::Builder` 使用流式接口（方法链）配置动画构建参数，将复杂的构造过程与最终对象的表示分离。
- **不可变动画对象**: `Animation` 构造后其结构不变（`const` 成员），只有动画状态（当前帧）会通过 `seek` 改变。
- **策略模式集合**: `ResourceProvider`、`Logger`、`PropertyObserver`、`MarkerObserver`、`PrecompInterceptor`、`ExpressionManager`、`SkShapers::Factory` 都是可选的策略对象。
- **IWYU pragma**: 头文件包含了一些即将移除的传递依赖（`SkFontMgr`, `ExternalLayer.h` 等），标记了 `IWYU pragma: keep`。
- **类型别名**: `ImageAsset` 和 `ResourceProvider` 在 `skottie` 命名空间中做了别名，简化使用。

## 性能考量

- **JSON 解析性能**: `Builder::Stats` 记录了 JSON 解析时间和场景图构建时间，便于性能分析。
- **帧跳转的 O(n) 复杂度**: `seekFrame` 遍历所有 `fAnimators` 执行 seek，复杂度与动画器数量成正比。
- **渲染裁剪**: 默认裁剪到动画边界，避免绘制越界内容的浪费。
- **延迟图片加载**: `kDeferImageLoading` 标志允许将图片解码推迟到实际需要时，减少初始加载时间。
- **顶层隔离优化**: 仅在使用非平凡混合模式时才创建额外的渲染层，避免不必要的合成开销。

## 相关文件

- `modules/skottie/src/Skottie.cpp` -- Animation 和 Builder 的实现
- `modules/skottie/src/SkottiePriv.h` -- AnimationBuilder 内部实现
- `modules/skottie/include/SkottieProperty.h` -- 属性系统
- `modules/skottie/include/SlotManager.h` -- 插槽管理器
- `modules/skottie/include/ExternalLayer.h` -- 外部图层
- `modules/skottie/include/TextShaper.h` -- 文本排版
- `modules/skresources/include/SkResources.h` -- 资源加载
- `modules/sksg/include/SkSGRenderNode.h` -- 场景图渲染节点
