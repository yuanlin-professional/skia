# debug.js

> 源文件: modules/canvaskit/debug.js

## 概述

`debug.js` 是 CanvasKit 模块中用于调试支持的极简配置文件。该文件定义了调试输出函数 `Debug` 和调试模式标志 `IsDebug`,用于在开发和调试过程中输出诊断信息。这是一个编译时可选模块,只在调试构建中包含,生产构建会使用空操作(no-op)版本以减少代码体积和运行时开销。

## 架构位置

```
skia/
├── modules/
│   └── canvaskit/
│       ├── debug.js           # 本文件 - 调试构建版本
│       ├── release.js         # 生产构建版本(no-op)
│       ├── canvaskit_bindings.cpp
│       └── compile.sh         # 根据构建模式选择包含的文件
```

该文件在编译时通过 `--pre-js` 标志包含到最终的 CanvasKit 构建中,与 `release.js` 互斥。

## 主要类与结构体

本文件不包含类或结构体,仅定义全局函数和常量。

## 公共 API 函数

### Debug(msg)

**功能**: 输出调试警告消息到浏览器控制台。

**参数**:
- `msg`: string - 要输出的调试消息

**实现**:
```javascript
function Debug(msg) {
  console.warn(msg);
}
```

**使用 console.warn 的原因**:
- 在控制台中以黄色警告样式显示,更容易注意
- 不会中断程序执行(不同于 console.error)
- 可以通过浏览器的过滤器筛选

**使用示例**:
```javascript
if (!pic) {
  Debug('Could not decode picture');
  return null;
}
```

### IsDebug 常量

```javascript
/** @const */ var IsDebug = true;
```

**功能**: 编译时常量,指示当前是否为调试构建。

**用途**:
1. **条件调试代码**: 允许代码在调试和生产模式下有不同行为
2. **优化提示**: `@const` 注解告诉 Closure Compiler 这是常量,可以内联和优化
3. **特性检测**: 用户代码可以检查此标志来决定是否启用调试功能

**使用示例**:
```javascript
if (IsDebug) {
  // 只在调试模式下执行的代码
  console.log('Extra diagnostic info');
}
```

## 内部实现细节

### JSDoc 注解

```javascript
/** @const */
```

**用途**: Closure Compiler 的类型注解,表示 `IsDebug` 是常量。

**优化效果**:
- Closure Compiler 会内联常量值
- 可以进行死代码消除(DCE)
- 条件分支可以在编译时确定

**示例**:
```javascript
// 原代码
if (IsDebug) {
  expensive_debug_operation();
}

// 编译后(如果使用高级优化)
expensive_debug_operation(); // 调试构建
// 或
// 完全移除 (生产构建)
```

### console.warn vs console.log

选择 `console.warn` 而非 `console.log`:

**优点**:
1. **视觉区分**: 黄色背景,更醒目
2. **严重性指示**: 表明这是需要注意的问题
3. **堆栈跟踪**: 某些浏览器会自动包含调用堆栈
4. **过滤便利**: 可以单独过滤警告级别的消息

**缺点**:
- 可能被误认为是错误
- 在某些环境(如测试)中可能触发告警

### 构建时替换

**调试构建**:
```bash
emcc ... --pre-js debug.js ...
```

**生产构建**:
```bash
emcc ... --pre-js release.js ...
```

**release.js 内容**:
```javascript
function Debug(msg) {
  // No-op
}
/** @const */ var IsDebug = false;
```

生产构建中,`Debug` 函数为空操作,`IsDebug` 为 false,允许编译器移除所有调试代码。

## 依赖关系

### 浏览器 API

**console.warn**: 浏览器控制台 API,所有现代浏览器都支持。

### 使用此模块的代码

CanvasKit 中的多个模块使用 `Debug` 函数:
- `skp.js`: 解码失败时输出警告
- `image.js`: 图像加载失败时输出警告
- `font.js`: 字体加载问题时输出警告
- 其他各种错误处理路径

### 构建系统

**compile.sh**: 根据构建配置选择包含 `debug.js` 或 `release.js`。

**Closure Compiler**: 利用 `@const` 注解进行优化。

## 设计模式与设计决策

### 编译时多态

通过编译时包含不同的文件实现调试和生产模式的不同行为,而非运行时检查:

**优点**:
- 零运行时开销
- 生产构建中完全移除调试代码
- 减小代码体积

**缺点**:
- 需要维护两个版本
- 无法在运行时切换模式

### 全局函数模式

使用全局函数而非模块化设计:

**原因**:
- 简单直接,无需依赖注入
- 在编译过程的早期阶段可用
- 与 Emscripten 生成的代码兼容

### 约定优于配置

函数名 `Debug` 清晰表明用途,不需要额外配置或命名空间。

### 渐进式增强

调试功能是可选的增强,移除后不影响核心功能。

## 性能考量

### 生产构建优化

**零开销抽象**: 在生产构建中,所有 `Debug` 调用和 `if (IsDebug)` 分支会被 Closure Compiler 完全移除。

**示例**:
```javascript
// 源代码
if (IsDebug) {
  Debug('Loading texture: ' + name);
}
performAction();

// 生产构建(高级优化后)
performAction();
```

### 调试构建性能

**console.warn 开销**: 相对较小,但在循环中大量调用可能影响性能。

**最佳实践**: 避免在热路径中使用 Debug 输出。

### 字符串拼接优化

现代 JavaScript 引擎优化了字符串拼接,但在紧密循环中仍应避免:

```javascript
// 较好
if (IsDebug) {
  Debug('Error: ' + message);
}

// 避免在循环中
for (let i = 0; i < 1000000; i++) {
  Debug('Processing: ' + i); // 性能问题!
}
```

### 条件编译

使用 `IsDebug` 常量允许编译器进行条件编译:

```javascript
if (IsDebug) {
  validateInput(data); // 仅调试构建
}
```

生产构建中,整个 `if` 块会被移除。

## 相关文件

### 构建变体
- `modules/canvaskit/release.js` - 生产构建版本,提供 no-op 实现

### 使用 Debug 的文件
- `modules/canvaskit/skp.js` - SKP 解码错误
- `modules/canvaskit/image.js` - 图像加载错误
- `modules/canvaskit/font.js` - 字体加载错误
- `modules/canvaskit/surface.js` - Surface 创建错误
- `modules/canvaskit/canvas.js` - Canvas 操作警告

### 构建脚本
- `modules/canvaskit/compile.sh` - 编译脚本,选择调试或生产模式
- `modules/canvaskit/BUILD.bazel` - Bazel 构建规则

### 编译器配置
- Closure Compiler 配置文件
- Emscripten 编译选项

### 测试
- `modules/canvaskit/tests/debug_test.js` - 测试调试功能(如果存在)
