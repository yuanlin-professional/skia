# SkFontMgr_FontConfigInterface

> 源文件: include/ports/SkFontMgr_FontConfigInterface.h, src/ports/SkFontMgr_FontConfigInterface.cpp

## 概述

`SkFontMgr_FontConfigInterface` 是 Skia 图形库提供的一个基于 `SkFontConfigInterface` 的字体管理器实现。该模块将 `SkFontConfigInterface` 封装为完整的 `SkFontMgr` 实现，支持字体查询、缓存和实例化。

该实现主要用于 Linux/Unix 系统，特别是在沙盒化的渲染进程中，通过 `SkFontConfigInterface` 与主进程通信来访问字体资源。它提供了两级缓存机制：字体请求缓存和字体实例缓存，以优化性能。

## 架构位置

```
skia/
├── include/
│   └── ports/
│       └── SkFontMgr_FontConfigInterface.h    # 公共接口
└── src/
    └── ports/
        ├── SkFontMgr_FontConfigInterface.cpp   # 主实现
        ├── SkFontConfigInterface.h             # 字体配置接口（依赖）
        └── SkFontConfigTypeface.h              # 字体类型定义（依赖）
```

该模块位于 `ports` 层，为 Linux/Unix 系统提供基于 FontConfig 的字体管理，是跨平台字体系统的一部分。

## 主要类与结构体

### SkFontMgr_FCI

基于 `SkFontConfigInterface` 的字体管理器实现。

**继承关系:**
- 继承自 `SkFontMgr`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fFCI` | sk_sp<SkFontConfigInterface> | 字体配置接口 |
| `fScanner` | std::unique_ptr<SkFontScanner> | 字体扫描器 |
| `fMutex` | SkMutex | 互斥锁，保护缓存 |
| `fTFCache` | SkTypefaceCache | 字体实例缓存 |
| `fCache` | SkFontRequestCache | 字体请求缓存 |

### SkFontStyleSet_FCI

空的字体样式集实现（未实际使用）。

**继承关系:**
- 继承自 `SkFontStyleSet`

**说明:**
该类所有方法都返回空值或断言失败，因为 `SkFontMgr_FCI` 不支持枚举字体族。

### SkFontRequestCache

字体请求的结果缓存，使用 `SkResourceCache` 实现 LRU 缓存。

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fCachedResults` | SkResourceCache | LRU 缓存实例 |

**内部类:**

#### Request

字体请求的缓存键，包含字体族名称和样式。

**继承关系:**
- 继承自 `SkResourceCache::Key`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fStyle` | SkFontStyle | 请求的字体样式 |
| 名称字符串 | char[] | 字体族名称（动态大小） |

#### Result

缓存的字体请求结果。

**继承关系:**
- 继承自 `SkResourceCache::Rec`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fRequest` | std::unique_ptr<Request> | 请求键 |
| `fFace` | sk_sp<SkTypeface> | 缓存的字体实例 |

### SkTypeface_FCI

基于 `SkFontConfigInterface` 的字体类型实现（定义在 `SkFontConfigTypeface.h`）。

**继承关系:**
- 继承自 `SkTypeface_proxy`

**关键方法:**

| 方法名 | 说明 |
|--------|------|
| `onOpenStream` | 通过 `SkFontConfigInterface` 打开字体流 |
| `onGetFontDescriptor` | 获取字体描述符，标记需要序列化 |
| `getIdentity` | 获取字体标识符 |

## 公共 API 函数

### SkFontMgr_New_FCI

```cpp
SK_API sk_sp<SkFontMgr> SkFontMgr_New_FCI(
    sk_sp<SkFontConfigInterface> fci,
    std::unique_ptr<SkFontScanner> scanner
);
```

创建基于 `SkFontConfigInterface` 的字体管理器。

**参数:**
- `fci`: 字体配置接口实例，不能为空
- `scanner`: 字体扫描器实例，用于解析字体文件

**返回值:**
- `SkFontMgr` 实例的智能指针

**断言:**
- `fci` 不能为空，否则触发 `SkASSERT_RELEASE`

## 内部实现细节

### 字体匹配流程

`onMatchFamilyStyle` 实现字体匹配的核心逻辑：

1. **检查请求缓存**:
   ```cpp
   sk_sp<SkTypeface> face = fCache.findAndRef(request.get());
   if (face) {
       return face;
   }
   ```

2. **调用 FCI 匹配**:
   ```cpp
   SkFontConfigInterface::FontIdentity identity;
   SkString outFamilyName;
   SkFontStyle outStyle;
   if (!fFCI->matchFamilyName(requestedFamilyName, requestedStyle,
                              &identity, &outFamilyName, &outStyle)) {
       return nullptr;
   }
   ```

3. **检查字体实例缓存**:
   ```cpp
   face = fTFCache.findByProcAndRef(find_by_FontIdentity, &identity);
   ```

4. **创建新字体实例**:
   ```cpp
   if (!face) {
       sk_sp<SkTypeface> realTypeface = fScanner->MakeFromStream(
           std::unique_ptr<SkStreamAsset>(fFCI->openStream(identity)),
           SkFontArguments().setCollectionIndex(identity.fTTCIndex)
       );
       face.reset(SkTypeface_FCI::Create(std::move(realTypeface), fFCI, identity,
                                         std::move(outFamilyName), outStyle, false));
       fTFCache.add(face);
   }
   ```

