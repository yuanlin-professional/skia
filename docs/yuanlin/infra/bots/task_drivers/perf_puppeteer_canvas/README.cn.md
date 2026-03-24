# perf_puppeteer_canvas - Puppeteer Canvas 性能测试驱动

## 概述

使用 Puppeteer（Chrome 无头浏览器自动化工具）执行 HTML Canvas 和 CanvasKit 的性能基准测试。在真实浏览器环境中测量渲染性能。

## 目录结构

```
perf_puppeteer_canvas/
├── perf_puppeteer_canvas.go        # 主程序
├── perf_puppeteer_canvas_test.go   # 单元测试
└── BUILD.bazel                     # Bazel 构建文件
```

## 依赖关系

- Node.js 和 Puppeteer
- Chrome 浏览器
- CanvasKit WASM 模块

## 相关文档与参考

- [Puppeteer](https://pptr.dev/)
- `perf_puppeteer_render_skps/` - SKP 渲染性能测试
- `perf_puppeteer_skottie_frames/` - Skottie 帧性能测试
