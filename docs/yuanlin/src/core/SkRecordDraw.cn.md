# SkRecordDraw

> 源文件: src/core/SkRecordDraw.h, src/core/SkRecordDraw.cpp

## 概述

`SkRecordDraw` 提供将 `SkRecord` 中录制的命令回放到 `SkCanvas` 的功能。该模块包含命令回放的核心逻辑、边界框计算和空间索引支持。通过 `SkRecords::Draw` 访问者类和 `SkRecordFillBounds` 函数,实现高效的录制内容渲染和裁剪优化。

## 架构位置

`SkRecordDraw` 位于 Skia 录制系统的回放层:
- 连接 `SkRecord` 存储和 `SkCanvas` 渲染
- 被 `SkRecordedDrawable` 和 `SkBigPicture` 使用
- 支持边界盒层次结构(BBH)加速
- 提供中断回放的回调机制
- 计算命令的保守边界用于构建空间索引

## 主要类与结构体

### SkRecords::Draw

**继承关系:**
```
SkNoncopyable
  └── SkRecords::Draw
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fInitialCTM` | `const SkM44` | 初始变换矩阵(恒定) |
| `fCanvas` | `SkCanvas*` | 目标画布 |
| `fDrawablePicts` | `SkPicture const* const*` | 可绘制对象的图片数组 |
| `fDrawables` | `SkDrawable* const*` | 可绘制对象数组 |
| `fDrawableCount` | `int` | 可绘制对象数量 |

**功能:** 访问者模式类,为每个 `SkRecords::*` 命令实现 `draw(const T&)` 方法。

### FillBounds

**继承关系:**
```
SkNoncopyable
  └── FillBounds
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCullRect` | `const SkRect` | 剔除矩形 |
| `fBounds` | `SkRect*` | 输出的边界数组 |
| `fMeta` | `SkBBoxHierarchy::Metadata*` | 边界元数据数组 |
| `fCTM` | `SkMatrix` | 当前变换矩阵 |
| `fCurrentOp` | `int` | 当前处理的命令索引 |
| `fSaveStack` | `SkTDArray<SaveBounds>` | Save/Restore 栈 |
| `fControlIndices` | `SkTDArray<int>` | 控制命令索引栈 |

**功能:** 计算每个命令的保守身份空间边界。

### SaveBounds (内部结构体)

**成员:**
- `int controlOps`: 此 Save 块中的控制命令数量
- `Bounds bounds`: 块内所有内容的边界
- `const SkPaint* paint`: SaveLayer 的 paint(未拥有)
- `SkMatrix ctm`: Save 时的 CTM

## 公共 API 函数

### SkRecordDraw

```cpp
void SkRecordDraw(const SkRecord& record,
                  SkCanvas* canvas,
                  SkPicture const* const drawablePicts[],
                  SkDrawable* const drawables[],
                  int drawableCount,
                  const SkBBoxHierarchy* bbh,
                  SkPicture::AbortCallback* callback)
```

**功能:** 将 `SkRecord` 回放到 `SkCanvas`。

**参数:**
- `record`: 要回放的命令序列
- `canvas`: 目标画布
- `drawablePicts/drawables`: 嵌套可绘制对象(二选一)
- `drawableCount`: 可绘制对象数量
- `bbh`: 可选的空间索引,用于裁剪优化
- `callback`: 可选的中断回调

**工作流程:**
1. 保存画布状态(`SkAutoCanvasRestore`)
2. 如果有 BBH:
   - 查询当前裁剪区域重叠的命令
   - 只回放这些命令
3. 否则回放所有命令
4. 每次回放前检查 `callback->abort()`

### SkRecordFillBounds

```cpp
void SkRecordFillBounds(const SkRect& cullRect,
                        const SkRecord& record,
                        SkRect bounds[],
                        SkBBoxHierarchy::Metadata meta[])
```

**功能:** 计算每个命令的保守身份空间边界。

