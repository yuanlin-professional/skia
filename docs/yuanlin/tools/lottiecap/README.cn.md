# Skia Lottie 截图工具

## 概述

`tools/lottiecap` 是一个 Node.js 命令行应用程序，用于在浏览器中渲染 Lottie 动画文件并截取 5x5 胶片条（Filmstrip）。该工具使用 Puppeteer 控制 Chrome 浏览器，通过 lottie-web 库渲染 Lottie JSON 动画，并将 25 个均匀采样的帧组合为一张 1000x1000 像素的 PNG 图像。主要用于 Skia CI 中的 Lottie 渲染正确性验证。

## 目录结构

```
tools/lottiecap/
├── .gitignore         # 忽略 node_modules
├── README.md          # 英文使用说明
├── package.json       # Node.js 依赖配置
├── package-lock.json  # 依赖锁定文件
├── lottiecap.js       # Puppeteer 驱动脚本（主入口）
└── driver.html        # 浏览器端渲染页面
```

## 核心组件

### lottiecap.js

Node.js 主脚本，使用 Puppeteer 自动化浏览器操作：

**工作流程：**

1. 启动本地 Express HTTP 服务器
2. 提供 Lottie JSON 文件和 lottie-web 播放器
3. 使用 Puppeteer 启动 Chrome 浏览器
4. 加载 `driver.html` 渲染页面
5. 在浏览器中渲染动画并采样 25 帧
6. 将 25 帧组合为 5x5 网格的胶片条
7. 导出为 1000x1000 PNG 图像

### driver.html

浏览器端页面，负责：

- 加载 lottie-web 动画库
- 解析 Lottie JSON 动画数据
- 按均匀时间间隔渲染 25 个帧
- 将帧排列为 5x5 网格
- 通过 Canvas API 导出 PNG

## 使用方法

### 安装依赖

```bash
cd tools/lottiecap
npm install
```

### 运行

```bash
node ./lottiecap.js --input some_lottie_file.json
```

### 更多选项

```bash
node ./lottiecap.js -h
```

## 依赖项

- **Node.js**: v8.9 或更高版本
- **puppeteer**: 浏览器自动化
- **express**: 本地 HTTP 服务器

安装 Node.js：https://nodejs.org/en/download/

## 输出格式

输出为 1000x1000 像素的 PNG 图像：

```
+------+------+------+------+------+
| 帧 0 | 帧 1 | 帧 2 | 帧 3 | 帧 4 |
+------+------+------+------+------+
| 帧 5 | 帧 6 | 帧 7 | 帧 8 | 帧 9 |
+------+------+------+------+------+
| 帧10 | 帧11 | 帧12 | 帧13 | 帧14 |
+------+------+------+------+------+
| 帧15 | 帧16 | 帧17 | 帧18 | 帧19 |
+------+------+------+------+------+
| 帧20 | 帧21 | 帧22 | 帧23 | 帧24 |
+------+------+------+------+------+
```

每个单元格为 200x200 像素，包含动画在对应时间点的渲染帧。

## CI 集成

在 Skia 的持续集成系统中，该工具用于：

- 生成 Lottie 动画的参考胶片条
- 与之前版本的胶片条进行图像比较
- 检测 Lottie 渲染的视觉回归

## 与其他模块的关系

- **modules/skottie/**: Skia 原生的 Lottie 动画引擎
- **tools/skottie-wasm-perf/**: Skottie WASM 性能测试工具
- **tools/lottie-web-perf/**: lottie-web 性能测试工具
- **modules/canvaskit/**: CanvasKit 提供 Skottie 的 WASM 版本
