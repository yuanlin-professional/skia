# SkSVGRenderContext

> 源文件: modules/svg/include/SkSVGRenderContext.h

## 概述

`SkSVGRenderContext` 管理 SVG 渲染过程中的上下文信息,包括画布状态、样式继承、坐标变换、长度解析等。这是 SVG 渲染管线的核心状态管理类。

## 主要功能

- 维护渲染状态栈(支持嵌套元素)
- 管理样式属性的继承
- 处理坐标变换
- 提供长度单位解析上下文
- 管理裁剪、遮罩和滤镜
- 维护资源引用(渐变、图案等)

## 核心组件

### 长度上下文(LengthContext)
将 SVG 长度单位转换为绝对像素值,考虑视口尺寸、字体大小等因素。

### 呈现属性(PresentationAttributes)
存储和继承填充、描边、字体等样式属性,支持 CSS 样式继承模型。

### 变换栈
管理累积的坐标变换,支持嵌套的 transform 属性。

### 资源管理
通过 IDMapper 查找和缓存渐变、滤镜等资源。

## 渲染流程

```
创建初始上下文 → 递归遍历 DOM 树
  → 对每个节点:
    - 应用局部样式和变换
    - 创建子上下文(继承父属性)
    - 执行渲染
    - 恢复上下文
```

## 设计特点

使用栈结构支持深度优先遍历,自动处理样式继承,提供便捷的属性访问接口,管理 Canvas 状态的保存和恢复。

## 相关文件

- `modules/svg/src/SkSVGRenderContext.cpp`: 实现
- `SkSVGNode.h`: 使用渲染上下文的节点基类
- `SkSVGLengthContext.h`: 长度解析上下文

该类是 SVG 渲染的核心基础设施,确保正确的样式继承和坐标变换。
