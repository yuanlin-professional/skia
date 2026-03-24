# SkSLProgramWriter

> 源文件: src/sksl/transform/SkSLProgramWriter.h

## 概述

`ProgramWriter` 是可写的程序访问者基类,允许转换器修改 IR 树。与只读的 `ProgramVisitor` 对应,提供修改节点的能力。

## 架构位置

作为所有 IR 转换器的基类:

```
TProgramVisitor<ProgramWriterTypes>
  ↓
ProgramWriter (本类) ← 可写访问者
  ↓
各种转换器继承此类
```

## 主要类与结构体

### ProgramWriter

```cpp
class ProgramWriter : public TProgramVisitor<ProgramWriterTypes>
```

**特性:**
- 提供非 const 的节点访问
- 允许修改表达式和语句
- 支持节点替换和删除

**典型用法:**

```cpp
class MyTransform : public ProgramWriter {
    bool visitExpression(Expression& expr) override {
        // 可以修改 expr
        return INHERITED::visitExpression(expr);
    }
};
```

## 设计决策

与 `ProgramVisitor` 共享模板基类,只是类型参数不同(const vs 非 const)。提供统一的接口,简化转换器的实现。

## 相关文件

- `src/sksl/analysis/SkSLProgramVisitor.h`: 只读访问者
- `src/sksl/transform/*`: 各种转换器实现
- `src/sksl/ir/*`: IR 节点定义
