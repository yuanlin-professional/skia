# skdiff_html

> 源文件: `tools/skdiff/skdiff_html.h`, `tools/skdiff/skdiff_html.cpp`

## 概述

skdiff_html 是 Skia 图像对比工具 skdiff 的 HTML 报告生成模块。它将图像差异比较结果输出为格式化的 HTML 页面，包含图像缩略图、差异统计、像素级差异可视化，以及用于选择和导出差异图像列表的交互式 JavaScript 功能。

该模块是 Skia 持续集成和质量保证工具链的一部分，用于直观地展示渲染结果的变化。

## 架构位置

```
skdiff 工具
  +-- skdiff.h         (核心差异计算)
  +-- skdiff_html.h    (HTML 报告生成) <-- 本文件
  +-- skdiff_main.cpp  (命令行入口)
```

## 主要类与结构体

本模块无自定义类，由独立函数组成。使用的外部类型包括：
- `DiffRecord`: 单个图像对的差异记录
- `DiffResource`: 差异资源信息
- `RecordArray`: 差异记录数组

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `print_diff_page(matchCount, colorThreshold, differences, baseDir, comparisonDir, outputDir)` | 生成完整的 HTML 差异报告页面 |

## 内部实现细节

### HTML 页面结构
1. **JavaScript**: 嵌入 `generateCheckedList()` 函数，收集所有选中的复选框生成文件列表
2. **表头**: 显示匹配统计（匹配数/总数）、颜色阈值、基准目录和对比目录
3. **差异行**: 每行包含复选框、标签（文件名+差异指标）、白色差异图、颜色差异图、基准图、对比图
4. **交互按钮**: "Create Rebaseline List" 按钮触发 JavaScript 收集选中项

### 图像尺寸计算（compute_image_height）
智能缩放图像高度，限制为 240px 高或 360px 宽（取较小值），保持宽高比。

### 差异标签显示（print_label_cell）
- 百分比形式的像素差异比例和加权差异比例
- 小于 1% 时额外显示精确像素数
- Alpha 通道的平均/最大/总 mismatch
- RGB 颜色通道的平均/最大 mismatch

### 路径处理
HTML 中的图像路径需要从相对于工作目录转换为相对于输出目录。通过计算输出目录深度并添加相应数量的 `../` 前缀实现。

### 差异记录过滤
仅输出 `kDifferentPixels`、`kDifferentSizes`、`kCouldNotCompare` 类型的记录，跳过完全相同的图像对。

## 依赖关系

- **Skia 核心**: `SkStream` (SkFILEWStream)
- **skdiff**: `skdiff.h` (DiffRecord, RecordArray 等)
- **SkString**: 路径拼接和格式化

## 设计模式与设计决策

1. **静态函数组织**: 所有 HTML 生成函数为模块级静态函数，仅暴露一个公共接口
2. **流式输出**: 使用 `SkFILEWStream` 逐段写入 HTML，避免大字符串拼接
3. **渐进式刷新**: 每行写完后调用 `flush()` 确保数据持久化
4. **跨平台路径**: 使用 `PATH_DIV_CHAR` / `PATH_DIV_STR` 宏处理路径分隔符差异

## 性能考量

- 逐行刷新文件流避免内存中累积大量 HTML 内容
- 图像缩放计算简单，不进行实际图像处理

## 相关文件

- `tools/skdiff/skdiff.h` - 核心差异数据结构和算法
- `tools/skdiff/skdiff_main.cpp` - skdiff 命令行工具入口
- `tools/skdiff/skdiff_utils.h` - skdiff 工具函数
