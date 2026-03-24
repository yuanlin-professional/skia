# LexUtil

> 源文件: src/sksl/lex/LexUtil.h

## 概述

`LexUtil` 提供词法分析器生成工具的基础宏定义和常量,包括断言、错误处理和无效值标记,为独立于 Skia 主代码库的词法工具提供轻量级基础设施。

## 架构位置

位于词法分析器生成工具基础层,被所有词法工具组件使用。

## 主要定义

### INVALID
```cpp
#define INVALID -1
```
表示无效状态、索引或 token ID。

### SK_ABORT
```cpp
#define SK_ABORT(...) (fprintf(stderr, __VA_ARGS__), abort())
```
打印错误消息并终止程序。

### SkASSERT
```cpp
#define SkASSERT(x) \
    (void)((x) || (SK_ABORT("failed SkASSERT(%s): %s:%d\n", #x, __FILE__, __LINE__), 0))
```
断言条件为真,否则终止并显示详细错误信息。

### SkUNREACHABLE
```cpp
#define SkUNREACHABLE (SK_ABORT("unreachable"))
```
标记不应执行到的代码路径。

## 设计决策

采用最小依赖原则,只使用 C 标准库,确保词法工具可独立编译。使用宏而非函数以实现零开销的断言和位置追踪。

## 相关文件

被 `NFAState.h`, `DFAState.h`, `Main.cpp` 等所有词法工具文件包含。
