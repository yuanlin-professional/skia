# perf_puppeteer_render_skps - Puppeteer SKP 渲染性能驱动

## 概述

使用 Puppeteer 在浏览器中通过 CanvasKit 渲染 SKP 文件，测量渲染性能。

## 目录结构

```
perf_puppeteer_render_skps/
├── perf_puppeteer_render_skps.go        # 主程序
├── perf_puppeteer_render_skps_test.go   # 单元测试
└── BUILD.bazel                          # Bazel 构建文件
```

## 依赖关系

- Node.js 和 Puppeteer
- SKP 测试数据资源

## 相关文档与参考

- `infra/bots/assets/skp/` - SKP 数据资源
