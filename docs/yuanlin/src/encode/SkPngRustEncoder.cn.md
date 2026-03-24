# SkPngRustEncoder

> 源文件
> - include/encode/SkPngRustEncoder.h
> - src/encode/SkPngRustEncoder.cpp

## 概述

`SkPngRustEncoder` 是 Skia 的 PNG 编码器,基于 Rust 实现(通过 FFI 调用 Rust 的 `png` crate)。该编码器提供了将像素数据编码为 PNG 格式的功能,支持压缩级别控制、文本注释(tEXt 块)、增量编码等特性。与传统的 C/C++ PNG 编码器相比,Rust 实现提供了更好的内存安全性和现代化的编码性能。

该编码器支持多种使用场景:一次性编码、增量编码、从 GPU 纹理编码等,适用于图像保存、截图、导出等功能。

## 架构位置

`SkPngRustEncoder` 位于 Skia 的编码模块中:

```
skia/
  include/encode/
    SkPngRustEncoder.h           # 公共接口
    SkEncoder.h                  # 编码器基类
  src/encode/
    SkPngRustEncoder.cpp         # 实现(转发到 Impl)
    SkPngRustEncoderImpl.h       # 真正的实现类
    SkPngRustEncoderImpl.cpp     # Rust FFI 调用
```

该编码器与 Skia 的图像和表面系统集成,可以直接编码 `SkPixmap`、`SkImage` 等对象。

## 主要类与结构体

### CompressionLevel 枚举

PNG 压缩级别枚举。

```cpp
enum class CompressionLevel : uint8_t {
    kLow,      // 低压缩 - 快速,文件较大
    kMedium,   // 中等压缩 - 平衡
    kHigh,     // 高压缩 - 慢速,文件较小
};
```

### Options 结构体

PNG 编码选项。

**成员变量:**

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `fCompressionLevel` | `CompressionLevel` | `kMedium` | 压缩级别 |
| `fComments` | `sk_sp<SkDataTable>` | `nullptr` | tEXt 注释块 |

**注释格式:**
- `fComments` 的偶数索引是关键字(keyword)
- 奇数索引是对应的文本内容
- 所有条目使用 Latin-1 编码(ISO-8859-1)
- 关键字长度最多 79 字符,不能包含非换行空格
- 文本可以包含任意 191 个 Latin-1 字符和换行符
- 尾部的 NUL 字符会被移除

## 公共 API 函数

### 一次性编码

```cpp
bool Encode(SkWStream* dst, const SkPixmap& src, const Options& options);
```
**功能:** 将像素数据编码为 PNG 并写入流
**参数:**
- `dst` - 输出流(必须有效,直到编码完成)
- `src` - 源像素数据
- `options` - 编码选项

**返回:** 成功返回 `true`,失败返回 `false`
**失败原因:**
- 源像素格式不支持
- 注释格式不符合 PNG 规范
- 流写入失败

```cpp
sk_sp<SkData> Encode(const SkPixmap& src, const Options& options);
```
**功能:** 将像素数据编码为 PNG 并返回数据块
**返回:** 编码后的 PNG 数据,失败返回 `nullptr`
**优势:** 自动管理内存,适合一次性编码

### 从图像编码

```cpp
sk_sp<SkData> Encode(GrDirectContext* ctx,
                     const SkImage* img,
                     const Options& options);
```
**功能:** 编码 `SkImage` 为 PNG 数据
**参数:**
- `ctx` - GPU 上下文(如果图像是 GPU 纹理则必须提供,光栅图像可为 `nullptr`)
- `img` - 要编码的图像
- `options` - 编码选项

**返回:** 编码后的 PNG 数据,失败返回 `nullptr`
**失败原因:**
- 图像无效
- 无法从 GPU 读取像素
- 编码失败

**使用场景:**
- 保存屏幕截图
- 导出渲染结果
- 图像格式转换

### 增量编码

```cpp
std::unique_ptr<SkEncoder> Make(SkWStream* dst,
                                const SkPixmap& src,
                                const Options& options);
```
**功能:** 创建 PNG 编码器,支持增量编码
**参数:**
- `dst` - 输出流(必须在编码器生命周期内保持有效)
- `src` - 源像素数据(仅用于初始化,不持有引用)
- `options` - 编码选项

