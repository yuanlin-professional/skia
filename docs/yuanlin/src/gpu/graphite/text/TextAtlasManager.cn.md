# TextAtlasManager -- 文本图集管理器

> 源文件:
> - `src/gpu/graphite/text/TextAtlasManager.h`
> - `src/gpu/graphite/text/TextAtlasManager.cpp`

## 概述

TextAtlasManager 管理 Graphite 中用于字形渲染的 DrawAtlas 的生命周期和访问。它维护三种遮罩格式（A8、565、ARGB）的图集,处理字形到图集的上传、图集空间的分配与回收,以及图集纹理代理的提供。该类是 Graphite 文本渲染管线的核心组件。

## 架构位置

```
AtlasProvider
  -> TextAtlasManager  <-- 本模块
       -> DrawAtlas[3] (A8, 565, ARGB)
       -> TextureProxy (图集纹理)
       -> Recorder (上传管理)
```

## 主要类与结构体

### AtlasConfig

```cpp
class AtlasConfig {
    SkISize fARGBDimensions;
    int fMaxTextureSize;
    static constexpr int kMaxAtlasDim = 2048;
};
```
根据 `maxTextureSize` 和 `maxBytes` 计算各格式图集和绘图区域的尺寸:
- ARGB 尺寸从 256x256 到 2048x1024（按内存预算对数选择）
- A8 尺寸为 ARGB 的 2 倍（因为最常用）
- A8 绘图区域在大纹理时增大到 512x512 以容纳 SDF 字形

### TextAtlasManager

```cpp
class TextAtlasManager : public DrawAtlas::GenerationCounter {
    Recorder* fRecorder;
    DrawAtlas::AllowMultitexturing fAllowMultitexturing;
    std::unique_ptr<DrawAtlas> fAtlases[kMaskFormatCount];  // 3 种格式
    bool fSupportBilerpAtlas;
    AtlasConfig fAtlasConfig;
};
```

## 公共 API 函数

### getProxies -- 获取图集纹理代理
```cpp
const sk_sp<TextureProxy>* getProxies(MaskFormat format, unsigned int* numActiveProxies);
```
初始化图集（如需要）并返回纹理代理数组。

### addGlyphToAtlas
```cpp
DrawAtlas::ErrorCode addGlyphToAtlas(const SkGlyph&, GlyphEntry*, int srcPadding);
```
将字形图像添加到图集,返回成功/重试/错误状态。

### addGlyphToBulkAndSetUseToken
```cpp
void addGlyphToBulkAndSetUseToken(DrawAtlas::BulkUsePlotUpdater*, MaskFormat, const GlyphEntry&, Token);
```
批量更新图集使用令牌,防止活跃字形被逐出。

### recordUploads / compact / freeGpuResources / evictAtlases
图集维护操作:记录上传、压缩空间、释放 GPU 资源、清空所有绘图区域。

## 内部实现细节

### 字形图像处理

`get_packed_glyph_image` 处理字形数据的格式转换:
1. **格式匹配**: 直接拷贝（考虑行字节对齐）
2. **BW 扩展**: 1 位掩码扩展为 8 位或 16 位
3. **565 -> ARGB 转换**: Intel macOS Metal 不支持 565 格式时,转换为 8888 格式（考虑 BGRA 本机字节序）

### 填充处理

| srcPadding | 用途 | 实际填充 |
|------------|------|----------|
| 0 | 直接遮罩/图像 | 0（除非 `fSupportBilerpAtlas` 则为 1） |
| 1 | 变换遮罩/图像 | 1 |
| SK_DistanceFieldInset | SDF | 0（填充已在图像中） |

### 格式解析

```cpp
MaskFormat resolveMaskFormat(MaskFormat format) const;
```
当 565 格式不被当前设备支持时（如 Intel macOS Metal），自动升级为 ARGB。

### 图集初始化

惰性创建,首次访问时根据 `AtlasConfig` 配置创建 `DrawAtlas`,标签为 `"TextAtlas"`。

### 多纹理支持

当 `allowMultipleAtlasTextures` 且着色器支持 32 位浮点或整数纹理坐标时启用,允许图集扩展到多个纹理页。

## 依赖关系

- `DrawAtlas` -- 图集分配和管理
- `DrawAtlas::GenerationCounter` -- 基类,提供代计数器
- `Recorder` -- 上传管理和能力查询
- `TextureProxy` -- 图集纹理代理
- `GlyphData` / `GlyphEntry` -- 字形数据
- `SkGlyph` / `SkStrikeSpec` -- 字形来源

## 设计模式与设计决策

1. **三图集策略**: 不同遮罩格式使用独立图集,A8 图集最大（2x ARGB）因为最常用。
2. **代计数器继承**: 作为 `GenerationCounter` 的子类,为所有图集提供统一的代序号管理。
3. **格式回退**: 565 -> ARGB 的自动回退对上层完全透明,数据转换在底层处理。
4. **双线性填充**: `fSupportBilerpAtlas` 控制是否为直接遮罩添加 1 像素填充,支持图集中的双线性采样。

## 性能考量

- `SkAutoSMalloc<1024>` 使用栈上小缓冲区存储临时字形数据,减少堆分配。
- 批量使用令牌更新（`BulkUsePlotUpdater`）减少逐字形的令牌更新开销。
- 2048x2048 最大图集尺寸限制确保半精度纹理坐标不溢出。
- 绘图区域尺寸根据图集大小自适应,大图集使用更大绘图区域以容纳 SDF 字形。
- `compact()` 允许释放不再使用的图集页面。

## 相关文件

- `src/gpu/graphite/DrawAtlas.h` -- 图集实现
- `src/gpu/graphite/text/GlyphData.h` -- 字形数据管理
- `src/gpu/graphite/text/TextStrike.h` -- 文本打击缓存
- `src/gpu/graphite/AtlasProvider.h` -- 图集提供者
- `src/text/gpu/GlyphUtils.h` -- 字形工具函数
