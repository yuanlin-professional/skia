# FillRRectOp

> 源文件
> - src/gpu/ganesh/ops/FillRRectOp.h
> - src/gpu/ganesh/ops/FillRRectOp.cpp

## 概述

`FillRRectOp` 是 Ganesh GPU 后端中用于高效渲染圆角矩形（Round Rect）的专用操作。该操作使用实例化渲染技术，通过自定义的几何处理器和着色器实现高质量的抗锯齿圆角矩形填充。它支持多种圆角矩形类型（简单圆角、九宫格、复杂圆角等），能够处理仿射变换，并提供了优化的裁剪合并功能。

该实现使用分析抗锯齿（analytical AA）在片段着色器中计算覆盖率，避免了传统的路径渲染开销。对于角落部分，使用椭圆公式精确计算距离；对于边缘部分，使用线性覆盖率渐变。

## 架构位置

`FillRRectOp` 位于 Ganesh 渲染管线的操作层，专门处理圆角矩形几何体：

- **上层**：由 `SurfaceDrawContext` 调用，响应高层绘制 API
- **同层**：继承自 `GrMeshDrawOp`，与其他几何操作（如 `FillRectOp`, `GrOvalOpFactory`）并列
- **下层**：使用 `GrGeometryProcessor` 定义顶点处理，通过 `GrOpFlushState` 提交绘制命令

在绘制流水线中，该操作是圆角矩形从高层形状描述到底层 GPU 指令的关键转换点。

## 主要类与结构体

### 类层次结构

```
GrOp
    └── GrDrawOp
        └── GrMeshDrawOp
            └── FillRRectOpImpl
```

### FillRRectOpImpl 关键成员

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fHelper` | `GrSimpleMeshDrawOpHelper` | 简化网格绘制操作的辅助类 |
| `fProcessorFlags` | `ProcessorFlags` | 处理器标志（HW 导数、局部坐标、宽色域等） |
| `fHeadInstance` | `Instance*` | 实例链表头 |
| `fTailInstance` | `Instance**` | 实例链表尾指针 |
| `fInstanceCount` | `int` | 实例数量 |
| `fInstanceBuffer` | `sk_sp<const GrBuffer>` | 实例数据缓冲区 |
| `fVertexBuffer` | `sk_sp<const GrBuffer>` | 顶点缓冲区（共享静态几何数据） |
| `fIndexBuffer` | `sk_sp<const GrBuffer>` | 索引缓冲区（共享静态索引数据） |
| `fProgramInfo` | `GrProgramInfo*` | 程序信息（用于预准备路径） |

### Instance 结构体

表示单个圆角矩形实例：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fViewMatrix` | `SkMatrix` | 视图变换矩阵 |
| `fRRect` | `SkRRect` | 圆角矩形 |
| `fLocalCoords` | `LocalCoords` | 局部坐标（矩形或矩阵形式） |
| `fColor` | `SkPMColor4f` | 预乘 alpha 颜色 |
| `fNext` | `Instance*` | 链表下一个节点 |

### LocalCoords 联合体

```cpp
struct LocalCoords {
    enum class Type : bool { kRect, kMatrix };
    Type fType;
    union {
        SkRect fRect;       // 简单矩形局部坐标
        SkMatrix fMatrix;   // 完整矩阵局部坐标
    };
};
```

### ProcessorFlags 枚举

| 标志 | 值 | 说明 |
|------|---|------|
| `kNone` | 0 | 无特殊标志 |
| `kUseHWDerivatives` | 1 << 0 | 使用硬件导数（fwidth） |
| `kHasLocalCoords` | 1 << 1 | 需要局部坐标 |
| `kWideColor` | 1 << 2 | 宽色域颜色 |
| `kMSAAEnabled` | 1 << 3 | MSAA 启用 |
| `kFakeNonAA` | 1 << 4 | 禁用抗锯齿 |

### Processor 内部类

`FillRRectOpImpl::Processor` 是自定义的几何处理器，定义顶点和实例属性：

