# DDL 创建模糊测试

> 源文件: `fuzz/FuzzCreateDDL.cpp`

## 概述

此文件对 Ganesh GPU 后端的 `GrDeferredDisplayList` (DDL) 创建和回放流程进行模糊测试。DDL 是 Chromium 使用的延迟渲染机制，允许在一个线程上录制绘图命令，在另一个线程的 GPU 上下文中回放。

## 架构位置

位于模糊测试框架 (`fuzz/`) 中，专注于 Chromium 集成层的 DDL API 测试。

## 主要类与结构体

无自定义结构体。使用 `GrSurfaceCharacterization`、`GrDeferredDisplayListRecorder` 等类型。

## 公共 API 函数

- `DEF_FUZZ(CreateDDL, fuzz)` - 创建 DDL 并在 Surface 上回放

## 内部实现细节

- `gen_fuzzed_imageinfo` 随机化图像尺寸（1-64）、颜色类型、alpha 类型和色彩空间
- `make_characterization` 使用 GrDirectContext 创建 GrSurfaceCharacterization
- `make_ddl` 在 DDL 录制器的 Canvas 上绘制随机矩形
- `make_surface` 创建 GPU 后端 Surface
- `draw_ddl` 将 DDL 回放到 Surface
- 支持 6 种传输函数和 5 种色域的组合
- Vulkan 构建支持 Protected 上下文选项
- 使用 `skgpu::ContextType::kGL` 上下文

## 依赖关系

- `include/private/chromium/GrDeferredDisplayList.h` - DDL API
- `include/private/chromium/GrSurfaceCharacterization.h` - Surface 特征
- `tools/ganesh/GrContextFactory.h` - GPU 上下文工厂

## 设计模式与设计决策

**端到端测试**：覆盖 DDL 的完整生命周期：特征创建 -> Surface 创建 -> DDL 录制 -> DDL 回放。

## 性能考量

最大 Surface 尺寸限制为 64x64 以加快模糊测试速度。

## 相关文件

- `fuzz/FuzzDDLThreading.cpp` - DDL 多线程模糊测试
