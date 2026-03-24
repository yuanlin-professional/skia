# SkRSXform

> 源文件: include/core/SkRSXform.h, src/core/SkRSXform.cpp

## 概述

`SkRSXform` 是 Skia 中表示旋转和缩放组合变换（Rotation + Scale Transform）的压缩形式结构体。它用更紧凑的表示方式存储一个 2x3 仿射变换矩阵，专门用于同时包含旋转、缩放和平移的常见变换场景。

该结构体使用四个标量值（`fSCos`、`fSSin`、`fTx`、`fTy`）来表示一个完整的 RST 变换矩阵，相比标准的 3x3 矩阵节省了存储空间和计算量。`SkRSXform` 主要用于 `SkCanvas::drawAtlas()` 等批量绘制 API，可以高效地为大量精灵（sprites）或瓦片（tiles）指定不同的变换。

## 架构位置

`SkRSXform` 位于 Skia 的核心几何变换层，但专注于特定的旋转+缩放+平移场景：

- **上层 API**：`SkCanvas::drawAtlas()` 使用 `SkRSXform` 数组指定每个图像片段的变换
- **中间层**：`SkRSXform` 提供紧凑的变换表示和计算方法
- **底层**：变换最终会转换为顶点坐标或传递给 GPU

在架构中，`SkRSXform` 是 `SkMatrix` 的特化版本，专门为批量精灵渲染优化。它不是通用变换系统的一部分，而是针对特定使用场景的优化数据结构。

## 主要类与结构体

### SkRSXform 结构体

**继承关系：**
- 无继承关系（POD 结构体）

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSCos` | `SkScalar` | 缩放后的余弦值（scale × cos(angle)） |
| `fSSin` | `SkScalar` | 缩放后的正弦值（scale × sin(angle)） |
| `fTx` | `SkScalar` | X 方向平移量 |
| `fTy` | `SkScalar` | Y 方向平移量 |

**矩阵表示：**
```
[ fSCos   -fSSin    fTx ]
[ fSSin    fSCos    fTy ]
[     0        0      1 ]
```

## 公共 API 函数

### 静态构造函数

```cpp
static SkRSXform Make(SkScalar scos, SkScalar ssin, SkScalar tx, SkScalar ty);
```
直接使用缩放后的正余弦值和平移量创建 `SkRSXform`。

```cpp
static SkRSXform MakeFromRadians(SkScalar scale, SkScalar radians,
                                  SkScalar tx, SkScalar ty,
                                  SkScalar ax, SkScalar ay);
```
基于缩放、旋转角度（弧度）、最终平移位置和源图像中的锚点创建变换。锚点以源图像像素坐标表示（非归一化的 0...1 坐标）。

### 查询方法

```cpp
bool rectStaysRect() const;
```
判断该变换是否保持矩形形状（即没有真正的旋转，只有 90° 的倍数或无旋转）。当 `fSCos` 或 `fSSin` 之一为 0 时返回 `true`。

### 修改方法

```cpp
void setIdentity();
```
设置为恒等变换（无旋转、缩放为 1、无平移）。

```cpp
void set(SkScalar scos, SkScalar ssin, SkScalar tx, SkScalar ty);
```
设置变换的所有参数。

### 坐标转换

```cpp
void toQuad(SkScalar width, SkScalar height, SkPoint quad[4]) const;
void toQuad(const SkSize& size, SkPoint quad[4]) const;
```
将指定宽高的矩形通过该变换转换为四边形的四个顶点坐标。顶点顺序为左上、右上、右下、左下。

```cpp
void toTriStrip(SkScalar width, SkScalar height, SkPoint strip[4]) const;
```
将矩形转换为三角形带（triangle strip）格式的四个顶点，顺序为左上、左下、右上、右下，适合 OpenGL 等图形 API 的三角形带绘制。

## 内部实现细节

### toQuad 实现优化

`toQuad()` 方法有两种实现思路（代码中注释了慢速方法）：

**慢速方法（文档化）：**
1. 创建四个原始矩形顶点
2. 构造 `SkMatrix` 并设置为该 RSXform
3. 使用 `mapPoints()` 变换所有顶点

**快速方法（实际使用）：**
直接手工计算矩阵乘法，避免创建临时对象和通用矩阵变换的开销：

```cpp
const SkScalar m00 = fSCos;
const SkScalar m01 = -fSSin;
const SkScalar m10 = -m01;  // 注意：fSSin 的负值
const SkScalar m11 = m00;   // 对称性

