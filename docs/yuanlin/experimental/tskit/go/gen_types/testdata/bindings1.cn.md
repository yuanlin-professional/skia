# bindings1.cpp 测试数据文件

> 源文件: experimental/tskit/go/gen_types/testdata/bindings1.cpp

## 概述

`bindings1.cpp` 是 `gen_types` 工具的测试数据文件,包含了各种 Emscripten 绑定模式的完整示例。该文件不是真实的 C++ 代码,而是专门设计用于测试类型生成器的功能,覆盖了所有支持的绑定语法,包括函数导出、类定义、值对象、常量声明等。

这个文件的设计目标是:
1. 提供完整的绑定模式示例,涵盖所有 `gen_types` 支持的语法
2. 验证解析器能够正确处理注释、文档字符串和类型注解
3. 测试字母顺序排序和格式化逻辑
4. 包含可选字段和条件编译的边缘情况

## 架构位置

```
experimental/tskit/go/gen_types/
├── gen_types.go          # 类型生成器实现
├── gen_types_test.go     # 测试代码
└── testdata/
    ├── bindings1.cpp                       # 测试输入(当前文件)
    └── expectedambientnamespace1.d.ts      # 预期输出
```

## 主要类与结构体

### class Something

简单的 C++ 类,包含一个字符串字段和 getter/setter 方法。

```cpp
class Something {
public:
    Something(std::string n): fName(n) {}
    const std::string getName() { return fName; }
    void setName(std::string name) { fName = name; }
private:
    std::string fName;
};
```

**绑定定义:**
```cpp
class_<Something>("Something")
    TS_EXPORT("new(name: string): Something")
    .constructor<std::string>()
    TS_EXPORT("getName(): string")
    .function("getName", &Something::getName)
    TS_PRIVATE_EXPORT("_setName(name: string): void")
    .function("_setName", &Something::setName);
```

**特点:**
- 单个构造函数(需要名称参数)
- 公共方法 `getName`
- 私有方法 `_setName`

### class AnotherClass

更复杂的类,支持多个构造函数重载。

```cpp
class_<AnotherClass>("AnotherClass")
    TS_EXPORT("new(): AnotherClass")
    .constructor<>()
    TS_EXPORT("new(name: string, thing: Something): AnotherClass")
    .constructor<std::string,Something>()
    TS_EXPORT("get(): Something")
    .function("get", &AnotherClass::get);
```

**特点:**
- 两个构造函数重载:无参数和带参数
- 构造函数参数包含另一个类实例(`Something`)
- 公共方法 `get` 返回类实例

### struct SomeValueObject

值对象,用于在 JavaScript 和 C++ 之间传递数据。

```cpp
value_object<SomeValueObject>("SomeValueObject")
    /**
        The number of columns that the frobulator needs.
        @type @optional number
     */
    .field("columns", &SomeValueObject::columns)
    /**
     *   The object associated with the frobulator.
     *   @type AnotherClass
     */
    .field("object", &SomeValueObject::object)
    /** @type string*/
    .field("name", &SomeValueObject::slot)
    /**
      *  @type boolean
      */
    .field("isInteger", &SomeValueObject::isInteger);
```

**字段类型:**
- `columns`: 可选的数字
- `object`: 类实例引用
- `name`: 字符串
- `isInteger`: 布尔值

## 公共 API 函数

### 模块函数

#### _privateFunction2

```cpp
TS_PRIVATE_EXPORT("_privateFunction2(x: number, y: number): number")
function("_privateFunction2", optional_override([](int x, int y)->size_t {
    return x * y;
}));
```

私有函数,计算两个整数的乘积。

#### publicFunction2

```cpp
TS_EXPORT("publicFunction2(input: string): void")
function("publicFunction2", optional_override([](std::string s)->void {
    printf("Hello %s\n", s.c_str());
}));
```

公共函数,打印字符串到控制台。

#### _privateFunction1

```cpp
TS_PRIVATE_EXPORT("_privateFunction1(ptr: number): number;")
function("_privateFunction1", &SkCanvas::whatever);
```

私有函数,接收指针参数(函数签名包含分号)。

#### publicFunction1

```cpp
TS_EXPORT("publicFunction1(): boolean;")
function("publicFunction1", &SkCanvas::blerg);
```

公共函数,返回布尔值(函数签名包含分号)。

### 常量定义

#### hasBird

```cpp
/**
 *  @type boolean
 */
constant("hasBird", true);
```

布尔常量,值为 `true`。

#### SOME_FLAG

```cpp
/**
 *  This is the flag which is a lot of fun.
 *  It is used in a variety of ways.
 *  #funwithflags
 *  @type number
 */
constant("SOME_FLAG", 0x2);
```

数字常量,值为十六进制 `0x2`,包含多行文档注释。

#### optionalConst

