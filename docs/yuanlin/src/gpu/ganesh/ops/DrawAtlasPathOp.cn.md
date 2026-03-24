# DrawAtlasPathOp

> 源文件
> - src/gpu/ganesh/ops/DrawAtlasPathOp.h

## 概述

`DrawAtlasPathOp` 是 Skia Ganesh GPU 后端的图集路径绘制操作，用于渲染已光栅化到图集纹理中的路径遮罩。该操作与 `AtlasPathRenderer` 和 `AtlasRenderTask` 配合使用，通过从图集纹理采样覆盖率值来实现高效的路径渲染。

该操作使用实例化渲染技术，可以在单个 draw call 中绘制多个使用相同图集的路径，显著提高渲染性能。支持反向填充、边界检查、颜色调制等特性。

## 架构位置

```
Skia GPU 渲染架构:
├── AtlasPathRenderer (创建路径遮罩)
│   └── AtlasRenderTask (渲染到图集)
├── GrDrawOp 操作层
│   └── DrawAtlasPathOp ← 本类（使用图集绘制）
├── AtlasInstancedHelper (实例化辅助)
└── 片段处理器
    └── GrModulateAtlasCoverageEffect (采样图集)
```

## 主要类与结构体

### DrawAtlasPathOp 类

继承自 `GrDrawOp`，实现图集路径绘制。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fHeadInstance` | `Instance*` | 实例链表头指针 |
| `fTailInstance` | `Instance**` | 实例链表尾指针 |
| `fAtlasHelper` | `AtlasInstancedHelper` | 图集实例化辅助工具 |
| `fUsesLocalCoords` | `bool` | 是否使用局部坐标 |
| `fInstanceCount` | `int` | 实例数量 |
| `fProgram` | `GrProgramInfo*` | GPU 程序信息 |
| `fInstanceBuffer` | `sk_sp<const GrBuffer>` | 实例数据缓冲区 |
| `fBaseInstance` | `int` | 基础实例索引 |
| `fVertexBufferIfNoIDSupport` | `sk_sp<const GrGpuBuffer>` | 不支持 VertexID 时的顶点缓冲区 |
| `fProcessors` | `GrProcessorSet` | 片段处理器集合 |

### Instance 结构体

存储单个路径实例的渲染参数：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFillBounds` | `SkIRect` | 填充边界矩形 |
| `fLocalToDeviceIfUsingLocalCoords` | `std::array<float, 6>` | 局部到设备的仿射变换（6 个分量） |
| `fColor` | `SkPMColor4f` | 预乘 alpha 颜色 |
| `fAtlasInstance` | `AtlasInstancedHelper::Instance` | 图集实例数据 |
| `fNext` | `Instance*` | 链表下一节点 |

## 公共 API 函数

### 构造函数

```cpp
DrawAtlasPathOp(SkArenaAlloc* arena, const SkIRect& fillBounds,
                const SkMatrix& localToDevice, GrPaint&& paint,
                SkIPoint16 locationInAtlas, const SkIRect& pathDevIBounds,
                bool transposedInAtlas, GrSurfaceProxyView atlasView,
                bool isInverseFill)
```
创建图集路径绘制操作。参数：
- `fillBounds`：填充区域（反向填充时为裁剪区域）
- `localToDevice`：变换矩阵
- `locationInAtlas`：路径在图集中的位置
- `pathDevIBounds`：路径的设备空间边界
- `transposedInAtlas`：路径是否在图集中转置
- `atlasView`：图集纹理视图
- `isInverseFill`：是否为反向填充

### GrDrawOp 接口

```cpp
const char* name() const override
```
返回操作名称 "DrawAtlasPathOp"。

```cpp
FixedFunctionFlags fixedFunctionFlags() const override
```
返回固定功能标志，图集路径不使用特殊固定功能。

```cpp
void visitProxies(const GrVisitProxyFunc& func) const override
```
访问图集代理和处理器代理。

```cpp
GrProcessorSet::Analysis finalize(const GrCaps&, const GrAppliedClip*,
                                  GrClampType) override
```
最终化处理器分析，确定是否使用局部坐标。

```cpp
CombineResult onCombineIfPossible(GrOp*, SkArenaAlloc*,
                                   const GrCaps&) override
```
尝试与其他图集路径操作合并。

## 内部实现细节

### 实例化渲染

使用 GPU 实例化技术：
1. **共享几何体**：所有实例共享四边形顶点
2. **实例属性**：每个实例独立的变换、颜色、图集位置
3. **单次绘制**：一个 draw call 渲染所有实例

