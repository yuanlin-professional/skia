# Pattern 图案填充

> 源文件: modules/canvaskit/htmlcanvas/pattern.js

## 概述

`pattern.js` 实现了 HTML Canvas 的 `CanvasPattern` 对象,用于创建基于图像的重复图案填充。该对象可以配置不同的重复模式(repeat, repeat-x, repeat-y, no-repeat),并支持变换矩阵,是 Canvas API 中实现纹理填充的核心组件。

## 架构位置

该文件位于 CanvasKit 的 HTML Canvas 兼容层,与渐变对象同级,都是 CanvasRenderingContext2D 可用的填充样式。

## 主要类与结构体

### CanvasPattern 类

**构造函数**:
```javascript
function CanvasPattern(image, repetition)
```

**内部字段**:
- `_shader`: CanvasKit.Shader 对象,实际渲染使用
- `_image`: 源图像(SkImage 或 HTMLImage)
- `_transform`: 3x3 变换矩阵
- `_tileX/Y`: 水平/垂直平铺模式

**重复模式映射**:
- `'repeat'`: TileMode.Repeat × Repeat
- `'repeat-x'`: TileMode.Repeat × Decal
- `'repeat-y'`: TileMode.Decal × Repeat
- `'no-repeat'`: TileMode.Decal × Decal

## 公共 API 函数

### setTransform(m)
设置图案的变换矩阵。

**参数**:
- `m`: DOMMatrix 对象 `{a, b, c, d, e, f}`

**变换格式**:
```javascript
[a, c, e]
[b, d, f]
[0, 0, 1]
```

### _getShader(currentTransform)
生成用于渲染的着色器(内部方法)。

**特点**:
- 使用 Cubic 采样(高质量)
- 每次调用重新生成,释放旧着色器
- 应用预设的变换矩阵

## 内部实现细节

### TileMode 选择
使用 `Decal` 而非 `Clamp` 用于非重复方向:
```javascript
// Decal: 边界外透明
// Clamp: 边界外重复最后一行/列(会看起来很奇怪)
this._tileY = CanvasKit.TileMode.Decal;
```

### 图像包装处理
```javascript
if (image instanceof HTMLImage) {
  image = image.getSkImage();
}
```

### 高质量采样
使用 Cubic Resampler:
```javascript
this._shader = this._image.makeShaderCubic(
  this._tileX, this._tileY,
  1/3, 1/3,  // Mitchell-Netravali 参数
  this._transform
);
```

## 设计模式与设计决策

### 懒加载着色器
着色器在实际使用时才生成,节省资源。

### 资源管理
`_dispose` 方法确保旧着色器被释放,防止内存泄漏。

### 不可变性
变换矩阵设置后固定,简化并发处理。

## 性能考量

- **Cubic 采样**: 质量高但稍慢,适合静态图案
- **着色器缓存**: 每次调用 `_getShader` 重建,适合动态变换
- **内存占用**: 每个 Pattern 约几十字节 + 着色器开销

## 相关文件

- **modules/canvaskit/htmlcanvas/lineargradient.js**: 线性渐变实现
- **modules/canvaskit/htmlcanvas/radialgradient.js**: 径向渐变实现
- **modules/canvaskit/interface.js**: Shader API
