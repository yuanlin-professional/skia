# ExternalLayer.h

> 源文件: `modules/skottie/include/ExternalLayer.h`

## 概述

`ExternalLayer.h` 定义了 Skottie 动画引擎中外部图层（External Layer）的接口。该文件提供两个关键抽象类：`ExternalLayer`（外部渲染图层接口）和 `PrecompInterceptor`（预合成拦截器接口）。这些接口允许嵌入方（embedder）在 Lottie 动画中替换预合成图层的内容，实现自定义渲染逻辑，例如嵌入实时视频流、自定义 UI 组件或其他动态内容。

## 架构位置

该文件位于 `modules/skottie/include/` 目录下，属于 Skottie 模块的公共 API 层。在 Skottie 的架构中，外部图层机制是一个扩展点，位于动画构建管线中：`Animation::Builder` -> `PrecompInterceptor::onLoadPrecomp()` -> `ExternalLayer::render()`。它为 Skottie 的封闭动画系统提供了一个开放的集成接口。

## 主要类与结构体

### `ExternalLayer`
```cpp
class ExternalLayer : public SkRefCnt
```
- **继承**: `SkRefCnt`（引用计数基类）
- **职责**: 定义外部渲染图层的接口，由嵌入方实现以提供自定义图层内容。
- **生命周期**: 通过 `sk_sp` 智能指针管理，由 `PrecompInterceptor::onLoadPrecomp()` 创建。

### `PrecompInterceptor`
```cpp
class PrecompInterceptor : public SkRefCnt
```
- **继承**: `SkRefCnt`（引用计数基类）
- **职责**: 定义预合成图层创建的拦截接口。在动画构建阶段，对每个预合成图层调用此接口，允许嵌入方决定是否用自定义内容替换原始的 Lottie 预合成内容。

## 公共 API 函数

### `ExternalLayer::render(SkCanvas*, double)`
```cpp
virtual void render(SkCanvas* canvas, double t) = 0;
```
- **功能**: 将外部图层内容渲染到指定画布上。
- **参数**:
  - `canvas`: 目标画布
  - `t`: 以秒为单位的时间，相对于图层入点（开始时间）
- **纯虚函数**: 必须由子类实现。

### `PrecompInterceptor::onLoadPrecomp(const char[], const char[], const SkSize&)`
```cpp
virtual sk_sp<ExternalLayer> onLoadPrecomp(const char id[],
                                            const char name[],
                                            const SkSize& size) = 0;
```
- **功能**: 在动画构建时对每个预合成图层调用，允许嵌入方替换其内容。
- **参数**:
  - `id`: 目标合成 ID（通常由 Bodymovin 自动分配，如 `comp_0`）
  - `name`: 预合成图层的名称（默认与目标合成名称匹配，可在 After Effects 中修改）
  - `size`: Lottie 文件中指定的预合成图层尺寸
- **返回值**: `sk_sp<ExternalLayer>` 实例用于替换原始内容，返回 `nullptr` 则使用 Lottie 文件的原始内容。
- **纯虚函数**: 必须由子类实现。

## 内部实现细节

该文件仅包含接口定义，无实现细节。实际的调用发生在 `AnimationBuilder` 的图层解析阶段（参见 `SkottiePriv.h` 中的 `attachExternalPrecompLayer` 和 `attachPrecompLayer`），当 `PrecompInterceptor` 被注册到 `Animation::Builder` 时，构建器会在遇到预合成图层时调用拦截器。

## 依赖关系

- **`include/core/SkRefCnt.h`**: 提供引用计数基类 `SkRefCnt` 和 `sk_sp` 智能指针。
- **`SkCanvas`**: 前向声明，用作 `render()` 的参数类型。
- **`SkSize`**: 前向声明，用于传递预合成图层尺寸。

## 设计模式与设计决策

- **策略模式**: `ExternalLayer` 是一个策略接口，允许在运行时替换图层的渲染实现。
- **抽象工厂模式**: `PrecompInterceptor` 充当 `ExternalLayer` 的工厂，在动画构建阶段为每个预合成图层决定是否创建外部实现。
- **Null Object 约定**: `onLoadPrecomp` 返回 `nullptr` 表示"不替换"，这是一个简洁的 Null Object 设计变体。
- **时间相对化**: `render()` 的时间参数 `t` 相对于图层入点，而非动画全局时间，简化了外部图层的时间管理。

## 性能考量

- `render()` 在每帧渲染时被调用，因此实现应尽可能高效。
- `onLoadPrecomp()` 仅在动画构建时调用一次（非热路径），性能不是主要关注点。
- 引用计数管理（`SkRefCnt`）的开销在大多数场景下可以忽略。

## 相关文件

- `modules/skottie/include/Skottie.h` -- 主 Skottie API，`Animation::Builder` 中注册 `PrecompInterceptor`
- `modules/skottie/src/SkottiePriv.h` -- `AnimationBuilder` 内部实现，调用拦截器
- `modules/skottie/utils/SkottieUtils.h` -- 提供 `ExternalAnimationPrecompInterceptor` 等工具实现