**返回:** 编码器实例,失败返回 `nullptr`
**用途:**
- 逐行编码(调用 `encodeRows()`)
- 控制编码进度
- 减少内存峰值

**使用示例:**
```cpp
std::unique_ptr<SkEncoder> encoder = SkPngRustEncoder::Make(stream, pixmap, options);
if (encoder) {
    // 逐行编码
    for (int i = 0; i < pixmap.height(); i++) {
        if (!encoder->encodeRows(1)) {
            // 处理错误
            break;
        }
    }
}
```

## 内部实现细节

### 转发到实现类

公共 API 函数都转发到 `SkPngRustEncoderImpl`:

```cpp
bool Encode(SkWStream* dst, const SkPixmap& src, const Options& options) {
    std::unique_ptr<SkEncoder> encoder = Make(dst, src, options);
    return encoder && encoder->encodeRows(src.height());
}

sk_sp<SkData> Encode(const SkPixmap& src, const Options& options) {
    SkDynamicMemoryWStream stream;
    if (!Encode(&stream, src, options)) {
        return nullptr;
    }
    return stream.detachAsData();
}
```

### 图像编码流程

从 `SkImage` 编码的步骤:

1. **验证图像有效性** - 检查 `img` 非空
2. **读取像素到 SkBitmap** - 调用 `as_IB(img)->getROPixels(ctx, &bm)`
   - 如果是 GPU 图像,需要提供上下文以从 GPU 读取
   - 如果是光栅图像,直接访问像素
3. **编码位图** - 调用 `Encode(bm.pixmap(), options)`

```cpp
sk_sp<SkData> Encode(GrDirectContext* ctx, const SkImage* img, const Options& options) {
    if (!img) {
        return nullptr;
    }
    SkBitmap bm;
    if (!as_IB(img)->getROPixels(ctx, &bm)) {
        return nullptr;
    }
    return Encode(bm.pixmap(), options);
}
```

### SkDynamicMemoryWStream 使用

用于将编码输出收集到内存:

```cpp
SkDynamicMemoryWStream stream;
if (!Encode(&stream, src, options)) {
    return nullptr;
}
return stream.detachAsData();
```

**特点:**
- 动态增长的内存流
- `detachAsData()` 将内存所有权转移到 `SkData`
- 避免额外的内存复制

### Rust FFI 边界

实际的 PNG 编码由 Rust 代码执行,通过 FFI 调用:

- `SkPngRustEncoderImpl` 封装 FFI 调用
- 处理 C++ 到 Rust 的数据转换
- 管理 Rust 对象的生命周期

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkDataTable.h` | 存储注释数据 |
| `include/core/SkRefCnt.h` | 引用计数智能指针 |
| `include/core/SkPixmap.h` | 像素数据访问 |
| `include/core/SkImage.h` | 图像抽象 |
| `include/core/SkBitmap.h` | 位图容器 |
| `include/core/SkStream.h` | 流接口 |
| `include/encode/SkEncoder.h` | 编码器基类 |
| `src/encode/SkPngRustEncoderImpl.h` | Rust 实现类 |
| `src/image/SkImage_Base.h` | 图像内部接口 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| 图像保存 API | 调用编码器保存图像 |
| 截图功能 | 将屏幕内容编码为 PNG |
| 图像导出 | 格式转换和导出 |
| 测试工具 | 生成测试图像 |

## 设计模式与设计决策

### 设计模式

1. **外观模式 (Facade Pattern)**
   - 公共 API 隐藏 Rust FFI 复杂性
   - 提供简洁的 C++ 接口

2. **工厂模式 (Factory Pattern)**
   - `Make()` 函数创建编码器实例
   - 封装实现类的创建细节

3. **策略模式 (Strategy Pattern)**
   - `Options` 封装编码策略
   - 压缩级别和注释是可配置的策略

4. **适配器模式 (Adapter Pattern)**
   - 适配 Rust `png` crate 到 Skia 接口
   - 转换数据类型和错误处理

### 设计决策

1. **Rust 实现选择**
   - 利用 Rust 的内存安全性
   - 使用成熟的 `png` crate
   - 避免 C/C++ 的安全问题

2. **多种编码接口**
   - 一次性编码:简单场景
   - 增量编码:大图像,控制内存
   - 从图像编码:高层便捷接口

3. **流式输出**
   - 使用 `SkWStream` 而非固定缓冲区
   - 支持文件流、内存流、网络流
   - 灵活的输出目标

4. **GPU 图像支持**
   - 提供 `GrDirectContext` 参数
   - 自动处理 GPU 到 CPU 的像素传输
   - 统一光栅和 GPU 图像编码

5. **注释格式限制**
   - 遵循 PNG 规范的 tEXt 块要求
   - 编码时验证关键字和文本
   - 编码失败时提供明确错误

6. **压缩级别抽象**
   - 不暴露底层压缩参数(如 zlib 级别)
   - 提供高层语义(低/中/高)
   - 简化客户端选择

## 性能考量

1. **压缩级别权衡**
   - `kLow`:速度优先,文件大 10-20%
   - `kMedium`:平衡选择
   - `kHigh`:文件小 5-10%,速度慢 2-3 倍

2. **增量编码优势**
   - 逐行编码减少内存峰值
   - 适合大图像(如 8K 分辨率)
   - 可与进度条配合

3. **内存流开销**
   - `SkDynamicMemoryWStream` 动态增长
   - 最终大小接近文件大小
   - 避免使用时考虑直接写文件

4. **GPU 图像开销**
   - 从 GPU 读取像素有延迟
   - 可能触发同步等待
   - 考虑异步读取优化

5. **Rust 边界开销**
   - FFI 调用有轻微开销
   - 数据复制在边界发生
   - 逐行编码减少单次传输量

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/encode/SkPngRustEncoder.h` | 公共接口 |
| `src/encode/SkPngRustEncoder.cpp` | 实现(转发) |
| `src/encode/SkPngRustEncoderImpl.h` | Rust 实现类 |
| `src/encode/SkPngRustEncoderImpl.cpp` | Rust FFI 调用 |
| `include/encode/SkEncoder.h` | 编码器基类 |
| `include/core/SkPixmap.h` | 像素数据接口 |
| `include/core/SkImage.h` | 图像抽象 |
| `include/core/SkStream.h` | 流接口 |

## 与传统 PNG 编码器的比较

| 特性 | SkPngRustEncoder | 传统编码器(libpng) |
|------|------------------|---------------------|
| 实现语言 | Rust | C |
| 内存安全 | 编译期保证 | 运行时检查 |
| 性能 | 相当或更好 | 成熟优化 |
| 代码大小 | 稍大(包含 Rust 运行时) | 较小 |
| 维护性 | 现代 Rust 生态 | 老旧 C 代码 |
| 功能 | 基础功能 | 全功能支持 |

## 未来扩展计划

根据头文件注释,未来可能支持:

1. **颜色配置文件** - iCCP 块支持
2. **更多元数据** - 如作者、时间戳
3. **动画 PNG** - APNG 格式支持
4. **更多压缩选项** - 如滤波器选择

## 使用示例

### 基本编码

```cpp
SkDynamicMemoryWStream stream;
SkPngRustEncoder::Options options;
options.fCompressionLevel = SkPngRustEncoder::CompressionLevel::kHigh;

if (SkPngRustEncoder::Encode(&stream, pixmap, options)) {
    sk_sp<SkData> data = stream.detachAsData();
    // 保存 data 到文件
}
```

### 添加注释

```cpp
SkString keywords[] = {"Author", "Description"};
SkString values[] = {"Skia", "Test image"};
sk_sp<SkDataTable> comments = SkDataTable::MakeArrayProc(
    keywords, values, 2, [](void*) {});

SkPngRustEncoder::Options options;
options.fComments = comments;

sk_sp<SkData> data = SkPngRustEncoder::Encode(pixmap, options);
```

### 编码 GPU 图像

```cpp
sk_sp<SkImage> gpuImage = surface->makeImageSnapshot();
sk_sp<SkData> data = SkPngRustEncoder::Encode(
    context, gpuImage.get(), options);
```
