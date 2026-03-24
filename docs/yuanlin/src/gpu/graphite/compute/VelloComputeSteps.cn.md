# VelloComputeSteps

> 源文件: src/gpu/graphite/compute/VelloComputeSteps.h, src/gpu/graphite/compute/VelloComputeSteps.cpp

## 概述

`VelloComputeSteps` 是 Skia Graphite 架构中实现 Vello 渲染管线各个计算阶段的模块。该模块定义了 Vello 矢量图形渲染所需的所有 `ComputeStep` 实现，包括路径展平、切片生成、排序、光栅化和合成等步骤。每个步骤封装了特定的计算着色器逻辑和资源配置。

## 架构位置

```
Graphite Vello 管线：
  ├── VelloComputeSteps（步骤集合）★
  │   ├── PathFlatteningStep
  │   ├── SliceGenerationStep
  │   ├── MergeSortStep
  │   ├── RasterizationStep
  │   └── CompositionStep
  ├── ComputeStep（抽象基类）
  └── DispatchGroup（调度组）
```

## 主要类与结构体

### Vello 计算步骤

```cpp
// 路径展平步骤
class PathFlatteningStep : public ComputeStep {
public:
    std::string computeSkSL() const override;
    WorkgroupSize calculateGlobalDispatchSize() const override;
    void prepareResources(...) const override;
};

// 切片生成步骤
class SliceGenerationStep : public ComputeStep {
    // 类似接口...
};

// 合并排序步骤
class MergeSortStep : public ComputeStep {
    // 类似接口...
};

// 光栅化步骤
class RasterizationStep : public ComputeStep {
    // 类似接口...
};

// 合成步骤
class CompositionStep : public ComputeStep {
    // 类似接口...
};
```

### 工厂函数

```cpp
namespace VelloComputeSteps {
    std::vector<std::unique_ptr<ComputeStep>>
    Create(const VelloScene& scene, const SkIRect& clipRect);
}
```

## 公共 API 函数

### Create 工厂函数

```cpp
std::vector<std::unique_ptr<ComputeStep>>
Create(const VelloScene& scene, const SkIRect& clipRect);
```

**功能**: 根据场景和裁剪区域创建完整的 Vello 计算步骤序列。

**返回值**: 按执行顺序排列的计算步骤向量。

## 内部实现细节

### 1. 路径展平步骤 (PathFlatteningStep)

**功能**: 将贝塞尔曲线转换为直线段。

**输入**: 路径数据（二次/三次贝塞尔曲线）
**输出**: 展平的线段缓冲区

**SkSL 示例**:
```glsl
// 展平二次贝塞尔
void flattenQuadratic(vec2 p0, vec2 p1, vec2 p2) {
    // 递归细分或迭代采样
    for (float t = 0; t <= 1.0; t += step) {
        vec2 point = (1-t)*(1-t)*p0 + 2*(1-t)*t*p1 + t*t*p2;
        emitLineSegment(point);
    }
}
```

### 2. 切片生成步骤 (SliceGenerationStep)

**功能**: 将路径按水平扫描线切分。

**输入**: 线段缓冲区
**输出**: 切片缓冲区（每个扫描线的段列表）

### 3. 合并排序步骤 (MergeSortStep)

**功能**: 按 X 坐标排序每个切片内的段。

**算法**: 并行归并排序

### 4. 光栅化步骤 (RasterizationStep)

**功能**: 计算每个像素的覆盖率和卷绕数。

**算法**:
```glsl
for each pixel (x, y) {
    winding = 0;
    coverage = 0;
    for each segment intersecting y {
        if (segment crosses pixel) {
            winding += segment.direction;
            coverage += segment.coverage;
        }
    }
    output[pixel] = (winding != 0) ? coverage : 0;
}
```

### 5. 合成步骤 (CompositionStep)

**功能**: 应用颜色、渐变和混合模式。

**输入**: 覆盖率缓冲区、样式数据
**输出**: 最终 RGBA 图像

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `ComputeStep` | 抽象基类 |
| `Buffer` | GPU 缓冲区 |
| `ResourceProvider` | 资源创建 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `VelloRenderer` | 构建渲染管线 |
| `DispatchGroup` | 执行计算步骤 |

## 设计模式与设计决策

### 工厂模式

`Create()` 函数根据场景动态创建步骤序列。

### 策略模式

每个步骤实现不同的计算策略（展平、排序、光栅化等）。

### 关键设计决策

1. **多步骤管线**: 将复杂渲染分解为多个简单步骤
2. **中间缓冲区**: 步骤间通过缓冲区传递数据
3. **并行化**: 每个步骤充分利用 GPU 并行能力
4. **可配置性**: 根据场景复杂度调整工作组大小

## 性能考量

### 并行度

- 路径展平: 每条曲线独立并行
- 切片生成: 每个扫描线独立并行
- 光栅化: 每个像素独立并行

### 内存访问

- 使用共享内存减少全局内存访问
- 合并内存访问模式

### 工作组优化

- 根据 GPU 架构选择最优工作组大小（通常256或512）
- 平衡寄存器使用和占用率

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/compute/ComputeStep.h` | 计算步骤抽象 |
| `src/gpu/graphite/compute/VelloRenderer.h` | Vello 渲染器 |
| `src/gpu/graphite/compute/DispatchGroup.h` | 调度组 |
| `src/gpu/graphite/Buffer.h` | GPU 缓冲区 |
