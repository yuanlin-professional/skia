# SkEncoder

> 源文件
> - include/encode/SkEncoder.h
> - src/encode/SkEncoder.cpp

## 概述

`SkEncoder` 是 Skia 图形库中用于图像编码的抽象基类,提供了逐行编码图像数据的基础架构。该类采用不可拷贝的设计模式,为具体的编码器实现(如 PNG、JPEG、WebP 编码器)提供了统一的接口。编码器支持单帧和多帧动画图像的编码,通过逐行处理的方式实现内存高效的图像数据编码。

`SkEncoder` 的核心设计围绕渐进式编码展开,允许调用者按需编码指定数量的行,而不是一次性编码整个图像。这种设计在处理大图像时可以显著降低内存压力,同时为流式编码场景提供了灵活性。

## 架构位置

`SkEncoder` 位于 Skia 编码模块的核心层,作为所有图像编码器的抽象基类:

- 位于 `include/encode/` 公共接口目录
- 为编码子系统提供统一的抽象层
- 被 `SkPngEncoder`、`SkJpegEncoder`、`SkWebpEncoder` 等具体编码器继承
- 与 `SkPixmap` 紧密协作,处理原始像素数据
- 作为编码管道的起点,连接图像数据源和编码输出

## 主要类与结构体

### SkEncoder

**继承关系:**
- 基类:`SkNoncopyable`(不可拷贝)
- 派生类:各种具体编码器实现(如 `SkPngEncoder`、`SkJpegEncoder`)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSrc` | `const SkPixmap&` | 源像素数据的引用,包含图像信息和像素缓冲区 |
| `fCurrRow` | `int` | 当前编码进度,记录下一行待编码的行号 |
| `fStorage` | `skia_private::AutoTMalloc<uint8_t>` | 编码过程中的临时存储缓冲区,大小在构造时指定 |

### SkEncoder::Frame

动画帧结构体,用于描述动画图像中的单个帧:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `pixmap` | `SkPixmap` | 帧的像素数据 |
| `duration` | `int` | 帧的显示时长,单位为毫秒 |

## 公共 API 函数

### encodeRows

```cpp
bool encodeRows(int numRows);
```

编码指定数量的输入行。该函数执行以下验证和逻辑:

- **参数验证:**确保 `numRows > 0` 且当前行未超出图像高度
- **边界调整:**如果请求的行数超过剩余行数,自动调整为剩余行数
- **状态管理:**成功编码后更新 `fCurrRow`,失败时将其设置为图像高度以短路后续调用
- **返回值:**成功返回 `true`,失败或参数无效返回 `false`

该函数是编码器的主要公共接口,内部委托给纯虚函数 `onEncodeRows` 进行实际编码。

### 静态工厂方法

注意:各具体编码器通常提供自己的静态工厂方法(如 `SkPngEncoder::Make`)来创建编码器实例。

## 内部实现细节

### 编码流程

1. **初始化:**构造函数接收源 `SkPixmap` 和存储缓冲区大小,初始化 `fCurrRow` 为 0
2. **逐行编码:**调用者重复调用 `encodeRows` 直到所有行都被编码
3. **委托模式:**`encodeRows` 验证参数后调用纯虚函数 `onEncodeRows`
4. **错误处理:**编码失败时,将 `fCurrRow` 设置为最大值,防止后续调用

### 纯虚函数

```cpp
virtual bool onEncodeRows(int numRows) = 0;
```

这是子类必须实现的核心编码逻辑。子类需要:
- 从 `fSrc` 读取当前行开始的 `numRows` 行数据
- 执行格式特定的编码操作
- 更新 `fCurrRow` 计数器
- 使用 `fStorage` 作为临时缓冲区

### 存储管理

`fStorage` 使用 `AutoTMalloc` 进行自动内存管理,在构造时分配,析构时自动释放。存储大小由子类根据编码需求确定,通常用于:
- 行缓冲区(row buffer)
- 压缩中间数据
- 格式转换临时空间

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkPixmap` | 提供源图像像素数据和元信息 |
| `SkNoncopyable` | 提供不可拷贝基类 |
| `AutoTMalloc` | 提供自动内存管理 |
| `SkAssert` | 提供调试断言功能 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkPngEncoder` | PNG 格式编码器实现 |
| `SkJpegEncoder` | JPEG 格式编码器实现 |
| `SkWebpEncoder` | WebP 格式编码器实现 |
| 编码工具类 | 各种使用编码器的高层工具 |

## 设计模式与设计决策

### 模板方法模式(Template Method)

`SkEncoder` 使用模板方法模式定义编码算法的骨架:
- `encodeRows` 作为模板方法,定义验证、调用、错误处理的流程
- `onEncodeRows` 作为钩子方法,由子类实现具体编码逻辑
- 这种设计确保所有编码器都遵循统一的错误处理和状态管理

### 不可拷贝设计

继承自 `SkNoncopyable`,因为:
- 编码器持有状态(当前行、存储缓冲区)
- 拷贝编码器可能导致资源管理问题
- 编码过程通常是一次性的,不需要拷贝

### 引用语义

使用 `const SkPixmap&` 引用源数据而非拷贝:
- 避免大块像素数据的拷贝
- 源数据生命周期由调用者管理
- 要求调用者确保编码期间数据有效

### 渐进式编码

支持逐行编码而非一次性编码:
- 降低内存峰值使用
- 支持流式编码场景
- 允许进度报告和取消操作

## 性能考量

### 内存效率

- **逐行处理:**避免同时持有完整的解码和编码数据
- **共享存储:**`fStorage` 可在多行之间复用
- **零拷贝设计:**直接引用源 `SkPixmap`,无需额外拷贝

### 编码效率

- **批量编码:**允许一次编码多行,减少函数调用开销
- **提前终止:**错误时短路后续调用,避免无效操作
- **边界检查优化:**只在公共接口进行检查,`onEncodeRows` 可以假设参数有效

### 缓存友好性

- 逐行处理符合行主序存储的访问模式
- 连续内存访问提高缓存命中率

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/encode/SkEncoder.h` | 公共接口头文件 |
| `src/encode/SkEncoder.cpp` | 基类实现文件 |
| `include/core/SkPixmap.h` | 像素数据容器 |
| `include/encode/SkPngEncoder.h` | PNG 编码器 |
| `include/encode/SkJpegEncoder.h` | JPEG 编码器 |
| `include/encode/SkWebpEncoder.h` | WebP 编码器 |
| `include/private/base/SkNoncopyable.h` | 不可拷贝基类 |
| `include/private/base/SkTemplates.h` | 模板工具(AutoTMalloc) |
