# WebGPU API

更新日期：2020 年 6 月 16 日

## 摘要与链接

WebGPU 提供了一个 API，用于在图形处理器 (Graphics Processing Unit) 上执行渲染和计算等操作。
[Dawn](https://dawn.googlesource.com/dawn) 是 WebGPU 在 Chromium 中的底层实现。未来，通过
[emscripten 提供的 WebGPU 绑定](https://github.com/emscripten-core/emscripten/pull/10218)，
CanvasKit 应该能够使用 WebGPU 渲染设备。

- [规范草案](https://gpuweb.github.io/gpuweb/)
- [WebGPU 示例](https://austineng.github.io/webgpu-samples/)
- [实现状态](https://github.com/gpuweb/gpuweb/wiki/Implementation-Status)

部分功能目前可以在 Chrome Canary 中通过 `--enable-unsafe-webgpu` 标志使用。
