# load 模块

> 源文件: experimental/tskit/interface/load.ts

## 概述

`load` 模块是 TSKit 实验性框架中负责管理运行时初始化的核心模块。它提供了一个回调注册机制,允许其他模块在 Emscripten 运行时完全初始化后执行特定的初始化逻辑。该模块通过拦截 `Module.onRuntimeInitialized` 事件,确保所有依赖 WebAssembly 模块的代码都能在正确的时机执行。

这个模块的设计体现了异步初始化的最佳实践,特别是在 WebAssembly 环境中,模块加载和初始化是异步的,需要一个集中的协调机制来管理依赖关系。

## 架构位置

在 TSKit 框架中,`load` 模块处于基础设施层,是整个系统启动流程的关键组件:

```
experimental/tskit/
├── interface/
│   ├── load.ts          # 运行时初始化管理器
│   ├── core.ts          # 依赖 load 模块进行初始化
│   ├── extension.ts     # 依赖 load 模块进行初始化
│   ├── memory.ts        # 内存管理工具
│   └── public_api.d.ts  # 公共 API 类型定义
├── bindings/
│   ├── embind.d.ts      # Emscripten 绑定类型
│   └── *.cpp            # C++ 绑定实现
└── npm_build/
    └── types/           # 构建输出的类型定义
```

`load` 模块是其他所有接口模块的依赖基础,确保在 Emscripten 运行时准备就绪后才执行绑定代码。

## 主要类与结构体

### namespace load

`load` 命名空间封装了所有运行时初始化相关的功能。

**类型定义:**
- `CallbackFn`: 回调函数类型,定义为无参数无返回值的函数 `() => void`

**内部状态:**
- `toLoad: CallbackFn[]`: 存储所有待执行的回调函数的数组

### 全局声明

- `Module: embind.EmbindModule`: 指向 Emscripten 生成的模块对象
- `CanvasKit`: `Module` 的别名,用于其他文件声明公共 API

## 公共 API 函数

### load.afterLoad(callback: CallbackFn): void

注册一个在运行时初始化完成后执行的回调函数。

**参数:**
- `callback`: 要执行的回调函数,类型为 `CallbackFn`

**功能:**
- 将回调函数添加到内部的 `toLoad` 数组中
- 当 Emscripten 运行时初始化完成时,所有注册的回调会被依次执行

**使用示例:**
```typescript
load.afterLoad(() => {
  // 在这里可以安全地访问 WASM 模块的功能
  console.log('Runtime is ready');
});
```

**设计特点:**
- 简单的注册机制,无需关心运行时的具体状态
- 支持多次调用,所有回调会按注册顺序执行
- 保证在 WebAssembly 模块完全加载后才执行业务逻辑

## 内部实现细节

### 运行时初始化机制

模块通过覆盖 `Module.onRuntimeInitialized` 钩子来实现初始化控制:

```typescript
Module.onRuntimeInitialized = () => {
  console.log('runtime initialized');
  toLoad.forEach(((callback) => callback()));
};
```

**执行流程:**
1. Emscripten 加载并初始化 WebAssembly 模块
2. 初始化完成后,Emscripten 调用 `Module.onRuntimeInitialized`
3. 该钩子函数输出日志并遍历 `toLoad` 数组
4. 依次执行所有已注册的回调函数

**关键设计决策:**
- 使用数组存储回调,保证执行顺序的确定性
- 直接覆盖 `onRuntimeInitialized` 而非链式调用,简化逻辑
- 在回调执行前输出日志,便于调试和监控

### 回调存储机制

`toLoad` 数组采用简单的追加模式:
- 每次调用 `afterLoad` 时,回调被 push 到数组末尾
- 不进行去重或验证,允许相同的回调多次注册
- 执行时使用 `forEach`,确保所有回调都有机会执行
- 即使某个回调抛出异常,后续回调仍会继续执行

## 依赖关系

### 依赖的外部类型

- `embind.EmbindModule`: 来自 `../bindings/embind.d.ts`,定义了 Emscripten 模块的接口

### 被依赖的模块

`load` 模块被以下模块引用:
- `core.ts`: 使用 `load.afterLoad` 注册核心功能的初始化逻辑
- `extension.ts`: 使用 `load.afterLoad` 注册扩展功能的初始化逻辑

### 依赖图

```
embind.d.ts (Emscripten 类型)
    ↓
load.ts (运行时初始化管理)
    ↓
├── core.ts (核心 API 初始化)
└── extension.ts (扩展 API 初始化)
```

## 设计模式与设计决策

### 1. 观察者模式 (Observer Pattern)

`load` 模块实现了简化的观察者模式:
- **主题 (Subject)**: Emscripten 运行时
- **观察者 (Observer)**: 通过 `afterLoad` 注册的回调函数
- **通知机制**: `Module.onRuntimeInitialized` 钩子

这种模式解耦了运行时初始化和业务逻辑,各个模块可以独立注册自己的初始化代码。

### 2. 命名空间模式

使用 TypeScript 的 `namespace` 而非 ES6 模块:
- 适配 Emscripten 的全局变量模式
- 简化与 C++ 绑定代码的集成
- 避免模块加载顺序问题

### 3. 单一职责原则

模块职责清晰,仅负责运行时初始化的协调:
- 不涉及具体的业务逻辑
- 不处理内存管理或 API 绑定
- 专注于生命周期管理

### 4. 全局别名设计

通过 `const CanvasKit = Module` 创建别名:
- 提供更语义化的命名
- 允许其他文件使用 `CanvasKit` 声明公共 API
- 保持与 Skia 项目的命名一致性

## 性能考量

### 1. 回调执行效率

- 使用简单的数组遍历,时间复杂度 O(n)
- 对于少量回调(<100个),性能影响可忽略
- 不使用异步执行,避免引入额外的调度开销

### 2. 内存占用

- 每个回调函数引用约占用 8 字节
- `toLoad` 数组本身的内存开销很小
- 回调执行后,闭包引用的变量可能影响垃圾回收

### 3. 初始化时序

- 所有回调在单个事件循环中同步执行
- 对于耗时的初始化操作,可能阻塞主线程
- 建议将复杂的初始化逻辑拆分为异步操作

### 4. 调试支持

- `console.log('runtime initialized')` 提供了清晰的时序标记
- 帮助开发者定位加载相关的问题
- 在生产环境中可以移除以减少日志输出

## 相关文件

1. **experimental/tskit/bindings/embind.d.ts**
   - 定义 `EmbindModule` 接口
   - 声明 `onRuntimeInitialized` 钩子的类型

2. **experimental/tskit/interface/core.ts**
   - 使用 `load.afterLoad` 注册核心 API 的初始化逻辑
   - 示例:绑定 `sayHello` 和 `Something.prototype.setName`

3. **experimental/tskit/interface/extension.ts**
   - 使用 `load.afterLoad` 注册扩展 API 的初始化逻辑
   - 示例:绑定 `publicExtension` 和 `withObject`

4. **experimental/tskit/interface/memory.ts**
   - 提供内存管理工具
   - 被 extension.ts 等模块使用

5. **experimental/tskit/interface/public_api.d.ts**
   - 定义公共 API 的 TypeScript 类型
   - 声明 `CanvasKit` 接口

6. **experimental/tskit/bindings/core.cpp**
   - 实现核心功能的 C++ 绑定
   - 通过 Emscripten 导出供 TypeScript 调用

7. **experimental/tskit/bindings/extension.cpp**
   - 实现扩展功能的 C++ 绑定
   - 提供 `_privateExtension` 等底层函数
