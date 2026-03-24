# ClearOp

> 源文件
> - src/gpu/ganesh/ops/ClearOp.h
> - src/gpu/ganesh/ops/ClearOp.cpp

## 概述

`ClearOp` 是 Skia Ganesh GPU 后端的清除操作，用于高效清除颜色缓冲区和模板缓冲区。该操作支持全屏清除和裁剪区域清除，是渲染管线中的基础操作，通常在渲染开始时或需要重置缓冲区时使用。

清除操作直接映射到 GPU 的硬件清除指令，比绘制全屏矩形更高效。该操作支持与相邻清除操作合并，减少 GPU 命令开销。

## 架构位置

```
Skia GPU 渲染架构:
├── GrOp 操作层
│   ├── GrDrawOp (绘制操作)
│   ├── GrOp (通用操作)
│   │   └── ClearOp ← 本类（清除操作）
│   └── 其他操作
└── OpsTask (操作任务管理)
    └── 管理和执行 ClearOp
```

## 主要类与结构体

### ClearOp 类

继承自 `GrOp`，实现缓冲区清除操作。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fScissor` | `GrScissorState` | 裁剪状态（全屏或裁剪矩形） |
| `fColor` | `std::array<float, 4>` | 清除颜色（RGBA，0.0-1.0） |
| `fStencilInsideMask` | `bool` | 模板清除值（内部或外部） |
| `fBuffer` | `Buffer` | 清除的缓冲区类型掩码 |

### Buffer 枚举

清除目标缓冲区的位掩码：

| 枚举值 | 值 | 说明 |
|-------|-----|------|
| `kColor` | 0b01 | 颜色缓冲区 |
| `kStencilClip` | 0b10 | 模板裁剪缓冲区 |
| `kBoth` | 0b11 | 颜色和模板缓冲区 |

## 公共 API 函数

### 工厂方法

```cpp
static GrOp::Owner MakeColor(GrRecordingContext* context,
                             const GrScissorState& scissor,
                             std::array<float, 4> color)
```
创建颜色缓冲区清除操作。参数：
- `scissor`：裁剪状态（启用裁剪或全屏）
- `color`：RGBA 清除颜色

```cpp
static GrOp::Owner MakeStencilClip(GrRecordingContext* context,
                                   const GrScissorState& scissor,
                                   bool insideMask)
```
创建模板裁剪清除操作。参数：
- `scissor`：裁剪状态
- `insideMask`：清除为内部遮罩值（true）或外部（false）

### GrOp 接口

```cpp
const char* name() const override
```
返回操作名称 "Clear"。

```cpp
const std::array<float, 4>& color() const
```
获取清除颜色。

```cpp
bool stencilInsideMask() const
```
获取模板清除值。

```cpp
CombineResult onCombineIfPossible(GrOp* t, SkArenaAlloc*, const GrCaps& caps) override
```
尝试与其他清除操作合并。

```cpp
void onExecute(GrOpFlushState* state, const SkRect& chainBounds) override
```
执行清除操作，调用 GPU 硬件清除指令。

## 内部实现细节

### 裁剪状态处理

`GrScissorState` 决定清除范围：
- **disabled**：全屏清除
- **enabled**：裁剪矩形清除

裁剪矩形在设备坐标空间中指定。

### 颜色格式

清除颜色使用浮点数数组 `std::array<float, 4>`：
- 范围：0.0（黑）到 1.0（白）
- 组件：R、G、B、A
- 映射到目标格式的实际位深

### 模板清除值

模板清除使用布尔标志：
- **true**：设置为内部遮罩值（通常 0xFF）
- **false**：设置为外部遮罩值（通常 0x00）

具体值由渲染目标的模板配置决定。

### 操作合并

`onCombineIfPossible` 检查合并条件：
1. 裁剪区域是否重叠或相邻
2. 清除目标缓冲区是否兼容
3. 清除值是否相同

合并策略：
- **扩展裁剪**：合并相邻区域
- **缓冲区组合**：同时清除多个缓冲区
- **优化 GPU 命令**：减少清除调用次数

### GPU 命令映射

`onExecute` 映射到平台特定的清除 API：
- **OpenGL**：`glClearBufferfv`、`glClearStencil`
- **Vulkan**：`vkCmdClearAttachments`
- **Direct3D**：`ClearRenderTargetView`、`ClearDepthStencilView`
- **Metal**：`MTLRenderCommandEncoder clearColor/Depth/Stencil`

### 无准备阶段

`onPrePrepare` 和 `onPrepare` 为空：
- 清除操作不需要顶点数据
- 不需要管线配置
- 直接映射到硬件指令

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `GrOp` | 继承 | 操作基类 |
| `GrScissorState` | 依赖 | 裁剪状态管理 |
| `GrOpFlushState` | 依赖 | 执行时状态 |
| `GrCaps` | 依赖 | 硬件能力查询 |

### 被依赖的模块

| 模块 | 依赖类型 | 说明 |
|------|---------|------|
| `OpsTask` | 使用 | 将清除操作添加到任务 |
| `SurfaceDrawContext` | 使用 | 通过上下文创建清除操作 |
| `GrRenderTargetContext` | 使用 | 渲染目标清除 |

## 设计模式与设计决策

### 1. 位掩码缓冲区类型

使用位掩码表示缓冲区类型：
- **灵活性**：支持同时清除多个缓冲区
- **高效性**：单个操作处理多个目标
- **扩展性**：易于添加新的缓冲区类型

### 2. 工厂方法分离

提供两个工厂方法而非单个通用方法：
- **清晰性**：明确清除目标
- **类型安全**：编译时检查
- **简化调用**：避免不必要的参数

### 3. 无准备阶段设计

清除操作跳过准备阶段：
- **简化**：无需复杂的状态管理
- **性能**：减少 CPU 开销
- **直接映射**：直接调用硬件指令

### 4. 操作合并策略

支持智能合并相邻清除：
- **减少 draw call**：多个清除合并为一个
- **优化带宽**：连续区域一次清除
- **保持正确性**：仔细检查合并条件

## 性能考量

### 1. 硬件清除优势

使用 GPU 硬件清除指令：
- 比绘制全屏矩形快
- 避免顶点处理和片段着色
- 直接操作缓冲区内存

### 2. 全屏 vs 裁剪清除

根据清除区域选择策略：
- **全屏清除**：最快，单个硬件命令
- **裁剪清除**：稍慢，需要设置裁剪状态
- **权衡**：清除整个缓冲区 vs 保留部分内容

### 3. 操作合并收益

合并相邻清除操作：
- 减少 GPU 命令数量
- 降低驱动开销
- 优化内存带宽使用

### 4. 早期清除

在渲染开始时清除：
- 允许 GPU 优化内存分配
- 启用快速清除路径
- 避免加载旧内容

### 5. 颜色格式转换

浮点颜色自动转换到目标格式：
- GPU 硬件处理转换
- 无 CPU 开销
- 支持任意目标位深

### 6. 模板清除成本

模板清除通常快于颜色清除：
- 更小的数据量（通常 8 位）
- 简单的内存写入
- 无混合或格式转换

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/ops/GrOp.h` | 基类 | 操作基类 |
| `src/gpu/ganesh/GrScissorState.h` | 依赖 | 裁剪状态 |
| `src/gpu/ganesh/GrOpFlushState.h` | 依赖 | 执行时状态 |
| `src/gpu/ganesh/ops/OpsTask.h` | 使用者 | 操作任务管理 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 使用者 | 表面绘制上下文 |
| `src/gpu/ganesh/GrCaps.h` | 依赖 | 硬件能力查询 |
