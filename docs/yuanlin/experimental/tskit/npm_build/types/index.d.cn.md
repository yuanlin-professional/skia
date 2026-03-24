# index.d.ts NPM 包类型定义

> 源文件: experimental/tskit/npm_build/types/index.d.ts

## 概述

`index.d.ts` 是 TSKit 框架最终发布到 NPM 的类型定义文件,是用户使用该库时获得 TypeScript 类型支持的核心入口。该文件整合了公共 API 的所有类型声明,提供完整的类型安全保障和 IDE 智能提示支持。它是从 `interface/public_api.d.ts` 和其他类型定义文件编译或整合而来,专门为外部使用者优化。

文件特点:
1. 包含完整的公共 API 类型定义
2. 导出 `CanvasKit` 接口作为主要入口
3. 定义所有公共类、接口和类型别名
4. 包含详细的 JSDoc 注释,增强 IDE 提示质量
5. 遵循 TypeScript 类型定义的最佳实践

这个文件是库的公共契约,任何对其的修改都会影响所有使用者。

## 架构位置

```
experimental/tskit/
├── interface/
│   ├── public_api.d.ts    # 内部类型定义
│   ├── core.ts            # 实现代码
│   └── extension.ts       # 实现代码
├── bindings/
│   ├── core.d.ts          # C++ 绑定类型
│   └── extension.d.ts     # C++ 绑定类型
└── npm_build/
    └── types/
        └── index.d.ts     # NPM 发布的类型(当前文件)
```

**类型流向:**
```
internal types (public_api.d.ts, *.d.ts)
    ↓ 编译/整合
npm_build/types/index.d.ts
    ↓ npm publish
@skia/tskit (NPM package)
    ↓
用户项目 (import CanvasKit)
```

## 主要类与结构体

### interface CanvasKit

主要的全局 API 接口,包含所有公共函数和类构造函数。

```typescript
export interface CanvasKit {
    /**
     * This function says hello
     *
     * @param x some number
     * @param y some other number
     */
    sayHello(x: number, y: number): void;

    /**
     * publicExtension takes the number of rects and returns how
     * many of them have the point (5, 5) in them.
     * @param myRects
     * @ts publicExtension(myRects: InputFlattenedRectArray): void;
     */
    publicExtension(myRects: InputFlattenedRectArray): number;

    /**
     * This function does a public thing.
     * @param input an ice cream flavor
     */
    publicFunction(input: string): void;

    withObject(obj: CompoundObj): void;

    readonly Extension: ExtensionConstructor;
    readonly Something: SomethingConstructor;
}
```

**API 分类:**
1. **实用函数**: `sayHello`, `publicFunction`
2. **几何计算**: `publicExtension`
3. **对象处理**: `withObject`
4. **类构造器**: `Extension`, `Something`

### interface ExtensionConstructor

`Extension` 类的构造函数接口,支持可选参数。

```typescript
export interface ExtensionConstructor {
    /**
     * Returns an extension with the provided property.
     * @param name - if not provided, use a default value
     */
    new(name?: string): Extension;
}
```

**构造方式:**
- 无参数: `new CanvasKit.Extension()`
- 带参数: `new CanvasKit.Extension("myName")`

### interface SomethingConstructor

`Something` 类的构造函数接口,必需参数。

```typescript
export interface SomethingConstructor {
    /**
     * Returns a Something with the provided name.
     * @param name
     */
    new(name: string): Something;
}
```

**构造约束:**
- 必须提供 `name` 参数

### interface Extension

`Extension` 类的实例接口。

```typescript
export interface Extension extends EmbindObject<Extension> {
    /**
     * Returns the associated property.
     */
    getProp(): string;
    /**
     * This sets the property with a prefix.
     * @param p
     */
    setProp(p: string): void;
}
```

**方法:**
- `getProp()`: 获取属性值
- `setProp(p)`: 设置属性值(带预处理)

