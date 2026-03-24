# AtlasRenderTask

> 源文件
> - src/gpu/ganesh/ops/AtlasRenderTask.h
> - src/gpu/ganesh/ops/AtlasRenderTask.cpp

## 概述

`AtlasRenderTask` 是 Skia Ganesh GPU 后端的专用渲染任务，负责将多个路径绘制到共享的图集纹理中。该任务被添加到渲染任务有向无环图（DAG）后保持打开状态，允许后续操作持续添加路径，并在图集布局完成后才关闭并生成实际的绘制操作。

该类的核心价值在于通过动态图集技术批量渲染路径，显著减少纹理切换和绘制调用次数。它使用模板缓冲技术和 MSAA（多重采样抗锯齿）实现高质量的路径渲染，支持非零缠绕和奇偶填充规则。

## 架构位置

`AtlasRenderTask` 位于 Skia GPU 渲染管线的任务调度层：

```
Skia GPU 渲染架构:
├── GrRecordingContext
├── GrDrawingManager
│   ├── 渲染任务 DAG
│   │   ├── OpsTask (常规绘制任务)
│   │   ├── AtlasRenderTask (本类) ← 专用于图集渲染
│   │   ├── CopyRenderTask
│   │   └── TransferFromRenderTask
│   └── 任务调度与执行
├── GrDynamicAtlas ← 图集资源管理
└── GPU 操作层
    ├── PathStencilCoverOp
    └── FillRectOp
```

`AtlasRenderTask` 继承自 `OpsTask`，但具有特殊的生命周期：在关闭前保持打开状态以累积路径，关闭时才生成内部绘制操作。

## 主要类与结构体

### AtlasRenderTask 类

继承自 `OpsTask`，管理图集的路径渲染任务。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDynamicAtlas` | `std::unique_ptr<GrDynamicAtlas>` | 动态图集管理器，负责纹理分配和空间布局 |
| `fPathDrawAllocator` | `PathDrawAllocator` | 路径绘制数据的块分配器，使用斐波那契增长策略 |
| `fWindingPathList` | `AtlasPathList` | 非零缠绕规则的路径列表 |
| `fEvenOddPathList` | `AtlasPathList` | 奇偶填充规则的路径列表 |

### AtlasPathList 内部类

管理具有相同填充规则的路径集合。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPathDrawList` | `PathDrawList*` | 路径绘制链表的头指针 |
| `fTotalCombinedPathVerbCnt` | `int` | 所有路径的总动词数量（用于资源估算） |
| `fPathCount` | `int` | 路径数量 |

## 公共 API 函数

### 构造与访问

```cpp
AtlasRenderTask(GrRecordingContext*, sk_sp<GrArenas>,
                std::unique_ptr<GrDynamicAtlas>)
```
构造函数，创建与给定动态图集关联的渲染任务。

```cpp
const GrTextureProxy* atlasProxy() const
```
获取图集的纹理代理对象。

```cpp
GrSurfaceProxyView readView(const GrCaps& caps) const
```
获取用于读取图集内容的表面代理视图。

### 路径管理

```cpp
bool addPath(const SkMatrix&, const SkPath&, SkIPoint pathDevTopLeft,
             int widthInAtlas, int heightInAtlas, bool transposedInAtlas,
             SkIPoint16* locationInAtlas)
```
向图集添加路径进行渲染。参数说明：
- `SkMatrix`：路径的视图矩阵变换
- `SkPath`：待渲染的路径对象
- `pathDevTopLeft`：路径在设备空间的左上角位置
- `widthInAtlas/heightInAtlas`：在图集中占用的尺寸
- `transposedInAtlas`：是否在图集中转置（用于空间优化）
- `locationInAtlas`：输出参数，返回在图集中的位置

返回值：成功返回 `true`，空间不足或容量限制返回 `false`。

### 资源实例化

```cpp
bool instantiate(GrOnFlushResourceProvider* onFlushRP,
                 sk_sp<GrTexture> backingTexture = nullptr)
```
在刷新时实例化图集纹理。可以提供已有纹理作为后备存储，或由系统分配新纹理。必须在任务关闭后调用。

## 内部实现细节

### 路径到图集的坐标变换

`addPath` 方法计算将路径从设备空间映射到图集空间的变换矩阵：

1. **基础变换**：从视图矩阵 `viewMatrix` 开始
2. **转置处理**（如果 `transposedInAtlas` 为 `true`）：
   - 交换矩阵的 X 和 Y 缩放/倾斜分量（索引 0, 3 和 1, 4）
   - 重新计算平移分量以适应转置后的坐标
3. **平移到图集位置**：
   - 非转置：`postTranslate(locationInAtlas - pathDevTopLeft)`
   - 转置：特殊的平移计算处理轴交换

