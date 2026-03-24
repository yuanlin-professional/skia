# memory 模块

> 源文件: experimental/tskit/interface/memory.ts

## 概述

`memory` 模块是 TSKit 框架中的核心内存管理工具,负责在 JavaScript/TypeScript 和 WebAssembly 之间安全高效地传递数据。该模块封装了 Emscripten 的内存操作 API,提供了简洁的接口来处理数组的分配、复制和释放,是跨语言数据交换的关键基础设施。

模块的核心功能包括:
1. 将 JavaScript 数组或 TypedArray 复制到 WebAssembly 堆内存
2. 智能判断是否需要释放内存,避免重复释放或内存泄漏
3. 提供类型安全的堆内存访问接口

这个模块体现了 WebAssembly 内存管理的最佳实践,特别是在处理动态分配内存和优化性能方面的考量。

## 架构位置

`memory` 模块位于 TSKit 框架的基础工具层,为所有需要传递数据到 WebAssembly 的模块提供服务:

```
experimental/tskit/
├── interface/
│   ├── load.ts          # 运行时初始化管理
│   ├── memory.ts        # 内存管理工具(当前模块)
│   ├── core.ts          # 核心功能(可能使用 memory)
│   ├── extension.ts     # 扩展功能(使用 memory)
│   └── public_api.d.ts  # 公共 API 类型定义
└── bindings/
    ├── embind.d.ts      # Emscripten 类型定义
    └── *.cpp            # C++ 绑定实现
```

**使用关系:**
```
extension.ts → memory.copy1dArray / memory.freeIfNecessary
core.ts → (可能间接使用)
其他模块 → memory 工具函数
```

## 主要类与结构体

### namespace memory

`memory` 命名空间封装了所有内存管理相关的功能。

**外部依赖:**
- `Module: embind.EmbindModule`: Emscripten 模块对象,提供 `_malloc`, `_free` 等底层函数

### 类型定义

#### type Heaps

```typescript
export type Heaps = 'HEAPF32' | 'HEAPU8' | 'HEAPU16' | 'HEAPU32' | 'HEAP8' | 'HEAP16' | 'HEAP32';
```

定义了所有可用的 WebAssembly 堆内存视图类型:
- `HEAPF32`: 32位浮点数数组视图
- `HEAPU8`: 无符号8位整数数组视图
- `HEAPU16`: 无符号16位整数数组视图
- `HEAPU32`: 无符号32位整数数组视图
- `HEAP8`: 有符号8位整数数组视图
- `HEAP16`: 有符号16位整数数组视图
- `HEAP32`: 有符号32位整数数组视图

**设计说明:**
- 使用字符串字面量联合类型,而非枚举
- 遵循《Effective TypeScript》第197页的建议
- 提供更好的类型安全性和灵活性

### 常量定义

#### nullptr

```typescript
export const nullptr = 0;
```

表示空指针的常量,值为 0。在 WebAssembly 中,地址 0 通常表示无效或空指针。

## 公共 API 函数

### copy1dArray

```typescript
export const copy1dArray = (
  arr: number[] | public_api.TypedArray | null,
  dest: Heaps,
  ptr?: number
): number
```

将 JavaScript 数组或 TypedArray 复制到 WebAssembly 堆内存。

**参数:**
- `arr`: 要复制的数组,可以是 `number[]`、TypedArray 或 `null`
- `dest`: 目标堆类型,例如 `'HEAPF32'`、`'HEAPU8'` 等
- `ptr` (可选): 预先分配的指针地址,如果不提供则自动分配

**返回值:**
- `number`: WebAssembly 堆内存中的指针地址,如果输入为空则返回 `nullptr` (0)

**实现逻辑:**
```typescript
export const copy1dArray = (arr: number[] | public_api.TypedArray | null,
                            dest: Heaps, ptr?: number): number => {
  if (!arr || !arr.length) {
    return nullptr;
  }
  const bytesPerElement = Module[dest].BYTES_PER_ELEMENT;
  ptr ||= Module._malloc(arr.length * bytesPerElement);
  Module[dest].set(arr, ptr / bytesPerElement);
  return ptr;
};
```

**关键步骤:**
1. **空值检查**: 如果数组为 `null`、`undefined` 或空数组,返回 `nullptr`
2. **计算字节大小**: 根据目标堆类型获取每个元素的字节数
3. **内存分配**: 如果未提供 `ptr`,使用 `Module._malloc` 分配内存
4. **数据复制**: 使用 TypedArray 的 `set` 方法将数据复制到目标地址
5. **返回指针**: 返回分配的内存地址

