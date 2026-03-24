# Extension TypeScript 类型声明

> 源文件: `experimental/tskit/bindings/extension.d.ts`

## 概述

`extension.d.ts` 是由 `gen_types.go` 自动生成的 TypeScript 类型声明文件，定义了扩展绑定模块的接口类型。它对应 `extension.cpp` 中通过 embind 导出的函数、类和值对象。

## 架构位置

位于 `experimental/tskit/bindings/` 目录，是 TSKit 类型系统的扩展模块声明文件。

## 主要类与结构体

- **`Bindings`**: 模块级函数接口
  - `_privateExtension(rPtr, len)`: 矩形包含测试（私有）
  - `_withObject(obj)`: 对象传递测试（私有）
  - `readonly Extension`: 构造器引用
- **`ExtensionConstructor`**: Extension 类构造器
  - `new(name?: string)`: 可选参数构造
- **`Extension`**: 绑定对象接口，继承 `EmbindObject<Extension>`
  - `setProp(p)`: 设置属性
  - `getProp()`: 获取属性
- **`CompoundObj`**: 值对象接口
  - `alpha: number`, `beta: string`, `gamma?: number`（gamma 可选）

## 公共 API 函数

通过接口声明暴露。

## 内部实现细节

- `gamma` 字段标记为可选（`?`），对应 C++ 侧的 `@type @optional` 注释
- `ExtensionConstructor` 支持无参和有参两种构造方式

## 依赖关系

- `embind.d.ts`: 基础类型声明

## 设计模式与设计决策

- 值对象 `CompoundObj` 直接映射为 TypeScript 接口，按值传递
- 可选字段通过 `?` 修饰符表达

## 性能考量

无。纯类型声明文件。

## 相关文件

- `experimental/tskit/bindings/extension.cpp`: C++ 绑定实现
- `experimental/tskit/bindings/core.d.ts`: 核心模块类型
