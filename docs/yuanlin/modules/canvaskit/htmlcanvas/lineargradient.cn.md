# LinearGradient 线性渐变

> 源文件: modules/canvaskit/htmlcanvas/lineargradient.js

## 概述

`lineargradient.js` 实现了 HTML Canvas 的线性渐变对象 `LinearCanvasGradient`,用于创建沿直线方向的颜色渐变效果。该对象支持添加多个颜色停止点,并在渲染时根据当前变换矩阵动态生成 Skia 着色器。

## 架构位置

该文件是 CanvasKit HTMLCanvas 兼容层的渐变模块之一,与 RadialCanvasGradient 并列,作为 CanvasRenderingContext2D 的填充/描边样式使用。

## 主要类与结构体

### LinearCanvasGradient 类

**构造函数**:
```javascript
function LinearCanvasGradient(x1, y1, x2, y2)
```

定义渐变的起点 (x1, y1) 和终点 (x2, y2)。

**内部字段**:
- `_shader`: 当前着色器对象
- `_colors`: 颜色数组(Float32Array 格式)
- `_pos`: 位置数组(0-1 范围)

## 公共 API 函数

### addColorStop(offset, color)
在渐变上添加颜色停止点。

**参数**:
- `offset`: 0-1 之间的位置(0=起点,1=终点)
- `color`: CSS 颜色字符串

**行为**:
- 颜色停止点按位置排序
- 相同位置的停止点,后添加的覆盖先添加的
- offset 超出范围或非有限值时抛出异常

**实现特点**:
```javascript
// 插入排序,保持位置递增
for (idx = 0; idx < this._pos.length; idx++) {
  if (this._pos[idx] > offset) {
    break;
  }
}
this._pos.splice(idx, 0, offset);
this._colors.splice(idx, 0, color);
```

## 内部实现细节

### 动态着色器生成
`_getShader` 方法在每次渲染时调用:
```javascript
this._getShader = function(currentTransform) {
  // 1. 变换起点和终点
  var pts = [x1, y1, x2, y2];
  CanvasKit.Matrix.mapPoints(currentTransform, pts);

  // 2. 释放旧着色器
  this._dispose();

  // 3. 创建新着色器
  this._shader = CanvasKit.Shader.MakeLinearGradient(
    [sx1, sy1], [sx2, sy2],
    this._colors, this._pos,
    CanvasKit.TileMode.Clamp
  );

  return this._shader;
}
```

### 变换处理
根据 Canvas 规范,渐变点必须随当前变换矩阵变换:
```javascript
CanvasKit.Matrix.mapPoints(currentTransform, pts);
```

这确保渐变正确跟随形状的旋转、缩放等变换。

### TileMode.Clamp
使用 Clamp 模式,渐变在起点前和终点后延续边界颜色:
- 起点前: 使用第一个颜色
- 终点后: 使用最后一个颜色

### 资源管理
每次生成新着色器前释放旧的:
```javascript
this._dispose = function() {
  if (this._shader) {
    this._shader.delete();
    this._shader = null;
  }
}
```

### 复制方法
`_copy` 方法用于克隆渐变对象:
```javascript
this._copy = function() {
  var lcg = new LinearCanvasGradient(x1, y1, x2, y2);
  lcg._colors = this._colors.slice();
  lcg._pos = this._pos.slice();
  return lcg;
}
```

## 依赖关系

### 内部依赖
- **color.js**: `parseColor` 函数解析颜色字符串
- **CanvasKit.Shader.MakeLinearGradient**: Skia 渐变着色器
- **CanvasKit.Matrix.mapPoints**: 矩阵变换

### 外部使用
- **CanvasRenderingContext2D**: `createLinearGradient()` 创建实例

## 设计模式与设计决策

### 延迟生成模式
着色器在使用时才生成,支持动态变换。

### 位置排序策略
停止点按位置排序,简化 Skia 着色器的使用:
- Skia 要求位置递增
- 二分插入保持有序

### 覆盖策略
相同位置的停止点覆盖而非累积,符合规范:
> 只有第一个和最后一个会生效,中间的被忽略

## 性能考量

### 添加停止点
- **时间复杂度**: O(n),n 为已有停止点数量
- **实际开销**: 通常 n < 10,开销可忽略

### 着色器生成
- 每次绘制重新生成
- 适合动态变换场景
- 静态渐变可考虑缓存(当前未实现)

### 内存占用
- 每个渐变: ~100 字节(数组 + 元数据)
- 着色器: ~数百字节

## 相关文件

- **modules/canvaskit/htmlcanvas/radialgradient.js**: 径向渐变实现
- **modules/canvaskit/htmlcanvas/color.js**: 颜色解析
- **modules/canvaskit/interface.js**: Shader API
