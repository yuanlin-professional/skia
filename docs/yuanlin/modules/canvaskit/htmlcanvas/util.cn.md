# Util 工具函数

> 源文件: modules/canvaskit/htmlcanvas/util.js

## 概述

`util.js` 提供了一组通用的 JavaScript 工具函数,用于支持 CanvasKit 的 HTML Canvas 兼容层。该文件包含参数验证、数据转换等基础功能,虽然代码量小但在整个模块中被广泛使用。主要功能包括有限性检查和 Base64 编码转换。

## 架构位置

该文件是 CanvasKit HTMLCanvas 模块的基础工具层:
- **上层**: 被 htmlcanvas.js、path2d.js、gradient.js 等所有模块使用
- **同层**: 与其他工具类文件并列
- **下层**: 纯 JavaScript 实现,无外部依赖

作为通用工具库,它提供跨平台(浏览器/Node.js)的基础功能。

## 主要类与结构体

该文件不包含类定义,仅提供全局函数。

## 公共 API 函数

### allAreFinite(args)
检查数组中的所有参数是否为有限数值。

**参数**:
- `args`: 数组,包含需要检查的参数

**返回**:
- `true`: 所有参数都是有限数值或 undefined
- `false`: 存在 NaN、Infinity 或非数值参数

**用途**:
在绘图操作前验证参数有效性,避免无效值导致的渲染错误。

**实现**:
```javascript
function allAreFinite(args) {
  for (var i = 0; i < args.length; i++) {
    if (args[i] !== undefined && !Number.isFinite(args[i])) {
      return false;
    }
  }
  return true;
}
```

**使用场景**:
- 路径操作: `moveTo(x, y)` 前检查坐标
- 变换操作: 矩阵参数验证
- 几何绘制: 矩形、圆形参数验证

### toBase64String(bytes)
将字节数组转换为 Base64 编码字符串。

**参数**:
- `bytes`: Uint8Array 或类似的字节数组

**返回**:
- Base64 编码的字符串

**用途**:
主要用于 `toDataURL()` 方法,将图像字节数据转换为 Data URL。

**实现策略**:
1. **Node.js 环境**: 使用 Buffer API
   ```javascript
   return Buffer.from(bytes).toString('base64');
   ```

2. **浏览器环境**: 分块转换避免栈溢出
   ```javascript
   var CHUNK_SIZE = 0x8000; // 32KB
   var index = 0;
   var result = '';
   while (index < bytes.length) {
     slice = bytes.slice(index, Math.min(index + CHUNK_SIZE, length));
     result += String.fromCharCode.apply(null, slice);
     index += CHUNK_SIZE;
   }
   return btoa(result);
   ```

**为什么分块处理**:
直接调用 `String.fromCharCode.apply(null, bytes)` 对大数组会导致"Maximum call stack size exceeded"错误,因为参数数量有限制(通常约 65536 个)。

## 内部实现细节

### 有限性检查的宽松策略
`allAreFinite` 允许 `undefined` 值通过检查:
```javascript
if (args[i] !== undefined && !Number.isFinite(args[i]))
```

这是因为许多 Canvas API 使用可选参数,undefined 表示使用默认值。

### 环境检测
通过检测 `Buffer` 全局对象判断运行环境:
```javascript
if (typeof Buffer !== 'undefined') { // Node.js
  // ...
} else { // 浏览器
  // ...
}
```

这种简单的检测方法在大多数场景下有效,但不够健壮。更严格的检测应该检查 `Buffer.from` 方法是否存在。

### Base64 转换的性能考虑
- **Node.js**: 使用原生 Buffer API,性能最优
- **浏览器**: 分块处理虽然多次循环,但避免了栈溢出,对大图像是必需的

## 依赖关系

### 内部依赖
无内部依赖,完全独立。

### 外部使用
- **htmlcanvas.js**: `toBase64String` 用于 `toDataURL()`
- **path2d.js**: `allAreFinite` 用于路径操作参数验证
- **lineargradient.js**: `allAreFinite` 用于渐变参数验证
- **radialgradient.js**: `allAreFinite` 用于渐变参数验证
- **pattern.js**: `allAreFinite` 用于变换矩阵验证

## 设计模式与设计决策

### 纯函数设计
所有函数都是纯函数,无副作用,便于测试和理解。

### 防御性编程
`allAreFinite` 采用防御性策略,允许 undefined 但拒绝无效数值,避免 Skia 内部错误。

### 跨平台抽象
`toBase64String` 提供统一接口,内部处理平台差异:
```javascript
function toBase64String(bytes) {
  if (typeof Buffer !== 'undefined') {
    return Buffer.from(bytes).toString('base64');
  } else {
    // 浏览器实现
  }
}
```

### 设计权衡

**为什么不使用第三方库**:
保持 CanvasKit 的轻量级和零依赖特性。

**为什么允许 undefined**:
Canvas API 大量使用可选参数,严格检查会导致额外的默认值填充逻辑。

**为什么 32KB 分块**:
0x8000(32768)是经验值,平衡了性能和栈使用:
- 更小的分块: 更多循环次数,性能下降
- 更大的分块: 可能触发栈溢出

## 性能考量

### allAreFinite 性能
- **时间复杂度**: O(n),线性扫描
- **提前退出**: 遇到第一个无效值立即返回 false
- **开销**: 极小,适合频繁调用

### Base64 转换性能
- **Node.js**: 原生实现,接近 C 性能
- **浏览器**:
  - 分块循环增加少量开销
  - `String.fromCharCode.apply` 对小数组高效
  - `btoa` 是浏览器原生实现

### 内存考量
- `allAreFinite`: 无额外内存分配
- `toBase64String`:
  - Node.js: 创建一个 Buffer 对象
  - 浏览器: 创建中间字符串,内存占用约为输入的 2 倍(UTF-16)

## 相关文件

- **modules/canvaskit/htmlcanvas/htmlcanvas.js**: 使用 `toBase64String`
- **modules/canvaskit/htmlcanvas/path2d.js**: 使用 `allAreFinite`
- **modules/canvaskit/htmlcanvas/lineargradient.js**: 使用 `allAreFinite`
- **modules/canvaskit/htmlcanvas/radialgradient.js**: 使用 `allAreFinite`
- **modules/canvaskit/htmlcanvas/pattern.js**: 使用 `allAreFinite`
