# src/utils/win - Windows 平台专用工具库

## 概述

`src/utils/win` 目录包含了 Skia 在 Windows 平台上与 Microsoft DirectWrite 和 COM（Component Object Model）框架交互的工具代码。这些工具是 Skia 在 Windows 上实现高质量字体渲染和系统集成的关键基础设施，提供了 DirectWrite 工厂管理、字体流适配、几何路径转换、COM 智能指针以及 HRESULT 错误处理等核心功能。

该目录中所有代码均通过 `SK_BUILD_FOR_WIN` 条件编译宏进行平台隔离，确保仅在 Windows 平台上编译和链接。代码与 Windows SDK 的 `dwrite.h`、`d2d1.h`、`ole2.h` 和 `objbase.h` 等头文件紧密集成，广泛使用了 COM 接口编程范式。

从功能维度划分，该目录的代码涵盖以下核心领域：DirectWrite 工厂管理与字符串转换工具（`SkDWrite`），提供全局共享的 IDWriteFactory 实例以及 UTF-8/WCHAR 字符串双向转换；字体流双向适配器（`SkDWriteFontFileStream`），实现了 Skia 流与 DirectWrite 流之间的互操作；DirectWrite 到 Skia 的几何路径转换器（`SkDWriteGeometrySink`），将 DirectWrite 的字形轮廓数据转换为 Skia 的 SkPath；COM 资源管理基础设施，包括 COM 智能指针（`SkTScopedComPtr`）、自动 COM 初始化（`SkAutoCoInitialize`）和 IStream 适配器（`SkIStream`）；以及 HRESULT 错误处理宏系统（`SkHRESULT`）。

这些工具在 Skia 的 Windows 字体端口（`src/ports/SkTypeface_win_dw.h`）、Windows 字体管理器（`src/ports/SkFontMgr_win_dw.cpp`）以及其他 Windows 特定的渲染代码中被广泛使用。

## 架构图

```
+--------------------------------------------------------------------------+
|                     src/utils/win 平台工具库                               |
+--------------------------------------------------------------------------+
|                                                                            |
|  +------------------------------+    +-------------------------------+    |
|  | DirectWrite 集成层            |    | COM 资源管理层                 |    |
|  |                              |    |                               |    |
|  | SkDWrite.h / .cpp            |    | SkAutoCoInitialize.h / .cpp   |    |
|  |   sk_get_dwrite_factory()    |    |   CoInitializeEx() / CoUninit |    |
|  |   sk_cstring_to_wchar()      |    |                               |    |
|  |   sk_wchar_to_skstring()     |    | SkTScopedComPtr.h             |    |
|  |   sk_get_locale_string()     |    |   COM 智能指针模板             |    |
|  |   AutoDWriteTable             |    |   AddRef() / Release() 管理   |    |
|  |   AutoTDWriteTable<T>         |    |                               |    |
|  |   DWriteStyle                |    | SkObjBase.h                   |    |
|  |                              |    |   SK_STDMETHODIMP 宏          |    |
|  | SkDWriteFontFileStream.h/.cpp|    |                               |    |
|  |   SkDWriteFontFileStream     |    +-------------------------------+    |
|  |   SkDWriteFontFileStream-    |                                         |
|  |     Wrapper                  |    +-------------------------------+    |
|  |                              |    | IStream 适配层                 |    |
|  | SkDWriteGeometrySink.h/.cpp  |    |                               |    |
|  |   IDWriteGeometrySink 实现    |    | SkIStream.h / .cpp            |    |
|  |   DWrite 路径 -> SkPath      |    |   SkBaseIStream (基类)         |    |
|  |                              |    |   SkIStream (只读适配器)       |    |
|  +------------------------------+    |   SkWIStream (只写适配器)      |    |
|                                      |                               |    |
|  +------------------------------+    +-------------------------------+    |
|  | 错误处理与版本管理             |                                        |
|  |                              |                                        |
|  | SkHRESULT.h / .cpp           |                                        |
|  |   HR / HRB / HRN / HRV 宏   |                                        |
|  |   SkTraceHR() 调试追踪        |                                        |
|  |                              |                                        |
|  | SkDWriteNTDDI_VERSION.h      |                                        |
|  |   NTDDI_VERSION 宏重置        |                                        |
|  +------------------------------+                                        |
+--------------------------------------------------------------------------+
           |                                      |
           v                                      v
+------------------------+              +---------------------+
| Windows 系统框架        |              | Skia 核心模块        |
|                        |              |                     |
| DirectWrite (dwrite.h) |              | include/core/       |
|   IDWriteFactory       |              |   SkStream          |
|   IDWriteFontFace      |              |   SkPathBuilder     |
|   IDWriteFontFileStream|              |   SkString          |
|   IDWriteGeometrySink  |              |   SkFontStyle       |
|                        |              |                     |
| Direct2D (d2d1.h)      |              | src/ports/          |
|   D2D1_POINT_2F        |              |   SkTypeface_win_dw |
|   D2D1_BEZIER_SEGMENT  |              |   SkFontMgr_win_dw  |
|                        |              |                     |
| COM / OLE (objbase.h)  |              | src/base/           |
|   IUnknown             |              |   SkLeanWindows.h   |
|   IStream              |              |                     |
+------------------------+              +---------------------+
```

