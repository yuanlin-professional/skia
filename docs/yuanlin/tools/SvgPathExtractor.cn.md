# SvgPathExtractor

> 源文件：tools/SvgPathExtractor.h, tools/SvgPathExtractor.cpp

## 概述

`SvgPathExtractor` 是 Skia 工具库中用于从 SVG 文件提取路径信息的工具模块。该工具通过解析 SVG 文件并渲染到自定义的 Canvas 中，拦截所有路径绘制操作，从而提取 SVG 中的几何路径数据及其变换矩阵和绘制属性。这对于测试路径渲染、分析 SVG 内容或从 SVG 中提取矢量数据非常有用。

## 架构位置

- 位于 `tools/` 目录，属于辅助工具函数
- 依赖 Skia 的 SVG 模块 (`modules/svg/`)
- 使用自定义 Canvas 拦截绘制操作
- 在 `ToolUtils` 命名空间中
- 主要用于测试和调试

## 主要类与结构体

### ToolUtils::ExtractPathsFromSVG
```cpp
void ExtractPathsFromSVG(const char filepath[],
                        std::function<PathSniffCallback> callback)
```
- **功能**：从 SVG 文件提取所有路径
- **参数**：
  - `filepath`: SVG 文件路径
  - `callback`: 回调函数，接收每个路径及其变换和绘制属性
- **回调签名**：`void(const SkMatrix&, const SkPath&, const SkPaint&)`

### PathSniffer 内部类
自定义 Canvas，重写 `onDrawPath()` 拦截路径绘制：
```cpp
class PathSniffer : public SkCanvas {
    void onDrawPath(const SkPath& path, const SkPaint& paint) override {
        fPathSniffCallback(this->getTotalMatrix(), path, paint);
    }
};
```

## 公共 API 函数

### ExtractPathsFromSVG
- **流程**：
  1. 打开 SVG 文件流
  2. 使用 `SkSVGDOM::MakeFromStream()` 解析 SVG
  3. 创建 `PathSniffer` Canvas
  4. 渲染 SVG 到 Canvas，触发路径回调
  5. 对每个路径调用用户提供的回调函数

## 内部实现细节

### SVG 解析
使用 Skia 的 SVG DOM 模块解析和渲染 SVG：
```cpp
sk_sp<SkSVGDOM> svg = SkSVGDOM::MakeFromStream(stream);
svg->setContainerSize(SkSize::Make(pathSniffer.getBaseLayerSize()));
svg->render(&pathSniffer);
```

### Canvas 拦截机制
通过继承 `SkCanvas` 并重写 `onDrawPath()` 实现路径拦截。`getTotalMatrix()` 获取当前变换矩阵，包含 SVG 元素的所有累积变换。

## 依赖关系

**Skia 核心**：
- `include/core/SkCanvas.h`
- `include/core/SkPath.h`
- `include/core/SkPaint.h`
- `include/core/SkMatrix.h`

**SVG 模块**：
- `modules/svg/include/SkSVGDOM.h`
- `modules/svg/include/SkSVGNode.h`

**工具**：
- `tools/ToolUtils.h` - PathSniffCallback 定义

## 设计模式与设计决策

### 访问者模式
通过回调函数访问每个提取的路径，避免在工具内部存储所有路径。

### 观察者模式
Canvas 作为观察者拦截绘制操作。

### 关键决策
1. **回调机制**：灵活处理路径，无需预定义存储
2. **保留变换矩阵**：提供完整的路径位置信息
3. **保留 Paint 属性**：提供完整的绘制样式信息

## 性能考量

- 解析和渲染整个 SVG，适合小到中等大小的文件
- 每个路径单独回调，可流式处理
- 适用于测试和工具，非生产环境

## 相关文件

- `tools/ToolUtils.h` - 回调类型定义
- `modules/svg/` - SVG 解析和渲染
- `tests/` - 路径测试用例
