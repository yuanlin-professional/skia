# SkXmp - XMP 元数据解析

> 源文件: `src/codec/SkXmp.cpp`

## 概述

`SkXmp.cpp` 实现了 XMP（Extensible Metadata Platform）元数据的解析功能，专注于从 JPEG 图像中提取 HDR 增益图相关信息。XMP 是 Adobe 定义的元数据标准，使用 XML/RDF 格式嵌入在图像文件中。该文件支持解析三种增益图格式：Adobe HDR 增益图（hdrgm 命名空间）、Apple HDR 增益图（Apple pixeldatainfo + HDRGainMap 命名空间）以及 Google Container 容器目录（用于定位增益图在多图文件中的位置）。文件同时处理标准 XMP 和扩展 XMP 两个 DOM 树的管理。

## 架构位置

该文件位于 `src/codec/` 目录下，属于 Skia 图像解码子系统的元数据处理层。它依赖 Skia 的 XML DOM 解析器（`SkDOM`）来解析 XMP 的 XML 结构，并使用 `SkParse` 工具将字符串值转换为数值类型。解析出的增益图信息以 `SkGainmapInfo` 结构体返回给调用者。

## 主要类与结构体

### `SkXmpImpl`（匿名实现类）
继承自 `SkXmp` 的具体实现类：
- `fStandardDOM`: 标准 XMP DOM 树
- `fExtendedDOM`: 扩展 XMP DOM 树

**公共方法**:
- `getGainmapInfoAdobe(SkGainmapInfo*)`: 提取 Adobe HDR 增益图信息
- `getGainmapInfoApple(float exifHdrHeadroom, SkGainmapInfo*)`: 提取 Apple HDR 增益图信息
- `getContainerGainmapLocation(size_t* offset, size_t* size)`: 获取 Google Container 增益图位置
- `getExtendedXmpGuid()`: 获取扩展 XMP 的 GUID（MD5 哈希）
- `parseDom(sk_sp<SkData>, bool extended)`: 解析 XMP 数据到对应的 DOM

## 公共 API 函数

### `SkXmp::Make(sk_sp<SkData>)`
从单个 XMP 数据块创建 `SkXmp` 实例。

### `SkXmp::Make(sk_sp<SkData> standard, sk_sp<SkData> extended)`
从标准 XMP 和扩展 XMP 数据块创建实例。扩展 XMP 解析失败不影响标准 XMP 的使用。

## 内部实现细节

### XML 命名空间解析
XMP 使用 `xmlns:PREFIX="URI"` 语法声明命名空间。`find_uri_namespaces()` 函数通过以下层级搜索：
1. 根节点必须是 `x:xmpmeta`
2. 遍历 `rdf:RDF` 子节点
3. 遍历 `rdf:Description` 子节点
4. 在每层收集 `xmlns:` 属性，匹配请求的 URI
5. 当所有请求的 URI 都找到匹配时返回节点

### XMP 属性读取
属性值可以存在于两种位置：
- `get_attr()`: 先查找 XML 属性，再查找同名子元素的文本内容
- `get_typed_child()`: 支持 RDF 类型节点（`rdf:type` + `rdf:value`）
- `get_attr_float3_as_list()`: 解析 `rdf:Seq` > `rdf:li` 结构中的三元组浮点值

### Adobe 增益图解析（`getGainmapInfoAdobe`）
命名空间: `http://ns.adobe.com/hdr-gain-map/1.0/`
- 要求 `hdrgm:Version="1.0"`
- 默认参数: gainMapMin=0, gainMapMax=1, gamma=1, offsetSdr/Hdr=1/64, hdrCapacityMin=0, hdrCapacityMax=1
- 所有参数在 log2 域中定义，通过 `exp(x * log(2))` 转为线性域
- 支持 `BaseRenditionIsHDR` 标志

### Apple 增益图解析（`getGainmapInfoApple`）
命名空间: `http://ns.apple.com/pixeldatainfo/1.0/` + `http://ns.apple.com/HDRGainMap/1.0/`
- 验证 `AuxiliaryImageType` 为 `urn:com:apple:photo:2020:aux:hdrgainmap`
- 支持 `HDRGainMapHeadroom` XMP 参数覆盖 EXIF headroom
- 简单映射：gainmapRatioMax = hdrHeadroom, gamma = 1

### Google Container 位置解析（`getContainerGainmapLocation`）
命名空间: `http://ns.google.com/photos/1.0/container/` + `.../container/item/`
- 解析 `Container:Directory` > `rdf:Seq` > `rdf:li` 列表
- 第一项必须为 `Primary`（image/jpeg），可有 Padding
- 遍历后续项，累加 Length 直到找到 `Semantic="GainMap"` 的项
- 返回增益图相对于主图像末尾的偏移和大小

### 标准/扩展 XMP 搜索
`findUriNamespaces()` 按顺序搜索标准 DOM 和扩展 DOM。按 XMP Part 3 规范，应将两者合并为单一数据模型，但此实现保持两个独立树并顺序搜索。

## 依赖关系

- `include/private/SkXmp.h`: 公共接口
- `include/private/SkGainmapInfo.h`: 增益图信息结构
- `include/utils/SkParse.h`: 字符串到数值的转换工具
- `src/xml/SkDOM.h`: XML DOM 解析器
- `src/codec/SkCodecPriv.h`: 调试输出宏

## 设计模式与设计决策

1. **实现隐藏**: `SkXmpImpl` 在 .cpp 中定义，通过 `SkXmp::Make` 工厂函数创建，客户端只看到 `SkXmp` 接口。

2. **多格式支持**: 同一个 `SkXmp` 实例支持 Adobe、Apple 和 Google Container 三种增益图格式的查询。

3. **容错设计**: 扩展 XMP 解析失败不影响标准 XMP 的可用性。

4. **命名空间前缀独立**: 通过 URI 查找命名空间前缀，不依赖特定前缀名（如 `hdrgm:` 可以是任意前缀）。

5. **RDF 类型节点支持**: `get_typed_child` 支持 XMP 规范中的 RDF Typed Nodes（Section 7.9.2.5），提高兼容性。

## 性能考量

- **DOM 缓存**: XMP 数据仅在 `parseDom` 时解析一次，后续查询直接遍历 DOM
- **惰性扩展解析**: 扩展 XMP 只在标准 XMP 未找到目标时才被搜索
- **最小化解析**: 各查询方法只解析与请求相关的命名空间和属性

## 相关文件

- `include/private/SkXmp.h`: XMP 公共接口
- `include/private/SkGainmapInfo.h`: 增益图信息
- `src/xml/SkDOM.h`: XML DOM 解析
- `src/codec/SkJpegConstants.h`: XMP 标记和签名常量
- `src/codec/SkExif.cpp`: EXIF 解析（Apple HDR 需要 EXIF headroom）