**参数:**
- `cullRect`: 剔除矩形,超出部分的命令边界将被限制
- `record`: 要分析的命令序列
- `bounds`: 输出的边界数组(需预分配 `record.count()` 个元素)
- `meta`: 输出的元数据数组(是否为绘制命令等)

## 内部实现细节

### Draw 类的命令分发

使用宏 `DRAW` 简化实现:

```cpp
#define DRAW(T, call) template <> void Draw::draw(const T& r) { fCanvas->call; }
DRAW(Restore, restore())
DRAW(Save, save())
DRAW(DrawRect, drawRect(r.rect, r.paint))
// ...
#undef DRAW
```

**特殊处理:**
- `NoOp`: 空实现
- `SaveLayer`: 使用 `SkCanvasPriv::ScaledBackdropLayer` 处理 backdrop
- `DrawDrawable`: 根据 `fDrawables` 或 `fDrawablePicts` 选择绘制方式
- `SetMatrix`: 合成 `fInitialCTM * r.matrix`

### FillBounds 的边界计算策略

#### 1. 控制命令的边界

控制命令(Save、Clip、Transform 等)本身没有固定边界,其边界定义为:
> "如果不执行此命令,这个矩形内的像素可能绘制错误"

因此,控制命令的边界 = 其影响的绘制命令的边界并集。

#### 2. Save/Restore 栈管理

```cpp
void trackBounds(const Save&) {
    this->pushSaveBlock(nullptr, false);
}

void trackBounds(const SaveLayer& op) {
    this->pushSaveBlock(op.paint, op.backdrop != nullptr);
}

void trackBounds(const Restore&) {
    fBounds[fCurrentOp] = this->popSaveBlock();
}
```

- 遇到 Save/SaveLayer 时压栈,创建新的边界累积器
- 遇到 Restore 时出栈,将累积的边界赋给所有栈内的控制命令
- SaveLayer 需要特殊处理,因为其 paint 可能影响透明区域

#### 3. 绘制命令的边界

```cpp
template <typename T>
void trackBounds(const T& op) {
    fBounds[fCurrentOp] = this->bounds(op);
    fMeta[fCurrentOp].isDraw = true;
    this->updateSaveBounds(fBounds[fCurrentOp]);
}
```

每个绘制命令实现专门的 `bounds()` 方法:

- `DrawRect`: `adjustAndMap(r.rect, &r.paint)`
- `DrawPath`: 处理逆填充路径(返回 cullRect)
- `DrawImage`: 根据图像尺寸和位置计算
- `DrawTextBlob`: 使用 blob 的边界 + 偏移
- `DrawPaint`: 返回 `fCullRect`(填充整个画布)

#### 4. adjustAndMap 方法

```cpp
Bounds adjustAndMap(SkRect rect, const SkPaint* paint) const {
    rect.sort();  // 修正倒置矩形
    if (!AdjustForPaint(paint, &rect)) {
        return fCullRect;  // paint 可能影响任意区域
    }
    if (!this->adjustForSaveLayerPaints(&rect)) {
        return fCullRect;  // SaveLayer paint 可能影响任意区域
    }
    fCTM.mapRect(&rect);  // 变换到身份空间
    if (!rect.intersect(fCullRect)) {
        return Bounds::MakeEmpty();  // 完全在剔除区域外
    }
    return rect;
}
```

**关键步骤:**
1. 排序矩形确保 left < right, top < bottom
2. 调整以适应绘制 paint(笔画宽度、图像滤镜等)
3. 逆向调整以适应所有外层 SaveLayer 的 paint
4. 变换到身份空间
5. 与剔除矩形求交集

#### 5. SaveLayer 影响透明黑的判断

```cpp
static bool PaintMayAffectTransparentBlack(const SkPaint* paint)
```

检查 paint 是否会影响透明黑色区域:
- ImageFilter 或 ColorFilter 影响透明色
- 特殊混合模式(Clear、Src、DstIn 等)
- Backdrop filter 存在

如果是,SaveLayer 的边界至少是 `fCullRect`。

### CTM 追踪

