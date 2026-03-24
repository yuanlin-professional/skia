# FootageLayer - Skottie 素材/图像图层

> 源文件: `modules/skottie/src/layers/FootageLayer.cpp`

## 概述

FootageLayer 实现了 Lottie 动画中图像素材图层的加载、缓存和渲染。它负责从 JSON 中解析图像资源引用（包括 Slot 机制），通过资源提供者加载图像资产，并根据单帧/多帧场景创建不同的渲染策略。该模块处理图像的尺寸适配变换，支持延迟加载和多帧动态图像序列。

## 架构位置

FootageLayer 位于 Skottie 图层管线中，连接了外部资源系统与 Scene Graph 渲染系统。

```
Lottie JSON
  |
  +-> attachFootageLayer()
  |     +-> ScopedAssetRef (资产引用解析)
  |     +-> attachFootageAsset()
  |           +-> loadFootageAsset() [资源加载/缓存]
  |           |     +-> SlotManager (Slot 机制)
  |           |     +-> fResourceProvider->loadImageAsset()
  |           |     +-> fImageAssetCache (缓存)
  |           |
  |           +-> sksg::Image + sksg::TransformEffect [渲染节点]
  |           +-> FootageAnimator [多帧/延迟加载动画器]
```

## 主要类与结构体

### FootageAnimator
- 继承自 `Animator`，驱动多帧图像或延迟加载图像的帧更新
- 持有 `sk_sp<ImageAsset>` 图像资产、`sk_sp<sksg::Image>` 图像节点、`sk_sp<sksg::Matrix<SkMatrix>>` 变换节点
- 关键成员：
  - `fAssetSize` - 声明的资产尺寸
  - `fTimeBias` / `fTimeScale` - 时间偏移和缩放（用于将帧号转换为资产时间）
  - `fIsMultiframe` - 是否为多帧资产
- `onSeek(float t)` 方法获取帧数据并更新图像、采样选项和变换矩阵

### FootageAssetInfo（在 SkottiePriv.h 中定义）
- 存储已加载的图像资产信息
- 成员：`fAsset`（图像资产指针）、`fSize`（声明的图像尺寸）

## 公共 API 函数

### `AnimationBuilder::attachFootageLayer`
```cpp
sk_sp<sksg::RenderNode> attachFootageLayer(const skjson::ObjectValue& jlayer,
                                            LayerInfo* layer_info) const;
```
- 通过 `ScopedAssetRef` 解析图层关联的素材资产
- 委托给 `attachFootageAsset` 处理资产加载和节点创建

### `AnimationBuilder::loadFootageAsset`
```cpp
const FootageAssetInfo* loadFootageAsset(const skjson::ObjectValue& defaultJImage) const;
```
- 支持 Slot 机制：检查 `"sid"` 字段，从 `fSlotsRoot` 查找替代资产
- 从 JSON 提取路径 `"p"`、目录 `"u"`、标识符 `"id"`
- 缓存策略：先查 `fImageAssetCache`，命中则直接返回
- 通过 `fResourceProvider->loadImageAsset()` 加载
- Slot 资产通过 `fSlotManager->trackImageValue()` 注册跟踪
- 缓存解析后的 `FootageAssetInfo`（含资产和尺寸）

### `AnimationBuilder::attachFootageAsset`
```cpp
sk_sp<sksg::RenderNode> attachFootageAsset(const skjson::ObjectValue& jimage,
                                            LayerInfo* layer_info) const;
```
- 创建 `sksg::Image` 渲染节点
- 根据条件选择渲染策略（见下文）
- 设置 `layer_info->fSize` 为资产声明的尺寸
- 需要变换时返回 `sksg::TransformEffect` 包装

## 内部实现细节

### 图像矩阵计算
```cpp
SkMatrix image_matrix(const ImageAsset::FrameData& frame_data, const SkISize& dest_size);
```
- 当 `SizeFit::kNone` 时使用单位矩阵
- 否则通过 `SkMatrix::RectToRectOrIdentity` 将图像内在尺寸映射到声明的资产尺寸
- 最终矩阵 = `frame_data.matrix * size_fit_matrix`

