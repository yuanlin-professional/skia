# SkRasterPipelineVizualizer

> 源文件: src/core/SkRasterPipelineVizualizer.h

## 概述

`SkRasterPipelineVizualizer` 是 Skia 光栅化管道的调试可视化工具命名空间，提供了将管道中间阶段的数据可视化到位图面板的能力。它允许开发者在管道的每个阶段之后插入调试操作，将特定通道（lane）的数据渲染到独立的位图中，从而直观地观察颜色、坐标等数据在管道中的流动和变换过程。这是一个强大的调试工具，专门用于理解和调试复杂的 Raster Pipeline 执行流程。

## 架构位置

`SkRasterPipelineVizualizer` 位于 Skia 核心渲染引擎的调试层：

- **上层使用**: 被测试代码、性能分析工具和内部调试工具使用
- **同层协作**: 与 `SkRasterPipelineBlitter` 紧密集成
- **下层依赖**: 依赖 `SkRasterPipeline` 的调试操作（debug_x, debug_y, debug_r 等）

该工具在正常生产代码中不会使用，主要用于开发和调试阶段。

## 主要类与结构体

### 核心结构体

| 结构体名 | 用途 |
|---------|------|
| `DebugStage` | 表示管道中一个阶段的调试配置 |
| `DebugStageBuilder` | 用于构建 `DebugStage` 向量的辅助类 |

### DebugStage 关键成员

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `panels` | `std::vector<SkBitmap>` | 用于存储可视化输出的位图面板 |
| `ops` | `std::vector<SkRasterPipelineOp>` | 与 panels 对应的调试操作（必须是 debug_* 开头的操作） |

### DebugStageBuilder 特性

| 特性 | 说明 |
|------|------|
| 不可拷贝 | 禁用拷贝构造和拷贝赋值 |
| 不可移动 | 禁用移动构造和移动赋值 |
| 可变参数模板 | 支持一次添加多个面板-操作对 |

## 公共 API 函数

### CreateBlitter 函数

```cpp
SkBlitter* CreateBlitter(
    const SkPixmap& output,                    // 最终输出目标
    const std::vector<DebugStage>& stages,     // 调试阶段配置
    const SkPaint&,                            // 绘制参数
    const SkMatrix& ctm,                       // 当前变换矩阵
    SkArenaAlloc*,                             // 内存分配器
    sk_sp<SkShader> clipShader,                // 裁剪着色器
    const SkSurfaceProps& props                // 表面属性
);
```

**功能**：创建一个带有中间阶段可视化能力的 Blitter。

**重要约束**：
- `stages` 的大小必须与实际管道阶段数量完全匹配，否则会中止程序
- 首次调用时会通过标准输出打印原始管道，帮助确定阶段数量
- 只能可视化来自着色器的阶段，无法可视化 Blitter 方法后期添加的混合阶段

### DebugStageBuilder 方法

```cpp
// 添加一个或多个面板-操作对
template <typename... Args>
DebugStageBuilder& add(const SkBitmap& panel, SkRasterPipelineOp op, Args... args);

// 添加一个空阶段（不进行任何可视化）
DebugStageBuilder& add();

// 构建最终的调试阶段向量
std::vector<DebugStage> build();
```

## 内部实现细节

### 可变参数模板递归

`DebugStageBuilder` 使用模板递归实现可变参数：

```cpp
// 递归终止条件
static void add_next(std::vector<SkBitmap>& v, std::vector<SkRasterPipelineOp>& ops) {}

// 递归展开
template <typename... Args>
static void add_next(std::vector<SkBitmap>& panels,
                     std::vector<SkRasterPipelineOp>& ops,
                     const SkBitmap& panel,
                     SkRasterPipelineOp op,
                     Args... args) {
    panels.emplace_back(panel);
    ops.emplace_back(op);
    add_next(panels, ops, args...);  // 递归处理剩余参数
}
```

### 支持的调试操作

从 `SkRasterPipelineOpList.h` 中可以看到以下调试操作：

| 操作名 | 可视化内容 |
|-------|-----------|
| `debug_x` | X 坐标通道 |
| `debug_y` | Y 坐标通道 |
| `debug_r` | 红色通道（浮点值） |
| `debug_g` | 绿色通道（浮点值） |
| `debug_b` | 蓝色通道（浮点值） |
| `debug_a` | Alpha 通道（浮点值） |
| `debug_r_255` | 红色通道（0-255 范围） |
| `debug_g_255` | 绿色通道（0-255 范围） |
| `debug_b_255` | 蓝色通道（0-255 范围） |
| `debug_a_255` | Alpha 通道（0-255 范围） |

### 管道注入机制

`CreateBlitter` 的实现（在 `SkRasterPipelineBlitter.cpp` 中）会：

1. 首次调用时打印原始管道结构（`shaderPipeline.dump()`）
2. 将原始管道分解为阶段列表
3. 在每个阶段后插入用户指定的调试操作
4. 创建一个修改后的 Blitter 用于绘制

