# Graphite 预编译模糊测试

> 源文件: `fuzz/FuzzPrecompile.cpp`

## 概述

此文件对 Graphite GPU 后端的管线预编译（Precompile）功能进行模糊测试。它随机构建 SkPaint 和对应的 PaintOptions，验证预编译生成的管线能够覆盖实际绘制时所需的所有管线变体，确保预编译 API 的正确性。

## 架构位置

位于模糊测试框架 (`fuzz/`) 中，针对 Graphite 的 `precompile/` 子系统。

## 主要类与结构体

定义了多个枚举类型用于随机选择：
- `ColorSpaceType` - 色彩空间类型（None/sRGB/sRGBLinear/RGB）
- `ColorFilterType` - 颜色滤镜类型（None/Blend/Matrix/HSLAMatrix）

## 公共 API 函数

- `DEF_FUZZ(Precompile, fuzz)` - Graphite 预编译模糊测试入口

### 辅助函数
- `create_random_paint` - 创建随机 SkPaint 和对应的 PaintOptions
- `create_random_colorfilter` - 创建随机颜色滤镜
- `create_random_colorspace` - 创建随机色彩空间
- `check_draw` - 验证绘制不会触发额外的管线编译

## 内部实现细节

- 对每种 `DrawTypeFlags`（SimpleShape/NonSimpleShape）分别测试
- 调用 `Precompile` API 预编译管线，然后实际绘制验证无额外编译
- 比较预编译前后的 `numGraphicsPipelines` 确保管线已被预编译
- 使用 Graphite 的 `ContextFactory` 和 `Recorder`

## 依赖关系

- `include/gpu/graphite/precompile/` - 预编译 API
- `src/gpu/graphite/` - Graphite 内部实现
- `tools/graphite/ContextFactory.h` - 测试上下文工厂

## 设计模式与设计决策

**预编译验证**：通过对比管线数量变化来验证预编译的完整性。

## 性能考量

Canvas 大小仅 16x16，最小化 GPU 负载。

## 相关文件

- `include/gpu/graphite/precompile/` - Graphite 预编译 API
