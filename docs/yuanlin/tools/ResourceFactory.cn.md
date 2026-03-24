# ResourceFactory - 资源工厂函数指针

> 源文件: `tools/ResourceFactory.h`

## 概述

`ResourceFactory.h` 声明了一个全局函数指针 `gResourceFactory`,用于在测试和工具中加载资源文件。不同的构建目标可以提供不同的实现(如从文件系统读取或从嵌入式资源读取)。

## 架构位置

属于 Skia 工具层的资源加载抽象接口。

## 主要类与结构体

- **`gResourceFactory`**: `sk_sp<SkData> (*)(const char*)` 类型的全局函数指针

## 设计模式与设计决策

- **函数指针注入**: 通过全局函数指针实现编译时可替换的资源加载策略

## 依赖关系

- `include/core/SkData.h`

## 相关文件

- 各构建目标中 `gResourceFactory` 的具体实现
