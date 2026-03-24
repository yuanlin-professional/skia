# FuzzTriangulation

> 源文件: fuzz/FuzzTriangulation.cpp

## 概述

`FuzzTriangulation.cpp` 是 Skia 图形库的模糊测试文件,专门用于测试 GPU 路径三角剖分(triangulation)功能。该 fuzzer 通过生成随机的复杂路径,并将其转换为三角形网格,以发现路径几何处理中的潜在崩溃、断言失败或内存错误。三角剖分是 GPU 渲染管道的核心步骤,将任意复杂的矢量路径转换为 GPU 可以高效渲染的三角形图元。

## 架构位置

该文件位于 Skia 的模糊测试框架中:

```
skia/
  └── fuzz/
      ├── Fuzz.h (模糊测试基础设施)
      ├── FuzzCommon.h (公共fuzzing辅助函数)
      └── FuzzTriangulation.cpp (本文件)
```

**在 GPU 渲染管线中的位置**:
```
SkPath (矢量路径)
    ↓
GrTriangulator (三角剖分器)
    ↓
Vertex Buffer (顶点缓冲区)
    ↓
GPU Shader (片段着色器)
    ↓
渲染输出
```

**测试目标组件**:
- `GrTriangulator`: Ganesh GPU 后端的三角剖分器
- `GrPathUtils`: 路径几何工具函数
- `GrEagerVertexAllocator`: 顶点内存分配器

## 主要类与结构体

### DEF_FUZZ 宏定义的测试

```cpp
DEF_FUZZ(Triangulation, fuzz)
```

**功能**: 定义名为 "Triangulation" 的模糊测试入口点。

**参数**:
- `fuzz`: `Fuzz*` 类型指针,提供随机数据流

**核心组件**:

1. **GrTriangulator**:
   - 将 `SkPath` 转换为三角形列表
   - 处理复杂填充规则(even-odd, winding)
   - 支持自相交路径

2. **GrCpuVertexAllocator**:
   - 在 CPU 内存中分配顶点数据
   - 管理顶点缓冲区生命周期

3. **FuzzEvilPath**:
   - 生成"邪恶"的测试路径
   - 包含极端几何情况(重合点、退化三角形等)

## 公共 API 函数

### Triangulation Fuzzer

```cpp
DEF_FUZZ(Triangulation, fuzz)
```

**功能**: 模糊测试三角剖分功能的主入口。

**执行流程**:

1. **路径生成**:
   ```cpp
   SkPath path = FuzzEvilPath(fuzz, SkPath::Verb::kDone_Verb);
   ```
   - 生成包含随机几何操作的路径
   - `SkPath::Verb::kDone_Verb` 表示生成完整路径

2. **容差计算**:
   ```cpp
   SkScalar tol = GrPathUtils::scaleToleranceToSrc(
       GrPathUtils::kDefaultTolerance,
       SkMatrix::I(),
       path.getBounds()
   );
   ```
   - 根据路径边界框计算几何容差
   - 用于控制三角剖分精度

3. **裁剪边界**:
   ```cpp
   SkRect clipBounds = path.getBounds();
   ```
   - 使用路径边界作为裁剪区域
   - 影响反向填充路径的处理

4. **三角剖分执行**:
   ```cpp
   int count = GrTriangulator::PathToTriangles(
       path, tol, clipBounds, &allocator, &isLinear
   );
   ```
   - 执行实际的三角剖分
   - 返回生成的三角形数量

5. **资源清理**:
   ```cpp
   if (count > 0) {
       allocator.detachVertexData();
   }
   ```
   - 释放顶点数据,模拟正常渲染流程
   - 防止内存泄漏

## 内部实现细节

### 编译条件

```cpp
#if !defined(SK_ENABLE_OPTIMIZE_SIZE)
// ... 测试代码
#endif
```

**原因**: 在代码大小优化构建中禁用此 fuzzer,因为三角剖分器可能被简化或移除。

### FuzzEvilPath 的作用

`FuzzEvilPath` 会生成包含以下极端情况的路径:
- 非常小的线段
- 接近共线的点
- 自相交路径
- 退化的贝塞尔曲线
- 数值精度边界情况

