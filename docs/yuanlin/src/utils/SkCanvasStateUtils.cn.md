# SkCanvasStateUtils

> 源文件: include/utils/SkCanvasStateUtils.h, src/utils/SkCanvasStateUtils.cpp

## 概述

SkCanvasStateUtils 提供了一组用于跨库边界复制 SkCanvas 状态的工具函数。该工具的主要目的是在不同版本的 Skia 库之间传递 Canvas 状态,例如在主应用程序和插件之间,或者在使用不同 Skia 版本编译的模块之间。通过捕获、传递和重建 Canvas 状态,可以在不同的 Skia 实例中继续绘图操作。

核心功能:
- 捕获当前 Canvas 的状态(矩阵、裁剪、设备)
- 将状态序列化为跨 ABI 稳定的数据结构
- 从捕获的状态重建新的 Canvas 实例
- 管理状态数据的生命周期

## 架构位置

SkCanvasStateUtils 位于 Skia 的 utils 模块中,处理跨版本兼容性:

```
Skia Graphics Library
├── Core
│   ├── SkCanvas (画布接口)
│   ├── SkDevice (设备抽象)
│   └── SkBitmap (位图数据)
├── Utils
│   ├── SkCanvasStateUtils (状态捕获/恢复) ← 当前模块
│   └── SkCanvasStack (多层 Canvas 栈)
└── Private
    └── SkWriter32 (序列化工具)
```

该工具作为 Skia 内部实现与外部模块之间的桥梁,提供稳定的 ABI 接口。

## 主要类与结构体

### SkCanvasStateUtils

**类型**: 静态工具类

**继承关系**:
- 无继承,纯静态工具类

**关键成员变量**:
- 无实例成员,仅提供静态方法

### 内部数据结构 (ABI 稳定)

#### RasterConfigs 枚举

| 配置 | 值 | 说明 |
|-----|---|------|
| kUnknown_RasterConfig | 0 | 未知像素格式 |
| kRGB_565_RasterConfig | 1 | 16位 RGB565 格式 |
| kARGB_8888_RasterConfig | 2 | 32位 ARGB8888 格式 |

#### CanvasBackends 枚举

| 后端类型 | 值 | 说明 |
|---------|---|------|
| kUnknown_CanvasBackend | 0 | 未知后端 |
| kRaster_CanvasBackend | 1 | 光栅化后端(支持) |
| kGPU_CanvasBackend | 2 | GPU 后端 |
| kPDF_CanvasBackend | 3 | PDF 后端 |

#### ClipRect 结构

| 成员类型 | 名称 | 说明 |
|---------|------|------|
| int32_t | left | 裁剪矩形左边界 |
| int32_t | top | 裁剪矩形上边界 |
| int32_t | right | 裁剪矩形右边界 |
| int32_t | bottom | 裁剪矩形下边界 |

#### SkMCState 结构

| 成员类型 | 名称 | 说明 |
|---------|------|------|
| float[9] | matrix | 3x3 变换矩阵 |
| int32_t | clipRectCount | 裁剪矩形数量 |
| ClipRect* | clipRects | 裁剪矩形数组指针 |

#### SkCanvasLayerState 结构

| 成员类型 | 名称 | 说明 |
|---------|------|------|
| CanvasBackend | type | 后端类型 |
| int32_t | x, y | 图层偏移 |
| int32_t | width, height | 图层尺寸 |
| SkMCState | mcState | 矩阵/裁剪状态 |
| union | raster/gpu | 后端特定数据 |

### SkCanvasState 基类

**继承关系**:
- 基类: SkCanvasState
- 派生类: SkCanvasState_v1

**关键成员变量**:

| 成员类型 | 名称 | 说明 |
|---------|------|------|
| int32_t | version | 结构版本号(必须首位) |
| int32_t | width | Canvas 宽度 |
| int32_t | height | Canvas 高度 |
| int32_t | alignmentPadding | 对齐填充 |

### SkCanvasState_v1 类

**继承关系**:
- 继承自: SkCanvasState

**关键成员变量**:

| 成员类型 | 名称 | 说明 |
|---------|------|------|
| SkMCState | mcState | 顶层矩阵/裁剪状态 |
| int32_t | layerCount | 图层数量 |
| SkCanvasLayerState* | layers | 图层数组 |
| SkCanvas* | originalCanvas | 原始 Canvas 指针(私有) |

**常量**:
- `kVersion = 1`: 当前版本号

## 公共 API 函数

### CaptureCanvasState

```cpp
static SkCanvasState* CaptureCanvasState(SkCanvas* canvas);
```

**功能**: 捕获 Canvas 的当前状态到不透明指针。

**参数**:
- `canvas`: 要捕获状态的 Canvas

**返回值**:
- 成功: 指向 SkCanvasState 的指针
- 失败: nullptr

**失败条件**:
1. Canvas 设备类型不支持(仅支持光栅设备)
2. 裁剪类型不支持(仅支持非抗锯齿裁剪)
3. 设备像素格式不支持(仅支持 RGB565/ARGB8888)
4. 设备不是像素对齐的(例如经过图像滤镜变换)
5. 设备无像素访问权限或尺寸为零

