# SkSLGLSL — GLSL 版本枚举定义

> 源文件：[`src/sksl/SkSLGLSL.h`](../../src/sksl/SkSLGLSL.h)

## 概述

SkSLGLSL.h 定义了 SkSL 编译器所支持的 GLSL（OpenGL Shading Language）版本枚举。该枚举用于指定 SkSL 编译器在生成 GLSL 代码时应目标的着色语言版本。调用方应将实际的 GLSL 版本向下取整到枚举中的某个值。

该文件仅 58 行，是一个纯头文件，不包含任何实现代码。

## 架构位置

```
SkSL 编译器
  └── 后端代码生成
        └── GLSL 后端
              └── GLSLGeneration 枚举 (SkSLGLSL.h)
```

`GLSLGeneration` 枚举被 SkSL 的 GLSL 代码生成器使用，以确定生成的着色器代码应遵循哪个版本的 GLSL 规范。它在 SkSL 编译管线的后端阶段起作用。

## 主要类与结构体

### `GLSLGeneration` 枚举

```cpp
enum class GLSLGeneration {
    k110,           // Desktop GLSL 1.10 / ES2
    k100es = k110,  // ES GLSL 1.00（别名，等同于 k110）
    k130,           // Desktop GLSL 1.30
    k140,           // Desktop GLSL 1.40
    k150,           // Desktop GLSL 1.50
    k330,           // Desktop GLSL 3.30 / ES GLSL 3.00
    k300es = k330,  // ES GLSL 3.00（别名，等同于 k330）
    k400,           // Desktop GLSL 4.00
    k420,           // Desktop GLSL 4.20
    k310es,         // ES GLSL 3.10
    k320es,         // ES GLSL 3.20
};
```

该枚举是强类型枚举（`enum class`），位于 `SkSL` 命名空间内。

## 公共 API 函数

本文件不包含函数定义，仅定义枚举类型。

## 内部实现细节

### Desktop 与 ES 版本的映射关系

枚举通过别名（alias）建立了 Desktop GLSL 和 OpenGL ES GLSL 之间的对应关系：
- `k100es = k110`：ES 2.0 着色语言基于 Desktop GLSL 1.20，在此映射到 1.10
- `k300es = k330`：ES 3.0 着色语言与 Desktop GLSL 3.30 功能大致对等

这种设计允许 SkSL 编译器在处理 Desktop 和 ES 目标时使用相同的枚举值，简化了条件分支逻辑。

### ES 3.10 和 3.20 的独立枚举

`k310es` 和 `k320es` 没有对应的 Desktop GLSL 别名，因为这些 ES 版本引入了一些 Desktop GLSL 中不直接对应的功能。源码中的 TODO 注释提到未来可能需要更细粒度的 `GLSLCap` 对象。

## 依赖关系

本文件没有任何 `#include` 依赖，是一个完全自包含的头文件。

## 设计模式与设计决策

- **有限版本集合**：不尝试覆盖所有 GLSL 版本，而是选择了 Skia 实际构建着色器所需的有限子集，简化了后端代码生成的复杂度。
- **向下取整策略**：要求调用方将 GLSL 版本向下取整到枚举中最近的值，保证生成的代码在该版本及更高版本上都能运行。
- **强类型枚举**：使用 `enum class` 防止隐式转换和命名冲突。

## 性能考量

作为一个枚举定义文件，不涉及运行时性能问题。枚举值在编译期确定，用于代码生成阶段的版本判断，不产生运行时开销。

## 相关文件

- `src/sksl/SkSLProgramSettings.h` — 程序设置（引用 GLSL 相关配置）
- `src/sksl/codegen/SkSLGLSLCodeGenerator.h` — GLSL 代码生成器（使用此枚举）
- `src/gpu/ganesh/glsl/GrGLSLShaderBuilder.h` — Ganesh GLSL 着色器构建器
