# GrTest.cpp - Ganesh 绘制操作随机测试

> 源文件: `tools/ganesh/GrTest.cpp`

## 概述

`GrTest.cpp` 实现了 Ganesh GPU 渲染后端的随机绘制操作测试基础设施。该文件的核心功能是 `GrDrawRandomOp` 函数，它从预先注册的一组绘制操作（Draw Op）工厂函数中随机选择一个，生成并执行一个随机参数化的 GPU 绘制操作。

此文件是 Skia 模糊测试（fuzz testing）和随机化测试的关键组件，通过随机组合不同的绘制操作类型和参数来发现潜在的渲染错误和崩溃。

## 架构位置

```
Skia 测试工具 (Ganesh)
├── tools/ganesh/
│   └── GrTest.cpp                      <-- 本文件：随机绘制操作测试
├── src/gpu/ganesh/ops/
│   ├── AAConvexPathOp.cpp              <-- 具体绘制操作实现（提供 __Test 工厂）
│   ├── CircleOp.cpp
│   ├── FillRectOp.cpp
│   └── ...
└── tests/
    └── OpChainTest.cpp 等              <-- 使用随机绘制操作的测试
```

## 主要类与结构体

本文件不定义新类，主要通过宏系统和函数指针表组织代码。

### 宏定义

```cpp
#define DRAW_OP_TEST_EXTERN(Op) \
    extern GrOp::Owner Op##__Test( \
        GrPaint&&, SkRandom*, GrRecordingContext*, \
        skgpu::ganesh::SurfaceDrawContext*, int)

#define DRAW_OP_TEST_ENTRY(Op) Op##__Test
```

- `DRAW_OP_TEST_EXTERN(Op)`：声明一个名为 `Op__Test` 的外部测试工厂函数
- `DRAW_OP_TEST_ENTRY(Op)`：在工厂函数表中引用该工厂函数

## 公共 API 函数

### `GrDrawRandomOp`
```cpp
void GrDrawRandomOp(SkRandom* random,
                    skgpu::ganesh::SurfaceDrawContext* sdc,
                    GrPaint&& paint);
```

从已注册的绘制操作工厂表中随机选择一个，使用随机参数生成一个 `GrOp` 并将其添加到 `SurfaceDrawContext` 中。

参数说明：
- `random`: 随机数生成器，用于选择操作类型和生成随机参数
- `sdc`: Surface 绘制上下文，生成的操作将被添加到此上下文
- `paint`: 绘制使用的画笔，会被移动到操作中

## 内部实现细节

### 已注册的绘制操作

文件中注册了以下绘制操作的测试工厂：

| 操作 | 说明 | 条件编译 |
|------|------|---------|
| `AAConvexPathOp` | 抗锯齿凸路径 | 始终可用 |
| `AAFlatteningConvexPathOp` | 抗锯齿平坦化凸路径 | 始终可用 |
| `AAHairlineOp` | 抗锯齿细线 | 始终可用 |
| `AAStrokeRectOp` | 抗锯齿描边矩形 | 始终可用 |
| `AtlasTextOp` | 图集文本渲染 | 始终可用 |
| `ButtCapDashedCircleOp` | 平头虚线圆 | 非优化尺寸构建 |
| `CircleOp` | 圆形 | 非优化尺寸构建 |
| `DashOpImpl` | 虚线 | 始终可用 |
| `DefaultPathOp` | 默认路径 | 始终可用 |
| `DrawAtlasOp` | 图集绘制 | 始终可用 |
| `DIEllipseOp` | 设备无关椭圆 | 非优化尺寸构建 |
| `EllipseOp` | 椭圆 | 非优化尺寸构建 |
| `FillRectOp` | 填充矩形 | 始终可用 |
| `NonAALatticeOp` | 非抗锯齿九宫格 | 始终可用 |
| `NonAAStrokeRectOp` | 非抗锯齿描边矩形 | 始终可用 |
| `RegionOp` | 区域 | 始终可用 |
| `RRectOp` | 圆角矩形 | 非优化尺寸构建 |
| `ShadowRRectOp` | 阴影圆角矩形 | 始终可用 |
| `SmallPathOp` | 小路径 | 非优化尺寸构建 |
| `TextureOpImpl` | 纹理 | 始终可用 |
| `TriangulatingPathOp` | 三角化路径 | 非优化尺寸构建 |

