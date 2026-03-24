# CommonDepthStencilSettings - 通用深度模板设置

> 源文件: `src/gpu/graphite/render/CommonDepthStencilSettings.h`

## 概述

`CommonDepthStencilSettings.h` 定义了 Skia Graphite 渲染后端中可复用的深度和模板测试（Depth-Stencil）配置常量。这些预定义配置覆盖了 Graphite 中所有 RenderStep 需要的深度模板状态，包括直接绘制通道（Direct Pass）和 Redbook 风格的模板-覆盖多通道算法（Stencil-then-Cover）。该文件是 Graphite 渲染架构中基于画家算法（Painter's Algorithm）排序的核心组成部分。

## 架构位置

```
Graphite 渲染管线
  ├── RenderStep (渲染步骤基类)
  │     ├── 直接绘制步骤 (使用 kDirectDepth* 设置)
  │     └── 多通道绘制步骤
  │           ├── 模板通道 (使用 kWindingStencilPass / kEvenOddStencilPass)
  │           └── 覆盖通道 (使用 kRegularCoverPass / kInverseCoverPass)
  └── CommonDepthStencilSettings.h (本文件 - 预定义配置)
```

## 主要类与结构体

本文件不定义新的类或结构体，而是定义了 `DepthStencilSettings` 和 `DepthStencilSettings::Face` 的 `constexpr` 常量实例。

## 公共 API 函数

### 直接绘制通道设置

| 常量 | 深度比较 | 说明 |
|------|----------|------|
| `kDirectDepthLessPass` | `CompareOp::kLess` | 直接绘制，不允许自相交 |
| `kDirectDepthLEqualPass` | `CompareOp::kLEqual` | 直接绘制，允许自相交 |

两者均启用深度测试和深度写入，禁用模板测试。

### 模板面（Face）配置

| 常量 | 操作 | 说明 |
|------|------|------|
| `kIncrementCW` | 通过时递增模板值 | 顺时针三角形，用于 Winding 填充 |
| `kDecrementCCW` | 通过时递减模板值 | 逆时针三角形，用于 Winding 填充 |
| `kToggle` | 通过时翻转最低位 | 用于 Even-Odd 填充 |
| `kPassNonZero` | 非零时通过，清零 | 覆盖通道 - 常规填充 |
| `kPassZero` | 零时通过，失败清零 | 覆盖通道 - 反向填充 |

### 模板通道设置

| 常量 | 前面 | 背面 | 说明 |
|------|------|------|------|
| `kWindingStencilPass` | `kIncrementCW` | `kDecrementCCW` | Winding 规则模板通道 |
| `kEvenOddStencilPass` | `kToggle` | `kToggle` | Even-Odd 规则模板通道 |

### 覆盖通道设置

| 常量 | 面配置 | 说明 |
|------|--------|------|
| `kRegularCoverPass` | `kPassNonZero` | 常规填充的覆盖通道 |
| `kInverseCoverPass` | `kPassZero` | 反向填充的覆盖通道 |

## 内部实现细节

### Redbook 算法实现

该文件实现了经典的 Redbook（OpenGL 红皮书）模板-覆盖算法的两种变体：

#### Winding 填充规则
1. **模板通道** (`kWindingStencilPass`):
   - 顺时针三角形递增模板值
   - 逆时针三角形递减模板值
   - 结果：路径内部模板值非零，外部为零
2. **覆盖通道** (`kRegularCoverPass`):
   - 仅在模板值非零处通过（路径内部）
   - 同时清零模板值

#### Even-Odd 填充规则
1. **模板通道** (`kEvenOddStencilPass`):
   - 所有三角形翻转模板最低位
   - 结果：奇数次覆盖区域最低位为 1
2. **覆盖通道** (`kRegularCoverPass`):
   - 仅在模板值非零处通过

### 反向填充

`kInverseCoverPass` 通过翻转模板测试条件（`kEqual` 替代 `kNotEqual`）实现反向填充——填充路径外部而非内部。

### 深度测试策略

- **模板通道**: 使用 `kLess` 深度测试但**不写入深度**，因为深度写入由后续覆盖通道处理
- **覆盖通道**: 使用 `kLess` 深度测试并**写入深度**，确保正确的画家算法排序
- **直接通道**: 深度测试和写入都启用，`kLess` vs `kLEqual` 取决于是否允许同深度的自相交

