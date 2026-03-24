# karma.conf.js

> 源文件: modules/canvaskit/karma.conf.js

## 概述

`karma.conf.js` 是 CanvasKit 模块的 Karma 测试运行器配置文件,用于在浏览器环境中执行 JavaScript 单元测试。Karma 是一个测试运行器,能够在真实浏览器或无头浏览器中运行测试,确保 WebAssembly 代码在实际运行环境中的正确性。

该配置文件定义了测试文件的加载顺序、代理规则、浏览器配置以及针对 Docker 环境和本地开发环境的不同设置。它支持代码覆盖率测试,并能在持续集成(CI)和本地开发两种模式下工作。

## 架构位置

```
skia/
├── modules/
│   └── canvaskit/
│       ├── karma.conf.js      # 本文件 - 传统构建测试配置
│       ├── karma.bazel.js     # Bazel 构建测试配置
│       ├── tests/
│       │   ├── *_test.js      # 测试文件
│       │   ├── util.js        # 测试工具函数
│       │   ├── legacy_init.js # 测试初始化
│       │   └── assets/        # 测试资源
│       ├── build/
│       │   ├── canvaskit.js   # 编译后的 JS
│       │   └── canvaskit.wasm # WebAssembly 模块
│       └── compile.sh         # 编译脚本
```

该文件是 CanvasKit 传统(非 Bazel)构建系统的测试配置,与 `karma.bazel.js` 形成对比,后者用于 Bazel 构建系统。

## 主要类与结构体

### module.exports 配置函数

```javascript
module.exports = function(config) {
  let cfg = { /* 配置对象 */ };
  config.set(cfg);
}
```

**参数**:
- `config`: Karma 配置对象,提供配置方法和常量

**配置对象结构**: 包含测试框架、文件列表、代理、报告器、浏览器等设置

### 配置对象属性

#### frameworks
```javascript
frameworks: ['jasmine']
```
指定使用 Jasmine 测试框架,这是一个行为驱动开发(BDD)测试框架。

#### files
```javascript
files: [
  { pattern: 'build/canvaskit.wasm', included:false, served:true},
  { pattern: 'tests/assets/*', included:false, served:true},
  'build/canvaskit.js',
  'tests/legacy_init.js',
  'tests/util.js',
  'tests/legacy_test_reporter.js',
  'tests/*_test.js'
]
```

