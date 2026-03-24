# SkPathOpsDebug - 路径操作调试基础设施

> 源文件：[src/pathops/SkPathOpsDebug.h](../../../../src/pathops/SkPathOpsDebug.h)、[src/pathops/SkPathOpsDebug.cpp](../../../../src/pathops/SkPathOpsDebug.cpp)

## 概述

`SkPathOpsDebug` 是 Skia 路径操作（PathOps）模块的调试基础设施，提供了全面的调试宏定义、诊断函数、数据转储功能和重合检测验证工具。该文件是 PathOps 开发和问题排查的核心支撑，包含了超过 30 个编译时调试开关、用于 Visual Studio 即时窗口的全局调试函数，以及用于跟踪和报告重合段处理问题（"glitch"）的完整框架。

## 架构位置

```
PathOps 模块
  ├── SkPathOpsDebug (调试基础设施) ← 被所有 PathOps 组件依赖
  │     ├── 调试宏开关 (DEBUG_COIN, DEBUG_ANGLE, ...)
  │     ├── GlitchLog (重合段问题记录)
  │     ├── CoinDict (重合段字典统计)
  │     └── Dump 函数集 (数据转储)
  ├── SkOpSegment, SkOpContour, SkOpAngle, ...
  └── SkIntersections
```

`SkPathOpsDebug` 横跨整个 PathOps 模块，几乎所有 PathOps 源文件都依赖该文件的宏定义和调试接口。它不参与运算逻辑，但在调试构建中深度嵌入各个组件。

## 主要类与结构体

### `SkPathOpsDebug`
调试工具类，主要包含静态方法和静态成员变量。

**关键静态成员：**
- `gContourID` / `gSegmentID`：全局 ID 计数器，用于在调试输出中标识轮廓和段。
- `gRunFail`：控制是否对已知失败测试检查成功。
- `gVeryVerbose`：启用详尽的检查测试。
- `gDumpOp` / `gVerifyOp`：控制操作转储和结果验证。
- `gActiveSpans`：缓存活跃跨度的字符串表示，用于增量输出。

### `SkPathOpsDebug::GlitchLog`
重合段问题日志，记录在重合段处理各阶段检测到的异常。

**结构：**
- `fGlitches`：`SkTDArray<SpanGlitch>` 数组，存储所有检测到的问题。
- `fGlobalState`：关联的全局状态指针。
- 提供多个 `record()` 重载方法，接受不同组合的跨度、点-t值、段等参数来记录不同类型的问题。

### `SpanGlitch`
单个问题的详细记录。

**字段：**
- `fBase` / `fSuspect`：相关的跨度基址和可疑跨度。
- `fSegment` / `fOppSegment`：相关的段和对手段。
- `fCoinSpan` / `fEndSpan` / `fOppSpan` / `fOppEndSpan`：重合段的起止点-t值引用。
- `fStartT` / `fEndT` / `fOppStartT` / `fOppEndT`：参数 t 值。
- `fPt`：相关的坐标点。
- `fType`：`GlitchType` 枚举值，标识问题类型。

### `SkPathOpsDebug::GlitchType` 枚举
定义了约 35 种重合段问题类型，包括：
- `kAddCorruptCoin_Glitch`：添加损坏的重合段。
- `kMissingCoin_Glitch`：缺失的重合段。
- `kCollapsedSpan_Glitch`：坍塌的跨度。
- `kMoveMultiple_Glitch`：多重移动问题。
- `kUnaligned_Glitch`：未对齐问题。

### `SkPathOpsDebug::CoinDict` / `CoinDictEntry`
重合段操作字典，用于统计哪些算法在哪些迭代中触发了变更。
- `CoinDictEntry` 记录迭代次数、行号、问题类型和函数名称。
- `CoinDict` 维护条目数组并支持合并和转储。

## 公共 API 函数

### 静态工具函数
- `OpStr(SkPathOp)`：将路径操作枚举转换为字符串（"diff"、"sect"、"union"、"xor"、"rdiff"）。
- `MathematicaIze(char*, size_t)`：将科学计数法的 `e` 转换为 Mathematica 语法 `*^`。
- `ValidWind(int)`：检查缠绕数是否在有效范围内。
- `WindingPrintf(int)`：打印缠绕数，无效值显示为 `?`。

### 显示与转储
- `ShowActiveSpans(SkOpContourHead*)`：显示所有活跃跨度，仅在内容变化时输出。
- `ShowOnePath(const SkPath&, const char*, bool)`：以可重建的代码形式输出单条路径。
- `ShowPath(const SkPath&, const SkPath&, SkPathOp, const char*)`：输出完整的路径操作测试用例。
- `CheckHealth(SkOpContourHead*)`：运行全面的健康检查，包括重合段验证、缺失重合检测等。

### 全局调试函数（Visual Studio 即时窗口兼容）
为每种核心类型提供基于 ID 查找的调试函数族：
- `AngleAngle/AngleContour/AnglePtT/AngleSegment/AngleSpan`
- `ContourAngle/ContourContour/ContourPtT/...`
- `CoincidenceAngle/CoincidenceContour/...`
- `PtTAngle/PtTContour/...`
- `SegmentAngle/SegmentContour/...`
- `SpanAngle/SpanContour/...`