### AtlasInstancedHelper 集成

利用 `AtlasInstancedHelper` 处理图集相关逻辑：
- **着色器注入**：注入图集采样代码
- **坐标变换**：设备坐标到图集坐标
- **覆盖率调制**：根据图集值调制片段覆盖率

### 反向填充处理

当 `isInverseFill` 为 `true`：
- 设置 `kInvertCoverage` 标志
- 覆盖率值反转：`1 - atlasCoverage`
- `fillBounds` 扩展为裁剪区域

这实现了路径的镂空效果。

### 边界检查

自动设置 `kCheckBounds` 标志：
- 防止采样到图集中相邻路径的区域
- 片段着色器检查坐标是否在路径边界内
- 超出边界的片段丢弃

### 实例数据打包

每个实例的数据包括：
1. **填充边界**（4 ints）：定义渲染矩形
2. **变换矩阵**（6 floats）：仿射变换分量
3. **颜色**（4 floats）：RGBA 颜色
4. **图集位置**（由 AtlasInstancedHelper 管理）

### 顶点 vs VertexID

两种渲染模式：
- **支持 VertexID**：使用 `gl_VertexID` 生成四边形顶点
- **不支持**：使用预生成的顶点缓冲区

### 操作合并

`onCombineIfPossible` 检查合并条件：
- 图集代理必须相同
- 处理器集合必须兼容
- 局部坐标使用必须匹配

合并时将实例追加到链表。

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `GrDrawOp` | 继承 | 绘制操作基类 |
| `AtlasInstancedHelper` | 核心依赖 | 图集实例化辅助工具 |
| `GrProcessorSet` | 强依赖 | 片段处理器管理 |
| `GrSurfaceProxyView` | 依赖 | 图集纹理视图 |
| `SkArenaAlloc` | 依赖 | 实例数据分配 |

### 被依赖的模块

| 模块 | 依赖类型 | 说明 |
|------|---------|------|
| `AtlasPathRenderer` | 创建 | 通过 AtlasPathRenderer 创建 |
| `SurfaceDrawContext` | 使用 | 添加操作到绘制上下文 |

## 设计模式与设计决策

### 1. 链表管理实例

使用侵入式链表存储实例：
- **效率**：无额外内存分配
- **Arena 分配**：与操作生命周期绑定
- **追加优化**：通过尾指针 O(1) 追加

### 2. 仿射变换紧凑表示

只存储 6 个浮点数而非完整矩阵：
- **节省空间**：实例数据更小
- **限制**：不支持透视变换
- **合理性**：图集路径不支持透视

### 3. 条件顶点缓冲区

根据硬件能力选择渲染路径：
- **VertexID 支持**：无需顶点缓冲区，节省内存
- **无 VertexID**：使用预生成缓冲区，兼容性好

### 4. 标志位配置

通过标志位控制着色器行为：
- **kInvertCoverage**：反向填充
- **kCheckBounds**：边界检查
- **编译时决定**：避免运行时分支

## 性能考量

### 1. 实例化收益

单个 draw call 绘制多个路径：
- 减少 CPU-GPU 通信
- 减少驱动验证开销
- 提高 GPU 利用率

### 2. 图集纹理复用

多个路径共享图集纹理：
- 减少纹理绑定次数
- 提高纹理缓存命中率
- 优化内存带宽

### 3. 实例数据大小

每个实例约 56 字节（不含 AtlasInstance）：
- 合理的数据量
- 适合 GPU 缓存
- 支持大量实例

### 4. 操作合并

合并兼容操作：
- 增加单次绘制的实例数
- 减少状态切换
- 提高批处理效率

### 5. VertexID 优化

使用 VertexID 避免顶点缓冲区：
- 节省内存
- 减少数据传输
- 在支持的硬件上性能更好

### 6. 边界检查成本

边界检查增加片段着色器成本：
- 额外的条件判断
- 但避免了错误的采样
- 权衡正确性与性能

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/ops/GrDrawOp.h` | 基类 | 绘制操作基类 |
| `src/gpu/ganesh/ops/AtlasInstancedHelper.h` | 核心组件 | 图集实例化辅助 |
| `src/gpu/ganesh/ops/AtlasPathRenderer.h` | 创建者 | 创建此操作 |
| `src/gpu/ganesh/ops/AtlasRenderTask.h` | 协作 | 生成图集纹理 |
| `src/gpu/ganesh/GrProcessorSet.h` | 依赖 | 片段处理器管理 |
| `src/base/SkArenaAlloc.h` | 依赖 | Arena 分配器 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 使用者 | 表面绘制上下文 |
