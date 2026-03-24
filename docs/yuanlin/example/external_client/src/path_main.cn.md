# path_main.cpp - 路径操作（PathOps）示例

> 源文件: `example/external_client/src/path_main.cpp`

## 概述

`path_main.cpp` 是一个极简的示例程序，演示了如何使用 Skia 的 PathOps 模块对两个路径执行布尔运算（Boolean Operations）。该示例创建了两个三角形路径，对它们执行交集（Intersect）操作，并将结果路径数据输出到标准输出。

PathOps 是 Skia 提供的路径布尔运算功能，支持交集、并集、差集、异或等操作，常用于矢量图形编辑器和 SVG 处理中。

## 架构位置

```
Skia 示例程序
├── example/external_client/src/
│   ├── path_main.cpp           <-- 本文件：PathOps 示例
│   └── ...
├── include/core/
│   ├── SkPath.h                <-- 路径类
│   └── SkPathBuilder.h         <-- 路径构建器
└── include/pathops/
    └── SkPathOps.h             <-- 路径布尔运算
```

## 主要类与结构体

本文件不定义新类，使用 Skia 的路径操作 API。

### 使用的核心类型
- `SkPathBuilder` - 路径构建器，用于构造路径几何形状
- `SkPath` - 不可变的路径对象
- `SkPathOps` - 路径布尔运算函数

## 公共 API 函数

### `main(int argc, char** argv)`
程序入口，无需命令行参数。

执行流程：
1. 使用 `SkPathBuilder` 构建第一个三角形路径 (10,10)-(15,5)-(20,10)
2. 使用 `SkPathBuilder` 构建第二个三角形路径 (12,12)-(18,6)-(24,12)
3. 对两条路径执行交集运算 `kIntersect_SkPathOp`
4. 输出结果路径数据

## 内部实现细节

### 路径构建

```cpp
SkPathBuilder pb;
pb.moveTo(10, 10);
pb.lineTo(15, 5);
pb.lineTo(20, 10);
pb.close();
SkPath path1 = pb.detach();
```

`SkPathBuilder` 使用流式 API 构建路径。`detach()` 方法将构建器内部的路径数据移出（零复制），并重置构建器以便构建下一条路径。

### 布尔运算

```cpp
SkPath combined;
if (Op(path1, path2, kIntersect_SkPathOp, &combined)) {
    combined.dump();
}
```

`Op` 函数执行路径布尔运算：
- `path1`：第一个操作数
- `path2`：第二个操作数
- `kIntersect_SkPathOp`：交集运算
- `combined`：输出路径

可用的运算类型：
- `kDifference_SkPathOp` - 差集（path1 - path2）
- `kIntersect_SkPathOp` - 交集
- `kUnion_SkPathOp` - 并集
- `kXOR_SkPathOp` - 异或
- `kReverseDifference_SkPathOp` - 反向差集（path2 - path1）

### 路径调试输出

```cpp
combined.dump();
```

`dump()` 将路径的控制点和动词以人类可读的格式输出到标准输出，用于调试验证。

## 依赖关系

- **Skia 核心**：`SkPath`, `SkPathBuilder`
- **PathOps 模块**：`SkPathOps`
- **C++ 标准库**：`<cstdio>`

## 设计模式与设计决策

1. **Builder 模式**：`SkPathBuilder` 提供了清晰的路径构建接口，将可变的构建过程与不可变的 `SkPath` 对象分离。

2. **detach 语义**：`pb.detach()` 使用移动语义将路径数据从构建器中取出，既避免了复制开销，又自动重置构建器以便复用。

3. **最小化示例**：此示例是所有示例中最简洁的之一（37 行），仅展示 PathOps 的核心用法，无需文件 I/O 或图像处理。

4. **自包含验证**：通过 `dump()` 输出结果路径，用户可以直接验证布尔运算的正确性。

## 性能考量

- **PathOps 算法复杂度**：路径布尔运算的时间复杂度与路径的线段数量相关。对于简单的三角形，运算几乎是即时的。
- **SkPathBuilder 的内存效率**：`detach()` 通过移动而非复制传递路径数据，对于包含大量控制点的复杂路径可以节省显著的内存和时间。
- **无渲染开销**：此示例不涉及任何光栅化或 GPU 操作，纯粹是几何运算。

## 相关文件

- `include/core/SkPath.h` - 路径类定义
- `include/core/SkPathBuilder.h` - 路径构建器
- `include/pathops/SkPathOps.h` - 路径布尔运算 API
- `src/pathops/` - PathOps 实现目录
