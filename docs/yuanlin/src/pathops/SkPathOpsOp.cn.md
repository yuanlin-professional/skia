# SkPathOpsOp

> 源文件: src/pathops/SkPathOpsOp.cpp

## 概述

`SkPathOpsOp.cpp` 是 Skia 路径操作(Path Operations)模块的核心实现文件,负责实现路径之间的布尔运算操作,包括并集(Union)、交集(Intersect)、差集(Difference)、异或(XOR)和反向差集(Reverse Difference)。该文件实现了将两个复杂路径进行组合运算并生成新路径的完整算法流程,是 Skia 矢量图形处理能力的关键组成部分。

该模块采用扫描线算法和角度排序策略,通过将路径分解为线段、计算交点、追踪轮廓边界等步骤,最终构造出符合布尔运算语义的结果路径。这些操作广泛应用于矢量图形编辑、字体渲染、2D 图形合成等场景。

## 架构位置

`SkPathOpsOp.cpp` 位于 Skia 的路径操作子系统中:

- **模块路径**: `src/pathops/`
- **上层接口**: 通过 `include/pathops/SkPathOps.h` 向外部暴露 `Op()` 函数
- **依赖组件**:
  - `SkPath`: Skia 的核心路径表示类
  - `SkOpContour`: 路径轮廓的内部表示
  - `SkOpSegment`: 路径段的表示
  - `SkOpCoincidence`: 重合边处理
  - `SkPathWriter`: 路径构建工具
  - `SkOpEdgeBuilder`: 边构建器
- **被依赖者**: 上层图形库、UI框架、矢量图形编辑工具等

该文件是路径操作管道的最顶层协调者,负责调度各个子模块完成复杂的几何计算任务。

## 主要类与结构体

### 核心数据结构

1. **SkOpContourHead**
   - 轮廓链表的头节点
   - 管理参与运算的所有路径轮廓
   - 支持遍历和段管理

2. **SkOpSegment**
   - 表示路径的单个线段(直线、二次曲线、三次曲线)
   - 维护缠绕数(winding number)信息
   - 支持角度排序和活动边判断

3. **SkOpSpanBase / SkOpSpan**
   - 表示线段上的点和跨度
   - 存储交点信息和参数化坐标
   - 支持前后遍历和追踪

4. **SkOpGlobalState**
   - 全局状态管理器
   - 维护内存分配器(SkSTArenaAlloc)
   - 调试和错误追踪支持

5. **SkOpCoincidence**
   - 处理重合边的特殊情况
   - 管理重合点对和重合段
   - 确保拓扑一致性

6. **SkPathWriter**
   - 构建输出路径
   - 管理轮廓的打开/关闭状态
   - 支持曲线和直线的添加

### 关键查找表

```cpp
static const SkPathOp gOpInverse[kReverseDifference_SkPathOp + 1][2][2]
```
- 根据输入路径的填充模式(内部/外部)映射操作类型
- 处理反转填充(inverse fill)的情况

```cpp
static const bool gOutInverse[kReverseDifference_SkPathOp + 1][2][2]
```
- 确定结果路径是否应使用反转填充

## 公共 API 函数

### `Op(const SkPath& one, const SkPath& two, SkPathOp op) -> std::optional<SkPath>`

对两个路径执行指定的布尔运算操作。

**参数**:
- `one`: 第一个输入路径(被减数)
- `two`: 第二个输入路径(减数)
- `op`: 操作类型(kDifference/kIntersect/kUnion/kXOR/kReverseDifference)

**返回值**:
- 成功时返回包含结果路径的 `std::optional`
- 失败时返回空的 `std::optional`

**特殊处理**:
- 矩形交集快速路径优化
- 空路径的简化处理
- 反转填充类型的自动转换

### `OpDebug(...)` (内部调试版本)

带调试支持的路径操作实现,提供详细的内部状态跟踪和验证。

**调试功能**:
- 路径转储(dump)和验证
- 循环计数统计
- 断言跳过选项

## 内部实现细节

### 1. 算法流程

完整的路径操作流程包括以下阶段:

#### **预处理阶段**
```cpp
// 1. 处理反转填充和操作映射
op = gOpInverse[op][one.isInverseFillType()][two.isInverseFillType()];
bool inverseFill = gOutInverse[op][one.isInverseFillType()][two.isInverseFillType()];
```

#### **快速路径优化**
```cpp
// 矩形交集优化
if (kIntersect_SkPathOp == op && one.isRect(&rect1) && two.isRect(&rect2)) {
    return SkPath::Rect(rect1.intersect(rect2));
}

// 空路径处理
if (one.isEmpty() || two.isEmpty()) {
    // 根据操作类型返回合适的结果
}
```

#### **主要计算阶段**
1. **边构建**: 将路径转换为段和轮廓
   ```cpp
   SkOpEdgeBuilder builder(*minuend, contourList, &globalState);
   builder.addOperand(*subtrahend);
   ```

2. **交点计算**: 找出所有段的交点
   ```cpp
   while (AddIntersectTs(current, next, &coincidence)) {
       // 迭代所有轮廓对
   }
   ```

3. **重合处理**: 处理重叠和退化情况
   ```cpp
   HandleCoincidence(contourList, &coincidence);
   ```

4. **轮廓构建**: 追踪活动边并构建输出路径
   ```cpp
   bridgeOp(contourList, op, xorMask, xorOpMask, &wrapper);
   ```

### 2. 核心辅助函数

#### **findChaseOp()**
从追踪栈中查找下一个活动边段。

**算法逻辑**:
- 从栈中弹出跨度点
- 查找活动角度和下一个段
- 计算缠绕数并更新标记
- 处理排序失败的情况

**关键代码**:
```cpp
SkOpAngle* last = segment->activeAngle(*startPtr, startPtr, endPtr, &done);
const SkOpAngle* angle = AngleWinding(*startPtr, *endPtr, &winding, &sortable);
```

#### **bridgeOp()**
构建最终路径的主循环。

**处理流程**:
1. 找到可排序的顶部跨度
2. 判断当前段是否活动(满足缠绕规则)
3. 追踪轮廓边界直到闭合
4. 处理未排序的退化情况
5. 标记已处理的段并继续

**缠绕规则检查**:
```cpp
if (current->activeOp(start, end, xorMask, xorOpMask, op)) {
    // 该段参与输出
}
```

### 3. 缠绕数算法

缠绕数(winding number)是布尔运算的核心概念:

- **差集**: 只保留被减数内部且减数外部的区域
- **交集**: 只保留两者都内部的区域
- **并集**: 保留任一路径内部的区域
- **异或**: 保留恰好一个路径内部的区域

通过 `setUpWindings()` 和 `updateWindingReverse()` 等函数维护缠绕数信息。

### 4. 错误处理

该模块使用多种策略处理几何退化和数值误差:

- 返回 `std::optional` 表示失败情况
- `unparseable()` 检测无法解析的输入
- `SK_MinS32` 标记计算失败的缠绕数
- 调试模式下的断言和状态验证

## 依赖关系

### 直接依赖

**核心依赖**:
- `include/core/SkPath.h`: 路径数据结构
- `include/pathops/SkPathOps.h`: 公共接口定义
- `src/pathops/SkOpContour.h`: 轮廓管理
- `src/pathops/SkOpSegment.h`: 段表示
- `src/pathops/SkAddIntersections.h`: 交点计算
- `src/pathops/SkPathOpsCommon.h`: 共用工具函数
- `src/base/SkArenaAlloc.h`: 内存分配器

**数学工具**:
- `include/private/base/SkMath.h`: 数学常量和函数
- `include/private/base/SkTDArray.h`: 动态数组

### 被依赖情况

该模块通过公共 API 被以下组件使用:
- `SkOpBuilder`: 多路径批量操作
- 上层图形库(Canvas 2D, SVG)
- 矢量图形编辑工具
- 字体轮廓处理模块

## 设计模式与设计决策

### 1. 策略模式

通过查找表 `gOpInverse` 和 `gOutInverse` 实现操作类型的动态映射,避免冗长的条件分支。