## 目录结构

```
src/utils/win/
├── BUILD.bazel                       # Bazel 构建配置
├── SkAutoCoInitialize.cpp            # COM 自动初始化实现
├── SkAutoCoInitialize.h              # COM 自动初始化头文件
├── SkDWrite.cpp                      # DirectWrite 工厂与字符串转换实现
├── SkDWrite.h                        # DirectWrite 工具头文件
├── SkDWriteFontFileStream.cpp        # DWrite 字体流适配器实现
├── SkDWriteFontFileStream.h          # DWrite 字体流适配器头文件
├── SkDWriteGeometrySink.cpp          # DWrite 几何路径转换器实现
├── SkDWriteGeometrySink.h            # DWrite 几何路径转换器头文件
├── SkDWriteNTDDI_VERSION.h           # NTDDI 版本宏重置
├── SkHRESULT.cpp                     # HRESULT 错误追踪实现
├── SkHRESULT.h                       # HRESULT 错误处理宏定义
├── SkIStream.cpp                     # IStream 适配器实现
├── SkIStream.h                       # IStream 适配器头文件
├── SkObjBase.h                       # COM STDMETHOD 宏修正
└── SkTScopedComPtr.h                 # COM 智能指针模板
```

## 关键类与函数

### SkDWrite - DirectWrite 工厂与工具集

```cpp
// src/utils/win/SkDWrite.h

// 全局 DirectWrite 工厂访问
IDWriteFactory* sk_get_dwrite_factory();

// UTF-8 与 WCHAR 字符串互转
typedef skia_private::AutoSTMalloc<16, WCHAR> SkSMallocWCHAR;
HRESULT sk_cstring_to_wchar(const char* skname, SkSMallocWCHAR* name);
HRESULT sk_wchar_to_skstring(WCHAR* name, int nameLen, SkString* skname);

// 本地化字符串获取
HRESULT sk_get_locale_string(IDWriteLocalizedStrings* names,
                              const WCHAR* preferedLocale, SkString* skname);
```

`sk_get_dwrite_factory()` 是最核心的函数，它使用 `SkOnce` 保证线程安全的单例初始化。初始化时首先尝试加载 `DWriteCore.dll`（WinUI 3 的 DWrite 实现），若失败则回退到系统的 `dwrite.dll`。创建的是 `DWRITE_FACTORY_TYPE_SHARED` 类型的共享工厂实例，并通过 `atexit()` 注册释放回调确保进程退出时正确清理。

#### AutoDWriteTable 与 AutoTDWriteTable

