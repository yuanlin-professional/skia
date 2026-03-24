# Skottie.cpp

> 源文件: `modules/skottie/src/Skottie.cpp`

## 概述

`Skottie.cpp` 是 Skottie 动画引擎的核心实现文件，包含了 `Animation` 类、`Animation::Builder` 类以及内部 `AnimationBuilder` 的关键方法实现。该文件实现了从 Lottie JSON 数据到可渲染动画对象的完整构建流程，以及动画的帧跳转和渲染逻辑。它是 Skottie 模块中代码量最大、最核心的实现文件之一。

## 架构位置

该文件位于 `modules/skottie/src/` 目录下，是 Skottie 模块的核心实现。在整体架构中：

```
公共 API 层:  Animation::Builder::make() / Animation::render() / Animation::seekFrame()
                        |
实现层:      Skottie.cpp (本文件)
                        |
                +-------+-------+--------+
                |       |       |        |
    AnimationBuilder  Composition  Layer  Text/Shape/Effect 子系统
                |
    场景图 (sksg) + 动画器 (Animator)
```

## 主要类与结构体

### `SceneGraphRevalidator`（实现）
- `setRoot()`: 设置场景图根节点
- `revalidate()`: 通过 `fRoot->revalidate(nullptr, SkMatrix::I())` 重验证场景图

### `OpacityAdapter`
```cpp
class OpacityAdapter final : public DiscardableAdapterBase<OpacityAdapter, sksg::OpacityEffect>
```
- **职责**: 不透明度动画适配器，将 Lottie 的不透明度值（0-100）转换为场景图的不透明度（0-1）。
- **绑定**: 从 JSON 对象的 `"o"` 字段绑定不透明度值。

### `NullResourceProvider`（内部）
```cpp
class NullResourceProvider final : public ResourceProvider
```
- **职责**: 空资源提供者，当未设置 `ResourceProvider` 时作为默认值使用。

## 公共 API 函数

### AnimationBuilder 核心实现

#### `AnimationBuilder::log()`
```cpp
void log(Logger::Level lvl, const skjson::Value* json, const char fmt[], ...) const;
```
- **功能**: 格式化日志消息并发送到注册的 Logger。使用 `vsnprintf` 格式化，超过 1024 字符的消息会被截断。

#### `AnimationBuilder::attachOpacity()`
```cpp
sk_sp<sksg::RenderNode> attachOpacity(const skjson::ObjectValue&, sk_sp<sksg::RenderNode>) const;
```
- **功能**: 为渲染节点附加不透明度效果。优化逻辑：若适配器是静态的且不透明度 >= 1，且未被属性观察者请求，则丢弃该效果节点（因为完全不透明无需额外节点）。

#### `AnimationBuilder::parse()`
```cpp
AnimationInfo parse(const skjson::ObjectValue& jroot);
```
- **功能**: 解析 Lottie JSON 根对象，构建完整的动画场景图。
- **流程**:
  1. 分发标记 (`markers`)
  2. 创建动画器作用域 (`AutoScope`)
  3. 创建属性追踪上下文 (`AutoPropertyTracker`)
  4. 解析资产 (`assets`)
  5. 解析字体 (`fonts`) 和字符 (`chars`)
  6. 获取插槽根 (`slots`)
  7. 通过 `CompositionBuilder` 构建场景图
  8. 设置重验证器根节点并执行初始重验证

#### 属性分发方法实现

- `dispatchColorProperty()`: 通过 `PropertyObserver::onColorProperty` 分发颜色属性
- `dispatchOpacityProperty()`: 分发不透明度属性
- `dispatchTextProperty()`: 分发文本属性，同时处理插槽 ID (`sid`) 的注册
- `dispatchTransformProperty()`: 分发变换属性

### Animation::Builder 实现

#### 流式配置方法
`setResourceProvider`, `setFontManager`, `setPropertyObserver`, `setLogger`, `setMarkerObserver`, `setPrecompInterceptor`, `setExpressionManager`, `setTextShapingFactory` -- 每个方法保存对应的 `sk_sp` 并返回 `*this` 以支持方法链。

