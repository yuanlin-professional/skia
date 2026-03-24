# SkTableColorFilter

> 源文件
> - `src/effects/colorfilters/SkTableColorFilter.h`
> - `src/effects/colorfilters/SkTableColorFilter.cpp`

## 概述

`SkTableColorFilter` 是 Skia 中实现基于查找表（LUT, Lookup Table）的颜色过滤器。它通过预定义的查找表对颜色的各个通道进行映射，实现快速的非线性颜色变换。每个颜色通道（R、G、B、A）都可以有独立的 256 个元素的查找表，将输入的 8 位值映射到输出的 8 位值。

查找表方式特别适合实现复杂的非线性颜色变换，如：
- 自定义曲线调整（如 S 曲线）
- 色阶调整
- 色调映射
- 颜色分级效果

与矩阵变换相比，查找表可以表示任意的单调或非单调函数，提供了更大的灵活性。

## 架构位置

```
skia/
├── include/
│   └── core/
│       ├── SkColorFilter.h          # 颜色过滤器公共接口
│       └── SkColorTable.h           # 颜色查找表类
├── src/
│   ├── core/
│   │   ├── SkRasterPipeline.h       # 光栅化管线
│   │   └── SkRasterPipelineOpContexts.h  # 管线操作上下文
│   └── effects/
│       └── colorfilters/
│           ├── SkColorFilterBase.h       # 颜色过滤器基类
│           ├── SkTableColorFilter.h      # 本模块头文件
│           └── SkTableColorFilter.cpp    # 本模块实现
```

`SkTableColorFilter` 依赖于 `SkColorTable` 类来存储和管理查找表数据，并通过 `SkRasterPipeline` 的 `byte_tables` 操作高效应用查找。

## 主要类与结构体

### SkTableColorFilter

查找表颜色过滤器类。

```cpp
class SkTableColorFilter final : public SkColorFilterBase {
public:
    SkTableColorFilter(sk_sp<SkColorTable> table) : fTable(table) {
        SkASSERT(fTable);
    }

    SkColorFilterBase::Type type() const override {
        return SkColorFilterBase::Type::kTable;
    }

    bool appendStages(const SkStageRec& rec, bool shaderIsOpaque) const override;
    void flatten(SkWriteBuffer& buffer) const override;

    const SkBitmap& bitmap() const { return fTable->bitmap(); }

private:
    sk_sp<SkColorTable> fTable;  // 颜色查找表
};
```

**特点**：
- 极简设计，主要逻辑在 `SkColorTable` 中
- 支持独立的 ARGB 通道查找表
- 通过智能指针管理查找表生命周期

## 公共 API 函数

### SkColorFilters::Table (单一查找表)

```cpp
sk_sp<SkColorFilter> SkColorFilters::Table(const uint8_t table[256]);
```

创建使用单一查找表的颜色过滤器，该表应用于所有 RGB 通道。

**参数**：
- `table` - 256 个元素的查找表，`table[i]` 表示输入值 `i` 映射到的输出值

**返回值**：颜色过滤器智能指针

**使用示例**：
```cpp
// 创建反相查找表
uint8_t invertTable[256];
for (int i = 0; i < 256; i++) {
    invertTable[i] = 255 - i;
}
auto filter = SkColorFilters::Table(invertTable);
```

### SkColorFilters::TableARGB (多通道查找表)

```cpp
sk_sp<SkColorFilter> SkColorFilters::TableARGB(
    const uint8_t tableA[256],
    const uint8_t tableR[256],
    const uint8_t tableG[256],
    const uint8_t tableB[256]);
```

创建为每个 ARGB 通道使用独立查找表的颜色过滤器。

**参数**：
- `tableA` - Alpha 通道查找表（可以为 nullptr，表示不变）
- `tableR` - 红色通道查找表（可以为 nullptr，表示不变）
- `tableG` - 绿色通道查找表（可以为 nullptr，表示不变）
- `tableB` - 蓝色通道查找表（可以为 nullptr，表示不变）

