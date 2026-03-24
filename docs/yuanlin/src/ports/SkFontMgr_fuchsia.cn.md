# SkFontMgr_fuchsia

> 源文件: include/ports/SkFontMgr_fuchsia.h, src/ports/SkFontMgr_fuchsia.cpp

## 概述

SkFontMgr_fuchsia 是 Skia 图形库为 Fuchsia 操作系统提供的字体管理器实现。它通过 Fuchsia 的字体服务 FIDL 接口与系统字体提供者通信，实现字体查询、加载和缓存功能。该实现采用代理模式，通过远程过程调用访问系统字体资源，支持字体样式匹配、字符回退和变体字体。

## 架构位置

该模块位于 Skia 的平台适配层（ports），专门为 Fuchsia 系统提供字体管理功能：

```
skia/
├── include/ports/
│   └── SkFontMgr_fuchsia.h         # 公共接口
└── src/ports/
    ├── SkFontMgr_fuchsia.cpp        # 实现
    ├── SkFontMgr_custom.h           # 基类支持
    └── SkTypeface_proxy.h           # 代理 typeface 基类
```

该模块依赖 Fuchsia SDK 的 FIDL 接口（fuchsia::fonts::Provider）与系统字体服务通信。

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|------|---------|------|
| `SkFuchsiaFontDataCache` | `SkRefCnt` | 管理从 Fuchsia 内存缓冲区创建的共享字体数据 |
| `SkTypeface_Fuchsia` | `SkTypeface_proxy` | Fuchsia 平台的 typeface 代理实现 |
| `SkFontMgr_Fuchsia` | `SkFontMgr` | Fuchsia 字体管理器主类 |
| `SkFontStyleSet_Fuchsia` | `SkFontStyleSet` | 字体家族样式集合 |

### 关键成员变量

**SkFuchsiaFontDataCache:**
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fMutex` | `SkMutex` | 保护缓冲区映射的互斥锁 |
| `fBuffers` | `std::unordered_map<int, SkData*>` | 缓冲区 ID 到字体数据的映射 |

**SkFontMgr_Fuchsia:**
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFontProvider` | `fuchsia::fonts::ProviderSyncPtr` | 同步字体服务接口 |
| `fBufferCache` | `sk_sp<SkFuchsiaFontDataCache>` | 字体数据缓存 |
| `fScanner` | `std::unique_ptr<SkFontScanner>` | 字体扫描器 |
| `fTypefaceCache` | `SkTypefaceCache` | typeface 缓存 |

**TypefaceId:**
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `bufferId` | `uint32_t` | 字体缓冲区标识符 |
| `ttcIndex` | `uint32_t` | TrueType 集合索引 |

## 公共 API 函数

### 工厂函数

```cpp
SK_API sk_sp<SkFontMgr> SkFontMgr_New_Fuchsia(
    fuchsia::fonts::ProviderSyncPtr provider,
    std::unique_ptr<SkFontScanner> scanner
);
```

创建 Fuchsia 字体管理器实例，需要提供字体服务提供者和字体扫描器。

### SkFontMgr 接口实现

```cpp
// 字体家族管理
int onCountFamilies() const override;
void onGetFamilyName(int index, SkString* familyName) const override;
sk_sp<SkFontStyleSet> onMatchFamily(const char familyName[]) const override;

// 字体匹配
sk_sp<SkTypeface> onMatchFamilyStyle(const char familyName[], const SkFontStyle&) const override;
sk_sp<SkTypeface> onMatchFamilyStyleCharacter(...) const override;

// 从数据创建 typeface
sk_sp<SkTypeface> onMakeFromData(sk_sp<SkData>, int ttcIndex) const override;
sk_sp<SkTypeface> onMakeFromStreamIndex(std::unique_ptr<SkStreamAsset>, int ttcIndex) const override;
sk_sp<SkTypeface> onMakeFromFile(const char path[], int ttcIndex) const override;
```

## 内部实现细节

### 字体数据缓存机制

SkFuchsiaFontDataCache 实现共享内存映射管理：

1. **内存映射**: 使用 Fuchsia 的 `zx::vmar` 将字体服务提供的 VMO（Virtual Memory Object）映射到进程地址空间
2. **引用计数**: 通过 `SkData::MakeWithProc` 关联自定义释放函数，在数据不再使用时自动解除映射
3. **共享数据**: 多个 typeface 可以共享同一个缓冲区的数据，避免重复内存映射

关键代码流程：
```cpp
// 映射 VMO 到进程内存
zx::vmar::root_self()->map(ZX_VM_PERM_READ, 0, buffer.vmo, 0, size, &mapped_addr);
// 创建带自定义释放函数的 SkData
auto data = SkData::MakeWithProc(reinterpret_cast<void*>(mapped_addr),
                                 size, ReleaseSkData, context);
```

### 样式转换

提供 Skia 和 Fuchsia 字体样式之间的双向转换：

