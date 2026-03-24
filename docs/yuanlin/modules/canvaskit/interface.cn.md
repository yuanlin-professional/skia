# CanvasKit Interface

> 源文件: modules/canvaskit/interface.js

## 概述

`interface.js` 是 CanvasKit 的核心 JavaScript 接口层,负责在 WASM 运行时初始化后增强和扩展 C++ 导出的 API。该文件实现了 JavaScript 层面的包装器、辅助函数和便捷方法,使得 Skia 的 C++ API 能够以更符合 JavaScript 习惯的方式被使用。它处理内存管理、类型转换、参数处理以及方法链式调用等功能。

该模块的核心是 `CanvasKit.onRuntimeInitialized` 回调函数,该函数在 WASM 库加载完成后执行,用于初始化全局状态、设置原型方法、创建常量对象等。文件中定义了大量的原型扩展方法,涵盖了 Path、Canvas、Image、Paint、Shader、Filter 等几乎所有 Skia 核心对象。

## 架构位置

该文件位于 CanvasKit 模块的核心层:
- **上层**: 被 HTML Canvas 兼容层(htmlcanvas/)和应用代码调用
- **同层**: 与 matrix.js、memory.js、paragraph.js 等其他接口文件协作
- **下层**: 调用 WASM 编译的 C++ Skia 核心库

作为 JavaScript 与 WASM 的桥梁,它处理从 JavaScript 类型到 WASM 内存的转换,并提供友好的 API 接口。

## 主要类与结构体

### 内存缓冲区
- `_scratchColor`: 4 个浮点数的颜色缓冲区
- `_scratch4x4Matrix`: 16 个浮点数的 4x4 矩阵缓冲区
- `_scratch3x3Matrix`: 9 个浮点数的 3x3 矩阵缓冲区
- `_scratchRRect`: 12 个浮点数的圆角矩形缓冲区
- `_scratchFourFloatsA/B`: 通用 4 浮点数缓冲区
- `_scratchThreeFloatsA/B`: 通用 3 浮点数缓冲区
- `_scratchIRect`: 4 个整数的矩形缓冲区

这些预分配的缓冲区用于减少频繁的内存分配和释放,提高性能。

### 颜色空间常量
```javascript
CanvasKit.ColorSpace.SRGB = CanvasKit.ColorSpace._MakeSRGB();
CanvasKit.ColorSpace.DISPLAY_P3 = CanvasKit.ColorSpace._MakeDisplayP3();
CanvasKit.ColorSpace.ADOBE_RGB = CanvasKit.ColorSpace._MakeAdobeRGB();
```

## 公共 API 函数

### Path 构造函数
- **`Path.MakeFromCmds(cmds)`**: 从命令数组创建路径
- **`Path.MakeFromVerbsPointsWeights(verbs, pts, weights)`**: 从动词、点和权重数组创建路径

### PathBuilder 方法(支持链式调用)
- **`addArc(oval, startAngle, sweepAngle)`**: 添加弧形
- **`addCircle(x, y, r, isCCW)`**: 添加圆形
- **`addOval(oval, isCCW, startIndex)`**: 添加椭圆
- **`addPath(...)`**: 添加路径,支持可选的变换矩阵
- **`addPolygon(points, close)`**: 添加多边形
- **`addRect(rect, isCCW)`**: 添加矩形
- **`addRRect(rrect, isCCW)`**: 添加圆角矩形
- **`arc(x, y, radius, startAngle, endAngle, ccw)`**: 添加 HTML Canvas 风格的弧形
- **`arcToOval/arcToRotated/arcToTangent`**: 多种弧形添加方式
- **`cubicTo/quadTo/conicTo`**: 添加三次/二次/圆锥曲线
- **`lineTo/moveTo/close`**: 基本路径操作
- **`offset(dx, dy)`**: 平移路径
- **`transform(...)`**: 变换路径

### Path 方法
- **`computeTightBounds(optionalOutputArray)`**: 计算紧凑边界框
- **`getBounds(optionalOutputArray)`**: 获取边界框
- **`getPoint(idx, optionalOutput)`**: 获取指定索引的点
- **`makeStroked(opts)`**: 创建描边版本的路径
- **`makeTrimmed(startT, stopT, isComplement)`**: 创建修剪版本的路径

### Canvas 绘制方法
- **`clear(color4f)`**: 清空画布
- **`clipRRect/clipRect`**: 裁剪区域
- **`concat(matr)`**: 连接变换矩阵
- **`drawArc/drawCircle/drawOval/drawRect/drawRRect`**: 绘制基本图形
- **`drawAtlas(atlas, srcRects, dstXforms, paint, ...)`**: 绘制图集
- **`drawImage/drawImageCubic/drawImageOptions`**: 绘制图像(支持不同采样方式)
- **`drawImageRect/drawImageRectCubic/drawImageRectOptions`**: 绘制图像矩形区域
- **`drawImageNine`**: 九宫格绘制
- **`drawLine/drawPoints`**: 绘制线条和点
- **`drawPaint/drawPath/drawPicture`**: 绘制填充、路径、图片
- **`drawParagraph`**: 绘制段落文本
- **`drawPatch`**: 绘制贝塞尔曲面片
- **`drawShadow`**: 绘制阴影
- **`drawTextBlob`**: 绘制文本块
- **`drawVertices`**: 绘制顶点数组
- **`drawColor/drawColorInt/drawColorComponents`**: 绘制颜色

