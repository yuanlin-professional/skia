# tests - CanvasKit 单元测试与图形正确性测试

## 概述

`tests` 目录包含 CanvasKit 的完整测试套件，涵盖单元测试和图形正确性测试（GM 测试）。
测试使用 Jasmine 框架编写，通过 Karma 测试运行器在真实的 Chrome 浏览器中执行。测试结果
会上报到 Skia 的 Gold 图形正确性系统（gold.skia.org），通过像素级比较确保渲染输出的
一致性。

测试按功能领域分组到不同的文件中，每个文件内部使用 `describe` 块进一步组织，`it()` 函数
定义具体的测试用例。此外，自定义的 `gm()` 方法支持定义图形比较测试，它会将 canvas 绘制
结果快照并上传到 Gold 系统进行基准对比。

测试覆盖了 CanvasKit 的核心 API（Canvas、Paint、Path、Image、Surface）、字体与文本处理、
段落排版、矩阵运算、Skottie 动画、路径操作、运行时着色器等所有主要功能模块。

## 架构图

```
+--------------------------------------------------+
|                Karma 测试运行器                     |
|  karma.conf.js / karma.bazel.js                  |
+--------------------------------------------------+
        |                    |
        v                    v
+------------------+ +------------------+
| 传统模式          | | Bazel 模式       |
| legacy_init.js   | | bazel 初始化     |
| legacy_test_     | | bazel_test_      |
|   reporter.js    | |   reporter.js    |
+------------------+ +------------------+
        |                    |
        v                    v
+--------------------------------------------------+
|              测试初始化 (util.js)                   |
|  - 加载 CanvasKit WASM                            |
|  - 定义 gm() 辅助函数                             |
|  - 定义图像比较工具                                |
+--------------------------------------------------+
        |
        v
+--------------------------------------------------+
|               测试文件集合                          |
|  +----------------+ +------------------+          |
|  | core_test.js   | | canvas_test.js   |          |
|  | (核心功能)      | | (Canvas 绘制)    |          |
|  +----------------+ +------------------+          |
|  +----------------+ +------------------+          |
|  | path_test.js   | | font_test.js     |          |
|  | (路径操作)      | | (字体文本)       |          |
|  +----------------+ +------------------+          |
|  +----------------+ +------------------+          |
|  | paragraph_test | | skottie_test.js  |          |
|  | (段落排版)      | | (Lottie 动画)    |          |
|  +----------------+ +------------------+          |
|  +----------------+ +------------------+          |
|  | matrix_test.js | | rtshader_test.js |          |
|  | (矩阵运算)     | | (运行时着色器)    |          |
|  +----------------+ +------------------+          |
|  +----------------+ +------------------+          |
|  | canvas2d_test  | | bidi_test.js     |          |
|  | (Canvas2D兼容) | | (双向文本)       |          |
|  +----------------+ +------------------+          |
+--------------------------------------------------+
        |
        v
+--------------------------------------------------+
|     测试资源 (assets/)                             |
|  字体文件、图片、Lottie JSON、SKP 等              |
+--------------------------------------------------+
```

## 目录结构

