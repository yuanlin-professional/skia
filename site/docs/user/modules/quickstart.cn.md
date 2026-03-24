
---
title: "CanvasKit - 快速入门"
linkTitle: "CanvasKit - 快速入门"

---


CanvasKit 是一个 wasm 模块，它使用 Skia 绘制到 canvas 元素，提供比 canvas API 更高级的功能集。

最小应用程序
-------------------

这个示例是一个最小的 CanvasKit 应用程序，绘制一个圆角矩形 (rounded rect) 的单帧。
它从 unpkg.com 拉取 wasm 二进制文件，但你也可以自己构建和托管它。

<!--?prettify?-->
``` js
<canvas id=foo width=300 height=300></canvas>

<script type="text/javascript"
  src="https://unpkg.com/canvaskit-wasm@0.19.0/bin/canvaskit.js"></script>
<script type="text/javascript">
  const ckLoaded = CanvasKitInit({
    locateFile: (file) => 'https://unpkg.com/canvaskit-wasm@0.19.0/bin/'+file});
  ckLoaded.then((CanvasKit) => {
    const surface = CanvasKit.MakeCanvasSurface('foo');

    const paint = new CanvasKit.Paint();
    paint.setColor(CanvasKit.Color4f(0.9, 0, 0, 1.0));
    paint.setStyle(CanvasKit.PaintStyle.Stroke);
    paint.setAntiAlias(true);
    const rr = CanvasKit.RRectXY(CanvasKit.LTRBRect(10, 60, 210, 260), 25, 15);

    function draw(canvas) {
      canvas.clear(CanvasKit.WHITE);
      canvas.drawRRect(rr, paint);
    }
    surface.drawOnce(draw);
  });
</script>
```

<canvas id=foo width=300 height=300></canvas>

<script type="text/javascript"
  src="https://unpkg.com/canvaskit-wasm@0.19.0/bin/canvaskit.js"></script>
<script type="text/javascript">
  const ckLoaded = CanvasKitInit({
    locateFile: (file) => 'https://unpkg.com/canvaskit-wasm@0.19.0/bin/'+file});
  ckLoaded.then((CanvasKit) => {
    const surface = CanvasKit.MakeCanvasSurface('foo');

    const paint = new CanvasKit.Paint();
    paint.setColor(CanvasKit.Color4f(0.9, 0, 0, 1.0));
    paint.setStyle(CanvasKit.PaintStyle.Stroke);
    paint.setAntiAlias(true);
    const rr = CanvasKit.RRectXY(CanvasKit.LTRBRect(10, 60, 210, 260), 25, 15);

    function draw(canvas) {
      canvas.clear(CanvasKit.WHITE);
      canvas.drawRRect(rr, paint);
    }
    surface.drawOnce(draw);
  });
</script>

让我们将其分解为各个部分并解释它们的作用：

`<canvas id=foo width=300 height=300></canvas>` 创建了 CanvasKit 将绘制到的 canvas。
该元素是我们控制绘图缓冲区宽度和高度的地方，而它的 css 样式
将控制绘制到这些像素后应用的任何缩放。尽管使用了 canvas 元素，
CanvasKit 并不调用 HTML canvas 自身的绘图方法。它使用此 canvas 元素来
获取 WebGL2 上下文，并在编译为 WebAssembly 的 C++ 代码中执行大部分绘图工作，
然后在每帧结束时向 GPU 发送命令。

<!--?prettify?-->
``` html
<script type="text/javascript"
  src="https://unpkg.com/canvaskit-wasm@0.19.0/bin/canvaskit.js"></script>
```
和

<!--?prettify?-->
``` js
const ckLoaded = CanvasKitInit({
  locateFile: (file) => 'https://unpkg.com/canvaskit-wasm@0.19.0/bin/'+file});
ckLoaded.then((CanvasKit) => {
```
分别加载 canvaskit 辅助 js 和 wasm 二进制文件。CanvasKitInit 接受一个函数，
允许你更改它尝试查找 `canvaskit.wasm` 的路径，并返回一个 promise，
该 promise 解析为已加载的模块，我们通常将其命名为 `CanvasKit`。