```cpp
void updateCTM(const Restore& op)   { fCTM = op.matrix; }
void updateCTM(const SetMatrix& op) { fCTM = op.matrix; }
void updateCTM(const Concat& op)    { fCTM.preConcat(op.matrix); }
void updateCTM(const Translate& op) { fCTM.preTranslate(op.dx, op.dy); }
```

`FillBounds` 维护精确的 CTM,用于将局部边界变换到身份空间。

### 控制命令处理

```cpp
void pushControl() {
    fControlIndices.push_back(fCurrentOp);
    if (!fSaveStack.empty()) {
        fSaveStack.back().controlOps++;
    }
}

void popControl(const Bounds& bounds) {
    fBounds[fControlIndices.back()] = bounds;
    fMeta[fControlIndices.back()].isDraw = false;
    fControlIndices.pop_back();
}
```

- 控制命令索引压栈,等待边界计算
- Save 块结束时,统一为所有控制命令填充边界

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkRecord` | 命令序列 |
| `SkCanvas` | 渲染目标 |
| `SkBBoxHierarchy` | 空间索引 |
| `SkRecords` | 命令类型 |
| `SkPaint` | 绘制属性分析 |
| `SkImageFilter` | 检查是否影响透明黑 |
| `SkDrawable` | 嵌套可绘制对象 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkRecordedDrawable` | 调用回放 |
| `SkBigPicture` | 调用回放和边界计算 |
| `SkPicturePlayback` | 使用边界构建 BBH |

## 设计模式与设计决策

### 1. 访问者模式(Visitor Pattern)
`Draw` 类为每个命令类型提供专门的 `draw` 方法。

### 2. 双重分发(Double Dispatch)
通过 `record.visit(i, draw)` 实现类型安全的命令分发。

### 3. 栈式状态管理
使用栈追踪 Save/Restore 块,确保正确的边界计算。

### 4. 保守估计(Conservative Estimation)
边界计算宁可过大不可过小,确保不丢失绘制内容。

### 5. 延迟计算(Lazy Evaluation)
控制命令的边界延迟到 Restore 时计算,基于实际绘制内容。

### 6. 空间索引优化(Spatial Index)
使用 BBH 跳过不在裁剪区域的命令,提升大场景性能。

### 7. 回调机制(Callback Pattern)
提供 `AbortCallback` 允许外部中断回放。

## 性能考量

### 1. BBH 加速
使用空间索引可以跳过大量不可见命令,对大场景提升显著。

### 2. 早期中断
`AbortCallback` 允许在渲染目标失效时立即停止。

### 3. 保守边界
过大的边界可能导致不必要的命令执行,但计算成本远低于精确边界。

### 4. 预缓存 CTM
`Restore` 记录恢复后的矩阵,避免回放时重建状态。

### 5. 单次遍历
边界计算只需一次遍历 `SkRecord`,时间复杂度 O(n)。

### 6. 栈内存
Save 栈通常很浅,适合栈分配。

### 7. 快速路径检查
`isEmpty()` 和 `intersect()` 提供快速拒绝测试。

### 8. SKVX 优化
`Bounds` 计算在某些平台使用 SIMD 优化(虽然 Rect 本身没有,但可能在未来扩展)。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/core/SkRecord.h` | 命令序列存储 |
| `src/core/SkRecords.h` | 命令类型定义 |
| `include/core/SkCanvas.h` | 渲染目标 |
| `include/core/SkBBHFactory.h` | 空间索引接口 |
| `include/core/SkPicture.h` | AbortCallback 定义 |
| `src/core/SkCanvasPriv.h` | Canvas 私有 API |
| `src/core/SkImageFilter_Base.h` | 滤镜透明黑检查 |
| `src/effects/colorfilters/SkColorFilterBase.h` | 颜色滤镜透明黑检查 |
| `include/core/SkDrawable.h` | 嵌套可绘制对象 |
| `src/utils/SkPatchUtils.h` | Patch 顶点数量常量 |
