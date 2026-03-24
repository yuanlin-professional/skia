# CanvasKit Gold 测试环境 (gold_test_env.go)

> 源文件: `modules/canvaskit/go/gold_test_env/gold_test_env.go`

## 概述

`gold_test_env.go` 是一个 Go 语言编写的测试环境服务，为 CanvasKit 的 Gold（图形正确性对比系统）测试提供后端支持。它启动一个 HTTP 服务器，监听随机端口，接收 JS 测试用例通过 POST 请求提交的 PNG 图像数据（Base64 编码），将其写入 Bazel 测试输出目录。该服务通过 Bazel 的 `test_on_env` 机制与测试二进制文件协调启动和终止。

## 架构位置

```
Bazel 测试框架
  └── test_on_env.bzl（测试环境编排）
      └── gold_test_env.go（HTTP 服务）
          ├── /healthz  ← 健康检查端点
          └── /report   ← 测试结果上报端点
              └── JS CanvasKit GM 测试
                  └── POST {name, b64_data, config}
```

## 主要类与结构体

### testPayload

HTTP POST 请求的 JSON 负载结构：

| 字段 | JSON 标签 | 说明 |
|------|----------|------|
| `TestName` | `name` | 测试名称 |
| `Base64Data` | `b64_data` | Base64 编码的 PNG 数据 |
| `Config` | `config` | 可选配置后缀（如 `html_canvas`） |

## 公共 API 函数

### main() 执行流程

1. `mustGetEnvironmentVariables()` — 读取 `ENV_DIR` 和 `ENV_READY_FILE` 环境变量
2. `mustGetUnusedNetworkPort()` — 获取 OS 分配的随机端口
3. `beginTestManagementLogic(listener)` — 启动 HTTP 服务
4. `mustPrepareTestEnvironment(envDir, port)` — 将端口号写入 `ENV_DIR/port` 文件
5. `setupTerminationLogic()` — 注册 SIGTERM 信号处理
6. `mustSignalTestsCanBegin(envReadyFile)` — 创建就绪文件
7. `select {}` — 阻塞直到 SIGTERM

### HTTP 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/healthz` | GET | 返回 200 OK，用于健康检查 |
| `/report` | POST | 接收测试结果 PNG，写入输出目录 |

### 核心函数

| 函数 | 说明 |
|------|------|
| `mustGetEnvironmentVariables()` | 读取 ENV_DIR 和 ENV_READY_FILE |
| `mustGetUnusedNetworkPort()` | 获取随机端口和监听器 |
| `beginTestManagementLogic(listener)` | 启动 HTTP 服务器 |
| `mustPrepareTestEnvironment(envDir, port)` | 写入端口文件 |
| `setupTerminationLogic()` | SIGTERM 信号处理 |
| `mustSignalTestsCanBegin(envReadyFile)` | 创建就绪信号文件 |
| `readPayload(r)` | 解析 HTTP 请求 JSON 负载 |
| `serveForever(listener)` | 永久服务（阻塞） |

## 内部实现细节

### 端口通信机制

使用非确定性端口（`:0`），因为多个测试可能并行运行。端口号写入 `ENV_DIR/port` 文件，测试二进制文件从该文件读取端口号以确定 POST 目标地址。

### 输出文件命名

输出文件路径为 `TEST_UNDECLARED_OUTPUTS_DIR/<test_name>[.<config>].png`。`config` 字段如果存在则作为后缀追加，用于区分同一测试的不同变体（如 CPU vs GPU）。

### Bazel 协调协议

1. 环境服务启动并监听端口
2. 将端口号写入共享目录
3. 创建 `ENV_READY_FILE` 信号文件
4. Bazel 检测到就绪文件后启动测试二进制文件
5. 测试完成后 Bazel 发送 SIGTERM
6. 环境服务收到 SIGTERM 后退出

### 测试结果传输

测试用例将 PNG 图像 Base64 编码后通过 POST 请求发送。服务器解码后写入 Bazel 的 undeclared output 目录，Bazel 会将这些文件打包为 `outputs.zip`。

## 依赖关系

| 依赖项 | 说明 |
|-------|------|
| `encoding/base64` | Base64 解码 |
| `encoding/json` | JSON 负载解析 |
| `net/http` | HTTP 服务器 |
| `os/signal` | SIGTERM 信号处理 |
| `path/filepath` | 文件路径构造 |
| Bazel 环境变量 | `ENV_DIR`, `ENV_READY_FILE`, `TEST_UNDECLARED_OUTPUTS_DIR` |

## 设计模式与设计决策

- **环境服务模式**: 作为 Bazel `test_on_env` 的环境进程运行，与测试二进制文件生命周期解耦
- **文件信号协议**: 使用文件系统（端口文件、就绪文件）作为进程间通信机制，简单可靠
- **随机端口**: 避免端口冲突，支持并行测试
- **panic 风格错误处理**: 使用 `must*` 前缀函数表示不可恢复的错误，符合测试基础设施的约定
- **无状态服务**: 每个 POST 请求独立处理，不维护测试状态

## 性能考量

- Base64 编码/解码增加了约 33% 的数据传输开销，但对测试场景影响不大
- HTTP 本地传输延迟极低
- 文件写入使用同步操作，确保测试收到响应时数据已持久化
- 服务器在单独的 goroutine 中运行，不阻塞信号处理

## 相关文件

- `modules/canvaskit/gm_bindings.cpp` — 产生测试 PNG 数据的 C++ 绑定
- Bazel `test_on_env.bzl` — 测试环境编排规则
- `tools/HashAndEncode.h` — PNG 编码工具（C++ 端）
