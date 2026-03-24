# SkSL Mangler（名称修饰器）

> 源文件：[src/sksl/SkSLMangler.h](../../src/sksl/SkSLMangler.h)、[src/sksl/SkSLMangler.cpp](../../src/sksl/SkSLMangler.cpp)

## 概述

`Mangler` 是 SkSL 编译器中的一个轻量级工具类，负责在内联（inlining）过程中为变量和符号生成唯一名称。当函数被内联到调用点时，原函数中的局部变量需要被重命名，以避免与当前作用域中已有的变量名发生冲突。`Mangler` 通过在基础名称前添加数字前缀（如 `_123_varName`）来实现这一目标，并通过查询符号表（SymbolTable）确保生成的名称在当前作用域中是唯一的。

## 架构位置

`Mangler` 位于 SkSL 编译器的核心层，主要服务于内联器（Inliner）。在 SkSL 编译管道中，它处于编译优化阶段：

```
SkSL 源代码 -> 解析器 -> IR 树 -> [Inliner 使用 Mangler 生成唯一名称] -> 代码生成
```

`Mangler` 隶属于 `SkSL` 命名空间，与 `SymbolTable` 紧密协作。

## 主要类与结构体

### `class Mangler`

名称修饰器的核心类，具有以下成员：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fCounter` | `int` | 私有计数器，用于生成递增的数字前缀，初始值为 0 |

## 公共 API 函数

### `std::string uniqueName(std::string_view baseName, SymbolTable* symbolTable)`

根据给定的基础名称和符号表，生成一个在该符号表中唯一的新名称。

- **参数**：
  - `baseName`：原始变量名，可能包含 `$` 前缀或之前的修饰前缀
  - `symbolTable`：当前作用域的符号表，用于检查名称冲突
- **返回值**：格式为 `_<counter>_<baseName>` 的唯一名称字符串
- **行为**：
  1. 移除 `$` 前缀（私有名称标记）
  2. 移除已有的修饰前缀（如 `_123_`），使代码更易读
  3. 移除可能导致 OpenGL 连续下划线错误的前导下划线
  4. 递增计数器直到找到符号表中不存在的名称

### `void reset()`

将内部计数器重置为 0。在新一轮编译开始时调用。

## 内部实现细节

### 名称构造的性能优化

`uniqueName` 方法使用栈上分配的 256 字节字符数组手动组装结果字符串，而非使用 `std::string` 的拼接操作。这是因为该函数是性能热点——在内联大量函数时会被频繁调用。

```cpp
char uniqueName[256];
uniqueName[0] = '_';
char* endPtr = SkStrAppendS32(uniqueName + 1, fCounter++);
*endPtr++ = '_';
```

### 前缀剥离逻辑

当内联器多次运行时，变量名可能已经被修饰过。函数会检测并移除形如 `_数字_` 的已有前缀，以避免名称无限增长（如 `_1__2__3_x`），保持生成代码的可读性。

### 名称截断

当基础名称过长，超过 256 字节缓冲区的剩余空间时，名称会被截断以适应缓冲区大小。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkString.h` (`SkStrAppendS32`) | 高效地将整数转换为字符串 |
| `SkStringView.h` (`skstd::starts_with`) | 字符串前缀检测 |
| `SkSLSymbolTable` | 查询名称是否已存在 |
| `SkTypes.h` (`SkASSERT`) | 断言检查 |

## 设计模式与设计决策

1. **有状态计数器**：使用递增计数器而非随机数或哈希，保证生成的名称可预测且可复现，有助于调试。
2. **惰性冲突解决**：通过循环递增计数器来避免冲突，而非一次性计算无冲突名称。这在大多数情况下只需一次迭代。
3. **与 OpenGL 规范兼容**：特别处理前导下划线，以遵守 OpenGL 禁止连续双下划线的规则。
4. **可重置性**：提供 `reset()` 方法使得同一 `Mangler` 实例可以在多次编译中复用。

## 性能考量

- 使用栈分配的字符数组和手动字符串构造，避免堆分配开销
- 使用 `SkStrAppendS32` 进行高效的整数到字符串转换
- 使用 `string_view` 减少不必要的字符串拷贝
- 符号表查找使用 `string_view` 避免在循环中创建临时 `std::string` 对象
- 该函数被标记为性能热点（"performance hotspot"），在内联密集型编译中可能被调用数千次

## 相关文件

- `src/sksl/SkSLInliner.h` / `SkSLInliner.cpp` —— 内联器，`Mangler` 的主要使用者
- `src/sksl/ir/SkSLSymbolTable.h` —— 符号表，用于名称唯一性检查
- `src/sksl/SkSLCompiler.h` —— 编译器，持有 `Mangler` 实例