- **倾斜 (Slant)**: `SkToFuchsiaSlant` / `FuchsiaToSkSlant`
- **宽度 (Width)**: `SkToFuchsiaWidth` / `FuchsiaToSkWidth`
- **综合样式**: `SkToFuchsiaStyle` 将 SkFontStyle 转换为 fuchsia::fonts::Style2

### 通用字体家族映射

支持 CSS 通用字体家族名称到 Fuchsia 类型的映射：

| CSS 名称 | Fuchsia 枚举 |
|---------|-------------|
| "serif" | `SERIF` |
| "sans-serif" / "sans" | `SANS_SERIF` |
| "monospace" / "mono" | `MONOSPACE` |
| "cursive" | `CURSIVE` |
| "fantasy" | `FANTASY` |
| "system-ui" | `SYSTEM_UI` |
| "emoji" | `EMOJI` |

### 字体查询流程

`FetchTypeface` 方法实现完整的字体匹配逻辑：

1. 构建 `TypefaceQuery` 设置样式、语言和字符要求
2. 判断是否为通用家族名，决定是否启用回退
3. 设置请求标志（精确家族匹配、精确样式匹配）
4. 通过 `fFontProvider->GetTypeface` 向系统服务查询
5. 使用返回的缓冲区 ID 和索引创建或获取缓存的 typeface

### Typeface 缓存策略

采用两级缓存架构：

1. **数据缓存**: `SkFuchsiaFontDataCache` 缓存内存映射的字体数据
2. **Typeface 缓存**: `SkTypefaceCache` 缓存已创建的 typeface 对象

查找逻辑使用 `FindByTypefaceId` 谓词函数比较 `TypefaceId`，确保相同字体不会重复创建。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `fuchsia::fonts` FIDL | 与 Fuchsia 字体服务通信 |
| `zx::vmar` | Fuchsia 虚拟内存管理 |
| `SkFontScanner` | 扫描字体文件元数据 |
| `SkTypeface_proxy` | 代理模式基类 |
| `SkFontDescriptor` | 字体描述符 |
| `SkTypefaceCache` | Typeface 缓存管理 |

### 被依赖的模块

该模块通过工厂函数被上层字体管理系统使用，在 Fuchsia 平台上作为默认字体管理器。

## 设计模式与设计决策

### 设计模式

1. **工厂模式**: `SkFontMgr_New_Fuchsia` 工厂函数创建字体管理器
2. **代理模式**: `SkTypeface_Fuchsia` 作为代理封装实际的 typeface 实现
3. **缓存模式**: 多级缓存减少重复加载和内存映射
4. **策略模式**: 通过 `SkFontScanner` 支持不同的字体扫描策略

### 设计决策

1. **同步 API**: 使用 `ProviderSyncPtr` 而非异步接口，简化实现但可能阻塞调用线程
2. **共享内存**: 利用 Fuchsia VMO 实现零拷贝字体数据传输
3. **缓冲区 ID**: 使用唯一标识符追踪字体缓冲区生命周期
4. **不支持枚举**: `onCountFamilies` 返回 0，依赖系统服务提供字体信息
5. **线程安全**: 使用互斥锁保护共享数据结构

### 平台特定考虑

- **Fuchsia 内核对象**: 直接操作 VMO 和 VMAR 等 Zircon 内核对象
- **FIDL 接口**: 严格遵循 Fuchsia FIDL 协议规范
- **组件隔离**: 字体服务作为独立组件运行，通过 FIDL 跨进程通信

## 性能考量

1. **内存映射优化**: 使用 VMO 映射而非复制字体数据，减少内存占用
2. **数据共享**: 多个 typeface 共享同一缓冲区映射，避免重复映射开销
3. **缓存策略**: 两级缓存减少 IPC 调用和字体解析次数
4. **懒加载**: 仅在需要时才映射和解析字体数据
5. **引用计数**: 自动管理资源生命周期，无需手动释放

### 潜在瓶颈

- **同步 IPC**: 每次字体查询都需要跨进程调用，延迟较高
- **锁竞争**: 缓存访问需要获取锁，高并发时可能成为瓶颈
- **内存映射开销**: 首次访问字体时的 VMAR 映射操作有一定成本

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/ports/SkFontMgr_fuchsia.h` | 公共接口定义 |
| `src/ports/SkFontMgr_fuchsia.cpp` | 实现文件 |
| `src/ports/SkFontMgr_custom.h` | 自定义字体管理器基类 |
| `src/ports/SkTypeface_proxy.h` | 代理 typeface 基类 |
| `src/core/SkFontDescriptor.h` | 字体描述符 |
| `src/core/SkTypefaceCache.h` | Typeface 缓存 |
| `include/core/SkFontMgr.h` | 字体管理器抽象基类 |
| `include/core/SkFontScanner.h` | 字体扫描器接口 |
