# SkFrameHolder - 动画帧管理基类

> 源文件: `src/codec/SkFrameHolder.h`

## 概述

`SkFrameHolder.h` 定义了 Skia 动画图像解码框架中的两个基类：`SkFrame`（单帧抽象）和 `SkFrameHolder`（帧序列管理器）。这些类被 GIF、WebP、APNG 等动画图像格式的解码器使用，提供了帧间依赖关系管理、alpha 信息缓存、处置方法（disposal method）跟踪和帧持续时间记录等功能。`SkFrame` 比公共 API 中的 `SkCodec::FrameInfo` 更详细，包含了解码器内部需要的额外状态。

## 架构位置

该文件位于 `src/codec/` 目录下，是动画图像解码框架的核心基础设施。具体的动画格式解码器（如 `SkGifCodec`、`SkWebpCodec`）定义 `SkFrame` 的子类来存储格式特有的帧信息，并使用 `SkFrameHolder` 来管理帧序列。`SkFrame::fillIn` 方法将内部帧信息转换为公共的 `SkCodec::FrameInfo` 格式。

## 主要类与结构体

### `SkFrame`
单个动画帧的基类，不可拷贝（继承 `SkNoncopyable`）但支持移动。

**成员变量**:
- `fId`: 帧的 0 基索引
- `fHasAlpha`: 合成后帧是否有透明度（缓存值）
- `fRequiredFrame`: 此帧依赖的前驱帧索引（`kUninitialized = -2` 表示未计算）
- `fRect`: 此帧更新的矩形区域
- `fDisposalMethod`: 处置方法（Keep, RestoreToBackground, RestoreToPrevious）
- `fDuration`: 帧持续时间（毫秒）
- `fBlend`: 混合模式（SrcOver 或 Src）

**关键方法**:
- `frameId()`: 返回帧索引
- `reportedAlpha()`: 帧自身报告的 alpha 类型（委托给纯虚函数 `onReportedAlpha`）
- `hasAlpha()` / `setHasAlpha()`: 合成后的 alpha 缓存
- `reachedStartOfData()`: 是否已确定帧依赖关系
- `getRequiredFrame()` / `setRequiredFrame()`: 前驱帧管理
- `setXYWH()` / `frameRect()`: 帧矩形区域
- `getDisposalMethod()` / `setDisposalMethod()`: 处置方法
- `setDuration()` / `getDuration()`: 帧持续时间
- `setBlend()` / `getBlend()`: 混合模式
- `fillIn(FrameInfo*, bool fullyReceived)`: 填充公共 FrameInfo 结构

**纯虚函数**:
- `onReportedAlpha()`: 子类必须实现，返回帧自身的 alpha 属性

### `SkFrameHolder`
帧序列管理器基类，不可拷贝。

**成员变量**:
- `fScreenWidth`, `fScreenHeight`: 画布尺寸

**关键方法**:
- `screenWidth()` / `screenHeight()`: 画布尺寸查询
- `setAlphaAndRequiredFrame(SkFrame*)`: 根据帧的 alpha 报告和混合方式计算合成后的 alpha 和帧依赖
- `getFrame(int i)`: 获取指定索引的帧（委托给纯虚函数 `onGetFrame`）

**纯虚函数**:
- `onGetFrame(int i)`: 子类必须实现，返回指定索引的帧

## 公共 API 函数

所有方法见上述类描述。主要的外部接口是 `fillIn` 方法（将内部帧信息转为公共格式）和 `setAlphaAndRequiredFrame` 方法（计算帧间依赖）。

## 内部实现细节

1. **帧依赖计算**: `setAlphaAndRequiredFrame` 是核心算法，根据当前帧的处置方法、混合模式、矩形区域和前驱帧的属性，递归计算此帧是否独立（`requiredFrame = kNone`）或依赖于某个前驱帧。

2. **kUninitialized 哨兵值**: `fRequiredFrame = -2` 表示帧依赖尚未计算，`kNone = -1`（来自 `SkCodec`）表示帧独立。`reachedStartOfData()` 通过检查 `!= kUninitialized` 判断是否已初始化。

3. **显式移动构造**: 由于存在用户定义的析构函数（虚析构），C++ 标准不会生成隐式移动构造函数。为了支持在 `std::vector` 中使用，显式声明 `SkFrame(SkFrame&&) = default`。

4. **Alpha 两阶段**: `reportedAlpha()` 是帧自身的 alpha（如帧数据是否包含透明像素），`hasAlpha()` 是合成到画布后的 alpha（考虑混合和前驱帧的影响）。

5. **protected 访问**: `fScreenWidth` 和 `fScreenHeight` 为 protected 成员，允许子类在解析图像头时直接设置。

## 依赖关系

- `include/codec/SkCodec.h`: `SkCodec::FrameInfo` 结构
- `include/codec/SkCodecAnimation.h`: `DisposalMethod` 和 `Blend` 枚举
- `include/core/SkRect.h`: `SkIRect` 矩形
- `include/private/SkEncodedInfo.h`: `SkEncodedInfo::Alpha` 枚举
- `include/private/base/SkNoncopyable.h`: 不可拷贝基类

## 设计模式与设计决策

1. **模板方法模式**: `reportedAlpha()` 和 `getFrame()` 通过纯虚函数委托给子类实现。

2. **值缓存模式**: `fHasAlpha` 和 `fRequiredFrame` 作为计算结果的缓存，避免每次查询重新计算帧依赖。

3. **两级抽象**: `SkFrame`（单帧）和 `SkFrameHolder`（帧集合）分离，各自独立扩展。

4. **Noncopyable + Movable**: 帧对象不可拷贝但可移动，适合容器存储。

5. **延迟初始化**: `fRequiredFrame` 在帧数据解析到足够程度后才被设置（通过 `setRequiredFrame`）。

## 性能考量

- **O(1) 帧访问**: `getFrame` 通过索引直接访问
- **缓存的依赖关系**: 帧依赖只计算一次，后续查询直接返回缓存值
- **最小内存占用**: 每帧仅存储必要的元数据（约 32 字节），不包含像素数据
- **矩形局部更新**: `fRect` 限制了每帧实际需要更新的区域

## 相关文件

- `include/codec/SkCodec.h`: `FrameInfo` 公共结构
- `include/codec/SkCodecAnimation.h`: 动画相关枚举定义
- GIF/WebP/APNG 解码器（继承 `SkFrame` 和 `SkFrameHolder` 的具体实现）
