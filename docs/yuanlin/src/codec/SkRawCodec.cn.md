# SkRawCodec — RAW/DNG 图像解码器

> 源文件：[src/codec/SkRawCodec.h](../../src/codec/SkRawCodec.h)、[src/codec/SkRawCodec.cpp](../../src/codec/SkRawCodec.cpp)

## 概述

`SkRawCodec` 是 Skia 编解码框架中的 RAW/DNG 图像解码器实现。它继承自 `SkCodec`，通过两个外部库实现 RAW 图像的解码：

- **PIEX（Preview Image EXtractor）**：快速提取 RAW 文件中嵌入的 JPEG 预览图
- **Adobe DNG SDK**：完整的 DNG（Digital Negative）图像处理管线，包括去马赛克（demosaic）、色彩渲染等

核心功能包括：
- RAW 文件格式检测（通过 PIEX 和 TIFF 头部验证）
- 嵌入式 JPEG 预览图的快速提取（优先策略）
- DNG 图像的完整渲染（去马赛克 → Stage2 → Stage3 → sRGB 输出）
- 整数因子缩放（利用 DNG SDK 的去马赛克缩放能力）
- 多线程并行处理（通过 `SkTaskGroup` 和自定义 `dng_host`）
- 流式数据访问（支持 asset 流和缓冲流两种模式）

## 架构位置

```
SkCodec (抽象基类)
    │
    ├── SkRawCodec
    │       │
    │       ├── SkDngImage (DNG 图像管理)
    │       │   ├── DNG SDK (dng_host, dng_negative, dng_render, ...)
    │       │   └── PIEX (快速元数据提取)
    │       │
    │       ├── SkRawStream (流抽象层)
    │       │   ├── SkRawAssetStream (可寻址流)
    │       │   └── SkRawBufferedStream (缓冲流，100MB 上限)
    │       │
    │       └── SkJpegCodec (用于解码嵌入的 JPEG 预览图)
    │
    └── skcms (最终色彩空间转换)
```

## 主要类与结构体

### `SkRawCodec`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fDngImage` | `unique_ptr<SkDngImage>` | DNG 图像处理器 |

### `SkDngImage`（内部类）

| 成员 | 类型 | 说明 |
|------|------|------|
| `fStream` | `unique_ptr<SkRawStream>` | RAW 数据流 |
| `fHost` | `unique_ptr<dng_host>` | DNG SDK 宿主 |
| `fInfo` | `unique_ptr<dng_info>` | DNG 文件信息 |
| `fNegative` | `unique_ptr<dng_negative>` | DNG 底片对象 |
| `fDngStream` | `unique_ptr<dng_stream>` | DNG SDK 流适配 |
| `fWidth` / `fHeight` | `int` | 图像尺寸 |
| `fIsScalable` | `bool` | 是否支持缩放（需有马赛克信息） |
| `fIsXtransImage` | `bool` | 是否为 Xtrans 传感器图像 |

### `SkDngHost`（自定义 dng_host）

重写 `PerformAreaTask()` 使用 `SkTaskGroup` 实现多线程瓦片处理。Android 平台限制为单线程以避免内存过量使用。

### `SkRawStream`（流抽象）

- **`SkRawAssetStream`**：适用于可寻址的 asset 流，支持 `seek()` 和 `getLength()`
- **`SkRawBufferedStream`**：适用于不可寻址的流，数据按需缓冲到 `SkRawLimitedDynamicMemoryWStream`（100MB 上限），最小读取单位 8KB

### 流适配器

- **`SkPiexStream`**：将 `SkRawStream` 适配为 PIEX 的 `StreamInterface`
- **`SkDngStream`**：将 `SkRawStream` 适配为 DNG SDK 的 `dng_stream`

## 公共 API 函数

### `MakeFromStream(unique_ptr<SkStream>, Result*) -> unique_ptr<SkCodec>`

静态工厂方法，解码策略如下：
1. 根据流类型选择 `SkRawAssetStream` 或 `SkRawBufferedStream`
2. 使用 PIEX 检测是否为 RAW 文件
3. 如果 PIEX 找到 JPEG 压缩的预览图 → 创建 `SkJpegCodec`（最快路径）
4. 否则验证 TIFF 头部 → 创建 `SkDngImage` → 构造 `SkRawCodec`

### `onGetPixels(...) -> Result`

渲染 DNG 图像：
1. 调用 `SkDngImage::render()` 获取渲染后的 `dng_image`
2. 逐行读取 RGB888 数据
3. 使用 `skcms_Transform()` 执行最终的色彩空间转换

### `onGetScaledDimensions(float desiredScale) -> SkISize`

返回缩放后尺寸。DNG SDK 仅支持整数因子缩放，最小边长 80 像素。Xtrans 传感器图像在半尺寸缩放时退回到 1/3 缩放。

