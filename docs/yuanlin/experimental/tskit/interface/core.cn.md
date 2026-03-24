# Core 模块

> 源文件: experimental/tskit/interface/core.ts

## 概述

`Core` 模块是 TSKit 框架中的核心功能实现层,负责将 C++ 层的核心绑定函数封装为用户友好的公共 API。该模块展示了如何在 TypeScript 中扩展和包装 Emscripten 生成的绑定代码,为开发者提供更符合 JavaScript/TypeScript 习惯的接口设计。

模块的主要职责包括:
1. 封装核心功能函数,添加控制台日志和错误处理
2. 扩展类原型方法,实现参数预处理和业务逻辑
3. 在运行时初始化完成后注册所有公共 API

这个模块体现了跨语言 API 设计的最佳实践,特别是如何在保持底层性能的同时,提供开发者友好的高层接口。

## 架构位置

`Core` 模块位于 TSKit 框架的接口层,与 `Extension` 模块并列,共同构成公共 API 的实现基础:

```
experimental/tskit/
├── interface/
│   ├── load.ts          # 提供运行时初始化机制
│   ├── core.ts          # 核心功能封装(当前模块)
│   ├── extension.ts     # 扩展功能封装
│   ├── memory.ts        # 内存管理工具
│   └── public_api.d.ts  # 公共 API 类型定义
├── bindings/
│   ├── core.d.ts        # C++ 核心绑定的类型声明
│   ├── core.cpp         # C++ 核心绑定的实现
│   └── embind.d.ts      # Emscripten 基础类型
└── npm_build/
    └── types/           # 最终发布的类型定义
```

**模块职责划分:**
```
Core 模块 → 核心功能 (sayHello, Something 类扩展)
Extension 模块 → 扩展功能 (publicExtension, withObject)
```

## 主要类与结构体

### namespace Core

`Core` 命名空间封装了所有核心功能的实现逻辑。

**外部依赖声明:**
- `Module: core.Bindings`: C++ 核心绑定对象,提供私有函数接口
- `CanvasKit: public_api.CanvasKit`: 公共 API 对象,用于挂载公共方法

### 涉及的类型

模块操作以下类型(来自 `public_api.d.ts`):
- `CanvasKit`: 全局 API 对象接口
- `Something`: 通过 Emscripten 暴露的 C++ 类

## 公共 API 函数

### CanvasKit.sayHello(x: number, y: number): void

调用底层 C++ 函数进行计算,并将结果输出到控制台。

**参数:**
- `x`: 第一个数值参数
- `y`: 第二个数值参数

**返回值:**
- `void`: 无返回值,结果通过 `console.log` 输出

**实现逻辑:**
```typescript
CanvasKit.sayHello = (x: number, y: number) => {
  console.log('hello', Module._privateFunction(x, y));
};
```

**功能说明:**
1. 调用 C++ 的 `_privateFunction` 计算 `x` 和 `y` 的某种组合
2. 将结果与字符串 `'hello'` 一起输出到控制台
3. 提供简单的调试和示例功能

**设计考量:**
- 使用箭头函数保持 `this` 绑定清晰
- 直接访问 `Module` 的私有函数
- 通过控制台输出而非返回值,简化接口

### CanvasKit.Something.prototype.setName(name: string): void

扩展 `Something` 类的原型,实现自定义的 `setName` 方法。

**参数:**
- `name`: 要设置的名称字符串

**返回值:**
- `void`: 无返回值

**实现逻辑:**
```typescript
CanvasKit.Something.prototype.setName = function setName(name: string) {
  this._setName(name + name);
};
```

**功能说明:**
1. 将输入的 `name` 字符串重复两次 (`name + name`)
2. 调用底层的 `_setName` 方法设置处理后的名称
3. 使用 `function` 声明保持 `this` 的正确绑定

**设计特点:**
- 覆盖或扩展 Emscripten 生成的原始方法
- 添加业务逻辑(重复名称)
- 保持与 C++ 对象的交互

