# SkFontMgr_empty

> 源文件: `include/ports/SkFontMgr_empty.h`

## 概述

`SkFontMgr_empty` 提供了一个工厂函数，用于创建不包含任何内置字体的空字体管理器。该管理器使用 FreeType 引擎进行渲染，但初始状态下没有可用字体。它主要用于需要完全控制字体来源、避免系统字体干扰的场景，如测试环境、嵌入式系统或自定义字体加载流程的起点。

## 架构位置

该头文件位于 `include/ports/` 目录，属于 Skia 的平台移植层(Ports Layer)。它与 `SkFontMgr_directory` 和 `SkFontMgr_data` 并列，代表最小化的字体管理器实现，可作为自定义字体加载策略的基础构建块。

## 公共 API 函数

### `SkFontMgr_New_Custom_Empty`

```cpp
SK_API sk_sp<SkFontMgr> SkFontMgr_New_Custom_Empty();
```

- **功能**: 创建一个不包含任何内置字体的空字体管理器
- **参数**: 无参数
- **返回值**: `sk_sp<SkFontMgr>` 智能指针，指向空字体管理器实例
- **行为特征**:
  - 调用 `matchFamilyStyle()` 等字体匹配方法时，通常返回空指针或回退到默认行为
  - 枚举字体族时返回空列表
  - 必须通过其他方式(如 `makeFromData()`, `makeFromFile()`)显式加载字体
- **线程安全**: 创建后的管理器可在多线程中安全使用

## 内部实现细节

### 最小化实现

空字体管理器提供 `SkFontMgr` 接口的最小实现：
- **空字体族列表**: `countFamilies()` 返回 0
- **匹配失败**: 所有字体匹配方法返回空结果
- **动态加载支持**: 支持通过 `makeFromData()` 和 `makeFromFile()` 方法动态添加字体

### FreeType 集成

尽管没有内置字体，管理器仍初始化 FreeType 库上下文：
- **延迟初始化**: FreeType 库在首次加载字体时初始化
- **共享上下文**: 动态加载的字体共享同一 FreeType 实例

### 使用场景

1. **测试隔离**: 单元测试需要确定性的字体环境，避免系统字体差异
2. **白名单字体**: 应用只允许使用特定字体，拒绝系统字体
3. **按需加载**: 根据用户选择或文档要求动态加载字体
4. **嵌入式系统**: 资源受限设备不预装任何字体
5. **组合策略**: 作为自定义字体加载链的第一环

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `SkFontMgr` | 字体管理器基类，定义标准接口 |
| `SkRefCnt` | 引用计数基础设施 |
| `sk_sp<T>` | Skia 智能指针 |
| FreeType 库 | 底层字体渲染引擎(动态加载字体时使用) |

### 被依赖的模块

典型使用场景：
- **单元测试框架**: 隔离测试环境，避免系统字体污染测试结果
- **字体沙盒**: 应用需要严格控制可用字体(如安全沙盒)
- **按需字体加载**: 游戏或应用根据关卡/场景动态加载字体
- **嵌入式GUI**: 最小化初始化开销，仅加载必需字体
- **字体回退链**: 作为多级字体管理器链的最后一环

## 设计模式与设计决策

### 工厂模式

使用全局工厂函数：
- **一致性**: 与其他 `SkFontMgr` 工厂函数命名风格一致
- **封装**: 隐藏具体实现类名
- **简洁**: 无参数构造，接口极简

### 空对象模式(Null Object Pattern)

空字体管理器实现了空对象模式的变体：
- **有效对象**: 返回的是功能完整的管理器，而非空指针
- **安全默认行为**: 不会因缺少字体而崩溃，而是返回空结果
- **可扩展**: 可以通过动态加载方法添加字体

### 组合优于继承

空管理器通常通过组合 FreeType 后端实现，而非从完整管理器派生：
- **轻量级**: 避免继承大型字体管理器的开销
- **清晰语义**: "空"的含义明确，没有隐藏的默认字体

## 性能考量

### 初始化开销

- **极低开销**: 创建空管理器几乎没有开销(不扫描目录或解析字体)
- **启动时间**: 适合对启动时间敏感的应用
- **内存占用**: 最小化内存占用(仅管理器对象本身)