### interface Something

`Something` 类的实例接口,包含文档注释。

```typescript
/**
 * The Something class is quite something. See SkSomething.h for more.
 */
export interface Something extends EmbindObject<Something> {
    /**
     * Returns the associated name.
     */
    getName(): string;
    /**
     * This sets the name twice for good measure.
     * @param name
     */
    setName(name: string): void;
}
```

**特点:**
- 类级别的文档注释
- 方法级别的文档注释
- 清晰的功能说明

### interface CompoundObj

复合对象接口,用于跨语言数据传递。

```typescript
export interface CompoundObj {
    alpha: number;
    beta: string;
    /**
     * This field (gamma) should be documented.
     * @optional - default value is 1.0
     */
    gamma?: number;
}
```

**字段:**
- `alpha`: 必需的数字
- `beta`: 必需的字符串
- `gamma`: 可选的数字,默认 1.0

### type InputFlattenedRectArray

输入矩形数组的类型别名。

```typescript
export type InputFlattenedRectArray = Float32Array | number[];
```

**灵活性:**
- 支持 TypedArray (性能优先)
- 支持普通数组 (易用性优先)

### interface EmbindObject<T>

所有 Emscripten 暴露对象的基础接口。

```typescript
/**
 * CanvasKit is built with Emscripten and Embind. Embind adds the following methods to all objects
 * that are exposed with it.
 */
export interface EmbindObject<T extends EmbindObject<T>> {
    clone(): T;
    delete(): void;
    deleteAfter(): void;
    isAliasOf(other: any): boolean;
    isDeleted(): boolean;
}
```

**方法说明:**
1. **clone()**: 克隆对象,返回新实例
2. **delete()**: 手动释放内存
3. **deleteAfter()**: 延迟释放,用于链式调用
4. **isAliasOf(other)**: 检查是否指向同一 C++ 对象
5. **isDeleted()**: 检查对象是否已被删除

## 公共 API 函数

### CanvasKit.sayHello(x: number, y: number): void

演示函数,输出计算结果到控制台。

**用途:**
- 示例代码
- 测试连接性
- 调试工具

### CanvasKit.publicExtension(myRects: InputFlattenedRectArray): number

计算包含点 (5, 5) 的矩形数量。

**参数:**
- `myRects`: 扁平化矩形数组 [x1, y1, w1, h1, x2, y2, w2, h2, ...]

**返回:**
- 包含点 (5, 5) 的矩形数量

**使用示例:**
```typescript
const rects = [0, 0, 10, 10, 20, 20, 5, 5];
const count = CanvasKit.publicExtension(rects); // count = 1
```

### CanvasKit.publicFunction(input: string): void

公共字符串处理函数。

**参数:**
- `input`: 输入字符串

**功能:**
- 在 C++ 层处理字符串
- 可能输出到控制台或日志

### CanvasKit.withObject(obj: CompoundObj): void

处理复合对象,自动填充默认值。

**参数:**
- `obj`: 包含 `alpha`, `beta`, 可选 `gamma` 的对象

**行为:**
- 如果 `gamma` 未提供,使用默认值 1.0
- 将对象传递给 C++ 层处理

**使用示例:**
```typescript
CanvasKit.withObject({ alpha: 1, beta: "test" });
CanvasKit.withObject({ alpha: 2, beta: "hello", gamma: 2.5 });
```

## 内部实现细节

### JSDoc 注释格式

文件使用标准的 JSDoc 格式:

```typescript
/**
 * This function says hello
 *
 * @param x some number
 * @param y some other number
 */
```

**好处:**
- IDE 自动提取并显示
- 支持 Markdown 格式
- 标准化文档

### 可选参数的文档

```typescript
/**
 * @param name - if not provided, use a default value
 */
new(name?: string): Extension;
```

使用 TypeScript 的 `?` 标记和 JSDoc 注释结合。

### 默认值说明