<!--?prettify?-->
``` js
const surface = CanvasKit.MakeCanvasSurface('foo');
```
创建与上面 HTML canvas 元素关联的 Surface。
硬件加速是默认行为，但可以通过调用
`MakeSWCanvasSurface` 来覆盖。`MakeCanvasSurface` 也是可以指定替代色彩空间或 gl
属性的地方。

<!--?prettify?-->
``` js
const paint = new CanvasKit.Paint();
paint.setColor(CanvasKit.Color4f(0.9, 0, 0, 1.0));
paint.setStyle(CanvasKit.PaintStyle.Stroke);
paint.setAntiAlias(true);
const rr = CanvasKit.RRectXY(CanvasKit.LTRBRect(10, 60, 210, 260), 25, 15);
```
创建一个 paint（画笔），它描述了如何在 canvaskit 中填充或描边矩形、路径、文本和其他几何图形。
`rr` 是一个圆角矩形，圆角在 x 轴上的半径为 25 像素，y 轴上为 15 像素。

<!--?prettify?-->
``` js
function draw(canvas) {
  canvas.clear(CanvasKit.WHITE);
  canvas.drawRRect(rr, paint);
}
```
定义一个函数来绘制我们的帧。该函数接收一个 Canvas 对象，我们在其上
进行绘制调用。一个用于清除整个画布，另一个用于使用上面的
paint 绘制圆角矩形。

我们还删除了 paint 对象。使用 `new` 创建的 CanvasKit 对象或以 `make` 为前缀的方法
创建的对象必须被删除才能释放 wasm 内存。Javascript 的 GC 不会自动
处理它。`rr` 只是一个数组，不是用 `new` 创建的，也不指向任何 WASM
内存，所以我们不需要对它调用 delete。

<!--?prettify?-->
``` js
surface.drawOnce(draw);
paint.delete()
```
将绘制函数交给 `surface.drawOnce`，它进行调用并刷新 (flush) 表面。
刷新时，Skia 将批处理并发送 WebGL 命令，使可见的更改出现在屏幕上。
此示例绘制一次并释放表面。如承诺的那样，它是一个最小的
应用程序。

基本绘制循环
---------------

如果我们需要每帧重绘画布怎么办？这个示例
像 90 年代的屏幕保护程序一样让一个圆角矩形弹来弹去。

<!--?prettify?-->
``` js
ckLoaded.then((CanvasKit) => {
  const surface = CanvasKit.MakeCanvasSurface('foo2');

  const paint = new CanvasKit.Paint();
  paint.setColor(CanvasKit.Color4f(0.9, 0, 0, 1.0));
  paint.setStyle(CanvasKit.PaintStyle.Stroke);
  paint.setAntiAlias(true);
  // const rr = CanvasKit.RRectXY(CanvasKit.LTRBRect(10, 60, 210, 260), 25, 15);
  const w = 100; // size of rect
  const h = 60;
  let x = 10; // initial position of top left corner.
  let y = 60;
  let dirX = 1; // box is always moving at a constant speed in one of the four diagonal directions
  let dirY = 1;

  function drawFrame(canvas) {
    // boundary check
    if (x < 0 || x+w > 300) {
      dirX *= -1; // reverse x direction when hitting side walls
    }
    if (y < 0 || y+h > 300) {
      dirY *= -1; // reverse y direction when hitting top and bottom walls
    }
    // move
    x += dirX;
    y += dirY;

    canvas.clear(CanvasKit.WHITE);
    const rr = CanvasKit.RRectXY(CanvasKit.LTRBRect(x, y, x+w, y+h), 25, 15);
    canvas.drawRRect(rr, paint);
    surface.requestAnimationFrame(drawFrame);
  }
  surface.requestAnimationFrame(drawFrame);
});
```

