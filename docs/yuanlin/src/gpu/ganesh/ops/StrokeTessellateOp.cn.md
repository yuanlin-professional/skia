# StrokeTessellateOp

> 源文件
> - src/gpu/ganesh/ops/StrokeTessellateOp.h
> - src/gpu/ganesh/ops/StrokeTessellateOp.cpp

## 概述

`StrokeTessellateOp` 是 Skia Ganesh GPU 后端中专门用于渲染路径笔触（stroke）的操作类，通过将笔触曲线线性化为排序的"参数化"和"径向"边来实现高性能渲染。该操作使用 GPU 硬件曲面细分技术，配合 `GrStrokeTessellationShader` 着色器，支持各种笔触样式（圆形端点、方形端点、连接样式等）和宽度，适用于 MSAA 抗锯齿场景。对于包含透明度的笔触，该操作采用两阶段模板-填充方法来正确处理重叠区域。

## 架构位置

`StrokeTessellateOp` 位于 Skia GPU 渲染管线的以下位置：

- **模块层级**：`src/gpu/ganesh/ops/` - Ganesh GPU 操作层
- **继承关系**：继承自 `GrDrawOp`
- **命名空间**：`skgpu::ganesh`
- **协作组件**：
  - 细分器：`StrokeTessellator` - 生成笔触几何数据
  - 着色器：`GrStrokeTessellationShader` - GPU 着色器程序
  - 调用者：`TessellationPathRenderer` - 路径渲染器

## 主要类与结构体

### StrokeTessellateOp

```cpp
class StrokeTessellateOp final : public GrDrawOp
```

**核心数据成员**：
- `GrAAType fAAType` - 抗锯齿类型（通常为 kMSAA）
- `SkMatrix fViewMatrix` - 视图变换矩阵
- `PatchAttribs fPatchAttribs` - 补丁属性标志（动态状态）
- `PathStrokeList fPathStrokeList` - 路径笔触链表头节点
- `PathStrokeList** fPathStrokeTail` - 链表尾指针
- `int fTotalCombinedVerbCnt` - 合并后的总动词数量
- `GrProcessorSet fProcessors` - 片段处理器集合
- `bool fNeedsStencil` - 是否需要模板缓冲（透明笔触）

**渲染对象**：
- `StrokeTessellator* fTessellator` - 笔触细分器
- `GrStrokeTessellationShader* fTessellationShader` - 细分着色器
- `const GrProgramInfo* fStencilProgram` - 模板阶段程序
- `const GrProgramInfo* fFillProgram` - 填充阶段程序

### PatchAttribs（补丁属性标志）

通过 `StrokeTessellator::PatchAttribs` 定义的位标志枚举：
- `kNone` - 无动态属性
- `kColor` - 动态颜色
- `kStrokeParams` - 动态笔触参数（宽度、miter、join等）
- `kExplicitCurveType` - 显式曲线类型（硬件不支持无穷大推断时）
- `kWideColorIfEnabled` - 宽颜色格式（颜色无法用字节表示时）

### PathStrokeList（路径笔触链表）

```cpp
using PathStrokeList = StrokeTessellator::PathStrokeList;
```

链表节点结构，存储单个路径的笔触信息：
- `SkPath fPath` - 路径几何
- `SkStrokeRec fStroke` - 笔触记录（宽度、样式等）
- `SkPMColor4f fColor` - 预乘颜色
- `PathStrokeList* fNext` - 链表下一节点

## 公共 API 函数

### 构造函数

```cpp
StrokeTessellateOp(GrAAType aaType,
                   const SkMatrix& viewMatrix,
                   const SkPath& path,
                   const SkStrokeRec& stroke,
                   GrPaint&& paint)
```

**功能**：创建笔触细分操作

**边界计算逻辑**：
1. 获取路径边界框
2. **非发丝笔触**：在局部空间膨胀（变换前）
   - 膨胀半径 = `stroke.getInflationRadius()`
3. 应用视图矩阵变换到设备空间
4. **发丝笔触**：在设备空间膨胀（变换后）
   - 膨胀半径通过 `SkStrokeRec::GetInflationRadius()` 计算，考虑连接、端点样式

**属性初始化**：
- 检测颜色是否需要宽格式（`fitsInBytes()`）
- 初始化路径笔触链表头节点
- 记录路径动词数量

## 内部实现细节

### 操作合并逻辑

