# SkFontHost_win

> 源文件
> - src/ports/SkFontHost_win.cpp

## 概述

`SkFontHost_win` 是 Skia 在 Windows 平台上使用 GDI（Graphics Device Interface）进行字体渲染的实现。该模块提供了基于 Windows 传统 GDI API 的字体管理和渲染功能，支持从 `LOGFONT` 结构创建字体、字形光栅化、子像素渲染（LCD）、以及与 Windows 字体系统的深度集成。

核心特点：
- **GDI 渲染后端**：使用 Windows GDI API（GetGlyphOutline、GetTextMetrics 等）
- **LOGFONT 支持**：直接使用 Windows LOGFONT 结构描述字体
- **ClearType 支持**：支持 Windows ClearType 子像素渲染
- **字体回退**：与 Windows 字体替换机制集成
- **向后兼容**：支持旧版本 Windows（Windows 7+）
- **可选 Skia 渲染**：在特定情况下使用 Skia 路径渲染器

该模块是 Windows 平台上的传统字体实现，与较新的 DirectWrite 实现（SkFontMgr_win_dw）共存，用于需要 GDI 兼容性或旧版本 Windows 支持的场景。

## 架构位置

```
SkTypeface (抽象基类)
    ↓
LogFontTypeface (本模块)
    ↓
SkScalerContext (字形缩放上下文)
    ↓
┌────────────────────┬──────────────────┐
│                    │                  │
SkScalerContext_GDI  SkScalerContext_Skia
(GDI 渲染)          (Skia 路径渲染)
    ↓                    ↓
Windows GDI API      SkPathBuilder
```

Windows 字体系统对比：
```
传统路径（本模块）:
LOGFONT → GDI API → 位图字形

现代路径:
IDWriteFont → DirectWrite → IDWriteFontFace
```

## 主要类与结构体

### LogFontTypeface
基于 LOGFONT 的 typeface 实现，继承自 `SkTypeface`。

**主要成员：**
- `fLogFont`: Windows LOGFONT 结构
- `fSerializeAsStream`: 是否序列化为流
- `fCanBeLCD`: 是否支持 LCD（ClearType）渲染

**核心方法：**
- `Make()`: 从 LOGFONT 创建 typeface（静态工厂方法）
- `EnsureAccessible()`: 确保字体可访问（触发字体加载回调）
- `onOpenStream()`: 打开字体文件流
- `onMakeClone()`: 克隆 typeface（支持可变字体参数）
- `onCreateScalerContext()`: 创建字形缩放上下文
- `onFilterRec()`: 过滤缩放记录（应用 ClearType 限制等）
- `onCountGlyphs()`: 返回字形数量
- `onGetUPEM()`: 返回 em 单位大小
- `onGetFamilyName()`: 获取家族名称
- `onGetAdvancedMetrics()`: 获取高级排版度量

### SkAutoHDC
RAII 包装器，管理 Windows 设备上下文（HDC）生命周期。

**主要成员：**
- `fHdc`: 兼容 DC 句柄
- `fFont`: HFONT 句柄
- `fSavefont`: 保存的旧字体句柄

**用途：**
- 自动创建 compatible DC
- 自动创建和选择字体
- 自动清理资源

### 辅助类型

#### SkGdiRGB
```cpp
typedef uint32_t SkGdiRGB;
```
打包的 RGB 颜色，格式为 `0x00RRGGBB`。

## 公共 API 函数

### SkTypeface_SetEnsureLOGFONTAccessibleProc()
```cpp
void SkTypeface_SetEnsureLOGFONTAccessibleProc(void (*proc)(const LOGFONT&));
```
设置字体访问回调函数，在无法访问字体时触发。

**用途：**
- 动态加载字体文件
- 触发字体下载
- 解决字体权限问题

**使用示例：**
```cpp
void MyFontLoader(const LOGFONT& lf) {
    // 加载字体文件，使其对 GDI 可见
    AddFontResourceEx(fontPath, FR_PRIVATE, 0);
}

SkTypeface_SetEnsureLOGFONTAccessibleProc(MyFontLoader);
```

### LogFontTypeface::Make()
```cpp
static sk_sp<LogFontTypeface> Make(const LOGFONT& lf);
```
从 LOGFONT 创建 typeface。

**参数：**
- `lf`: Windows LOGFONT 结构

