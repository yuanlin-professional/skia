# htmlcanvas - HTML Canvas 2D API 兼容层

## 概述

`htmlcanvas` 目录实现了一个基于 CanvasKit/Skia 的 HTML Canvas 2D API 兼容层。它提供了
`CanvasRenderingContext2D`、`HTMLCanvas`、`Path2D`、`LinearGradient`、`RadialGradient`
等标准 Web API 的实现，使得在没有真正 HTML Canvas 的环境中（如 Node.js、无头服务器）也能
使用熟悉的 Canvas 2D 绘图接口。

该兼容层通过将标准 Canvas 2D API 调用转发为底层 CanvasKit（Skia）调用来实现功能。例如，
`ctx.fillRect()` 最终会调用 `SkCanvas::drawRect()`，`ctx.createLinearGradient()` 会
创建 `SkShader` 渐变着色器。这种方式保证了渲染质量与 Skia 原生输出一致，同时提供了跨平台
的可移植性。

该模块作为可选功能，通过 `skia_canvaskit_enable_canvas_bindings` 构建标志控制，依赖于
矩阵辅助模块（`matrix.js`）。在构建时通过一系列 `--pre-js` 指令按特定顺序注入。

## 架构图

```
+----------------------------------------------------+
|             用户代码 (Canvas 2D API)                |
|  ctx.fillStyle = 'red';                            |
|  ctx.fillRect(0, 0, 100, 100);                     |
+----------------------------------------------------+
                        |
                        v
+----------------------------------------------------+
|           HTMLCanvas (htmlcanvas.js)                |
|  - MakeCanvas(w, h) -> HTMLCanvas                  |
|  - getContext('2d') -> CanvasRenderingContext2D     |
|  - toDataURL(codec, quality)                       |
|  - decodeImage(data) -> HTMLImage                  |
|  - loadFont(buffer, descriptors)                   |
+----------------------------------------------------+
                        |
                        v
+----------------------------------------------------+
|     CanvasRenderingContext2D (canvas2dcontext.js)   |
|  - fillRect/strokeRect/clearRect                   |
|  - drawImage / putImageData / getImageData         |
|  - createLinearGradient / createRadialGradient     |
|  - createPattern / fill / stroke / clip            |
|  - save / restore / transform / setTransform       |
+----------------------------------------------------+
        |           |           |            |
        v           v           v            v
+----------+ +----------+ +----------+ +----------+
|color.js  | |font.js   | |path2d.js | |pattern.js|
|(颜色解析) | |(字体缓存) | |(Path2D)  | |(图案)    |
+----------+ +----------+ +----------+ +----------+
+--------------------+ +------------------------+
|lineargradient.js   | |radialgradient.js       |
|(线性渐变)           | |(径向渐变)               |
+--------------------+ +------------------------+
                        |
                        v
+----------------------------------------------------+
|            CanvasKit / Skia 核心 API                |
|  SkCanvas, SkPaint, SkPath, SkShader, SkImage ...  |
+----------------------------------------------------+
```

## 目录结构

```
htmlcanvas/
|-- preamble.js           # 模块作用域开始
|-- postamble.js          # 模块作用域结束
|-- canvas2dcontext.js    # CanvasRenderingContext2D 完整实现
|-- htmlcanvas.js         # HTMLCanvas 类（表面管理、编码导出）
|-- htmlimage.js          # HTMLImage 类（图像包装）
|-- imagedata.js          # ImageData 类（像素数据）
|-- color.js              # 颜色字符串解析（CSS 颜色名称、hex、rgb/rgba）
|-- font.js               # 字体解析与缓存管理
|-- path2d.js             # Path2D 标准实现
|-- pattern.js            # CanvasPattern 实现
|-- lineargradient.js     # 线性渐变实现
|-- radialgradient.js     # 径向渐变实现
|-- util.js               # 兼容层工具函数
|-- _namedcolors.js       # CSS 命名颜色映射表
```

