Skia Canvas API 的 WASM 版本。

更多背景信息请参见 https://skia.org/user/modules/canvaskit。

# 快速入门

## 浏览器

要使用该库，请运行 `npm install canvaskit-wasm`，然后简单地引入：

```html
<script src="/node_modules/canvaskit-wasm/bin/canvaskit.js"></script>
```
```javascript
CanvasKitInit({
    locateFile: (file) => '/node_modules/canvaskit-wasm/bin/'+file,
}).then((CanvasKit) => {
    // Code goes here using CanvasKit
});
```

与所有 npm 包一样，可以通过 unpkg.com 免费使用 CDN：

```html
<script src="https://unpkg.com/canvaskit-wasm@latest/bin/canvaskit.js"></script>
```
```javascript
CanvasKitInit({
    locateFile: (file) => 'https://unpkg.com/canvaskit-wasm@latest/bin/'+file,
}).then((CanvasKit) => {
    // Code goes here using CanvasKit
});
```

## Node
要在 Node 中使用 CanvasKit，方法与浏览器类似：

```javascript
const CanvasKitInit = require('canvaskit-wasm/bin/canvaskit.js');
CanvasKitInit({
    locateFile: (file) => __dirname + '/bin/'+file,
}).then((CanvasKit) => {
    // Code goes here using CanvasKit
});
```

## WebPack

WebPack 对 WASM 的支持仍处于实验阶段，但 CanvasKit 可以通过一些配置更改来使用。

在 JS 代码中，使用 require()：

```javascript
const CanvasKitInit = require('canvaskit-wasm/bin/canvaskit.js')
CanvasKitInit().then((CanvasKit) => {
    // Code goes here using CanvasKit
});
```

由于 WebPack 不会暴露整个 `/node_modules/` 目录，而只打包所需的部分，我们需要将 canvaskit.wasm 复制到构建目录中。
一种解决方案是使用 [CopyWebpackPlugin](https://github.com/webpack-contrib/copy-webpack-plugin)。
例如，添加以下插件：

```javascript
config.plugins.push(
    new CopyWebpackPlugin([
        { from: 'node_modules/canvaskit-wasm/bin/canvaskit.wasm' }
    ])
);
```

如果 webpack 出现类似以下错误：

```warn
ERROR in ./node_modules/canvaskit-wasm/bin/canvaskit.js
Module not found: Error: Can't resolve 'fs' in '...'
```

则需要在配置的 node 部分添加以下配置更改：

```javascript
config.node = {
    fs: 'empty'
};
```


# 不同的 canvaskit 构建包

`canvaskit-wasm` 包含 3 种构建包：

* 默认版 `./bin/canvaskit.js` - 基本的 canvaskit 功能


```javascript
const InitCanvasKit = require('canvaskit-wasm/bin/canvaskit');
```

* 完整版 `./bin/full/canvaskit.js` - 包含 [Skottie](https://skia.org/docs/user/modules/skottie/) 和其他库

```javascript
const InitCanvasKit = require('canvaskit-wasm/bin/full/canvaskit');
```

* 性能分析版 (Profiling) `./bin/profiling/canvaskit.js` - 与 `full` 相同，但包含内部调用的 WASM 函数的完整名称

```javascript
const InitCanvasKit = require('canvaskit-wasm/bin/profiling/canvaskit');
```

# ES6 导入和 Node 入口点 (Entrypoints)

此包还暴露了[入口点](https://nodejs.org/api/packages.html#package-entry-points)

```javascript
import InitCanvasKit from 'canvaskit-wasm'; // default
```

```javascript
import InitCanvasKit from 'canvaskit-wasm/full';
```

```javascript
import InitCanvasKit from 'canvaskit-wasm/profiling';
```

如果您使用 [TypeScript](https://www.typescriptlang.org/)，

需要在 `tsconfig.json` 中启用 [resolvePackageJsonExports](https://www.typescriptlang.org/tsconfig#resolvePackageJsonExports)

```json
{
    "compilerOptions": {
        "resolvePackageJsonExports": true
    }
}
```

# 使用 CanvasKit API

请参阅 `example.html` 和 `node.example.js` 了解核心 API 的使用演示。

请参阅 `extra.html` 了解一些可选附加功能，例如动画播放器 (Skottie)。

请参阅 `types/index.d.ts` 获取包含所有 API 及部分文档的 TypeScript 定义文件。

## Canvas2D 直接替代方案

在无法使用 HTML Canvas 的环境中（例如 Node、无头服务器），
CanvasKit 有一个可选 API（默认包含），大部分模拟了 [CanvasRenderingContext2D](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D) 接口。

```javascript
const skcanvas = CanvasKit.MakeCanvas(600, 600);

const ctx = skcanvas.getContext('2d');
const rgradient = ctx.createRadialGradient(200, 300, 10, 100, 100, 300);

// Add three color stops
rgradient.addColorStop(0, 'red');
rgradient.addColorStop(0.7, 'white');
rgradient.addColorStop(1, 'blue');

ctx.fillStyle = rgradient;
ctx.globalAlpha = 0.7;
ctx.fillRect(0, 0, 600, 600);

const imgData = skcanvas.toDataURL();
// imgData is now a base64 encoded image.
```

更多示例请参见 `example.html` 和 `node.example.js`。

### Canvas2D 模拟层的已知问题
 - measureText 仅返回宽度且不进行文本整形 (Shaping)。它仅对 ASCII 字母大致有效。
 - 不支持 textAlign。
 - 不支持 textBaseAlign。
 - fillText 不支持 width 参数。

# 提交 Bug

请在 [https://skbug.com](skbug.com) 提交 Bug。
使用[我们的在线代码演示工具](https://jsfiddle.skia.org/canvaskit)来展示遇到的问题可能会比较方便。

有关提交拉取请求 (Pull Request) 的更多信息，请参阅 CONTRIBUTING.md。

# 类型定义与文档

TypeScript 类型定义和相关 API 文档位于 [types/](./types/) 目录中。
