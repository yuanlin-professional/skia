# LinearTolerances

> 源文件
> - src/gpu/tessellate/LinearTolerances.h

## 概述

`LinearTolerances` 是 Skia GPU 镶嵌化系统的核心类，用于存储和计算曲线线性化的容差状态。它近似设备空间变换，并据此计算参数曲线和径向分量（描边）所需的分段级别，确定将曲线精确线性化所需的最坏情况参数段数和径向段数。

主要功能：
- 跟踪参数段数（基于Wang公式）
- 跟踪径向段数（描边的曲线旋转）
- 计算填充路径的细分级别（resolve level）
- 计算描边路径的边数（edges）
- 累积多条曲线的最坏情况容差

容差在局部路径空间估算，PatchWriter 使用 2x2 向量变换近似完整的局部到设备空间变换的缩放/倾斜。

## 架构位置

```
skgpu::tess (镶嵌化渲染)
  ├── LinearTolerances (容差计算 - 本类)
  ├── WangsFormula (Wang公式计算)
  ├── PatchWriter (使用容差确定分段)
  ├── FixedCountBufferUtils (使用容差确定顶点数)
  └── 各种镶嵌器
```

## 主要方法

### 查询方法

```cpp
float numParametricSegments_p4() const;        // 参数段数的4次方
float numRadialSegmentsPerRadian() const;      // 每弧度的径向段数
int numEdgesInJoins() const;                   // 连接处的边数
```

### requiredResolveLevel

```cpp
int requiredResolveLevel() const
```

**功能：** 计算填充路径所需的最小细分级别（基于 Wang 公式）。

**实现：** `log16(n^4) == log2(n)`，使用快速 log16 计算。

### requiredStrokeEdges

```cpp
int requiredStrokeEdges() const
```

**功能：** 计算描边路径所需的边数。

**计算步骤：**
1. **最大径向段数** = ceil(numRadialSegmentsPerRadian * π)（180度旋转）
2. **最大参数段数** = ceil(∜numParametricSegments_p4)
3. **描边边数** = 参数段数 + 径向段数（首尾边共享）
4. **总边数** = 连接边数 + 描边边数

### setParametricSegments

```cpp
void setParametricSegments(float n4)
```

**功能：** 设置参数段数的4次方（来自 Wang 公式计算）。

### setStroke

```cpp
void setStroke(const StrokeParams& strokeParams, float maxScale)
```

**功能：** 根据描边参数和最大缩放因子设置描边相关容差。

**实现：**
- 计算近似设备空间描边半径
- 计算每弧度径向段数
- 计算连接处边数（固定边 + 圆形连接的径向边）

### accumulate

```cpp
void accumulate(const LinearTolerances& tolerances)
```

**功能：** 累积另一个容差对象的最坏情况值（取最大值）。

**用途：** 批量处理多条路径时，跟踪所有路径的最坏情况。

## 内部实现细节

### 数据成员

```cpp
private:
    float fNumParametricSegments_p4 = 1.f;      // 至少1个参数段
    float fNumRadialSegmentsPerRadian = 0.f;    // 仅描边使用
    int   fEdgesInJoins = 0;                    // 仅描边使用
```

### 描边边数计算公式

```
参数段数 = ∜(fNumParametricSegments_p4)
径向段数 = ceil(fNumRadialSegmentsPerRadian * π)
描边边数 = 参数段数 + 径向段数
总边数 = 连接边数 + 描边边数
```

**原理：**
- 段数（segments） = 边数（edges） - 1
- 参数和径向的首尾边共享，所以总边数 = 参数段数 + 径向段数

### 优化机会（注释中提到）

1. **更紧的径向段界限**
   - 当前假设最坏情况180度旋转
   - 可以跟踪实际的曲线旋转角度（通过切线点积）
   - 权衡：更多CPU计算 vs 更少GPU工作

2. **圆形连接的旋转角度**
   - 当前假设180度
   - PatchWriter 有所有控制点可以计算实际角度
   - 权衡：CPU vs GPU 和精度 vs 减少 acos 调用

## 依赖关系

### 依赖的头文件

| 头文件 | 用途 |
|--------|------|
| `src/gpu/tessellate/Tessellation.h` | 核心常量和类型 |
| `src/gpu/tessellate/WangsFormula.h` | Wang 公式计算 |
| `include/core/SkScalar.h` | 浮点类型和常量 |

### 被依赖关系

- **PatchWriter** - 使用容差确定是否需要分割曲线
- **FixedCountBufferUtils** - 根据容差计算顶点数和索引数
- **PathTessellator** - 累积路径的容差

## 设计模式与决策

### 存储4次方值

`fNumParametricSegments_p4` 存储 n^4 而非 n：
- Wang 公式直接计算 n^4
- `log16(n^4) = log2(n)`，快速计算细分级别
- 避免 4 次方根运算（除了最终使用时）

### 最坏情况跟踪

使用 `accumulate` 方法跟踪最大值：
- 单次绘制调用处理所有实例
- 必须为最坏情况分配资源
- 避免多次绘制调用的开销

### 分离的参数和径向容差

清晰区分填充（仅参数）和描边（参数 + 径向）：
- 填充路径：仅设置 `fNumParametricSegments_p4`
- 描边路径：额外设置 `fNumRadialSegmentsPerRadian` 和 `fEdgesInJoins`

## 性能考量

### CPU 性能

- 快速 log16 计算细分级别
- 避免浮点除法和开方（尽可能延迟到最后）
- 累积操作仅需简单比较

### GPU 性能

- 更高的容差 → 更多段数 → 更多 GPU 工作
- 平衡 CPU 计算精度和 GPU 工作负载
- 批处理减少绘制调用开销

### 内存效率

类只有 12 字节（2个 float + 1个 int），可高效复制和传递。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/tessellate/WangsFormula.h` | 计算工具 | 提供 Wang 公式计算函数 |
| `src/gpu/tessellate/Tessellation.h` | 核心定义 | 镶嵌化常量和类型 |
| `src/gpu/tessellate/PatchWriter.h` | 使用者 | 根据容差决定分割策略 |
| `src/gpu/tessellate/FixedCountBufferUtils.h` | 使用者 | 根据容差计算顶点数 |
| `src/gpu/tessellate/PathTessellator.h` | 使用者 | 路径镶嵌器累积容差 |
