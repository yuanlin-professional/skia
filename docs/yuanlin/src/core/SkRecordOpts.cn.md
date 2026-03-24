# SkRecordOpts

> 源文件: src/core/SkRecordOpts.h, src/core/SkRecordOpts.cpp

## 概述

`SkRecordOpts` 提供了一套针对 `SkRecord` 录制命令序列的优化算法。这些优化通过模式匹配识别并消除冗余的绘图命令,如无效的 Save/Restore 对、可合并的 SaveLayer 操作等,从而减少最终回放时的开销。该模块是 Skia 绘图录制系统性能优化的核心组件。

## 架构位置

`SkRecordOpts` 位于 Skia 核心绘图引擎的优化层:
- 处于 `SkRecord` 录制与回放之间
- 由 `SkPictureRecorder` 在完成录制后调用
- 使用 `SkRecordPattern` 提供的模式匹配框架
- 影响最终 `SkPicture` 或 `SkRecordedDrawable` 的性能

## 主要类与结构体

### 优化 Pass 结构体

#### SaveOnlyDrawsRestoreNooper

**功能:** 将只包含绘制命令的 Save-Draw*-Restore 模式转换为无操作(NoOp)。

**模式定义:**
```cpp
Pattern<Is<Save>, Greedy<Or<Is<NoOp>, IsDraw>>, Is<Restore>>
```

**优化逻辑:**
- 匹配 Save 后只有绘制命令(或已是 NoOp)再 Restore 的序列
- 将首尾的 Save 和 Restore 替换为 NoOp
- 减少不必要的状态保存/恢复

#### SaveNoDrawsRestoreNooper

**功能:** 消除完全不包含绘制的 Save-Restore 块。

**模式定义:**
```cpp
Pattern<Is<Save>, Greedy<Not<Or<Is<Save>, Is<SaveLayer>, Is<Restore>, IsDraw>>>, Is<Restore>>
```

**优化逻辑:**
- 匹配 Save 后只有非绘制命令(裁剪、变换等)再 Restore 的序列
- 将整个序列替换为 NoOp
- 排除嵌套 Save/SaveLayer 避免误匹配

#### SaveLayerDrawRestoreNooper (非 Android Framework)

**功能:** 合并 SaveLayer 的透明度到单个绘制命令中。

**模式定义:**
```cpp
Pattern<Is<SaveLayer>, IsSingleDraw, Is<Restore>>
```

**优化条件:**
- SaveLayer 没有 backdrop filter
- SaveLayer 没有 filter 列表
- 绘制命令的 paint 满足可合并条件
- LayerPaint 只包含纯透明度(无颜色、无特效)

**合并逻辑:**
```cpp
paint->setAlpha(SkMulDiv255Round(paint->getAlpha(), SkColorGetA(layerColor)))
```

#### SvgOpacityAndFilterLayerMergePass

**功能:** 优化 SVG 生成的嵌套 SaveLayer 模式。

**模式定义:**
```cpp
Pattern<Is<SaveLayer>, Is<Save>, Is<ClipRect>, Is<SaveLayer>,
        Is<Restore>, Is<Restore>, Is<Restore>>
```

**场景:** SVG 的 CSS 透明度 + 滤镜效果通常生成此嵌套结构。

**优化逻辑:**
- 将外层 SaveLayer 的透明度合并到内层 SaveLayer
- 消除外层 SaveLayer 和其对应的 Restore

## 公共 API 函数

### SkRecordOptimize

```cpp
void SkRecordOptimize(SkRecord* record)
```
运行所有推荐的优化 pass,顺序为:
1. ~~SkRecordNoopSaveRestores~~ (已禁用,与 drawAnnotation 有冲突)
2. `SkRecordNoopSaveLayerDrawRestores` (非 Android)
3. `SkRecordMergeSvgOpacityAndFilterLayers`
4. `record->defrag()` 清理 NoOp 命令

### SkRecordNoopSaveRestores

```cpp
void SkRecordNoopSaveRestores(SkRecord* record)
```
循环应用 `SaveOnlyDrawsRestoreNooper` 和 `SaveNoDrawsRestoreNooper` 直到无法再优化。

### SkRecordNoopSaveLayerDrawRestores

```cpp
void SkRecordNoopSaveLayerDrawRestores(SkRecord* record)
```
应用 `SaveLayerDrawRestoreNooper` 优化。仅在非 Android Framework 构建时可用。

### SkRecordMergeSvgOpacityAndFilterLayers

```cpp
void SkRecordMergeSvgOpacityAndFilterLayers(SkRecord* record)
```
应用 `SvgOpacityAndFilterLayerMergePass` 优化 SVG 特有的层嵌套。

