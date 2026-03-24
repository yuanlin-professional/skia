# GrGLVaryingHandler

> 源文件
> - src/gpu/ganesh/gl/GrGLVaryingHandler.h

## 概述

`GrGLVaryingHandler` 是 Ganesh OpenGL 后端中用于处理 varying 变量的类。它继承自 `GrGLSLVaryingHandler`，为 OpenGL 提供了特定的 varying 管理实现。该类非常轻量，主要作用是作为 GL 特定的类型包装器，实际的 varying 管理逻辑在基类中实现。

## 架构位置

```
GrGLSLVaryingHandler (基类)
    ↓
GrGLVaryingHandler (OpenGL 特化) ← 当前模块
    ↓
GrGLProgramBuilder
```

该模块是 OpenGL 着色器构建系统中 varying 管理的专用接口。

## 主要类与结构体

### GrGLVaryingHandler

**继承关系**：
- 基类：`GrGLSLVaryingHandler`

**关键成员变量**：
无额外成员变量，完全继承基类成员。

## 公共 API 函数

### 构造函数

```cpp
GrGLVaryingHandler(GrGLSLProgramBuilder* program)
```

**功能**：创建 varying 处理器实例。

**参数**：
- `program`: 程序构建器指针

### onFinalize（私有虚函数）

```cpp
void onFinalize() override {}
```

**功能**：完成 varying 设置的最终化步骤。OpenGL 实现为空，因为不需要额外的最终化操作。

## 内部实现细节

### 最小化设计

OpenGL 的 varying 处理相对简单：
- 不需要特殊的声明格式
- 不需要额外的绑定操作
- 自动通过名称匹配连接顶点和片段着色器

因此 `onFinalize()` 实现为空操作。

### 与其他后端的对比

其他图形 API 可能需要在 `onFinalize` 中：
- Vulkan：记录 varying 的 location 布局
- Metal：处理 stage-in/stage-out 结构
- OpenGL：无需额外操作

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLSLVaryingHandler` | 基类，提供核心功能 |
| `GrGLSLProgramBuilder` | 程序构建器 |
| `GrGLProgramDataManager` | 程序数据管理 |
| `GrTypesPriv` | 类型定义 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrGLProgramBuilder` | 创建和使用 varying 处理器 |

## 设计模式与设计决策

### 空实现模式

`onFinalize()` 的空实现体现了模板方法模式：
- 基类定义算法框架
- 子类根据需要覆盖特定步骤
- OpenGL 不需要最终化，因此为空

### 友元关系

```cpp
friend class GrGLProgramBuilder;
```

允许 `GrGLProgramBuilder` 访问私有成员，保持封装性的同时提供必要的访问权限。

## 性能考量

### 零开销抽象

该类几乎没有性能开销：
- 无虚函数调用开销（`onFinalize` 内联为空）
- 无额外内存分配
- 编译器可以完全优化掉空函数

### 代码简洁性

通过继承获得所有 varying 管理功能，无需重复实现。

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `src/gpu/ganesh/glsl/GrGLSLVarying.h/cpp` | 基类实现 |
| `src/gpu/ganesh/gl/builders/GrGLProgramBuilder.h` | 使用者 |
| `src/gpu/ganesh/gl/GrGLProgramDataManager.h` | 数据管理 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 类型定义 |