```cpp
// src/utils/win/SkDWrite.h
class AutoDWriteTable {
public:
    AutoDWriteTable(IDWriteFontFace* fontFace, UINT32 beTag);
    ~AutoDWriteTable();  // 自动释放字体表锁
    const uint8_t* fData;
    UINT32 fSize;
    BOOL fExists;
};

template<typename T> class AutoTDWriteTable : public AutoDWriteTable {
public:
    static const UINT32 tag = DWRITE_MAKE_OPENTYPE_TAG(T::TAG0, T::TAG1, T::TAG2, T::TAG3);
    const T* get() const;
    const T* operator->() const;
};
```

RAII 风格的 OpenType 字体表访问器。`AutoDWriteTable` 通过 `IDWriteFontFace::TryGetFontTable()` 获取字体表数据并持有锁，在析构时通过 `ReleaseFontTable()` 释放锁。`AutoTDWriteTable<T>` 是类型安全的模板版本，支持通过 `operator->()` 直接以结构体方式访问字体表字段。

#### DWriteStyle

```cpp
// src/utils/win/SkDWrite.h
struct DWriteStyle {
    explicit DWriteStyle(const SkFontStyle& pattern);
    DWRITE_FONT_WEIGHT fWeight;    // 字重
    DWRITE_FONT_STRETCH fWidth;    // 字宽
    DWRITE_FONT_STYLE fSlant;      // 倾斜
};
```

将 Skia 的 `SkFontStyle` 转换为 DirectWrite 的字体样式参数。字重和字宽通过直接强制类型转换完成（两个系统使用相同的数值范围），字形倾斜则需要从 Skia 的 Upright/Italic/Oblique 映射为 DirectWrite 的 Normal/Italic/Oblique。

### SkDWriteFontFileStream - 字体流双向适配器

```cpp
// src/utils/win/SkDWriteFontFileStream.h

// 方向 1: IDWriteFontFileStream -> SkStreamMemory
// 允许 Skia 代码读取 DirectWrite 字体流
class SkDWriteFontFileStream : public SkStreamMemory {
public:
    explicit SkDWriteFontFileStream(IDWriteFontFileStream* fontFileStream);
    size_t read(void* buffer, size_t size) override;
    bool isAtEnd() const override;
    bool rewind() override;
    bool seek(size_t position) override;
    size_t getLength() const override;
    const void* getMemoryBase() override;
    std::unique_ptr<SkDWriteFontFileStream> duplicate() const;
    std::unique_ptr<SkDWriteFontFileStream> fork() const;
};

// 方向 2: SkStreamAsset -> IDWriteFontFileStream
// 允许 DirectWrite 代码读取 Skia 流
class SkDWriteFontFileStreamWrapper : public IDWriteFontFileStream {
public:
    // IUnknown 方法
    SK_STDMETHODIMP QueryInterface(REFIID iid, void** ppvObject) override;
    SK_STDMETHODIMP_(ULONG) AddRef() override;
    SK_STDMETHODIMP_(ULONG) Release() override;

    // IDWriteFontFileStream 方法
    SK_STDMETHODIMP ReadFileFragment(...) override;
    SK_STDMETHODIMP_(void) ReleaseFileFragment(void* fragmentContext) override;
    SK_STDMETHODIMP GetFileSize(UINT64* fileSize) override;
    SK_STDMETHODIMP GetLastWriteTime(UINT64* lastWriteTime) override;

    static HRESULT Create(SkStreamAsset* stream,
                          SkDWriteFontFileStreamWrapper** streamFontFileStream);
};
```

这是一对互补的适配器类，实现了 Skia 流系统与 DirectWrite 流系统之间的完全双向互操作。

- **SkDWriteFontFileStream**（DWrite -> Skia 方向）：将 `IDWriteFontFileStream` 包装为 `SkStreamMemory`，使 Skia 的字体解析代码可以读取 DirectWrite 管理的字体数据。内部通过 `IDWriteFontFileStream::ReadFileFragment()` 获取锁定的内存片段。