#### `Animation::Builder::make(SkStream*)`
- **功能**: 从流构建动画。
- **实现**: 检查流是否有长度信息，将流内容读入 `SkData`，然后委托给数据版本。

#### `Animation::Builder::make(const char*, size_t)`
- **功能**: 从 JSON 数据构建动画的核心方法。
- **流程**:
  1. 确保资源提供者存在（无则使用 `NullResourceProvider`）
  2. 解析 JSON DOM
  3. 提取动画元数据（版本、尺寸、帧率、入点、出点、持续时间）
  4. 验证参数合法性
  5. 选择排版工厂（有则使用，无则使用 `SkShapers::Primitive::Factory()`）
  6. 创建 `AnimationBuilder` 并调用 `parse()`
  7. 记录构建时间统计
  8. 创建 `Animation` 对象

### Animation 实现

#### `Animation::render()`
```cpp
void render(SkCanvas* canvas, const SkRect* dstR, RenderFlags renderFlags) const;
```
- **功能**: 渲染当前帧到画布。
- **实现**:
  1. 保存画布状态 (`SkAutoCanvasRestore`)
  2. 如果指定了目标矩形，计算并应用变换矩阵
  3. 除非禁用，裁剪到动画边界
  4. 如果需要顶层隔离，创建透明层 (`saveLayer`)
  5. 调用 `fSceneRoot->render(canvas)`

#### `Animation::seekFrame(double, InvalidationController*)`
```cpp
void seekFrame(double t, sksg::InvalidationController* ic = nullptr);
```
- **功能**: 按帧索引跳转动画状态。
- **实现**: 将帧索引加上入点，钳制到 `[fInPoint, lastValidFrame]` 范围，然后遍历所有动画器执行 seek，最后重验证场景图。
- **语义**: `outPoint` 是排除的（exclusive），通过 `std::nextafterf` 获取最后一个有效帧。

#### `Animation::seekFrameTime(double, InvalidationController*)`
- **功能**: 按时间（秒）跳转。内部转换为帧索引后调用 `seekFrame`。

## 内部实现细节

- **时间统计**: 使用 `std::chrono::steady_clock` 精确测量 JSON 解析时间和场景图构建时间。
- **Duration 计算**: `duration = (outPoint - inPoint) / fps`，使用 `sk_ieee_float_divide` 避免除零。
- **出点排除语义**: AE/Lottie 中 `outPoint` 是排除的，因此最后有效帧是 `nextafterf(fOutPoint, fInPoint)`。
- **属性分发中的插槽注册**: `dispatchTextProperty` 不仅分发给 `PropertyObserver`，还检查 JSON 中的 `"sid"` 字段以注册到 `SlotManager`。
- **不透明度优化**: `attachOpacity` 中静态且完全不透明的节点会被丢弃，减少场景图复杂度。
- **TRACE_EVENT**: 在关键方法中使用 `TRACE_EVENT0` 宏进行性能追踪。

## 依赖关系

- **Skia 核心**: `SkCanvas`, `SkData`, `SkFontMgr`, `SkMatrix`, `SkRect`, `SkStream`
- **JSON**: `SkJSONReader.h` (skjson DOM)
- **公共 Skottie**: `Skottie.h`, `ExternalLayer.h`, `SkottieProperty.h`, `SlotManager.h`
- **内部 Skottie**: `Adapter.h`, `Composition.h`, `SkottieJson.h`, `SkottiePriv.h`, `SkottieValue.h`, `Transform.h`, `Animator.h`, `TextAdapter.h`
- **场景图**: `SkSGOpacityEffect.h`, `SkSGRenderNode.h`
- **排版**: `SkShaper_factory.h`
- **工具**: `SkTHash.h`, `SkTraceEvent.h`

## 设计模式与设计决策

- **Builder 模式**: `Animation::Builder` 使用流式接口配置参数，最终通过 `make()` 方法创建 `Animation` 对象。
- **适配器模式**: `OpacityAdapter` 将 Lottie 的 0-100 不透明度映射到 sksg 的 0-1 不透明度。
- **不可变对象**: `Animation` 的核心成员（`fSceneRoot`, `fAnimators`, `fVersion` 等）都是 `const` 的，帧跳转通过修改动画器状态而非动画对象本身来实现。
- **两阶段构建**: 外部 `Animation::Builder` 负责 I/O 和参数准备，内部 `AnimationBuilder` 负责实际的 JSON 解析和场景图构建。
- **延迟初始化**: 默认排版工厂在 `make()` 中延迟初始化为 `Primitive::Factory()`，仅在用户未指定时使用。

