# SkSLCodeGenerator

> 源文件: src/sksl/codegen/SkSLCodeGenerator.h

## 概述

`CodeGenerator` 是所有 SkSL 代码生成器的抽象基类,定义将 SkSL IR 转换为目标着色器语言的通用接口。派生类实现GLSL、SPIR-V、Metal 等后端。

## 架构位置

位于编译流程的最终阶段:
```
SkSL IR → CodeGenerator (基类) → 具体后端
                          ├── GLSLCodeGen
                          ├── SPIRVCodeGen
                          ├── MetalCodeGen
                          └── WGSLCodeGen
```

## 主要类与结构体

### CodeGenerator
```cpp
class CodeGenerator
```

**核心方法:**
- `generateCode()`: 生成目标代码的主入口
- `writeProgramElement()`: 处理顶层元素
- `writeStatement()`: 生成语句代码
- `writeExpression()`: 生成表达式代码

## 设计决策

使用访问者模式遍历 IR 树,每个后端实现特定的代码生成逻辑。提供通用的辅助方法简化派生类实现。

## 相关文件

- `SkSLGLSLCodeGenerator.h`: GLSL 后端
- `SkSLSPIRVCodeGenerator.h`: SPIR-V 后端
- `SkSLMetalCodeGenerator.h`: Metal 后端
- `src/sksl/ir/*`: IR 节点定义