### 双填充规则路径列表

路径根据填充规则分为两个独立列表：
- **Winding（非零缠绕）**：`fWindingPathList`
- **EvenOdd（奇偶）**：`fEvenOddPathList`

这种分离允许使用不同的模板配置高效处理不同填充规则，避免在单个 Op 中切换状态。

### 反向填充路径的处理

对于反向填充路径（`isInverseFillType()`）：
1. 添加到图集时切换填充类型（`toggleInverseFillType()`）
2. 图集内永远不存储反向路径
3. 反向效果在后续使用图集时通过遮罩反转实现

这种设计简化了图集渲染逻辑，因为图集本身只需处理正向填充。

### 延迟操作生成（onMakeClosed）

任务关闭时执行以下步骤：

1. **设置图集尺寸**：根据 `fDynamicAtlas->drawBounds()` 设置目标尺寸
2. **启用模板缓冲**：调用 `setNeedsStencil()`
3. **清除图集**：
   - 如果硬件要求通过绘制清除：使用透明矩形 + 模板重置
   - 否则：使用 `GrLoadOp::kClear` 硬件清除
4. **生成模板操作**：
   - 为 `fWindingPathList` 和 `fEvenOddPathList` 各创建 `PathStencilCoverOp`
   - 使用 `FillPathFlags::kStencilOnly` 只更新模板不写颜色
5. **覆盖操作**：
   - 绘制全屏白色矩形，根据模板值写入最终颜色
   - 如果硬件会丢弃模板：使用 `kTestStencil`（只测试）
   - 否则：使用 `kTestAndResetStencil`（测试后重置为 0）

### MSAA 解析

由于图集任务的特殊生命周期，绘制管理器无法自动检测 MSAA 解析需求。`onExecute` 方法在执行完所有操作后手动触发 MSAA 解析：

```cpp
flushState->gpu()->resolveRenderTarget(target, nativeRect)
```

只有当目标需要手动解析（`requiresManualMSAAResolve()`）时才执行。

### 块分配器策略

`fPathDrawAllocator` 使用以下配置：
- **内联条目**：16 个路径绘制
- **块大小**：64 字节
- **增长策略**：斐波那契序列（1, 1, 2, 3, 5, 8...）

这种策略在小图集场景避免堆分配，在大图集场景平滑增长内存。

### 动词计数溢出保护

`AtlasPathList::canAdd` 检查是否会导致总动词数溢出：
```cpp
static constexpr int kMaxVerbLimit = std::numeric_limits<int>::max() >> 4;
return kMaxVerbLimit - fTotalCombinedPathVerbCnt >= path.countVerbs();
```

使用 `>> 4` 预留 16 倍安全边际，避免后续分配意外溢出。

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `OpsTask` | 继承 | 渲染任务基类，提供操作管理和执行框架 |
| `GrDynamicAtlas` | 核心依赖 | 动态图集管理，处理纹理分配和矩形打包 |
| `PathTessellator` | 强依赖 | 路径镶嵌器，提供 `PathDrawList` 数据结构 |
| `PathStencilCoverOp` | 强依赖 | 模板-覆盖路径渲染操作 |
| `FillRectOp` | 强依赖 | 矩形填充操作，用于清除和覆盖 |
| `GrOnFlushResourceProvider` | 依赖 | 刷新时资源提供者，用于纹理实例化 |
| `SkTBlockList` | 依赖 | 块链表容器，高效管理路径绘制链表 |

### 被依赖的模块

| 模块 | 依赖类型 | 说明 |
|------|---------|------|
| `AtlasPathRenderer` | 使用 | 基于图集的路径渲染器创建和使用此任务 |
| `AtlasTextOp` | 使用 | 文本渲染操作使用图集任务渲染字形 |
| `GrDrawingManager` | 管理 | 将此任务添加到渲染 DAG 并调度执行 |
| `DrawAtlasPathOp` | 使用 | 图集路径绘制操作使用此任务生成的图集 |

## 设计模式与设计决策

### 1. 延迟操作生成模式

任务在关闭前保持打开状态，允许持续添加路径。这种设计：
- **优点**：最大化批处理机会，优化图集空间利用
- **实现**：重写 `onMakeClosed` 在关闭时生成所有内部操作
- **权衡**：增加了任务生命周期管理的复杂性

### 2. 模板-覆盖两遍渲染

使用经典的模板-覆盖技术渲染路径：
- **第一遍**：使用 `PathStencilCoverOp` 只写模板不写颜色
- **第二遍**：根据模板值绘制全屏矩形，写入最终颜色

这种方法支持复杂路径和填充规则，且在 GPU 上高效执行。

