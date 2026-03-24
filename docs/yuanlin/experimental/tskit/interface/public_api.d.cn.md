# public_api.d.ts 类型定义

> 源文件: experimental/tskit/interface/public_api.d.ts

## 概述

`public_api.d.ts` 是 TSKit 框架的公共 API 类型定义文件,定义了所有暴露给最终用户的接口、类型别名和类型约束。这个文件是 TypeScript 开发者使用 TSKit 时的主要类型参考,提供了完整的类型安全保障和 IDE 智能提示支持。

该文件的核心职责包括:
1. 定义 `CanvasKit` 全局 API 对象的接口
2. 声明所有公共类和构造函数的类型
3. 定义数据传递的类型别名和复合类型
4. 声明 Emscripten 对象的通用接口

这是一个纯类型声明文件,不包含任何运行时代码,但却是整个类型系统的核心。

## 架构位置

`public_api.d.ts` 位于类型系统的顶层,是其他实现文件的类型约束来源:

```
experimental/tskit/
├── interface/
│   ├── public_api.d.ts  # 公共 API 类型定义(当前文件)
│   ├── load.ts          # 引用 public_api 命名空间
│   ├── core.ts          # 实现 public_api 定义的接口
│   ├── extension.ts     # 实现 public_api 定义的接口
│   └── memory.ts        # 使用 public_api 的类型别名
├── bindings/
│   └── *.d.ts           # C++ 绑定的类型定义
└── npm_build/
    └── types/
        └── index.d.ts   # 基于 public_api 生成的最终类型
```

**类型流向:**
```
public_api.d.ts (类型定义)
    ↓
core.ts, extension.ts (实现)
    ↓
npm_build/types/index.d.ts (发布)
    ↓
用户代码 (消费)
```

## 主要类与结构体

### namespace public_api

所有类型定义都在 `public_api` 命名空间内,避免全局命名冲突。

### interface CanvasKit

`CanvasKit` 是主要的全局 API 对象接口,包含所有公共函数和类的引用。

```typescript
export interface CanvasKit {
  publicExtension(myRects: InputFlattenedRectArray): number;
  sayHello(x: number, y: number): void;
  publicFunction(input: string): void;
  withObject(obj: CompoundObj): void;

  readonly Extension: ExtensionConstructor;
  readonly Something: SomethingConstructor;
}
```

**函数方法:**
1. **publicExtension**: 处理矩形数组,返回包含特定点的矩形数量
2. **sayHello**: 演示函数,输出计算结果
3. **publicFunction**: 接收字符串参数的公共函数
4. **withObject**: 处理复合对象

**类引用:**
1. **Extension**: 扩展类的构造函数
2. **Something**: 核心类的构造函数

**设计特点:**
- 使用 `readonly` 确保构造函数不可被重写
- 函数签名清晰,参数类型明确
- 支持函数重载(通过不同的构造函数接口)

### interface ExtensionConstructor

定义 `Extension` 类的构造函数接口,支持多种构造方式。

```typescript
export interface ExtensionConstructor {
  new(): Extension;
  new(name: string): Extension;
}
```

**构造函数重载:**
1. **无参数构造**: `new Extension()` - 使用默认值
2. **带名称构造**: `new Extension(name)` - 使用提供的名称

**使用示例:**
```typescript
const ext1 = new CanvasKit.Extension();
const ext2 = new CanvasKit.Extension("myExtension");
```

### interface SomethingConstructor

定义 `Something` 类的构造函数接口,要求必须提供名称参数。

```typescript
export interface SomethingConstructor {
  new(name: string): Something;
}
```

**构造约束:**
- 必须提供 `name` 参数
- 不支持无参数构造

### interface Extension

定义 `Extension` 类的实例接口,继承 `EmbindObject`。

```typescript
export interface Extension extends EmbindObject<Extension> {
  getProp(): string;
  setProp(p: string): void;
}
```

**实例方法:**
1. **getProp**: 获取属性值,返回字符串
2. **setProp**: 设置属性值,接收字符串参数

**继承关系:**
- 继承 `EmbindObject<Extension>`
- 自动获得 `clone`, `delete`, `isAliasOf`, `isDeleted` 等方法

### interface Something

