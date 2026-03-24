# task_drivers - 任务驱动程序

## 概述

`task_drivers/` 目录包含用 Go 语言编写的任务驱动程序。任务驱动是比 Recipe 更灵活的任务执行方式，适用于需要复杂逻辑、直接访问 Go 生态系统库或需要更好错误处理的 CI 任务。

每个任务驱动程序作为独立的 Go 二进制文件编译和分发，在 Swarming 任务中直接执行。

## 目录结构

```
task_drivers/
├── common/                         # 共享库（非独立驱动）
├── testutils/                      # 测试工具库
├── bazel_build/                    # Bazel 构建任务
├── canvaskit_gold/                 # CanvasKit Gold 测试
├── check_generated_files/          # 检查自动生成的文件
├── codesize/                       # 代码体积分析
├── compile_wasm_gm_tests/          # 编译 WASM GM 测试
├── cpu_tests/                      # CPU 测试执行
├── external_client/                # 外部客户端构建测试
├── g3_canary/                      # Google3 金丝雀测试
├── go_linters/                     # Go 代码检查
├── perf_puppeteer_canvas/          # Puppeteer Canvas 性能测试
├── perf_puppeteer_render_skps/     # Puppeteer SKP 渲染性能测试
├── perf_puppeteer_skottie_frames/  # Puppeteer Skottie 帧性能测试
├── recreate_skps/                  # 重新生成 SKP 文件
├── run_gn_to_bp/                   # 运行 GN 到 Blueprint 转换
├── run_wasm_gm_tests/              # 运行 WASM GM 测试
└── toolchain_layering_check/       # 工具链分层检查
```

## 编译

使用以下脚本编译所有任务驱动程序：

```bash
bash infra/bots/build_task_drivers.sh
```

每个任务驱动目录包含 `BUILD.bazel` 文件，也可通过 Bazel 构建。

## 依赖关系

- `common/` - 共享的 Bazel 工具函数和性能步骤
- `testutils/` - 测试辅助工具
- `go.skia.org/infra` - Skia 基础设施 Go 库

## 相关文档与参考

- [Task Driver 框架文档](https://skia.googlesource.com/buildbot/+/main/task_driver/)
- 父目录 `infra/bots/README.md`
