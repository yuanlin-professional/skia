# FuzzPathMeasure (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzPathMeasure.cpp

## 概述

`FuzzPathMeasure.cpp` 测试 `SkPathMeasure` 类,用于测量路径长度、获取路径上的点和切线等几何操作。这些功能在动画路径跟随、文本沿路径排布等场景中至关重要。

## 架构位置

测试 `include/core/SkPathMeasure.h` 中的路径测量 API。

## 主要类与结构体

**LLVMFuzzerTestOneInput**: 最大输入 4000 字节,足以生成复杂路径。

**fuzz_PathMeasure** (外部定义):
- 生成随机 SkPath
- 创建 SkPathMeasure 对象
- 调用 getLength(), getPosTan(), getSegment() 等

## 内部实现细节

测试覆盖:
- **路径类型**: 直线、曲线、闭合路径
- **长度计算**: 精度和性能
- **位置查询**: 路径上任意 t 值的点
- **切线计算**: 方向向量的正确性
- **路径分段**: getSegment() 的正确性

## 依赖关系

- `include/core/SkPath.h`: 路径定义
- `src/core/SkPathMeasure.cpp`: 路径测量实现

## 设计模式与设计决策

通过随机路径和测量参数,发现数值精度问题和边界情况。

## 性能考量

- **曲线细分**: 精确测量需要迭代细分
- **缓存**: SkPathMeasure 内部缓存中间结果
- **大路径**: 4000 字节可生成数百个路径操作

## 相关文件

- `include/core/SkPathMeasure.h`: 公共 API
- `tests/PathMeasureTest.cpp`: 单元测试

该 fuzzer 帮助发现和修复了多个路径测量相关的精度和崩溃问题。
