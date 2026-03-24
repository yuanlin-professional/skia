# codesize - 代码体积分析任务驱动

> 源文件: `infra/bots/task_drivers/codesize/codesize.go`

## 概述

`codesize` 是一个综合性的代码体积分析任务驱动,使用 Bloaty 工具分析编译产物的体积分布。在 tryjob 模式下,它还会对比补丁前后的体积差异。分析结果上传到 codesize.skia.org 的 GCS 桶和 perf.skia.org 的 Perf 数据桶,支持长期体积趋势追踪和 CL 级别的体积变化检测。

## 架构位置

属于 Skia CI 的构建分析子系统,连接编译任务输出、Bloaty 分析工具和 codesize/perf 展示服务。

## 主要类与结构体

- **`BloatyOutputMetadata`**: 元数据结构,包含版本、时间戳、Swarming 信息、任务信息、Bloaty 参数、补丁信息和提交信息
- **`runStepsArgs`**: runSteps 的输入参数集合

## 公共 API 函数

- **`main()`**: 解析标志、初始化客户端、调用 runSteps
- **`runSteps()`**: 核心流程(获取提交信息、运行 Bloaty、上传结果)
- **`runBloaty()`**: 剥离调试符号后运行 Bloaty 分析(TSV 输出)
- **`runBloatyDiff()`**: 对比补丁前后二进制体积差异
- **`uploadPerfData()`**: 上传 stripped 二进制体积和差异到 Perf
- **`parseBloatyDiffOutput()`**: 解析 Bloaty diff 输出提取 VM 和 File 差异值

## 内部实现细节

- 通过 `strip` 工具剥离调试符号,使体积数据反映实际部署体积
- Bloaty 分析使用 `compileunits,symbols` 两级分解和 TSV 格式
- GCS 路径按 `YYYY/MM/DD/HH/revision/task` 格式组织
- tryjob 路径增加 `tryjob/<issue>/<patchset>/<taskID>` 前缀
- TSV 文件最后上传以避免 Pub/Sub 触发时 JSON 未就绪的竞态

## 依赖关系

- Bloaty (CIPD 包) - 二进制体积分析
- strip (binutils) - 调试符号剥离
- `go.skia.org/infra/go/gerrit`, `go.skia.org/infra/go/gitiles` - 获取提交信息
- `go.skia.org/infra/perf/go/ingest/format` - Perf 数据格式

## 设计模式与设计决策

- **tryjob/post-submit 双模式**: 根据 repoState 自动选择 Gerrit 或 Gitiles 获取提交信息
- **有序上传**: TSV 最后上传确保元数据和 diff 文件先就位
- **Perf 集成**: 非 tryjob 运行自动上传体积数据到 Perf 追踪长期趋势

## 性能考量

Bloaty 分析和 strip 操作对大型二进制文件可能耗时较长。GCS 上传是顺序执行的。

## 相关文件

- `codesize_test.go` - 单元测试
- `infra/bots/task_drivers/common/perf_steps.go` - Perf 上传工具
