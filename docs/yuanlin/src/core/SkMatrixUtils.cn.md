# SkMatrixUtils

> 源文件: src/core/SkMatrixUtils.h

## 概述

`SkMatrixUtils` 提供了矩阵变换相关的实用工具函数,主要包括两个功能:判断变换后的位图是否可以优化为精灵绘制(sprite drawing),以及将矩阵分解为旋转-缩放-旋转序列。这些工具函数用于优化渲染路径和分析变换属性。

该模块是 Skia 绘图优化策略的一部分,通过分析变换矩阵的特性,选择最合适的绘制路径。特别是精灵绘制优化可以避免不必要的采样和插值,显著提升性能。

## 架构位置

`SkMatrixUtils` 位于 Skia 核心工具层,与矩阵和位图绘制系统交互:

```
src/core/
├── SkMatrix.h              # 3x3 变换矩阵
├── SkMatrixUtils.h         # 矩阵工具函数(本模块)
├── SkMatrixPriv.h          # 矩阵私有辅助功能
├── SkDraw.h                # 绘图引擎,使用 SkTreatAsSprite
└── SkBitmapDevice.h        # 位图设备,优化位图绘制

include/core/
├── SkPoint.h               # 2D 点类型
├── SkSize.h                # 尺寸类型
└── SkSamplingOptions.h     # 采样选项
```

该模块主要被 `SkDraw`、`SkCanvas`、`SkDevice` 等绘图子系统使用,用于优化决策。

## 主要函数

| 函数名 | 功能描述 |
|--------|---------|
| `SkTreatAsSprite` | 判断变换后的位图是否可以作为精灵绘制 |
| `SkDecomposeUpper2x2` | 分解矩阵左上角 2x2 为旋转-缩放-旋转组合 |

## 公共 API 函数

### SkTreatAsSprite

```cpp
bool SkTreatAsSprite(const SkMatrix& matrix,
                     const SkISize& size,
                     const SkSamplingOptions& sampling,
                     bool isAntiAlias)
```

**功能**: 判断应用变换后的位图是否可以优化为精灵绘制,即源像素和目标像素是否存在一对一映射关系。

**参数**:
- `matrix`: 要应用的变换矩阵
- `size`: 源位图尺寸(宽度和高度)
- `sampling`: 采样选项,影响对齐要求
- `isAntiAlias`: 是否启用抗锯齿

**返回值**:
- `true`: 可以使用 `drawSprite` 优化路径,直接像素拷贝
- `false`: 必须使用 `drawBitmap`,需要采样和插值

**判断条件** (推测实现):
1. 矩阵必须是平移或平移+90度旋转
2. 平移量必须对齐到整数像素边界
3. 若启用抗锯齿,则不能作为精灵处理
4. 采样模式必须是最近邻(Nearest)或兼容模式

**使用场景**:
- UI 元素精确像素对齐绘制
- 平铺纹理的快速填充
- 位图缓存的快速重绘

**性能影响**: 精灵路径避免了:
- 双线性/三线性采样计算
- 像素格式转换开销
- 边界条件检查

### SkDecomposeUpper2x2

```cpp
bool SkDecomposeUpper2x2(const SkMatrix& matrix,
                         SkPoint* rotation1,
                         SkPoint* scale,
                         SkPoint* rotation2)
```

**功能**: 将矩阵的左上角 2x2 部分分解为 `旋转1 × 缩放 × 旋转2` 的组合,用于分析变换的几何属性。

**参数**:
- `matrix`: 输入的变换矩阵(只使用左上角 2x2 部分,忽略平移)
- `rotation1`: 输出第一个旋转的单位向量 `(cos θ₁, sin θ₁)`
- `scale`: 输出缩放因子 `(scaleX, scaleY)`
- `rotation2`: 输出第二个旋转的单位向量 `(cos θ₂, sin θ₂)`

**返回值**:
- `true`: 成功分解
- `false`: 矩阵退化(行列式为零),无法分解

**数学背景**: 极分解(Polar Decomposition)
```
M = R₁ × S × R₂
其中 R₁, R₂ 为旋转矩阵,S 为对角缩放矩阵
```

**特殊情况**:
- 若存在镜像变换,其中一个缩放因子将为负值
- 退化矩阵(如全零矩阵)返回 `false`

**应用场景**:
- 分析路径变换的各向异性缩放
- 提取倾斜变换的角度
- 字体渲染中的缩放因子提取
- 笔画宽度计算

## 内部实现细节

### SkTreatAsSprite 判断逻辑(推测)

```cpp
bool SkTreatAsSprite(const SkMatrix& m, const SkISize& size,
                     const SkSamplingOptions& sampling, bool aa) {
    // 1. 抗锯齿绘制不能作为精灵
    if (aa) return false;

    // 2. 检查是否为整数平移
    if (m.getType() <= SkMatrix::kTranslate_Mask) {
        return m.getTranslateX() == floor(m.getTranslateX()) &&
               m.getTranslateY() == floor(m.getTranslateY());
    }

    // 3. 检查是否为 90 度旋转 + 整数平移
    // (需要检查是否为 [0, ±1; ±1, 0] 形式)

    // 4. 采样模式必须兼容
    if (sampling.filter != SkFilterMode::kNearest) {
        return false;
    }

    return true;
}
```

### SkDecomposeUpper2x2 算法

