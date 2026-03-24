# FuzzSkMeshSpecification (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzSkMeshSpecification.cpp

## 概述

测试 SkMesh 自定义网格规范功能,特别是顶点着色器和片段着色器的 SkSL 编译。通过生成随机 SkSL 代码发现编译器的崩溃和错误处理问题。

## 架构位置

测试 `include/core/SkMesh.h` 中的自定义网格规范和 SkSL 编译器。

## 主要类与结构体

### FuzzSkMeshSpecification 函数

从模糊数据生成:
1. 属性列表(最多 kMaxAttributes 个)
2. Varying 列表(最多 kMaxVaryings 个)
3. 顶点步幅
4. 顶点着色器和片段着色器 SkSL 代码

### SkSL 生成策略

通过映射字节到 SkSL 语言元素:
- **0-127**: ASCII 字符
- **128+**: 特殊注入:
  - 属性名引用
  - Varying 名引用
  - SkSL 关键字(if, for, while 等)
  - SkSL 运算符(&&, ||, ==, != 等)
  - SkSL 类型(float2, float3, float4 等)

## 内部实现细节

### 智能 SkSL 生成

不是完全随机字节,而是:
- 注入有效的标识符
- 插入关键字和运算符
- 提高生成有效 SkSL 程序的概率

### 测试目标

- SkSL 编译器的鲁棒性
- 语法错误处理
- 类型检查
- 着色器链接

## 依赖关系

- `include/core/SkMesh.h`: Mesh 规范接口
- SkSL 编译器: 着色器编译

## 设计模式与设计决策

**语法引导 Fuzzing**: 通过注入有效的语法元素,提高测试覆盖率。

## 性能考量

SkSL 编译可能很慢,需要超时保护。

## 相关文件

- `src/sksl/SkSLCompiler.cpp`: SkSL 编译器
- `src/core/SkMesh.cpp`: Mesh 实现

该 fuzzer(2022 年添加)针对 Skia 的自定义网格功能,是发现 SkSL 编译器问题的重要工具。