<canvas id=foo2 width=300 height=300></canvas>

<script type="text/javascript">
  ckLoaded.then((CanvasKit) => {
    const surface = CanvasKit.MakeCanvasSurface('foo2');

    const paint = new CanvasKit.Paint();
    paint.setColor(CanvasKit.Color4f(0.9, 0, 0, 1.0));
    paint.setStyle(CanvasKit.PaintStyle.Stroke);
    paint.setAntiAlias(true);
    // const rr = CanvasKit.RRectXY(CanvasKit.LTRBRect(10, 60, 210, 260), 25, 15);
    const w = 100; // size of rect
    const h = 60;
    let x = 10; // initial position of top left corner.
    let y = 60;
    // The box is always moving at a constant speed in one of the four diagonal directions
    let dirX = 1;
    let dirY = 1;

    function drawFrame(canvas) {
      // boundary check
      if (x < 0 || x+w > 300) {
        dirX *= -1; // reverse x direction when hitting side walls
      }
      if (y < 0 || y+h > 300) {
        dirY *= -1; // reverse y direction when hitting top and bottom walls
      }
      // move
      x += dirX;
      y += dirY;

      canvas.clear(CanvasKit.WHITE);
      const rr = CanvasKit.RRectXY(CanvasKit.LTRBRect(x, y, x+w, y+h), 25, 15);
      canvas.drawRRect(rr, paint);
      surface.requestAnimationFrame(drawFrame);
    }
    surface.requestAnimationFrame(drawFrame);
  });
</script>

这里的主要区别是我们定义了一个在每帧绘制前被调用的函数，
并将其传递给 `surface.requestAnimationFrame(drawFrame);` 该回调函数会收到一个 `canvas`，
刷新操作会自动处理。

<!--?prettify?-->
``` js
function drawFrame(canvas) {
  canvas.clear(CanvasKit.WHITE);
  // code to update and draw the frame goes here
  surface.requestAnimationFrame(drawFrame);
}
surface.requestAnimationFrame(drawFrame);
```

创建一个函数作为我们的主绘制循环。每次帧即将渲染时
（浏览器通常以 60fps 为目标），我们的函数被调用，我们用白色清除画布，
重新绘制圆角矩形，并调用 `surface.requestAnimationFrame(drawFrame)` 注册
该函数在下一帧前再次被调用。

`surface.requestAnimationFrame(drawFrame)` 将 window.requestAnimationFrame 与
`surface.flush()` 结合使用，应以相同的方式使用。如果你的应用程序只会因鼠标事件
才产生可见变化，
不要在 drawFrame 函数末尾调用 `surface.requestAnimationFrame`。只在
处理鼠标输入后调用它。

文本排版
------------

CanvasKit 提供的超越 HTML Canvas API 的最大功能之一是段落排版 (paragraph shaping)。
要在你的应用程序中使用文本，提供一个字体文件并使用 Promise.all 在 CanvasKit
和字体文件都准备好时运行你的代码。

<!--?prettify?-->
``` js
const loadFont = fetch('https://cdn.skia.org/misc/Roboto-Regular.ttf')
  .then((response) => response.arrayBuffer());

Promise.all([ckLoaded, loadFont]).then(([CanvasKit, robotoData]) => {
  const surface = CanvasKit.MakeCanvasSurface('foo3');
  const canvas = surface.getCanvas();
  canvas.clear(CanvasKit.Color4f(0.9, 0.9, 0.9, 1.0));

  const fontMgr = CanvasKit.FontMgr.FromData([robotoData]);
  const paraStyle = new CanvasKit.ParagraphStyle({
    textStyle: {
      color: CanvasKit.BLACK,
      fontFamilies: ['Roboto'],
      fontSize: 28,
    },
    textAlign: CanvasKit.TextAlign.Left,
  });
  const text = 'Any sufficiently entrenched technology is indistinguishable from Javascript';
  const builder = CanvasKit.ParagraphBuilder.Make(paraStyle, fontMgr);
  builder.addText(text);
  const paragraph = builder.build();
  paragraph.layout(290); // width in pixels to use when wrapping text
  canvas.drawParagraph(paragraph, 10, 10);
  surface.flush();
});
```

