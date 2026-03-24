# demos.skia.org/ - Skia 在线演示站点

## 概述

`demos.skia.org/` 包含 Skia 在线演示网站的源码和资源。这些演示展示了
CanvasKit（Skia 的 WebAssembly 版本）的各种功能，包括基础绘图、图像处理、
网格渲染、纹理操作、WebGPU 渲染等。演示可以在浏览器中直接运行。

## 目录结构

```
demos.skia.org/
├── Makefile             # 构建和启动本地服务器
├── README.md            # 原始说明文档
└── demos/               # 演示项目目录
    ├── hello_world/             # Hello World 入门示例
    ├── image_decode_web_worker/ # Web Worker 图像解码
    ├── image_sampling/          # 图像采样模式演示
    ├── mesh2d/                  # 2D 网格渲染
    ├── path_performance/        # 路径渲染性能测试
    ├── sampling_types/          # 采样类型对比
    ├── spreadsheet/             # 电子表格渲染示例
    ├── textedit/                # 文本编辑器
    ├── textures/                # 纹理操作
    ├── up_scaling/              # 图像放大
    ├── web_worker/              # Web Worker 通用示例
    └── webgpu/                  # WebGPU 渲染演示
```

## 使用方法

### 使用本地 CanvasKit 构建
```bash
# 先在 modules/canvaskit 中构建
cd modules/canvaskit && make debug

# 启动本地服务器
cd demos.skia.org && make local
```

注意：需要修改演示代码，使其从本地服务器而非 CDN 加载 CanvasKit。
参考 `demos/hello_world` 中的示例。

## 关键演示

- **hello_world**: 最简单的 CanvasKit 使用示例，适合入门
- **webgpu**: 展示通过 WebGPU API 进行 GPU 加速渲染
- **image_decode_web_worker**: 在 Web Worker 中进行图像解码，不阻塞主线程
- **path_performance**: 路径渲染性能基准测试
- **mesh2d**: 2D 网格和三角形渲染

## 依赖关系

- CanvasKit WASM 模块（`modules/canvaskit/`）
- 现代 Web 浏览器（支持 WebAssembly）
- WebGPU 支持（webgpu 演示需要）

## 相关文档与参考

- CanvasKit 模块: `modules/canvaskit/`
- CanvasKit API 文档: https://skia.org/docs/dev/modules/canvaskit/
- 在线演示: https://demos.skia.org/