**onCombineIfPossible 决策树**：

**必须满足的合并条件**：
1. 两个操作都已完成 `finalize()`
2. 都不需要模板缓冲（`!fNeedsStencil`）
3. 视图矩阵相同
4. AA 类型相同
5. 片段处理器集合相同
6. 发丝样式一致性（都是或都不是发丝）

**动态状态协商**：
- **笔触参数不同**：尝试启用 `PatchAttribs::kStrokeParams`
  - 发丝笔触不支持动态参数，直接拒绝合并
- **颜色不同**：尝试启用 `PatchAttribs::kColor`
- **成本评估**：调用 `shouldUseDynamicStates()` 判断是否值得启用动态状态
  - 如果已启用所有需要的状态：合并
  - 如果动词数量 ≤ 50：合并（`kMaxVerbsToEnableDynamicState`）
  - 否则：拒绝合并（避免大批次数据膨胀）

**链表拼接**：
- 将被合并操作的 `PathStrokeList` 复制到 Arena 分配器
- 更新尾指针 `fPathStrokeTail`
- 累加总动词数量

### 模板-填充两阶段渲染

**透明笔触处理**（`fNeedsStencil == true`）：

**模板阶段**（`kMarkStencil`）：
```cpp
GrUserStencilSettings::StaticInit<
    0x0001,                          // ref = 1
    GrUserStencilTest::kLessIfInClip, // 在裁剪区内测试
    0x0000,                          // 比较掩码（总是失败）
    GrUserStencilOp::kZero,          // 测试失败：清零
    GrUserStencilOp::kReplace,       // 测试通过：替换为1
    0xffff                           // 写掩码
>()
```
**功能**：标记所有笔触覆盖区域为模板值 1

**填充阶段**（`kTestAndResetStencil`）：
```cpp
GrUserStencilSettings::StaticInit<
    0x0000,                          // ref = 0
    GrUserStencilTest::kLessIfInClip, // 即"不等于零"
    0x0001,                          // 比较掩码
    GrUserStencilOp::kZero,          // 重置为0
    GrUserStencilOp::kReplace,
    0xffff
>()
```
**功能**：仅在模板值非零处渲染，并重置模板值，防止重复绘制重叠区域

**不透明笔触**（`fNeedsStencil == false`）：
- 仅执行填充阶段
- 使用 `GrUserStencilSettings::kUnused`
- 单通道直接渲染

### 曲线类型推断

**Infinity-based 推断**：
- 现代 GPU 支持通过无穷大浮点值推断曲线类型
- 二次曲线：w2 = infinity
- 立方曲线：w3 = infinity
- 直线：w1 = infinity

**显式类型属性**（`fExplicitCurveType`）：
- 当 `!caps.shaderCaps()->fInfinitySupport` 时启用
- 在 `finalize()` 阶段检测并设置
- 通过额外顶点属性传递曲线类型标识

### 准备流程

**prePrepareTessellator 职责**：
1. 创建渲染管线（`GrTessellationShader::MakePipeline`）
2. 分配细分器（`StrokeTessellator`）
3. 创建细分着色器（`GrStrokeTessellationShader`）
4. 根据 `fNeedsStencil` 创建程序：
   - 透明笔触：创建 `fStencilProgram` 和 `fFillProgram`
   - 不透明笔触：仅创建 `fFillProgram`

**两种准备路径**：
1. **onPrePrepare**（DDL 记录时）：
   - 使用记录时 Arena 分配器
   - 调用 `recordProgramInfo()` 注册程序到 DDL
2. **onPrepare**（flush 时）：
   - 检查 `fTessellator` 是否已存在（预准备）
   - 未预准备则现场调用 `prePrepareTessellator`
   - 调用 `fTessellator->prepare()` 生成几何数据

### 执行流程

**onExecute 渲染顺序**：
1. **模板通道**（如果 `fStencilProgram` 存在）：
   - 绑定模板程序和裁剪
   - 绑定纹理（无纹理，仅模板写入）
   - 调用 `fTessellator->draw()`
2. **填充通道**（`fFillProgram` 总是存在）：
   - 绑定填充程序和裁剪
   - 绑定纹理和片段处理器
   - 调用 `fTessellator->draw()` 渲染最终颜色

## 依赖关系