**顶点属性**：
- `radii_selector`：半径选择器（4D 向量，用于选择角落）
- `corner_and_radius_outsets`：角落位置和半径偏移
- `aa_bloat_and_coverage`：抗锯齿扩展方向和覆盖率

**实例属性**：
- `radii_x`, `radii_y`：四个角的 X 和 Y 半径
- `skew`：变换矩阵的缩放和倾斜分量
- `translate_and_localrotate`：平移和局部旋转
- `localrect`：局部坐标矩形（可选）
- `color`：颜色

## 公共 API 函数

### 工厂方法

```cpp
GrOp::Owner Make(GrRecordingContext* ctx,
                 SkArenaAlloc* arena,
                 GrPaint&& paint,
                 const SkMatrix& viewMatrix,
                 const SkRRect& rrect,
                 const SkRect& localRect,
                 GrAA aa)
```
创建使用矩形局部坐标的圆角矩形填充操作。

```cpp
GrOp::Owner Make(GrRecordingContext* ctx,
                 SkArenaAlloc* arena,
                 GrPaint&& paint,
                 const SkMatrix& viewMatrix,
                 const SkRRect& rrect,
                 const SkMatrix& localMatrix,
                 GrAA aa)
```
创建使用矩阵局部坐标的圆角矩形填充操作。

两个工厂方法都会进行预检查：
- 不支持透视变换（`viewMatrix.hasPerspective()`）
- 不支持实例化渲染的设备
- 尺寸过大（超过 1e6）导致数学溢出的情况

## 内部实现细节

### 几何表示

圆角矩形在标准化的 `[-1, -1, +1, +1]` 空间中绘制，由以下几何组成：

1. **内嵌八边形**：实心覆盖区域（索引 0-7）
2. **边缘渐变带**：四条边的线性覆盖率渐变（索引 8-15）
3. **角落弧形**：四个角的椭圆弧覆盖（每角 6 个顶点，索引 16-39）

顶点数据 `kVertexData` 包含 40 个顶点，索引数据 `kIndexData` 包含 114 个索引（38 个三角形）。

### 八边形角落处理

角落使用 `kOctoOffset = 1/(1 + √2/2)` 定义八边形顶点，避免在高椭圆率情况下使用矩形导致的覆盖问题。

### 硬件导数优化

函数 `can_use_hw_derivatives_with_coverage` 检查是否可以使用硬件导数（`fwidth`）：

```cpp
bool can_use_hw_derivatives_with_coverage(const skvx::float2& devScale,
                                          const skvx::float2& cornerRadii) {
    skvx::float2 devRadii = devScale * cornerRadii;
    if (devRadii[1] < devRadii[0]) {
        devRadii = skvx::shuffle<1,0>(devRadii);
    }
    float minDevRadius = std::max(devRadii[0], 1.f);
    return minDevRadius * minDevRadius * 5 > devRadii[1];
}
```

该检查确保高椭圆率的角落不会因硬件导数精度问题而产生视觉瑕疵。阈值 `minDevRadius² × 5 > maxDevRadius` 是在 NVIDIA 芯片上主观测试得出的。

### 变换处理

操作不支持透视但支持仿射变换。变换分解为：
- 缩放和倾斜（`skew`）：用于顶点变换
- 平移（`translate`）：添加到最终位置

半径在标准化空间中缩放：
```cpp
radiiX *= 2 / (r - l);
radiiY *= 2 / (b - t);
```

### 裁剪优化

`clipToShape` 方法实现几何裁剪优化，当裁剪形状也是矩形或圆角矩形时：

1. 将裁剪形状变换到视图矩阵空间
2. 计算圆角矩形的保守交集（`SkRRectPriv::ConservativeIntersect`）
3. 更新局部坐标以保持纹理映射连续性
4. 避免子像素情况（宽度或高度 < 1px）

### 实例合并

`onCombineIfPossible` 将兼容的操作合并到实例链表中：