### kPassNonZero 的 depthFail 处理

```cpp
constexpr DepthStencilSettings::Face kPassNonZero = {
    /*stencilFail=*/   StencilOp::kKeep,
    /*depthFail=*/     StencilOp::kZero,  // 深度失败也清零
    /*dsPass=*/        StencilOp::kZero,
    ...
};
```

注释解释了为什么 `depthFail` 也设为 `kZero`：如果 `kNotEqual=0` 模板测试通过但深度测试失败，模板值仍需被清零（因为模板值非零说明该位置在路径内，但深度更远）。实际上这种情况不太可能发生（模板通道已经做过相同的深度测试），但明确设置更安全。

### 模板掩码配置

- **Winding**: `readMask = 0xffffffff`, `writeMask = 0xffffffff` — 使用全部模板位
- **Even-Odd kToggle**: `readMask = 0xffffffff`, `writeMask = 0x00000001` — 只写最低位

## 依赖关系

- **src/gpu/graphite/DrawTypes.h**: `DepthStencilSettings`, `CompareOp`, `StencilOp` 类型定义

## 设计模式与设计决策

### 编译时常量模式

所有设置均为 `constexpr`/`static constexpr`，在编译时完全确定。这些常量直接嵌入到 RenderStep 的管线状态中，无运行时构造开销。

### 可组合的配置

通过将 Face 配置和完整的 DepthStencilSettings 分开定义，实现了高度的可组合性：
- `kWindingStencilPass` 组合了 `kIncrementCW` (前面) + `kDecrementCCW` (背面)
- `kRegularCoverPass` 组合了 `kPassNonZero` (两面)
- 未来添加新的填充算法时可以混合搭配这些原子配置

### 基于深度的排序

Graphite 使用深度缓冲区实现画家算法的逆序排序（近物体深度值小）。通过 `kLess` 深度测试，后绘制的物体只有在更近时才能通过测试，从而正确处理遮挡关系。这避免了传统画家算法中的覆盖重绘问题。

## 性能考量

- 所有常量为 `constexpr`，零运行时初始化成本
- 模板-覆盖算法需要两个通道，但支持任意复杂的路径填充
- 直接绘制通道（单通道）用于简单几何体，性能更优
- 深度写入分离策略避免了模板通道中不必要的深度缓冲区带宽消耗
- Even-Odd 的单位写掩码最小化了模板缓冲区的写入位宽

### 通道选择对性能的影响

不同的深度模板配置在 GPU 上有显著的性能差异：

1. **直接通道**（`kDirectDepthLessPass` / `kDirectDepthLEqualPass`）:
   - 单通道完成绘制，最佳性能
   - 适用于凸多边形、矩形、圆角矩形等简单几何体
   - 不使用模板缓冲区，节省带宽

2. **模板-覆盖通道**:
   - 需要两个通道，增加了 draw call 开销
   - 模板通道不写入颜色缓冲区（通过深度测试控制），减少了颜色缓冲区带宽
   - 覆盖通道统一写入颜色，有利于 GPU 像素着色器效率

3. **深度测试的 Early-Z 优化**:
   - `kLess` 深度比较允许 GPU 硬件进行 Early-Z 剔除
   - 这意味着被遮挡的片元在像素着色器之前就被剔除，大幅减少着色开销
   - Graphite 的深度排序策略专门为此优化设计

### 模板缓冲区精度

Winding 填充使用全部 32 位模板值，理论上支持任意复杂度的自交叉路径。Even-Odd 仅使用 1 位，模板缓冲区的利用率最低，但对于大多数矢量图形场景已经足够。

## 相关文件

- `src/gpu/graphite/DrawTypes.h` - DepthStencilSettings 结构体定义
- `src/gpu/graphite/RenderStep.h` - 渲染步骤基类（使用这些设置）
- `src/gpu/graphite/render/AnalyticRRectRenderStep.cpp` - 使用 kDirectDepth* 的具体实现
- `src/gpu/graphite/render/TessellateCurvesRenderStep.cpp` - 使用模板-覆盖通道的实现
- `src/gpu/graphite/render/TessellateWedgesRenderStep.cpp` - 扇形细分渲染步骤
- `src/gpu/graphite/render/CoverBoundsRenderStep.cpp` - 覆盖边界渲染步骤
- `src/gpu/graphite/render/MiddleOutFanRenderStep.cpp` - 中间扇出渲染步骤
