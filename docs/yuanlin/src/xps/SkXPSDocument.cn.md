# SkXPSDocument - XPS 文档生成实现

> 源文件: `src/xps/SkXPSDocument.cpp`

## 概述

`SkXPSDocument.cpp` 实现了 Skia 的 XPS（XML Paper Specification）文档生成功能。该文件定义了 `SkXPSDocument` 类，它继承自 `SkDocument`，负责创建多页 XPS 文档。XPS 是微软定义的固定布局文档格式，类似于 PDF。此实现仅在 Windows 平台上编译（由 `SK_BUILD_FOR_WIN` 宏控制），依赖 Windows COM 接口 `IXpsOMObjectFactory` 来创建 XPS 对象模型。

## 架构位置

该文件位于 `src/xps/` 目录下，属于 Skia 文档输出子系统的一部分。它与 `SkXPSDevice`（XPS 渲染设备）协同工作：`SkXPSDocument` 管理文档级别的生命周期（开始/结束页面、关闭文档），而 `SkXPSDevice` 负责将 Skia 绘图命令转换为 XPS 图形原语。

## 主要类与结构体

### `SkXPSDocument`
匿名命名空间中的 final 类，继承自 `SkDocument`。

**成员变量**:
- `fXpsFactory`: `IXpsOMObjectFactory` 的智能指针，XPS 对象工厂
- `fDevice`: `SkXPSDevice` 实例，实际的 XPS 渲染设备
- `fCanvas`: 当前页面的 `SkCanvas`，由设备创建
- `fUnitsPerMeter`: 每米的绘图单位数（约 2834.65 点/米）
- `fPixelsPerMeter`: 每米的像素数（基于 DPI 配置）

**生命周期方法**:
- 构造函数: 初始化工厂、设备和单位转换因子，调用 `beginPortfolio` 开始文档
- 析构函数: 调用 `close()` 确保资源释放
- `onBeginPage()`: 创建新页面的 sheet 并返回关联的 canvas
- `onEndPage()`: 结束当前 sheet 并释放 canvas
- `onClose()`: 结束整个文档组合（portfolio）
- `onAbort()`: 空实现

## 公共 API 函数

### `SkXPS::MakeDocument(SkWStream*, IXpsOMObjectFactory*, Options)`
工厂函数，创建 XPS 文档实例。
- **参数**: 输出流、XPS 对象工厂指针、选项（包含 DPI）
- **返回**: `sk_sp<SkDocument>` 智能指针，如果参数无效则返回 `nullptr`

## 内部实现细节

1. **单位转换**: 使用常量 `360000.0 / 127.0`（约 2834.65）将英寸转换为点/米，DPI 到像素/米的转换使用 `dpi * 5000.0 / 127.0`。

2. **COM 资源管理**: 使用 `SkTScopedComPtr` 管理 `IXpsOMObjectFactory` 的生命周期，确保 COM 引用计数正确。

3. **Canvas 生命周期**: 每页创建一个新的 `SkCanvas`（通过 `sk_ref_sp` 引用设备），页面结束时释放。

4. **匿名命名空间**: `SkXPSDocument` 定义在匿名命名空间中，仅通过 `SkXPS::MakeDocument` 工厂函数间接创建，隐藏了实现细节。

5. **设备初始化尺寸**: 设备使用 `{10000, 10000}` 的初始尺寸创建，实际页面尺寸在 `beginSheet` 时指定。

## 依赖关系

- `include/docs/SkXPSDocument.h`: 公共头文件，声明 `SkXPS::MakeDocument`
- `include/core/SkStream.h`: 输出流
- `src/utils/win/SkHRESULT.h`: Windows HRESULT 处理
- `src/utils/win/SkTScopedComPtr.h`: COM 智能指针
- `src/xps/SkXPSDevice.h`: XPS 渲染设备
- `<XpsObjectModel.h>`: Windows XPS COM 接口

## 设计模式与设计决策

1. **工厂模式**: 通过 `SkXPS::MakeDocument` 工厂函数创建文档，隐藏具体实现类。

2. **模板方法模式**: 继承 `SkDocument` 并覆写 `onBeginPage`/`onEndPage`/`onClose`/`onAbort` 虚函数。

3. **仅 Windows 编译**: 整个文件被 `SK_BUILD_FOR_WIN` 条件编译包围，反映了 XPS 格式与 Windows 平台的强绑定关系。

4. **所有权转移**: `IXpsOMObjectFactory` 通过 `std::move` 转移所有权给文档对象，确保唯一所有者。

## 性能考量

- **最小内存分配**: 每页仅创建一个 `SkCanvas` 对象
- **流式输出**: 通过 `SkWStream` 直接写入，无需缓存整个文档
- **COM 对象复用**: 工厂对象在文档生命周期内复用

## 相关文件

- `include/docs/SkXPSDocument.h`: 公共 API 头文件
- `src/xps/SkXPSDevice.h`: XPS 渲染设备实现
- `src/utils/win/SkTScopedComPtr.h`: COM 智能指针工具
