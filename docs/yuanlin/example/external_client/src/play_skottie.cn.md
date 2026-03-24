# play_skottie.cpp - Skottie 动画渲染示例

> 源文件: `example/external_client/src/play_skottie.cpp`

## 概述

`play_skottie.cpp` 是一个示例程序，演示了如何使用 Skia 的 Skottie 模块解析和渲染 Lottie 动画文件。Lottie 是 Adobe After Effects 导出的 JSON 格式矢量动画，Skottie 是 Skia 对 Lottie 格式的高性能实现。

该程序从 JSON 文件读取 Lottie 动画，按指定帧数将动画各帧渲染为 PNG 序列图像。支持渲染单帧或多帧动画序列。

## 架构位置

```
Skia 示例程序
├── example/external_client/src/
│   ├── play_skottie.cpp        <-- 本文件：Skottie 动画渲染示例
│   └── ...
├── modules/skottie/
│   └── include/Skottie.h       <-- Skottie API
└── include/encode/
    └── SkPngEncoder.h          <-- PNG 编码器
```

## 主要类与结构体

本文件不定义新类，使用 Skia 的 Skottie API。

### 使用的核心类型
- `skottie::Animation` - Lottie 动画对象
- `SkSurface` / `SkCanvas` - 渲染表面和画布
- `SkFILEStream` - 文件输入流
- `SkPngEncoder` - PNG 编码器

## 公共 API 函数

### `main(int argc, char** argv)`
程序入口。用法：`play_skottie <lottie.json> [<nframes>]`

参数：
- `<lottie.json>`: Lottie 动画 JSON 文件路径
- `[<nframes>]`: 可选的帧数（默认为 1）

执行流程：
1. 读取并解析 Lottie JSON 文件
2. 创建与动画尺寸匹配的光栅 Surface
3. 按帧数循环渲染动画
4. 每帧清除白色背景后渲染动画当前帧
5. 编码为 PNG 输出

## 内部实现细节

### 动画解析

```cpp
auto animation = skottie::Animation::Make(&input);
```

`Animation::Make` 从输入流解析 Lottie JSON，返回动画对象。解析失败返回 `nullptr`。

### Surface 尺寸自适应

```cpp
SkISize surfaceSize = animation->size().toCeil();
auto surface = SkSurfaces::Raster(SkImageInfo::MakeN32Premul(surfaceSize, nullptr));
```

Surface 尺寸从动画的固有尺寸自动获取，使用向上取整确保足够的像素空间。

### 帧时间计算

```cpp
for (unsigned f = 0; f < n; ++f) {
    double t;
    if (n > 1) {
        t = static_cast<double>(f) / (n - 1) * animation->duration();
    } else {
        t = 0.0;
    }
    animation->seekFrameTime(t);
    animation->render(surface->getCanvas());
}
```

- 单帧模式：渲染时间 t=0 的第一帧
- 多帧模式：在动画时长内均匀分布帧时间，首帧对应 t=0，末帧对应 t=duration

### 输出文件命名

```cpp
if (n > 1) {
    outFileName = SkStringPrintf("%s.%u.png", argv[1], f);  // animation.json.0.png
} else {
    outFileName = SkStringPrintf("%s.png", argv[1]);          // animation.json.png
}
```

多帧模式在原始文件名后附加帧编号。

### 每帧清除

```cpp
surface->getCanvas()->clear(SK_ColorWHITE);
animation->seekFrameTime(t);
animation->render(surface->getCanvas());
```

每帧渲染前清除白色背景，确保前一帧的残留不影响当前帧（Lottie 动画可能有透明区域）。

## 依赖关系

- **Skia 核心**：`SkCanvas`, `SkSurface`, `SkStream`, `SkString`
- **Skottie 模块**：`modules/skottie/include/Skottie.h`
- **编码器**：`SkPngEncoder`
- **C++ 标准库**：`<cstdio>`

## 设计模式与设计决策

1. **自适应尺寸**：Surface 尺寸从动画元数据自动获取，无需用户指定，简化了使用。

2. **灵活的帧数控制**：支持单帧快照和多帧序列渲染，通过可选的第二个参数控制。

3. **帧时间而非帧索引**：使用 `seekFrameTime(t)` 以时间为单位定位帧，而非帧索引。这使得帧数可以与动画原始帧率不同，实现任意密度的采样。

4. **结构化绑定的 PNG 编码**：
   ```cpp
   if (SkPixmap pm; !surface->peekPixels(&pm) || !SkPngEncoder::Encode(&out, pm, {}))
   ```
   使用 C++17 的 init-statement 语法使代码更紧凑。

## 性能考量

- **CPU 光栅化**：每帧使用 CPU 渲染。对于复杂的 Lottie 动画和大量帧数，总渲染时间可能较长。
- **每帧文件 I/O**：每帧都创建新的文件流并编码 PNG，I/O 开销随帧数线性增长。
- **Surface 复用**：同一 Surface 在所有帧之间复用，避免重复分配内存。
- **seekFrameTime 的开销**：Skottie 内部可能需要重新计算动画属性树，对于跳跃式寻帧可能比顺序播放开销更大。

## 相关文件

- `modules/skottie/include/Skottie.h` - Skottie 动画 API
- `modules/skottie/include/SkottieProperty.h` - 动画属性操作
- `include/encode/SkPngEncoder.h` - PNG 编码器
- `include/core/SkSurface.h` - Surface API