- **SkDWriteFontFileStreamWrapper**（Skia -> DWrite 方向）：将 `SkStreamAsset` 包装为 `IDWriteFontFileStream`，使 DirectWrite 可以读取 Skia 管理的字体数据。使用 `SkMutex` 保护内部的 `SkStreamAsset`，因为 DirectWrite 可能从多个线程并发访问。手动实现 COM 引用计数（`AddRef`/`Release`）。

### SkDWriteGeometrySink - 字形轮廓路径转换器

```cpp
// src/utils/win/SkDWriteGeometrySink.h
class SkDWriteGeometrySink : public IDWriteGeometrySink {
public:
    // IUnknown 方法
    SK_STDMETHODIMP QueryInterface(REFIID iid, void** object) override;
    SK_STDMETHODIMP_(ULONG) AddRef() override;
    SK_STDMETHODIMP_(ULONG) Release() override;

    // IDWriteGeometrySink（即 ID2D1SimplifiedGeometrySink）方法
    SK_STDMETHODIMP_(void) SetFillMode(D2D1_FILL_MODE fillMode) override;
    SK_STDMETHODIMP_(void) SetSegmentFlags(D2D1_PATH_SEGMENT vertexFlags) override;
    SK_STDMETHODIMP_(void) BeginFigure(D2D1_POINT_2F startPoint,
                                         D2D1_FIGURE_BEGIN figureBegin) override;
    SK_STDMETHODIMP_(void) AddLines(const D2D1_POINT_2F* points, UINT pointsCount) override;
    SK_STDMETHODIMP_(void) AddBeziers(const D2D1_BEZIER_SEGMENT* beziers,
                                        UINT beziersCount) override;
    SK_STDMETHODIMP_(void) EndFigure(D2D1_FIGURE_END figureEnd) override;
    SK_STDMETHODIMP Close() override;

    static HRESULT Create(SkPathBuilder*, IDWriteGeometrySink** geometryToPath);

private:
    LONG fRefCount;
    SkPathBuilder* fBuilder;
    bool fStarted;
    D2D1_POINT_2F fCurrent;
};
```

这是 DirectWrite 字形轮廓到 Skia 路径的核心转换器。DirectWrite 使用 `IDWriteGeometrySink`（继承自 `ID2D1SimplifiedGeometrySink`）回调接口来输出字形的几何数据，此类实现该接口并将所有几何操作转换为 `SkPathBuilder` 调用：

- `BeginFigure()` -> 记录起始点，延迟 `moveTo()`
- `AddLines()` -> `SkPathBuilder::lineTo()`
- `AddBeziers()` -> `SkPathBuilder::cubicTo()`（三次 Bezier 曲线）
- `EndFigure()` -> 根据结束类型决定是否调用 `close()`
- `SetFillMode()` -> 设置 `SkPathFillType`

`goingTo()` 辅助方法实现了延迟 `moveTo()` 的逻辑：只有在实际需要绘制线段或曲线时才调用 `moveTo()`，避免了对空图形的无效移动。

### SkTScopedComPtr - COM 智能指针

```cpp
// src/utils/win/SkTScopedComPtr.h
template<typename T> T* SkRefComPtr(T* ptr);      // 增加引用计数
template<typename T> T* SkSafeRefComPtr(T* ptr);   // 安全增加引用计数（检查 null）

template<typename T>
class SkTScopedComPtr {
public:
    constexpr SkTScopedComPtr();
    explicit SkTScopedComPtr(T* ptr);
    SkTScopedComPtr(SkTScopedComPtr&& that);     // 支持移动语义
    ~SkTScopedComPtr();                           // 自动调用 Release()

    T& operator*() const;
    T* operator->() const;
    T** operator&();          // 仅允许在空指针上使用（用于 COM 输出参数）
    explicit operator bool() const;

    T* get() const;
    void reset(T* ptr = nullptr);
    void swap(SkTScopedComPtr<T>& that);
    T* release();             // 释放所有权
};
```