### 数据转储函数
- `Dump/DumpAll/DumpAngles/DumpContours/...`：各种粒度的数据转储。
- `DumpQ/DumpT`：输出与 `path_sorter.htm` 和 `path_visualizer.htm` 兼容的数据。
- `DumpHex`：以十六进制格式转储路径。

## 内部实现细节

### 调试开关体系
头文件定义了两套调试开关值：
- **FORCE_RELEASE 模式**：所有开关设为 0，无调试输出。在 release 构建或多线程场景下使用。
- **调试模式**：大部分开关设为 1，启用全面的调试检查和输出。

共包含约 25 个开关，覆盖：活跃操作、活跃跨度、交点添加、T值添加、对齐、角度、装配、重合、立方曲线搜索、段转储、验证转储、流程、标记完成、路径构建、垂线、排序、T-区间等各个方面。

### 重合段问题检测框架
`CheckHealth()` 方法是核心入口，它执行以下检查：
1. 验证重合段有效性（`debugCheckValid`）。
2. 遍历所有轮廓检查健康状态（`debugCheckHealth`）。
3. 检测缺失的重合段（`debugMissingCoincidence`）。
4. 添加缺失的重合段（`debugAddMissing`）。
5. 扩展重合段（`debugExpand`、`debugAddExpanded`）。
6. 标记重合段（`debugMark`）。
检测结果以位掩码形式输出，每种问题类型占一个位。

### 重合段变更字典
`debugAddToCoinChangedDict()` 在每次重合段操作后运行与操作对应的调试版本，检查操作是否产生了变更。它维护两个全局字典：
- `gCoinSumChangedDict`：记录产生实际变更的操作。
- `gCoinSumVisitedDict`：记录所有访问过的操作。

### 调试版本的并行实现
cpp 文件中大量代码是生产代码的调试版本（如 `debugAddT`、`debugMissingCoincidence`、`debugMoveMultiples`、`debugMoveNearby` 等）。这些函数与生产版本保持同步（通过注释标注），但只记录问题而不修改数据结构。

### 段和跨度的调试验证
- `SkOpAngle::debugValidate()`：验证角度环中的缠绕数总和为零。
- `SkOpAngle::debugValidateNext()`：验证角度链表无环路问题。
- `SkOpSegment::debugShowActiveSpans()`：显示每个未完成跨度的曲线数据和缠绕值。

## 依赖关系

- **SkPathOps**：路径操作枚举和公共 API。
- **SkTDArray**：动态数组，用于 GlitchLog 和 CoinDict。
- **SkOpSegment / SkOpContour / SkOpAngle / SkOpSpan / SkOpPtT / SkOpCoincidence**：调试函数检查这些类的内部状态。
- **SkIntersections**：循环计数调试。
- **SkPath / SkPoint**：路径和点数据类型。
- **SkMutex**：`ShowPath` 使用互斥锁确保线程安全的输出。

## 设计模式与设计决策

### 编译时开关体系
使用 `#define` 而非运行时标志控制调试功能，确保 release 构建中完全没有调试代码的开销。大量使用 `SkDEBUGPARAMS`、`DEBUG_COIN_DECLARE_PARAMS` 等宏来条件性地添加或省略函数参数。

### 生产代码的调试镜像
调试版本的函数与生产代码保持同步，通过注释标注（"commented-out lines keep this in sync with ..."）。这种模式允许在不修改生产代码的情况下进行深入诊断，但维护成本较高。

### Visual Studio 即时窗口兼容
由于 Visual Studio 2017 的即时窗口不支持调用成员函数，所有调试查找函数都设计为全局自由函数。这些函数接受对象指针和 ID 参数，返回相关的对象。

### 阶段跟踪
`SkOpPhase` 枚举和 `debugSetPhase` 方法跟踪路径操作的当前处理阶段，使得调试输出能够关联到特定的算法步骤。

### 问题类型分类
`GlitchType` 枚举将所有已知的重合段处理问题分类为具体的命名类型，便于统计和定位特定类别的 bug。

## 性能考量

- **零 release 开销**：所有调试代码都被编译时开关隔离，release 构建中不产生任何运行时开销。
- **增量输出**：`ShowActiveSpans` 缓存上次输出的字符串，仅在内容变化时才实际输出。
- **互斥锁保护**：`ShowPath` 使用互斥锁保护输出，适用于多线程测试场景。
- **字典去重**：`CoinDict::add` 对重复的迭代+行号条目进行去重，避免字典无限增长。

## 相关文件

- `src/pathops/SkOpSegment.h`：段的调试方法声明。
- `src/pathops/SkOpContour.h`：轮廓的调试方法声明。
- `src/pathops/SkOpAngle.h`：角度的调试方法声明。
- `src/pathops/SkOpCoincidence.h`：重合段的调试方法声明。
- `src/pathops/SkOpSpan.h`：跨度的调试方法声明。
- `src/pathops/SkPathOpsTypes.h`：精度和比较函数。
- `include/pathops/SkPathOps.h`：公共 API 和枚举定义。