## 关键类与函数

### HTMLCanvas (htmlcanvas.js)
```javascript
CanvasKit.MakeCanvas(width, height)  // 创建 HTMLCanvas 实例
HTMLCanvas.getContext('2d')          // 获取 2D 渲染上下文
HTMLCanvas.toDataURL(codec, quality) // 导出为 data URL (PNG/JPEG)
HTMLCanvas.decodeImage(data)         // 解码图像数据
HTMLCanvas.loadFont(buffer, desc)    // 加载自定义字体
HTMLCanvas.dispose()                 // 释放所有资源
```

### CanvasRenderingContext2D (canvas2dcontext.js)
```javascript
// 绘制操作
ctx.fillRect(x, y, w, h)            // 填充矩形
ctx.strokeRect(x, y, w, h)          // 描边矩形
ctx.clearRect(x, y, w, h)           // 清除矩形区域
ctx.drawImage(img, ...)             // 绘制图像
ctx.fill(path, fillRule)            // 填充路径
ctx.stroke(path)                    // 描边路径
ctx.clip(path, fillRule)            // 裁剪路径

// 状态管理
ctx.save() / ctx.restore()          // 保存/恢复状态栈
ctx.fillStyle / ctx.strokeStyle     // 填充/描边样式
ctx.globalAlpha                     // 全局透明度
ctx.globalCompositeOperation        // 混合模式
ctx.lineWidth / ctx.lineCap         // 线条属性
ctx.shadowBlur / ctx.shadowColor    // 阴影属性

// 变换
ctx.translate(x, y)                 // 平移
ctx.rotate(angle)                   // 旋转
ctx.scale(x, y)                     // 缩放
ctx.setTransform(a, b, c, d, e, f)  // 设置变换矩阵
```

## 依赖关系

- **CanvasKit 核心**: 使用 `CanvasKit.Paint`、`CanvasKit.PathBuilder`、`CanvasKit.Font` 等
- **matrix.js**: 矩阵辅助计算（`skia_canvaskit_enable_canvas_bindings` 依赖 `skia_canvaskit_enable_matrix_helper`）
- **Skia SkCanvas**: 所有绘制操作最终委托给 Skia 的 SkCanvas 实现

## 设计模式分析

### 属性代理模式
`canvas2dcontext.js` 大量使用 `Object.defineProperty` 定义 getter/setter，将标准
Canvas 2D 属性（如 `fillStyle`、`strokeStyle`）映射到内部的 CanvasKit.Paint 状态。

### 资源清理模式
`HTMLCanvas.dispose()` 采用递归清理策略：先清理 Context 持有的路径和画笔，再清理
所有通过 `_toCleanUp` 数组跟踪的效果对象（渐变、图案），最后释放 Surface 资源。

### 已知限制
- `measureText` 仅返回宽度，不执行文本整形，仅对 ASCII 字母有效
- 不支持 `textAlign` 和 `textBaseAlign`
- `fillText` 不支持 width 参数

## 数据流

```
ctx.fillStyle = 'rgba(255, 0, 0, 0.5)'
        |
        v
color.js: parseColorString() ----> 解析为 CanvasKit.Color4f
        |
        v
存储到 ctx._fillStyle (SkColor4f)
        |
        v
ctx.fillRect(10, 10, 100, 50)
        |
        v
创建临时 Paint，设置 fillStyle 颜色
        |
        v
CanvasKit Canvas._drawRect(rect, paint)
        |
        v
Skia SkCanvas::drawRect() ----> GPU/CPU 渲染
```

## 相关文档与参考

- **MDN Canvas 2D API**: https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D
- **npm 使用示例**: `npm_build/example.html` 中的 Canvas 2D 对比演示
- **Node.js 示例**: `npm_build/node.example.js`
- **CanvasKit Canvas 2D 测试**: `tests/canvas2d_test.js`