### 条件编译

使用 `SK_ENABLE_OPTIMIZE_SIZE` 宏控制是否包含某些较复杂的操作：

```cpp
#if !defined(SK_ENABLE_OPTIMIZE_SIZE)
DRAW_OP_TEST_EXTERN(CircleOp);
// ...
#endif
```

在优化尺寸的构建中（如 Android），部分几何图形操作不可用。

### 随机选择和执行

```cpp
static constexpr size_t kTotal = std::size(gFactories);
uint32_t index = random->nextULessThan(static_cast<uint32_t>(kTotal));
auto op = gFactories[index](std::move(paint), random, rContext, sdc, sdc->numSamples());
if (op) {
    sdc->addDrawOp(std::move(op));
}
```

注意：部分操作（如 `AtlasTextOp`）在某些情况下可能返回空指针（例如完全在渲染目标外部），因此在添加前进行了空检查。

## 依赖关系

- **Skia 核心**：`SkString`, `SkRandom`
- **Ganesh GPU 核心**：`GrDirectContextPriv`, `GrDrawingManager`, `GrGpu`, `GrResourceCache`, `GrTexture`
- **Ganesh GPU 操作**：`GrClip`, `GrDrawOpAtlas`, `GrRenderTargetProxy`, `SurfaceDrawContext`
- **Ganesh 图像**：`SkImage_Ganesh`
- **文本渲染**：`StrikeCache`, `TextBlobRedrawCoordinator`
- **Ganesh 后端**：`GrBackendSurface`, `GrContextOptions`, `GrRecordingContext`

## 设计模式与设计决策

1. **工厂方法表**：使用静态函数指针数组 `gFactories[]` 存储所有操作的测试工厂函数，通过宏自动生成声明和引用，减少手动维护的工作量。

2. **宏驱动的注册机制**：`DRAW_OP_TEST_EXTERN` 和 `DRAW_OP_TEST_ENTRY` 宏将操作名称自动映射为 `OpName__Test` 格式的函数名，建立了隐式的命名约定。

3. **条件编译的操作集**：在优化尺寸的构建中排除部分复杂操作，平衡了测试覆盖率和二进制尺寸。

4. **随机化测试**：通过可控的随机数生成器（`SkRandom`），测试是可重现的。相同的随机种子将产生相同的操作序列。

5. **容错设计**：操作创建可能失败（返回空指针），函数对此进行了优雅处理，不会因为单个操作创建失败而中断测试。

## 性能考量

- **编译时操作表**：`gFactories` 是 `constexpr` 静态数组，在编译时确定，零运行时初始化开销。
- **std::size 获取表大小**：使用 `std::size` 在编译时计算数组长度，避免手动维护计数。
- **移动语义**：`GrPaint` 通过移动语义传递到操作中，避免不必要的复制。
- **仅用于测试**：该函数不出现在生产代码路径中，性能影响局限于测试执行时间。

## 相关文件

- `src/gpu/ganesh/ops/` - 各绘制操作的实现文件（每个包含 `__Test` 工厂函数）
- `src/gpu/ganesh/SurfaceDrawContext.h` - Surface 绘制上下文
- `src/gpu/ganesh/GrDrawingManager.h` - 绘制管理器
- `include/gpu/ganesh/GrRecordingContext.h` - 录制上下文
- `src/base/SkRandom.h` - 随机数生成器
- `src/gpu/ganesh/GrGpu.h` - GPU 抽象层