### Canvas 状态查询
- **`getDeviceClipBounds(outputRect)`**: 获取设备裁剪边界
- **`getLocalToDevice()`**: 获取 4x4 变换矩阵
- **`getTotalMatrix()`**: 获取 3x3 变换矩阵
- **`quickReject(rect)`**: 快速判断矩形是否在裁剪区域外
- **`readPixels(...)`**: 读取像素数据
- **`writePixels(...)`**: 写入像素数据
- **`saveLayer(paint, boundsRect, backdrop, flags, backdropTileMode)`**: 保存图层

### Image 方法
- **`encodeToBytes(fmt, quality)`**: 编码为字节数组
- **`makeShaderCubic/makeShaderOptions`**: 创建着色器
- **`readPixels(...)`**: 读取像素数据

### 滤镜和效果
- **`ColorFilter.MakeBlend(color4f, mode, colorSpace)`**: 创建混合颜色滤镜
- **`ColorFilter.MakeMatrix(colorMatrix)`**: 创建矩阵颜色滤镜
- **`ImageFilter.MakeDropShadow/MakeDropShadowOnly`**: 创建阴影滤镜
- **`ImageFilter.MakeImage`**: 创建图像滤镜
- **`ImageFilter.MakeMatrixTransform`**: 创建矩阵变换滤镜
- **`PathEffect.MakeDash/MakeLine2D/MakePath2D`**: 创建路径效果

### Shader 创建
- **`Shader.MakeColor(color4f, colorSpace)`**: 创建纯色着色器
- **`Shader.MakeLinearGradient`**: 创建线性渐变
- **`Shader.MakeRadialGradient`**: 创建径向渐变
- **`Shader.MakeSweepGradient`**: 创建扫描渐变
- **`Shader.MakeTwoPointConicalGradient`**: 创建双点圆锥渐变

### Paint 方法
- **`getColor()`**: 获取颜色
- **`setColor(color4f, colorSpace)`**: 设置颜色
- **`setColorComponents(r, g, b, a, colorSpace)`**: 设置颜色分量

### Surface 方法
- **`getCanvas()`**: 获取画布
- **`makeImageSnapshot(optionalBoundsRect)`**: 创建图像快照
- **`makeSurface(imageInfo)`**: 创建子表面
- **`requestAnimationFrame(callback, dirtyRect)`**: 请求动画帧
- **`drawOnce(callback, dirtyRect)`**: 绘制一次后释放

### 工具函数
- **`computeTonalColors(tonalColors)`**: 计算色调颜色
- **`getShadowLocalBounds(...)`**: 获取阴影局部边界
- **`LTRBRect/XYWHRect/LTRBiRect/XYWHiRect`**: 创建矩形
- **`RRectXY(rect, rx, ry)`**: 创建圆角矩形
- **`MakeAnimatedImageFromEncoded(data)`**: 从编码数据创建动画图像
- **`MakeImageFromEncoded(data)`**: 从编码数据创建图像
- **`MakeImageFromCanvasImageSource(canvasImageSource)`**: 从 Canvas 图像源创建图像
- **`MakeImage(info, pixels, bytesPerRow)`**: 从像素数据创建图像
- **`MakeVertices(mode, positions, textureCoordinates, colors, indices, isVolatile)`**: 创建顶点对象

## 内部实现细节

### 内存管理策略
文件使用两种内存管理策略:
1. **预分配缓冲区**: 使用 `CanvasKit.Malloc` 分配固定大小的缓冲区,用于频繁的临时数据存储
2. **临时分配**: 对于动态大小的数据,使用 `copy1dArray` 等函数临时分配,用后立即释放

### 数据传递模式
JavaScript 到 WASM 的数据传递通过以下辅助函数:
- `copyColorToWasm`: 复制颜色到 WASM 内存
- `copyRectToWasm`: 复制矩形到 WASM 内存
- `copyRRectToWasm`: 复制圆角矩形到 WASM 内存
- `copy3x3MatrixToWasm`: 复制 3x3 矩阵到 WASM 内存
- `copy4x4MatrixToWasm`: 复制 4x4 矩阵到 WASM 内存
- `copy1dArray`: 复制一维数组到 WASM 内存
- `freeArraysThatAreNotMallocedByUsers`: 释放非用户分配的内存

