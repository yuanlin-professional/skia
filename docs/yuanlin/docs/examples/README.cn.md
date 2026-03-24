# docs/examples - API 使用示例

## 概述

`examples/` 包含数百个独立的 C++ 代码示例文件，每个文件演示 Skia API 的
特定功能或用法。这些示例是学习 Skia API 的最佳参考资源，覆盖了从基础绘图
到高级效果的各个方面。

## 目录结构

```
examples/
├── 50_percent_gray.cpp              # 灰度绘制示例
├── Anti_Alias.cpp                   # 抗锯齿示例
├── Bitmap_*.cpp                     # Bitmap API 系列示例
├── Canvas_*.cpp                     # Canvas API 系列示例
├── Color_*.cpp                      # 颜色处理示例
├── Image_*.cpp                      # Image API 系列示例
├── Matrix_*.cpp                     # 矩阵变换示例
├── Paint_*.cpp                      # Paint API 系列示例
├── Path_*.cpp                       # Path API 系列示例
├── RRect_*.cpp                      # 圆角矩形示例
├── Surface_*.cpp                    # Surface API 示例
├── backdrop_blur_with_rrect_clip.cpp  # 背景模糊效果
├── bezier_curves.cpp                # 贝塞尔曲线
└── ... (数百个文件)
```

## 示例分类

### 核心绘图
- Bitmap 操作（创建、分配、像素操作）
- Canvas 绘制方法（drawPath、drawImage、drawText 等）
- Surface 管理

### 几何与变换
- Path 构建（线段、曲线、弧线）
- Matrix 变换（平移、旋转、缩放、透视）
- RRect 圆角矩形

### 效果与样式
- Paint 配置（颜色、描边、填充）
- Shader（渐变、图案）
- ColorFilter 和 ImageFilter
- 混合模式

## 使用方式

每个 `.cpp` 文件是独立的示例，可以直接参考其中的代码学习对应 API 的用法。

## 相关文档与参考

- Skia API 头文件: `include/core/`
- Skia 官网教程: https://skia.org/docs/