**返回值：** typeface 智能指针

## 内部实现细节

### LOGFONT 标准化

#### make_canonical()
```cpp
static void make_canonical(LOGFONT* lf);
```
将 LOGFONT 标准化为规范形式：
- `lfHeight = -64`: 固定高度（64 像素）
- `lfWidth = 0`: 不限制宽度
- `lfQuality = CLEARTYPE_QUALITY`: 使用 ClearType
- `lfCharSet = DEFAULT_CHARSET`: 默认字符集

### 字形数量计算

#### calculateGlyphCount()
```cpp
static unsigned calculateGlyphCount(HDC hdc, const LOGFONT& lf);
```

**算法：**
1. 尝试从 `maxp` 表读取字形数量（偏移 4，2 字节）
2. 如果失败，使用二分搜索：
   - 范围：0 到 65536
   - 对每个中点调用 `GetGlyphOutlineW(..., GGO_GLYPH_INDEX, ...)`
   - 成功则向右搜索，失败则向左搜索
   - 返回第一个失败的索引

**性能：**
- 最优情况（maxp 表可用）：O(1)
- 最坏情况（二分搜索）：O(log n) ≈ 16 次调用

### EM 单位计算

#### calculateUPEM()
```cpp
static unsigned calculateUPEM(HDC hdc, const LOGFONT& lf);
```

**算法：**
1. 调用 `GetTextMetrics()` 检查是否为矢量字体
2. 如果是位图字体，返回 `tmMaxCharWidth`
3. 调用 `GetOutlineTextMetrics()` 获取 `otmEMSquare`
4. 如果失败，触发 `call_ensure_accessible()` 并重试

### 渲染路径选择

#### needToRenderWithSkia()
```cpp
static bool needToRenderWithSkia(const SkScalerContextRec& rec);
```

**选择 Skia 渲染的条件：**
1. **无 hinting 或轻微 hinting**：GDI 不支持这些模式
2. **强制旋转 AA**（可选编译）：旋转文本且尺寸较小时
3. **非轴对齐变换**：倾斜或旋转变换

**否则使用 GDI 渲染**。

### LCD 渲染支持

#### isLCD()
```cpp
static bool isLCD(const SkScalerContextRec& rec);
```
检查是否请求 LCD（ClearType）渲染。

**限制：**
- 仅支持 TrueType/OpenType 字体（矢量）
- 不支持 PostScript（立方体轮廓）字体
- 通过 `fCanBeLCD` 标志控制

### 坐标转换

Windows 使用 16.16 定点数（FIXED），Skia 使用 26.6 定点数（SkFixed）或浮点数（SkScalar）。

**转换函数：**
```cpp
static inline FIXED SkFixedToFIXED(SkFixed x);
static inline SkFixed SkFIXEDToFixed(FIXED x);
static inline FIXED SkScalarToFIXED(SkScalar x);
static inline SkScalar SkFIXEDToScalar(FIXED x);
```

这些函数通过指针类型转换实现零开销转换（前提是布局兼容）。

### 字体名称提取

#### dcfontname_to_skstring()
```cpp
static void dcfontname_to_skstring(HDC deviceContext, const LOGFONT& lf, SkString* familyName);
```

**流程：**
1. 调用 `GetTextFace(hdc, 0, nullptr)` 获取名称长度
2. 如果失败，调用 `call_ensure_accessible(lf)` 并重试
3. 调用 `GetTextFace(hdc, len, buffer)` 获取名称
4. 使用 `tchar_to_skstring()` 转换为 UTF-8（如果是 Unicode 构建）

### 文本度量

#### 固定间距检测
```cpp
// The fixed pitch bit is set if the font is *not* fixed pitch.
this->setIsFixedPitch((textMetric.tmPitchAndFamily & TMPF_FIXED_PITCH) == 0);
```

注意：Windows 的 `TMPF_FIXED_PITCH` 位的含义是"非固定间距"（命名反直觉）。

#### PostScript 字体检测
```cpp
fCanBeLCD = !((textMetric.tmPitchAndFamily & TMPF_VECTOR) &&
              (textMetric.tmPitchAndFamily & TMPF_DEVICE));
```
同时设置 `TMPF_VECTOR` 和 `TMPF_DEVICE` 表示 PostScript 字体（立方体轮廓），不支持 ClearType。

