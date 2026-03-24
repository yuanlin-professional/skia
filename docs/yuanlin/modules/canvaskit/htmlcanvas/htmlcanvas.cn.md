# HTMLCanvas

> 源文件: modules/canvaskit/htmlcanvas/htmlcanvas.js

## 概述

`htmlcanvas.js` 实现了 HTML Canvas API 的兼容层核心类 `HTMLCanvas`,该类封装了 CanvasKit 的 Surface 对象,提供类似浏览器 `<canvas>` 元素的接口。这使得基于标准 HTML Canvas API 编写的代码可以在 Node.js 或其他非浏览器环境中运行,通过 Skia 进行高质量渲染。

该模块是 CanvasKit 提供 HTML Canvas 兼容性的关键桥梁,它不仅包装了底层的 Skia Surface,还提供了图像解码、字体加载、Path2D 创建等辅助功能,以及将渲染结果导出为 Data URL 的能力。

## 架构位置

该文件位于 CanvasKit 的 HTML Canvas 兼容层:
- **上层**: 被应用代码调用,提供标准 Canvas API
- **同层**: 与 CanvasRenderingContext2D(在其他文件中定义)协作
- **下层**: 封装 CanvasKit.Surface 和相关 Skia 对象

作为适配器层,它将标准 Canvas API 转换为 CanvasKit/Skia 调用。

## 主要类与结构体

### HTMLCanvas 类
封装 Skia Surface 的主类,模拟浏览器 canvas 元素。

**核心字段**:
- `_surface`: 底层的 CanvasKit.Surface 对象
- `_context`: CanvasRenderingContext2D 实例
- `_toCleanup`: 需要清理的对象数组(图像、字体、路径等)

**构造函数**:
```javascript
function HTMLCanvas(skSurface) {
  this._surface = skSurface;
  this._context = new CanvasRenderingContext2D(skSurface.getCanvas());
  this._toCleanup = [];
}
```

### HTMLImage 类
内部使用的图像包装类,定义在 htmlimage.js 中,此处通过 `decodeImage` 创建。

## 公共 API 函数

### 工厂方法
**`CanvasKit.MakeCanvas(width, height)`**
- 创建指定尺寸的 HTMLCanvas 对象
- 内部创建 CanvasKit.Surface 并封装
- 返回 HTMLCanvas 实例或 null(创建失败时)

### HTMLCanvas 实例方法

#### getContext(type)
获取渲染上下文,模拟标准 Canvas API。
- **参数**:
  - `type`: 上下文类型,目前仅支持 `'2d'`
- **返回**: CanvasRenderingContext2D 实例或 null
- **用途**: 这是获取绘图接口的标准入口

#### decodeImage(data)
解码图像数据并创建可用于绘制的图像对象。
- **参数**:
  - `data`: ArrayBuffer、TypedArray 或 Node Buffer
- **返回**: HTMLImage 实例
- **异常**: 输入无效时抛出 'Invalid input'
- **内存管理**: 自动将图像添加到 `_toCleanup` 数组

#### loadFont(buffer, descriptors)
加载字体文件到字体缓存。
- **参数**:
  - `buffer`: 字体文件的二进制数据
  - `descriptors`: 字体描述符对象(family, style, weight, variant)
- **返回**: 成功返回 undefined,失败返回 null
- **副作用**: 将字体添加到全局字体缓存

#### makePath2D(path)
创建 Path2D 对象。
- **参数**:
  - `path`: 可选的路径字符串或 Path2D 对象
- **返回**: Path2D 实例
- **内存管理**: 自动将路径添加到 `_toCleanup` 数组

#### toDataURL(codec, quality)
将画布内容导出为 Data URL。
- **参数**:
  - `codec`: 可选,编解码器类型(`'image/png'` 或 `'image/jpeg'`),默认 PNG
  - `quality`: 可选,JPEG 质量(0-1),默认 0.92
- **返回**: Data URL 字符串(`data:image/png;base64,...`)
- **过程**: flush → 截图 → 编码 → Base64 转换

#### dispose()
释放所有资源。
- **清理顺序**:
  1. 释放渲染上下文
  2. 删除所有跟踪的对象(图像、字体、路径)
  3. 释放底层 Surface
- **重要性**: 避免内存泄漏,必须在不再使用时调用

## 内部实现细节

### 资源跟踪机制
使用 `_toCleanup` 数组跟踪所有创建的 Skia 对象:
```javascript
this.decodeImage = function(data) {
  var img = CanvasKit.MakeImageFromEncoded(data);
  if (!img) {
    throw 'Invalid input';
  }
  this._toCleanup.push(img);  // 跟踪以便后续清理
  return new HTMLImage(img);
};
```

这确保了当 HTMLCanvas 被释放时,所有相关资源都能被正确清理。

