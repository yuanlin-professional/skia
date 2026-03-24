# SkDistanceFieldGen

> 源文件: src/core/SkDistanceFieldGen.h, src/core/SkDistanceFieldGen.cpp

## 概述

`SkDistanceFieldGen` 模块负责从字形遮罩图像生成有符号距离场（Signed Distance Field, SDF），这是一种用于高质量文本渲染的技术。距离场将每个像素的值表示为该像素到最近边缘的距离，允许在任意缩放级别下保持清晰的边缘。该模块支持三种输入格式：8 位灰度（A8）、16 位 LCD 亚像素遮罩和 1 位黑白遮罩。

距离场的典型应用场景是 GPU 文本渲染，通过在片段着色器中解码距离值实现平滑的抗锯齿和缩放。Skia 使用 4 像素的距离幅度范围，并在边缘周围添加 4 像素的填充。

## 架构位置

`SkDistanceFieldGen` 位于文本渲染管道的预处理阶段：

```
字形栅格化
    ↓
SkMask（字形遮罩）
    ↓
SkDistanceFieldGen（距离场生成）← 当前模块
    ↓
纹理缓存
    ↓
GPU 着色器（距离场解码）
    ↓
屏幕渲染
```

- 上游：接收来自字形栅格化的遮罩数据
- 下游：生成的距离场存储在纹理缓存中供 GPU 使用
- 相关：与 `SkMask`、`SkGlyph` 协作

## 主要类与结构体

### DFData 结构体

存储距离场计算的中间数据：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fAlpha` | `float` | 源纹素的 Alpha 值（0.0-1.0） |
| `fDistSq` | `float` | 到最近边缘的距离平方 |
| `fDistVector` | `SkPoint` | 到最近边缘的距离向量（x, y） |

### NeighborFlags 枚举

定义 8 连通邻域的标志位：

| 标志 | 值 | 说明 |
|------|------|------|
| `kLeft_NeighborFlag` | 0x01 | 左邻域 |
| `kRight_NeighborFlag` | 0x02 | 右邻域 |
| `kTopLeft_NeighborFlag` | 0x04 | 左上邻域 |
| `kTop_NeighborFlag` | 0x08 | 上邻域 |
| `kTopRight_NeighborFlag` | 0x10 | 右上邻域 |
| `kBottomLeft_NeighborFlag` | 0x20 | 左下邻域 |
| `kBottom_NeighborFlag` | 0x40 | 下邻域 |
| `kBottomRight_NeighborFlag` | 0x80 | 右下邻域 |
| `kAll_NeighborFlags` | 0xff | 所有邻域 |

### 常量定义

| 常量 | 值 | 说明 |
|------|------|------|
| `SK_DistanceFieldMagnitude` | 4 | 距离场的最大幅度（纹素） |
| `SK_DistanceFieldPad` | 4 | 距离场边缘填充（纹素） |
| `SK_DistanceFieldInset` | 2 | 渲染时的内缩（用于双线性插值） |
| `SK_DistanceFieldMultiplier` | "7.96875" | 片段着色器乘数（4 × 255/128） |
| `SK_DistanceFieldThreshold` | "0.50196078431" | 片段着色器阈值（128/255） |

## 公共 API 函数

### 主要生成函数

| 函数 | 说明 |
|------|------|
| `SkGenerateDistanceFieldFromA8Image(...)` | 从 8 位灰度遮罩生成距离场 |
| `SkGenerateDistanceFieldFromLCD16Mask(...)` | 从 16 位 LCD 遮罩生成距离场 |
| `SkGenerateDistanceFieldFromBWImage(...)` | 从 1 位黑白遮罩生成距离场 |

**参数说明：**
- `distanceField`：输出缓冲区（需预分配）
- `image`：输入遮罩数据
- `w, h`：原始图像宽度和高度
- `rowBytes`：图像每行的字节数

### 工具函数

| 函数 | 说明 |
|------|------|
| `SkComputeDistanceFieldSize(int w, int h)` | 计算距离场所需的字节数 |

**计算公式：**
```cpp
(w + 2*SK_DistanceFieldPad) * (h + 2*SK_DistanceFieldPad) * sizeof(unsigned char)
```

## 内部实现细节

### 边缘检测算法

`found_edge` 函数检测像素是否为边缘：

1. **锐利过渡**：相邻像素跨越 128 阈值（`currCheck != neighborCheck`）
2. **非零边界**：两个像素都 < 128 且都非零

边缘定义遵循 Alpha 值的 0.5 阈值（128/255），将图像分为内部和外部区域。

### 数据初始化流程

`init_glyph_data` 函数：

1. **Alpha 转换**：将 [0, 255] 整数值转换为 [0.0, 1.0] 浮点数
2. **边界处理**：根据像素位置计算 `checkMask`，避免越界访问
3. **边缘标记**：调用 `found_edge` 标记边缘像素为 255

### 距离计算方法

`edge_distance` 函数实现 Gustavson (2011) 算法：

**输入：**
- `direction`：边缘法向量（已归一化）
- `alpha`：像素的 Alpha 值

**计算逻辑：**
```cpp
if (dx ≈ 0 或 dy ≈ 0):
    distance = 0.5 - alpha