### 渲染策略分支
1. **动画模式**（`kDeferImageLoading` 或 `isMultiFrame()`）：
   - 创建 `FootageAnimator` 挂入动画器作用域
   - 时间参数：`time_bias = -layer_info->fInPoint`，`time_scale = 1/fFrameRate`
   - 始终准备缩放变换（因帧间尺寸可能变化）
2. **静态模式**：
   - 立即解析第一帧（`getFrameData(0)`）
   - 如果矩阵非单位则创建变换节点，否则直接返回图像节点

### FootageAnimator::onSeek
- 单帧资产已有图像时直接返回 `false`（无状态变化）
- 多帧资产：获取当前时间的帧数据，比较图像、采样选项和变换矩阵
- 仅在数据实际变化时更新节点并返回 `true`

### Slot 机制
- Slot ID（`"sid"`）允许外部替换图像资产
- 查找失败时回退到默认资产并输出警告
- 成功加载的 Slot 资产通过 `SlotManager` 跟踪以支持动态更新

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkImage.h` | 图像数据 |
| `SkMatrix.h` | 图像变换矩阵 |
| `SkSamplingOptions.h` | 图像采样选项 |
| `SlotManager.h` | Slot 资产替换机制 |
| `SkResources.h` | ImageAsset 资源接口 |
| `Animator.h` | Animator 基类 |
| `SkSGImage.h` | Image 渲染节点 |
| `SkSGTransform.h` | TransformEffect 变换节点 |
| `SkTHash.h` | 图像资产缓存哈希表 |
| `SkJSONReader.h` / `SkottieJson.h` | JSON 解析 |

## 设计模式与设计决策

- **缓存模式**：`fImageAssetCache` 确保同一资源 ID 的图像只加载一次，多个图层可共享同一资产。
- **策略模式**：静态/动态渲染路径根据资产特性自动选择，静态路径避免了不必要的动画器开销。
- **懒加载**：`kDeferImageLoading` 标志支持延迟图像解析，适用于首屏优化场景。
- **Slot 替换机制**：通过 SlotManager 实现运行时图像资产替换，是 Lottie 交互式功能的基础。
- **增量更新**：`FootageAnimator::onSeek` 仅在帧数据实际变化时更新渲染节点，避免不必要的 Scene Graph 失效。

## 性能考量

- 图像资产缓存避免重复加载相同资源。
- 单帧资产在首次 seek 后短路返回，无后续开销。
- `onSeek` 中的三向比较（图像、采样、矩阵）确保最小化 Scene Graph 更新。
- 时间偏移/缩放预计算（`fTimeBias`、`fTimeScale`）减少每帧运算。
- `TransformEffect` 仅在需要尺寸适配时创建，静态单帧且无缩放的图像直接返回 Image 节点。

### 图像尺寸适配（SizeFit）模式

FootageLayer 支持多种图像尺寸适配模式，通过 `ImageAsset::FrameData::scaling` 控制：

- `SizeFit::kNone` - 不进行尺寸适配，使用原始图像尺寸
- 其他模式通过 `SkMatrix::RectToRectOrIdentity` 将图像映射到声明的资产尺寸，支持 `ScaleToFit` 的 Fill、Contain 等语义

这种设计使得同一个图像资产可以在不同大小的图层中使用，由 `FrameData::matrix` 和尺寸适配矩阵共同控制最终的渲染变换。

### 时间映射机制

FootageAnimator 的时间映射公式为：`asset_time = (frame + timeBias) * timeScale`，其中：
- `timeBias = -layer_info->fInPoint`（将图层入点对齐到资产时间 0）
- `timeScale = 1/fFrameRate`（帧号转换为秒）

这确保了图层的入点帧对应资产的第 0 秒，与 AE 的时间映射行为一致。

## 相关文件

- `modules/skottie/src/SkottiePriv.h` - AnimationBuilder、FootageAssetInfo、ScopedAssetRef
- `modules/skottie/include/SlotManager.h` - Slot 管理器
- `modules/skresources/include/SkResources.h` - ImageAsset 接口
- `modules/sksg/include/SkSGImage.h` - Image 渲染节点
- `modules/sksg/include/SkSGTransform.h` - TransformEffect 节点
- `modules/skottie/src/layers/AudioLayer.cpp` - 类似的资产加载模式
