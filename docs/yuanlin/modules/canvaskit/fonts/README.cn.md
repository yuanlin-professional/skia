# fonts - CanvasKit 内嵌字体资源

## 概述

`fonts` 目录包含 CanvasKit 内嵌的默认字体资源。当启用 `skia_canvaskit_enable_embedded_font`
构建选项时，此目录下的字体文件会通过 `embed_resources.py` 工具在编译时嵌入到 WASM 二进制
文件中，成为 CanvasKit 的内置默认字体。

当前唯一的内嵌字体是 `NotoMono-Regular.ttf`（Google 的 Noto Mono 等宽字体），它作为
CanvasKit 的后备默认字体使用。当用户未指定自定义字体时，所有文本绘制操作会使用此内嵌字体。
这种设计确保了即使在没有系统字体的 WASM 环境中，基本的文本渲染也能正常工作。

嵌入字体会增加最终 WASM 二进制的体积，因此 CanvasKit 提供了 `no_embedded_font` 编译选项
来排除内嵌字体，以及 `no_font` 选项来完全禁用字体相关功能，从而大幅减小产物体积。

## 架构图

```
+---------------------------------------------------+
|              构建时字体嵌入流程                      |
+---------------------------------------------------+
|                                                   |
|  fonts/NotoMono-Regular.ttf                       |
|         |                                         |
|         v                                         |
|  tools/embed_resources.py                         |
|  (--name=SK_EMBEDDED_FONTS)                       |
|         |                                         |
|         v                                         |
|  NotoMono-Regular.ttf.ninja.cpp                   |
|  (自动生成的 C++ 资源文件)                          |
|         |                                         |
|         v                                         |
|  编译链接到 canvaskit.wasm                         |
|         |                                         |
|         v                                         |
|  运行时: SK_EMBEDDED_FONTS 全局资源                 |
|         |                                         |
|         v                                         |
|  SkFontMgr 使用内嵌字体作为默认字体                 |
+---------------------------------------------------+
```

## 目录结构

```
fonts/
|-- NotoMono-Regular.ttf     # Google Noto Mono 等宽字体（内嵌默认字体）
|-- README.md                # 英文说明文档
```

## 关键类与函数

### 构建系统集成 (BUILD.gn)

```gn
action("create_notomono_cpp") {
  script = "../../tools/embed_resources.py"
  inputs = [ "fonts/NotoMono-Regular.ttf" ]
  output_path = "$root_out_dir/modules/canvaskit/fonts/NotoMono-Regular.ttf.ninja.cpp"
  args = [
    "--name=SK_EMBEDDED_FONTS",
    "--input", rebase_path("fonts/NotoMono-Regular.ttf"),
    "--output", rebase_path(output_path),
    "--align=4",
  ]
}
```

### C++ 资源结构 (canvaskit_bindings.cpp)

```cpp
struct SkEmbeddedResource {
    const uint8_t* data;
    size_t size;
};
struct SkEmbeddedResourceHeader {
    const SkEmbeddedResource* entries;
    int count;
};
extern "C" const SkEmbeddedResourceHeader SK_EMBEDDED_FONTS;
```

## 依赖关系

- **embed_resources.py**: `tools/embed_resources.py` 将字体二进制转换为 C++ 数组
- **CK_EMBED_FONT 宏**: 控制是否包含内嵌字体的编译宏
- **SkFontMgr_data**: 使用内嵌数据创建字体管理器的 Skia 端口
- **FreeType**: 字体光栅化引擎，用于解析和渲染 TTF 字体

## 设计模式分析

### 编译时资源嵌入
字体文件在编译时转换为 C++ 常量数组并直接链接到 WASM 二进制中，避免了运行时网络加载的
延迟和不确定性。这是嵌入式环境中资源分发的常见模式。

### 可选嵌入
通过 `skia_canvaskit_enable_embedded_font` 构建标志，用户可以选择是否嵌入默认字体。
不嵌入字体可以减小 WASM 文件约几十 KB，适合自行提供字体的应用场景。

## 数据流

```
编译时:
  NotoMono-Regular.ttf ---> embed_resources.py ---> .cpp 文件 ---> 链接到 .wasm

运行时:
  CanvasKit 初始化
       |
       v
  读取 SK_EMBEDDED_FONTS 全局资源
       |
       v
  SkFontMgr_data::Make(SK_EMBEDDED_FONTS)
       |
       v
  创建默认 SkTypeface
       |
       v
  CanvasKit.Typeface.GetDefault() ----> 返回内嵌字体的 Typeface
```

## 相关文档与参考

- **Google Noto Fonts**: https://fonts.google.com/noto
- **嵌入工具**: `tools/embed_resources.py`
- **构建配置**: `BUILD.gn` 中的 `create_notomono_cpp` action
- **编译选项**: `./compile.sh no_embedded_font` 或 `./compile.sh no_font`