### 3. 按填充规则分组

将路径按填充规则分为两个独立列表的设计决策：
- **优势**：每个列表可以使用优化的模板配置
- **实现**：通过 `GrFillRuleForSkPath` 判断路径填充规则
- **效果**：避免在单个绘制操作中频繁切换模板设置

### 4. 转置支持

支持在图集中转置路径的设计：
- **目的**：提高矩形打包算法的空间利用率
- **实现**：通过交换变换矩阵的分量实现 90 度旋转
- **应用**：瘦长路径可以转置后更好地填充图集空白

### 5. 反向填充路径的标准化

图集内部不存储反向路径，统一转换为正向路径：
- **简化**：图集渲染逻辑无需处理反向填充
- **延迟**：反向效果在使用图集时通过覆盖率反转实现
- **一致性**：图集内容总是以相同方式解释

### 6. 手动 MSAA 解析

由于特殊的任务生命周期，需要手动解析 MSAA：
- **原因**：绘制管理器的脏跟踪机制无法检测延迟关闭的任务
- **实现**：在 `onExecute` 结束时显式调用 GPU 解析操作
- **条件**：只在目标需要手动解析时执行

### 7. 硬件清除兼容性处理

根据硬件能力选择清除策略：
- **支持硬件清除**：使用 `GrLoadOp::kClear` 高效清除
- **需要绘制清除**：使用透明矩形 + 模板操作模拟清除
- **灵活性**：适配不同 GPU 的能力差异

## 性能考量

### 1. 图集批处理收益

通过将多个路径渲染到单个图集纹理：
- 减少纹理绑定次数
- 减少渲染目标切换
- 提高 GPU 利用率

特别适合渲染大量小路径（如字形、图标）的场景。

### 2. 块分配器效率

使用 `SkTBlockList` 和斐波那契增长策略：
- 小图集（<= 16 路径）：零堆分配
- 大图集：内存增长平滑，减少重新分配次数
- 局部性：链表节点在连续内存块中，缓存友好

### 3. 延迟实例化

图集纹理直到刷新时才实例化：
- 在录制阶段无需实际 GPU 资源
- 允许更灵活的资源管理和复用
- 减少纹理内存峰值占用

### 4. 模板优化

根据硬件能力优化模板使用：
- **丢弃模板值的硬件**：使用 `kTestStencil` 避免不必要的重置
- **保留模板值的硬件**：显式重置以复用模板缓冲区

### 5. MSAA 抗锯齿

使用 MSAA 而非其他抗锯齿方法：
- 硬件加速，性能优异
- 高质量边缘
- 与模板缓冲兼容良好

### 6. 动词计数预检

在添加路径前检查动词数量溢出：
- 避免开始昂贵的镶嵌操作后才失败
- 预留安全边际，减少后续操作意外溢出风险

### 7. 空间布局优化

支持转置路径改善空间利用：
- 提高图集填充率
- 减少浪费空间
- 允许更多路径共享同一图集

### 8. 单遍绘制操作

尽管使用两遍渲染（模板 + 覆盖），但所有路径在每一遍中合并为单个操作，最小化 draw call 开销。

### 9. 目标尺寸延迟设置

图集尺寸在 `onMakeClosed` 时才确定：
- 根据实际使用的空间设置尺寸
- 避免分配过大的纹理
- 优化内存和带宽使用

### 10. 条件解析

只在必要时执行 MSAA 解析：
- 检查 `requiresManualMSAAResolve()` 避免不必要操作
- 使用 `GrNativeRect` 只解析图集使用的区域

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/ops/OpsTask.h` | 基类 | 渲染任务基类，提供操作管理框架 |
| `src/gpu/ganesh/GrDynamicAtlas.h` | 核心组件 | 动态图集管理器 |
| `src/gpu/ganesh/tessellate/PathTessellator.h` | 依赖 | 路径镶嵌器和数据结构 |
| `src/gpu/ganesh/ops/PathStencilCoverOp.h` | 使用 | 模板-覆盖路径渲染操作 |
| `src/gpu/ganesh/ops/FillRectOp.h` | 使用 | 矩形填充操作 |
| `src/gpu/ganesh/ops/AtlasPathRenderer.h` | 使用者 | 基于图集的路径渲染器 |
| `src/gpu/ganesh/GrDrawingManager.h` | 管理者 | 渲染任务调度和 DAG 管理 |
| `src/base/SkTBlockList.h` | 依赖 | 块链表容器 |
| `src/gpu/ganesh/GrOnFlushResourceProvider.h` | 依赖 | 刷新时资源提供者 |
| `src/gpu/ganesh/GrUserStencilSettings.h` | 依赖 | 用户模板配置 |