## 依赖关系

### Windows API 依赖
| API | 用途 |
|-----|------|
| **GDI32.dll** | 字形渲染和度量 |
| `CreateCompatibleDC` | 创建内存 DC |
| `CreateFontIndirect` | 从 LOGFONT 创建字体 |
| `SelectObject` | 选择字体到 DC |
| `GetGlyphOutlineW` | 获取字形轮廓或位图 |
| `GetTextMetrics` | 获取字体度量 |
| `GetOutlineTextMetrics` | 获取轮廓度量 |
| `GetTextFace` | 获取字体名称 |
| `GetFontData` | 读取字体表数据 |
| **USP10.dll** | Unicode 文本处理（可选） |

### Skia 内部依赖
| 模块 | 用途 |
|------|------|
| `SkTypeface` | typeface 抽象基类 |
| `SkScalerContext` | 字形缩放上下文 |
| `SkGlyph` | 字形数据结构 |
| `SkPath` | 矢量路径 |
| `SkMaskGamma` | Gamma 校正 |
| `SkFontMetrics` | 字体度量 |
| `SkTypefaceCache` | typeface 缓存 |
| `SkOTTable_*` | OpenType 表解析 |
| `SkMatrix22` | 2x2 矩阵 |

## 设计模式与设计决策

### 1. RAII 模式（Resource Acquisition Is Initialization）
`SkAutoHDC` 自动管理 Windows 资源生命周期，防止泄漏。

### 2. 策略模式（Strategy Pattern）
根据渲染需求选择 GDI 或 Skia 渲染器。

### 3. 适配器模式（Adapter Pattern）
将 Windows LOGFONT/GDI API 适配为 Skia 的 SkTypeface 接口。

### 4. 工厂模式（Factory Pattern）
`LogFontTypeface::Make()` 静态工厂方法创建 typeface。

### 5. 回调机制
`gEnsureLOGFONTAccessibleProc` 回调允许应用程序扩展字体加载行为。

### 6. 延迟加载
字形数据和轮廓在首次请求时才从 GDI 获取。

### 7. 防御式编程
所有 GDI API 调用都有错误检查和回退逻辑。

### 8. 性能优先
- 直接使用 GDI 位图避免路径转换
- 二分搜索字形数量
- 缓存字体度量

## 性能考量

### 1. GDI 渲染开销
- `GetGlyphOutlineW()`: 10-50μs/字形（取决于大小和复杂度）
- ClearType 渲染：比灰度慢 2-3 倍
- 缓存是关键：字形缓存命中率 > 95%

### 2. 字形数量二分搜索
- 最多 16 次 GDI 调用（log₂ 65536）
- 总时间约 160-800μs
- 仅在首次创建 typeface 时执行

### 3. LOGFONT 标准化
零开销操作，仅修改结构体字段。

### 4. 坐标转换
通过指针转换实现，零运行时开销（假设类型兼容）。

### 5. 与 DirectWrite 对比

| 特性 | GDI (本模块) | DirectWrite |
|------|-------------|-------------|
| **启动时间** | 快（<1ms） | 慢（10-100ms） |
| **渲染质量** | ClearType 好 | 更好 |
| **可变字体** | 不支持 | 完整支持 |
| **COLRv1** | 不支持 | 支持 |
| **内存占用** | 低 | 较高 |
| **兼容性** | Win7+ | Win7 SP1+ |

### 6. 优化建议
- **预加载字体**：在启动时调用 `EnsureAccessible`
- **批量字形请求**：减少 GDI 调用次数
- **缓存 typeface**：避免重复创建
- **使用 DirectWrite**：在 Win10+ 上获得更好性能

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/ports/SkTypeface_win.h` | Windows typeface 公共 API |
| `src/ports/SkFontMgr_win_dw.cpp` | DirectWrite 字体管理器（现代实现） |
| `src/ports/SkScalerContext_win_dw.cpp` | DirectWrite 缩放上下文 |
| `src/sfnt/SkOTTable_*.h` | OpenType 表结构定义 |
| `src/utils/win/SkHRESULT.h` | HRESULT 错误处理 |
| `src/core/SkScalerContext.h` | 缩放上下文基类 |
| `src/core/SkTypefaceCache.h` | typeface 缓存 |
