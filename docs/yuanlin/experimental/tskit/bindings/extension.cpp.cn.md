# extension.cpp C++ 扩展绑定

> 源文件: experimental/tskit/bindings/extension.cpp

## 概述

`extension.cpp` 是 TSKit 框架的 C++ 扩展绑定实现文件,使用 Emscripten 的 Embind 库将 C++ 类和函数暴露给 JavaScript/TypeScript。该文件定义了扩展功能的核心实现,包括矩形几何计算、对象传递处理,以及 `Extension` 类的完整绑定。

文件的核心职责:
1. 定义 `Extension` 类,提供属性的 getter 和 setter 方法
2. 实现 `_privateExtension` 函数,计算包含特定点的矩形数量
3. 定义 `CompoundObj` 结构体,实现跨语言数据传递
4. 使用 `TS_EXPORT` 和 `TS_PRIVATE_EXPORT` 宏标记类型信息,供自动生成类型定义

该文件展示了如何将 C++ 的面向对象特性和高性能计算能力通过 WebAssembly 暴露给 Web 平台。

## 架构位置

```
experimental/tskit/
├── bindings/
│   ├── bindings.h        # 宏定义
│   ├── extension.cpp     # C++ 扩展实现(当前文件)
│   ├── extension.d.ts    # 自动生成的类型定义
│   └── core.cpp          # C++ 核心实现
├── interface/
│   └── extension.ts      # TypeScript 封装层
└── npm_build/
    └── bundle.js         # 编译输出
```

**调用链:**
```
TypeScript (extension.ts)
    ↓
JavaScript Module._privateExtension
    ↓
WebAssembly
    ↓
C++ (extension.cpp)
```

## 主要类与结构体

### struct SkRect

简化的矩形结构体,用于几何计算。

```cpp
struct SkRect {
    SkScalar fLeft;
    SkScalar fTop;
    SkScalar fRight;
    SkScalar fBottom;

    bool contains(SkScalar x, SkScalar y) const {
        return x >= fLeft && x < fRight && y >= fTop && y < fBottom;
    }
};
```

**字段:**
- `fLeft`: 左边界 x 坐标
- `fTop`: 上边界 y 坐标
- `fRight`: 右边界 x 坐标
- `fBottom`: 下边界 y 坐标

**方法:**
- `contains(x, y)`: 判断点是否在矩形内(左闭右开区间)

**注意:**
- 这是为 POC 简化的版本,避免链接完整的 Skia 库
- 实际 Skia 中有更复杂的 SkRect 实现

### class Extension

扩展类,管理一个字符串属性。

```cpp
class Extension {
public:
    Extension(): fProp("foo") {}
    Extension(std::string n): fProp(n) {}

    const std::string getProp() {
        return fProp;
    }

    void setProp(std::string p) {
        fProp = p;
    }

private:
    std::string fProp;
};
```

**构造函数:**
1. 无参构造: 使用默认值 `"foo"`
2. 带参构造: 使用提供的名称

**方法:**
- `getProp()`: 返回属性值
- `setProp(p)`: 设置属性值

**私有成员:**
- `fProp`: 字符串属性

### struct CompoundObj

复合对象,用于在 JavaScript 和 C++ 之间传递数据。

```cpp
struct CompoundObj {
    int alpha;
    std::string beta;
    float gamma;
};
```

**字段:**
- `alpha`: 整数
- `beta`: 字符串
- `gamma`: 浮点数

**用途:**
- 演示 value_object 绑定
- 展示如何传递复杂数据结构

## 公共 API 函数

### _privateExtension

```cpp
TS_PRIVATE_EXPORT("_privateExtension(rPtr: number, len: number): number")
function("_privateExtension", optional_override([](uintptr_t rPtr, size_t len)->int {
    int containsPoint = 0;
    SkRect* rects = reinterpret_cast<SkRect*>(rPtr);
    for (int i = 0; i < len; i++) {
        if (rects[i].contains(5, 5)) {
            containsPoint++;
        }
    }
    return containsPoint;
}));
```