**返回值**：颜色过滤器智能指针

**使用示例**：
```cpp
// 增强红色通道，减弱蓝色通道
uint8_t redTable[256], blueTable[256];
for (int i = 0; i < 256; i++) {
    redTable[i] = std::min(255, i * 1.5);     // 增强
    blueTable[i] = i * 0.7;                    // 减弱
}
auto filter = SkColorFilters::TableARGB(nullptr, redTable, nullptr, blueTable);
```

### SkColorFilters::Table (SkColorTable)

```cpp
sk_sp<SkColorFilter> SkColorFilters::Table(sk_sp<SkColorTable> table);
```

使用现有的 `SkColorTable` 对象创建颜色过滤器。

**参数**：
- `table` - 颜色查找表对象

**返回值**：颜色过滤器智能指针，如果 `table` 为 nullptr 则返回 nullptr

## 内部实现细节

### 管线构建

`appendStages` 方法构建查找表应用管线：

```cpp
bool SkTableColorFilter::appendStages(const SkStageRec& rec,
                                      bool shaderIsOpaque) const {
    SkRasterPipeline* p = rec.fPipeline;

    // 1. 如果输入不是不透明的，反预乘以获得直接颜色值
    if (!shaderIsOpaque) {
        p->append(SkRasterPipelineOp::unpremul);
    }

    // 2. 准备查找表上下文
    SkRasterPipelineContexts::TablesCtx* tables =
            rec.fAlloc->make<SkRasterPipelineContexts::TablesCtx>();
    tables->a = fTable->alphaTable();
    tables->r = fTable->redTable();
    tables->g = fTable->greenTable();
    tables->b = fTable->blueTable();

    // 3. 应用字节查找表操作
    p->append(SkRasterPipelineOp::byte_tables, tables);

    // 4. 判断输出是否确定不透明
    bool definitelyOpaque = shaderIsOpaque && tables->a[0xff] == 0xff;

    // 5. 如果不确定不透明，重新预乘
    if (!definitelyOpaque) {
        p->append(SkRasterPipelineOp::premul);
    }

    return true;
}
```

**关键设计**：

1. **预乘处理**：查找表在非预乘颜色空间中操作
2. **不透明性优化**：如果输入不透明且 alpha 表的 `table[255] == 255`，输出也不透明
3. **上下文分配**：使用栈分配器创建上下文，与管线生命周期绑定

### TablesCtx 结构

```cpp
struct TablesCtx {
    const uint8_t* a;  // Alpha 查找表指针
    const uint8_t* r;  // 红色查找表指针
    const uint8_t* g;  // 绿色查找表指针
    const uint8_t* b;  // 蓝色查找表指针
};
```

这个轻量级结构仅包含指针，实际数据由 `SkColorTable` 管理。

### 序列化

```cpp
void SkTableColorFilter::flatten(SkWriteBuffer& buffer) const {
    fTable->flatten(buffer);  // 委托给 SkColorTable
}

sk_sp<SkFlattenable> SkTableColorFilter::CreateProc(SkReadBuffer& buffer) {
    return SkColorFilters::Table(SkColorTable::Deserialize(buffer));
}
```

**简洁性**：
- 过滤器本身不包含额外状态
- 所有序列化逻辑在 `SkColorTable` 中
- 创建过程使用工厂函数保证一致性

### 向后兼容性

```cpp
void SkRegisterTableColorFilterFlattenable() {
    SK_REGISTER_FLATTENABLE(SkTableColorFilter);
    // 注册旧类名
    SkFlattenable::Register("SkTable_ColorFilter",
                           SkTableColorFilter::CreateProc);
}
```

支持读取使用旧类名序列化的数据。

## 依赖关系

### 内部依赖

| 组件 | 用途 |
|-----|------|
| `SkColorFilterBase` | 颜色过滤器基类 |
| `SkColorTable` | 存储和管理查找表数据 |
| `SkRasterPipeline` | 构建执行管线 |
| `SkRasterPipelineOpContexts` | 定义管线操作上下文 |
| `SkArenaAlloc` | 栈分配器 |

