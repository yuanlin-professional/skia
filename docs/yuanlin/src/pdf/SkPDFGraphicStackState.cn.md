# SkPDFGraphicStackState - PDF 图形栈状态管理

> 源文件：
> - `src/pdf/SkPDFGraphicStackState.h`
> - `src/pdf/SkPDFGraphicStackState.cpp`

## 概述

`SkPDFGraphicStackState` 是 Skia PDF 后端中管理 PDF 内容流图形状态栈的核心结构体。它跟踪当前的变换矩阵、裁剪栈、颜色、着色器、图形状态和文本缩放等状态，并通过 PDF 的 `q`（保存）和 `Q`（恢复）操作符管理状态栈。该模块的关键职责是：在写入 PDF 内容流时，智能地检测状态变更并仅输出必要的 PDF 操作符，避免冗余的状态设置指令。

**注意**：不要将 `SkPDFGraphicStackState` 与 `SkPDFGraphicState` 混淆。前者管理内容流中的图形状态栈，后者表示 PDF 文件中的图形状态字典对象。

## 架构位置

该模块是 `SkPDFDevice` 的核心组件，直接控制 PDF 内容流的生成。

```
SkPDFDevice
  └── SkPDFGraphicStackState (图形栈状态)
        ├── updateClip → 裁剪状态管理 (q/Q + W/W*)
        ├── updateMatrix → 变换矩阵管理 (q/Q + cm)
        ├── updateDrawingState → 绘图状态管理 (颜色/着色器/GS)
        ├── push/pop → 状态栈操作 (q/Q)
        └── drainStack → 清空栈（文档结束时）
```

## 主要类与结构体

### `SkPDFGraphicStackState`

```cpp
struct SkPDFGraphicStackState {
    struct Entry {
        SkMatrix fMatrix = SkMatrix::I();
        uint32_t fClipStackGenID = SkClipStack::kWideOpenGenID;
        SkColor4f fColor = {NaN, NaN, NaN, NaN};
        SkScalar fTextScaleX = 1;
        int fShaderIndex = -1;
        int fGraphicStateIndex = -1;
    };
    static constexpr int kMaxStackDepth = 2;
    Entry fEntries[kMaxStackDepth + 1];
    int fStackDepth = 0;
    SkDynamicMemoryWStream* fContentStream;
};
```

### `Entry` 子结构体

每个栈帧记录以下状态：
- `fMatrix`：当前变换矩阵（CTM）
- `fClipStackGenID`：裁剪栈的代数 ID，用于快速比较裁剪是否变化
- `fColor`：当前绘图颜色（RGB 分量，Alpha 由 GraphicState 处理）
- `fTextScaleX`：文本水平缩放因子
- `fShaderIndex`：当前模式着色器的资源索引（-1 表示无）
- `fGraphicStateIndex`：当前图形状态的资源索引（-1 表示无）

颜色初始值为 NaN，确保首次设置时一定会写出颜色指令。

## 公共 API 函数

### `updateClip`

```cpp
void updateClip(const SkClipStack* clipStack, const SkIRect& bounds);
```

更新裁剪状态。通过比较裁剪栈的 `GenID` 确定是否需要变更。如果当前裁剪不匹配，会先弹出栈帧直到找到匹配的祖先状态，然后 push 新帧并写入裁剪路径。

### `updateMatrix`

```cpp
void updateMatrix(const SkMatrix& matrix);
```

更新变换矩阵。如果当前矩阵非单位矩阵，先 pop 恢复到单位矩阵状态，再 push 并写入新矩阵（通过 `cm` 操作符）。如果新矩阵为单位矩阵，仅执行 pop。

### `updateDrawingState`

```cpp
void updateDrawingState(const Entry& state);
```

更新绘图状态（颜色、着色器、图形状态、文本缩放）。PDF 将着色器视为颜色，因此颜色和着色器互斥设置。仅在状态实际变化时输出对应的 PDF 操作符。

### `push` / `pop`

```cpp
void push();
void pop();
```

手动管理栈帧。`push` 写入 `q` 并复制当前帧，`pop` 写入 `Q` 并清除顶层帧。

### `drainStack`

```cpp
void drainStack();
```

清空所有栈帧，逐层 pop 直到栈深度为 0。在页面或文档结束时调用。

### `currentEntry`

```cpp
Entry* currentEntry();
```

返回当前栈顶的状态条目指针。

## 内部实现细节

### 裁剪处理

裁剪的写入分为三种情况：

