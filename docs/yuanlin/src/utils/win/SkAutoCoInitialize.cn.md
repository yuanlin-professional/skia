# SkAutoCoInitialize - COM 自动初始化

> 源文件:
> - `src/utils/win/SkAutoCoInitialize.h`
> - `src/utils/win/SkAutoCoInitialize.cpp`

## 概述

SkAutoCoInitialize 是一个 RAII 包装类，用于在 Windows 平台上自动管理 COM (Component Object Model) 库的初始化和反初始化。创建实例时调用 `CoInitializeEx`，销毁时调用 `CoUninitialize`，确保 COM 资源被正确清理。

## 架构位置

```
Skia Windows 平台层
├── COM 依赖的子系统
│   ├── DirectWrite 字体
│   ├── WIC 图像编解码
│   └── XPS 输出
│       └── SkAutoCoInitialize (本模块 - COM 生命周期管理)
└── Windows API (COM 运行时)
```

## 主要类与结构体

### `SkAutoCoInitialize`
- 使用 `[[nodiscard]]` 属性标记，编译器会在返回值被忽略时发出警告。
- 继承自 `SkNoncopyable`，禁止复制。
- **成员变量**: `fHR` (HRESULT) - 存储 `CoInitializeEx` 的返回值。

## 公共 API 函数

### 构造函数
```cpp
SkAutoCoInitialize();
```
- **功能**: 调用 `CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE)` 初始化 COM。
- **参数选择**: 使用单线程单元模型 (STA) 并禁用旧式 OLE1 DDE 支持。

### 析构函数
```cpp
~SkAutoCoInitialize();
```
- **功能**: 如果初始化成功 (`SUCCEEDED(fHR)`)，调用 `CoUninitialize()`。

### `succeeded`
```cpp
bool succeeded();
```
- **功能**: 检查 COM 初始化是否成功。
- **特殊处理**: 除了标准的 `SUCCEEDED(fHR)` 检查外，还将 `RPC_E_CHANGED_MODE` 视为成功。这是因为如果 COM 已经以不同模式初始化过（如 MTA），`CoInitializeEx` 会返回 `RPC_E_CHANGED_MODE`，但 COM 仍然可用。

## 内部实现细节

- `COINIT_APARTMENTTHREADED`: 请求单线程单元 (STA) 模式，这是大多数 UI 应用的标准选择。
- `COINIT_DISABLE_OLE1DDE`: 禁用 OLE1 DDE（动态数据交换），这是一个不再需要的遗留功能。
- `RPC_E_CHANGED_MODE` 处理: 当线程已在不同的并发模型下初始化 COM 时返回此错误码。Skia 正确地将其视为"COM 可用"而非失败。

## 依赖关系

- `include/core/SkTypes.h`: 平台检测宏 (`SK_BUILD_FOR_WIN`)。
- `include/private/base/SkNoncopyable.h`: 不可复制基类。
- `src/base/SkLeanWindows.h`: 精简的 Windows 头文件。
- `<objbase.h>`: `CoInitializeEx`, `CoUninitialize`。
- `<winerror.h>`: `RPC_E_CHANGED_MODE` 等错误码。

## 设计模式与设计决策

1. **RAII 模式**: 利用构造/析构的确定性调用保证 COM 的正确初始化和清理。
2. **容错设计**: 将 `RPC_E_CHANGED_MODE` 视为成功，增强了在已有 COM 初始化环境中的兼容性。
3. **[[nodiscard]] 注解**: 防止用户创建临时对象后立即销毁，导致 COM 在使用前就被反初始化。

## 性能考量

该类通常在作用域入口处创建一次，开销极小且可忽略。`CoInitializeEx` 在已初始化的线程上是快速的引用计数操作。

## 相关文件

- `src/utils/win/SkDWrite.h/.cpp`: DirectWrite 工具，依赖 COM 初始化。
- `src/utils/win/SkIStream.h/.cpp`: IStream 实现，依赖 COM。
- `src/ports/SkFontMgr_win_dw.cpp`: Windows 字体管理器，使用此类初始化 COM。