### Surface 刷新
`toDataURL` 方法在截图前调用 `flush()`,确保所有待处理的绘制操作都已完成:
```javascript
this._surface.flush();
var img = this._surface.makeImageSnapshot();
```

### 图像编码
支持两种图像格式:
1. **PNG**: 无损格式,默认选项
2. **JPEG**: 有损格式,支持质量参数

编码后的字节数组通过 `toBase64String` 辅助函数转换为 Base64 字符串。

### Base64 转换
- **Node.js 环境**: 使用 `Buffer.from(bytes).toString('base64')`
- **浏览器环境**: 使用 `btoa()`分块转换,避免栈溢出

### 字体管理
字体加载通过 `addToFontCache` 全局函数(定义在 font.js)将字体注册到缓存:
```javascript
this.loadFont = function(buffer, descriptors) {
  var newFont = CanvasKit.Typeface.MakeTypefaceFromData(buffer);
  if (!newFont) {
    Debug('font could not be processed', descriptors);
    return null;
  }
  this._toCleanup.push(newFont);
  addToFontCache(newFont, descriptors);
};
```

## 依赖关系

### 内部依赖
- **CanvasRenderingContext2D**: 2D 渲染上下文类(在其他文件中定义)
- **HTMLImage**: 图像包装类(htmlimage.js)
- **Path2D**: 路径对象类(path2d.js)
- **font.js**: 字体缓存管理(`addToFontCache`)
- **util.js**: 工具函数(`toBase64String`)
- **CanvasKit 核心**: Surface、Typeface、Image 等

### 外部使用
- **应用代码**: 通过 `CanvasKit.MakeCanvas` 创建实例
- **测试代码**: 用于 Node.js 环境的 Canvas 功能测试

## 设计模式与设计决策

### 1. 适配器模式
HTMLCanvas 作为适配器,将标准 HTML Canvas API 适配到 CanvasKit/Skia:
```javascript
this.getContext = function(type) {
  if (type === '2d') {
    return this._context;
  }
  return null;
};
```

### 2. 代理模式
HTMLCanvas 代理对底层 Surface 的访问,提供更高级的接口。

### 3. 工厂模式
`CanvasKit.MakeCanvas` 作为工厂方法创建 HTMLCanvas 实例:
```javascript
CanvasKit.MakeCanvas = function(width, height) {
  var surf = CanvasKit.MakeSurface(width, height);
  if (surf) {
    return new HTMLCanvas(surf);
  }
  return null;
};
```

### 4. 资源管理模式
使用 `_toCleanup` 数组实现 RAII(资源获取即初始化)风格的资源管理。

### 设计决策

#### 为什么需要 HTMLCanvas?
1. **API 兼容性**: 提供标准 Canvas API,降低移植成本
2. **环境抽象**: 支持 Node.js 等非浏览器环境
3. **资源管理**: 统一管理相关资源的生命周期
4. **功能扩展**: 提供 `decodeImage`、`loadFont` 等便利方法

#### 为什么跟踪资源?
Skia 对象需要显式释放内存,通过跟踪所有创建的对象,确保:
1. 避免内存泄漏
2. 简化用户代码(无需手动跟踪每个对象)
3. 正确的清理顺序

#### 为什么限制 '2d' 上下文?
目前仅实现 2D 渲染上下文,未来可能扩展支持 WebGL、WebGPU 等其他上下文类型。

## 性能考量

### 内存效率
1. **延迟创建**: 上下文仅在构造时创建一次
2. **资源复用**: 字体加载到全局缓存,可被多个画布共享
3. **显式清理**: `dispose()` 确保及时释放资源

### 编码性能
1. **格式选择**: PNG 质量高但慢,JPEG 快但有损,用户可选择
2. **质量参数**: JPEG 质量默认 0.92,平衡质量和大小
3. **分块转换**: Base64 转换使用分块避免栈溢出

### 渲染性能
1. **直接访问**: `_context` 直接访问底层 SkCanvas
2. **批量操作**: 通过 Context2D 的方法实现批量绘制
3. **Hardware 加速**: 底层 Surface 可使用 GPU 加速

## 相关文件

- **modules/canvaskit/htmlcanvas/util.js**: 工具函数(`toBase64String`、`allAreFinite`)
- **modules/canvaskit/htmlcanvas/htmlimage.js**: HTMLImage 类定义
- **modules/canvaskit/htmlcanvas/path2d.js**: Path2D 类实现
- **modules/canvaskit/htmlcanvas/font.js**: 字体解析和缓存
- **modules/canvaskit/interface.js**: CanvasKit 核心接口
- **modules/canvaskit/canvasrenderingcontext2d.js**: 渲染上下文实现(其他文件)