```cpp
GrOp::CombineResult FillRRectOpImpl::onCombineIfPossible(GrOp* op,
                                                         SkArenaAlloc*,
                                                         const GrCaps& caps) {
    auto that = op->cast<FillRRectOpImpl>();
    if (!fHelper.isCompatible(that->fHelper, caps, this->bounds(), that->bounds()) ||
        fProcessorFlags != that->fProcessorFlags) {
        return CombineResult::kCannotCombine;
    }
    *fTailInstance = that->fHeadInstance;
    fTailInstance = that->fTailInstance;
    fInstanceCount += that->fInstanceCount;
    return CombineResult::kMerged;
}
```

合并条件：
- 辅助类兼容（混合模式、裁剪等）
- 处理器标志相同

### 覆盖率计算

片段着色器中的覆盖率计算：

**线性覆盖**（边缘）：
```glsl
coverage = y;  // 直接插值
```

**弧形覆盖**（角落）：
```glsl
float fn = x * (x - 2);       // fn = x² - 1 (因为传入 x+1)
fn = fma(y, y, fn);           // fn = x² + y² - 1
float fnwidth = fwidth(fn);   // 或手动插值梯度
coverage = 0.5 - fn / fnwidth;
```

椭圆公式 `x² + y² = 1` 的符号距离场用于计算覆盖率。

### MSAA 支持

当 MSAA 启用时（`kMSAAEnabled`），抗锯齿渐变带宽度加倍：

```glsl
float aa_bloat_multiplier = (kMSAAEnabled) ? 2 : 1;
```

覆盖率范围从 `[0, 1]` 扩展到 `[-0.5, 1.5]`，确保多采样覆盖所有部分覆盖的像素。

### 小半径处理

当半径小于 1.5 个像素长度时，角落退化为 90 度尖角：

```glsl
if (any(lessThan(radii, aa_bloatradius * 1.5))) {
    radii = float2(0);
    aa_bloat_direction = sign(corner);
    is_linear_coverage = 1;
}
```

这避免了微小圆角的渲染瑕疵。

### 窄矩形处理

当圆角矩形比半像素抗锯齿渐变带更窄时：

```glsl
if (any(greaterThan(aa_bloatradius, float2(1)))) {
    corner = max(abs(corner), aa_bloatradius) * sign(corner);
    coverage_multiplier = 1 / (max(aa_bloatradius.x, 1) * max(aa_bloatradius.y, 1));
    radii = float2(0);
}
```

通过调整尺寸到渐变带宽度，然后缩放覆盖率来保持视觉尺寸。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrMeshDrawOp` | 基类，提供网格绘制基础设施 |
| `GrSimpleMeshDrawOpHelper` | 简化处理器集合和绘制状态管理 |
| `GrGeometryProcessor` | 定义顶点/实例属性和着色器 |
| `SkRRect` | 圆角矩形表示 |
| `SkMatrix` | 仿射变换 |
| `GrBuffer` | GPU 缓冲区 |
| `GrOpFlushState` | 刷新状态和绘制提交 |
| `GrResourceProvider` | 缓冲区分配 |
| `SkRRectPriv` | 圆角矩形私有工具（交集计算） |
| `skvx` | SIMD 向量运算 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SurfaceDrawContext` | 调用 `FillRRectOp::Make` 创建操作 |
| `GrShape` | 形状表示可能触发圆角矩形路径 |
| 高层绘制 API | 通过 `drawRRect` 间接使用 |

## 设计模式与设计决策

### 实例化渲染

使用 GPU 实例化渲染一次提交多个圆角矩形：
- **共享几何数据**：所有实例使用相同的顶点和索引缓冲区
- **每实例数据**：变换矩阵、半径、颜色等存储在实例缓冲区
- **高效合并**：兼容的操作可以合并为单个绘制调用

优势：减少 CPU 开销和绘制调用数量。

### 标准化空间

在 `[-1, -1, +1, +1]` 标准化空间中定义几何：
- 半径独立于实际尺寸
- 顶点着色器应用缩放和平移变换
- 简化着色器逻辑

### 分析抗锯齿

使用数学公式在片段着色器中计算覆盖率：
- **精确**：基于精确的椭圆距离函数
- **高效**：避免多采样或路径渲染开销
- **灵活**：支持任意变换和半径