**注意事项:**
- `ptr` 参数以字节为单位,但 `Module[dest].set` 的索引以元素为单位,需要除以 `bytesPerElement`
- 如果提供了 `ptr`,函数不会检查内存是否足够,需要调用者保证

### freeIfNecessary

```typescript
export const freeIfNecessary = (ptr: number, arr: any[] | public_api.TypedArray): void
```

智能释放内存,仅在数组不在 WebAssembly 堆上时才释放。

**参数:**
- `ptr`: 要释放的内存地址
- `arr`: 原始数组,用于判断是否需要释放

**返回值:**
- `void`: 无返回值

**实现逻辑:**
```typescript
export const freeIfNecessary = (ptr: number, arr: any[] | public_api.TypedArray): void => {
  if (arr && !(arr as any)._ck) {
    Module._free(ptr);
  }
};
```

**关键判断:**
1. **数组存在性**: 检查 `arr` 不为 `null` 或 `undefined`
2. **堆标记检查**: 检查 `arr._ck` 属性,如果不存在表示是临时分配的内存
3. **条件释放**: 只有当内存是临时分配时才调用 `Module._free`

**`_ck` 标记说明:**
- `_ck` 是一个内部标记,表示 TypedArray 已经在 WebAssembly 堆上
- 如果 TypedArray 直接映射到 WASM 内存,`_ck` 会被设置
- 这种情况下,内存不应该被释放,因为它不是由 `copy1dArray` 分配的

## 内部实现细节

### 内存分配策略

**字节计算:**
```typescript
const bytesPerElement = Module[dest].BYTES_PER_ELEMENT;
ptr ||= Module._malloc(arr.length * bytesPerElement);
```
- 每个堆类型有不同的 `BYTES_PER_ELEMENT`
  - `HEAPF32`: 4 字节
  - `HEAPU16`: 2 字节
  - `HEAPU8`: 1 字节
- 总内存大小 = 数组长度 × 每元素字节数

**地址对齐:**
- `Module._malloc` 返回的地址已经正确对齐
- TypedArray 的 `set` 方法要求正确的对齐,否则会抛出异常

### 数据复制机制

```typescript
Module[dest].set(arr, ptr / bytesPerElement);
```
- `Module[dest]` 是一个 TypedArray 视图,映射到 WebAssembly 的线性内存
- `set(arr, offset)` 将 `arr` 的内容复制到视图的 `offset` 位置
- `offset` 以元素为单位,所以需要将字节地址除以 `bytesPerElement`

**复制性能:**
- TypedArray 的 `set` 方法通常由浏览器引擎优化
- 对于 TypedArray 到 TypedArray 的复制,可能使用 `memcpy` 级别的优化
- 对于 JavaScript 数组,需要逐个元素转换和复制

### 零拷贝优化

理论上,如果 `arr` 已经是一个指向 WASM 堆的 TypedArray:
- 可以直接使用其地址,无需复制
- `_ck` 标记用于识别这种情况
- `freeIfNecessary` 通过检查 `_ck` 避免错误释放

**实现限制:**
当前实现总是执行复制,即使 `arr` 已在 WASM 堆上。更优化的版本可以检测这种情况:
```typescript
if ((arr as any)._ck) {
  // 已经在 WASM 堆上,返回其地址
  return (arr as any).byteOffset;
}
```

## 依赖关系

### 依赖的模块

1. **embind.d.ts**
   - 定义 `embind.EmbindModule` 接口
   - 声明 `_malloc` 和 `_free` 函数

2. **public_api.d.ts**
   - 定义 `TypedArray` 类型: `Float32Array | Int32Array`

### 被依赖的模块

1. **extension.ts**
   - 使用 `copy1dArray` 复制矩形数组
   - 使用 `freeIfNecessary` 释放临时内存

2. **其他接口模块**
   - 任何需要传递数组到 WASM 的模块

### 依赖图

```
embind.d.ts → memory.ts ← public_api.d.ts
                ↓
          extension.ts
          core.ts (潜在)
```

## 设计模式与设计决策

### 1. 工具类模式 (Utility Pattern)

`memory` 模块作为纯工具类,不维护状态:
- 所有函数都是无副作用的(除了内存操作)
- 可以在任何上下文中安全调用
- 易于测试和调试