**直接依赖**：
- `GrDrawOp` - 基类
- `StrokeTessellator` - 笔触几何细分器
- `GrStrokeTessellationShader` - GPU 着色器
- `GrProcessorSet` - 片段处理器集合
- `GrProgramInfo` - 程序配置信息

**渲染管线依赖**：
- `GrPaint` - 绘制参数（构造时移动语义获取）
- `GrAppliedClip` - 应用的裁剪
- `GrDstProxyView` - 目标代理视图
- `GrOpFlushState` - 操作刷新状态

**核心库依赖**：
- `SkPath` - 路径几何表示
- `SkStrokeRec` - 笔触记录
- `SkMatrix` - 变换矩阵

## 设计模式与设计决策

### 链表聚合模式

使用链表（`PathStrokeList`）存储多个待渲染路径，支持高效的批量合并：
- 头节点内联在操作对象中，避免额外分配
- 尾指针加速链表追加（O(1) 复杂度）
- 节点通过 `SkArenaAlloc` 分配，自动生命周期管理

### 懒惰初始化模式

细分器和程序信息在准备阶段才创建，而非构造阶段：
- 支持 DDL 预准备和即时模式两种路径
- 避免构造时的重量级操作
- 允许合并后再统一创建资源

### 策略模式（透明度处理）

根据 `fNeedsStencil` 标志动态选择渲染策略：
- 透明笔触：两阶段模板-填充
- 不透明笔触：单阶段直接填充

该标志在 `finalize()` 中由处理器分析决定（`unaffectedByDstValue()`）。

### 位标志组合（Patch Attributes）

使用位标志枚举 `PatchAttribs` 表示顶点属性配置：
- 紧凑表示多个布尔标志
- 支持按位或合并操作
- 易于检查特定标志子集

### 启发式成本模型

`shouldUseDynamicStates()` 实现简单但有效的启发式：
- 已启用状态无额外成本
- 小批次（≤50 动词）启用成本可接受
- 大批次避免数据膨胀

### 模板配方复用

`kMarkStencil` 和 `kTestAndResetStencil` 设计为尽可能匹配：
- 仅 ref 和 compare mask 不同
- 支持动态模板状态的 GPU 可复用管线
- 注释提到未来可能优化纹理屏障位置

## 性能考量

### 批处理优化

**动态状态支持**：
- 不同颜色的笔触可合并，通过顶点属性传递颜色
- 不同参数的笔触可合并，通过顶点属性传递宽度等
- 减少绘制调用次数和状态切换

**动态状态成本控制**：
- 启用动态颜色：每补丁额外 16 字节（SkPMColor4f）
- 启用动态笔触参数：额外数十字节（宽度、miter、join等）
- 通过 50 动词阈值平衡批处理收益与数据膨胀

### GPU 曲面细分利用

- 利用硬件曲面细分管线加速曲线线性化
- 避免 CPU 预处理开销
- 支持自适应细分密度（基于曲率和缩放）

### 模板缓冲重用

- 透明笔触的模板-填充复用同一几何数据
- 第一次绘制写模板，第二次绘制读模板并重置
- 避免重复计算几何数据

### 边界精确计算

- 根据笔触样式精确计算膨胀半径
- 发丝和非发丝在不同空间膨胀
- 考虑连接样式（miter、bevel、round）和端点样式
- 避免过度保守的边界导致不必要的渲染

### 合并拒绝快速路径

- 早期检查视图矩阵、AA 类型等不可变条件
- 在昂贵的动态状态计算前拒绝不兼容操作
- 减少合并失败的开销

## 相关文件

**细分核心**：
- `src/gpu/ganesh/tessellate/StrokeTessellator.h/cpp` - 笔触细分器实现
- `src/gpu/ganesh/tessellate/GrStrokeTessellationShader.h/cpp` - 笔触细分着色器

**基础设施**：
- `src/gpu/ganesh/ops/GrDrawOp.h` - 绘制操作基类
- `src/gpu/ganesh/tessellate/GrTessellationShader.h` - 细分着色器基类
- `src/gpu/ganesh/GrProcessorSet.h` - 处理器集合管理

**调用者**：
- `src/gpu/ganesh/ops/TessellationPathRenderer.h/cpp` - 细分路径渲染器

**核心类型**：
- `include/core/SkPath.h` - 路径几何
- `include/core/SkStrokeRec.h` - 笔触记录
- `include/core/SkMatrix.h` - 变换矩阵