```typescript
/**
 * @optional - default value is 1.0
 */
gamma?: number;
```

在注释中明确说明默认值。

### 泛型约束

```typescript
export interface EmbindObject<T extends EmbindObject<T>>
```

自引用泛型确保类型安全:
- `Extension.clone()` 返回 `Extension`
- `Something.clone()` 返回 `Something`

## 依赖关系

### 无外部依赖

该文件是自包含的,不依赖其他类型定义文件。

### 被依赖的代码

1. **用户 TypeScript 代码**
   ```typescript
   import { CanvasKit } from '@skia/tskit';
   ```

2. **用户 JavaScript 代码(带 JSDoc)**
   ```javascript
   /** @type {import('@skia/tskit').CanvasKit} */
   const CanvasKit = ...;
   ```

### 依赖图

```
index.d.ts (NPM 包类型)
    ↓ npm install
node_modules/@skia/tskit/types/index.d.ts
    ↓ import
用户项目 (类型检查 + 智能提示)
```

## 设计模式与设计决策

### 1. 单一入口原则

所有 API 都通过 `CanvasKit` 接口访问:
- 简化使用
- 避免命名冲突
- 清晰的命名空间

### 2. 构造函数接口分离

```typescript
interface SomethingConstructor {
    new(name: string): Something;
}
interface Something extends EmbindObject<Something> { ... }
```

- 清晰区分静态和实例成员
- 支持构造函数重载
- 便于类型推断

### 3. 类型别名提升可用性

```typescript
export type InputFlattenedRectArray = Float32Array | number[];
```

- 简化复杂类型
- 提供语义化名称
- 支持多种输入方式

### 4. 可选性的明确表达

使用 `?` 和 JSDoc 注释结合:
```typescript
/**
 * @optional - default value is 1.0
 */
gamma?: number;
```

### 5. 自文档化设计

丰富的 JSDoc 注释:
- 减少外部文档需求
- 提升开发体验
- 降低学习曲线

### 6. 只读构造函数引用

```typescript
readonly Extension: ExtensionConstructor;
```

防止用户代码意外修改构造函数。

## 性能考量

作为纯类型定义文件,不直接影响运行时性能,但其设计影响开发和编译性能:

### 1. 类型检查性能

- 简单的接口层次结构
- 适度的泛型复杂度
- 快速的类型推导

### 2. 编译时间

- 文件大小适中(95行)
- 无复杂的条件类型
- 编译快速

### 3. IDE 性能

- 清晰的接口定义,加快 IntelliSense
- JSDoc 注释提供即时文档
- 无大量类型计算

### 4. 捆绑大小

- 类型定义不包含在运行时捆绑中
- 仅影响开发时体验

### 5. 树摇优化

类型定义不影响树摇,但清晰的 API 设计便于用户只导入需要的功能。

## 相关文件

1. **experimental/tskit/interface/public_api.d.ts**
   - 内部类型定义
   - 此文件的来源

2. **experimental/tskit/interface/core.ts**
   - 实现 `sayHello` 和 `Something` 相关功能
   - 遵循此文件的类型约束

3. **experimental/tskit/interface/extension.ts**
   - 实现 `publicExtension` 和 `withObject`
   - 遵循此文件的类型约束

4. **experimental/tskit/bindings/core.d.ts**
   - C++ 核心绑定的类型
   - 提供底层类型信息

5. **experimental/tskit/bindings/extension.d.ts**
   - C++ 扩展绑定的类型
   - 提供底层类型信息

6. **experimental/tskit/go/gen_types/gen_types.go**
   - 类型生成工具
   - 可能参与生成部分类型定义

7. **package.json**
   - NPM 包配置
   - 指定 `types` 字段指向此文件

8. **tsconfig.json**
   - TypeScript 编译配置
   - 可能指定如何生成此文件

9. **用户项目**
   - 导入并使用此文件定义的类型
   - 获得类型安全和智能提示
