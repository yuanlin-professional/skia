# FuzzTriangulation (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzTriangulation.cpp

## 概述

`FuzzTriangulation.cpp` 是 `fuzz/FuzzTriangulation.cpp` 的 OSS-Fuzz 适配器版本,专门用于持续模糊测试 GPU 路径三角剖分功能。该文件作为 LibFuzzer 和 Skia 内部三角剖分 fuzzer 之间的桥接层。

## 架构位置

```
OSS-Fuzz → LLVMFuzzerTestOneInput → fuzz_Triangulation → GrTriangulator
```

## 主要类与结构体

**LLVMFuzzerTestOneInput**: 最大输入 4000 字节,足以生成包含数百个路径操作的复杂路径。

**fuzz_Triangulation** (外部定义): 执行与 `fuzz/FuzzTriangulation.cpp` 相同的测试逻辑。

## 内部实现细节

### 输入大小选择

4000 字节平衡了:
- **覆盖率**: 足够复杂以触发边界情况
- **性能**: 避免超时(三角剖分可能很慢)
- **内存**: 限制顶点数量防止OOM

### 与独立版本的区别

- 独立版本(`fuzz/FuzzTriangulation.cpp`): 用于本地 fuzzing
- OSS-Fuzz 版本(本文件): 集成到 Google 分布式 fuzzing 基础设施

## 依赖关系

- `fuzz/Fuzz.h`: Skia fuzzing 框架
- `fuzz_Triangulation`: 实际测试逻辑(链接时提供)
- `src/gpu/ganesh/geometry/GrTriangulator.cpp`: 被测试的实现

## 设计模式与设计决策

### 适配器模式

作为 OSS-Fuzz 和 Skia 之间的薄适配层,最小化开销。

### 持续集成

在 Google 基础设施上:
- **24/7 运行**: 持续发现新问题
- **语料库**: 积累有趣的测试用例
- **回归检测**: 验证修复的有效性

## 性能考量

- **超时保护**: OSS-Fuzz 提供执行时间限制(通常 25 秒)
- **内存限制**: 防止过度内存使用
- **覆盖率引导**: LibFuzzer 自动关注高覆盖率输入

## 相关文件

- `fuzz/FuzzTriangulation.cpp`: 独立 fuzzer 版本
- `fuzz/FuzzCommon.h`: 共享的 fuzzing 工具
- `src/gpu/ganesh/geometry/GrTriangulator.cpp`: 实现
- OSS-Fuzz 项目配置: `projects/skia/` in ClusterFuzz

**自动化工作流**:
1. LibFuzzer 生成/变异输入
2. 执行 LLVMFuzzerTestOneInput
3. 监控崩溃、超时、内存错误
4. 最小化触发问题的输入
5. 报告到 Skia 团队

该 fuzzer 是 Skia GPU 渲染质量保证的关键组成部分,自 2021 年持续运行。
