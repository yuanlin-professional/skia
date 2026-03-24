# module_uses_ck.ts

> 源文件: modules/canvaskit/external_test/typescript_browser/module_uses_ck.ts

## 概述

`module_uses_ck.ts` 是 CanvasKit 的 TypeScript 浏览器集成测试文件,用于验证 TypeScript 类型定义在传统模块系统(非 ES6 模块)中的正确性。该文件展示了如何在使用全局 `CanvasKitInit` 函数的项目中集成 CanvasKit 并获得完整的类型支持。

这是针对使用 `<script>` 标签直接加载 CanvasKit 的传统Web应用的集成示例,与 ES6 模块版本形成对比。

## 架构位置

```
skia/
├── modules/
│   └── canvaskit/
│       └── external_test/
│           ├── typescript_browser/
│           │   ├── module_uses_ck.ts    # 本文件 - 传统模块测试
│           │   ├── tsconfig.json        # TypeScript 配置
│           │   └── index.html           # HTML 加载页面
│           └── typescript_browser_es6/
│               └── module_uses_ck.ts    # ES6 模块版本
```

## 主要类与结构体

本文件不定义类或结构体,仅包含测试代码。

## 公共 API 函数

### init()

```typescript
async function init() {
    const CK = await CanvasKitInit({
        locateFile: (file: string) => "node_modules/canvaskit-wasm/bin/" + file
    });
    const color = CK.Color(1,2,3,4);
    console.log(color);
}
init();
```

**功能**: 初始化 CanvasKit 并测试基本 API。

## 内部实现细节

### 模块导入方式

```typescript
import {CanvasKitInit as CKInit} from "canvaskit-wasm";
```

**与 ES6 版本的区别**:
- ES6 版本: 从 `.js` 文件导入
- 本版本: 从包名导入,TypeScript 会查找类型定义

### 全局类型声明

```typescript
declare const CanvasKitInit: typeof CKInit;
```

**目的**: 声明全局 `CanvasKitInit` 函数的类型。

**背景**: 在浏览器中,CanvasKit 通过 `<script>` 标签加载时会创建全局函数 `CanvasKitInit`,但 TypeScript 不知道这个全局函数的类型。

**解决方案**: 使用 `typeof` 操作符获取导入的 `CKInit` 的类型,并声明全局 `CanvasKitInit` 具有相同的类型。

**类型安全**: 这样既能使用全局函数,又能获得完整的类型检查。

### Value Space vs Type Space

注释说明:
```typescript
// Right now, CanvasKitInit is exported from canvaskit-wasm in value space, not type space.
```

**Value Space**: 运行时的值,如函数、对象。

**Type Space**: 编译时的类型,如接口、类型别名。

**问题**: `CanvasKitInit` 是一个值,不是类型,所以不能直接在类型位置使用。

**解决**: 使用 `typeof` 将值转换为类型。

### locateFile 路径

```typescript
locateFile: (file: string) => "node_modules/canvaskit-wasm/bin/" + file
```

**与 ES6 版本的区别**:
- ES6 版本: 使用 `__dirname + "FIXME/bin/" + file`
- 本版本: 使用相对路径 `"node_modules/canvaskit-wasm/bin/" + file`

**原因**: 传统模块系统中,通常从项目根目录引用文件。

## 依赖关系

### npm 包

**canvaskit-wasm**: 同 ES6 版本。

### HTML 加载

```html
<script src="node_modules/canvaskit-wasm/bin/canvaskit.js"></script>
<script src="build/module_uses_ck.js"></script>
```

**流程**:
1. 加载 `canvaskit.js`,创建全局 `CanvasKitInit`
2. 加载编译后的测试代码
3. 测试代码调用全局 `CanvasKitInit`

### TypeScript 配置

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "module": "CommonJS"
  }
}
```

**区别**: `module: "CommonJS"` 而非 `"ES6"`。

## 设计模式与设计决策

### 类型空间和值空间分离

使用 `import` 获取类型,使用全局变量获取值:
- 编译时: TypeScript 使用导入的类型
- 运行时: JavaScript 使用全局函数

**优点**:
- 保持类型安全
- 兼容传统的全局变量模式
- 无需修改现有的 HTML 结构

### 向后兼容

支持不使用模块打包工具的项目:
- 直接使用 `<script>` 标签
- 全局命名空间
- 简单的文件结构

### TypeScript 类型提升

虽然使用全局变量,但仍然获得:
- 类型检查
- 自动补全
- 参数提示
- 重构支持

## 性能考量

### 加载方式对比

**传统方式** (本文件):
```html
<script src="canvaskit.js"></script>
```
- 阻塞式加载
- 简单直接
- 适合小型项目

**ES6 模块方式**:
```html
<script type="module" src="main.js"></script>
```
- 异步加载
- 可并行加载依赖
- 适合大型项目

### 适用场景

**选择传统方式**:
- 简单的单页面应用
- 无构建工具的项目
- 快速原型开发

**选择 ES6 模块**:
- 复杂的多页面应用
- 使用现代构建工具
- 需要代码分割和 tree-shaking

## 相关文件

### ES6 模块版本
- `modules/canvaskit/external_test/typescript_browser_es6/module_uses_ck.ts` - ES6 模块测试

### TypeScript 类型
- `modules/canvaskit/npm_build/types/index.d.ts` - 类型定义

### HTML 入口
- `index.html` - 测试页面

### 配置文件
- `tsconfig.json` - TypeScript 配置
- `package.json` - 依赖配置

### CanvasKit 核心
- `canvaskit.js` - 主文件
- `canvaskit.wasm` - WebAssembly 模块