1. **简单矩形裁剪**：`is_rect()` 检测裁剪栈是否可以简化为单个矩形。如果可以，直接输出矩形裁剪（`re W* n`），避免路径运算。

2. **复杂裁剪（含 Replace 操作）**：`is_complex_clip()` 检测是否包含 Replace 操作。如果是，使用 `SkClipStack_AsPath` 将整个裁剪栈转为路径，再与边界框求交。

3. **简单裁剪（仅 Intersect/Difference）**：`apply_clip()` 逐个处理裁剪元素，每个元素独立生成裁剪路径。对于 Difference 操作或超出边界的路径，先与边界矩形做布尔运算。

### 裁剪路径输出

`append_clip_path()` 将路径写入 PDF 内容流，然后根据填充规则添加 `W n`（Winding）或 `W* n`（Even-Odd）裁剪操作符。边界框微量外扩（1 像素）以容忍浮点精度和位图近似误差。

### 矩阵管理策略

矩阵更新采用"回退到单位矩阵再设置新值"的策略，而非增量更新。这简化了矩阵管理逻辑，因为 PDF 的 `cm` 操作符是乘法性质的（前乘到 CTM），回退到已知状态比计算增量变换更可靠。

### 栈深度限制

`kMaxStackDepth = 2` 限制了最大栈深度（加上基础层共 3 层）。这足以处理裁剪和矩阵各需一层的典型场景。

### 颜色与着色器互斥

PDF 中着色器模式（Pattern）被视为一种特殊的颜色空间。当使用着色器时，通过 `cs/CS` 和 `scn/SCN` 操作符设置模式；当使用纯色时，通过 `rg/RG` 操作符设置 DeviceRGB 颜色。两者在同一个 `Entry` 中通过 `fShaderIndex` 和 `fColor` 互斥管理。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkClipStack.h` | 裁剪栈管理和遍历 |
| `SkMatrix.h` | 变换矩阵 |
| `SkColor.h` | 颜色类型 |
| `SkPDFUtils.h` | PDF 操作符输出工具 |
| `SkPathOps.h` | 路径布尔运算（裁剪合并）|
| `SkClipStackUtils.h` | 裁剪栈转路径工具 |
| `SkPath.h` | 路径类型 |
| `SkStream.h` | 动态内存流 |

## 设计模式与设计决策

1. **增量状态更新**：每个 `update*` 方法都会比较新旧状态，仅在变化时输出 PDF 操作符。这显著减少了内容流的体积。

2. **GenID 快速比较**：裁剪状态通过 `SkClipStack::getTopmostGenID()` 进行 O(1) 比较，避免逐元素比较裁剪栈内容。

3. **固定大小栈**：使用固定大小数组（3 个 Entry）而非动态容器，避免堆分配开销。最大深度 2 是基于实际使用模式（裁剪 + 矩阵）的经验值。

4. **矩阵回退策略**：选择 pop-push 模式而非增量矩阵计算，换取实现简洁性和正确性保证。

5. **NaN 初始颜色**：颜色初始化为 NaN 值，保证首次绘图时颜色一定会被设置，避免依赖 PDF 查看器的默认颜色行为。

6. **裁剪分层优化**：对简单矩形裁剪、非复杂裁剪和复杂裁剪分别处理，在常见情况下避免昂贵的路径布尔运算。

## 性能考量

- **状态比较开销极低**：GenID 比较为整数比较，矩阵比较仅在 type 不同时才需深度比较。
- **避免冗余输出**：增量更新模式在连续绘图操作共享相同状态时省去大量 PDF 操作符。
- **矩形裁剪快速路径**：`is_rect()` 对纯矩形裁剪（最常见情况）避免了 PathOps 路径运算。
- **栈内存无堆分配**：固定大小的 Entry 数组位于结构体内部，无额外堆分配。
- **边界框外扩策略**：1 像素外扩避免了浮点精度问题导致的裁剪遗漏，代价极低。

## 相关文件

- `src/pdf/SkPDFDevice.h` / `src/pdf/SkPDFDevice.cpp` — 使用方，拥有 `SkPDFGraphicStackState` 实例
- `src/pdf/SkPDFGraphicState.h` — 图形状态字典对象（不同于本模块）
- `src/pdf/SkPDFUtils.h` — PDF 操作符输出工具函数
- `src/core/SkClipStack.h` — 裁剪栈核心实现
- `src/utils/SkClipStackUtils.h` — 裁剪栈转路径工具
- `include/pathops/SkPathOps.h` — 路径布尔运算