```cpp
// 伪代码示例
for (size_t i = 0; i < stages.size(); i++) {
    newPipeline.append(originalStages[i]);        // 原始阶段
    for (size_t j = 0; j < debugStages[i].panels.size(); j++) {
        newPipeline.append(debugStages[i].ops[j], // 注入调试操作
                          &panelContexts[j]);
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkBitmap` | 存储可视化输出 |
| `SkBlitter` | 创建的可视化 Blitter 基于此类 |
| `SkRasterPipeline` | 管道的基础实现 |
| `SkRasterPipelineOp` | 调试操作枚举 |
| `SkArenaAlloc` | 内存分配 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| 测试代码 | 验证管道各阶段的正确性 |
| 调试工具 | 可视化管道执行流程 |
| 性能分析 | 检查数据流动模式 |

## 设计模式与设计决策

### 1. Builder 模式

`DebugStageBuilder` 实现了链式调用的 Builder 模式：

```cpp
stageBuilder.add(panel1, op1)
            .add(panel2, op2, panel3, op3)
            .add()  // 空阶段
            .add(panel4, op4);
auto stages = stageBuilder.build();
```

### 2. 命名空间隔离

使用命名空间而非类来组织功能，避免不必要的实例化：

```cpp
namespace SkRasterPipelineVisualizer {
    // 所有功能都是静态的或作为独立函数存在
}
```

### 3. 类型安全的调试操作

编译时强制要求使用正确的操作类型（`SkRasterPipelineOp` 枚举），防止运行时错误。

### 4. 严格的阶段匹配检查

使用 `SkASSERT_RELEASE` 确保生产构建中也能检测到阶段数量不匹配：

```cpp
SkASSERT_RELEASE(stages.size() == debugStages.size());
```

### 5. 首次运行辅助机制

使用 `SkOnce` 确保管道结构只打印一次，帮助用户确定正确的阶段数量。

## 性能考量

### 1. 仅调试使用

该工具设计为调试专用，不考虑性能优化，因为：
- 向管道注入额外的写入操作会显著降低性能
- 每个调试阶段都需要额外的内存写入

### 2. 内存开销

每个调试面板都是一个完整的 `SkBitmap`，需要考虑：
- 大尺寸图像 × 多个阶段 × 多个通道 = 巨大的内存占用
- 建议只调试小图像或感兴趣的区域

### 3. 避免生产代码使用

文档明确说明该功能仅用于开发阶段，不应在发布版本中启用。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkRasterPipelineBlitter.cpp` | 实现文件 | 包含 `CreateBlitter` 的实际实现 |
| `src/core/SkRasterPipeline.h` | 基础设施 | 管道的核心定义 |
| `src/core/SkRasterPipelineOpList.h` | 操作定义 | 所有管道操作的枚举 |
| `src/core/SkRasterPipelineOpContexts.h` | 上下文结构 | 调试操作使用的内存上下文 |
| `src/core/SkBlitter.h` | 基类 | Blitter 的基础接口 |
| `include/core/SkBitmap.h` | 数据结构 | 存储可视化结果 |

## 典型使用场景

### 场景 1: 可视化渐变着色器的各个阶段

```cpp
// 创建输出面板
SkBitmap output, xPanel, yPanel, colorPanel;
// ... 初始化位图 ...

// 配置调试阶段
SkRasterPipelineVisualizer::DebugStageBuilder builder;
builder.add(xPanel, SkRasterPipelineOp::debug_x,
            yPanel, SkRasterPipelineOp::debug_y)
       .add(colorPanel, SkRasterPipelineOp::debug_r_255,
                        SkRasterPipelineOp::debug_g_255,
                        SkRasterPipelineOp::debug_b_255);
auto stages = builder.build();

// 创建可视化 Blitter
SkBlitter* blitter = SkRasterPipelineVisualizer::CreateBlitter(
    output.pixmap(), stages, paint, matrix, alloc, clipShader, props);

// 使用 blitter 绘制
blitter->blitRect(0, 0, width, height);

// xPanel, yPanel, colorPanel 现在包含可视化结果
```

### 场景 2: 跳过不感兴趣的阶段

```cpp
SkRasterPipelineVisualizer::DebugStageBuilder builder;
builder.add()  // 第一阶段：不可视化
       .add(panel1, SkRasterPipelineOp::debug_a)  // 第二阶段：只看 alpha
       .add()  // 第三阶段：不可视化
       .add(panel2, SkRasterPipelineOp::debug_r_255,
            panel3, SkRasterPipelineOp::debug_g_255);  // 第四阶段：红绿通道
```

### 场景 3: 调试复杂着色器

```cpp
// 首次运行，查看管道有多少阶段
auto stages = builder.add().build();  // 初始猜测
SkBlitter* blitter = SkRasterPipelineVisualizer::CreateBlitter(...);
// 输出会打印实际阶段数量

// 根据输出调整，例如发现有 5 个阶段
SkRasterPipelineVisualizer::DebugStageBuilder builder;
builder.add(...)  // 阶段 0
       .add(...)  // 阶段 1
       .add(...)  // 阶段 2
       .add(...)  // 阶段 3
       .add(...); // 阶段 4
auto stages = builder.build();
// 现在可以正确运行
```
