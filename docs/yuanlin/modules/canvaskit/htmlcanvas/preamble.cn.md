# Preamble 前导代码

> 源文件: modules/canvaskit/htmlcanvas/preamble.js

## 概述

`preamble.js` 是 CanvasKit HTMLCanvas 模块的前导文件,用于建立模块作用域并初始化测试接口。该文件包含约 17 行代码,主要作用是创建一个匿名函数作用域,以便将所有 htmlcanvas 相关的 JavaScript 代码隔离在同一作用域内,避免全局命名空间污染。

## 架构位置

该文件是 htmlcanvas 模块的开始标记:
- **编译顺序**: 最先被包含
- **作用范围**: 与 postamble.js 配对,形成闭包
- **下层**: 定义模块内共享的命名空间

## 主要类与结构体

### CanvasKit._testing 对象
用于暴露内部函数以供单元测试使用:
```javascript
CanvasKit._testing = {};
```

即使在压缩版本中,`_testing` 命名空间也会保留,方便测试访问内部实现。

## 公共 API 函数

无公共 API,仅建立作用域。

## 内部实现细节

### 作用域创建
```javascript
(function() {
  // 所有 htmlcanvas 代码在此作用域内
```

这个立即执行函数表达式(IIFE)确保:
1. 变量不泄漏到全局作用域
2. 所有模块文件共享相同作用域
3. 模拟 C++ 命名空间效果

### 构建流程
编译时,构建系统按以下顺序连接文件:
1. preamble.js(开启作用域)
2. color.js, font.js, path2d.js 等(模块实现)
3. postamble.js(关闭作用域)

最终生成单个连续的作用域。

## 设计模式与设计决策

### 模块模式
使用 IIFE 实现模块化:
- 封装内部实现
- 暴露选定的 API
- 避免命名冲突

### 测试友好设计
`_testing` 命名空间允许白盒测试:
```javascript
CanvasKit._testing['parseColor'] = parseColor;
```

这样测试代码可以访问 `CanvasKit._testing.parseColor`,但普通用户不会误用。

## 性能考量

- **零运行时开销**: IIFE 仅在加载时执行一次
- **压缩友好**: 闭包内的变量可被压缩器重命名

## 相关文件

- **modules/canvaskit/htmlcanvas/postamble.js**: 闭合作用域
- **modules/canvaskit/htmlcanvas/*.js**: 作用域内的所有模块文件
