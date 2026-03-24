# Extension 模块

> 源文件: experimental/tskit/interface/extension.ts

## 概述

`Extension` 模块是 TSKit 框架中的扩展功能实现层,负责将 C++ 层的私有扩展函数封装为用户友好的公共 API。该模块展示了如何通过 TypeScript 接口层将底层的内存管理和数据转换细节隐藏,为开发者提供简洁的高级接口。

模块的核心功能包括:
1. 将扁平化的矩形数组传递给 C++ 进行几何计算
2. 处理复合对象的默认值填充和类型转换
3. 管理 WebAssembly 堆内存的分配和释放

这个模块体现了跨语言互操作的最佳实践,特别是在 JavaScript/TypeScript 与 WebAssembly 之间进行数据交换时的安全性和效率考量。

## 架构位置

`Extension` 模块位于 TSKit 框架的接口层,作为公共 API 和底层 C++ 绑定之间的桥梁:

```
experimental/tskit/
├── interface/
│   ├── load.ts          # 提供运行时初始化机制
│   ├── memory.ts        # 提供内存管理工具
│   ├── extension.ts     # 扩展功能封装(当前模块)
│   ├── core.ts          # 核心功能封装
│   └── public_api.d.ts  # 定义公共 API 类型
├── bindings/
│   ├── extension.d.ts   # C++ 扩展绑定的类型声明
│   └── extension.cpp    # C++ 扩展绑定的实现
└── npm_build/
    └── types/           # 最终发布的类型定义
```

**数据流向:**
```
用户代码 (TypeScript)
    ↓
public_api.CanvasKit.publicExtension()
    ↓
extension.ts (参数转换 + 内存管理)
    ↓
extension.d.ts → extension.cpp (C++ 实现)
    ↓
Skia 底层库
```

## 主要类与结构体

### namespace Extension

`Extension` 命名空间封装了所有扩展功能的实现逻辑。

**外部依赖声明:**
- `Module: extension.Bindings`: C++ 绑定对象,提供私有函数接口
- `CanvasKit: public_api.CanvasKit`: 公共 API 对象,用于挂载公共方法

### 类型系统

模块使用以下类型(来自 `public_api.d.ts`):
- `InputFlattenedRectArray`: 输入的矩形数组类型,可以是 `Float32Array` 或 `number[]`
- `CompoundObj`: 复合对象类型,包含 `alpha: number`, `beta: string`, `gamma?: number`

## 公共 API 函数

### CanvasKit.publicExtension(myRects: InputFlattenedRectArray): number

计算给定矩形数组中有多少个矩形包含点 (5, 5)。

**参数:**
- `myRects`: 扁平化的矩形数组,每4个数值表示一个矩形 `[x, y, width, height]`

**返回值:**
- `number`: 包含点 (5, 5) 的矩形数量

**实现逻辑:**
```typescript
CanvasKit.publicExtension = (myRects: public_api.InputFlattenedRectArray) => {
  const rPtr = memory.copy1dArray(myRects, 'HEAPF32');
  const num = Module._privateExtension(rPtr, myRects.length / 4);
  memory.freeIfNecessary(rPtr, myRects);
  return num;
};
```

**关键步骤:**
1. 使用 `memory.copy1dArray` 将 JavaScript 数组复制到 WASM 堆
2. 调用 C++ 的 `_privateExtension` 函数进行计算
3. 通过 `memory.freeIfNecessary` 释放临时分配的内存
4. 返回计算结果

**内存安全特性:**
- 自动管理内存分配和释放
- 支持 TypedArray 的零拷贝优化(如果数组已经在 WASM 堆上)

### CanvasKit.withObject(obj: CompoundObj): void

处理一个复合对象,如果缺少 `gamma` 字段则使用默认值 1.0。

**参数:**
- `obj`: 复合对象,必须包含 `alpha` 和 `beta`,可选 `gamma`

**实现逻辑:**
```typescript
CanvasKit.withObject = (obj: public_api.CompoundObj) => {
  obj.gamma ||= 1.0;
  Module._withObject(obj);
};
```

**关键特性:**
1. 使用 `||=` 运算符为 `gamma` 提供默认值
2. 直接将对象传递给 C++ 层(依赖 Emscripten 的 value_object 绑定)
3. 修改原始对象,副作用明确

**默认值策略:**
- 只在 `gamma` 为 `undefined` 或 `null` 时设置默认值
- 不影响其他字段
- 符合 Emscripten value_object 的类型映射规则

## 内部实现细节

### 初始化时序

所有公共 API 的绑定都在 `load.afterLoad` 回调中完成:
```typescript
load.afterLoad(() => {
  // 在这里挂载 publicExtension 和 withObject
});
```

这确保了:
- Emscripten 运行时已完全初始化
- C++ 绑定函数已可用
- 内存管理工具已就绪

### 内存管理策略

#### 矩形数组处理

```typescript
const rPtr = memory.copy1dArray(myRects, 'HEAPF32');
```
- 目标堆: `HEAPF32` (32位浮点数组)
- 自动计算所需字节数
- 返回 WASM 堆指针

```typescript
memory.freeIfNecessary(rPtr, myRects);
```
- 检查原始数组是否已在 WASM 堆上(通过 `_ck` 标记)
- 如果是临时分配的内存,则调用 `Module._free` 释放
- 如果是 TypedArray 且已在堆上,则跳过释放(避免重复释放)

#### 数组长度计算