### 2. RAII 风格的资源管理

虽然 JavaScript 没有 RAII,但模块提供了配对的分配/释放函数:
```typescript
const ptr = memory.copy1dArray(arr, 'HEAPF32');  // 获取资源
try {
  // 使用 ptr
} finally {
  memory.freeIfNecessary(ptr, arr);  // 释放资源
}
```

### 3. 智能指针风格

`freeIfNecessary` 类似于智能指针的析构逻辑:
- 自动判断是否需要释放
- 避免重复释放或内存泄漏
- 简化调用者的逻辑

### 4. 类型安全设计

使用 `Heaps` 类型而非字符串:
```typescript
copy1dArray(arr, 'HEAPF32')  // 类型安全
copy1dArray(arr, 'HEAPF64')  // 编译错误,不存在的堆类型
```

### 5. 空值处理

统一的空值处理策略:
- 空数组返回 `nullptr`
- `null` 或 `undefined` 返回 `nullptr`
- 避免在底层抛出异常

### 6. 逻辑短路运算符的使用

```typescript
ptr ||= Module._malloc(arr.length * bytesPerElement);
```
- 使用 `||=` 实现条件分配
- 简洁且高效
- 符合现代 JavaScript 惯用法

## 性能考量

### 1. 内存分配开销

**_malloc 性能:**
- 时间复杂度: O(1) 或 O(log n),取决于分配器实现
- Emscripten 使用 dlmalloc,通常为 O(1)
- 频繁分配可能导致内存碎片化

**优化策略:**
- 预分配大块内存,多次复用
- 使用内存池减少分配次数

### 2. 数据复制开销

**TypedArray.set 性能:**
- 对于 TypedArray → TypedArray: 接近 memcpy 性能,O(n)
- 对于 Array → TypedArray: 需要类型转换,O(n) 但常数较大
- 对于大型数组(>10000元素),复制可能成为瓶颈

**优化策略:**
- 尽可能使用 TypedArray 而非普通数组
- 考虑零拷贝方案(直接在 WASM 堆上创建数组)
- 批处理多个小数组的操作

### 3. 内存对齐

- TypedArray 的 `set` 方法要求正确对齐
- `Module._malloc` 返回的地址满足最大对齐要求
- 不正确的对齐会导致性能下降或异常

### 4. 空值检查开销

```typescript
if (!arr || !arr.length) {
  return nullptr;
}
```
- 开销极小,通常被 JIT 编译器优化
- 避免了后续的无效操作
- 权衡:少量开销换取健壮性

### 5. 释放策略

**freeIfNecessary 的检查:**
```typescript
if (arr && !(arr as any)._ck) {
  Module._free(ptr);
}
```
- 检查开销极小(两次属性访问)
- 避免错误释放的代价远大于检查成本
- 及时释放避免内存泄漏

### 6. 内存使用模式

**临时数组:**
```typescript
const arr = [1, 2, 3, 4];
const ptr = copy1dArray(arr, 'HEAPF32');
// 使用 ptr
freeIfNecessary(ptr, arr);  // 会释放
```

**持久化 TypedArray:**
```typescript
const arr = new Float32Array(Module.HEAPF32.buffer, ptr, length);
arr._ck = true;  // 标记为 WASM 堆上的数组
// 使用 arr
freeIfNecessary(ptr, arr);  // 不会释放
```

## 相关文件

1. **experimental/tskit/bindings/embind.d.ts**
   - 定义 `EmbindModule` 接口
   - 声明 `_malloc(size: number): number`
   - 声明 `_free(ptr: number): void`
   - 声明各种堆视图类型 (HEAPF32, HEAPU8 等)

2. **experimental/tskit/interface/public_api.d.ts**
   - 定义 `TypedArray = Float32Array | Int32Array`
   - 定义其他公共 API 类型

3. **experimental/tskit/interface/extension.ts**
   - 主要使用者之一
   - 在 `publicExtension` 函数中使用 `copy1dArray` 和 `freeIfNecessary`

4. **experimental/tskit/interface/core.ts**
   - 可能间接使用内存管理功能

5. **experimental/tskit/interface/load.ts**
   - 不直接依赖 memory,但都是基础设施模块

6. **experimental/tskit/bindings/*.cpp**
   - C++ 层接收从 `copy1dArray` 传递的指针
   - 实现实际的数据处理逻辑