else:
    对方向向量归一化到第一八分圆
    a1num = 0.5 * dy  // 边缘切割的分数面积

    if alpha * dx < a1num:
        distance = 0.5*(dx+dy) - √(2*dx*dy*alpha)
    else if alpha * dx < (dx - a1num):
        distance = (0.5 - alpha) * dx
    else:
        distance = -0.5*(dx+dy) + √(2*dx*dy*(1-alpha))
```

**返回值：**
- 正值：像素在边缘外部
- 负值：像素在边缘内部

### 梯度计算

`init_distances` 函数使用 Sobel 算子计算梯度：

```cpp
currGrad.fX = (prevData+1)->fAlpha - (prevData-1)->fAlpha
            + √2*(currData+1)->fAlpha - √2*(currData-1)->fAlpha
            + (nextData+1)->fAlpha - (nextData-1)->fAlpha

currGrad.fY = (nextData-1)->fAlpha - (prevData-1)->fAlpha
            + √2*nextData->fAlpha - √2*prevData->fAlpha
            + (nextData+1)->fAlpha - (prevData+1)->fAlpha
```

梯度指向 Alpha 增大的方向（从低到高），然后归一化为单位向量。

### 欧几里得距离变换（EDT）

使用 Danielsson 8SSEDT 算法，四阶段扫描：

**F1（第一阶段前向）：** Y 前向，X 前向
- 检查左上、上、右上、左 4 个邻域

**F2（第二阶段前向）：** Y 前向，X 后向
- 检查右邻域

**B1（第一阶段后向）：** Y 后向，X 前向
- 检查左邻域

**B2（第二阶段后向）：** Y 后向，X 后向
- 检查右、左下、下、右下 4 个邻域

**更新规则示例（F1 左上）：**
```cpp
distVec = check->fDistVector;
distSq = check->fDistSq - 2*(distVec.fX + distVec.fY - 1);
if (distSq < curr->fDistSq) {
    distVec.fX -= 1;
    distVec.fY -= 1;
    curr->fDistSq = distSq;
    curr->fDistVector = distVec;
}
```

### 距离场编码

`pack_distance_field_val` 模板函数：

1. **裁剪**：将距离限制在 [-4, 4×127/128] 范围
2. **偏移**：加上幅度值转换为无符号范围 [0, 2×4]
3. **缩放**：映射到 [0, 255] 并四舍五入

**编码公式：**
```cpp
unsigned char = round(((dist + 4) / 8) * 256)
```

**零值映射：** 距离 0 → 值 128

### 输入图像预处理

三个生成函数都执行相同的预处理：

1. **边界填充**：在原始图像周围添加 1 像素的零值边界
2. **格式转换**：
   - A8：直接复制
   - LCD16：使用 `SkMask::AlphaIter` 提取 Alpha
   - BW：将位值 0/1 转换为字节值 0/255

3. **调用核心函数**：`generate_distance_field_from_image`

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPoint` | 存储距离向量 |
| `SkScalar` | 浮点数运算 |
| `SkMask` | LCD16 遮罩格式迭代器 |
| `SkPointPriv` | 向量长度归一化 |
| `SkAutoMalloc` | 自动内存管理 |
| `SkMalloc` | 内存分配 |
| `SkTPin` | 数值裁剪 |
| `SkTemplates` | 自动数组 |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| `SkGlyph` | 调用距离场生成函数 |
| `SkStrike` | 缓存生成的距离场纹理 |
| 文本渲染管道 | 使用距离场进行 GPU 文本渲染 |

