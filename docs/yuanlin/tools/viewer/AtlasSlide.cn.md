# AtlasSlide

> 源文件: `tools/viewer/AtlasSlide.cpp`

## 概述

AtlasSlide 是一个动画演示幻灯片，使用 `drawAtlas` API 在屏幕上绘制 256 个弹跳、旋转、缩放的字符精灵。每个精灵从预生成的字符图集中取样，支持可选的颜色调制，提供了丰富的 Atlas 绘制压力测试场景。

## 架构位置

属于 `tools/viewer` 模块，通过 `DEF_SLIDE` 宏注册了两个变体（`DrawAtlas` 和 `DrawAtlasSim`），分别使用批处理和逐个绘制方式。

## 主要类与结构体

### DrawAtlasDrawable
- 继承自 `SkDrawable`
- 核心成员:
  - `fAtlas`: 512x512 的字符图集（32x32 单元格）
  - `fRec[256]`: 每个精灵的动画状态记录
  - `fTex[256]`: 纹理坐标矩形
  - `fBounds`: 运动边界
  - `fUseColors`: 颜色调制开关

### Rec 结构体
精灵动画状态：
- `fCenter/fVelocity`: 位置和速度（带边界反弹）
- `fScale/fDScale`: 缩放和缩放变化率（0.5-2.0 范围振荡）
- `fRadian/fDRadian`: 旋转角度和角速度
- `fAlpha/fDAlpha`: 透明度和变化率（0-1 范围振荡）

### DrawAtlasSlide
- 继承自 `Slide`
- 包装 `DrawAtlasDrawable`，转发绘制和动画调用

## 公共 API 函数

- `load(SkScalar, SkScalar)`: 创建 DrawAtlasDrawable
- `draw(SkCanvas*)`: 调用 `drawDrawable`
- `animate(double)`: 返回 true 持续动画
- `onChar(SkUnichar)`: 'C' 键切换颜色调制
- `getDimensions()`: 返回 {640, 480}

## 内部实现细节

### 图集生成
`make_atlas()` 在 512x512 的 Surface 上绘制字符网格，每个 32x32 单元格包含一个随机颜色的字符（字母数字和特殊字符）。

### 精灵动画
每帧调用 `Rec::advance()`：
- 位置按速度更新，碰到边界则反弹
- 缩放在 0.5-2.0 间振荡
- 旋转以随机角速度持续旋转
- Alpha 在 0-1 间线性振荡

### 颜色调制
启用时将精灵 alpha 乘入白色（`SkColorSetARGB(alpha*0xFF, 0xFF, 0xFF, 0xFF)`），使用 `SkBlendMode::kModulate` 混合。

## 依赖关系

- `include/core/SkRSXform.h`: 精灵变换
- `include/core/SkDrawable.h`: 可绘制对象
- `include/utils/SkTextUtils.h`: 文本居中绘制
- `src/base/SkRandom.h`: 随机数生成

## 设计模式与设计决策

- **Drawable 封装**: 将动画逻辑封装在 `SkDrawable` 中，与 Slide 分离
- **策略模式**: `DrawAtlasProc` 函数指针支持批处理和逐个绘制两种策略

## 性能考量

- 256 个精灵的批处理 drawAtlas 调用非常高效
- 模拟版本逐个 drawImageRect，开销约为 256 倍
- 使用线性过滤采样

## 相关文件

- `tools/viewer/ShipSlide.cpp`: 类似的 Atlas 性能测试
- `include/core/SkRSXform.h`: RSXform 变换