### `onDimensionsSupported(const SkISize&) -> bool`

检查请求的尺寸是否可通过整数因子缩放实现（检查 floor 和 ceil 两种舍入方式）。

## 内部实现细节

### PIEX 快速路径

大多数 RAW 文件（来自各制造商如 Canon、Nikon、Sony 等）内嵌 JPEG 预览图。PIEX 可以快速定位和提取这些预览图，避免完整的 DNG 处理管线。如果 PIEX 返回 AdobeRGB 色彩空间信息，会传递给 `SkJpegCodec` 作为默认颜色配置文件。

### DNG 渲染管线

`SkDngImage::render()` 执行完整的 DNG 处理：
1. `ReadStage1Image` — 读取原始传感器数据
2. `ReadTransparencyMask` — 读取透明遮罩（如果存在）
3. `ValidateRawImageDigest` — 验证数据完整性
4. `BuildStage2Image` — 去马赛克（demosaicing）
5. `BuildStage3Image` — 颜色校正
6. `dng_render::Render` — 最终渲染（输出 sRGB、8 位 RGB）

### 多线程瓦片处理

`SkDngHost::PerformAreaTask()` 将图像分割为瓦片（通常 256x256），分配到多个线程并行处理。异常通过 `SkMutex` 保护的数组收集，处理完成后重新抛出第一个异常。

### 内存安全

- `SkRawLimitedDynamicMemoryWStream` 限制缓冲区大小为 100MB
- `safe_add_to_size_t()` 模板函数防止整数溢出
- DNG SDK 异常通过 try/catch 捕获并转为错误码返回
- `SkDngStream` 构造时设置 `offsetInOriginalFile=0` 以避免 DNG SDK 的无符号溢出 bug

### 尺寸容差

DNG SDK 不保证精确渲染到请求尺寸。`onGetPixels()` 允许最大 3% 的尺寸差异（`maxDiffRatio = 1.03f`），仅转换重叠区域。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| Adobe DNG SDK | DNG 图像处理（dng_host、dng_negative、dng_render 等） |
| PIEX | RAW 文件预览图提取 |
| `SkJpegCodec` | 解码嵌入的 JPEG 预览图 |
| `skcms` | 色彩空间转换 |
| `SkTaskGroup` | 多线程任务分组 |
| `SkMutex` | 线程同步 |
| `SkCodec` | 编解码器基类 |
| `SkCodecPriv` | 字节序工具 |

## 设计模式与设计决策

1. **双路径解码策略**：优先尝试 PIEX 快速提取 JPEG 预览图，失败时退回到完整 DNG 渲染。这在绝大多数情况下提供了最优性能。

2. **流抽象层**：`SkRawStream` 抽象了两种流访问模式（可寻址 vs 缓冲），使上层代码无需关心底层流的能力差异。

3. **适配器模式**：`SkPiexStream` 和 `SkDngStream` 将 `SkRawStream` 适配为第三方库期望的流接口，解耦了 Skia 流体系和外部库。

4. **自定义 DNG Host**：`SkDngHost` 重写了 `PerformAreaTask()` 用 Skia 的 `SkTaskGroup` 替代 DNG SDK 默认的线程模型，并在 Android 上限制为单线程以控制内存。

5. **色彩管理分离**：`usesColorXform()` 返回 `false`，因为 DNG SDK 自行处理色彩转换（输出固定为 sRGB），最终通过 `skcms` 转到目标色彩空间。

6. **Libfuzzer 保护**：在 Libfuzzer 构建中，`SkDngImage::NewFromStream` 直接返回 `nullptr`，因为 DNG SDK 的内存使用容易触发 OOM。

## 性能考量

- **PIEX 快速路径**：提取嵌入式 JPEG 比完整 DNG 渲染快 10-100 倍。
- **整数因子缩放**：DNG SDK 在去马赛克阶段直接缩放，避免先渲染全尺寸再缩放的开销。
- **多线程瓦片处理**：DNG 渲染的计算密集操作通过瓦片并行化加速。
- **100MB 缓冲上限**：防止非 asset 流读取时无限缓冲，但可能导致超大 RAW 文件解码失败。
- **最小读取 8KB**：`SkRawBufferedStream` 避免过多小读取操作，提高 I/O 效率。
- **Android 单线程限制**：DNG warp 效果的内存消耗与线程数线性相关，单线程可节省约 50% 的内存。

## 相关文件

- `src/codec/SkJpegCodec.h` — JPEG 解码（用于预览图）
- `include/codec/SkRawDecoder.h` — RAW 解码器公共接口
- `src/codec/SkCodecPriv.h` — 编解码器私有工具
- `src/core/SkTaskGroup.h` — 多线程任务组
- `src/core/SkStreamPriv.h` — 流拷贝工具
