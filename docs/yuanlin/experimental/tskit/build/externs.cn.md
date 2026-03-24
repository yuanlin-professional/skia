# externs.js Closure 编译器外部声明

> 源文件: experimental/tskit/build/externs.js

## 概述

`externs.js` 是用于 Google Closure Compiler 的外部声明文件,定义了不应被压缩或重命名的 JavaScript 符号。在 TSKit 框架的构建过程中,Closure Compiler 用于优化和压缩 JavaScript 代码,但某些由 Emscripten 生成或需要暴露给外部的符号必须保持原始名称,这就是 externs 文件的作用。

文件的核心职责:
1. 声明 Module 对象上的所有公共和私有 API,防止被重命名
2. 声明 Emscripten 提供的底层函数(`_malloc`, `_free`, `onRuntimeInitialized`)
3. 声明类和对象的结构,确保属性名不被混淆
4. 简化的函数签名(无实际实现),仅用于类型标记

这个文件不会被执行,只是告诉 Closure Compiler:"这些名称很重要,不要改变它们。"

## 架构位置

```
experimental/tskit/
├── build/
│   └── externs.js        # Closure externs(当前文件)
├── interface/
│   ├── core.ts           # TypeScript 实现
│   └── extension.ts      # TypeScript 实现
├── bindings/
│   └── *.cpp             # C++ 绑定
└── npm_build/
    └── bundle.min.js     # 压缩后的输出(使用 externs)
```

**构建流程:**
```
TypeScript 源码
    ↓ tsc编译
JavaScript 代码
    ↓ Closure Compiler + externs.js
压缩后的 JavaScript (符号名保留)
```

## 主要类与结构体

### Module 对象

全局 Module 对象,包含所有 Emscripten 暴露的功能。

```javascript
Module.sayHello = function() {};
Module.publicFunction = function() {};
Module.publicExtension = function() {};
Module.withObject = function() {};
Module._privateFunction = function() {};
Module._privateExtension = function() {};
Module._withObject = function() {};
```

**函数类别:**
1. **公共函数**: `sayHello`, `publicFunction`, `publicExtension`, `withObject`
2. **私有函数**: `_privateFunction`, `_privateExtension`, `_withObject`

**特点:**
- 空实现 `function() {}`
- 仅声明存在性,不关心参数和返回值
- 防止 Closure Compiler 删除或重命名

### Module.Something 类

Something 类的外部声明。

```javascript
Module.Something =  {
  getName: function() {},
  prototype: {
    setName: function() {},
  },
  _setName: function() {},
};
```

**结构:**
- `getName`: 静态方法或构造函数上的方法
- `prototype.setName`: 实例方法
- `_setName`: 私有方法

**注意:**
- 这个结构可能不完全准确,但足以让 Closure Compiler 保留相关名称

### Module.CompoundObj 对象

复合对象的外部声明。

```javascript
Module.CompoundObj = {
  alpha: 0,
  beta: "",
  gamma: 0,
};
```

**字段:**
- `alpha`: 数字类型(示例值 0)
- `beta`: 字符串类型(示例值 "")
- `gamma`: 数字类型(示例值 0)

**用途:**
- 确保对象字段名不被重命名
- 保持与 TypeScript 定义的一致性

### Emscripten 函数

Emscripten 提供的底层函数。

```javascript
Module.onRuntimeInitialized = function() {};
Module._malloc = function() {};
Module._free = function() {};
```

**功能:**
1. `onRuntimeInitialized`: 运行时初始化完成的回调钩子
2. `_malloc`: 在 WASM 堆上分配内存
3. `_free`: 释放 WASM 堆上的内存

**重要性:**
- 这些函数在 Emscripten 运行时中至关重要
- 必须保持原始名称以便正确调用

## 公共 API 函数

所有声明的函数都是简化的,没有实际实现:

```javascript
Module.sayHello = function() {};
Module.publicFunction = function() {};
Module.publicExtension = function() {};
Module.withObject = function() {};
```

这些声明告诉 Closure Compiler:
- "存在这些函数"
- "不要删除对它们的引用"
- "不要将它们的名称改为 `a`, `b`, `c` 等"

## 内部实现细节

### Externs 文件的工作原理

Closure Compiler 有两种模式处理代码:
1. **内部代码**: 可以自由重命名、内联、删除
2. **外部代码**: 假设来自外部,不能修改

Externs 文件中声明的符号被视为"外部代码",编译器会:
- 保留所有引用这些符号的代码
- 不重命名这些符号
- 不删除看似未使用的声明

### 为什么需要 Externs

**问题场景:**
```javascript
// 原始代码
CanvasKit.sayHello(1, 2);

// 没有 externs,Closure Compiler 可能输出:
a.b(1, 2);  // sayHello 被重命名为 b
```

这会导致:
- JavaScript 无法找到 `b` 方法
- 运行时错误:"b is not a function"