5. **更新请求缓存**:
   ```cpp
   fCache.add(face, request.release());
   ```

### 两级缓存机制

#### 请求缓存 (fCache)

- **键**: `(familyName, SkFontStyle)`
- **值**: `sk_sp<SkTypeface>`
- **目的**: 缓存完整的查找请求，避免重复调用 `matchFamilyName`
- **淘汰策略**: LRU，最大容量 32KB

#### 实例缓存 (fTFCache)

- **键**: `FontIdentity`（通过 `find_by_FontIdentity` 函数查找）
- **值**: `sk_sp<SkTypeface>`
- **目的**: 共享相同 `FontIdentity` 的字体实例
- **淘汰策略**: 由 `SkTypefaceCache` 管理

### Request 内存布局

`Request` 类使用自定义内存布局，将字体族名称存储在对象尾部：

```
[SkResourceCache::Key]
[fStyle: SkFontStyle]
[name: char[]]  <- 对齐到 4 字节
```

通过 `SkTAfter` 和 `SkAlign4` 确保内存布局正确。

### 自定义内存管理

`Request` 使用 placement new 和自定义 delete：

```cpp
static Request* Create(const char* name, const SkFontStyle& style) {
    size_t nameLen = name ? strlen(name) : 0;
    size_t contentLen = SkAlign4(nameLen);
    char* storage = new char[sizeof(Request) + contentLen];
    return new (storage) Request(name, nameLen, style);
}

void operator delete(void* storage) {
    delete[] reinterpret_cast<char*>(storage);
}
```

### 大小限制

`onMakeFromStreamArgs` 拒绝过大的字体文件：

```cpp
const size_t length = stream->getLength();
if (length >= 1024 * 1024 * 1024) {
    return nullptr;  // 拒绝 >= 1GB 的字体
}
```

### 未实现的方法

以下方法调用 `SK_ABORT`，因为 `SkFontConfigInterface` 不支持相关功能：

- `onCountFamilies`: 无法枚举所有字体族
- `onGetFamilyName`: 无法按索引获取字体族名称
- `onCreateStyleSet`: 无法创建样式集
- `onMatchFamily`: 无法返回样式集
- `onMatchFamilyStyleCharacter`: 不支持按字符匹配

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkFontConfigInterface` | 字体配置接口 |
| `SkFontScanner` | 扫描和解析字体文件 |
| `SkTypefaceCache` | 字体实例缓存 |
| `SkResourceCache` | 通用 LRU 缓存 |
| `SkMutex` | 互斥锁 |
| `SkFontConfigTypeface` | 字体类型定义 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| Chromium 渲染进程 | 在沙盒环境中访问字体 |
| Linux/Unix 应用 | 通过 FontConfig 管理字体 |

## 设计模式与设计决策

### 适配器模式

`SkFontMgr_FCI` 将 `SkFontConfigInterface` 适配为 `SkFontMgr` 接口，使其可以在 Skia 的字体管理框架中使用。

### 代理模式

`SkTypeface_FCI` 代理底层的真实字体实例，通过 `SkFontConfigInterface` 延迟加载字体数据。

### 缓存策略

- **两级缓存**: 请求缓存和实例缓存
- **LRU 淘汰**: 自动管理内存使用
- **线程安全**: 使用互斥锁保护缓存

### 懒加载

字体数据流仅在需要时通过 `SkFontConfigInterface::openStream` 打开，避免预加载所有字体。

### 限制明确

通过 `SK_ABORT` 明确标识不支持的功能，而不是返回错误或空值，避免误用。

### 内存安全

- 使用智能指针管理对象生命周期
- 自定义内存布局使用 placement new 确保正确构造

## 性能考量

### 缓存效率

- **请求缓存**: 避免重复的 FCI 查询和字体匹配
- **实例缓存**: 避免重复创建相同的字体实例
- **缓存大小**: 默认 32KB，根据 Chromium 经验优化

### 查找性能

- 哈希表查找（O(1)）
- LRU 缓存命中率取决于使用模式

### IPC 开销

如果 `SkFontConfigInterface` 基于 IPC：
- 首次查询需要跨进程通信
- 缓存命中可以完全避免 IPC

### 内存使用

- 请求缓存占用 32KB
- 实例缓存由 `SkTypefaceCache` 全局管理
- 每个缓存条目包含 `Request` 对象和 `SkTypeface` 智能指针

### 线程安全开销

所有缓存访问都需要获取互斥锁，可能成为多线程场景的瓶颈。

### 大文件防护

拒绝 >= 1GB 的字体文件，防止内存耗尽和安全问题。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/ports/SkFontMgr_FontConfigInterface.h` | 公共 API 头文件 |
| `src/ports/SkFontMgr_FontConfigInterface.cpp` | 主实现文件 |
| `include/ports/SkFontConfigInterface.h` | 字体配置接口定义 |
| `src/ports/SkFontConfigInterface.cpp` | 接口全局单例实现 |
| `src/ports/SkFontConfigTypeface.h` | 字体类型定义 |
| `src/ports/SkFontConfigTypeface.cpp` | 字体类型实现 |
| `include/core/SkFontMgr.h` | 字体管理器基类 |
| `src/core/SkResourceCache.h` | 通用资源缓存 |
| `src/core/SkTypefaceCache.h` | 字体实例缓存 |
