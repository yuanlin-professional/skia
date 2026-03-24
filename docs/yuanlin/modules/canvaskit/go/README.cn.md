# go - Go 语言测试环境工具

## 概述

`go` 目录包含用 Go 语言编写的 CanvasKit 测试基础设施工具。其核心组件是 `gold_test_env`，
一个为 CanvasKit 的 Gold 图形正确性测试提供运行环境的服务程序。该程序在 Skia 的持续集成
（CI）系统中运行，负责管理测试环境的初始化、网络端口分配、以及测试结果的收集与上报。

Gold（gold.skia.org）是 Skia 项目的图形正确性验证系统，通过像素级比较来检测渲染输出
的变化。CanvasKit 的 GM 测试将绘制结果以 PNG 图像的形式上传到 Gold 服务器，与已知的
基准图像进行对比。`gold_test_env` 程序在测试执行前启动一个本地 HTTP 服务器，接收测试
产生的图像数据（Base64 编码），并将其转发到 Gold 服务进行比较。

该目录使用 Bazel 构建系统，`BUILD.bazel` 定义了 Go 二进制的构建规则。

## 架构图

```
+---------------------------------------------------+
|           CI 测试执行环境                           |
+---------------------------------------------------+
|                                                   |
|  gold_test_env (Go 程序)                          |
|  +---------------------------------------------+ |
|  | 1. 读取环境变量 (ENV_DIR, READY_FILE)        | |
|  | 2. 获取空闲网络端口                           | |
|  | 3. 启动 HTTP 服务器                           | |
|  | 4. 写入端口文件到 ENV_DIR                     | |
|  | 5. 创建 READY_FILE 信号文件                   | |
|  | 6. 等待测试完成                               | |
|  +---------------------------------------------+ |
|           |                                       |
|           v                                       |
|  +---------------------------------------------+ |
|  | HTTP 服务器                                   | |
|  | - 接收测试图像 (Base64 PNG)                   | |
|  | - 管理测试生命周期                             | |
|  | - 转发结果到 Gold                             | |
|  +---------------------------------------------+ |
|           ^                                       |
|           |                                       |
+-----------|---------------------------------------+
            |
            v
+---------------------------------------------------+
|         CanvasKit WASM 测试 (浏览器内)              |
|  - GM 测试绘制到 canvas                            |
|  - 快照为 PNG                                     |
|  - 通过 HTTP 上传到 gold_test_env                  |
+---------------------------------------------------+
            |
            v
+---------------------------------------------------+
|              Gold 服务器 (gold.skia.org)            |
|  - 接收图像                                        |
|  - 像素级基准比较                                   |
|  - 报告变更                                        |
+---------------------------------------------------+
```

## 目录结构

```
go/
|-- gold_test_env/
|   |-- gold_test_env.go     # 测试环境管理主程序
|   |-- BUILD.bazel          # Bazel 构建配置
```

## 关键类与函数

### gold_test_env.go 主要函数

```go
func main()
// 程序入口：初始化环境、启动服务器、信号处理

func mustGetEnvironmentVariables() (string, string)
// 读取 ENV_DIR 和 READY_FILE 环境变量

func mustGetUnusedNetworkPort() (int, net.Listener)
// 获取空闲网络端口

func beginTestManagementLogic(listener net.Listener)
// 启动 HTTP 服务器，开始管理测试

func mustPrepareTestEnvironment(envDir string, port int)
// 写入端口信息到环境目录

func mustSignalTestsCanBegin(envReadyFile string)
// 创建就绪信号文件，通知测试可以开始

func setupTerminationLogic()
// 设置信号处理（SIGINT/SIGTERM）
```

## 依赖关系

- **Bazel 构建系统**: 用于编译 Go 二进制
- **Skia CI 基础设施**: Docker 容器环境
- **Gold 服务器**: gold.skia.org 图形正确性验证服务
- **环境变量**: `ENV_DIR`（通信目录）、`READY_FILE`（就绪信号文件路径）

## 设计模式分析

### 环境隔离模式
通过文件系统（端口文件、就绪信号文件）进行进程间通信，而非直接的 IPC，确保了测试环境
管理器与测试执行器之间的松耦合。

### 信号同步模式
使用文件创建作为同步原语：`gold_test_env` 启动完毕后创建 `READY_FILE`，测试运行器
轮询该文件存在后才开始执行测试，确保环境就绪。

### 优雅终止
通过 `signal.Notify` 监听系统信号（SIGINT/SIGTERM），确保在 CI 环境中能够优雅地
清理资源和上报最终状态。

## 数据流

```
CI 触发 CanvasKit 测试
       |
       v
启动 gold_test_env ---> 获取空闲端口 ---> 启动 HTTP 服务
       |
       v
写入端口到 ENV_DIR/port
       |
       v
创建 READY_FILE ---> 测试运行器检测到就绪
       |
       v
浏览器运行 GM 测试 ---> 绘制 canvas ---> 快照 PNG
       |
       v
HTTP POST 图像到 gold_test_env ---> 转发到 Gold
       |
       v
Gold 比较结果 ---> 报告通过/失败
```

## 相关文档与参考

- **Gold 图形正确性系统**: https://gold.skia.org
- **Skia CI 基础设施**: `infra/wasm-common/docker/README.md`
- **测试入口**: `tests/init_with_gold_server.js`
- **GM 测试运行工具**: `tools/run-wasm-gm-tests/`