这是专门为 COM 对象设计的智能指针，类似于 `std::unique_ptr` 但使用 COM 的 `AddRef()/Release()` 引用计数机制。关键设计要点：

- **禁止拷贝**：删除了拷贝构造和拷贝赋值操作符，防止意外增加引用计数
- **支持移动**：通过移动构造和移动赋值实现所有权转移
- **安全的 `operator&()`**：仅允许在指针为空时获取地址，用于 COM 的输出参数模式（如 `factory->CreateXxx(&ptr)`）。在非空指针上使用会触发断言失败
- **自动释放**：析构时自动调用 `Release()`

### SkAutoCoInitialize - COM 自动初始化

```cpp
// src/utils/win/SkAutoCoInitialize.h
class [[nodiscard]] SkAutoCoInitialize : SkNoncopyable {
public:
    SkAutoCoInitialize();   // 调用 CoInitializeEx(COINIT_APARTMENTTHREADED)
    ~SkAutoCoInitialize();  // 调用 CoUninitialize()
    bool succeeded();       // 检查初始化是否成功
};
```

RAII 风格的 COM 运行时初始化管理器。构造时调用 `CoInitializeEx()` 以单线程套间（STA）模式初始化 COM，析构时调用 `CoUninitialize()`。`succeeded()` 方法在 `CoInitializeEx()` 返回 `S_OK` 或 `RPC_E_CHANGED_MODE`（COM 已以不同模式初始化）时均返回 true。`[[nodiscard]]` 属性确保调用者不会忽略返回的对象。

### SkHRESULT - 错误处理宏体系

```cpp
// src/utils/win/SkHRESULT.h
void SkTraceHR(const char* file, unsigned long line, HRESULT hr, const char* msg);

// 核心宏 - 计算表达式并在失败时返回
#define HR_GENERAL(_ex, _msg, _ret) do { ... } while(false)

// 各种返回值类型的变体
#define HR(ex)          // 失败时返回 HRESULT
#define HRM(ex, msg)    // 失败时返回 HRESULT + 追踪消息
#define HRB(ex)         // 失败时返回 false
#define HRBM(ex, msg)   // 失败时返回 false + 追踪消息
#define HRN(ex)         // 失败时返回 nullptr
#define HRNM(ex, msg)   // 失败时返回 nullptr + 追踪消息
#define HRV(ex)         // 失败时无返回值（void 函数）
#define HRVM(ex, msg)   // 失败时无返回值 + 追踪消息
#define HRZ(ex)         // 失败时返回 0
#define HRZM(ex, msg)   // 失败时返回 0 + 追踪消息
```

这套宏体系提供了统一的 Windows HRESULT 错误处理模式。每个宏都会评估表达式，如果结果 HRESULT 表示失败（`FAILED(hr)`），则在 Debug 构建中通过 `SkTraceHR()` 记录文件名、行号和可选的错误消息，然后从当前函数返回指定类型的错误值。

### SkIStream - IStream 接口适配器

```cpp
// src/utils/win/SkIStream.h

// IStream 基类 - 所有方法返回 E_NOTIMPL
class SkBaseIStream : public IStream {
    // IUnknown: QueryInterface, AddRef, Release
    // ISequentialStream: Read, Write
    // IStream: SetSize, CopyTo, Commit, Revert, LockRegion, UnlockRegion, Clone, Seek, Stat
};

// 只读适配器: SkStreamAsset -> IStream
class SkIStream : public SkBaseIStream {
public:
    static HRESULT CreateFromSkStream(std::unique_ptr<SkStreamAsset>, IStream** ppStream);
    // 覆盖 Read, Write(返回错误), Seek, Stat
};

// 只写适配器: SkWStream -> IStream
class SkWIStream : public SkBaseIStream {
public:
    static HRESULT CreateFromSkWStream(SkWStream* stream, IStream** ppStream);
    // 覆盖 Write, Commit, Stat
};
```

