# docs/architecture - Skia 架构文档

## 概述

`architecture/` 包含 Skia 核心组件的架构设计文档，以结构化的方式描述
Skia 内部的数据流和组件交互。

## 目录结构

```
architecture/
├── CPU.md               # CPU 后端架构详解
└── CPU.dot              # CPU 后端数据流图（Graphviz 格式）
```

## 关键文件

### CPU.md
Skia CPU 后端的完整架构文档，内容包括：

1. **术语定义**: 位图（Bitmap）、混合模式（Blend Mode）、裁剪（Clip）、
   覆盖遮罩（Coverage Mask）、光栅化（Rasterization）、着色器（Shader）等
2. **数据流详解**:
   - API 层: SkSurface -> SkCanvas -> SkPath/SkPaint
   - 设备层: SkBitmapDevice（分块优化、裁剪管理）
   - 编排层: SkDraw（协调单次绘制操作）
   - 光栅化层: SkScan（矢量到扫描线转换）
   - 像素写入层: SkRasterPipelineBlitter
   - 计算引擎: SkRasterPipeline（SIMD 阶段化管线）
   - 像素存储: SkPixmap / SkBitmap / SkPixelRef
3. **文本渲染**: SkFontMgr -> SkTypeface -> SkFont 流程
4. **Paint 效果管线**: Shader -> ColorFilter -> MaskFilter -> PathEffect -> Blender -> ImageFilter

### CPU.dot
使用 Graphviz DOT 语言编写的 CPU 后端数据流图，可用 `dot` 工具生成可视化图表：
```bash
dot -Tpng CPU.dot -o CPU.png
```

## 相关文档与参考

- CPU 后端源码: `src/core/`
- 光栅管线: `src/opts/`
- Skia 官网架构: https://skia.org/docs/dev/