```
tests/
|-- util.js                      # 测试工具与初始化（gm 定义、图像比较）
|-- core_test.js                 # 核心功能测试（Picture、Codec、Surface 等）
|-- canvas_test.js               # Canvas 绘制测试（drawRect、drawImage 等）
|-- canvas2d_test.js             # HTML Canvas 2D 兼容层测试
|-- path_test.js                 # 路径操作测试（PathBuilder、PathOps 等）
|-- font_test.js                 # 字体与文本测试（Font、Typeface、TextBlob）
|-- paragraph_test.js            # 段落排版测试（ParagraphBuilder 等）
|-- matrix_test.js               # 矩阵运算测试（3x3、4x4、DOMMatrix）
|-- skottie_test.js              # Skottie 动画测试（MakeManagedAnimation）
|-- rtshader_test.js             # 运行时着色器测试（SkSL 编译执行）
|-- bidi_test.js                 # 双向文本测试
|-- legacy_init.js               # 传统模式初始化脚本
|-- legacy_test_reporter.js      # 传统模式测试报告器
|-- bazel_test_reporter.js       # Bazel 模式测试报告器
|-- init_with_gold_server.js     # Gold 服务器初始化（CI 环境）
|
|-- assets/                      # 测试资源文件
|   |-- Roboto-Regular.woff2     # Roboto 字体 (WOFF2)
|   |-- Roboto-Regular.woff      # Roboto 字体 (WOFF)
|   |-- Roboto-Regular.otf       # Roboto 字体 (OTF)
|   |-- NotoSerif-Regular.ttf    # Noto Serif 常规字体
|   |-- NotoSerif-BoldItalic.ttf # Noto Serif 粗斜体字体
|   |-- Bungee-Regular.ttf       # Bungee 字体
|   |-- RobotoSlab-VariableFont_wght.ttf  # 可变字体
|   |-- NotoColorEmoji.ttf       # 彩色表情字体
|   |-- test_glyphs-glyf_colr_1.ttf # COLRv1 彩色字体
|   |-- test.ttc                 # 字体集合文件
|   |-- mandrill_512.png         # 测试图片 (PNG)
|   |-- mandrill_16.png          # 小尺寸测试图片
|   |-- mandrill_h1v1.jpg        # 测试图片 (JPEG)
|   |-- color_wheel.webp         # 测试图片 (WebP)
|   |-- color_wheel.gif          # 测试图片 (GIF)
|   |-- flightAnim.gif           # 动画 GIF
|   |-- exif_rotated_heart.jpg   # EXIF 旋转图片
|   |-- brickwork-texture.jpg    # 纹理贴图
|   |-- flutter_106433.png       # Flutter 兼容性测试图
|   |-- animated_gif.json        # Lottie 动画 JSON
|   |-- map-shield.json          # Lottie 动画 JSON
|   |-- text_edit.json           # 文本编辑动画 JSON
|   |-- audio_external.json      # 音频动画 JSON
|   |-- skottie_inline_font.json # 内嵌字体 Lottie
|   |-- skottie_basic_slots.json # Slot 属性 Lottie
|   |-- red_line.skp             # SKP 绘制记录
|   |-- BUILD.bazel              # Bazel 构建配置
```

## 关键类与函数

### util.js 测试工具

```javascript
// gm 定义 - 图形正确性测试
gm(testName, (canvas) => {
    // 在 canvas 上绘制
    // 结果自动快照并上传 Gold
});

// EverythingLoaded - CanvasKit 加载完成的 Promise
await EverythingLoaded;
```

### 测试示例 (core_test.js)
```javascript
describe('Core canvas behavior', () => {
    gm('picture_test', (canvas) => {
        const spr = new CanvasKit.PictureRecorder();
        const rcanvas = spr.beginRecording(bounds, true);
        // 绘制操作...
        const pic = spr.finishRecordingAsPicture();
        canvas.drawPicture(pic);
    });
});
```

## 依赖关系

- **Jasmine**: 测试框架（describe/it/expect）
- **Karma**: 测试运行器（浏览器自动化）
- **CanvasKit WASM**: 被测试的目标库
- **Gold (gold.skia.org)**: 图形正确性比较服务
- **Chrome 浏览器**: 测试执行环境

## 设计模式分析

### GM 测试模式
`gm()` 函数封装了图形正确性测试的完整流程：创建 canvas、执行绘制、快照、上传 Gold 比较。
这与 Skia C++ 端的 GM 测试框架理念一致，确保 WASM 输出与原生输出的视觉一致性。

### 聚焦测试
使用 Jasmine 的 `fdescribe` / `fit` 可临时聚焦到特定测试，加速调试周期。

## 数据流

```
Karma 启动 ---> 加载 canvaskit.wasm
     |
     v
legacy_init.js ---> CanvasKitInit() ---> EverythingLoaded
     |
     v
*_test.js 文件依次执行
     |
     v
gm() 绘制 ---> canvas 快照 (PNG)
     |
     v
上传到 Gold 服务器 ---> 像素级基准比较
```

## 相关文档与参考

- **Karma 配置**: `karma.conf.js`（传统）、`karma.bazel.js`（Bazel）
- **Gold 图形正确性**: https://gold.skia.org
- **Jasmine 文档**: https://jasmine.github.io/
- **测试运行命令**: `make test-continuous` / `make test-continuous-headless`