**注意事项:**
- 使用 `function` 关键字而非箭头函数,确保 `this` 指向实例
- 方法名 `setName` 在函数表达式中重复声明,有助于调试

## 内部实现细节

### 初始化时序

所有公共 API 的绑定都在 `load.afterLoad` 回调中完成:
```typescript
load.afterLoad(() => {
  // 注册 sayHello 函数
  CanvasKit.sayHello = ...;

  // 扩展 Something 类的原型
  CanvasKit.Something.prototype.setName = ...;
});
```

**执行流程:**
1. Emscripten 加载并初始化 WebAssembly 模块
2. `load.ts` 触发 `onRuntimeInitialized` 事件
3. `Core` 模块的回调被执行
4. 公共 API 被挂载到 `CanvasKit` 对象上

### 私有函数调用

`Module._privateFunction` 是 C++ 层导出的私有函数:
- 函数名以 `_` 开头,表示内部使用
- 不直接暴露给最终用户
- 通过 TypeScript 包装层调用

**调用栈:**
```
用户调用 CanvasKit.sayHello(x, y)
    ↓
console.log('hello', Module._privateFunction(x, y))
    ↓
WebAssembly 函数调用
    ↓
C++ 实现 (_privateFunction)
    ↓
返回计算结果
```

### 原型方法扩展

扩展 `Something` 类的原型方法需要特殊处理:
```typescript
CanvasKit.Something.prototype.setName = function setName(name: string) {
  this._setName(name + name);
};
```

**关键点:**
1. **使用 `function` 声明**: 箭头函数会捕获外部的 `this`,导致错误
2. **访问私有方法**: `this._setName` 是 C++ 层暴露的私有方法
3. **参数预处理**: 在调用底层方法前修改参数(`name + name`)

### 函数声明 vs 箭头函数

模块中使用了两种函数声明方式:
```typescript
// 箭头函数 - 用于模块级函数
CanvasKit.sayHello = (x: number, y: number) => { ... };

// 函数表达式 - 用于原型方法
CanvasKit.Something.prototype.setName = function setName(name: string) { ... };
```

**选择原因:**
- 箭头函数: `this` 绑定到定义时的上下文,适合不依赖实例的函数
- 函数表达式: `this` 绑定到调用时的实例,适合类方法

## 依赖关系

### 依赖的模块

1. **load.ts**
   - 提供 `load.afterLoad` 函数
   - 确保运行时初始化完成后才注册 API

2. **core.d.ts**
   - 声明 `core.Bindings` 接口
   - 定义 C++ 私有函数的类型签名 (`_privateFunction`, `_setName`)

3. **public_api.d.ts**
   - 定义公共 API 的类型
   - 声明 `CanvasKit` 接口和 `Something` 类

### 被依赖的模块

- 最终的 npm 包会包含这些 API
- 用户代码通过 `CanvasKit` 全局对象调用

### 依赖图

```
embind.d.ts
    ↓
load.ts → Core.ts
    ↓       ↓
public_api.d.ts
    ↓
core.d.ts (C++ 绑定)
    ↓
core.cpp
```

## 设计模式与设计决策

### 1. 装饰器模式 (Decorator Pattern)

`sayHello` 函数装饰了底层的 `_privateFunction`:
- 保留原始功能(计算 x 和 y)
- 添加新功能(控制台输出)
- 不修改底层实现

### 2. 模板方法模式 (Template Method Pattern)

`setName` 方法定义了一个算法骨架:
1. 预处理输入参数(`name + name`)
2. 调用底层方法(`this._setName`)
3. 可扩展为添加后处理逻辑

### 3. 外观模式 (Facade Pattern)

模块为底层 C++ 函数提供了简化的外观:
- 隐藏 `Module` 对象的直接访问
- 提供语义化的函数名
- 统一错误处理和日志记录