## 性能考量

- **JSON 解析时间追踪**: 通过 `Stats` 记录 JSON 解析和场景图构建时间，便于性能诊断。典型的 Lottie 文件解析时间在数毫秒到数十毫秒之间。
- **不透明度节点裁剪**: `attachOpacity` 中完全不透明（>= 1）的静态节点被丢弃，减少渲染时的场景图节点遍历数量。这对于大量形状图层的动画效果显著。
- **seekFrame 的 O(n) 遍历**: 每次帧跳转遍历所有动画器，复杂度与动画属性数量（`fAnimators.size()`）成正比。这是动画播放的核心热路径，动画器数量直接影响播放性能。
- **saveLayer 成本**: 顶层隔离（`saveLayer`）会增加一次 GPU 纹理分配和混合操作，仅在动画使用了非平凡混合模式时启用（通过 `kRequiresTopLevelIsolation` 标志检测）。
- **TRACE_EVENT**: 在 `make`, `render`, `seekFrame` 等关键方法中使用 `TRACE_EVENT0` 宏进行性能追踪，允许使用 Chrome Tracing 等工具分析热点。
- **SkAutoCanvasRestore**: `render()` 中使用 RAII 画布状态保存，确保渲染后画布状态恢复，但会引入一次 `save()`/`restore()` 调用的微小开销。
- **SkData::MakeFromStream**: `make(SkStream*)` 将整个流内容读入内存，对于非常大的 Lottie 文件（数十 MB）可能有内存压力。大文件场景下应考虑流内存管理策略。
- **CompositionBuilder 的构建时间**: `parse()` 中的 `CompositionBuilder(*this, fCompSize, jroot).build(*this)` 是场景图构建的主要时间消耗点，涉及递归地解析所有图层和子合成。
- **初始重验证**: `parse()` 末尾执行的 `fRevalidator->revalidate()` 确保场景图在首次使用前完全一致，这是一次性开销。

### 关键数据流

动画构建的完整数据流如下：

```
JSON 数据 -> skjson::DOM 解析 -> skjson::ObjectValue (JSON 根对象)
    |
    +-> 元数据提取 (版本、尺寸、帧率、时间范围)
    |
    +-> AnimationBuilder::parse()
    |       |
    |       +-> parseAssets() -- 构建资产 ID 到 JSON 对象的映射表
    |       +-> parseFonts() -- 解析字体定义和字符表
    |       +-> CompositionBuilder::build() -- 递归构建场景图
    |       +-> 动画器收集 (AnimatorScope)
    |       +-> 初始重验证 (fRevalidator->revalidate())
    |
    +-> Animation 构造 (场景图根、动画器列表、元数据)
```

## 相关文件

- `modules/skottie/include/Skottie.h` -- 公共 API 声明
- `modules/skottie/src/SkottiePriv.h` -- AnimationBuilder 声明
- `modules/skottie/src/Composition.h` -- CompositionBuilder，递归构建合成场景图
- `modules/skottie/src/Adapter.h` -- DiscardableAdapterBase 适配器基类模板
- `modules/skottie/src/SkottieJson.h` -- ParseDefault 等 JSON 工具函数
- `modules/skottie/src/animator/Animator.h` -- 动画器基类和 AnimatablePropertyContainer
- `modules/skottie/src/text/TextAdapter.h` -- 文本图层适配器
- `modules/sksg/include/SkSGRenderNode.h` -- 场景图渲染节点基类
- `modules/sksg/include/SkSGOpacityEffect.h` -- 不透明度效果节点
- `modules/skottie/src/SkottieValue.h` -- ScalarValue 等内部值类型定义
- `modules/skottie/src/BlendModes.cpp` -- 混合模式到 SkBlender 的映射
- `modules/skottie/src/Transform.h` -- 变换适配器实现
