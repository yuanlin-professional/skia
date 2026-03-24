# SkAddIntersections - 交点添加到路径段

> 源文件：[src/pathops/SkAddIntersections.h](../../../../src/pathops/SkAddIntersections.h)、[src/pathops/SkAddIntersections.cpp](../../../../src/pathops/SkAddIntersections.cpp)

## 概述

`SkAddIntersections` 模块负责将两个轮廓之间的所有交叉点计算并添加到路径操作的数据结构中。它是 PathOps 处理流水线中交叉检测阶段的顶层协调者，遍历两个轮廓的所有段对，根据曲线类型分发到 `SkIntersections` 的相应方法，然后将检测到的交点添加为段上的跨度。

## 架构位置

```
PathOps 处理流水线
  ├── SkOpEdgeBuilder (输入转换)
  ├── SkAddIntersections (交叉检测) ← 本文件
  │     ├── SkIntersectionHelper (段包装)
  │     ├── SkIntersections (底层交叉计算)
  │     └── SkOpSegment::addT (交点添加)
  ├── SkOpCoincidence (重合处理)
  └── 缠绕数计算与路径输出
```

`AddIntersectTs` 是路径操作中第一个实质性的计算步骤（在数据结构构建之后），其结果直接影响后续所有处理。

## 主要类与结构体

该文件的公共接口极其简洁，只有一个函数声明。

## 公共 API 函数

### `AddIntersectTs(SkOpContour* test, SkOpContour* next, SkOpCoincidence* coincidence)`
计算 `test` 和 `next` 两个轮廓之间的所有交叉点，并将结果添加到各段的跨度链表中。同时检测并记录重合段到 `coincidence`。

**处理流程：**
1. 遍历 `test` 轮廓的所有段。
2. 对每个段，遍历 `next` 轮廓的所有段。
3. 先做边界框快速排除。
4. 根据两段的曲线类型（line/quad/conic/cubic），调用对应的 `SkIntersections` 方法。
5. 将计算得到的交点通过 `addT` 添加到两段上。
6. 检测并记录重合段。

## 内部实现细节

### 曲线类型分发
cpp 文件中包含大量根据曲线类型组合（line-line、line-quad、quad-quad、conic-line、cubic-cubic 等）分发到不同计算方法的逻辑。每种组合使用针对性的算法，低阶组合使用解析解，高阶组合使用 T-区间细分。

### 调试输出
在 `DEBUG_ADD_INTERSECTING_TS` 开关下，为每种曲线组合提供了详细的调试输出函数（如 `debugShowLineIntersection`、`debugShowQuadIntersection` 等），输出格式与 PathOps 调试格式字符串宏兼容。

### 交叉点验证
计算出的交叉点会进行端点精确匹配和近似匹配的双重验证，确保交点坐标与两条曲线上对应的参数值一致。

### 重合检测
当交叉计算返回重合标记时，自动将重合信息传递给 `SkOpCoincidence` 进行后续处理。

## 依赖关系

- **SkIntersectionHelper**：段的包装器，提供统一的曲线访问接口。
- **SkIntersections**：底层交叉计算。
- **SkOpContour / SkOpSegment**：数据结构。
- **SkOpCoincidence**：重合段管理。
- **SkOpSpan / SkOpPtT**：交点存储。
- **SkPathOpsBounds**：边界框快速排除。
- **所有曲线类型**：SkDLine、SkDQuad、SkDConic、SkDCubic。

## 设计模式与设计决策

### 简洁的公共接口
整个模块只暴露一个函数，将复杂的交叉检测逻辑封装在实现文件中。这简化了调用者的使用并允许内部实现自由演化。

### 类型分发
使用 `SkPath::Verb` 进行运行时类型分发，而非编译时多态。这符合 PathOps 模块的整体设计风格。

### 边界框预过滤
在执行任何昂贵的交叉计算之前，先用边界框快速排除不可能相交的段对。

## 性能考量

- **边界框排除**：O(1) 的边界框测试排除大部分不相交的段对。
- **N^2 段对遍历**：两个轮廓的段对为 O(N*M)，但边界框排除使实际计算量远小于此。
- **调试输出隔离**：大量调试代码通过编译开关隔离，不影响 release 性能。

## 相关文件

- `src/pathops/SkIntersectionHelper.h`：段包装器。
- `src/pathops/SkIntersections.h`：交叉计算核心。
- `src/pathops/SkOpContour.h`：轮廓定义。
- `src/pathops/SkOpSegment.h`：段定义。
- `src/pathops/SkOpCoincidence.h`：重合段管理。
