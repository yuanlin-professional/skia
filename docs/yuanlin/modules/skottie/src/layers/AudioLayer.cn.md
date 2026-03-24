# AudioLayer - Skottie 音频图层

> 源文件: `modules/skottie/src/layers/AudioLayer.cpp`

## 概述

AudioLayer 实现了 Lottie 动画中音频图层的加载与播放控制。该文件负责解析音频资源引用，通过外部资源提供者加载音频轨道，并创建一个转发式的播放控制器（ForwardingPlaybackController）来驱动音频的播放时序。音频图层不会产生任何渲染节点，其播放完全由动画器（Animator）树控制。

## 架构位置

AudioLayer 位于 Skottie 模块的图层解析子系统中，是 `AnimationBuilder` 中五种图层类型之一。它处于动画构建管线的图层附加阶段，连接了外部资源加载系统（`SkResources`）与 Skottie 内部的动画控制系统（`Animator`）。

```
Skottie AnimationBuilder
  -> attachAudioLayer()
    -> ScopedAssetRef (资源引用解析)
    -> fResourceProvider->loadAudioAsset() (外部资源加载)
    -> ForwardingPlaybackController (播放控制 Animator)
```

## 主要类与结构体

### ForwardingPlaybackController
- 继承自 `Animator`，作为音频播放的时间控制器
- 持有 `sk_sp<skresources::ExternalTrackAsset>` 音频轨道资源
- 记录音频的入点（`fInPoint`）、出点（`fOutPoint`）和帧率（`fFps`）
- 在 `onSeek(float t)` 中将动画帧时间转换为音频相对秒数，调用 `fTrack->seek(t)` 控制播放
- 当时间超出入点到出点范围时传递 -1 表示静音
- 始终返回 `false`（不影响渲染树）

## 公共 API 函数

### `AnimationBuilder::attachAudioLayer`
```cpp
sk_sp<sksg::RenderNode> attachAudioLayer(const skjson::ObjectValue& jlayer,
                                          LayerInfo* layer_info) const;
```
- 从 JSON 图层对象解析音频资源引用（通过 `ScopedAssetRef`）
- 从音频资源 JSON 中提取路径 `"p"`、目录 `"u"` 和标识符 `"id"`
- 调用 `fResourceProvider->loadAudioAsset()` 加载外部音频
- 成功时创建 `ForwardingPlaybackController` 并加入当前动画器作用域
- 始终返回 `nullptr`（音频图层无渲染节点）

## 内部实现细节

1. **时间映射逻辑**：`onSeek` 方法将全局动画帧号 `t` 转换为音频局部时间秒数。公式为 `(t - fInPoint) / fFps`，其中 `fInPoint` 是音频入点帧号，`fFps` 是动画帧率。
2. **静音处理**：当 `t < fInPoint` 或 `t > fOutPoint` 时，传递 `-1` 给音频轨道的 seek 方法，表示音频应被静音或停止。
3. **渲染树隔离**：`onSeek` 始终返回 `false`，表明音频播放不会触发渲染树的状态变更或重绘。
4. **资源加载失败处理**：当音频加载失败时，通过 `this->log()` 输出警告级别的日志。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkRefCnt` | 引用计数智能指针基础设施 |
| `SkJSONReader` | JSON 解析 |
| `Skottie.h` | Skottie 公共接口，Logger 等 |
| `SkottiePriv.h` | AnimationBuilder 内部接口 |
| `Animator.h` | Animator 基类 |
| `SkResources.h` | ExternalTrackAsset 外部音频资源接口 |
| `SkSGRenderNode.h` | RenderNode 返回类型 |

## 设计模式与设计决策

- **策略模式/代理模式**：`ForwardingPlaybackController` 将音频播放的时间控制委托给外部的 `ExternalTrackAsset`，Skottie 本身不实现音频解码或播放逻辑，仅负责时间映射和转发。
- **空对象返回**：`attachAudioLayer` 返回 `nullptr` 而非渲染节点，音频图层仅通过 Animator 树参与动画系统，这是音频和视觉渲染的清晰职责分离。
- **外部化音频实现**：通过 `SkResources` 的 `ExternalTrackAsset` 抽象，将平台相关的音频播放实现完全外部化，保持 Skottie 的平台无关性。

## 性能考量

- 音频图层不参与渲染管线，`onSeek` 返回 `false` 避免了不必要的渲染树失效和重绘。
- 每帧仅执行简单的浮点比较和除法运算，开销极小。
- 音频资源通过 `sk_sp` 智能指针管理生命周期，避免资源泄漏。

## 相关文件

- `modules/skottie/src/SkottiePriv.h` - AnimationBuilder 定义及 ScopedAssetRef
- `modules/skottie/src/animator/Animator.h` - Animator 基类定义
- `modules/skresources/include/SkResources.h` - ExternalTrackAsset 接口定义
- `modules/skottie/src/layers/SolidLayer.cpp` - 同级其他图层类型实现
- `modules/skottie/src/layers/FootageLayer.cpp` - 含类似资源加载模式的图层
