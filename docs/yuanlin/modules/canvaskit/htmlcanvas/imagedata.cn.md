# ImageData

> 源文件: modules/canvaskit/htmlcanvas/imagedata.js

## 概述

`imagedata.js` 实现了符合 HTML Canvas 标准的 `ImageData` 对象,用于表示像素数据。该对象是 Canvas API 中处理像素级操作的核心数据结构,包含了图像的原始 RGBA 像素数据以及宽度和高度信息。该实现完全模拟了浏览器的 ImageData 行为,确保在 Node.js 等非浏览器环境中也能使用标准的像素操作 API。

## 架构位置

该文件位于 CanvasKit 的 HTML Canvas 兼容层:
- **上层**: 被 CanvasRenderingContext2D 的 `getImageData`/`putImageData` 使用
- **同层**: 与其他 Canvas API 对象(Path2D、Gradient 等)并列
- **下层**: 封装原生 JavaScript 数组和对象属性

作为标准 API 实现,它是纯 JavaScript 代码,不直接调用 Skia。

## 主要类与结构体

### ImageData 构造函数
创建 ImageData 对象,存储像素数据。

**内部结构**:
- `data`: Uint8ClampedArray,存储 RGBA 像素数据(只读)
- `width`: 图像宽度(只读)
- `height`: 图像高度(只读)

**构造函数签名**:
```javascript
function ImageData(arr, width, height)
```

**参数**:
- `arr`: Uint8ClampedArray,RGBA 像素数据
- `width`: 图像宽度(像素)
- `height`: 可选,图像高度(可从数组长度推导)

### CanvasKit.ImageData 工厂函数
提供两种创建 ImageData 的方式:

#### 模式 1: 创建空白 ImageData
```javascript
CanvasKit.ImageData(width, height)
```
创建指定尺寸的 ImageData,像素数据初始化为全 0(透明黑色)。

#### 模式 2: 从数据创建 ImageData
```javascript
CanvasKit.ImageData(arr, width, height)
```
使用提供的像素数据创建 ImageData。

## 公共 API 函数

### CanvasKit.ImageData(...)
多态工厂函数,根据参数数量创建 ImageData。

**重载 1: ImageData(width, height)**
- **参数**:
  - `width`: 整数,图像宽度
  - `height`: 整数,图像高度
- **返回**: 新的 ImageData 对象,像素数据全为 0
- **字节长度**: `4 * width * height`(每像素 4 字节 RGBA)

**重载 2: ImageData(arr, width, height)**
- **参数**:
  - `arr`: Uint8ClampedArray,像素数据
  - `width`: 整数,图像宽度
  - `height`: 可选,图像高度
- **返回**: 新的 ImageData 对象
- **验证**: 检查数组类型、长度、对齐等

**异常**:
- `TypeError`: 参数数量不是 2 或 3
- `TypeError`: 数组不是 Uint8ClampedArray
- `TypeError`: 数组长度不是 4 的倍数
- `TypeError`: 数组长度不能被 width 整除
- `TypeError`: height 与计算值不匹配

### ImageData 实例属性

#### data (只读)
Uint8ClampedArray,包含 RGBA 像素数据。
- **格式**: [R0, G0, B0, A0, R1, G1, B1, A1, ...]
- **范围**: 每个分量 0-255
- **顺序**: 从左到右,从上到下

#### width (只读)
整数,图像宽度(像素)。

#### height (只读)
整数,图像高度(像素)。

## 内部实现细节

### 属性保护
使用 `Object.defineProperty` 定义只读属性:
```javascript
Object.defineProperty(this, 'data', {
  value: arr,
  writable: false
});
```

这确保了 `data`、`width`、`height` 属性符合标准,不可被重新赋值(但 `data` 数组内容可修改)。

### 高度推导
如果未提供 height,从数组长度自动计算:
```javascript
height = height || arr.length/(4*width);
```

这符合 Canvas 标准,允许省略高度参数。

### 严格类型检查
工厂函数进行严格的类型和尺寸验证:
```javascript
if (arr.prototype.constructor !== Uint8ClampedArray) {
  throw new TypeError('bytes must be given as a Uint8ClampedArray');
}
if (arr % 4) {
  throw new TypeError('bytes must be given in a multiple of 4');
}
```

### 参数验证顺序
1. 检查参数数量
2. 检查宽高有效性(非零)
3. 检查数组长度和对齐
4. 检查宽度整除性
5. 检查高度匹配

这种顺序确保了错误信息的准确性。

## 依赖关系

### 内部依赖
无依赖,纯 JavaScript 实现。

### 外部使用
- **CanvasRenderingContext2D**:
  - `getImageData()` 返回 ImageData
  - `putImageData()` 接受 ImageData
  - `createImageData()` 创建 ImageData
- **应用代码**: 直接操作像素数据

## 设计模式与设计决策

### 1. 工厂模式
`CanvasKit.ImageData` 是工厂函数,隐藏了构造函数的复杂性:
```javascript
CanvasKit.ImageData = function() {
  if (arguments.length === 2) {
    // 创建空白
  } else if (arguments.length === 3) {
    // 从数据创建
  } else {
    throw new TypeError('invalid number of arguments');
  }
}
```

### 2. 不可变性(部分)
属性本身不可变,但数组内容可修改:
- `imageData.width = 100;` // 失败
- `imageData.data[0] = 255;` // 成功

这符合标准:尺寸不变,但像素可修改。

### 3. 防御性编程
多层验证确保数据完整性:
- 类型检查
- 长度检查
- 对齐检查
- 一致性检查

### 设计决策

**为什么使用 Uint8ClampedArray**:
Canvas 标准要求使用 Uint8ClampedArray,因为:
1. 自动箝位到 0-255 范围
2. 符合颜色值的语义
3. 与浏览器行为一致

**为什么属性只读**:
防止意外修改尺寸,导致数据与尺寸不匹配:
```javascript
// 如果允许修改:
imageData.width = 10; // 数据长度不变,但宽度变了
// 会导致访问越界或数据解释错误
```

**为什么严格验证**:
提前发现错误,避免难以调试的渲染问题:
- 错误的尺寸导致图像畸变
- 错误的对齐导致颜色错误
- 类型错误导致不可预测的行为

## 性能考量

### 内存布局
- **紧凑存储**: RGBA 连续存储,缓存友好
- **无额外开销**: 直接存储原始数组,无包装
- **内存大小**: `4 * width * height` 字节

### 访问性能
- **直接数组访问**: `data[i]` 是最快的访问方式
- **无边界检查**: Uint8ClampedArray 由 JavaScript 引擎优化
- **自动箝位**: Uint8ClampedArray 的写入自动箝位,无需手动检查

### 创建性能
- **空白创建**: O(n) 填充零
- **数据创建**: O(1) 引用传递(无复制)

### 使用建议
1. **批量操作**: 使用循环批量修改像素,避免逐像素调用
2. **避免频繁创建**: 复用 ImageData 对象
3. **使用 TypedArray**: 直接操作 `data` 数组比调用 API 快

## 相关文件

- **modules/canvaskit/htmlcanvas/canvasrenderingcontext2d.js**: 使用 ImageData 的上下文方法
- **W3C Canvas 2D Context 规范**: ImageData 的标准定义