**注意事项**:
- 建议在所有使用该状态的 Canvas 释放前,不要使用原始 Canvas
- 不会捕获绘制滤镜(draw filters)
- 调用者负责调用 ReleaseCanvasState 释放内存

### MakeFromCanvasState

```cpp
static std::unique_ptr<SkCanvas> MakeFromCanvasState(
    const SkCanvasState* state
);
```

**功能**: 从捕获的状态重建新的 Canvas。

**参数**:
- `state`: 由 CaptureCanvasState 返回的状态指针

**返回值**:
- 成功: SkCanvas 智能指针,其设备和矩阵/裁剪状态与原始 Canvas 相同
- 失败: nullptr

**失败条件**:
1. 状态格式无法识别(版本不匹配)
2. 捕获的设备类型不支持

**特性**:
- 返回的 Canvas 是独立的新实例
- 可以在与捕获不同的 Skia 版本中调用
- 调用者负责管理返回的 Canvas 生命周期

### ReleaseCanvasState

```cpp
static void ReleaseCanvasState(SkCanvasState* state);
```

**功能**: 释放捕获状态占用的内存。

**参数**:
- `state`: 要释放的状态指针

**注意事项**:
- 必须在所有使用该状态创建的 Canvas 销毁后才能调用
- 必须从创建状态的同一个库实例中调用
- 传入 nullptr 是安全的

## 内部实现细节

### 状态捕获流程

```cpp
CaptureCanvasState(canvas):
1. 检查裁剪是否为抗锯齿 (不支持则返回 null)
2. 创建 SkCanvasState_v1 实例
3. 调用 setup_MC_state() 捕获顶层矩阵/裁剪
4. 获取 Canvas 的顶层设备
5. 验证设备是光栅设备且可访问像素
6. 验证设备是像素对齐的
7. 获取设备的像素映射 (SkPixmap)
8. 将像素格式映射到 RasterConfig
9. 记录设备偏移、尺寸、行字节、像素指针
10. 调用 setup_MC_state() 捕获设备级矩阵/裁剪
11. 分配并复制图层状态数据
12. 返回状态指针
```

### setup_MC_state 实现

捕获矩阵和裁剪状态:

```cpp
void setup_MC_state(SkMCState* state, const SkMatrix& matrix, const SkIRect& clip) {
    // 1. 复制 3x3 矩阵的 9 个浮点数
    for (int i = 0; i < 9; i++) {
        state->matrix[i] = matrix.get(i);
    }

    // 2. 处理裁剪矩形
    if (!clip.isEmpty()) {
        state->clipRectCount = 1;
        state->clipRects = 分配单个 ClipRect
        state->clipRects[0] = {left, top, right, bottom}
    } else {
        state->clipRectCount = 0;
    }
}
```

**设计决策**: 仅支持单个裁剪矩形,这是对遗留多矩形裁剪的简化。

### 状态重建流程

```cpp
MakeFromCanvasState(state):
1. 验证版本号是否为 kVersion (1)
2. 转换为 SkCanvasState_v1 指针
3. 检查图层数量至少为 1
4. 创建 SkCanvasStack 实例
5. 调用 setup_canvas_from_MC_state() 设置顶层矩阵/裁剪
6. 逆序遍历图层:
   a. 调用 make_canvas_from_canvas_layer() 为每个图层创建 Canvas
   b. 从图层的光栅数据创建 SkBitmap
   c. 用 SkBitmap 创建 SkCanvas
   d. 应用图层的矩阵/裁剪状态
   e. 将 Canvas 推入 SkCanvasStack
7. 返回 SkCanvasStack 实例
```

### setup_canvas_from_MC_state 实现

从捕获的状态恢复矩阵和裁剪:

```cpp
void setup_canvas_from_MC_state(const SkMCState& state, SkCanvas* canvas) {
    // 1. 重建矩阵
    SkMatrix matrix;
    for (int i = 0; i < 9; i++) {
        matrix.set(i, state.matrix[i]);
    }

    // 2. 合并所有裁剪矩形为边界框
    SkIRect bounds = SkIRect::MakeEmpty();
    for (int i = 0; i < clipRectCount; ++i) {
        bounds.join(clipRects[i]);
    }

    // 3. 应用到 Canvas
    canvas->clipRect(SkRect::Make(bounds));
    canvas->concat(matrix);
}
```

### 像素格式映射

ColorType 到 RasterConfig 的转换:

| SkColorType | RasterConfig |
|-------------|--------------|
| kN32_SkColorType | kARGB_8888_RasterConfig |
| kRGB_565_SkColorType | kRGB_565_RasterConfig |
| 其他 | 不支持(返回 null) |

### 内存管理

**分配策略**:
- 使用 `sk_malloc_throw()` 分配裁剪矩形和图层数组
- 保证分配成功或抛出异常

