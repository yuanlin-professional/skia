# SkSVGDOM

> 源文件: modules/svg/include/SkSVGDOM.h

## 概述

`SkSVGDOM` 是 SVG 文档对象模型的根类,负责 SVG 文件的解析、DOM 树构建和渲染管理。这是 Skia SVG 模块的主要入口点。

## 主要功能

- 从 XML 字符串或流解析 SVG 文档
- 构建 SVG DOM 树(节点层次结构)
- 管理 SVG 根元素(`<svg>`)
- 提供渲染接口
- 维护 ID 到节点的映射(用于引用)

## 核心接口

```cpp
static sk_sp<SkSVGDOM> MakeFromStream(SkStream&);
static sk_sp<SkSVGDOM> MakeFromString(const char*);

void render(SkCanvas*);
void setContainerSize(const SkSize&);

SkSVGNode* findNodeById(const char* id);
```

## 工作流程

1. 解析 XML 文档
2. 创建 SVG 节点对象
3. 构建 DOM 树结构
4. 解析和设置属性
5. 渲染到 Canvas

## 设计特点

封装 XML 解析细节,提供简洁的 API。支持动态容器尺寸设置,自动处理 viewBox 和 preserveAspectRatio。

## 相关文件

- `modules/svg/src/SkSVGDOM.cpp`: 实现
- `modules/svg/include/SkSVGNode.h`: 节点基类
- `modules/svg/include/SkSVGSVG.h`: SVG 根元素

`SkSVGDOM` 是 Skia SVG 渲染的核心,提供从文件到图形的完整管线。