定义 `Something` 类的实例接口,同样继承 `EmbindObject`。

```typescript
export interface Something extends EmbindObject<Something> {
  getName(): string;
  setName(name: string): void;
}
```

**实例方法:**
1. **getName**: 获取名称,返回字符串
2. **setName**: 设置名称,接收字符串参数(实际实现会将名称重复两次)

### interface CompoundObj

定义复合对象的结构,用于跨语言数据传递。

```typescript
export interface CompoundObj {
  alpha: number;
  beta: string;
  gamma?: number;
}
```

**字段说明:**
1. **alpha** (必需): 数值类型
2. **beta** (必需): 字符串类型
3. **gamma** (可选): 数值类型,默认值为 1.0

**设计考量:**
- 使用 `?` 标记可选字段
- 简单的值对象,适合直接传递给 C++ 的 value_object
- 支持 Emscripten 的自动序列化

### type InputFlattenedRectArray

定义输入矩形数组的类型别名。

```typescript
export type InputFlattenedRectArray = Float32Array | number[];
```

**支持的类型:**
1. **Float32Array**: TypedArray,性能更好
2. **number[]**: 普通 JavaScript 数组,更灵活

**使用场景:**
- 传递大量几何数据到 C++ 层
- 支持两种输入方式,平衡性能和易用性

### type TypedArray

定义通用的 TypedArray 类型别名。

```typescript
export type TypedArray = Float32Array | Int32Array;
```

**支持的类型:**
1. **Float32Array**: 32位浮点数数组
2. **Int32Array**: 32位有符号整数数组

**使用场景:**
- 内存管理工具的参数类型
- 高性能数据传递

### interface EmbindObject<T>

定义所有通过 Emscripten 暴露的对象的通用接口,使用泛型实现类型安全。

```typescript
export interface EmbindObject<T extends EmbindObject<T>> {
  clone(): T;
  delete(): void;
  deleteAfter(): void;
  isAliasOf(other: any): boolean;
  isDeleted(): boolean;
}
```

**方法说明:**

1. **clone(): T**
   - 克隆当前对象
   - 返回类型与当前对象相同(通过泛型 T)
   - 创建深拷贝

2. **delete(): void**
   - 手动释放对象占用的内存
   - 调用后对象不可再使用
   - 必须显式调用以避免内存泄漏

3. **deleteAfter(): void**
   - 延迟删除,在当前操作完成后释放
   - 用于链式调用的最后一步
   - 自动管理生命周期

4. **isAliasOf(other: any): boolean**
   - 检查两个对象是否指向同一 C++ 对象
   - 用于对象相等性判断
   - 比较指针而非值

5. **isDeleted(): boolean**
   - 检查对象是否已被删除
   - 用于防御性编程
   - 避免访问已释放的内存

**泛型约束:**
```typescript
T extends EmbindObject<T>
```
- 自引用泛型,确保 `clone()` 返回正确的类型
- 例如: `Extension.clone()` 返回 `Extension`,而非 `EmbindObject`

## 公共 API 函数

所有公共函数都在 `CanvasKit` 接口中定义,实际实现在 `core.ts` 和 `extension.ts` 中。

### 函数签名汇总

```typescript
// 矩形数组处理
publicExtension(myRects: InputFlattenedRectArray): number

// 演示函数
sayHello(x: number, y: number): void

// 字符串处理
publicFunction(input: string): void

// 对象处理
withObject(obj: CompoundObj): void
```

## 内部实现细节

### 类型声明的特点

1. **纯声明文件**: 使用 `declare namespace` 而非 `namespace`
2. **导出接口**: 所有接口都使用 `export` 关键字
3. **无实现**: 只有类型签名,无函数体

### 命名约定

1. **接口命名**: PascalCase (如 `CanvasKit`, `Extension`)
2. **类型别名**: PascalCase (如 `TypedArray`)
3. **字段命名**: camelCase (如 `alpha`, `beta`)
4. **构造函数接口**: 类名 + `Constructor` 后缀

### 可选字段处理

```typescript
gamma?: number;
```
- 使用 `?` 标记
- 允许 `undefined`
- 不允许 `null`(除非显式声明)

## 依赖关系

### 依赖的外部类型

无直接依赖,这是最底层的类型定义文件。

### 被依赖的模块

