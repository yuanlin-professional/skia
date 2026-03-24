# module_uses_ck.ts

> 源文件: modules/canvaskit/external_test/typescript_browser_es6/module_uses_ck.ts

## 概述

`module_uses_ck.ts` 是 CanvasKit 的 TypeScript ES6 模块集成测试文件。该文件验证 CanvasKit 的 TypeScript 类型定义在 ES6 模块环境中的正确性,确保开发者可以在现代浏览器的 ES6 模块系统中正确导入和使用 CanvasKit,并获得完整的类型检查和自动补全支持。

这是一个最小化的测试示例,展示了如何在 TypeScript + ES6 模块项目中集成 CanvasKit。

## 架构位置

```
skia/
├── modules/
│   └── canvaskit/
│       ├── external_test/
│       │   ├── typescript_browser_es6/
│       │   │   ├── module_uses_ck.ts  # 本文件 - ES6 模块测试
│       │   │   ├── tsconfig.json      # TypeScript 配置
│       │   │   └── package.json       # 依赖配置
│       │   └── typescript_browser/
│       │       └── module_uses_ck.ts  # 非 ES6 版本
│       └── npm_build/
│           └── types/
│               └── index.d.ts         # TypeScript 类型定义
```

该文件是外部集成测试的一部分,验证 npm 包的可用性。

## 主要类与结构体

本文件不定义类或结构体,仅包含测试代码。

## 公共 API 函数

### init()

```typescript
async function init() {
    const CK = await CanvasKitInit({
        locateFile: (file: string) => __dirname + "FIXME/bin/" + file
    });
    const color = CK.Color(1,2,3,4);
    console.log(color);
}
init();
```

**功能**: 异步初始化 CanvasKit 并测试基本功能。

**流程**:
1. 调用 `CanvasKitInit` 初始化 WebAssembly 模块
2. 配置 `locateFile` 指定 WASM 文件位置
3. 创建颜色对象测试 API 可用性
4. 输出结果验证功能正常

## 内部实现细节

### ES6 模块导入

```typescript
import { CanvasKitInit } from "./node_modules/canvaskit-wasm/bin/canvaskit.js";
```

**关键点**:
- 使用 ES6 的 `import` 语法
- 直接从 `node_modules` 导入,模拟实际项目场景
- 导入的是 `.js` 文件(编译后的 JavaScript),不是 TypeScript

**类型推导**: TypeScript 编译器会自动查找对应的 `.d.ts` 文件获取类型信息。

### locateFile 配置

```typescript
locateFile: (file: string) => __dirname + "FIXME/bin/" + file
```

**用途**: 告诉 CanvasKit 在哪里找到 `.wasm` 文件。

**FIXME 标记**: 表示这是测试代码,实际项目中需要替换为正确的路径。

**__dirname**: Node.js 全局变量,表示当前模块所在目录。

### 异步初始化模式

```typescript
async function init() {
    const CK = await CanvasKitInit({...});
    // ...
}
init();
```

**设计理由**:
- WebAssembly 加载是异步的
- 使用 `async/await` 提供清晰的控制流
- 立即调用 `init()` 开始测试

### Color API 测试

```typescript
const color = CK.Color(1,2,3,4);
console.log(color);
```

**选择 Color API 的原因**:
- 简单直接,无需复杂设置
- 覆盖基本的数值参数传递
- 验证 TypeScript 类型推导正确

**预期输出**: 打包后的颜色值(32位整数)。

## 依赖关系

### npm 包依赖

**canvaskit-wasm**: CanvasKit 的 npm 包,包含:
- 编译后的 JavaScript (`canvaskit.js`)
- WebAssembly 模块 (`canvaskit.wasm`)
- TypeScript 类型定义 (`index.d.ts`)

### TypeScript 编译器

**tsconfig.json**: 配置 TypeScript 编译选项:
```json
{
  "compilerOptions": {
    "target": "ES2017",
    "module": "ES6",
    "moduleResolution": "node",
    "esModuleInterop": true
  }
}
```

**关键选项**:
- `module: "ES6"`: 输出 ES6 模块
- `esModuleInterop`: 允许与 CommonJS 模块互操作

### 浏览器支持

**ES6 模块**: 现代浏览器原生支持 `<script type="module">`。

**WebAssembly**: 所有现代浏览器都支持。

## 设计模式与设计决策

### 最小化测试

提供最简单的集成示例,降低学习曲线。

### 真实场景模拟

从 `node_modules` 导入,模拟实际项目结构。

### 类型安全验证

通过 TypeScript 编译验证类型定义的正确性:
- 编译错误会暴露类型定义问题
- IDE 自动补全验证 API 暴露正确

### FIXME 约定

使用 `FIXME` 标记需要用户自定义的部分,提供明确的指导。

## 性能考量

### 异步加载开销

WebAssembly 模块的加载和编译需要时间:
- 小型模块: < 100ms
- CanvasKit(约 1.5MB): 200-500ms

**优化**: 使用 CDN 和浏览器缓存。

### ES6 模块性能

**优点**:
- 原生浏览器支持,无需打包工具
- 静态分析,可进行 tree-shaking
- 并行加载依赖

**缺点**:
- 可能产生多次网络请求
- 不如打包的单文件快(首次加载)

### 最佳实践

1. **使用 CDN**: 加速文件下载
2. **启用缓存**: 避免重复下载
3. **延迟加载**: 只在需要时加载 CanvasKit
4. **使用 Service Worker**: 离线缓存

## 相关文件

### 对应的非 ES6 版本
- `modules/canvaskit/external_test/typescript_browser/module_uses_ck.ts` - 传统模块系统版本

### TypeScript 类型定义
- `modules/canvaskit/npm_build/types/index.d.ts` - 主类型定义文件
- `modules/canvaskit/npm_build/types/canvaskit-wasm-tests.ts` - 类型测试文件

### 配置文件
- `tsconfig.json` - TypeScript 编译配置
- `package.json` - npm 包依赖

### CanvasKit 核心
- `modules/canvaskit/npm_build/canvaskit.js` - 编译后的 JavaScript
- `modules/canvaskit/npm_build/canvaskit.wasm` - WebAssembly 模块

### 文档
- CanvasKit npm 包使用指南
- ES6 模块兼容性说明