**功能:**
计算有多少个矩形包含点 (5, 5)。

**参数:**
- `rPtr`: 矩形数组在 WASM 堆上的指针
- `len`: 矩形数量

**返回:**
- 包含点 (5, 5) 的矩形数量

**实现细节:**
1. 将指针转换为 `SkRect*` 类型
2. 遍历所有矩形
3. 对每个矩形调用 `contains(5, 5)`
4. 统计返回 `true` 的数量

**性能特点:**
- O(n) 时间复杂度
- 零内存分配
- 内联的 `contains` 调用

### _withObject

```cpp
TS_PRIVATE_EXPORT("_withObject(obj: CompoundObj): void")
function("_withObject", optional_override([](CompoundObj o)->void {
    printf("Object %d %s %f\n", o.alpha, o.beta.c_str(), o.gamma);
}));
```

**功能:**
接收复合对象并打印其内容。

**参数:**
- `o`: CompoundObj 实例

**行为:**
- 打印对象的所有字段到标准输出
- 格式: "Object [alpha] [beta] [gamma]"

**用途:**
- 演示对象传递
- 调试和日志记录

## 内部实现细节

### Emscripten 绑定宏

#### EMSCRIPTEN_BINDINGS

```cpp
EMSCRIPTEN_BINDINGS(Extension) {
    // 绑定定义
}
```

**作用:**
- 定义一个绑定模块,名为 "Extension"
- 在 Emscripten 编译时处理
- 生成 JavaScript 接口代码

#### function 绑定

```cpp
function("_privateExtension", optional_override([](uintptr_t rPtr, size_t len)->int {
    // 实现
}));
```

**组成:**
1. 函数名: `"_privateExtension"`
2. 实现: lambda 表达式
3. `optional_override`: 启用函数重载和可选参数支持

#### class_ 绑定

```cpp
class_<Extension>("Extension")
    .constructor<>()
    .constructor<std::string>()
    .function("getProp", &Extension::getProp)
    .function("_setProp", &Extension::setProp);
```

**链式调用:**
1. `class_<Extension>("Extension")`: 开始绑定类
2. `.constructor<>()`: 绑定无参构造函数
3. `.constructor<std::string>()`: 绑定带参构造函数
4. `.function(...)`: 绑定成员函数

#### value_object 绑定

```cpp
value_object<CompoundObj>("CompoundObj")
    .field("alpha", &CompoundObj::alpha)
    .field("beta", &CompoundObj::beta)
    .field("gamma", &CompoundObj::gamma);
```

**特点:**
- 自动映射 JavaScript 对象到 C++ 结构体
- 支持双向转换
- 每个字段需要 `@type` 注解

### 类型注解系统

#### 函数签名

```cpp
TS_PRIVATE_EXPORT("_privateExtension(rPtr: number, len: number): number")
```

**格式:**
- TypeScript 风格的函数签名
- 参数名和类型
- 返回类型

**用途:**
- 由 `gen_types.go` 解析
- 生成 `extension.d.ts`

#### 字段类型

```cpp
/** @type number */
.field("alpha", &CompoundObj::alpha)
```

**格式:**
- JSDoc 风格的类型注解
- 放在 `.field` 调用之前

#### 可选字段

```cpp
/**
 * This field (gamma) should be documented.
 * The default value is 1.0 if not set.
 * @type @optional number
 */
.field("gamma", &CompoundObj::gamma);
```

**标记:**
- `@optional` 表示字段可选
- 生成的 TypeScript 类型使用 `?`

### 指针和内存管理

#### 指针转换

```cpp
SkRect* rects = reinterpret_cast<SkRect*>(rPtr);
```

**安全性考虑:**
- `reinterpret_cast` 是不安全的转换
- 依赖 JavaScript 层正确传递指针
- 无边界检查

**改进建议:**
- 添加指针有效性检查
- 验证数组长度
- 使用智能指针

#### 内存布局

```cpp
for (int i = 0; i < len; i++) {
    if (rects[i].contains(5, 5)) {
```

