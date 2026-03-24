# JpegDecoderMgr - JPEG 解码管理器

> 源文件: `src/codec/SkJpegDecoderMgr.h`, `src/codec/SkJpegDecoderMgr.cpp`

## 概述

`JpegDecoderMgr` 是 Skia JPEG 编解码模块中管理 libjpeg 解压缩基础设施的核心类。它封装了 libjpeg 的 `jpeg_decompress_struct`（解压缩信息结构体）、错误管理器和数据源管理器，提供了初始化、错误处理和颜色空间检测功能。该类桥接了 Skia 的流接口与 libjpeg 的数据源接口。

## 架构位置

```
SkJpegCodec
  └── JpegDecoderMgr (解码管理器)
        ├── jpeg_decompress_struct (libjpeg 解压缩结构)
        ├── SourceMgr : jpeg_source_mgr (libjpeg 源管理器适配)
        │     └── SkJpegSourceMgr (Skia 源管理器)
        ├── skjpeg_error_mgr (错误管理器)
        └── jpeg_progress_mgr (进度管理器)
```

## 主要类与结构体

### `JpegDecoderMgr`
- 不可拷贝（继承 `SkNoncopyable`）
- 持有 libjpeg 核心结构体和适配器
- 管理 libjpeg 的生命周期（创建/销毁）

### `JpegDecoderMgr::SourceMgr` (私有内部类)
- 继承自 `jpeg_source_mgr`（libjpeg 的源管理器接口）
- 包含一个 `std::unique_ptr<SkJpegSourceMgr>`
- 将 libjpeg 的静态回调函数路由到 `SkJpegSourceMgr` 的方法

## 公共 API 函数

### 错误处理
- `returnFalse(const char caller[])`: 打印错误消息并返回 false
- `returnFailure(const char caller[], SkCodec::Result)`: 打印错误消息并返回失败结果

### 初始化
- `JpegDecoderMgr(SkStream* stream)`: 创建管理器，设置错误处理器（不获取流的所有权）
- `init()`: 初始化 libjpeg 解压缩结构，设置源管理器、输出消息函数和进度监视器

### 查询
- `getEncodedColor(SkEncodedInfo::Color*)`: 从 libjpeg 的颜色空间映射到 Skia 的编码颜色类型
- `errorMgr()`: 获取错误管理器（用于设置 setjmp 缓冲区）
- `dinfo()`: 获取解压缩信息结构体
- `getSourceMgr()`: 获取底层的 `SkJpegSourceMgr`

## 内部实现细节

### 错误处理机制
- 使用 `jpeg_std_error` 设置默认错误处理
- 将 `error_exit` 替换为 `skjpeg_err_exit`（使用 longjmp 跳转）
- `output_message` 被替换为调试打印函数

### 进度监视器
```cpp
static void progress_monitor(j_common_ptr info) {
    int scan = ((j_decompress_ptr)info)->input_scan_number;
    if (scan >= 100) {
        skjpeg_err_exit(info);
    }
}
```
防止恶意构造的渐进式 JPEG（扫描次数过多）导致解码器挂起。阈值为 100 次扫描。

### 颜色空间映射 (`getEncodedColor`)
| libjpeg 颜色空间 | Skia 编码颜色 |
|---|---|
| JCS_GRAYSCALE | kGray_Color |
| JCS_YCbCr | kYUV_Color |
| JCS_RGB | kRGB_Color |
| JCS_YCCK | kYCCK_Color |
| JCS_CMYK | kInvertedCMYK_Color |

### SourceMgr 适配器
四个静态回调函数将 libjpeg 的调用转发给 `SkJpegSourceMgr`：
- `InitSource`: 调用 `fSourceMgr->initSource`
- `FillInputBuffer`: 调用 `fSourceMgr->fillInputBuffer`
- `SkipInputData`: 调用 `fSourceMgr->skipInputBytes`
- `TermSource`: 空操作
- `resync_to_restart`: 使用 libjpeg 默认实现

### 生命周期管理
- 构造时仅设置错误管理器（libjpeg 要求在任何调用前设置）
- `init()` 创建解压缩结构并注册所有回调
- 析构时调用 `jpeg_destroy_decompress`（仅在 `fInit` 为 true 时）

## 依赖关系

- libjpeg (`jpeglib.h`): JPEG 解码库
- `SkJpegSourceMgr`: Skia JPEG 源管理器
- `SkJpegPriv` / `SkJpegUtility`: JPEG 私有工具（`skjpeg_error_mgr`、`skjpeg_err_exit`）
- `SkNoncopyable`: 禁止拷贝
- `SkEncodedInfo`: 编码信息
- `SkCodec::Result`: 解码结果类型

## 设计模式与设计决策

### 适配器模式
`SourceMgr` 将 `SkJpegSourceMgr` 适配为 libjpeg 的 `jpeg_source_mgr` 接口。通过 C 风格的静态函数回调桥接 C 和 C++ 代码。

### 两阶段初始化
构造和 `init()` 分离，允许在两阶段之间设置 setjmp 缓冲区（libjpeg 的错误处理要求）。

### 防御性安全
- 渐进式 JPEG 扫描次数限制（100 次）防止拒绝服务攻击
- Android 框架的 SafetyNet 日志用于跟踪特定颜色空间问题

## 性能考量

- libjpeg 结构体直接作为成员变量存储，避免额外的堆分配
- 源管理器在构造时创建，避免解码过程中的初始化开销
- 进度监视器的开销极小（仅比较整数值）

## 相关文件

- `src/codec/SkJpegCodec.h` / `.cpp`: 使用此管理器的 JPEG 编解码器
- `src/codec/SkJpegSourceMgr.h` / `.cpp`: Skia JPEG 源管理器
- `src/codec/SkJpegPriv.h`: JPEG 私有类型定义
- `src/codec/SkJpegUtility.h`: JPEG 工具函数
