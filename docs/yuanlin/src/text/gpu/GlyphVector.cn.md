# GlyphVector - GPU 字形向量

> 源文件: `src/text/gpu/GlyphVector.h`, `src/text/gpu/GlyphVector.cpp`

## 概述

GlyphVector 提供了一种延迟查找字形的机制：在多线程环境中以 SkPackedGlyphID 的形式创建字形向量，然后在 GPU 单线程环境中将这些 ID 转换为后端特定的字形条目（包含 Atlas 位置信息）。这种设计是必要的，因为 StrikeCache 和 Atlas 仅支持单线程访问。

GlyphVector 使用 C++20 concepts 定义了后端数据的类型要求（BackendData 和 GlyphType），允许 Ganesh 和 Graphite 后端存储各自特定的字形数据类型。

## 架构位置

```
sktext::gpu 命名空间
  └── GlyphVector
        ├── 使用 SkStrikePromise 延迟获取 Strike
        ├── 存储 BackendData（后端特定数据）
        └── 存储 GlyphBytes 数组（PackedID 或后端字形）
```

- **所有者**: AtlasSubRun（DirectMaskSubRun、TransformedMaskSubRun、SDFTSubRun）
- **使用者**: GPU 后端的 Atlas 操作

## 主要类与结构体

### GlyphVector
**关键成员**:
- `fBackendDataBytes` — 后端数据的类型擦除存储（最大 88 字节）
- `fBackendDataReleaser` — 后端数据的析构函数指针
- `fGetGlyphID` — 从后端字形提取 PackedID 的函数指针
- `fStrikePromise` — Strike 的延迟获取承诺
- `fGlyphs` (SkSpan<GlyphBytes>) — 字形数组（每个元素最大 sizeof(void*)）

### GlyphVector_Concepts 命名空间
使用 C++20 concepts 定义后端类型约束：

**GlyphType concept**: 要求类型大小不超过 `sizeof(void*)`，可平凡销毁，并有 `packedID()` 方法。

**BackendData concept**: 要求有 `FindStrike` 静态方法和 `makeGlyphFromID` 成员方法。

## 公共 API 函数

```cpp
static GlyphVector Make(SkStrikePromise&&, SkSpan<const SkPackedGlyphID>, SubRunAllocator*);
static std::optional<GlyphVector> MakeFromBuffer(SkReadBuffer&, const SkStrikeClient*, SubRunAllocator*);
void flatten(SkWriteBuffer&) const;
int glyphCount() const;
```

### 模板方法
```cpp
template <BackendData B> void initBackendData(StrikeCache*, MaskFormat, auto&&...);
template <BackendData B> const B& accessBackendData() const;
template <GlyphType G> SkSpan<const G> accessBackendGlyphs() const;
```

## 内部实现细节

### 初始化流程
1. `Make()`: 分配 GlyphBytes 数组并存储 SkPackedGlyphID
2. `initBackendData<B>()`: 在 GPU 线程中调用
   - 从 SkStrikePromise 获取 Strike
   - 通过 `B::FindStrike` 查找/创建后端 Strike
   - 在 fBackendDataBytes 中原地构造 BackendData
   - 遍历所有字形，将 PackedID 原地替换为后端 GlyphType
   - 记录析构器和 ID 提取器函数指针
   - 释放 SkStrikePromise 对 Strike 的引用

### 序列化
`flatten()` 方法支持两种状态：
- 未初始化后端数据: 直接读取 PackedID
- 已初始化后端数据: 通过 `fGetGlyphID` 回调从后端字形提取 PackedID

### 内存布局
```
GlyphVector 对象
  ├── BackendDataBytes [88 bytes, max_align_t aligned]
  ├── fStrikePromise
  └── fGlyphs -> [GlyphBytes[0], GlyphBytes[1], ..., GlyphBytes[n-1]]
                  (每个 sizeof(void*) 字节)
```

## 依赖关系

- `SkStrikePromise` — Strike 延迟获取
- `SubRunAllocator` — 内存分配
- `StrikeCache` / `TextStrikeBase` — GPU 端 Strike 缓存
- `SkPackedGlyphID` — 打包字形 ID
- `skgpu::MaskFormat` — 遮罩格式

## 设计模式与设计决策

1. **类型擦除**: 使用字节数组 + 函数指针实现类型擦除，避免虚函数开销
2. **原地替换**: PackedID 和后端字形共用相同存储，避免额外分配
3. **Concepts 约束**: 使用 C++20 concepts 确保后端类型满足接口要求
4. **禁用拷贝/赋值**: GlyphVector 不可拷贝，仅支持移动（且仅在后端数据初始化前）
5. **延迟转换**: 字形 ID 到后端类型的转换延迟到 GPU 单线程环境

## 性能考量

- GlyphBytes 大小限制为 `sizeof(void*)` 确保紧凑的内存布局
- 原地替换避免额外的内存分配和拷贝
- 后端数据初始化后释放 Strike 引用，允许 Strike 被缓存淘汰

## 相关文件

- `src/text/StrikeForGPU.h` — SkStrikePromise
- `src/text/gpu/SubRunAllocator.h` — 内存分配器
- `src/text/gpu/StrikeCache.h` — GPU Strike 缓存
- `src/text/gpu/SubRunContainer.h` — AtlasSubRun（GlyphVector 的所有者）