### 2. 访问者模式

追踪算法通过访问段、跨度、角度等节点,使用统一的接口进行遍历和处理。

### 3. 状态机模式

`bridgeOp()` 和 `findChaseOp()` 实现了一个状态机,在不同的段和轮廓之间转换,直到构建完整路径。

### 4. 内存管理策略

使用栈式内存分配器 `SkSTArenaAlloc<4096>` 实现高效的临时对象分配:
- 避免频繁的堆分配
- 自动批量释放
- 缓存友好的内存布局

### 5. 反向差集的等价转换

将 `kReverseDifference_SkPathOp` 转换为交换操作数的 `kDifference_SkPathOp`:
```cpp
if (op == kReverseDifference_SkPathOp) {
    swap(minuend, subtrahend);
    op = kDifference_SkPathOp;
}
```
简化了后续逻辑的实现。

### 6. 快速路径优化

针对常见场景(矩形交集、空路径)提供专门的快速实现,避免完整的计算管道。

## 性能考量

### 1. 时间复杂度

- **最坏情况**: O(n²),当两路径有大量交点时
- **典型情况**: O(n log n),主要耗时在排序和交点查找
- **最佳情况**: O(1),快速路径优化命中

其中 n 为路径段的总数。

### 2. 空间复杂度

- **主要开销**: O(n + k),n 为段数,k 为交点数
- **栈式分配**: 使用 4KB 栈内存块,减少堆分配
- **追踪栈**: `SkTDArray<SkOpSpanBase*>` 动态增长

### 3. 优化技术

**矩形快速检测**:
```cpp
if (kIntersect_SkPathOp == op && one.isRect(&rect1) && two.isRect(&rect2)) {
    return SkPath::Rect(rect1.intersect(rect2));
}
```
避免 95% 以上的计算成本。

**XOR 掩码预计算**:
```cpp
const int xorMask = builder.xorMask();
const int xorOpMask = builder.xorMask();
```
快速判断奇偶规则,减少条件分支。

**内联和尾递归**:
主循环使用 `do-while` 和 `continue` 优化控制流。

### 4. 数值稳定性

- 使用参数化坐标(t 值)而非笛卡尔坐标进行交点判断
- 容差机制处理浮点误差
- 退化情况的鲁棒处理(共线段、零长度段)

### 5. 调试模式开销

调试版本包含大量验证代码:
- `DEBUG_VALIDATE`: 状态一致性检查
- `DEBUG_DUMP_SEGMENTS`: 段信息转储
- `DEBUG_T_SECT_LOOP_COUNT`: 循环统计

生产版本通过宏完全移除这些代码,零运行时开销。

## 相关文件

### 核心依赖文件

- `src/pathops/SkOpSegment.cpp`: 段的操作实现
- `src/pathops/SkOpContour.cpp`: 轮廓管理
- `src/pathops/SkOpAngle.cpp`: 角度排序算法
- `src/pathops/SkOpCoincidence.cpp`: 重合边处理
- `src/pathops/SkPathOpsCommon.cpp`: 公共辅助函数
- `src/pathops/SkPathWriter.cpp`: 路径构建器
- `src/pathops/SkAddIntersections.cpp`: 交点检测
- `src/pathops/SkOpEdgeBuilder.cpp`: 边构建

### 公共接口

- `include/pathops/SkPathOps.h`: 公共 API 声明
- `include/core/SkPath.h`: 路径数据结构

### 测试文件

- `tests/PathOpsOpTest.cpp`: 单元测试
- `tests/PathOpsExtendedTest.cpp`: 扩展测试套件
- `tests/PathOpsDebug.cpp`: 调试工具

### 相关高级功能

- `src/pathops/SkOpBuilder.cpp`: 批量路径操作
- `src/pathops/SkPathOpsSimplify.cpp`: 路径简化
- `src/pathops/SkPathOpsTightBounds.cpp`: 紧密边界计算

该文件是 Skia 路径操作系统的核心枢纽,协调各个子模块完成复杂的几何布尔运算,是实现高质量矢量图形处理的基础设施。
