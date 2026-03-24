# perf_steps_test - Perf 上传步骤的单元测试

> 源文件: `infra/bots/task_drivers/common/perf_steps_test.go`

## 概述

本文件全面测试 `perf_steps` 包的功能,包括 CLI 标志计算、ZIP 和目录两种输入模式的上传流程,以及各种错误场景(缺少输出文件、缺少 results.json)。

## 架构位置

Perf 上传公共步骤的测试层。

## 主要类与结构体

无新定义。使用 `mocks.GCSClient` 和 `testutils` 辅助函数。

## 公共 API 函数

- **`TestComputeBenchmarkTestRunnerCLIFlags_Success`**: 验证 post-submit 和 CL 任务的 CLI 标志生成
- **`TestUploadToPerf_NoOutputsZIPOrDir_Error`**: 验证输入不存在时的错误处理
- **`TestUploadToPerf_OutputsZip_NoResultsJSONFile_Error`**: 验证 ZIP 中缺少 results.json
- **`TestUploadToPerf_OutputsDirectory_NoResultsJSONFile_Error`**: 验证目录中缺少 results.json
- **`TestUploadToPerf_OutputsZip_Success`**: 验证 ZIP 输入的完整上传流程
- **`TestUploadToPerf_OutputsDirectory_Success`**: 验证目录输入的完整上传流程

## 内部实现细节

- 每个测试用例同时测试 post-submit 和 CL 两种模式
- 使用 `now.TimeTravelingContext` 固定时间确保 GCS 路径可预测
- 验证 GCS SetFileContents 的调用参数(路径、内容)
- 验证任务驱动步骤名称序列

## 依赖关系

- `go.skia.org/infra/go/gcs/mocks` - GCS mock
- `go.skia.org/infra/go/now` - 时间控制

## 设计模式与设计决策

- **参数化测试**: 每个用例同时覆盖 post-submit 和 CL 两种场景
- **mock 验证**: 通过 `AssertNotCalled` 和 `AssertExpectations` 确保无意外调用

## 性能考量

纯内存操作,执行迅速。

## 相关文件

- `perf_steps.go` - 被测试的主程序
