# Core TypeScript 类型声明

> 源文件: `experimental/tskit/bindings/core.d.ts`

## 概述

`core.d.ts` 是由 `gen_types.go` 自动生成的 TypeScript 类型声明文件，定义了核心绑定模块的接口类型。它对应 `core.cpp` 中通过 embind 导出的函数和类。

## 架构位置

位于 `experimental/tskit/bindings/` 目录，是 TSKit 类型系统的核心声明文件。通过三斜杠指令引用 `embind.d.ts` 作为基础类型。

## 主要类与结构体

- **`Bindings`**: 模块级函数接口
  - `_privateFunction(x, y)`: 私有乘法函数
  - `publicFunction(input)`: 公共打印函数
  - `readonly Something`: 构造器引用
- **`SomethingConstructor`**: Something 类的构造器接口
  - `new(name: string)`: 创建实例
- **`Something`**: 绑定对象接口，继承 `EmbindObject<Something>`
  - `setName(name)`: 设置名称
  - `getName()`: 获取名称

## 公共 API 函数

通过接口声明暴露，无独立函数实现。

## 内部实现细节

- 使用 `declare namespace core` 声明环境命名空间
- `SomethingConstructor` 分离构造器类型，支持 TypeScript 的 `new` 语法
- `Something` 继承 `embind.EmbindObject<Something>` 获得生命周期管理方法

## 依赖关系

- `embind.d.ts`: 基础类型声明（通过三斜杠引用）

## 设计模式与设计决策

- 自动生成模式：由 Go 工具 `gen_types.go` 从 C++ 绑定代码提取类型信息
- 构造器模式：使用独立的 `Constructor` 接口，与 embind 的类暴露方式一致
- `readonly` 修饰构造器引用，防止运行时篡改

## 性能考量

无。纯类型声明文件，不包含运行时代码。

## 相关文件

- `experimental/tskit/bindings/core.cpp`: C++ 绑定实现
- `experimental/tskit/bindings/embind.d.ts`: 基础类型
- `experimental/tskit/bindings/extension.d.ts`: 扩展模块类型