### 可选输出数组模式
许多方法支持可选的输出数组参数,避免重复分配:
```javascript
Path.prototype.getBounds = function(optionalOutputArray) {
  this._getBounds(_scratchFourFloatsAPtr);
  var ta = _scratchFourFloatsA['toTypedArray']();
  if (optionalOutputArray) {
    optionalOutputArray.set(ta);
    return optionalOutputArray;
  }
  return ta.slice();
};
```

### 上下文管理
Canvas 和 Surface 对象维护 `_context` 字段,用于 WebGL/WebGPU 上下文管理:
```javascript
CanvasKit.Canvas.prototype.clear = function(color4f) {
  CanvasKit.setCurrentContext(this._context);
  // ...
};
```

### 链式调用支持
PathBuilder 的所有修改方法都返回 `this`,支持链式调用:
```javascript
CanvasKit["PathBuilder"].prototype["addCircle"] = function(x, y, r, isCCW) {
  this._addCircle(x, y, r, !!isCCW);
  return this;
};
```

### 采样选项处理
图像和滤镜方法支持两种采样方式:
1. **Cubic Resampler**: 通过 `B` 和 `C` 参数指定
2. **Filter Options**: 通过 `filter` 和可选的 `mipmap` 参数指定

代码动态检测参数类型并调用相应的内部方法。

## 依赖关系

### 内部依赖
- **memory.js**: 提供内存分配和复制函数
- **matrix.js**: 提供矩阵操作函数
- **WASM 导出**: 依赖 C++ 导出的 `_MakeXxx` 等下划线前缀方法

### 外部使用
- **htmlcanvas 模块**: 使用本接口提供 HTML Canvas 兼容层
- **paragraph.js**: 文本排版功能
- **skottie.js**: 动画功能
- **应用代码**: 直接调用 CanvasKit API

## 设计模式与设计决策

### 1. 包装器模式
JavaScript 方法包装 WASM 导出的 C++ 方法,处理参数转换和内存管理:
```javascript
CanvasKit.Path.MakeFromCmds = function(cmds) {
  var cmdPtr = copy1dArray(cmds, 'HEAPF32');
  var path = CanvasKit.Path._MakeFromCmds(cmdPtr, cmds.length);
  freeArraysThatAreNotMallocedByUsers(cmdPtr, cmds);
  return path;
};
```

### 2. 工厂模式
提供多个静态工厂方法创建对象:
- `Path.MakeFromCmds`
- `Path.MakeFromVerbsPointsWeights`
- `Shader.MakeLinearGradient`
- `ImageFilter.MakeDropShadow`

### 3. 构建器模式
`PathBuilder` 使用构建器模式,支持链式调用构建复杂路径。

### 4. 策略模式
采样选项处理使用策略模式,根据参数类型选择不同的采样策略。

### 5. 对象池模式
预分配的 scratch 缓冲区实现了简单的对象池,避免频繁分配。

### 设计决策
1. **延迟初始化**: 在 `onRuntimeInitialized` 中初始化,确保 WASM 已加载
2. **双接口设计**: 提供 `_method` 和 `method` 两种接口,前者是 C++ 导出,后者是 JavaScript 包装
3. **可选参数**: 广泛使用可选参数和默认值,提供灵活性
4. **类型转换**: 自动处理数组、TypedArray、malloced 对象等多种输入类型
5. **闭包保护**: 使用闭包保护内部状态,避免外部污染

## 性能考量

### 内存优化
1. **预分配缓冲区**: 避免频繁分配小块内存
2. **用户可提供输出数组**: 允许调用者提供输出缓冲区,减少分配
3. **及时释放**: 使用 `freeArraysThatAreNotMallocedByUsers` 及时释放临时内存

### 调用优化
1. **批量操作**: `drawAtlas`、`drawVertices` 等支持批量绘制
2. **快速路径**: `quickReject` 提供快速裁剪判断
3. **缓存画布**: Surface 缓存 Canvas 对象避免重复创建

### 数据传递优化
1. **直接指针操作**: 使用指针直接操作 WASM 内存
2. **避免中间复制**: 支持 malloced 对象直接传递
3. **TypedArray**: 使用 TypedArray 提高数据传递效率

### 渲染优化
1. **dirtyRect 支持**: `requestAnimationFrame` 和 `drawOnce` 支持脏矩形优化
2. **图层合成**: `saveLayer` 支持高效的图层合成
3. **采样控制**: 提供多种采样方式平衡质量和性能

## 相关文件

- **modules/canvaskit/memory.js**: 内存管理辅助函数
- **modules/canvaskit/matrix.js**: 矩阵操作函数
- **modules/canvaskit/paragraph.js**: 段落文本功能
- **modules/canvaskit/skottie.js**: Lottie 动画支持
- **modules/canvaskit/webgl.js**: WebGL 后端支持
- **modules/canvaskit/webgpu.js**: WebGPU 后端支持
- **modules/canvaskit/htmlcanvas/**: HTML Canvas 兼容层
- **modules/canvaskit/canvaskit_bindings.cpp**: C++ WASM 绑定源文件