使用奇异值分解(SVD)或类似方法:

```
给定矩阵 M = [a b; c d]
1. 计算 M^T × M 的特征值和特征向量
2. 缩放因子为特征值的平方根
3. 旋转矩阵通过正交化得到
```

可能的实现步骤:
1. 提取左上角 2x2 子矩阵
2. 计算行列式检查非退化性
3. 使用极分解公式计算各分量
4. 归一化旋转向量

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkMatrix.h` | 矩阵类型 |
| `include/core/SkPoint.h` | 点和向量类型 |
| `include/core/SkSize.h` | 尺寸类型 |
| `include/core/SkSamplingOptions.h` | 采样模式定义 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `SkDraw` | 调用 `SkTreatAsSprite` 决定绘制路径 |
| `SkBitmapDevice` | 优化位图绘制 |
| `SkCanvas` | 间接通过绘制设备使用 |
| `SkFont` 相关 | 使用 `SkDecomposeUpper2x2` 分析文字缩放 |

## 设计模式与设计决策

### 查询式接口

函数采用只读查询方式,不修改输入:
- 接受 `const SkMatrix&` 引用
- 返回布尔值表示成功/失败
- 通过指针参数输出结果

这种设计符合 Skia 的函数式编程风格。

### 早期优化决策

`SkTreatAsSprite` 在绘制路径选择前调用,属于"提前优化":
- 优点: 避免进入复杂的采样代码路径
- 缺点: 增加额外判断开销

在常见 UI 场景下,精灵绘制命中率高,优化收益显著。

### 几何分解通用性

`SkDecomposeUpper2x2` 仅处理 2x2 部分:
- 忽略透视变换(第三行)
- 忽略平移(第三列)

这适用于大多数 2D 图形场景,其中平移单独处理。

## 性能考量

### SkTreatAsSprite 性能影响

**命中精灵路径** (典型 UI 场景):
- 性能提升: 2-5 倍(避免采样开销)
- 常见于: 图标绘制、平铺背景、像素完美 UI

**未命中精灵路径**:
- 额外开销: 几个比较操作,可忽略
- 通过分支预测优化,现代 CPU 上接近零成本

### SkDecomposeUpper2x2 计算成本

- 复杂度: O(1),约 20-30 次浮点运算
- 包括: 三角函数计算(atan2, sin, cos)
- 适合: 非频繁调用的分析场景

若在热路径使用,应考虑缓存分解结果。

## 使用示例

### 判断是否可精灵绘制

```cpp
SkMatrix matrix = SkMatrix::Translate(10.0f, 20.0f);
SkISize bitmapSize = {100, 100};
SkSamplingOptions sampling(SkFilterMode::kNearest);
bool aa = false;

if (SkTreatAsSprite(matrix, bitmapSize, sampling, aa)) {
    // 使用快速精灵路径
    device->drawSprite(bitmap, 10, 20, paint);
} else {
    // 使用通用位图绘制
    canvas->drawImage(image, 10, 20, sampling, &paint);
}
```

### 分析变换的缩放因子

```cpp
SkMatrix transform = ...;
SkPoint rot1, scale, rot2;

if (SkDecomposeUpper2x2(transform, &rot1, &scale, &rot2)) {
    // 提取各向异性缩放
    float scaleX = scale.fX;
    float scaleY = scale.fY;

    // 检查是否有镜像
    bool hasMirror = (scaleX < 0) || (scaleY < 0);

    // 计算总旋转角度
    float angle1 = atan2(rot1.fY, rot1.fX);
    float angle2 = atan2(rot2.fY, rot2.fX);
}
```

### 优化笔画宽度计算

```cpp
// 根据变换调整笔画宽度
SkPoint rot1, scale, rot2;
if (SkDecomposeUpper2x2(ctm, &rot1, &scale, &rot2)) {
    float avgScale = (abs(scale.fX) + abs(scale.fY)) / 2.0f;
    float adjustedStrokeWidth = strokeWidth * avgScale;
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkDraw.cpp` | 使用者 | 位图绘制路径选择 |
| `src/core/SkBitmapDevice.cpp` | 使用者 | 设备级优化 |
| `include/core/SkMatrix.h` | 依赖 | 变换矩阵类 |
| `src/core/SkMatrixPriv.h` | 同级 | 矩阵私有工具 |
| `include/core/SkSamplingOptions.h` | 依赖 | 采样模式定义 |

## 注意事项

1. **源矩形假设**: `SkTreatAsSprite` 假设源矩形为 `{0, 0, size.width(), size.height()}`
2. **采样模式依赖**: 不同采样模式对精灵判断的影响未在头文件中明确
3. **抗锯齿限制**: 启用抗锯齿时通常不能作为精灵处理
4. **分解唯一性**: `SkDecomposeUpper2x2` 的分解可能不唯一(旋转角度可能有多个等价表示)
5. **退化矩阵**: 零缩放或接近零的情况需要特别处理
6. **浮点精度**: 整数对齐判断可能受浮点误差影响,实现中可能使用小的 epsilon
7. **非仿射变换**: 这些工具假设输入为仿射变换,不处理透视投影

该模块虽然简洁,但在 Skia 的绘制优化策略中扮演重要角色。正确使用这些工具可以帮助开发者理解变换属性并做出合适的渲染决策。
