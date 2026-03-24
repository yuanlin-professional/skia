# tests/ganesh/ - Ganesh GPU 后端测试工具

## 概述

`tests/ganesh/` 目录包含 Skia Ganesh GPU 后端的专用测试工具函数和辅助类。Ganesh 是 Skia 的传统 GPU 渲染后端，支持 OpenGL、Vulkan、Metal、Direct3D 和 Dawn 等多种图形 API。此目录提供了在单元测试中操作 GPU 资源（如纹理、Surface、像素）所需的工具函数。

该目录仅包含两个文件：`GaneshTestUtils.h` 和 `GaneshTestUtils.cpp`，它们为 `tests/` 根目录中的 Ganesh GPU 测试提供通用的像素读写验证、Surface 上下文创建和引用计数检查等功能。这些工具函数被大量 GPU 测试文件引用，是 Ganesh 测试基础设施的核心组成部分。

需要注意的是，实际的 Ganesh GPU 单元测试文件（如 `BackendAllocationTest.cpp`、`VkBackendSurfaceTest.cpp` 等）位于 `tests/` 根目录下，而非此子目录中。此子目录专注于提供可复用的测试辅助功能。

## 架构图

```
+-------------------------------------------------------+
|              tests/ 根目录 (Ganesh 测试文件)            |
|  BackendAllocationTest.cpp  VkBackendSurfaceTest.cpp   |
|  TransferPixelsTest.cpp     EGLImageTest.cpp  ...      |
+---------------------------+---------------------------+
                            |
                            | 引用
                            v
+-------------------------------------------------------+
|              tests/ganesh/GaneshTestUtils               |
|  +---------------------------------------------------+|
|  | TestReadPixels()      -- 读取并验证像素            ||
|  | TestWritePixels()     -- 写入并验证像素            ||
|  | TestCopyFromSurface() -- 从 Surface 复制验证       ||
|  | CompareGaneshPixels() -- 像素比较(含容差)          ||
|  | CheckSingleThreadedProxyRefs() -- 引用计数检查     ||
|  | CreateSurfaceContext()  -- 创建测试用 SurfaceCtx   ||
|  +---------------------------------------------------+|
+-------------------------------------------------------+
            |                       |
            v                       v
+-------------------+  +-------------------------+
| src/gpu/ganesh/   |  | tests/ComparePixels.h   |
| (Ganesh 内部实现)  |  | (通用像素比较)           |
+-------------------+  +-------------------------+
```

## 目录结构

```
tests/ganesh/
├── GaneshTestUtils.h       # 头文件：声明所有测试工具函数
└── GaneshTestUtils.cpp     # 实现文件
```

## 关键类与函数

### GaneshTestUtils.h

| 函数 | 说明 |
|------|------|
| `TestReadPixels(Reporter*, GrDirectContext*, SurfaceContext*, uint32_t[], const char*)` | 从 GPU SurfaceContext 读取 RGBA 8888 像素并与期望值比较 |
| `TestWritePixels(Reporter*, GrDirectContext*, SurfaceContext*, bool, const char*)` | 尝试向 GPU SurfaceContext 写入 RGBA 8888 像素，验证是否符合预期 |
| `TestCopyFromSurface(Reporter*, GrDirectContext*, sk_sp<GrSurfaceProxy>, GrSurfaceOrigin, GrColorType, uint32_t[], const char*)` | 验证像素是否能从 proxy 复制到纹理和渲染目标两种目标 |
| `CompareGaneshPixels(const GrCPixmap&, const GrCPixmap&, const float[4], ErrorReporter&)` | 在通用色彩空间中比较两组像素，支持每通道容差 |
| `CheckSingleThreadedProxyRefs(Reporter*, GrSurfaceProxy*, int32_t proxyRefs, int32_t backingRefs)` | 验证 proxy 及其后备存储的引用计数 |
| `CreateSurfaceContext(GrRecordingContext*, const GrImageInfo&, ...)` | 根据参数创建 SurfaceContext/SurfaceFillContext/SurfaceDrawContext |

### 像素比较详解

`CompareGaneshPixels` 函数的工作流程：
1. 检查两个像素图的尺寸是否匹配
2. 将两个像素图转换为通用色彩空间（线性 sRGB 或共同色彩空间）
3. 使用 32 位浮点精度进行逐像素比较
4. 如果 Alpha 类型混合（一个 premul 一个 unpremul），使用 premul 进行比较
5. 对每个通道应用容差值 `tolRGBA[4]`

## 依赖关系

```
GaneshTestUtils.h 依赖:
├── include/core/SkColor.h           (颜色定义)
├── include/core/SkRefCnt.h          (引用计数)
├── include/gpu/GpuTypes.h           (GPU 类型)
├── include/gpu/ganesh/GrTypes.h     (Ganesh 类型)
├── src/gpu/SkBackingFit.h           (后备适配)
├── src/gpu/ganesh/GrImageInfo.h     (图像信息)
├── src/gpu/ganesh/GrPixmap.h        (GPU 像素图)
├── tests/ComparePixels.h            (通用像素比较接口)
└── src/gpu/ganesh/SurfaceContext.h   (Surface 上下文)
```

## 设计模式分析

### 1. 工具函数库模式

该目录采用纯工具函数库的设计，没有定义独立的类层次结构。所有函数都是无状态的，接受必要的上下文参数（`GrDirectContext*`、`Reporter*`）并执行验证操作。

### 2. 参数化测试支持

`CreateSurfaceContext` 函数通过丰富的默认参数（`SkBackingFit`、`GrSurfaceOrigin`、`GrRenderable`、`sampleCount`、`Mipmapped`、`Protected`、`Budgeted`）支持各种 GPU 资源配置的测试场景。

### 3. 错误报告回调模式

`CompareGaneshPixels` 使用 `std::function<ComparePixmapsErrorReporter>` 回调报告像素差异，允许调用者灵活处理比较失败（如记录日志、触发断言等）。

## 数据流

```
典型 Ganesh 测试执行流程:

测试函数 (如 BackendAllocationTest)
          |
          v
CreateSurfaceContext() -- 创建 GPU Surface
          |
          v
执行绘制/上传操作
          |
          v
TestReadPixels() -- 读取 GPU 数据到 CPU
          |
          v
CompareGaneshPixels() -- 逐像素比较
          |
          v
通过/失败 --> Reporter 报告结果
```

## 相关文档与参考

- `tests/ganesh/GaneshTestUtils.h` - 完整 API 声明
- `tests/ComparePixels.h` - 通用像素比较接口定义
- `src/gpu/ganesh/` - Ganesh GPU 后端内部实现
- `tests/Test.h` - 测试框架核心（`DEF_GANESH_TEST_FOR_*` 宏）
- `tools/ganesh/GrContextFactory.h` - GPU 上下文工厂