三层 IStream 适配器架构：`SkBaseIStream` 提供默认的 E_NOTIMPL 实现和引用计数管理；`SkIStream` 将 Skia 的只读流适配为 Windows 的 IStream 只读流；`SkWIStream` 将 Skia 的只写流适配为 Windows 的 IStream 只写流。

### SkObjBase.h - COM 方法宏修正

```cpp
// src/utils/win/SkObjBase.h
#define SK_STDMETHODIMP COM_DECLSPEC_NOTHROW STDMETHODIMP
#define SK_STDMETHODIMP_(type) COM_DECLSPEC_NOTHROW STDMETHODIMP_(type)
```

修正了 Windows SDK 中 `STDMETHOD`（接口声明）和 `STDMETHODIMP`（实现声明）之间的异常规范不一致问题。`STDMETHOD` 使用 `COM_DECLSPEC_NOTHROW` 而 `STDMETHODIMP` 没有，这会在实现 COM 接口时产生编译警告。通过定义 `SK_STDMETHODIMP` 宏，为实现端也添加 `COM_DECLSPEC_NOTHROW`，确保接口声明和实现之间的异常规范一致。

### SkDWriteNTDDI_VERSION.h - 版本宏管理

```cpp
// src/utils/win/SkDWriteNTDDI_VERSION.h
// 必须在所有 Windows 和 DWrite 头文件之前包含
#if defined(NTDDI_VERSION)
#  undef NTDDI_VERSION
#  undef _WIN32_WINNT
#  undef WINVER
#endif
```

此头文件解决了 `dwrite_3.h` 中 API 可用性的条件编译问题。DWrite 3 的头文件使用 `NTDDI_VERSION` 宏来决定哪些枚举、宏和接口可见。由于 DWrite 的接口是不可变的（immutable），所以无论 NTDDI_VERSION 设置为何值，这些接口都应该可用。此头文件通过重置这些版本宏来确保所有 DWrite 3 的 API 声明都可见。

## 依赖关系

```
src/utils/win/ 的依赖关系图:

Windows SDK 依赖:
  dwrite.h            -> IDWriteFactory, IDWriteFontFace, IDWriteFontFileStream
  dwrite_3.h          -> IDWriteFactory3 等高版本接口
  d2d1.h              -> D2D1_POINT_2F, D2D1_BEZIER_SEGMENT, IDWriteGeometrySink
  objbase.h           -> CoInitializeEx, CoUninitialize, STDMETHOD
  ole2.h              -> IStream, ISequentialStream
  winsdkver.h         -> SDK 版本信息

内部相互依赖:
  SkDWrite.cpp         -> SkHRESULT.h (HRVM 宏)
  SkDWriteFontFileStream.h -> SkObjBase.h, SkTScopedComPtr.h
  SkDWriteGeometrySink.h   -> SkObjBase.h
  SkIStream.h              -> SkObjBase.h
  SkTScopedComPtr.h        -> SkObjBase.h

Skia 内部依赖:
  include/core/SkStream.h      -> SkStream, SkWStream, SkStreamMemory
  include/core/SkString.h      -> SkString
  include/core/SkFontStyle.h   -> SkFontStyle
  include/core/SkPathBuilder.h -> SkPathBuilder
  include/private/base/SkMutex.h         -> SkMutex（线程安全）
  include/private/base/SkOnce.h          -> SkOnce（单例初始化）
  include/private/base/SkNoncopyable.h   -> SkNoncopyable
  include/private/base/SkTemplates.h     -> AutoSTMalloc
  src/base/SkLeanWindows.h               -> 精简 Windows 头文件

被以下模块使用:
  src/ports/SkTypeface_win_dw.cpp  -> 使用 AutoTDWriteTable, DWriteStyle 等
  src/ports/SkFontMgr_win_dw.cpp   -> 使用 sk_get_dwrite_factory() 等
  src/ports/SkScalerContext_win_dw.cpp -> 使用 SkDWriteGeometrySink
```

