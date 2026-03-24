# ImageDecoder API

更新日期：2020 年 6 月 16 日

## 摘要与链接

[ImageDecoder API](https://github.com/dalecurtis/image-decoder-api/blob/master/explainer.md)
负责处理静态和动画图像的解码。
类似于更大的 [web codecs](https://github.com/WICG/web-codecs/blob/master/explainer.md)
提案，后者主要关注视频和音频。
ImageDecoder API 可以与 `CanvasKit.MakeImageFromCanvasImageSource`
配合使用，创建 CanvasKit 兼容的 `SkImage` 对象。
对于静态图像，`createImageBitmap(blob)` API 可以实现相同的效果。

- [说明文档](https://github.com/dalecurtis/image-decoder-api/blob/master/explainer.md)
- [原型实现](https://chromium-review.googlesource.com/c/chromium/src/+/2145133)
- [讨论区](https://discourse.wicg.io/t/proposal-imagedecoder-api-extension-for-webcodecs/4418)

目前作为原型功能，可以在 Chrome Canary 中通过 `--enable-blink-features=WebCodecs` 标志启用，
适用于 85.0.4175.0 及更高版本。

## 运行原型

1. 下载并安装 [Chrome Canary](https://www.google.com/chrome/canary/)。确认您的版本为 85.0.4175.0 或更高。
2. 关闭所有已打开的 Chromium 浏览器实例，包括 Chrome。
2. 使用 `--enable-blink-features=WebCodecs` 标志运行 Chrome Canary。

**MacOS**：运行 `/applications/Google\ Chrome\ Canary.app/Contents/MacOS/Google\ Chrome\ Canary --enable-blink-features=WebCodecs`

**Windows、Linux**：[https://www.chromium.org/developers/how-tos/run-chromium-with-flags](https://www.chromium.org/developers/how-tos/run-chromium-with-flags)

3. 导航至：[http://storage.googleapis.com/dalecurtis/test-gif.html?src=giphy.gif](http://storage.googleapis.com/dalecurtis/test-gif.html?src=giphy.gif)
4. 您应该能看到一个可爱的动画猫咪插图。

## 与 CanvasKit 配合使用的 API 示例

处理静态图像：
```jsx
const response = await fetch(stillImageUrl); // e.g. png or jpeg
const data = await response.arrayBuffer();

const imageDecoder = new ImageDecoder({ data });
const imageBitmap = await imageDecoder.decode();

const skImage = CanvasKit.MakeImageFromCanvasImageSource(imageBitmap);
// do something with skImage, such as drawing it
```

处理动画图像：
```jsx
const response = await fetch(animatedImageUrl); // e.g. gif or mjpeg
const data = await response.arrayBuffer();

const imageDecoder = new ImageDecoder({ data });

for (let frame = 0; frame < imageDecoder.frameCount; frame++) {
    const imageBitmap = await imageDecoder.decode(frame);
    const skImage = CanvasKit.MakeImageFromCanvasImageSource(imageBitmap);
    // do something with skImage, such as drawing it
}
```