```cpp
#ifdef SK_EXTRA_FEATURE
    /**
     *  This is set if the extra feature is compiled in.
     *  @type @optional string
     */
    constant("optionalConst", "foo");
#endif
```

可选常量,仅在定义 `SK_EXTRA_FEATURE` 宏时存在。

## 内部实现细节

### 导出宏的使用

文件使用了两种导出宏:

1. **TS_PRIVATE_EXPORT**: 导出私有 API,函数名以 `_` 开头
2. **TS_EXPORT**: 导出公共 API,无前缀

### 类型注解格式

#### 函数签名

```cpp
TS_EXPORT("publicFunction2(input: string): void")
```
- TypeScript 风格的函数签名
- 包含参数名、类型和返回类型

#### 字段类型

```cpp
/** @type number */
/** @type @optional string */
```
- 使用 `@type` 标记指定类型
- 使用 `@optional` 标记可选字段

### 注释格式

文件包含多种注释格式:

#### 单行注释

```cpp
/** @type number */
```

#### 多行注释

```cpp
/**
 *  This is the flag which is a lot of fun.
 *  It is used in a variety of ways.
 *  #funwithflags
 *  @type number
 */
```

#### 文档注释

```cpp
/**
 * Returns a Something with the provided name.
 * @param name
 */
```

### 条件编译

```cpp
#ifdef SK_EXTRA_FEATURE
    constant("optionalConst", "foo");
#endif
```

用于测试可选常量的生成。

## 依赖关系

### 依赖的头文件

```cpp
#include <string>
#include "experimental/tskit/bindings/bindings.h"
```

### 生成的输出

对应的输出文件: `expectedambientnamespace1.d.ts`

```typescript
declare namespace namespace_one {
    export interface Bindings {
        _privateFunction1(ptr: number): number;
        _privateFunction2(x: number, y: number): number;

        publicFunction1(): boolean;
        publicFunction2(input: string): void;

        readonly AnotherClass: AnotherClassConstructor;
        readonly Something: SomethingConstructor;

        readonly SOME_FLAG: number;
        readonly hasBird: boolean;
        readonly optionalConst?: string;
    }

    export interface AnotherClassConstructor {
        new(): AnotherClass;
        new(name: string, thing: Something): AnotherClass;
    }

    export interface SomethingConstructor {
        new(name: string): Something;
    }

    export interface AnotherClass extends embind.EmbindObject<AnotherClass> {
        get(): Something;
    }

    export interface Something extends embind.EmbindObject<Something> {
        _setName(name: string): void;

        getName(): string;
    }

    export interface SomeValueObject {
        columns?: number,
        isInteger: boolean,
        name: string,
        object: AnotherClass,
    }
}
```

## 设计模式与设计决策

### 1. 覆盖所有功能点

文件设计为包含所有支持的绑定模式:
- 多个类定义
- 构造函数重载
- 公共和私有方法
- 值对象定义
- 常量定义
- 可选字段和常量

### 2. 测试边缘情况

- 函数签名有无分号
- 多行文档注释
- 条件编译的可选常量
- 可选字段类型注解

### 3. 字母顺序验证

通过刻意使用非字母顺序定义,测试排序功能:
- `publicFunction2` 在 `publicFunction1` 之前定义
- `AnotherClass` 在 `Something` 之前定义

### 4. 类型系统完整性

包含各种类型:
- 基本类型: `number`, `string`, `boolean`
- 类实例: `Something`, `AnotherClass`
- 可选类型: `@optional number`

## 性能考量

作为测试数据文件,性能不是主要考虑因素,但文件设计具有以下特点:

### 1. 文件大小适中

- 112 行代码
- 足够复杂以测试所有功能
- 足够小以快速解析

### 2. 解析复杂度

- 包含多种绑定模式
- 测试解析器的健壮性
- 验证正则表达式的正确性

### 3. 输出验证

- 生成的输出格式清晰
- 便于手动验证正确性
- 易于发现解析错误

## 相关文件

1. **experimental/tskit/go/gen_types/gen_types.go**
   - 解析此文件的工具
   - 生成类型定义

2. **experimental/tskit/go/gen_types/testdata/expectedambientnamespace1.d.ts**
   - 预期的输出文件
   - 用于验证生成结果

3. **experimental/tskit/go/gen_types/gen_types_test.go**
   - 使用此文件的测试
   - 验证解析和生成逻辑

4. **experimental/tskit/bindings/bindings.h**
   - 定义 `TS_EXPORT` 和 `TS_PRIVATE_EXPORT` 宏
   - 实际绑定代码使用的头文件

5. **experimental/tskit/bindings/core.cpp**
   - 实际的核心绑定实现
   - 与测试文件格式类似

6. **experimental/tskit/bindings/extension.cpp**
   - 实际的扩展绑定实现
   - 与测试文件格式类似