### 三角剖分算法

`GrTriangulator` 使用以下技术:
- **Ear Clipping** (耳切法): 用于简单多边形
- **Constrained Delaunay Triangulation** (约束 Delaunay): 用于复杂路径
- **Sweep Line**: 处理大量顶点的高效算法

### isLinear 标志

```cpp
bool isLinear;
```

**含义**: 路径是否只包含线性片段(无曲线)。
- `true`: 优化路径,无需曲线细分
- `false`: 包含二次或三次贝塞尔曲线

## 依赖关系

**头文件依赖**:
- `fuzz/Fuzz.h`: 模糊测试框架核心
- `fuzz/FuzzCommon.h`: 公共fuzzing辅助函数(`FuzzEvilPath`)
- `include/core/SkPath.h`: 路径数据结构
- `src/gpu/ganesh/GrEagerVertexAllocator.h`: 顶点分配器
- `src/gpu/ganesh/geometry/GrPathUtils.h`: 几何工具函数
- `src/gpu/ganesh/geometry/GrTriangulator.h`: 三角剖分器

**库依赖**:
- Skia Core: 路径和几何基础
- Ganesh GPU Backend: GPU 渲染后端

## 设计模式与设计决策

### 1. 模糊测试模式 (Fuzz Testing Pattern)

通过随机输入发现边界情况和错误。

**优势**:
- 自动发现意外的崩溃
- 覆盖人工测试难以构造的情况
- 持续集成中自动执行

### 2. 资源获取即初始化 (RAII)

通过 `GrCpuVertexAllocator` 管理顶点内存:
- 自动分配
- 异常安全
- 显式 `detachVertexData()` 转移所有权

### 3. 防御性编程

```cpp
if (count > 0) {
    allocator.detachVertexData();
}
```

只有成功生成三角形时才释放资源,避免无效操作。

## 性能考量

### Fuzzer 执行效率

- **路径复杂度**: 随机生成的路径可能极其复杂
- **三角剖分成本**: 最坏情况 O(n²),n 为顶点数
- **内存分配**: 大量顶点需要显著内存

### 优化策略

1. **尺寸限制**: 编译时排除(SK_ENABLE_OPTIMIZE_SIZE)
2. **超时机制**: Fuzzer 框架提供执行时间限制
3. **容差调整**: 较大的容差减少三角形数量

### 性能监控

在 fuzzing 过程中监控:
- 执行时间(检测性能退化)
- 内存峰值(检测内存泄漏)
- 生成的三角形数量(合理性检查)

## 相关文件

**同目录 fuzzer**:
- `fuzz/FuzzCanvas.cpp`: 测试 Canvas API
- `fuzz/FuzzPathop.cpp`: 测试路径操作(布尔运算)
- `fuzz/FuzzGrStyledShape.cpp`: 测试 GPU 形状样式

**OSS-Fuzz 版本**:
- `fuzz/oss_fuzz/FuzzTriangulation.cpp`: 用于 Google OSS-Fuzz 的版本

**被测试的实现**:
- `src/gpu/ganesh/geometry/GrTriangulator.cpp`: 三角剖分器实现
- `src/gpu/ganesh/geometry/GrPathUtils.cpp`: 路径工具函数

**构建配置**:
- `BUILD.bazel` 或 `gn` 文件: 定义fuzzer编译目标

**运行示例**:
```bash
# 使用 Skia 的 fuzz 工具
out/Debug/fuzz -t api -n Triangulation

# 提供种子文件
out/Debug/fuzz -t api -n Triangulation -b seed_file

# 集成到 OSS-Fuzz
# 自动在 Google 基础设施上连续运行
```

**Bug 报告示例**:
当 fuzzer 发现问题时,会生成包含:
- 触发崩溃的输入数据(seed file)
- 堆栈跟踪
- 内存错误报告(AddressSanitizer)

该 fuzzer 是 Skia 质量保证的重要组成部分,通过大量随机测试确保 GPU 路径渲染的稳定性和可靠性。