**假设:**
- 数组在内存中连续存储
- 每个 `SkRect` 占用 4 * sizeof(float) 字节
- 与 JavaScript 传递的 Float32Array 布局一致

## 依赖关系

### 依赖的头文件

```cpp
#include <string>
#include "experimental/tskit/bindings/bindings.h"
```

**bindings.h 提供:**
- `TS_EXPORT` 和 `TS_PRIVATE_EXPORT` 宏
- Emscripten 的头文件引用

### 生成的输出

1. **extension.d.ts**
   - 由 `gen_types.go` 生成
   - 包含类型定义

2. **WebAssembly 模块**
   - 由 Emscripten 编译
   - 包含实际的机器码

### 被调用的代码

1. **interface/extension.ts**
   - 调用 `Module._privateExtension`
   - 调用 `Module._withObject`

### 依赖图

```
bindings.h
    ↓
extension.cpp (编译)
    ↓
├── extension.wasm (运行时)
└── extension.d.ts (类型定义)
    ↓
extension.ts (TypeScript 封装)
```

## 设计模式与设计决策

### 1. 外观模式 (Facade Pattern)

TypeScript 层为 C++ 函数提供更友好的接口:
```typescript
// TypeScript 外观
publicExtension(myRects: InputFlattenedRectArray): number

// C++ 实现
_privateExtension(rPtr: uintptr_t, len: size_t): int
```

### 2. 适配器模式 (Adapter Pattern)

将 JavaScript 数组适配为 C++ 指针:
```
Float32Array → WASM 堆指针 → SkRect*
```

### 3. 值对象模式 (Value Object Pattern)

`CompoundObj` 作为值对象:
- 简单的数据容器
- 无复杂行为
- 按值传递

### 4. 命名约定

- **私有函数**: `_` 前缀 (如 `_privateExtension`)
- **公共方法**: 无前缀 (如 `getProp`)
- **私有方法暴露**: `_` 前缀 (如 `_setProp`)

### 5. 构造函数重载

```cpp
Extension()
Extension(std::string n)
```

- 提供灵活性
- 支持默认值和自定义值
- 映射到 TypeScript 的构造函数重载

## 性能考量

### 1. 指针传递效率

- 零拷贝:直接访问 WASM 堆上的数据
- O(1) 指针转换
- 避免 JavaScript ↔ C++ 数据拷贝

### 2. 循环性能

```cpp
for (int i = 0; i < len; i++) {
    if (rects[i].contains(5, 5)) {
        containsPoint++;
    }
}
```

- 紧密循环,编译器易于优化
- `contains` 可能被内联
- 缓存友好的顺序访问

### 3. 字符串处理

```cpp
std::string fProp;
```

- 小字符串优化 (SSO)
- 对于短字符串(<15字符),无堆分配
- 长字符串会分配堆内存

### 4. 对象传递开销

`CompoundObj` 传递:
- 按值传递,涉及拷贝
- 对于小对象(<32字节),开销可接受
- Emscripten 自动处理序列化

### 5. printf 性能

```cpp
printf("Object %d %s %f\n", ...);
```

- I/O 操作,相对慢
- 仅用于调试,生产环境应移除
- 可替换为日志系统

## 相关文件

1. **experimental/tskit/bindings/bindings.h**
   - 定义 `TS_EXPORT` 和 `TS_PRIVATE_EXPORT` 宏

2. **experimental/tskit/bindings/extension.d.ts**
   - 自动生成的类型定义

3. **experimental/tskit/interface/extension.ts**
   - TypeScript 封装层
   - 调用 `_privateExtension` 和 `_withObject`

4. **experimental/tskit/interface/memory.ts**
   - 提供内存管理工具
   - 为数组复制提供支持

5. **experimental/tskit/go/gen_types/gen_types.go**
   - 解析此文件生成类型定义

6. **Emscripten SDK**
   - 提供 `emscripten.h` 和 `emscripten/bind.h`
   - 编译为 WebAssembly

7. **include/core/SkRect.h**
   - 完整的 Skia SkRect 实现
   - 此文件使用简化版本