**释放策略**:
- 析构函数遍历所有图层,释放每个图层的 clipRects
- 释放顶层 mcState.clipRects
- 释放 layers 数组
- 即使 `sk_malloc(0)` 也会返回非 null,因此总是安全释放

### ABI 稳定性保证

关键设计原则:
1. **版本号首位**: version 字段必须在结构体首位,确保版本不匹配时仍可读取
2. **固定大小类型**: 使用 int32_t/float 等明确大小的类型
3. **扩展策略**: 新增字段通过新的子类(如 SkCanvasState_v2)实现
4. **向后兼容**: 旧版本库可以拒绝新版本状态
5. **前向兼容**: 新版本库可以处理旧版本状态

## 依赖关系

### 依赖的模块

| 模块 | 类型 | 说明 |
|-----|------|------|
| SkCanvas | 核心接口 | 源 Canvas 和目标 Canvas |
| SkDevice | 核心设备 | 访问设备像素数据 |
| SkBitmap | 核心图像 | 重建 Canvas 时创建位图 |
| SkPixmap | 核心图像 | 像素数据访问 |
| SkMatrix | 核心几何 | 变换矩阵 |
| SkCanvasStack | 工具类 | 多层 Canvas 管理 |
| SkWriter32 | 内部工具 | 序列化辅助 |

### 被依赖的模块

| 模块 | 使用场景 | 说明 |
|-----|---------|------|
| Android Framework | 跨进程绘图 | 在不同进程间传递 Canvas 状态 |
| 插件系统 | 跨模块渲染 | 插件使用主程序的 Canvas |
| 测试框架 | 状态验证 | CanvasState 测试库 |

## 设计模式与设计决策

### 不透明指针模式

使用 SkCanvasState 不透明指针:
- **隐藏实现**: 用户代码不需要了解内部结构
- **版本隔离**: 不同版本的结构体布局可以共存
- **ABI 稳定**: 指针类型在所有版本中大小一致

### 版本控制策略

结构体版本管理:
- **显式版本号**: version 字段标识结构版本
- **版本号首位**: 确保跨版本可读取版本号
- **子类扩展**: 新版本通过继承添加字段
- **运行时检查**: 函数中验证版本号兼容性

### 限制与权衡

支持限制的设计原因:

1. **仅光栅设备**:
   - GPU 状态包含复杂的 GL/Vulkan 上下文,难以序列化
   - PDF 等矢量后端状态不适合重建

2. **非抗锯齿裁剪**:
   - 抗锯齿裁剪需要存储复杂的遮罩数据
   - 矩形裁剪可以用简单的整数坐标表示

3. **单矩阵裁剪**:
   - 简化 ABI 结构
   - 遗留多层裁剪已不再使用

4. **有限像素格式**:
   - RGB565 和 ARGB8888 是最常用格式
   - 减少跨平台格式差异

### 资源所有权

清晰的所有权语义:
- **捕获**: CaptureCanvasState 分配内存,返回指针
- **使用**: MakeFromCanvasState 读取但不修改状态
- **释放**: ReleaseCanvasState 必须由同一库调用
- **限制**: 状态在所有衍生 Canvas 销毁前不能释放

### 遗留兼容性

处理历史设计:
- 支持多图层状态(虽然新代码只生成单层)
- 在重建时逆序处理图层(保持历史行为)
- 保留对旧版本状态的读取能力

## 性能考量

### 内存复制

状态捕获的开销:
- 仅复制元数据(矩阵、裁剪矩形、像素指针)
- **不复制像素数据**,仅存储指针
- 内存占用: O(layerCount + clipRectCount)

### 状态重建成本

MakeFromCanvasState 的性能:
- 创建新的 SkCanvas 和 SkBitmap 对象
- 使用 `installPixels()` 共享像素数据(零拷贝)
- 不涉及像素复制或解码

### SkCanvasStack 开销

使用栈式 Canvas 的影响:
- 每次绘图操作需遍历所有子 Canvas
- 对单层情况增加轻微间接调用开销
- 支持历史多层状态的必要代价

### 限制检查

早期失败策略:
- 在捕获时立即检查所有限制
- 避免部分捕获后才失败的情况
- 减少无效状态的传播

### 序列化优化

使用 SkWriter32 的好处:
- 高效的内存布局计算
- 避免多次分配
- `reserve()` 和 `flatten()` 模式减少复制

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/utils/SkCanvasStateUtils.h | 公共 API 声明 |
| src/utils/SkCanvasStateUtils.cpp | 实现代码 |
| src/utils/SkCanvasStack.h | Canvas 栈辅助类 |
| src/utils/SkCanvasStack.cpp | Canvas 栈实现 |
| include/core/SkCanvas.h | Canvas 基类 |
| src/core/SkDevice.h | 设备抽象 |
| include/core/SkBitmap.h | 位图类 |
| include/core/SkPixmap.h | 像素映射 |
| include/core/SkMatrix.h | 变换矩阵 |
| src/core/SkWriter32.h | 序列化工具 |
| gyp/canvas_state_lib.gyp | 测试库构建配置 |
