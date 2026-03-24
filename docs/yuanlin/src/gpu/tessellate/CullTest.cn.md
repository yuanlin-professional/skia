# CullTest

> 源文件
> - src/gpu/tessellate/CullTest.h

## 概述

`CullTest` 是 Skia GPU 镶嵌化系统中用于剔除测试的高性能类。它使用 SIMD 优化的算法快速判断局部空间的点在变换后是否会出现在设备空间的剔除边界内，从而跳过不可见的几何体渲染，提高性能。

核心特性：
- 使用特殊的矩阵表示：M*p → [x, y, -x, -y]
- 矩阵不包含平移，将平移预先应用到剔除边界
- SIMD 向量化所有计算
- 支持单点测试和多点包围盒测试

该类是路径渲染优化的关键组件，在镶嵌化前快速剔除屏幕外的曲线和路径段。

## 架构位置

```
skgpu::tess (镶嵌化渲染)
  ├── CullTest (剔除测试 - 本类)
  ├── PatchWriter (使用 CullTest 跳过不可见补丁)
  ├── PathCurveTessellator (曲线剔除)
  └── StrokeTessellator (描边剔除)
```

## 主要方法

### 构造和设置

```cpp
CullTest() = default;
CullTest(const SkRect& devCullBounds, const SkMatrix& m);
void set(const SkRect& devCullBounds, const SkMatrix& m);
```

**功能：** 初始化剔除测试，设置设备空间剔除边界和变换矩阵。

**实现细节：**
1. **矩阵设置：**
   ```cpp
   // [fMatX, fMatY] 将路径坐标映射到 [x, y, -x, -y]
   fMatX = {scaleX, skewY, -scaleX, -skewY};
   fMatY = {skewX, scaleY, -skewX, -scaleY};
   ```

2. **剔除边界预处理：**
   ```cpp
   // 存储为 [l, t, -r, -b]，并预先减去平移
   fCullBounds = {
       left - translateX,
       top - translateY,
       translateX - right,
       translateY - bottom
   };
   ```

**优点：**
- 无需在每次测试时应用平移
- 统一的比较操作（所有比较都是 `<`）

### isVisible

```cpp
bool isVisible(SkPoint p) const
```

**功能：** 测试单个点变换后是否在剔除边界内。

**实现：**
```cpp
auto devPt = fMatX*p.fX + fMatY*p.fY;  // [x, y, -x, -y]
return all(fCullBounds < devPt);       // l<x && t<y && -r<-x && -b<-y
```

**等价于：** `l < x && t < y && r > x && b > y`

### areVisible3

```cpp
bool areVisible3(const SkPoint p[3]) const
```

**功能：** 测试3个点的设备空间包围盒是否与剔除边界相交。

**实现步骤：**
1. 变换所有3个点到 [x, y, -x, -y] 格式
2. 对每个分量取最大值：`val0 = max(max(val0, val1), val2)`
3. 结果 `val0 = [r, b, -l, -t]` 是包围盒的边界
4. 测试包围盒与剔除边界相交：`all(fCullBounds < val0)`

**等价于：** `l0 < r1 && t0 < b1 && r0 > l1 && b0 > t1`（矩形相交测试）

### areVisible4

```cpp
bool areVisible4(const SkPoint p[4]) const
```

**功能：** 测试4个点的设备空间包围盒是否与剔除边界相交。

**实现：** 与 `areVisible3` 类似，但处理4个点。

## 内部实现细节

### 数据成员

```cpp
private:
    skvx::float4 fMatX;        // 矩阵 X 分量：[scaleX, skewY, -scaleX, -skewY]
    skvx::float4 fMatY;        // 矩阵 Y 分量：[skewX, scaleY, -skewX, -scaleY]
    skvx::float4 fCullBounds;  // 剔除边界：[l, t, -r, -b]
```

### 特殊矩阵表示

标准矩阵变换：
```
x' = scaleX * x + skewX * y + translateX
y' = skewY * x + scaleY * y + translateY
```

CullTest 变换（无平移）：
```
[x, y, -x, -y] = [scaleX, skewY, -scaleX, -skewY] * x +
                 [skewX, scaleY, -skewX, -scaleY] * y
```

**优点：**
- 同时计算正负坐标，用于边界测试
- 所有4个边界检查在单个 SIMD 比较中完成

### 包围盒计算

取最大值操作 `max(val0, val1, ...)` 作用于 [x, y, -x, -y] 向量：
- 取最大 x → 右边界 r
- 取最大 y → 下边界 b
- 取最大 -x → -左边界 -l（即取最小 x）
- 取最大 -y → -上边界 -t（即取最小 y）

结果：[r, b, -l, -t]，正好是包围盒的4个边界。

### SIMD 优化

所有计算使用 `skvx::float4` 向量类型：
- 单条 SIMD 指令完成4个浮点操作
- `all(a < b)` 生成掩码并检查所有位

**性能：** 剔除测试通常只需 4-6 条 CPU 指令。

## 依赖关系

### 依赖的头文件

| 头文件 | 用途 |
|--------|------|
| `include/core/SkMatrix.h` | `SkMatrix` 类型 |
| `include/core/SkRect.h` | `SkRect` 类型 |
| `include/core/SkPoint.h` | `SkPoint` 类型 |
| `src/base/SkVx.h` | SIMD 向量类型 |

### 被依赖关系

- **PatchWriter** - 剔除不可见补丁
- **PathCurveTessellator** - 剔除屏幕外曲线
- **StrokeTessellator** - 剔除屏幕外描边段

## 设计模式与决策

### 预处理平移

将矩阵平移预先应用到剔除边界：
- 避免每次测试时加平移
- 减少每次测试的计算量
- 假设剔除边界固定，变换许多点

### [x, y, -x, -y] 表示

同时计算正负坐标：
- 左/上边界测试需要最小值（负坐标的最大值）
- 右/下边界测试需要最大值（正坐标的最大值）
- 统一表示简化逻辑

### 包围盒测试而非精确测试

对于多点测试，使用包围盒而非逐点测试：
- 更快（单次 SIMD 比较）
- 保守剔除（可能保留部分不可见几何体）
- 权衡：简单性和性能 vs 剔除效率

### 仿射限制

断言矩阵无透视变换：
- 简化数学（无需齐次坐标）
- 镶嵌化在变换后执行，通常在仿射空间
- 透视路径需要不同的剔除策略

## 性能考量

### CPU 性能

- **SIMD 加速：** 所有操作向量化，单指令处理4个 float
- **减少分支：** `all()` 避免多个 if 语句
- **预计算：** 平移预先应用，每次测试不重复计算

### 剔除效率

保守剔除策略：
- **单点测试：** 100% 准确
- **多点测试：** 可能保留部分不可见的曲线（包围盒相交但曲线实际不可见）
- **实践中：** 大部分屏幕外几何体成批剔除，性能提升显著

### 内存占用

类只有 12 字节（3个 float4），可高效复制和传递。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/tessellate/PatchWriter.h` | 使用者 | 补丁写入器使用 CullTest 剔除 |
| `src/gpu/tessellate/PathCurveTessellator.h` | 使用者 | 曲线镶嵌器剔除屏幕外曲线 |
| `src/gpu/tessellate/StrokeTessellator.h` | 使用者 | 描边镶嵌器剔除不可见段 |
| `src/base/SkVx.h` | 基础设施 | SIMD 向量类型 |
| `include/core/SkMatrix.h` | 输入类型 | 变换矩阵 |
