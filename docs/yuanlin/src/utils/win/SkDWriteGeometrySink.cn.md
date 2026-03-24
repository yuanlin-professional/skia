# SkDWriteGeometrySink - DirectWrite 几何体到 SkPath 转换

> 源文件:
> - `src/utils/win/SkDWriteGeometrySink.h`
> - `src/utils/win/SkDWriteGeometrySink.cpp`

## 概述

SkDWriteGeometrySink 是 Skia 在 Windows 平台上将 DirectWrite 字体字形轮廓转换为 SkPath 的桥接类。它实现了 `IDWriteGeometrySink`（即 `ID2D1SimplifiedGeometrySink`）COM 接口，当 DirectWrite 输出字形几何数据时，该类将其直接转换为 SkPathBuilder 操作。

## 架构位置

```
DirectWrite 字形渲染管线
├── IDWriteFontFace::GetGlyphRunOutline()
│   └── IDWriteGeometrySink (回调接口)
│       └── SkDWriteGeometrySink (本模块 - 几何体转换)
│           └── SkPathBuilder (构建 SkPath)
└── SkPath (Skia 路径表示)
```

## 主要类与结构体

### `SkDWriteGeometrySink`
- 实现 `IDWriteGeometrySink` COM 接口（继承自 `ID2D1SimplifiedGeometrySink`）。
- 使用手动引用计数 (`fRefCount`) 管理生命周期。
- **私有成员**:
  - `fRefCount` (LONG): COM 引用计数。
  - `fBuilder` (SkPathBuilder*): 借用的路径构建器指针。
  - `fStarted` (bool): 当前图形是否已开始（即 `moveTo` 是否已调用）。
  - `fCurrent` (D2D1_POINT_2F): 当前点位置。
- **辅助方法**:
  - `goingTo()`: 如果图形尚未开始，先调用 `moveTo` 然后更新当前点。
  - `currentIsNot()`: 判断给定点是否与当前点不同，用于去重。

## 公共 API 函数

### `Create` (静态工厂方法)
```cpp
static HRESULT Create(SkPathBuilder*, IDWriteGeometrySink** geometryToPath);
```
- **功能**: 创建 SkDWriteGeometrySink 实例。
- **用法**: 传入 SkPathBuilder 指针，获取 IDWriteGeometrySink 接口指针。

### COM 接口方法

#### `SetFillMode`
- 将 D2D1 填充模式转换为 SkPath 填充类型。
- `D2D1_FILL_MODE_ALTERNATE` -> `SkPathFillType::kEvenOdd`
- `D2D1_FILL_MODE_WINDING` -> `SkPathFillType::kWinding`

#### `BeginFigure`
- 记录图形起始点但不立即调用 `moveTo`，延迟到第一次实际绘制操作时。

#### `AddLines`
- 将 DirectWrite 的线段序列转换为 `SkPathBuilder::lineTo()` 调用。
- 跳过与当前点重合的点以避免冗余操作。

#### `AddBeziers`
- 将 DirectWrite 的三次贝塞尔曲线转换为 SkPath 操作。
- **优化**: 使用 `check_quadratic()` 检测是否可以降级为二次曲线 (`quadTo`)。如果三次曲线实际是一条二次曲线，则使用更高效的 `quadTo` 代替 `cubicTo`。

#### `EndFigure`
- 如果图形已开始绘制，调用 `SkPathBuilder::close()` 闭合路径。

#### `Close`
- COM 接口的 Close 方法，简单返回 S_OK。

## 内部实现细节

### 三次到二次曲线降级
`check_quadratic()` 函数检测三次贝塞尔曲线是否可以精确表示为二次贝塞尔曲线：
1. 计算三次曲线的控制点差值。
2. 使用 `3/2` 比率计算预期的二次曲线中间控制点。
3. 使用 `approximately_equal()` 函数（基于 `SkFloatingPoint<float, 10>` 的 ULP 比较）判断是否匹配。
4. 如果 x 和 y 坐标都匹配，输出二次曲线的控制点。

### 延迟 moveTo
`BeginFigure` 不直接调用 `moveTo`，而是设置 `fStarted = false` 并记录起点。实际的 `moveTo` 延迟到 `goingTo()` 被首次调用时执行。这避免了在图形没有实际内容时生成空的 move 操作。

### 近似相等比较
`approximately_equal()` 使用基于 ULP (Units in the Last Place) 的浮点比较，允许 10 个 ULP 的误差，适用于几何计算中的近似比较。

## 依赖关系

- `<dwrite.h>`: DirectWrite API。
- `<d2d1.h>`: Direct2D 几何类型定义。
- `include/core/SkPathBuilder.h`: Skia 路径构建器。
- `src/utils/SkFloatUtils.h`: 浮点数近似比较工具 (`SkFloatingPoint`)。
- `src/utils/win/SkObjBase.h`: Windows COM 基础设施宏 (`SK_STDMETHODIMP`)。

## 设计模式与设计决策

1. **适配器模式**: 将 DirectWrite 的 COM 回调接口适配为 Skia 的 SkPathBuilder 操作。
2. **延迟执行**: moveTo 操作被延迟到第一次绘制调用，避免产生无效路径段。
3. **曲线降级优化**: 自动检测可降级的三次曲线，减少路径复杂度。
4. **冗余消除**: 线段和贝塞尔操作都跳过与当前点重合的输入。

## 性能考量

1. **最小化路径操作**: 通过去重和曲线降级减少 SkPath 中的操作数量。
2. **ULP 比较**: 使用高效的整数运算进行浮点近似比较，而非基于误差阈值的比较。
3. **引用计数**: 使用 `InterlockedIncrement`/`InterlockedDecrement` 实现线程安全的引用计数。

## 相关文件

- `src/utils/win/SkDWrite.h/.cpp`: DirectWrite 核心工具函数。
- `src/utils/SkFloatUtils.h`: 浮点近似比较工具。
- `src/utils/win/SkObjBase.h`: COM 接口宏定义。
- `include/core/SkPathBuilder.h`: 路径构建器接口。