## 设计模式与设计决策

### 模板方法模式

`generate_distance_field_from_image` 作为核心模板函数，三个公共 API 提供不同的预处理策略。

### 分离边缘与距离数据

使用两个独立的缓冲区（`DFData*` 和 `unsigned char*`）：
- `DFData`：存储详细的距离信息（12 字节）
- `edges`：标记边缘像素（1 字节）

避免在非边缘像素上执行梯度计算，提升性能。

### 双缓冲区策略

在 EDT 算法中，每个像素访问其邻域的已计算值，利用扫描顺序保证依赖关系。

### 条件编译隔离

```cpp
#if !defined(SK_DISABLE_SDF_TEXT)
// 整个模块代码
#endif
```

支持禁用 SDF 功能以减少二进制大小。

### 调试支持

```cpp
#define DUMP_EDGE 0
#if DUMP_EDGE
    // 输出边缘数据而非距离场
#endif
```

便于开发时可视化边缘检测结果。

## 性能考量

### 关键优化点

1. **边缘跳过**：非边缘像素在 EDT 阶段直接跳过梯度计算
2. **平方距离**：存储 `fDistSq` 避免平方根计算，仅在最终步骤调用 `SkScalarSqrt`
3. **快速长度近似**：`fast_len` 函数在某些上下文中使用曼哈顿距离近似
4. **栈内存分配**：使用 `SkAutoSMalloc<1024>` 避免小图像的堆分配
5. **单次调用内存分配**：`sk_calloc_throw` 一次性分配 `DFData` 和边缘数组

### 内存布局

**临时数据大小：**
```cpp
dataWidth * dataHeight * (sizeof(DFData) + 1)
= (w+2*pad) * (h+2*pad) * 13 字节
```

对于 32×32 字形：(32+10) × (32+10) × 13 ≈ 23 KB

### 算法复杂度

- **时间复杂度**：O(w × h)，每个像素处理固定次数
- **空间复杂度**：O(w × h)，存储中间数据
- **EDT 扫描**：4 次完整扫描（F1、F2、B1、B2）

### 近似与精度

- **边缘距离**：Gustavson 算法使用解析近似，误差 < 0.01 像素
- **梯度归一化**：`SetLengthFast` 使用快速平方根倒数近似
- **非对称编码**：[128, 255] 只有 127 个值，乘以 127/128 防止溢出

### SIMD 机会

当前实现为标量代码，未来可优化：
- 矢量化 EDT 更新步骤
- SIMD 边缘检测
- 并行化 Y 方向扫描

## 相关文件

| 文件路径 | 关系 |
|----------|------|
| `src/core/SkMask.h/.cpp` | 遮罩数据结构与 LCD16 迭代器 |
| `src/core/SkGlyph.h/.cpp` | 字形数据结构，调用距离场生成 |
| `src/core/SkStrike.h/.cpp` | 字形缓存，存储距离场纹理 |
| `include/core/SkPoint.h` | 2D 向量运算 |
| `src/core/SkPointPriv.h` | 向量归一化工具 |
| `include/private/base/SkMalloc.h` | 内存分配函数 |
| `src/base/SkAutoMalloc.h` | RAII 内存管理 |
| `src/gpu/text/*` | GPU 文本渲染使用距离场 |
| `include/private/base/SkTPin.h` | 数值裁剪函数 |
