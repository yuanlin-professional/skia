# SkPatchUtils — 贝塞尔曲面片工具

> 源文件：[src/utils/SkPatchUtils.h](../../src/utils/SkPatchUtils.h)、[src/utils/SkPatchUtils.cpp](../../src/utils/SkPatchUtils.cpp)

## 概述

`SkPatchUtils` 是用于处理 Coons 贝塞尔曲面片（patch）的工具类。贝塞尔曲面片由 12 个控制点（4 条三次贝塞尔曲线）定义，用于实现 `SkCanvas::drawPatch()` 的网格生成。

核心功能：
- 提取曲面片的四条边界贝塞尔曲线（上、下、左、右）
- 根据曲线曲率自动计算细分级别（LOD）
- 将曲面片转换为 `SkVertices`（三角形网格），支持颜色和纹理坐标插值

## 架构位置

```
SkCanvas::drawPatch()
    │
    └── SkPatchUtils
            ├── GetLevelOfDetail() → 计算细分级别
            └── MakeVertices() → 生成三角形网格
                    └── SkVertices (GPU 可渲染的三角形数据)
```

## 主要类与结构体

### `SkPatchUtils`（静态方法类）

常量：
- `kNumCtrlPts = 12` — 控制点总数
- `kNumCorners = 4` — 角点数
- `kNumPtsCubic = 4` — 每条贝塞尔曲线的控制点数

## 公共 API 函数

### 边界曲线提取

- **`GetTopCubic(cubics[12], points[4])`**：提取顶部三次贝塞尔曲线的 4 个控制点
- **`GetBottomCubic(cubics[12], points[4])`**：提取底部三次贝塞尔曲线
- **`GetLeftCubic(cubics[12], points[4])`**：提取左侧三次贝塞尔曲线
- **`GetRightCubic(cubics[12], points[4])`**：提取右侧三次贝塞尔曲线

### 细分级别计算

**`GetLevelOfDetail(cubics[12], const SkMatrix* matrix) -> SkISize`**

根据曲线曲率和变换矩阵计算 X 和 Y 方向的最佳细分级别。返回的 `SkISize` 表示两个方向上的细分数。

### 网格生成

**`MakeVertices(cubics[12], colors[4], texCoords[4], lodX, lodY, colorSpace) -> sk_sp<SkVertices>`**

将曲面片转换为三角形网格：
- `cubics`：12 个控制点
- `colors`：4 个角点颜色（可选）
- `texCoords`：4 个角点纹理坐标（可选）
- `lodX`/`lodY`：X/Y 方向细分数
- `colorSpace`：颜色空间（用于颜色插值）

返回包含位置、颜色和纹理坐标的 `SkVertices` 对象。

## 内部实现细节

### 控制点布局

12 个控制点按顺时针排列：
```
  P0  P1  P2  P3    (顶部曲线)
  P11             P4  (右侧)
  P10             P5
  P9  P8  P7  P6    (底部曲线，反向)
```
P0、P3、P6、P9 为四个角点。

### 双三次插值

网格生成使用 Coons patch 双三次插值公式。对于参数 (u, v)，位置通过四条边界曲线的双线性组合减去双线性插值的角点位置来计算。

### LOD 计算

根据每条边界曲线的控制点距离和变换后的屏幕空间大小确定细分级别，确保屏幕空间中三角形边长约为几个像素。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `SkVertices` | 三角形网格数据 |
| `SkMatrix` | 变换矩阵（LOD 计算） |
| `SkPoint` | 控制点 |
| `SkColor` | 角点颜色 |
| `SkColorSpace` | 颜色空间（颜色插值） |

## 设计模式与设计决策

1. **纯静态类**：所有方法都是静态的，无实例状态。
2. **自适应细分**：LOD 根据变换矩阵动态调整，确保在不同缩放级别下都有合适的三角形密度。
3. **可选属性**：颜色和纹理坐标都可以为 nullptr，MakeVertices 会相应调整输出。

## 性能考量

- LOD 计算使用简单的距离度量，开销极低。
- 网格顶点数为 `(lodX+1) * (lodY+1)`，三角形数为 `2 * lodX * lodY`。
- 颜色插值使用 `SkColorSpace` 进行线性混合，确保色彩准确。

## 相关文件

- `include/core/SkCanvas.h` — `drawPatch()` API
- `include/core/SkVertices.h` — 三角形网格数据
