# SkSVGCanvas

> 源文件: include/svg/SkSVGCanvas.h, src/svg/SkSVGCanvas.cpp

## 概述

SkSVGCanvas 是 Skia 中用于生成 SVG (可缩放矢量图形) 输出的工厂类。它提供了将 Skia 绘图命令转换为 SVG 格式的能力,允许将 2D 图形以矢量格式导出。该类通过创建一个特殊的 SkCanvas 实例,将所有绘图操作序列化为 SVG 命令并输出到流中。

主要功能:
- 创建能够生成 SVG 输出的 Canvas 实例
- 支持多种 SVG 输出选项配置
- 处理文本转换和路径编码
- 支持 PNG 图像编码嵌入
- 提供 XML 格式控制

## 架构位置

SkSVGCanvas 位于 Skia 的 SVG 模块中,是 SVG 输出功能的入口点:

```
Skia Graphics Library
├── Core (SkCanvas, SkWStream)
├── SVG Module
│   ├── SkSVGCanvas (工厂类) ← 当前模块
│   ├── SkSVGDevice (设备实现)
│   └── XML Writer (XML 序列化)
└── Encode (PNG 编码器)
```

该类作为用户代码与底层 SVG 设备实现之间的接口,封装了创建 SVG 渲染管道的复杂性。

## 主要类与结构体

### SkSVGCanvas

**类型**: 工厂类

**继承关系**:
- 无继承,独立的工厂类

**关键成员变量**:

| 成员类型 | 名称 | 说明 |
|---------|------|------|
| enum | Flags | SVG 输出标志 |
| typedef | EncodePngCallback | PNG 编码回调函数类型 |
| struct | Options | SVG 生成选项配置 |

### Flags 枚举

| 标志 | 值 | 说明 |
|-----|---|------|
| kConvertTextToPaths_Flag | 0x01 | 将文本转换为路径元素 |
| kNoPrettyXML_Flag | 0x02 | 禁用 XML 格式化(无换行和制表符) |
| kRelativePathEncoding_Flag | 0x04 | 使用相对路径命令编码 |

### Options 结构体

**关键成员**:

| 成员类型 | 名称 | 默认值 | 说明 |
|---------|------|-------|------|
| Flags | flags | 0x00 | 输出标志组合 |
| EncodePngCallback | pngEncoder | nullptr | PNG 编码函数指针 |

## 公共 API 函数

### Make (新版本)

```cpp
static std::unique_ptr<SkCanvas> Make(
    const SkRect& bounds,
    SkWStream* writer,
    Options opts
);
```

**功能**: 创建用于生成 SVG 的 Canvas 实例。

**参数**:
- `bounds`: SVG 视口边界(对应 viewBox 属性)
- `writer`: 输出流指针(不转移所有权)
- `opts`: SVG 生成选项

**返回值**:
- 成功返回 SkCanvas 智能指针
- 失败返回 nullptr

**特性**:
- 输出流必须在 Canvas 生命周期内保持有效
- Canvas 可能缓冲绘图命令,销毁后才保证输出完整
- 支持自定义 PNG 编码器或使用默认实现

### Make (旧版本)

```cpp
static std::unique_ptr<SkCanvas> Make(
    const SkRect& bounds,
    SkWStream* stream,
    uint32_t flags = 0
);
```

**功能**: 使用 flags 参数创建 SVG Canvas(遗留接口)。

**可用性**: 仅在未定义 `SK_DISABLE_LEGACY_SVG_FACTORIES` 时可用。

## 内部实现细节

### 创建流程

1. **参数验证与配置**: 检查 Options,设置默认 PNG 编码器
2. **尺寸计算**: 将浮点边界向外取整为整数尺寸
3. **XML 标志转换**: 根据 kNoPrettyXML_Flag 设置 XML 格式化标志
4. **设备创建**: 创建 SkSVGDevice 实例,传入尺寸和 XML 写入器
5. **Canvas 封装**: 将设备封装为 SkCanvas 返回

### PNG 编码器处理

默认编码器选择逻辑:

```cpp
if (!opts.pngEncoder) {
    opts.pngEncoder = [](SkWStream* dst, const SkPixmap& src) {
#if defined(SK_CODEC_ENCODES_PNG_WITH_RUST)
        return SkPngRustEncoder::Encode(dst, src, {});
#else
        return SkPngEncoder::Encode(dst, src, {});
#endif
    };
}
```

- 遗留模式下自动选择 Rust 或 libpng 编码器
- 新模式下要求用户提供编码器(否则中止程序)

### XML 格式化

通过 SkXMLStreamWriter 控制输出格式:
- `kNoPrettyXML_Flag` 设置时: 生成紧凑的单行 XML
- 未设置时: 生成带缩进和换行的可读 XML