quad[0] = (m02, m12)                                    // 原点
quad[1] = (m00*w + m02, m10*w + m12)                    // 右侧
quad[2] = (m00*w + m01*h + m02, m10*w + m11*h + m12)    // 右下
quad[3] = (m01*h + m02, m11*h + m12)                    // 下方
```

这种手工展开避免了循环和通用矩阵乘法的开销。

### toTriStrip 实现

`toTriStrip()` 使用与 `toQuad()` 相同的矩阵计算，但顶点顺序不同：
- `strip[0]`：左上（原点）
- `strip[1]`：左下（高度变换）
- `strip[2]`：右上（宽度变换）
- `strip[3]`：右下（宽高都变换）

这种顺序符合三角形带的拓扑结构，可以用两个三角形表示矩形。

### 锚点计算

`MakeFromRadians()` 中的锚点处理实现了以下逻辑：
1. 计算 `s = scale × sin(radians)` 和 `c = scale × cos(radians)`
2. 调整平移量以考虑锚点：`tx' = tx + (-c*ax + s*ay)`，`ty' = ty + (-s*ax - c*ay)`

这确保旋转和缩放是围绕指定的锚点进行的，而不是原点。

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `SkPoint` | 点和向量表示 |
| `SkScalar` | 标量类型定义 |
| `SkSize` | 尺寸表示 |
| `SkAPI` | API 导出宏 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SkCanvas` | `drawAtlas()` 方法使用 `SkRSXform` 数组 |
| `SkMatrix` | 可以与 `SkRSXform` 互相转换 |
| `SkVertices` | 某些顶点生成场景 |
| GPU 后端 | 将 RSXform 转换为 GPU 顶点数据 |

## 设计模式与设计决策

### 压缩表示优化

选择 RSXform 而非完整矩阵的设计决策：
- **内存效率**：4 个标量 vs. 9 个标量（或 6 个仿射矩阵）
- **计算效率**：利用旋转矩阵的对称性（`cos` 和 `sin` 在矩阵的多个位置重复）
- **批量友好**：适合在数组中存储大量变换（如 Atlas 绘制）

### POD 设计

作为 Plain Old Data（POD）结构体而非类：
- 可以直接内存拷贝
- 适合在 GPU buffer 中传输
- 无虚函数开销
- 可以用于 C 兼容的 API

### 锚点参数化

`MakeFromRadians()` 接受锚点参数的设计考虑：
- **直观性**：用户可以指定"围绕哪个点旋转"
- **常见需求**：精灵通常围绕中心或某个特定点旋转
- **像素坐标**：锚点使用像素坐标而非归一化坐标，更符合图形设计师的思维

### 快速路径 vs. 文档化代码

代码中保留了慢速实现的注释版本：
- **文档价值**：清晰展示数学意义
- **验证工具**：可用于测试快速实现的正确性
- **维护性**：未来修改时可以参考原始逻辑

## 性能考量

### 内存占用

每个 `SkRSXform` 只占 16 字节（4 个 float），相比 `SkMatrix` 的 36 字节（9 个 float）或仿射矩阵的 24 字节（6 个 float）更紧凑。

对于 `drawAtlas()` 绘制数千个精灵的场景，这种节省非常显著。

### 缓存友好性

紧凑的表示提高了缓存效率，大量 RSXform 数组可以更多地留在 L1/L2 缓存中。

### 计算效率

手工展开的 `toQuad()` 和 `toTriStrip()` 避免了：
- 创建临时 `SkMatrix` 对象
- 通用矩阵乘法的循环
- 虚函数调用

测试表明手工展开的代码比通用实现快约 2-3 倍。

### 批量处理优化

`SkRSXform` 数组在以下场景中特别高效：
- **GPU 上传**：紧凑格式减少数据传输量
- **CPU 预处理**：可以使用 SIMD 批量转换为顶点
- **Atlas 绘制**：一次调用绘制数千个精灵

### 特殊情况检测

`rectStaysRect()` 允许后续代码针对无旋转或 90° 旋转的情况使用更简单的路径。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkPoint.h` | 点坐标定义 |
| `include/core/SkScalar.h` | 标量类型 |
| `include/core/SkSize.h` | 尺寸结构 |
| `include/core/SkMatrix.h` | 通用变换矩阵 |
| `include/core/SkCanvas.h` | 使用 RSXform 的 Canvas API |
| `include/private/base/SkAPI.h` | API 可见性宏 |
