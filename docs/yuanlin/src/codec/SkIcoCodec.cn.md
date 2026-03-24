# SkIcoCodec - ICO/CUR 图像解码器

> 源文件: `src/codec/SkIcoCodec.h`, `src/codec/SkIcoCodec.cpp`

## 概述

`SkIcoCodec` 是 Skia 图像编解码框架中用于解码 ICO（图标）和 CUR（光标）格式图像的编解码器实现。ICO/CUR 文件是一种容器格式，内部可以嵌入多个不同尺寸的 BMP 或 PNG 图像。`SkIcoCodec` 的核心设计思路是将解码工作委托给内嵌的子编解码器（BMP 或 PNG），自身主要负责解析容器结构和选择最合适的嵌入图像。

## 架构位置

`SkIcoCodec` 位于 Skia 编解码模块（`src/codec/`）中，继承自 `SkCodec` 基类。它在编解码注册系统中通过 `SkIcoDecoder` 命名空间暴露 `IsIco` 和 `Decode` 接口，用于格式检测和解码入口。

```
SkCodec (基类)
  └── SkIcoCodec
        ├── 内嵌 SkPngCodec (PNG 子图像)
        └── 内嵌 SkBmpCodec (BMP 子图像)
```

## 主要类与结构体

### `SkIcoCodec`
- 继承自 `SkCodec`
- 管理一组嵌入的子编解码器 (`fEmbeddedCodecs`)
- 维护当前活跃的子编解码器指针 (`fCurrCodec`)，用于扫描行解码和增量解码
- 提供 ICO 格式的检测、创建和解码功能

### `Entry`（内部结构体）
- 在 `MakeFromStream` 中定义的临时结构体
- 存储每个嵌入图像的偏移量 (`offset`) 和大小 (`size`)
- 用于排序和定位嵌入图像

## 公共 API 函数

### `static bool IsIco(const void*, size_t)`
检查数据流的前 4 个字节是否匹配 ICO 签名 (`\x00\x00\x01\x00`) 或 CUR 签名 (`\x00\x00\x02\x00`)。

### `static std::unique_ptr<SkCodec> MakeFromStream(std::unique_ptr<SkStream>, Result*)`
从数据流创建 ICO 解码器。此方法执行以下步骤：
1. 将整个流读入连续的内存缓冲区
2. 解析 ICO 目录头，获取嵌入图像数量
3. 按偏移量排序嵌入图像
4. 为每个嵌入图像创建子编解码器（PNG 或 BMP）
5. 选择最大的图像作为默认图像信息

### `SkIcoDecoder::Decode`
命名空间级别的解码入口，内部调用 `MakeFromStream`。提供 `SkStream` 和 `SkData` 两种重载。

## 内部实现细节

### 子编解码器选择机制
- `chooseCodec(requestedSize, startIndex)`: 在嵌入编解码器列表中查找匹配请求尺寸的编解码器
- `onGetScaledDimensions(desiredScale)`: 根据目标缩放比例选择最接近面积的嵌入图像
- 如果某个编解码器解码失败，会继续尝试列表中的下一个匹配编解码器

### 解码委托模式
所有实际的像素解码操作都委托给 `fCurrCodec` 或匹配的嵌入编解码器：
- `onGetPixels`: 遍历匹配的编解码器直到成功解码
- `onStartScanlineDecode` / `onGetScanlines` / `onSkipScanlines`: 委托给 `fCurrCodec`
- `onStartIncrementalDecode` / `onIncrementalDecode`: 委托给 `fCurrCodec`
- `getSampler`: 委托给 `fCurrCodec`

### 内存管理
- ICO 数据被完全加载到内存中（通过 `SkData`）
- 如果流已有内存基地址（`getMemoryBase`），则使用零拷贝方式；否则复制整个流
- `fCurrCodec` 是非所有权指针，由 `fEmbeddedCodecs` 管理生命周期

### 颜色转换
- `conversionSupported` 始终返回 `true`，实际检查由嵌入编解码器执行
- `usesColorXform` 返回 `false`，颜色变换由嵌入编解码器处理

## 依赖关系

- `SkCodec`: 基类
- `SkPngDecoder`: 用于检测和解码嵌入的 PNG 图像
- `SkBmpCodec`: 用于解码嵌入的 BMP 图像（通过 `MakeFromIco` 专用接口）
- `SkData` / `SkStream`: 数据流管理
- `SkTSort` / `SkTArray`: 排序和动态数组
- `SkCodecPriv`: 编解码器私有工具函数（如 `UnsafeGetShort`、`UnsafeGetInt`）

## 设计模式与设计决策

### 组合模式（Composite Pattern）
ICO 编解码器不直接解码像素，而是作为多个子编解码器的容器和调度器。这是组合模式的经典应用。

### 容错机制
- 无效的嵌入图像会被跳过，不会导致整个 ICO 解码失败
- 解码失败时会继续尝试其他匹配尺寸的嵌入图像
- 目录条目按偏移量排序以处理非标准的存储顺序

### 不支持子集解码
`onGetPixels` 中明确检查 `opts.fSubset`，子集解码返回 `kUnimplemented`。

## 性能考量

- 整个 ICO 文件在创建编解码器时即被加载到内存中，避免了后续的流操作开销
- 嵌入图像数据通过 `SkData::MakeSubset` 共享底层内存，避免不必要的拷贝
- 目录条目排序确保了线性扫描流数据，减少了随机访问
- 对于大量嵌入图像的 ICO 文件，`chooseCodec` 使用简单的线性搜索，但 ICO 文件通常只包含少量图像，因此不会成为瓶颈

## 相关文件

- `include/codec/SkIcoDecoder.h`: 公共 ICO 解码器接口
- `src/codec/SkBmpCodec.h` / `src/codec/SkBmpCodec.cpp`: BMP 子编解码器
- `include/codec/SkPngDecoder.h`: PNG 子编解码器接口
- `src/codec/SkCodecPriv.h`: 编解码器私有工具函数
- `include/codec/SkCodec.h`: 编解码器基类定义
