# serve.py

> 源文件: specs/web-img-decode/proposed/serve.py

## 概述

`serve.py` 是一个轻量级的 HTTP 服务器脚本,专门用于在本地测试 Web 图像解码规范的实现。该脚本基于 Python 的 `http.server` 模块创建一个简单的静态文件服务器,并配置了正确的 MIME 类型来支持 JavaScript 模块和 WebAssembly,确保基于 CanvasKit-WASM 的图像解码 polyfill 能够正确加载和运行。

这个工具是 Skia 的 Web 图像解码规范验证流程的一部分,为开发者提供了一个即开即用的测试环境,无需配置复杂的 Web 服务器。

## 架构位置

`serve.py` 在 Skia Web 规范测试框架中的位置:

```
skia/
├── specs/
│   └── web-img-decode/
│       └── proposed/
│           ├── serve.py             # 本脚本 - 测试服务器
│           ├── index.html           # 测试页面入口
│           ├── impl/
│           │   ├── impl.js          # Polyfill 实现
│           │   └── ...
│           └── canvaskit.wasm       # CanvasKit WebAssembly 模块
```

工作流程:
1. **启动服务器**: `python serve.py`
2. **访问测试页面**: 浏览器打开 `http://localhost:8000`
3. **加载资源**: 服务器提供 HTML/JS/WASM 文件
4. **运行测试**: 浏览器执行图像解码测试

## 主要类与结构体

### Handler 类

```python
class Handler(http.server.SimpleHTTPRequestHandler):
    pass
```

**继承关系**: `Handler` → `SimpleHTTPRequestHandler` → `BaseHTTPRequestHandler`

**用途**: 自定义 HTTP 请求处理器

**特性**:
- 继承 `SimpleHTTPRequestHandler` 的所有功能
- 静态文件服务(自动)
- 目录列表(自动)
- 支持 GET 和 HEAD 请求

**为什么是空类?**
- 仅需修改类属性(`extensions_map`),不需要重写方法
- 保持代码简洁
- 充分利用父类功能

## 公共 API 函数

### 脚本执行流程

```python
PORT = 8000

Handler.extensions_map['.js'] = 'application/javascript'
Handler.extensions_map['.wasm'] = 'application/wasm'

httpd = socketserver.TCPServer(("", PORT), Handler)

httpd.serve_forever()
```

**功能**: 启动 HTTP 服务器并永久运行

**服务器配置**:
- **端口**: 8000
- **绑定地址**: "" (所有网络接口,包括 localhost 和局域网 IP)
- **请求处理器**: 自定义的 `Handler` 类

**运行示例**:
```bash
# 启动服务器
python specs/web-img-decode/proposed/serve.py

# 访问测试页面
open http://localhost:8000/index.html

# 或从其他设备访问(局域网)
open http://192.168.1.100:8000/index.html
```

**停止服务器**: Ctrl+C 发送 KeyboardInterrupt

## 内部实现细节

### 端口配置

```python
PORT = 8000
```

**端口选择理由**:
- 8000 是常用的开发服务器端口
- 无需 root 权限(> 1024)
- 通常不被其他服务占用
- 易于记忆

**端口冲突处理**:
脚本不处理端口占用情况,如果 8000 被占用会抛出异常:
```python
OSError: [Errno 48] Address already in use
```

### MIME 类型配置

```python
Handler.extensions_map['.js'] = 'application/javascript'
# Without the correct MIME type, async compilation doesn't work
Handler.extensions_map['.wasm'] = 'application/wasm'
```

**为什么需要配置 MIME 类型?**

**JavaScript 模块**:
- 标准 MIME 类型: `application/javascript`
- 旧版可能使用: `text/javascript`
- ES6 模块需要正确的 MIME 类型才能加载

**WebAssembly**:
- 标准 MIME 类型: `application/wasm`
- 默认可能缺失此类型
- 异步编译(`WebAssembly.instantiateStreaming()`)严格要求正确的 MIME 类型

**浏览器行为**:
```javascript
// 需要 application/wasm MIME 类型
WebAssembly.instantiateStreaming(fetch('canvaskit.wasm'))
    .then(module => { /* 使用模块 */ });

// 如果 MIME 类型错误,会回退到:
fetch('canvaskit.wasm')
    .then(response => response.arrayBuffer())
    .then(bytes => WebAssembly.instantiate(bytes));
```

### TCP 服务器创建

```python
httpd = socketserver.TCPServer(("", PORT), Handler)
```

**参数解析**:
- **`("", PORT)`**: 服务器地址元组
  - `""`: 空字符串表示绑定所有可用接口
  - `PORT`: 监听端口 8000
- **`Handler`**: 请求处理器类(不是实例)

**TCP vs 其他协议**:
- HTTP 基于 TCP
- `TCPServer` 提供可靠的连接
- 自动处理多个并发请求(单线程但支持 keep-alive)

### 服务器主循环

```python
httpd.serve_forever()
```

**行为**:
- 阻塞式调用,永不返回(除非异常)
- 监听端口,接受连接
- 为每个请求调用 `Handler`
- 单线程处理(适合开发测试)

**信号处理**:
- Ctrl+C 触发 `KeyboardInterrupt`
- Python 自动清理并退出
- 不需要显式的 try-finally

## 依赖关系

### Python 标准库

```python
import http.server    # HTTP 服务器实现
import socketserver   # 网络服务器框架
```

