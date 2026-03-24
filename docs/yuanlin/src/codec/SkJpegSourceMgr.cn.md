# SkJpegSourceMgr - JPEG 数据源管理器

> 源文件: `src/codec/SkJpegSourceMgr.h`, `src/codec/SkJpegSourceMgr.cpp`

## 概述

`SkJpegSourceMgr` 是一个抽象接口，用于将 Skia 的 `SkStream` 适配到 libjpeg 的 `jpeg_source_mgr` 接口。由于不同类型的 `SkStream`（内存映射流、可寻址流、不可寻址流）有不同的能力，该类提供了三种具体实现来最优化地处理每种情况。除了 libjpeg 数据馈送功能外，当启用增益图解码时，它还提供 JPEG 段扫描和数据子集提取功能。

## 架构位置

```
SkJpegSourceMgr (抽象基类)
  ├── SkJpegMemorySourceMgr (内存映射流)
  ├── SkJpegBufferedSourceMgr (可寻址缓冲流)
  └── SkJpegUnseekableSourceMgr (不可寻址流, 条件编译)
```

该类由 `JpegDecoderMgr` 通过其内部 `SourceMgr` 包装器使用，桥接 Skia 流与 libjpeg。

## 主要类与结构体

### `SkJpegSourceMgr` (抽象基类)
- 持有对 `SkStream` 的非所有权引用
- 定义 libjpeg 数据馈送接口
- 条件编译的段扫描和数据提取接口

### `SkJpegMemorySourceMgr` (内存映射实现)
- 适用于 `getMemoryBase()` 非空的流
- 零拷贝访问，直接指向内存基地址
- 段参数和子集数据均使用 `MakeWithoutCopy`

### `SkJpegBufferedSourceMgr` (缓冲实现)
- 适用于可寻址但非内存映射的流
- 使用固定大小的缓冲区读取数据
- 使用 `ScopedSkStreamRestorer` RAII 类保存/恢复流位置

### `SkJpegUnseekableSourceMgr` (不可寻址实现)
- 条件编译，仅在 `SK_CODEC_DECODES_JPEG_GAINMAPS` 启用时存在
- 适用于不支持寻址和回退的流
- 在数据馈送给 libjpeg 的同时进行段扫描
- 维护读取偏移追踪用于子集提取

### `ScopedSkStreamRestorer` (RAII 辅助类)
- 构造时回退流到起始位置
- 析构时恢复流到原始位置
- 用于缓冲源管理器的段扫描和数据提取

## 公共 API 函数

### 工厂方法
- `static Make(SkStream*, size_t bufferSize = 1024)`: 根据流的能力自动选择最佳实现：
  - 不可寻址流 -> `SkJpegUnseekableSourceMgr`
  - 内存映射流 -> `SkJpegMemorySourceMgr`
  - 其他 -> `SkJpegBufferedSourceMgr`

### libjpeg 接口
- `initSource(...)`: 初始化数据源
- `fillInputBuffer(...)`: 填充输入缓冲区
- `skipInputBytes(...)`: 跳过指定字节数

### 增益图接口（条件编译）
- `getAllSegments()`: 扫描并返回所有 JPEG 段
- `getSubsetData(size_t offset, size_t size, bool* wasCopied)`: 提取指定偏移和大小的数据子集
- `getSegmentParameters(const SkJpegSegment&)`: 获取指定段的参数数据

## 内部实现细节

### 内存映射源 (SkJpegMemorySourceMgr)
- `initSource`: 直接指向 `getMemoryBase()`，长度为 `getLength()`
- `fillInputBuffer`: 总是返回错误（不应被调用，因为数据已全部在内存中）
- `getSubsetData`: 使用 `MakeWithoutCopy` 零拷贝返回
- `getSegmentParameters`: 直接计算偏移量访问内存

### 缓冲源 (SkJpegBufferedSourceMgr)
- 使用 `SkData::MakeUninitialized(bufferSize)` 作为缓冲区
- `fillInputBuffer`: 从流中读取一个缓冲区大小的数据
- `skipInputBytes`: 先消耗缓冲区中的数据，再跳过流中的剩余字节
- `getAllSegments`: 使用 `ScopedSkStreamRestorer` 回退流并逐块扫描
- `getSubsetData`: 寻址到偏移位置并读取数据（总是拷贝）

### 不可寻址源 (SkJpegUnseekableSourceMgr)
- 在构造时立即创建段扫描器
- `readToBufferAndScan`: 读取数据到缓冲区并同时馈送给扫描器
- `getSubsetData`: 复杂的逻辑处理缓冲区与流之间的数据边界
  - 处理部分数据仍在缓冲区的情况
  - 追踪 `fLastReadOffset` 和 `fLastReadSize` 确定数据位置
  - 不支持请求已被消耗的数据（返回 nullptr）

### 段扫描器
所有实现都使用 `SkJpegSegmentScanner` 进行懒加载式段扫描，扫描到 EndOfImage 标记为止。

## 依赖关系

- `SkStream`: Skia 流接口
- `SkJpegSegmentScanner`: JPEG 段扫描器
- `SkJpegSegment`: JPEG 段信息结构
- `SkData`: 数据管理
- `SkJpegConstants`: JPEG 常量（标记码大小、段参数长度等）
- `SkCodecPriv`: 调试输出

## 设计模式与设计决策

### 策略模式
工厂方法根据流能力选择最优实现，对调用者透明。

### RAII 资源管理
`ScopedSkStreamRestorer` 确保流位置在段扫描或数据提取后被正确恢复。

### 渐进式扫描
不可寻址源在正常的 libjpeg 解码过程中同步进行段扫描，避免额外的数据传递。

### 条件编译
增益图相关功能通过 `SK_CODEC_DECODES_JPEG_GAINMAPS` 条件编译，在不需要时减小代码大小。

## 性能考量

- 内存映射源完全零拷贝，是最高效的路径
- 缓冲源使用固定大小缓冲区（默认 1024 字节），平衡内存使用和系统调用频率
- 不可寻址源避免了双重传递数据（扫描和解码同步进行）
- 子集数据在内存映射源中使用零拷贝，在其他源中必须拷贝
- 段扫描器是懒创建的，仅在需要时初始化

## 相关文件

- `src/codec/SkJpegDecoderMgr.h` / `.cpp`: 使用此源管理器的解码管理器
- `src/codec/SkJpegSegmentScan.h`: JPEG 段扫描器
- `src/codec/SkJpegConstants.h`: JPEG 格式常量
- `include/core/SkStream.h`: Skia 流接口
