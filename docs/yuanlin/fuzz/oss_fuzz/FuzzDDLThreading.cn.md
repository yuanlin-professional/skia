# FuzzDDLThreading (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzDDLThreading.cpp

## 概述

测试延迟显示列表(DDL, Deferred Display List)的多线程行为。DDL 允许在后台线程生成渲染命令,然后在GPU线程执行,是 Skia 异步渲染的核心机制。

## 架构位置

测试 `include/core/SkDeferredDisplayList.h` 和相关线程安全性。

## 主要类与结构体

**LLVMFuzzerTestOneInput**: 最大 4000 字节输入
**fuzz_DDLThreadingGL**: 创建多线程场景,并发生成和执行 DDL

## 内部实现细节

测试场景:
- 多个线程同时创建 DDL
- DDL 的传递和所有权转移
- 在 GL 上下文中执行 DDL
- 线程同步和竞态条件

## 依赖关系

- `include/gpu/GrDirectContext.h`: GPU 上下文管理
- `src/core/SkDeferredDisplayList.cpp`: DDL 实现

## 设计模式与设计决策

**并发测试**: 通过 fuzzing 发现线程安全问题和竞态条件。

## 性能考量

多线程测试可能触发竞态,需要 ThreadSanitizer 检测。

## 相关文件

- `fuzz/FuzzDDLThreading.cpp`: 独立版本
- `tests/DeferredDisplayListTest.cpp`: 单元测试
