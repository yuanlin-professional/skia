# FuzzAPICreateDDL (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzAPICreateDDL.cpp

## 概述

测试通过 API 创建延迟显示列表(DDL)的流程。使用可移植字体管理器确保跨平台一致性。

## 架构位置

测试 DDL 的创建 API 和序列化/反序列化。

## 主要类与结构体

**LLVMFuzzerTestOneInput**:
- 最大 4000 字节
- 使用 `ToolUtils::UsePortableFontMgr()` 设置可移植字体

**fuzz_CreateDDL**: 创建 DDL 并测试其属性

## 内部实现细节

测试流程:
1. 创建 SkDeferredDisplayListRecorder
2. 获取 canvas 并绘制随机内容
3. 生成 DDL
4. 验证 DDL 的有效性

## 依赖关系

- `include/core/SkDeferredDisplayListRecorder.h`: DDL 记录器
- `tools/fonts/FontToolUtils.h`: 可移植字体工具

## 设计模式与设计决策

**可移植性**: 使用统一字体避免平台差异导致的不一致行为。

## 性能考量

DDL 创建涉及命令记录和资源管理。

## 相关文件

- `fuzz/FuzzCreateDDL.cpp`: 独立版本
- `tests/DeferredDisplayListTest.cpp`: 单元测试