## 设计模式分析

### 1. 适配器模式（Adapter Pattern）
该目录的核心设计模式。几乎每个文件都体现了适配器模式：
- `SkDWriteFontFileStream`：将 IDWriteFontFileStream 适配为 SkStreamMemory
- `SkDWriteFontFileStreamWrapper`：将 SkStreamAsset 适配为 IDWriteFontFileStream
- `SkDWriteGeometrySink`：将 SkPathBuilder 适配为 IDWriteGeometrySink
- `SkIStream`/`SkWIStream`：将 SkStream/SkWStream 适配为 IStream

### 2. RAII 模式（Resource Acquisition Is Initialization）
贯穿整个目录的资源管理策略：
- `SkTScopedComPtr<T>`：自动管理 COM 对象的引用计数
- `SkAutoCoInitialize`：自动管理 COM 运行时的初始化/反初始化
- `AutoDWriteTable`：自动管理 DirectWrite 字体表锁的获取/释放

### 3. 单例模式（Singleton Pattern）
`sk_get_dwrite_factory()` 使用 `SkOnce` 保证 `IDWriteFactory` 的线程安全单例初始化。工厂实例存储在全局静态变量 `gDWriteFactory` 中，通过 `atexit()` 注册释放回调。

### 4. 模板方法模式（Template Method Pattern）
`SkBaseIStream` 提供了 IStream 接口的默认骨架实现（所有方法返回 `E_NOTIMPL`），子类 `SkIStream` 和 `SkWIStream` 覆盖特定方法以提供实际功能。这允许每个子类只关注自己需要支持的操作。

### 5. 空对象/空操作模式（Null Object Pattern）
`SkBaseIStream` 中所有未实现的方法均返回 `E_NOTIMPL`，这是 COM 编程中的空操作模式。调用者通过检查返回值来判断某个操作是否被支持。

### 6. 宏定义策略模式
`SkHRESULT.h` 的宏体系通过在编译期选择不同的返回值策略（HRESULT / bool / nullptr / void / 0）来处理 COM 错误。同一个核心逻辑（`HR_GENERAL`）通过不同的返回值参数产生不同的错误处理行为。

### 7. 延迟初始化模式（Lazy Initialization）
`SkDWriteGeometrySink` 中的 `goingTo()` 方法体现了延迟初始化模式。`moveTo()` 操作被延迟到第一个实际的几何操作（lineTo/cubicTo）时才执行，避免了对空图形的无效操作。

## 数据流

### DirectWrite 工厂初始化流程
```
首次调用 sk_get_dwrite_factory()
    |
    v
SkOnce 保护的 create_dwrite_factory()
    |
    +---> 尝试加载 DWriteCore.dll (WinUI 3)
    |       |
    |       +---> 成功: 使用 DWriteCoreCreateFactory
    |       |
    |       +---> 失败: 回退
    |
    +---> 尝试加载 dwrite.dll (系统)
    |       |
    |       +---> 成功: 使用 DWriteCreateFactory
    |       |
    |       +---> 失败: 返回错误
    |
    v
DWriteCreateFactory(DWRITE_FACTORY_TYPE_SHARED, ...)
    |
    v
gDWriteFactory = IDWriteFactory*
atexit(release_dwrite_factory) -- 注册清理回调
    |
    v
返回 IDWriteFactory* 给调用者
```