### 外部依赖

| 组件 | 用途 |
|-----|------|
| `SkColorFilter` | 公共接口 |
| `SkReadBuffer` / `SkWriteBuffer` | 序列化支持 |

## 设计模式与设计决策

### 1. 委托模式（Delegation Pattern）

`SkTableColorFilter` 将数据管理委托给 `SkColorTable`：
- 过滤器类保持简洁
- 查找表可以在多个过滤器之间共享
- 序列化逻辑集中在数据类中

### 2. 策略模式（Strategy Pattern）

通过不同的查找表实现不同的颜色变换策略：
- 恒等表：`table[i] = i`（无变换）
- 反相表：`table[i] = 255 - i`
- Gamma 校正表：`table[i] = pow(i/255.0, gamma) * 255`
- 自定义曲线表

所有策略共享相同的应用机制。

### 3. 分离关注点（Separation of Concerns）

- `SkColorTable`：负责存储和查找表数据
- `SkTableColorFilter`：负责将查找表集成到颜色过滤器框架
- `SkRasterPipeline`：负责高效执行查找操作

这种分离使得每个类都有清晰的职责。

### 4. 不透明性推断

```cpp
bool definitelyOpaque = shaderIsOpaque && tables->a[0xff] == 0xff;
```

通过检查 alpha 表的最大值映射，推断输出的不透明性：
- 如果输入不透明（alpha = 255）
- 且 alpha 表将 255 映射到 255
- 则输出也不透明

这个简单的检查避免了不必要的预乘操作。

## 性能考量

### 1. 查找表的缓存效率

查找表大小固定为 256 字节/通道：
- 总共 1KB（4 个通道 × 256 字节）
- 适合 L1 缓存（通常 32-64KB）
- 访问模式对缓存友好

### 2. byte_tables 操作优化

`byte_tables` 管线操作高度优化：
- 支持 SIMD 向量化（一次处理多个像素）
- 查找操作无分支（branchless）
- 可以在 GPU 上高效执行（通过纹理采样）

### 3. 预乘优化

```cpp
if (!shaderIsOpaque) {
    p->append(SkRasterPipelineOp::unpremul);
}
// ... 应用查找表 ...
if (!definitelyOpaque) {
    p->append(SkRasterPipelineOp::premul);
}
```

**优化点**：
- 不透明输入跳过 unpremul
- 确定不透明输出跳过 premul
- 最佳情况下完全避免预乘开销

### 4. 查找表共享

通过智能指针共享 `SkColorTable`：
```cpp
sk_sp<SkColorTable> fTable;
```

**优势**：
- 多个过滤器可以共享相同的查找表
- 减少内存占用
- 提高缓存命中率

### 5. 与矩阵变换的比较

| 特性 | 查找表 | 矩阵变换 |
|-----|--------|---------|
| 内存占用 | 1KB（固定） | 80 字节（20 个浮点数） |
| 计算复杂度 | O(1) 查找 | O(20) 乘法加法 |
| 表达能力 | 任意函数 | 线性函数 |
| 精度 | 8 位量化 | 浮点精度 |

**选择建议**：
- 线性变换：使用矩阵（更快，更精确）
- 非线性变换：使用查找表（更灵活）
- Gamma 校正、曲线调整：查找表更合适

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkColorTable.h` | 颜色查找表类定义 |
| `src/effects/colorfilters/SkColorFilterBase.h` | 颜色过滤器基类 |
| `src/core/SkRasterPipeline.h` | 光栅化管线 |
| `src/core/SkRasterPipelineOpContexts.h` | 定义 TablesCtx 结构 |
| `src/core/SkRasterPipelineOpList.h` | 定义 byte_tables 操作 |
| `src/effects/colorfilters/SkMatrixColorFilter.cpp` | 矩阵颜色过滤器（比较对象） |
| `include/core/SkColorFilter.h` | 颜色过滤器公共接口 |
| `src/base/SkArenaAlloc.h` | 栈分配器 |
