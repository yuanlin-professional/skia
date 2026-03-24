# FuzzGrStyledShape (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzGrStyledShape.cpp

## 概述

测试 Ganesh GPU 后端的样式化形状类 `GrStyledShape`,该类封装了路径和样式(描边、填充)信息,用于 GPU 路径渲染。

## 架构位置

测试 `src/gpu/ganesh/GrStyledShape.h` 中的形状样式处理。

## 主要类与结构体

**LLVMFuzzerTestOneInput**: 最大 4000 字节
**fuzz_GrStyledShape**: 创建随机形状和样式组合

## 内部实现细节

测试包括:
- 路径的样式化(描边宽度、连接样式、端点样式)
- 形状简化和规范化
- 边界框计算
- GPU 友好的表示转换

## 依赖关系

- `src/gpu/ganesh/GrStyledShape.cpp`: 实现
- `include/core/SkPathEffect.h`: 路径效果

## 设计模式与设计决策

**形状抽象**: GrStyledShape 为 GPU 渲染提供统一的形状接口。

## 性能考量

形状简化和样式应用可能涉及复杂的几何运算。

## 相关文件

- `fuzz/FuzzGrStyledShape.cpp`: 独立版本
- `src/gpu/ganesh/GrShape.cpp`: 基础形状类