### 坐标空间转换

bounds 参数定义 SVG 根元素的 viewBox:
- 使用 `roundOut()` 将浮点矩形扩展为覆盖的最小整数矩形
- 该尺寸传递给 SkSVGDevice 作为设备尺寸
- 视口映射在 SkSVGDevice 中处理

## 依赖关系

### 依赖的模块

| 模块 | 类型 | 说明 |
|-----|------|------|
| SkCanvas | 核心接口 | 返回的绘图上下文类型 |
| SkWStream | 核心输出 | 流式写入接口 |
| SkSVGDevice | 内部实现 | 实际的 SVG 渲染设备 |
| SkXMLStreamWriter | XML 序列化 | 处理 XML 标签输出 |
| SkPngEncoder | 编码器 | libpng 编码实现 |
| SkPngRustEncoder | 编码器 | Rust 编码实现 |
| SkRect | 核心几何 | 边界定义 |
| SkPixmap | 核心图像 | 像素数据访问 |

### 被依赖的模块

| 模块 | 使用场景 | 说明 |
|-----|---------|------|
| 用户应用代码 | SVG 导出 | 调用 Make 创建 SVG Canvas |
| 测试代码 | 单元测试 | 验证 SVG 输出正确性 |
| 文档生成工具 | 矢量输出 | 生成可缩放的图形文档 |

## 设计模式与设计决策

### 工厂模式

SkSVGCanvas 采用静态工厂方法模式:
- **优势**: 隐藏 SkSVGDevice 的复杂创建过程
- **意图**: 提供清晰的用户接口,避免暴露内部实现细节
- **实现**: 通过 `Make()` 静态方法返回抽象的 SkCanvas 接口

### 分离关注点

配置与实现分离:
- **Options 结构**: 集中管理所有配置选项
- **SkSVGDevice**: 专注于 SVG 生成逻辑
- **SkXMLStreamWriter**: 处理底层 XML 序列化

### 编码器抽象

EncodePngCallback 函数指针设计:
- **灵活性**: 允许用户自定义 PNG 编码策略
- **可测试性**: 可以注入 mock 编码器进行测试
- **兼容性**: 支持多种编码实现(Rust/libpng)

### 资源所有权

明确的所有权语义:
- **不转移**: SkWStream 指针不转移所有权,调用者负责生命周期管理
- **转移**: 返回的 `std::unique_ptr<SkCanvas>` 转移所有权给调用者
- **文档化**: 在注释中明确说明所有权规则

### 渐进式 API 升级

遗留 API 的处理策略:
- 保留旧的 `Make(bounds, stream, flags)` 接口向后兼容
- 通过编译宏 `SK_DISABLE_LEGACY_SVG_FACTORIES` 允许禁用
- 内部将旧接口转发到新接口实现
- 为平滑迁移提供过渡期

## 性能考量

### 流式输出

直接写入 SkWStream 避免内存累积:
- 大型 SVG 不会完全保存在内存中
- 适合生成大文件或网络流输出
- 注意 Canvas 可能缓冲部分命令,延迟输出

### 文本处理

kConvertTextToPaths_Flag 的性能权衡:
- **启用时**: 文本转换为路径,文件更大但保证跨平台一致性
- **禁用时**: 使用 SVG 文本元素,文件更小但依赖字体可用性

### XML 格式化开销

kNoPrettyXML_Flag 的影响:
- **紧凑模式**: 减少文件大小,加快写入速度
- **格式化模式**: 增加换行/缩进,便于人工调试但增加文件大小

### 路径编码优化

kRelativePathEncoding_Flag:
- 使用相对路径命令可能减小路径数据大小
- 对包含大量连续线段的路径效果明显
- 解析器实现复杂度略微增加

### 内存管理

智能指针使用避免内存泄漏:
- `std::unique_ptr` 自动管理 Canvas 生命周期
- SkSVGDevice 通过 `sk_sp` 引用计数管理
- 无需手动释放资源

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/svg/SkSVGCanvas.h | 公共 API 声明 |
| src/svg/SkSVGCanvas.cpp | 工厂实现代码 |
| src/svg/SkSVGDevice.h | SVG 设备类声明 |
| src/svg/SkSVGDevice.cpp | SVG 设备实现 |
| src/xml/SkXMLWriter.h | XML 写入器接口 |
| include/core/SkCanvas.h | Canvas 基类 |
| include/core/SkWStream.h | 输出流接口 |
| include/encode/SkPngEncoder.h | PNG 编码器(libpng) |
| include/encode/SkPngRustEncoder.h | PNG 编码器(Rust) |
