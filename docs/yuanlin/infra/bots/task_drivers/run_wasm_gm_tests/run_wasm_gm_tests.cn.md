# run_wasm_gm_tests - WASM GM 测试运行任务驱动

> 源文件: `infra/bots/task_drivers/run_wasm_gm_tests/run_wasm_gm_tests.go`

## 概述

`run_wasm_gm_tests` 运行 Skia 的 WASM GM (Graphical Model) 测试并将结果上传到 Gold 图像比较服务。它通过 Puppeteer 在浏览器中执行编译为 WASM 的 GM 测试,使用已知哈希避免重复上传,最后通过 goldctl 将新图像和测试结果提交给 Gold。

## 架构位置

属于 CanvasKit/WASM 测试执行子系统,连接 WASM 测试运行时和 Gold 图像比较服务。

## 主要类与结构体

- **`goldResult`**: Gold 测试结果(TestName, MD5Hash)

## 公共 API 函数

- **`main()`**: 完整的测试流程编排
- **`setupGoldctl()`**: goldctl 认证和初始化(支持 luci 和 service-account 模式)
- **`downloadKnownHashes()`**: 从 Gold 下载已知哈希列表
- **`setupTests()`**: npm ci 安装测试依赖
- **`runTests()`**: 通过 Node.js 运行 WASM GM 测试(180 秒超时/批次)
- **`processTestData()`**: 读取 gold_results.json,调用 goldctl imgtest add
- **`finalizeGoldctl()`**: goldctl imgtest finalize

## 内部实现细节

- WebGL 版本(0=CPU, 1=WebGL1, 2=WebGL2)映射到不同的 Gold key
- 已知哈希列表避免重复上传(只上传新的或变化的 PNG)
- 测试输出格式: `gold_results.json` + `<md5>.png` 文件
- 支持 tryjob 模式(changelist/patchset/tryjob ID)

## 依赖关系

- Node.js + Puppeteer + npm
- goldctl - Gold 命令行工具
- WASM GM 测试二进制(wasm_gm_tests.js + .wasm)

## 设计模式与设计决策

- **增量上传**: 已知哈希避免重复传输未变化的图像
- **摘要优先**: 当 PNG 文件不存在时只报告摘要(已存在于 Gold 中)
- **批次超时**: 每 50 个测试一批,180 秒超时

## 性能考量

- 已知哈希列表大幅减少上传量
- 180 秒/批次的超时平衡了可靠性和效率
- 测试输出使用 MD5 摘要作为文件名支持去重

## 相关文件

- `tools/run-wasm-gm-tests/` - Puppeteer 测试运行器