## 内部实现细节

### 模式匹配框架

```cpp
template <typename Pass>
static bool apply(Pass* pass, SkRecord* record)
```
通用的模式应用函数:
1. 使用 `Pass::Match` 类型定义的模式搜索记录
2. 对每个匹配调用 `pass->onMatch(record, &match, begin, end)`
3. 返回是否进行了任何修改

### 透明度合并条件检查

```cpp
static bool fold_opacity_layer_color_to_paint(
    const SkPaint* layerPaint, bool isSaveLayer, SkPaint* paint)
```

**检查条件:**
- 绘制 paint 必须是 SrcOver 混合模式
- 非 SaveLayer 绘制时不能有 ImageFilter
- 不能有 ColorFilter(会影响输入颜色)
- LayerPaint 必须只有 alpha 分量(颜色为透明)
- LayerPaint 不能有任何特效(PathEffect、Shader、MaskFilter 等)

**透明度计算:**
使用 `SkMulDiv255Round` 将两个透明度值相乘并正确舍入到 [0, 255] 范围。

### effectively_srcover 检查

```cpp
static bool effectively_srcover(const SkPaint* paint)
```
检查 paint 是否等效于 SrcOver:
- 无 paint 或显式是 SrcOver
- 或者是不透明的 Src 模式且无改变不透明度的特效

### 为什么禁用 SkRecordNoopSaveRestores

注释指出存在已知 bug:
- 该优化与 `drawAnnotation` 不兼容
- Bug 链接: https://bugs.chromium.org/p/skia/issues/detail?id=5548
- 注释中的原因是 BBH 会更好地处理 Save-NoDraw-Restore 序列

### Android Framework 特殊处理

SaveLayer 优化在 Android Framework 中被禁用的原因:
- 会导致 CTS 测试失败: `android.uirendering.cts.testclasses.LayerTests#testSaveLayerClippedWithAlpha`
- Android 需要精确的 SaveLayer 语义以保证渲染兼容性

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkRecord` | 被优化的命令序列 |
| `SkRecordPattern` | 模式匹配框架 |
| `SkRecords` | 命令类型定义 |
| `SkPaint` | 绘制属性检查和修改 |
| `SkBlendMode` | 混合模式检查 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkPictureRecorder` | 录制结束后调用优化 |
| `SkRecordedDrawable` | 间接受益于优化 |
| `SkBigPicture` | 优化后的记录用于构建图片 |

## 设计模式与设计决策

### 1. 策略模式
每个优化 pass 是一个独立的策略,可以选择性地应用。

### 2. 访问者模式
通过模板化的 `apply` 函数和模式匹配遍历 `SkRecord`,无需修改命令类型。

### 3. 贪婪匹配
使用 `Greedy` 模式匹配器连续匹配多个命令,最大化优化范围。

### 4. 迭代优化
`SkRecordNoopSaveRestores` 循环应用直到收敛,因为一次优化可能暴露新的优化机会。

### 5. 保守优化
透明度合并有严格的前提条件检查,确保不改变渲染结果。

### 6. 平台差异化
使用 `#ifndef SK_BUILD_FOR_ANDROID_FRAMEWORK` 条件编译,为不同平台提供不同优化策略。

## 性能考量

### 1. 减少绘制命令数量
消除冗余 Save/Restore 直接减少回放时的状态管理开销。

### 2. 避免 SaveLayer 开销
SaveLayer 需要创建离屏缓冲区,合并透明度可避免这一昂贵操作。

### 3. 单次遍历优化
大多数优化 pass 只需遍历一次 `SkRecord`,时间复杂度为 O(n)。

### 4. 延迟清理
NoOp 命令在优化过程中原地替换,统一由 `defrag()` 清理,避免频繁的内存重排。

### 5. 条件编译
平台特定的优化通过宏控制,避免运行时检查开销。

### 6. 透明度计算优化
使用 `SkMulDiv255Round` 实现高效的定点乘法,避免浮点运算。

### 7. 模式搜索效率
`Pattern::search` 使用快进机制,失败时快速跳到下一个位置,而非逐命令检查。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/core/SkRecord.h` | 被优化的记录结构 |
| `src/core/SkRecordPattern.h` | 模式匹配框架 |
| `src/core/SkRecords.h` | 命令类型定义 |
| `include/core/SkPaint.h` | 绘制属性 |
| `include/core/SkBlendMode.h` | 混合模式枚举 |
| `include/core/SkCanvas.h` | SaveLayerFlags 等定义 |
| `include/private/base/SkMath.h` | SkMulDiv255Round 数学工具 |