### 硬件导数自适应

根据角落的椭圆率决定是否使用硬件导数：
- **快速路径**：使用 `fwidth` 的硬件导数（所有平台都更快）
- **精确路径**：手动插值梯度（高椭圆率情况）

### 几何裁剪优化

当裁剪形状也是圆角矩形时，直接在几何层面裁剪：
- 减少片段着色器执行
- 避免裁剪硬件开销
- 保持局部坐标连续性

### 静态缓冲区重用

顶点和索引数据是静态的，通过唯一键在所有实例间共享：

```cpp
SKGPU_DEFINE_STATIC_UNIQUE_KEY(gVertexBufferKey);
fVertexBuffer = target->resourceProvider()->findOrMakeStaticBuffer(
    GrGpuBufferType::kVertex, sizeof(kVertexData), kVertexData, gVertexBufferKey);
```

### 处理器标志位域

使用位域紧凑表示处理器变体，减少着色器排列数：
- 只有 5 个标志，32 种可能组合
- 通过标志动态生成着色器代码
- 平衡编译时间和运行时效率

## 性能考量

### 实例化渲染批处理

通过合并多个圆角矩形到单个绘制调用，大幅减少：
- CPU 开销（状态设置）
- GPU 驱动开销
- 绘制调用数量

典型场景：UI 列表中的多个卡片/按钮。

### 静态几何数据

顶点和索引缓冲区在首次使用后缓存，避免：
- 重复缓冲区创建
- 重复数据上传
- 内存分配开销

### 硬件导数性能

`fwidth()` 在所有平台上始终比手动插值梯度更快：
- 硬件原生支持
- 避免额外的 varying 插值
- 减少寄存器压力

### SIMD 优化

使用 `skvx` SIMD 库进行向量运算：
```cpp
skvx::float4 radiiX, radiiY;
skvx::strided_load2(&SkRRectPriv::GetRadiiArray(i->fRRect)->fX, radiiX, radiiY);
radiiX *= 2 / (r - l);
radiiY *= 2 / (b - t);
```

### 内存布局

实例数据紧凑打包，减少带宽：
- 半径归一化到 [-1, 1] 范围
- 使用 float4 对齐
- 避免填充字节

### 着色器分支优化

使用 `is_linear_coverage` 标志区分线性和弧形覆盖，避免动态分支：
```glsl
if (0 == x_plus_1) {
    coverage = y;  // 快速路径
} else {
    // 弧形计算路径
}
```

编译器可以优化为条件移动指令。

### 早期退出

在 `Make` 工厂方法中进行早期检查：
- 不支持的变换类型
- 过大的尺寸
- 不支持实例化的设备

避免创建无法执行的操作。

### 裁剪优化收益

几何裁剪可以显著减少片段着色器调用：
- 裁剪掉不可见像素
- 减少 overdraw
- 提高像素填充率

特别在复杂裁剪场景下（如圆角裁剪区域）收益明显。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/ops/GrMeshDrawOp.h` | 继承 | 网格绘制操作基类 |
| `src/gpu/ganesh/ops/GrSimpleMeshDrawOpHelper.h` | 使用 | 简化操作辅助类 |
| `src/gpu/ganesh/GrGeometryProcessor.h` | 使用 | 几何处理器基类 |
| `include/core/SkRRect.h` | 依赖 | 圆角矩形定义 |
| `src/core/SkRRectPriv.h` | 依赖 | 圆角矩形私有工具 |
| `src/gpu/ganesh/ops/FillRectOp.h` | 相关 | 矩形填充操作 |
| `src/gpu/ganesh/ops/GrOvalOpFactory.h` | 相关 | 椭圆/圆形操作工厂 |
| `src/gpu/ganesh/GrOpFlushState.h` | 依赖 | 操作刷新状态 |
| `src/gpu/ganesh/GrResourceProvider.h` | 依赖 | 资源分配 |
| `src/base/SkVx.h` | 依赖 | SIMD 向量库 |
