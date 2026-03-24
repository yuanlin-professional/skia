# SkCodecAnimation

> 源文件: `include/codec/SkCodecAnimation.h`

## 概述

SkCodecAnimation 命名空间定义了动画图像解码过程中用于控制帧处理方式的核心枚举类型。该模块为 GIF、APNG 等多帧格式提供了统一的动画行为描述,包括帧处置方法和混合模式,是 Skia 图像解码框架中动画支持的基础设施。

## 架构位置

该模块位于 Skia 的 Codec 子系统中,处于图像解码架构的核心层。它为 SkCodec 及其派生类(如 SkGifCodec)提供动画相关的类型定义,是连接底层编解码器实现和上层图像渲染逻辑的桥梁。

## 核心枚举类型

### DisposalMethod

定义动画帧的处置方法,决定下一帧如何基于当前帧进行渲染。

**设计依据**: 枚举值直接对应 GIF 89a 规范中的数值,确保与标准的兼容性。

**枚举值说明**:

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| kKeep | 1 | 保留当前帧内容,下一帧直接绘制在其上。GIF 中值为 0(未指定)时也使用此模式 |
| kRestoreBGColor | 2 | 在绘制下一帧前,将当前帧矩形区域清除为背景色(透明) |
| kRestorePrevious | 3 | 忽略当前帧,下一帧绘制在上一帧的基础上。GIF 中值为 4 时也使用此模式 |

**使用场景**:
- **kKeep**: 适用于帧之间内容累积的动画,如 loading 动画或部分更新的场景
- **kRestoreBGColor**: 常见于需要清除前一帧影响的动画,避免残影
- **kRestorePrevious**: 用于临时覆盖层或弹出效果,确保当前帧不影响后续动画流程

### Blend

定义当前帧与前一帧的混合方式。

**枚举值说明**:

| 枚举值 | 对应混合模式 | 说明 |
|--------|--------------|------|
| kSrcOver | SkBlendMode::kSrcOver | 标准的 Alpha 混合,将当前帧与前一帧按透明度混合 |
| kSrc | SkBlendMode::kSrc | 直接替换,当前帧的像素完全覆盖目标像素,忽略 Alpha 通道 |

**技术细节**:
- **kSrcOver**: 使用公式 `result = src + dst * (1 - src.alpha)`,支持半透明效果
- **kSrc**: 使用公式 `result = src`,常用于不透明区域的快速渲染

## 设计模式与设计决策

### 基于标准的设计
该模块严格遵循 GIF 89a 规范,将枚举值与规范数值直接对应。这种设计简化了 GIF 解码器的实现,减少了映射转换的开销,同时保证了跨平台行为的一致性。

### 命名空间隔离
使用 `SkCodecAnimation` 命名空间而非类封装,体现了这些类型作为公共定义的性质。这些枚举被多个解码器实现共享,命名空间方式避免了不必要的继承关系,降低了耦合度。

### 枚举类(enum class)选择
使用强类型枚举(`enum class`)防止隐式转换和命名冲突,提升了类型安全性。这在大型项目中尤为重要,避免了与其他模块枚举值的意外碰撞。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| 无直接依赖 | 该头文件为纯类型定义,不依赖其他 Skia 模块 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkCodec | 使用这些枚举描述动画帧属性 |
| SkGifCodec | 在解析 GIF 图形控制扩展块时使用 DisposalMethod |
| SkWebpCodec | WebP 动画帧处理参考这些类型 |
| SkAnimatedImage | 基于这些枚举实现动画播放逻辑 |

## 典型使用流程

### 解码器设置帧信息
```cpp
// 在 GIF 解码器中设置帧处置方法
SkCodec::FrameInfo frameInfo;
frameInfo.fDisposalMethod = SkCodecAnimation::DisposalMethod::kRestoreBGColor;
frameInfo.fBlend = SkCodecAnimation::Blend::kSrcOver;
```

### 动画渲染器处理帧
```cpp
// 动画播放时根据处置方法处理画布
if (frameInfo.fDisposalMethod == SkCodecAnimation::DisposalMethod::kRestoreBGColor) {
    canvas->clear(SK_ColorTRANSPARENT);
} else if (frameInfo.fDisposalMethod == SkCodecAnimation::DisposalMethod::kKeep) {
    // 保留现有内容,无需操作
}
```

## 性能考量

### 内存效率
枚举类型占用空间极小(通常 4 字节),作为帧元数据的一部分传递时几乎无额外开销。

### 处置方法的性能差异
- **kKeep**: 性能最优,无需额外操作
- **kRestoreBGColor**: 需要执行清除操作,对大尺寸帧有一定开销
- **kRestorePrevious**: 需要维护额外的前一帧缓冲区,内存占用翻倍,但渲染逻辑清晰

### 混合模式影响
- **kSrc**: 直接内存拷贝,速度快
- **kSrcOver**: 需要逐像素计算 Alpha 混合,性能取决于硬件加速支持

## 扩展性设计

### 跨格式兼容性
虽然枚举值源自 GIF 规范,但设计上具有通用性,可适配其他动画格式:
- **APNG**: 使用 APNG_DISPOSE_OP_* 和 APNG_BLEND_OP_* 可直接映射到这些枚举
- **WebP**: WebP 动画的处置和混合模式语义与此一致

### 未来扩展空间
如需支持新的处置方法(如部分区域清除或自定义混合函数),可通过添加新枚举值而无需改变现有代码结构。

## 相关文件

| 文件 | 关系 |
|------|------|
| include/codec/SkCodec.h | 定义 FrameInfo 结构体,使用 DisposalMethod 和 Blend 枚举 |
| src/codec/SkGifCodec.cpp | GIF 解码器实现,解析图形控制扩展块并设置处置方法 |
| src/codec/SkWebpCodec.cpp | WebP 解码器参考此枚举实现动画支持 |
| include/core/SkBlendMode.h | 定义完整的混合模式枚举,Blend 枚举映射到其子集 |
| src/android/SkAnimatedImage.cpp | Android 动画图像播放实现,依据处置方法管理帧缓冲 |

## 注意事项

### GIF 规范兼容性
- 值为 0 或 1 时均按 kKeep 处理
- 值为 4 时按 kRestorePrevious 处理
- 这些规则在解码器实现中需要显式处理

### 线程安全
枚举类型本身无状态,可在多线程环境中安全使用。但基于这些枚举的动画渲染逻辑需要确保帧缓冲区访问的同步。

### API 稳定性
作为公共 API 的一部分,这些枚举定义保持长期稳定,不会轻易改变枚举值或语义,确保向后兼容性。
