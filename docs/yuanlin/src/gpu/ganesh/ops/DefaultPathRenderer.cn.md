# DefaultPathRenderer

> 源文件
> - src/gpu/ganesh/ops/DefaultPathRenderer.h

## 概述

`DefaultPathRenderer` 是 Skia Ganesh GPU 后端的默认路径渲染器，作为路径渲染系统的后备选项。当其他专用渲染器无法处理特定路径时，该渲染器使用模板缓冲区解决填充规则（如缠绕规则、奇偶规则），提供通用但可靠的路径渲染能力。

该渲染器是路径渲染链中的"最后防线"，保证所有合法路径都能被正确渲染。它牺牲部分性能以换取最大的兼容性和正确性。

## 架构位置

```
Skia GPU 渲染架构:
├── PathRenderer 系统
│   ├── AALinearizingConvexPathRenderer
│   ├── AAHairLinePathRenderer
│   ├── AtlasPathRenderer
│   └── DefaultPathRenderer ← 本类（后备渲染器）
└── 渲染策略
    ├── 模板-覆盖两遍渲染
    └── 填充规则解析
```

## 主要类与结构体

### DefaultPathRenderer 类

继承自 `PathRenderer`，提供通用路径渲染能力。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| 无公共成员变量 | - | 无状态渲染器 |

## 公共 API 函数

### PathRenderer 接口

```cpp
const char* name() const override
```
返回渲染器名称 "Default"。

```cpp
StencilSupport onGetStencilSupport(const GrStyledShape&) const override
```
返回模板支持类型。DefaultPathRenderer 通常支持模板操作。

```cpp
CanDrawPath onCanDrawPath(const CanDrawPathArgs&) const override
```
判断是否可以渲染给定路径。作为后备渲染器，通常返回 `kYes`，除非路径无效或硬件限制。

```cpp
bool onDrawPath(const DrawPathArgs&) override
```
执行路径渲染，调用内部 `internalDrawPath` 实现实际绘制。

```cpp
void onStencilPath(const StencilPathArgs&) override
```
只更新模板缓冲区而不写入颜色，用于复杂的裁剪和合成操作。

## 内部实现细节

### 模板-覆盖两遍渲染

经典的路径渲染算法：

**第一遍（模板遍）**：
1. 禁用颜色写入
2. 根据填充规则配置模板操作
3. 渲染路径三角剖分到模板缓冲区

**第二遍（覆盖遍）**：
1. 根据模板值绘制全屏矩形
2. 写入最终颜色
3. 可选地清除模板

### 填充规则解析

支持两种标准填充规则：

**非零缠绕规则（Winding）**：
- 模板操作：`Increment` 和 `Decrement`
- 判断：模板值 != 0 的像素填充

**奇偶规则（Even-Odd）**：
- 模板操作：`Invert`
- 判断：模板值为奇数的像素填充

### 路径三角剖分

将路径转换为三角形列表：
1. 分解贝塞尔曲线为线段
2. 使用三角剖分算法生成三角形
3. 提交三角形到 GPU

### 抗锯齿处理

DefaultPathRenderer 支持多种抗锯齿策略：
- **MSAA**：多重采样抗锯齿
- **Coverage**：覆盖率抗锯齿（可能需要额外处理）

### internalDrawPath 方法

核心渲染方法，参数：
- `stencilOnly`：是否只更新模板不写颜色
- `GrUserStencilSettings`：用户指定的模板配置
- 其他标准绘制参数

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `PathRenderer` | 继承 | 路径渲染器基类 |
| `GrStyledShape` | 依赖 | 封装路径和样式 |
| `SurfaceDrawContext` | 依赖 | 绘制上下文 |
| `GrPaint` | 依赖 | 绘制参数 |
| `GrClip` | 依赖 | 裁剪信息 |

### 被依赖的模块

| 模块 | 依赖类型 | 说明 |
|------|---------|------|
| `PathRendererChain` | 使用 | 作为后备渲染器注册 |
| `SurfaceDrawContext` | 使用 | 当其他渲染器失败时使用 |

## 设计模式与设计决策

### 1. 后备渲染器模式

作为路径渲染链的最后一环：
- **职责**：处理其他渲染器无法处理的路径
- **保证**：提供完整的路径渲染覆盖
- **权衡**：牺牲性能保证正确性

### 2. 模板缓冲区依赖

依赖硬件模板缓冲区：
- **优点**：通用、简单、正确
- **限制**：需要硬件支持模板
- **替代**：在不支持模板的平台可能降级

### 3. 两遍渲染策略

使用经典的模板-覆盖技术：
- **历史悠久**：经过验证的算法
- **硬件优化**：GPU 高度优化模板操作
- **通用性**：适用于任意复杂路径

### 4. 无状态设计

渲染器本身不保存状态：
- 简化并发和多线程
- 每次调用独立完成
- 状态在操作对象中管理

## 性能考量

### 1. 两遍开销

模板-覆盖需要两次渲染遍历：
- 模板遍：几何处理和光栅化
- 覆盖遍：全屏矩形绘制
- 适合复杂路径，简单路径可能过度

### 2. 模板缓冲区带宽

模板操作消耗内存带宽：
- 读-修改-写循环
- 在高分辨率下影响显著
- 移动设备尤其敏感

### 3. 三角剖分成本

CPU 端三角剖分开销：
- 复杂路径生成大量三角形
- 可能成为瓶颈
- 考虑缓存剖分结果

### 4. 填充率

覆盖遍绘制全屏矩形：
- 大量片段着色器调用
- 模板测试剔除大部分片段
- 早期模板测试优化有帮助

### 5. 批处理限制

模板依赖限制批处理：
- 每个路径独立的模板状态
- 难以合并多个路径
- 增加 draw call 数量

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/PathRenderer.h` | 基类 | 路径渲染器抽象接口 |
| `src/gpu/ganesh/geometry/GrStyledShape.h` | 依赖 | 封装路径和样式 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 使用者 | 表面绘制上下文 |
| `src/gpu/ganesh/GrPaint.h` | 依赖 | 绘制参数 |
| `src/gpu/ganesh/GrUserStencilSettings.h` | 依赖 | 用户模板配置 |