**http.server 模块**:
- Python 3.x 标准库
- Python 2.x 为 `SimpleHTTPServer`
- 提供基本的 HTTP/1.0 和 HTTP/1.1 支持

**socketserver 模块**:
- 通用网络服务器框架
- 支持 TCP, UDP, Unix domain sockets
- 提供多线程和多进程选项(未使用)

**无外部依赖**: 完全基于标准库,即开即用。

### 服务的文件

**HTML 入口**:
- `index.html`: 主测试页面

**JavaScript 实现**:
- `impl/impl.js`: 图像解码 polyfill 实现

**WebAssembly 模块**:
- `canvaskit.wasm`: Skia 的 WebAssembly 编译版本
- 可能从 CDN 加载(如 unpkg.com)

## 设计模式与设计决策

### 最小配置原则

**仅修改必要的设置**:
```python
# 仅添加两个 MIME 类型
Handler.extensions_map['.js'] = 'application/javascript'
Handler.extensions_map['.wasm'] = 'application/wasm'
```

不修改其他行为:
- 不添加路由
- 不添加中间件
- 不配置日志
- 不处理 CORS

### 开发友好设计

**即开即用**:
- 无配置文件
- 无命令行参数
- 固定端口(简化文档)
- 自动服务当前目录

**局限性接受**:
- 单线程(开发测试足够)
- 无 HTTPS(本地测试无需)
- 无认证(本地使用)
- 固定端口(可手动修改代码)

### 现代 Web 标准支持

**WebAssembly 优化**:
```python
Handler.extensions_map['.wasm'] = 'application/wasm'
```
确保使用最快的 WASM 加载路径(`instantiateStreaming`)。

**JavaScript 模块支持**:
```python
Handler.extensions_map['.js'] = 'application/javascript'
```
支持 ES6 模块的 `import/export` 语法。

### 简洁优于复杂

**为什么不使用更强大的服务器?**

**替代方案**:
- Flask/Django: 过于重量级
- Node.js http-server: 需要额外安装
- Apache/Nginx: 配置复杂

**选择 Python 内置服务器的理由**:
- Python 在 Skia 构建环境中总是可用
- 无额外依赖
- 代码清晰易懂
- 满足测试需求

## 性能考量

### 并发限制

**单线程处理**:
- 一次处理一个请求
- 适合开发测试(单用户)
- 不适合生产环境

**改进选项**(未实现):
```python
# 多线程版本
from socketserver import ThreadingMixIn
class ThreadedTCPServer(ThreadingMixIn, socketserver.TCPServer):
    pass
httpd = ThreadedTCPServer(("", PORT), Handler)
```

### 文件服务性能

**缓存行为**:
- 发送 `Last-Modified` 头
- 支持 `If-Modified-Since` 条件请求
- 浏览器缓存生效

**静态文件优化**:
- 无压缩(gzip/brotli)
- 无 CDN
- 直接读取文件系统
- 对小文件(< 1MB)性能足够

### 内存占用

**最小内存足迹**:
- Python 基线: ~10-20 MB
- 服务器开销: ~5 MB
- 每个连接: ~100 KB
- 总计: < 50 MB(对开发机器可忽略)

## 相关文件

### 测试页面

**index.html**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Image Decode Polyfill Test</title>
    <script src="impl/impl.js"></script>
</head>
<body>
    <h1>Web Image Decode Proposal Test</h1>
    <!-- 测试界面 -->
</body>
</html>
```

### Polyfill 实现

**impl/impl.js**:
- 实现 Web 图像解码 API 的 polyfill
- 使用 CanvasKit-WASM 作为后端
- 提供 `createImageData()` 等函数

### CanvasKit 资源

**可能的文件**:
- `canvaskit.wasm`: WebAssembly 二进制模块
- `canvaskit.js`: JavaScript 加载器和绑定
- 通常从 CDN 加载(如 unpkg.com)

### 相关规范文档

**README 或规范文档**:
- 描述图像解码 API 提案
- 使用说明
- 浏览器兼容性信息

### 替代服务器

**其他 Python 服务器**:
```bash
# Python 3
python -m http.server 8000

# Python 2
python -m SimpleHTTPServer 8000
```

**为什么不直接使用?**
- 需要手动配置 MIME 类型(通过系统 mime.types)
- serve.py 提供开箱即用的配置
- 明确的 WASM 支持说明

### 生产部署

**开发 vs 生产**:
```python
# 开发(serve.py)
python serve.py

# 生产(Nginx 配置示例)
location ~ \.wasm$ {
    types { application/wasm wasm; }
}
location ~ \.js$ {
    types { application/javascript js; }
}
```

### 安全考虑

**仅用于开发**:
- 绑定所有接口(`""`)可能暴露到局域网
- 无访问控制
- 无 HTTPS
- 不应用于公网部署

**安全改进**(如需要):
```python
# 仅绑定 localhost
httpd = socketserver.TCPServer(("127.0.0.1", PORT), Handler)

# 或使用环境变量配置
import os
HOST = os.getenv('SERVER_HOST', '127.0.0.1')
httpd = socketserver.TCPServer((HOST, PORT), Handler)
```

该脚本提供了一个简单有效的本地测试服务器,通过正确配置 MIME 类型确保现代 Web 技术(特别是 WebAssembly)能够正常工作,是 Web 规范验证工作流中不可或缺的开发工具。