<canvas id=foo3 width=300 height=300></canvas>

<script type="text/javascript">
const loadFont = fetch('https://cdn.skia.org/misc/Roboto-Regular.ttf')
  .then((response) => response.arrayBuffer());

Promise.all([ckLoaded, loadFont]).then(([CanvasKit, robotoData]) => {
  const surface = CanvasKit.MakeCanvasSurface('foo3');
  const canvas = surface.getCanvas();
  canvas.clear(CanvasKit.Color4f(0.9, 0.9, 0.9, 1.0));

  const fontMgr = CanvasKit.FontMgr.FromData([robotoData]);
  const paraStyle = new CanvasKit.ParagraphStyle({
    textStyle: {
      color: CanvasKit.BLACK,
      fontFamilies: ['Roboto'],
      fontSize: 28,
    },
    textAlign: CanvasKit.TextAlign.Left,
  });
  const text = 'Any sufficiently entrenched technology is indistinguishable from Javascript';
  const builder = CanvasKit.ParagraphBuilder.Make(paraStyle, fontMgr);
  builder.addText(text);
  const paragraph = builder.build();
  paragraph.layout(290); // width in pixels to use when wrapping text
  canvas.drawParagraph(paragraph, 10, 10);
  surface.flush();
});
</script>

<!--?prettify?-->
``` js
const fontMgr = CanvasKit.FontMgr.FromData([robotoData]);
```
创建一个对象，按名称向 CanvasKit 中的各种文本设施提供字体。如果需要，
你可以在此语句中加载多个字体。

<!--?prettify?-->
``` js
const paraStyle = new CanvasKit.ParagraphStyle({
  textStyle: {
    color: CanvasKit.BLACK,
    fontFamilies: ['Roboto'],
    fontSize: 28,
  },
  textAlign: CanvasKit.TextAlign.Left,
});
```
指定文本的样式。字体名称 Roboto 将用于从字体管理器中获取它。
你可以指定 (color) 或 (foregroundColor 和 backgroundColor) 以获得高亮效果。
有关 API 的完整文档，请查看 npm 包的 `types/` 子文件夹中的 Typescript 定义或
[Skia 仓库](https://github.com/google/skia/tree/main/modules/canvaskit/npm_build/types)。

<!--?prettify?-->
``` js
const builder = CanvasKit.ParagraphBuilder.Make(paraStyle, fontMgr);
builder.addText(text);
const paragraph = builder.build();
```
接下来，我们创建一个带有样式的 `ParagraphBuilder`，添加一些文本，并用 `build()` 完成构建。
或者，我们可以在一个段落中使用多个 `TextStyle`：

<!--?prettify?-->
``` js
const builder = CanvasKit.ParagraphBuilder.Make(paraStyle, fontMgr);
builder.addText(text1);
const boldTextStyle = CanvasKit.TextStyle({
    color: CanvasKit.BLACK,
    fontFamilies: ['Roboto'],
    fontSize: 28,
    fontStyle: {'weight': CanvasKit.FontWeight.Bold},
})
builder.pushStyle(boldTextStyle);
builder.addText(text2);
builder.pop();
builder.addText(text3);
const paragraph = builder.build();
```
最后，我们对段落进行 *layout*（布局），即将文本换行到特定宽度，并使用以下方式将其绘制到
画布上：

<!--?prettify?-->
``` js
paragraph.layout(290); // width in pixels to use when wrapping text
canvas.drawParagraph(paragraph, 10, 10); // (x, y) position of left top corner of paragraph.
```