**加载顺序**:
1. **canvaskit.wasm**: WebAssembly 模块,不直接包含,仅提供服务
2. **tests/assets/***: 测试资源(图片、字体等),不包含,仅提供服务
3. **canvaskit.js**: CanvasKit 主模块,首先加载
4. **legacy_init.js**: 测试环境初始化
5. **util.js**: 测试辅助函数
6. **legacy_test_reporter.js**: 测试报告器
7. ***_test.js**: 所有测试文件

## 公共 API 函数

### 主配置导出函数

该文件导出一个配置函数,由 Karma 在启动时调用。

## 内部实现细节

### 代理配置

```javascript
proxies: {
  '/assets/': '/base/tests/assets/',
  '/build/': '/base/build/',
}
```

**作用**: 将测试中的 URL 请求映射到实际文件位置。

**示例**: 测试代码中的 `fetch('/assets/test.png')` 实际访问 `/base/tests/assets/test.png`

### 报告器配置

```javascript
reporters: ['progress']
```

使用 `progress` 报告器显示测试进度。在本地环境中会额外添加 `coverage` 报告器。

### 浏览器配置

**基础设置**:
```javascript
browsers: ['Chrome']
```
默认使用 Chrome 浏览器运行测试。

**Docker/无头模式**:
```javascript
if (isDocker || config.headless) {
  cfg.browsers = ['ChromeHeadlessNoSandbox'];
  cfg.customLaunchers = {
    ChromeHeadlessNoSandbox: {
      base: 'ChromeHeadless',
      flags: [
        '--no-sandbox',
        '--browser-test',
        '--disable-dev-shm-usage',
      ],
    },
  };
}
```

**Chrome 标志解释**:
- `--no-sandbox`: 禁用沙箱,在 Docker 容器中必需
- `--browser-test`: 减少测试的不稳定性
- `--disable-dev-shm-usage`: 避免共享内存问题导致崩溃

### 环境检测

```javascript
const isDocker = require('is-docker')();
```

自动检测是否在 Docker 容器中运行,并相应调整配置。

### 代码覆盖率配置

```javascript
if (!isDocker && !config.headless) {
  cfg.reporters.push('coverage');
  cfg.preprocessors = {
    'canvaskit/bin/canvaskit.js': ['coverage'],
  };
}
```

**仅在本地环境启用**: CI 环境中不收集覆盖率,以提高测试速度。

**覆盖率目标**: `canvaskit/bin/canvaskit.js` - CanvasKit 主文件(包含 Emscripten 生成的代码)

### 超时设置

```javascript
browserDisconnectTimeout: 20000,
browserNoActivityTimeout: 20000,
```

**原因**: WebAssembly 初始化和大型测试可能需要较长时间,设置为 20 秒以避免误报超时。

### 观察模式设置

```javascript
autoWatch: true,
singleRun: false,
```

**开发模式默认值**:
- `autoWatch: true`: 文件变化时自动重新运行测试
- `singleRun: false`: 持续运行,不自动退出

## 依赖关系

### Node.js 模块

**is-docker**:
```javascript
const isDocker = require('is-docker')();
```
检测是否在 Docker 容器中运行。

### Karma 插件

- **karma-jasmine**: Jasmine 测试框架适配器
- **karma-chrome-launcher**: Chrome 浏览器启动器
- **karma-coverage**: 代码覆盖率报告器(本地开发时)

### 测试文件依赖关系

```
canvaskit.js (CanvasKit 核心)
    ↓
legacy_init.js (初始化 CanvasKit)
    ↓
util.js (测试工具)
    ↓
legacy_test_reporter.js (报告配置)
    ↓
*_test.js (实际测试)
```

### 外部资源

- `build/canvaskit.wasm`: 编译的 WebAssembly 模块
- `tests/assets/*`: 测试用图片、字体等资源

## 设计模式与设计决策

### 环境适配模式

通过检测运行环境(Docker vs 本地)自动调整配置,确保测试在不同环境中都能正常运行。

**优点**:
- 单一配置文件支持多种环境
- 减少维护负担
- 降低配置错误风险

### 渐进式增强

基础配置足够简单,只在特定环境下添加额外功能(如覆盖率测试):
```javascript
if (!isDocker) {
  cfg.reporters.push('coverage');
}
```

### 关注点分离

- **karma.conf.js**: 传统构建系统的配置
- **karma.bazel.js**: Bazel 构建系统的配置
- 测试文件与配置文件分离

### 约定优于配置

使用文件命名约定(`*_test.js`)自动发现测试文件,无需手动列举。

### 防御性设计

**慷慨的超时设置**: 20 秒超时避免网络延迟或 CI 环境性能波动导致测试失败。

**沙箱禁用**: 在 Docker 中显式禁用沙箱,避免权限问题。

## 性能考量

### 文件服务优化

**仅服务不包含模式**:
```javascript
{ pattern: 'build/canvaskit.wasm', included:false, served:true}
```

WASM 文件和资源文件不直接包含在 HTML 中,而是按需加载,减少初始加载时间。

### 并发控制

```javascript
concurrency: Infinity
```

允许同时启动无限数量的浏览器实例,适合分布式测试环境。

### 覆盖率开销

覆盖率测试仅在本地开发时启用:
- **原因**: 覆盖率插桩会显著增加代码体积和执行时间
- **CI 环境**: 优先考虑测试速度,不收集覆盖率
- **本地开发**: 允许开发者分析代码覆盖情况

### WebAssembly 加载优化

**异步加载**: canvaskit.wasm 通过 canvaskit.js 异步加载,不阻塞其他资源。

### 最佳实践

1. **使用无头模式**: CI 环境中使用 ChromeHeadless 节省资源
2. **合理设置超时**: 根据测试复杂度调整超时时间
3. **按需启用覆盖率**: 避免在所有环境中都收集覆盖率
4. **保持测试独立**: 每个测试文件应该独立可运行

## 相关文件

### Karma 配置
- `modules/canvaskit/karma.bazel.js` - Bazel 构建的 Karma 配置
- `karma.conf.js` 的 Bazel 变体,集成 Gold 测试服务

### 测试文件
- `modules/canvaskit/tests/legacy_init.js` - CanvasKit 初始化
- `modules/canvaskit/tests/util.js` - 测试工具函数
- `modules/canvaskit/tests/legacy_test_reporter.js` - 测试报告器
- `modules/canvaskit/tests/*_test.js` - 实际测试用例

### 构建产物
- `modules/canvaskit/build/canvaskit.js` - 编译后的 JavaScript
- `modules/canvaskit/build/canvaskit.wasm` - WebAssembly 模块

### 构建脚本
- `modules/canvaskit/compile.sh` - Emscripten 编译脚本
- `modules/canvaskit/Makefile` - Make 构建规则

### 文档
- Karma 官方文档: https://karma-runner.github.io/
- Jasmine 文档: https://jasmine.github.io/
