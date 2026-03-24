# karma.bazel.js

> 源文件: modules/canvaskit/karma.bazel.js

## 概述

`karma.bazel.js` 是 CanvasKit 模块用于 Bazel 构建系统的 Karma 测试配置文件。该文件配置了在 Bazel 环境中运行浏览器测试时的特定设置,包括与 Gold 测试服务的集成、资源代理配置和测试报告机制。

与传统的 `karma.conf.js` 不同,该配置专门为 Bazel 构建和 Gold 视觉回归测试系统设计,支持将渲染结果上传到 Gold 服务进行图像对比和分析。

## 架构位置

```
skia/
├── modules/
│   └── canvaskit/
│       ├── karma.bazel.js     # 本文件 - Bazel 测试配置
│       ├── karma.conf.js      # 传统构建测试配置
│       ├── tests/
│       │   └── *_test.js      # 测试文件
│       ├── BUILD.bazel        # Bazel 构建规则
│       └── go/
│           └── gold_test_env/
│               └── gold_test_env.go # Gold 测试环境服务
```

该文件是 Bazel 构建和测试基础设施的一部分,与 Go 编写的 Gold 测试服务集成。

## 主要类与结构体

### module.exports 配置函数

```javascript
module.exports = function(config) {
  let cfg = { /* 配置对象 */ };
  BAZEL_APPLY_SETTINGS(cfg);
  config.set(cfg);
}
```

**特殊点**: 包含 `BAZEL_APPLY_SETTINGS(cfg)` 调用,这是 Bazel 注入的配置函数。

## 公共 API 函数

本文件导出 Karma 配置函数,由 Karma 在启动时调用。

## 内部实现细节

### 端口文件读取

```javascript
const testOnEnvPortPath = path.join(process.env['ENV_DIR'], 'port');
const port = fs.readFileSync(testOnEnvPortPath, 'utf8').toString();
console.log('test_on_env PORT:', port);
```

**工作原理**:
1. `gold_test_env.go` 启动 Gold 服务并将端口号写入文件
2. Karma 配置从环境变量 `ENV_DIR` 指定的目录读取端口文件
3. 解析端口号用于代理配置

**为什么不直接传递端口**:
Karma 需要静态文件,直接传递端口号在某些情况下不可靠,使用文件更稳定。

### 代理配置

```javascript
proxies: {
  '/gold_rpc/': `http://localhost:${port}/`,
  '/assets/': '/static/skia/modules/canvaskit/tests/assets/',
}
```

**gold_rpc 代理**:
- 测试代码调用 `/gold_rpc/*` API
- 请求被转发到本地 Gold 服务(`http://localhost:${port}/`)
- Gold 服务处理图像上传和对比

**assets 代理**:
- 测试资源(图片、字体等)通过 `/assets/` 访问
- 实际路径为 Bazel 静态文件服务的路径

### Karma 基础配置

```javascript
frameworks: ['jasmine']
```
使用 Jasmine 测试框架。

```javascript
reporters: ['progress']
colors: true
logLevel: config.LOG_INFO
```
基本的测试输出配置。

```javascript
browserDisconnectTimeout: 20000
browserNoActivityTimeout: 20000
```
设置较长的超时时间,适应 WebAssembly 加载和 Gold 上传。

```javascript
concurrency: Infinity
```
允许并发运行多个浏览器实例。

### Bazel 集成

```javascript
// Bazel will inject some code here to add/change the following items:
//  - files
//  - proxies
//  - browsers
//  - basePath
//  - singleRun
//  - plugins
BAZEL_APPLY_SETTINGS(cfg);
```

**Bazel 注入的配置**:
- **files**: 测试文件列表(由 BUILD.bazel 定义)
- **proxies**: 额外的代理规则
- **browsers**: 要使用的浏览器(Chrome, Firefox 等)
- **basePath**: 文件服务的基础路径
- **singleRun**: CI 模式下为 true,开发模式下为 false
- **plugins**: Karma 插件列表

**BAZEL_APPLY_SETTINGS 函数**:
这是 Bazel 的 karma_web_test 规则在运行时注入的函数,用于动态配置 Karma。

## 依赖关系

### Node.js 模块

**path**: 文件路径操作。

**fs**: 文件系统访问,读取端口文件。

### 环境变量

**ENV_DIR**: 指向包含 Gold 服务配置文件的目录。

### Gold 测试服务

**gold_test_env.go**: Go 程序,启动 Gold RPC 服务:
- 监听随机端口
- 将端口号写入文件
- 处理图像上传和对比请求

### Bazel 构建系统

**karma_web_test 规则**: Bazel 提供的 Karma 测试规则,负责:
- 启动 Gold 服务
- 注入 BAZEL_APPLY_SETTINGS 函数
- 管理测试生命周期

## 设计模式与设计决策

### 依赖注入模式

通过 `BAZEL_APPLY_SETTINGS` 函数注入配置,而非硬编码:

**优点**:
- 配置灵活,可根据构建目标调整
- 测试隔离,每个测试有独立的配置
- 支持分布式测试

### 进程间通信

使用文件系统作为进程间通信机制:
- Gold 服务写入端口文件
- Karma 配置读取端口文件
- 简单可靠,无需复杂的 IPC

### 关注点分离

- **karma.bazel.js**: Karma 特定配置
- **gold_test_env.go**: Gold 服务管理
- **BUILD.bazel**: Bazel 构建规则
- **测试文件**: 实际测试逻辑

每个文件职责单一,易于维护。

### 环境适配

通过不同的配置文件适配不同的构建系统:
- `karma.conf.js`: 传统构建(Make, 手动运行)
- `karma.bazel.js`: Bazel 构建(CI, Bazel test)

## 性能考量

### 端口读取开销

端口文件读取是同步操作,但只在配置加载时执行一次,对测试性能影响可忽略。

### 代理开销

本地代理(`localhost`)几乎无延迟,不影响测试速度。

### Gold 上传

图像上传到 Gold 服务可能是瓶颈:
- 大图像需要编码和传输
- 网络 I/O 时间
- Gold 服务处理时间

**优化**: Bazel 的缓存机制可以跳过已知良好的测试。

### 超时设置

20 秒超时足够处理:
- WebAssembly 加载(通常 < 1 秒)
- 测试执行(通常 < 5 秒)
- Gold 上传(通常 < 10 秒)

### 最佳实践

1. **使用 Bazel 缓存**: 避免重复上传相同的图像
2. **并行测试**: 利用 `concurrency: Infinity` 并行运行测试
3. **增量测试**: 只运行受影响的测试
4. **本地 Gold 服务**: 减少网络延迟

## 相关文件

### Karma 配置
- `modules/canvaskit/karma.conf.js` - 传统构建的配置

### Gold 测试服务
- `modules/canvaskit/go/gold_test_env/gold_test_env.go` - Go 服务实现
- Gold RPC API 定义

### Bazel 构建
- `modules/canvaskit/BUILD.bazel` - Bazel 构建规则
- `karma_web_test` 规则定义

### 测试文件
- `modules/canvaskit/tests/*_test.js` - 测试实现
- `modules/canvaskit/tests/util.js` - 测试工具

### Gold 系统
- Skia Gold 图像对比服务
- Gold Web UI(用于查看对比结果)

### 文档
- Bazel karma_web_test 文档
- Skia Gold 使用指南
