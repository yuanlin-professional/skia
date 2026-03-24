# Skia WASM GM 测试运行工具

## 概述

`tools/run-wasm-gm-tests` 提供了在浏览器中运行 Skia GM（Golden Master）测试和单元测试的 WebAssembly 环境。该工具使用 Puppeteer 控制 Chrome 浏览器，加载编译为 WASM 的 GM 测试程序，执行测试并收集渲染结果。生成的图像可以上传到 Gold（Skia 的图像比较系统）进行视觉回归检测。

## 目录结构

```
tools/run-wasm-gm-tests/
├── Makefile                    # 构建和运行命令
├── package.json                # Node.js 依赖配置
├── package-lock.json           # 依赖锁定文件
├── run-wasm-gm-tests.html      # 浏览器端测试运行页面
└── run-wasm-gm-tests.js        # Puppeteer 驱动脚本（主入口）
```

## 核心组件

### run-wasm-gm-tests.js

Node.js 命令行应用，通过 Puppeteer 自动化浏览器执行 WASM GM 测试：

**命令行参数：**

| 参数 | 说明 |
|------|------|
| `--js_file` | (必需) wasm_gm_tests.js 文件路径 |
| `--wasm_file` | (必需) wasm_gm_tests.wasm 文件路径 |
| `--known_hashes` | (必需) 已知哈希文件（不需要写入磁盘的结果） |
| `--output` | (必需) 输出 JSON 和图像的目录 |
| `--resources` | (必需) 测试图像资源目录 |
| `--use_gpu` | 使用 GPU 模式（非无头模式） |
| `--enable_simd` | 启用 WASM SIMD 指令 |
| `--port` | 本地服务器端口（默认 8081） |
| `--timeout` | 测试超时时间 |

### run-wasm-gm-tests.html

浏览器端测试页面，负责：

- 加载和初始化 WASM GM 测试模块
- 执行各个 GM 测试用例
- 捕获渲染结果为 PNG 图像
- 计算图像哈希值
- 对比已知哈希值，仅输出新结果
- 通过 HTTP POST 将结果发回 Node.js 服务器

### 工作流程

```
1. Puppeteer 启动 Express HTTP 服务器
2. 提供 WASM 文件、JS 文件和测试资源
3. Chrome 浏览器加载 run-wasm-gm-tests.html
4. WASM 模块初始化并开始执行测试
5. 每个 GM 测试：
   a. 创建 SkSurface 进行渲染
   b. 执行 GM 的 draw() 函数
   c. 捕获渲染结果为 PNG
   d. 计算 PNG 的哈希值
   e. 如果不在已知哈希列表中，发送到服务器
6. 单元测试直接执行并报告通过/失败
7. 服务器收集所有结果，写入输出目录
```

## 使用方法

### 构建 WASM GM 测试

```bash
# 需要先构建 wasm_gm_tests 目标
ninja -C out/wasm_gm_tests wasm_gm_tests
```

### 安装依赖

```bash
cd tools/run-wasm-gm-tests
npm ci
```

### 运行测试

```bash
node run-wasm-gm-tests.js \
  --js_file ../../out/wasm_gm_tests/wasm_gm_tests.js \
  --wasm_file ../../out/wasm_gm_tests/wasm_gm_tests.wasm \
  --known_hashes /tmp/gold/hashes.txt \
  --output /tmp/gold/tests/ \
  --resources ../../resources \
  --timeout 180
```

### 使用 GPU 模式

```bash
node run-wasm-gm-tests.js \
  --use_gpu \
  --js_file path/to/wasm_gm_tests.js \
  --wasm_file path/to/wasm_gm_tests.wasm \
  --known_hashes hashes.txt \
  --output /tmp/output/ \
  --resources ../../resources
```

### 启用 SIMD

```bash
node run-wasm-gm-tests.js \
  --enable_simd \
  --js_file path/to/wasm_gm_tests.js \
  ...
```

## 输出格式

### 目录结构

```
output/
├── results.json     # 测试结果 JSON（Gold 兼容格式）
└── *.png            # 渲染结果图像
```

### results.json

包含每个 GM 测试的元数据和哈希值，用于上传到 Gold 系统进行视觉比较和审批。

## 已知哈希机制

`--known_hashes` 文件包含之前已确认正确的图像哈希值。对于这些哈希值对应的 GM 测试，不需要重新生成和上传图像，从而节省存储和带宽。

## 依赖项

- **Node.js**: 运行环境
- **puppeteer**: 浏览器自动化
- **express**: HTTP 服务器
- **body-parser**: HTTP 请求体解析
- **command-line-args**: 命令行参数

## 与其他模块的关系

- **gm/**: GM 测试的 C++ 源码
- **tests/**: 单元测试源码
- **modules/canvaskit/**: CanvasKit WASM 基础设施
- **infra/bots/**: CI 集成脚本
- **Gold (skia.org/infra/gold)**: 图像比较和审批系统