**使用 externs 后:**
```javascript
// 有 externs,Closure Compiler 输出:
CanvasKit.sayHello(1, 2);  // 名称保留
```

### 不同于 TypeScript 类型定义

| 特性 | Externs | TypeScript Types |
|------|---------|------------------|
| 用途 | Closure Compiler | TypeScript Compiler |
| 包含类型 | 否(只有结构) | 是(完整类型) |
| 包含实现 | 否(空函数) | 否(纯声明) |
| 参数签名 | 省略 | 完整 |

**Externs 示例:**
```javascript
Module.sayHello = function() {};
```

**TypeScript 示例:**
```typescript
sayHello(x: number, y: number): void;
```

### 注释说明

```javascript
// This externs format needs to be a little different due to the fact we don't rename
// Module to CanvasKit in quite the same way.
```

**含义:**
- TSKit 使用 `Module` 作为主对象名
- 与 CanvasKit 项目的命名略有不同
- Externs 必须反映实际的运行时结构

```javascript
// Things provided by Emscripten that we don't want minified.
```

**含义:**
- `onRuntimeInitialized`, `_malloc`, `_free` 来自 Emscripten
- 这些名称是硬编码的,不能改变

## 依赖关系

### 被 Closure Compiler 使用

```bash
closure-compiler \
  --externs=experimental/tskit/build/externs.js \
  --js=output.js \
  --js_output_file=output.min.js
```

### 对应的源文件

1. **experimental/tskit/interface/core.ts**
   - 实现 `sayHello`
   - 实现 `Something` 类

2. **experimental/tskit/interface/extension.ts**
   - 实现 `publicExtension`
   - 实现 `withObject`

3. **experimental/tskit/bindings/*.cpp**
   - C++ 层实现
   - 通过 Emscripten 暴露给 JavaScript

### 依赖图

```
C++ 绑定 → Emscripten → Module.*
TypeScript 实现 → 编译 → JavaScript 代码
    ↓ Closure Compiler (使用 externs.js)
压缩的 JavaScript (符号名保留)
```

## 设计模式与设计决策

### 1. 外观模式 (Facade Pattern)

Externs 定义了一个简化的外观:
- 只声明名称,不关心实现
- 足以让编译器理解结构

### 2. 最小化原则

只声明必要的符号:
- 公共 API 函数
- 私有但被 TypeScript 代码引用的函数
- Emscripten 的关键函数

### 3. 扁平化结构

```javascript
Module.Something = {
  getName: function() {},
  prototype: { setName: function() {} },
  _setName: function() {},
};
```

- 不使用 `class` 语法
- 使用对象字面量和 `prototype`
- 更接近编译后的实际结构

### 4. 命名约定一致性

- 私有函数: `_` 前缀
- 公共函数: 无前缀
- 与 TypeScript 和 C++ 保持一致

### 5. 无类型信息

```javascript
Module.sayHello = function() {};  // 无参数,无返回值
```

- Externs 不需要类型信息
- 简化维护
- 类型检查由 TypeScript 负责

## 性能考量

### 1. 编译时性能

- Externs 文件很小(28 行)
- 解析快速,对编译时间影响可忽略

### 2. 运行时性能

- Externs 不影响运行时
- 编译后的代码与有无 externs 无关(除了符号名)

### 3. 代码大小

**保留符号名的代价:**
- 长的函数名占用更多字节
- `sayHello` vs `a`

**但是:**
- 公共 API 必须保留名称
- 内部代码仍然会被压缩
- 总体影响较小

**示例:**
```javascript
// 有 externs
Module.sayHello(x, y);  // 16 字节

// 无 externs(假设被压缩)
a.b(x, y);              // 9 字节
```

差异: 7 字节/调用

对于一个库,这个开销是可接受的。

### 4. 维护成本

**同步问题:**
- Externs 必须与实际 API 保持同步
- 添加新函数时需要更新 externs

**自动化机会:**
- 可以从 TypeScript 类型定义自动生成 externs
- 减少手动维护

## 相关文件

1. **experimental/tskit/interface/core.ts**
   - 实现 `Module.sayHello` 和 `Module.Something`

2. **experimental/tskit/interface/extension.ts**
   - 实现 `Module.publicExtension` 和 `Module.withObject`

3. **experimental/tskit/interface/public_api.d.ts**
   - TypeScript 类型定义
   - 包含完整的类型信息

4. **experimental/tskit/bindings/core.cpp**
   - C++ 核心功能实现
   - 通过 `_privateFunction` 等暴露

5. **experimental/tskit/bindings/extension.cpp**
   - C++ 扩展功能实现
   - 通过 `_privateExtension` 等暴露

6. **Closure Compiler 配置文件**
   - 指定使用此 externs 文件
   - 配置编译选项

7. **构建脚本 (Makefile 或 package.json)**
   - 调用 Closure Compiler
   - 传递 externs 参数

8. **experimental/tskit/npm_build/bundle.min.js**
   - 编译输出
   - 使用 externs 保护符号名
