# serve_wasm - WASM 开发服务器

> 源文件: `tools/serve_wasm.py`

## 概述

`serve_wasm.py` 是一个简单的 HTTP 服务器,为 `.wasm` 文件设置正确的 MIME 类型 (`application/wasm`),使浏览器能够进行异步编译。监听端口 8000。

## 架构位置

属于 CanvasKit/WASM 本地开发工具。

## 内部实现细节

- 继承 `http.server.SimpleHTTPRequestHandler`
- 添加 `.wasm` -> `application/wasm` 和 `.js` -> `application/javascript` MIME 映射
- 使用 `socketserver.TCPServer`

## 依赖关系

- Python 标准库: `http.server`, `socketserver`

## 性能考量

单线程服务器,仅用于开发目的。

## 相关文件

- CanvasKit 本地开发文档