### 4. 适配器模式 (Adapter Pattern)

将 C++ 的命名和调用约定适配为 JavaScript 风格:
- C++ 的 `_privateFunction` → JavaScript 的 `sayHello`
- C++ 的 `_setName` → JavaScript 的 `setName`(带预处理)

### 5. 命名约定

- **私有函数**: 以 `_` 开头(如 `_privateFunction`, `_setName`)
- **公共函数**: 无前缀(如 `sayHello`, `setName`)
- **清晰的访问控制**: 私有/公共界限明确

### 6. 参数预处理策略

在调用底层方法前处理参数:
```typescript
this._setName(name + name);  // 预处理: 重复名称
```
- 在 JavaScript 层处理,避免修改 C++ 代码
- 灵活性高,易于调试和测试
- 适合添加验证和转换逻辑

## 性能考量

### 1. 函数调用开销

**JavaScript → WebAssembly 调用:**
- `sayHello` 的调用链: JS → Module._privateFunction → WASM
- 每次跨边界调用有固定开销(~10-50ns)
- 对于简单计算,调用开销可能超过计算成本

**优化策略:**
- 批处理多个操作,减少调用次数
- 对于频繁调用的函数,考虑在 WASM 中实现更多逻辑

### 2. 字符串操作开销

`setName` 中的字符串拼接:
```typescript
this._setName(name + name);
```
- 时间复杂度: O(n),n 为字符串长度
- 内存分配: 创建新字符串对象
- 对于短字符串(<1000字符),开销可忽略
- 对于长字符串或频繁调用,考虑在 C++ 层实现

### 3. 控制台输出开销

```typescript
console.log('hello', Module._privateFunction(x, y));
```
- `console.log` 在某些浏览器中较慢(尤其是开发者工具打开时)
- 生产环境中应移除或使用条件编译
- 考虑使用性能更好的日志库

### 4. 原型方法查找

```typescript
CanvasKit.Something.prototype.setName = ...;
```
- 原型方法查找的时间复杂度: O(1)(哈希表)
- 扩展原型不影响已创建的实例
- 每次调用时都会进行原型链查找

### 5. 函数声明性能差异

箭头函数 vs 函数表达式:
- 性能差异极小(现代 JavaScript 引擎优化良好)
- 主要考虑 `this` 绑定的正确性
- 不应该成为性能瓶颈

### 6. 内存占用

- 每个函数对象占用约 40-80 字节
- 原型方法被所有实例共享,节省内存
- 闭包可能捕获外部变量,影响垃圾回收

## 相关文件

1. **experimental/tskit/interface/load.ts**
   - 提供 `load.afterLoad` 函数注册初始化逻辑
   - 管理运行时初始化生命周期

2. **experimental/tskit/interface/public_api.d.ts**
   - 定义 `CanvasKit` 接口
   - 声明 `Something` 类的公共接口
   - 包含 `sayHello` 和 `setName` 的类型签名

3. **experimental/tskit/bindings/core.d.ts**
   - 声明 `core.Bindings` 接口
   - 定义 `_privateFunction` 的类型: `(x: number, y: number) => number`
   - 定义 `_setName` 的类型: `(name: string) => void`

4. **experimental/tskit/bindings/core.cpp**
   - 实现 `_privateFunction` 的 C++ 逻辑
   - 实现 `Something` 类及其 `_setName` 方法
   - 使用 Emscripten 的 `class_` 和 `function` 绑定

5. **experimental/tskit/bindings/embind.d.ts**
   - 定义 Emscripten 的基础类型
   - 声明 `EmbindModule` 接口

6. **experimental/tskit/interface/extension.ts**
   - 类似的扩展功能模块
   - 展示不同的封装模式

7. **experimental/tskit/npm_build/types/index.d.ts**
   - 最终发布的类型定义文件
   - 包含所有公共 API 的声明
   - 用户代码的类型检查依据