```typescript
Module._privateExtension(rPtr, myRects.length / 4);
```
- 将扁平数组长度除以 4 得到矩形数量
- 每个矩形由 4 个浮点数表示 (x, y, width, height)
- C++ 层接收矩形数量而非总元素数

### 对象传递机制

`withObject` 函数依赖 Emscripten 的 value_object 绑定:
- JavaScript 对象字段自动映射到 C++ 结构体成员
- 类型转换由 Emscripten 自动处理
- 可选字段需要在 JavaScript 层填充默认值

## 依赖关系

### 依赖的模块

1. **load.ts**
   - 提供 `load.afterLoad` 函数
   - 确保运行时初始化完成后才注册 API

2. **memory.ts**
   - 提供 `memory.copy1dArray` 内存复制工具
   - 提供 `memory.freeIfNecessary` 内存释放工具

3. **extension.d.ts**
   - 声明 `extension.Bindings` 接口
   - 定义 C++ 私有函数的类型签名

4. **public_api.d.ts**
   - 定义公共 API 的类型
   - 声明 `InputFlattenedRectArray` 和 `CompoundObj` 类型

### 被依赖的模块

- 最终的 npm 包会包含这些 API
- 用户代码通过 `CanvasKit` 全局对象调用

### 依赖图

```
embind.d.ts
    ↓
load.ts → Extension.ts ← memory.ts
    ↓           ↓
public_api.d.ts
    ↓
extension.d.ts (C++ 绑定)
    ↓
extension.cpp
```

## 设计模式与设计决策

### 1. 外观模式 (Facade Pattern)

`Extension` 模块为底层 C++ 函数提供了简化的外观:
- 隐藏内存管理细节
- 隐藏指针操作
- 隐藏数据格式转换

### 2. 适配器模式 (Adapter Pattern)

将 JavaScript 的数据结构适配为 C++ 可以处理的格式:
- `InputFlattenedRectArray` → WASM 堆上的 `float*`
- `CompoundObj` → C++ `value_object`

### 3. RAII (Resource Acquisition Is Initialization)

虽然 JavaScript 没有传统的 RAII,但模块实现了类似的资源管理:
```typescript
const rPtr = memory.copy1dArray(...);  // 获取资源
try {
  const num = Module._privateExtension(...);  // 使用资源
  return num;
} finally {
  memory.freeIfNecessary(rPtr, ...);  // 释放资源
}
```

实际代码未使用 try-finally,依赖同步执行保证释放顺序。

### 4. 默认参数模式

使用 `||=` 运算符提供默认值:
```typescript
obj.gamma ||= 1.0;
```
- 简洁且高效
- 符合 JavaScript 惯用法
- 避免不必要的对象拷贝

### 5. 命名约定

- 私有 C++ 函数以 `_` 开头 (如 `_privateExtension`)
- 公共 API 无前缀 (如 `publicExtension`)
- 清晰的访问控制语义

## 性能考量

### 1. 内存拷贝开销

**扁平数组拷贝:**
```typescript
const rPtr = memory.copy1dArray(myRects, 'HEAPF32');
```
- 时间复杂度: O(n),n 为数组长度
- 对于大型数组(>10000元素),拷贝可能成为瓶颈
- 优化策略:使用 TypedArray 并预先分配在 WASM 堆上

**零拷贝优化:**
- 如果 `myRects` 已经是 `Float32Array` 且在 WASM 堆上
- `memory.copy1dArray` 可能避免拷贝(取决于实现)
- 通过 `_ck` 标记识别可复用的内存

### 2. 函数调用开销

- JavaScript → WebAssembly 调用有固定开销(~10-50ns)
- 对于小数据集,调用开销可能超过计算成本
- 批处理多个操作可以摊薄调用成本

### 3. 内存管理开销

**分配:**
- `Module._malloc` 的时间复杂度取决于 WASM 堆分配器
- 通常为 O(1) 或 O(log n)

**释放:**
- `Module._free` 同样为 O(1) 或 O(log n)
- 及时释放避免内存碎片化

### 4. 对象传递优化

`withObject` 直接传递 JavaScript 对象:
- Emscripten 自动序列化/反序列化
- 对于小对象,开销可接受
- 大对象或频繁调用时,考虑使用指针传递

### 5. 默认值设置

```typescript
obj.gamma ||= 1.0;
```
- 非常轻量,几乎无性能影响
- 避免了条件分支的预测失败

## 相关文件

1. **experimental/tskit/interface/load.ts**
   - 提供 `afterLoad` 函数注册初始化逻辑

2. **experimental/tskit/interface/memory.ts**
   - 实现 `copy1dArray` 和 `freeIfNecessary`

3. **experimental/tskit/interface/public_api.d.ts**
   - 定义 `InputFlattenedRectArray` 和 `CompoundObj` 类型

4. **experimental/tskit/bindings/extension.d.ts**
   - 声明 `extension.Bindings` 接口
   - 定义 `_privateExtension` 和 `_withObject` 的类型

5. **experimental/tskit/bindings/extension.cpp**
   - 实现 `_privateExtension` 的 C++ 逻辑
   - 实现 `_withObject` 的 C++ 逻辑

6. **experimental/tskit/bindings/embind.d.ts**
   - 定义 Emscripten 的基础类型

7. **experimental/tskit/npm_build/types/index.d.ts**
   - 最终发布的类型定义文件
   - 包含所有公共 API 的声明