### 字体字形轮廓到 SkPath 转换流程
```
IDWriteFontFace::GetGlyphRunOutline()
    |
    v
SkDWriteGeometrySink (实现 IDWriteGeometrySink)
    |
    +---> SetFillMode(D2D1_FILL_MODE_WINDING/ALTERNATE)
    |       -> 设置 SkPathFillType
    |
    +---> BeginFigure(startPoint, figureBegin)
    |       -> 记录 fCurrent，重置 fStarted = false
    |
    +---> AddLines([pt1, pt2, ...])  (可能多次调用)
    |       -> goingTo(pt) -- 延迟 moveTo
    |       -> fBuilder->lineTo(pt.x, pt.y)
    |
    +---> AddBeziers([bezier1, bezier2, ...])  (可能多次调用)
    |       -> goingTo(pt) -- 延迟 moveTo
    |       -> fBuilder->cubicTo(p1, p2, p3)  (三次 Bezier)
    |
    +---> EndFigure(D2D1_FIGURE_END_CLOSED / OPEN)
    |       -> CLOSED: fBuilder->close()
    |
    +---> Close()
    |       -> 完成所有图形
    |
    v
SkPathBuilder -> SkPath (Skia 路径输出)
```

### 字体流双向适配数据流
```
方向 1: DirectWrite -> Skia
+---------------------------+        +---------------------------+
| IDWriteFontFileStream     | -----> | SkDWriteFontFileStream    |
| (DWrite 字体数据)         |        | (继承 SkStreamMemory)     |
|                           |        |                           |
| ReadFileFragment()        |  封装  | read() / seek() / rewind()|
| ReleaseFileFragment()     | -----> | getLength()               |
| GetFileSize()             |        | getMemoryBase()           |
+---------------------------+        +---------------------------+
                                              |
                                              v
                                     Skia 字体解析代码

方向 2: Skia -> DirectWrite
+---------------------------+        +------------------------------+
| SkStreamAsset             | -----> | SkDWriteFontFileStreamWrapper|
| (Skia 字体数据)           |        | (实现 IDWriteFontFileStream) |
|                           |        |                              |
| read() / seek()           |  封装  | ReadFileFragment()           |
| getLength()               | -----> | ReleaseFileFragment()        |
|                           |        | GetFileSize()                |
+---------------------------+  互斥  | GetLastWriteTime()           |
                              锁保护  +------------------------------+
                                              |
                                              v
                                     DirectWrite 字体枚举/加载
```

### IStream 适配数据流
```
Skia 流系统                         Windows COM 流系统
+------------------+                +------------------+
| SkStreamAsset    |  SkIStream    | IStream (只读)    |
| (只读流)         | -----------> | Read() + Seek()   |
+------------------+                +------------------+

+------------------+                +------------------+
| SkWStream        |  SkWIStream   | IStream (只写)    |
| (只写流)         | -----------> | Write() + Commit()|
+------------------+                +------------------+
```

## 相关文档与参考

| 参考项 | 路径/链接 |
|-------|----------|
| Windows 字体端口 | `src/ports/SkTypeface_win_dw.h`, `src/ports/SkTypeface_win_dw.cpp` |
| Windows 字体管理器 | `src/ports/SkFontMgr_win_dw.cpp`, `src/ports/SkFontMgr_win_dw_factory.cpp` |
| Windows 缩放上下文 | `src/ports/SkScalerContext_win_dw.cpp` |
| 精简 Windows 头文件 | `src/base/SkLeanWindows.h` |
| Skia 流系统 | `include/core/SkStream.h` |
| Skia 路径构建器 | `include/core/SkPathBuilder.h` |
| Skia 字体样式 | `include/core/SkFontStyle.h` |
| 父目录工具库 | `src/utils/README.md` |
| Microsoft DirectWrite 文档 | https://learn.microsoft.com/en-us/windows/win32/directwrite/direct-write-portal |
| Microsoft COM 文档 | https://learn.microsoft.com/en-us/windows/win32/com/component-object-model--com--portal |
| Microsoft IStream 文档 | https://learn.microsoft.com/en-us/windows/win32/api/objidl/nn-objidl-istream |
| Skia 官方文档 | https://skia.org/docs/ |
