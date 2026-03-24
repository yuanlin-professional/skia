# bench/graphite/ - Graphite GPU 后端基准测试

## 概述

`bench/graphite/` 目录包含针对 Skia Graphite GPU 后端专用数据结构和算法的性能基准测试。Graphite 是 Skia 的下一代 GPU 渲染后端，其内部使用了一些独特的几何管理数据结构来优化绘制顺序和批处理，这些基准测试专门衡量这些关键组件的性能。

当前目录包含两个基准测试文件，分别测试 Graphite 渲染引擎中两个关键的空间管理数据结构：`BoundsManager`（边界管理器）和 `IntersectionTree`（相交树）。这些数据结构在 Graphite 的绘制命令排序和合并过程中发挥着至关重要的作用。

`BoundsManager` 负责跟踪绘制操作的空间边界，确定绘制顺序以实现正确的画家算法（Painter's Order）排序。`IntersectionTree` 用于高效检测绘制区域之间的重叠关系，帮助 Graphite 决定哪些绘制操作可以合并到同一个绘制集（draw set）中。

## 架构图

```
+--------------------------------------------------+
|           nanobench (基准测试运行器)               |
|  +----------------------------------------------+|
|  |         BenchRegistry 注册                    ||
|  +----------------------------------------------+|
+--------------------+-----------------------------+
                     |
      +--------------+--------------+
      |                             |
+-----v-----------+    +----------v-----------+
| BoundsManager   |    | IntersectionTree    |
| Bench            |    | Bench               |
| (边界管理器基准)  |    | (相交树基准)         |
+-----+------------+    +----------+-----------+
      |                             |
      v                             v
+------------------+    +---------------------+
| src/gpu/graphite/|    | src/gpu/graphite/   |
| geom/            |    | geom/               |
| BoundsManager.h  |    | IntersectionTree.h  |
+------------------+    +---------------------+
```

## 目录结构

```
bench/graphite/
├── BoundsManagerBench.cpp       # BoundsManager 性能基准测试
└── IntersectionTreeBench.cpp    # IntersectionTree 性能基准测试
```

## 关键类与函数

### BoundsManagerBench.cpp

```cpp
namespace skgpu::graphite {

class BoundsManagerBench : public Benchmark {
public:
    BoundsManagerBench(std::unique_ptr<BoundsManager> manager);

protected:
    virtual void gatherRects(TArray<SkRect>* rects) = 0; // 子类提供矩形数据
    bool isSuitableFor(Backend backend) override;         // 仅支持 kNonRendering
    void onDelayedSetup() final;                          // 转换 SkRect -> Rect
    void onDraw(int loops, SkCanvas*) final;              // 执行基准测试循环
};

} // namespace skgpu::graphite
```

此基准测试的关键特性：
- 支持从 SVG/SKP 文件中提取真实路径数据作为输入
- 使用 `--boundsManagerFile` 命令行参数指定数据源
- 当无外部数据时，使用随机生成的矩形
- 仅在 `kNonRendering` 后端运行（纯算法性能测试）
- 使用 `SkArenaAlloc` 进行对齐内存分配

### IntersectionTreeBench.cpp

类似结构，专注于测试 `IntersectionTree` 的插入和查询性能。`IntersectionTree` 是 Graphite 中用于检测绘制操作之间空间重叠的核心数据结构。

### 测试维度

两个基准测试都支持以下测试维度：
- **随机数据**：使用 `SkRandom` 生成随机矩形
- **真实数据**：从 SVG 或 SKP 文件中提取实际绘制区域的路径边界
- **不同规模**：从几十个到数千个矩形不等

## 依赖关系

```
bench/graphite/ 依赖:
├── bench/Benchmark.h                    (基准测试基类)
├── src/gpu/graphite/geom/BoundsManager.h (边界管理器)
├── src/gpu/graphite/geom/IntersectionTree.h (相交树)
├── src/base/SkArenaAlloc.h              (Arena 内存分配器)
├── src/base/SkRandom.h                  (随机数生成)
├── tools/ToolUtils.h                    (通用工具)
├── tools/flags/CommandLineFlags.h       (命令行参数)
└── tools/SvgPathExtractor.h             (SVG 路径提取, 可选)
```

## 设计模式分析

### 1. 模板方法模式

`BoundsManagerBench` 定义了固定的测试流程（setup -> gather rects -> benchmark loop），子类通过覆写 `gatherRects()` 提供不同的输入数据。

### 2. 策略模式

通过构造函数注入不同的 `BoundsManager` 实现，同一个基准测试框架可以测试不同的空间管理算法实现。

### 3. 数据驱动测试

支持通过命令行参数加载真实场景数据，使基准测试结果更贴近实际使用场景。

## 数据流

```
基准测试执行流程:

1. 数据准备
   命令行参数 --boundsManagerFile
          |
          +-- 有文件 --> SVG/SKP 路径提取 --> 矩形列表
          |
          +-- 无文件 --> SkRandom 生成随机矩形

2. 初始化
   SkRect[] --> 转换为 Graphite Rect[] (对齐分配)

3. 测量循环
   for (loops) {
       for (每个矩形) {
           BoundsManager/IntersectionTree 操作
       }
       统计 CompressedPaintersOrder 分组数
   }

4. 输出
   性能数据 --> nanobench 统计 --> JSON 结果
```

## 相关文档与参考

- `bench/Benchmark.h` - 基准测试基类
- `src/gpu/graphite/geom/BoundsManager.h` - BoundsManager 接口
- `src/gpu/graphite/geom/IntersectionTree.h` - IntersectionTree 实现
- `bench/nanobench.cpp` - 基准测试运行器
- `tests/graphite/BoundsManagerTest.cpp` - BoundsManager 正确性测试
- `tests/graphite/IntersectionTreeTest.cpp` - IntersectionTree 正确性测试
