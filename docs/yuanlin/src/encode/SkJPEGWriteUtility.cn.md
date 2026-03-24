# SkJPEGWriteUtility — JPEG 编码写入工具

> 源文件：[src/encode/SkJPEGWriteUtility.h](../../src/encode/SkJPEGWriteUtility.h)、[src/encode/SkJPEGWriteUtility.cpp](../../src/encode/SkJPEGWriteUtility.cpp)

## 概述

`SkJPEGWriteUtility` 提供了 libjpeg/libjpeg-turbo 编码所需的目标管理器（destination manager）和错误处理函数。它将 Skia 的 `SkWStream` 适配为 libjpeg 的输出机制。

## 架构位置

```
SkJpegEncoderImpl
    └── SkJpegEncoderMgr
            ├── jpeg_compress_struct
            ├── skjpeg_error_mgr (错误处理)
            └── skjpeg_destination_mgr (输出适配) ← 本模块
                    └── SkWStream (Skia 输出流)
```

## 主要类与结构体

### `skjpeg_destination_mgr`

继承自 libjpeg 的 `jpeg_destination_mgr`，将 JPEG 压缩输出重定向到 `SkWStream`。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fStream` | `SkWStream* const` | 目标输出流（非拥有） |
| `fBuffer` | `uint8_t[1024]` | 1KB 输出缓冲区 |

构造时注册三个回调函数：
- `init_destination` → 初始化缓冲区指针
- `empty_output_buffer` → 缓冲区满时写入流
- `term_destination` → 编码结束时刷出剩余数据

## 公共 API 函数

### `skjpeg_error_exit(j_common_ptr cinfo)`

libjpeg 错误退出处理函数。输出错误消息，销毁 JPEG 对象，然后通过 `longjmp` 跳转回设置的恢复点。如果没有设置 `jmp_buf`，则调用 `SK_ABORT` 终止程序。

## 内部实现细节

### 缓冲写入机制

1. `init_destination`：将 `next_output_byte` 指向 `fBuffer`，`free_in_buffer` 设为 1024
2. `empty_output_buffer`：将整个 1024 字节缓冲区写入 `SkWStream`，重置指针。写入失败时通过 `ERREXIT` 触发 libjpeg 错误处理
3. `term_destination`：计算剩余数据量（`kBufferSize - free_in_buffer`），写入流并调用 `flush()`

### 错误处理

`skjpeg_error_exit` 使用 `skjpeg_error_mgr`（定义在 `SkJpegPriv.h`）中的 `fStack` 栈管理 `jmp_buf`。通过 `longjmp` 返回 -1 到最近的 `setjmp` 调用点。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| libjpeg-turbo (`jpeglib.h`) | JPEG 压缩框架 |
| `SkWStream` | Skia 写入流 |
| `SkJpegPriv` | `skjpeg_error_mgr` 定义 |

## 设计模式与设计决策

1. **适配器模式**：`skjpeg_destination_mgr` 将 libjpeg 的 C 回调接口适配到 `SkWStream` 的 C++ 对象接口。
2. **1KB 缓冲区**：平衡了内存使用和 I/O 效率，减少频繁的小写入操作。
3. **longjmp 错误恢复**：遵循 libjpeg 的错误处理约定，与 libjpeg 的 setjmp/longjmp 机制保持一致。

## 性能考量

- 1KB 缓冲区减少了流写入调用次数。libjpeg-turbo 内部也有缓冲，实际的小写入次数较少。
- 错误路径使用 longjmp 快速退出，避免逐层返回的开销。

## 相关文件

- `src/encode/SkJpegEncoderImpl.h` — JPEG 编码器实现
- `src/codec/SkJpegPriv.h` — `skjpeg_error_mgr` 定义
- `include/core/SkStream.h` — Skia 流接口