### 动态加载性能

- **按需开销**: 每次调用 `makeFromData()` 或 `makeFromFile()` 都会解析字体
- **无缓存共享**: 动态加载的字体不自动添加到管理器的匹配索引中(取决于实现)
- **推荐模式**: 对于频繁使用的字体，手动缓存 `SkTypeface` 对象

### 与其他方案对比

| 管理器类型 | 初始化时间 | 内存占用 | 字体匹配性能 |
|-----------|----------|----------|-------------|
| `SkFontMgr_empty` | 极快(<1ms) | 极低(~1KB) | 不支持(需手动) |
| `SkFontMgr_directory` | 慢(10-500ms) | 中等(~1MB) | 快(O(log n)) |
| `SkFontMgr_data` | 中等(5-100ms) | 高(数据+元数据) | 快(O(log n)) |

## 平台相关说明

### 跨平台一致性

空字体管理器在所有平台上行为一致：
- **无平台依赖**: 不访问系统字体目录
- **行为统一**: 所有平台的匹配结果相同(都失败)

### 测试可移植性

特别适合跨平台测试：
```cpp
// 所有平台上结果一致
sk_sp<SkFontMgr> mgr = SkFontMgr_New_Custom_Empty();
ASSERT_TRUE(mgr->countFamilies() == 0);
ASSERT_TRUE(mgr->matchFamilyStyle("Arial", SkFontStyle()) == nullptr);
```

## 使用示例

### 基础用法

```cpp
// 创建空管理器
sk_sp<SkFontMgr> fontMgr = SkFontMgr_New_Custom_Empty();

// 确认没有字体
int familyCount = fontMgr->countFamilies();  // 返回 0

// 动态加载字体
sk_sp<SkData> fontData = SkData::MakeFromFileName("MyFont.ttf");
sk_sp<SkTypeface> typeface = fontMgr->makeFromData(fontData);

// 使用加载的字体
SkFont font(typeface, 16.0f);
canvas->drawString("Hello", 0, 0, font, paint);
```

### 测试场景

```cpp
// 单元测试：验证文本渲染在无字体时的回退行为
TEST(TextTest, NoFontFallback) {
    sk_sp<SkFontMgr> emptyMgr = SkFontMgr_New_Custom_Empty();
    sk_sp<SkTypeface> typeface = emptyMgr->matchFamilyStyle("NonExistent", SkFontStyle());

    EXPECT_TRUE(typeface == nullptr);
    // 验证应用的错误处理逻辑
}
```

### 组合字体源

```cpp
// 组合多个字体源
sk_sp<SkFontMgr> baseMgr = SkFontMgr_New_Custom_Empty();

// 逐个加载需要的字体
for (const char* path : fontPaths) {
    sk_sp<SkData> data = SkData::MakeFromFileName(path);
    baseMgr->makeFromData(data);  // 注意：标准 API 不修改管理器状态
                                   // 实际使用需要缓存 Typeface
}
```

## 设计权衡

### 优点

- **可预测性**: 行为确定，不受系统字体影响
- **轻量级**: 最小的资源占用
- **隔离性**: 完全隔离的字体环境
- **控制力**: 应用完全控制字体加载策略

### 缺点

- **额外工作**: 需要手动管理字体加载
- **无回退**: 不提供默认字体，可能导致渲染失败
- **不便性**: 对于常见字体，仍需显式加载

### 适用场景判断

选择空管理器当：
- 需要完全确定性的字体环境
- 应用字体需求简单且已知
- 资源极度受限(如微控制器)

选择其他管理器当：
- 需要支持系统字体回退
- 用户期望使用系统安装的字体
- 应用处理任意文本(如浏览器、编辑器)

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkFontMgr.h` | 字体管理器基类定义 |
| `include/ports/SkFontMgr_directory.h` | 提供预加载字体的替代方案 |
| `include/ports/SkFontMgr_data.h` | 内存数据方案 |
| `src/ports/SkFontMgr_custom_empty.cpp` | 实现文件(源代码树) |
| `include/core/SkTypeface.h` | 字体面对象 |
| `include/core/SkData.h` | 用于动态加载字体数据 |