1. **load.ts**: 引用 `public_api.CanvasKit`
2. **core.ts**: 实现 `public_api.CanvasKit` 的部分方法
3. **extension.ts**: 实现 `public_api.CanvasKit` 的部分方法
4. **memory.ts**: 使用 `public_api.TypedArray`

### 依赖图

```
public_api.d.ts (类型定义)
    ↓
├── load.ts (引用 CanvasKit)
├── core.ts (实现 CanvasKit.sayHello 等)
├── extension.ts (实现 CanvasKit.publicExtension 等)
└── memory.ts (使用 TypedArray)
```

## 设计模式与设计决策

### 1. 接口分离原则 (Interface Segregation)

将不同职责的类型分离到不同的接口:
- `CanvasKit`: 全局 API
- `Extension`, `Something`: 具体类
- `EmbindObject`: 通用对象行为

### 2. 泛型设计

`EmbindObject<T>` 使用自引用泛型:
- 保证类型安全
- 支持方法链
- 避免类型转换

### 3. 构造函数接口模式

分离构造函数接口和实例接口:
```typescript
interface SomethingConstructor { new(...): Something }
interface Something extends EmbindObject<Something> { ... }
```
- 清晰区分静态和实例成员
- 支持构造函数重载

### 4. 类型别名 vs 接口

**使用类型别名:**
```typescript
export type InputFlattenedRectArray = Float32Array | number[];
```
- 适合联合类型
- 语义简洁

**使用接口:**
```typescript
export interface CompoundObj { ... }
```
- 适合对象形状
- 支持扩展和实现

### 5. 只读构造函数

```typescript
readonly Extension: ExtensionConstructor;
```
- 防止重写构造函数
- 确保 API 稳定性

### 6. 可选参数策略

在构造函数中使用重载而非可选参数:
```typescript
// 好的设计
new(): Extension;
new(name: string): Extension;

// 避免的设计
new(name?: string): Extension;
```
- 重载提供更精确的类型推断
- 明确不同的构造方式

## 性能考量

作为纯类型定义文件,`public_api.d.ts` 不直接影响运行时性能,但其设计影响使用模式和性能特征:

### 1. TypedArray 优先

```typescript
export type InputFlattenedRectArray = Float32Array | number[];
```
- 鼓励使用 TypedArray
- TypedArray 的内存传递更高效
- 普通数组需要转换

### 2. 值对象设计

```typescript
export interface CompoundObj {
  alpha: number;
  beta: string;
  gamma?: number;
}
```
- 简单的值对象,序列化开销低
- 避免复杂的嵌套结构
- 直接映射到 C++ struct

### 3. 手动内存管理

`EmbindObject` 提供显式的 `delete()`:
- 允许精确控制生命周期
- 避免 GC 压力
- 需要开发者负责内存管理

### 4. 方法签名简洁性

- 避免复杂的泛型参数
- 参数数量保持在 1-3 个
- 返回类型明确,无 `any`

## 相关文件

1. **experimental/tskit/interface/load.ts**
   - 使用 `public_api.CanvasKit` 类型声明全局对象

2. **experimental/tskit/interface/core.ts**
   - 实现 `sayHello` 和 `Something.prototype.setName`
   - 遵循 `public_api.d.ts` 的类型约束

3. **experimental/tskit/interface/extension.ts**
   - 实现 `publicExtension` 和 `withObject`
   - 使用 `InputFlattenedRectArray` 和 `CompoundObj` 类型

4. **experimental/tskit/interface/memory.ts**
   - 使用 `public_api.TypedArray` 类型
   - 为数据传递提供支持

5. **experimental/tskit/bindings/embind.d.ts**
   - 定义底层的 Emscripten 类型
   - `EmbindObject` 的灵感来源

6. **experimental/tskit/npm_build/types/index.d.ts**
   - 基于 `public_api.d.ts` 生成
   - 包含所有公共类型定义
   - 最终发布给用户

7. **experimental/tskit/go/gen_types/gen_types.go**
   - 自动生成部分类型定义
   - 从 C++ 绑定代码解析类型信息

8. **用户代码**
   - 导入 `CanvasKit` 类型
   - 使用 TypeScript 类型检查
   - 获得 IDE 智能提示
