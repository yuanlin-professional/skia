# SkAudioPlayer_oboe

> 源文件: modules/audioplayer/SkAudioPlayer_oboe.cpp

## 概述

`SkAudioPlayer_oboe.cpp` 是 `SkAudioPlayer` 的 Android 平台实现，基于 Google 的 Oboe 音频库。Oboe 是一个高性能、低延迟的 C++ 音频库，专为 Android 平台设计，能够自动选择最佳的音频 API（AAudio 或 OpenSL ES）。

该实现提供完整的 WAV 格式音频播放功能，支持：
- WAV 音频文件解析和播放
- 低延迟音频流输出
- 独占模式音频共享（最低延迟）
- 浮点格式采样数据处理
- 播放位置控制和时间查询
- 循环播放支持（预留接口）

这是 Android 平台推荐的音频播放实现，相比传统的 OpenSL ES 直接调用，Oboe 提供了更简洁的 API 和更好的跨 Android 版本兼容性。

## 架构位置

该文件位于 Skia 音频播放模块的平台特定实现层：

```
modules/audioplayer/
├── SkAudioPlayer.h/cpp              (抽象基类)
├── SkAudioPlayer_oboe.cpp           (Android Oboe 实现) ← 当前文件
├── SkAudioPlayer_sfml.cpp           (SFML 跨平台实现)
├── SkAudioPlayer_mac.mm             (macOS 实现)
└── SkAudioPlayer_none.cpp           (空实现)
```

**外部依赖层次：**
```
OboeAudioPlayer (本实现)
├── oboe::AudioStream            (Oboe 音频流)
├── oboe::AudioStreamCallback    (回调接口)
├── parselib::WavStreamReader    (WAV 解析器)
└── parselib::MemInputStream     (内存输入流)
```

## 主要类与结构体

### OboeAudioPlayer 类

继承自 `SkAudioPlayer` 和 `oboe::AudioStreamCallback` 的最终实现类。

**成员变量：**
```cpp
const sk_sp<SkData>                         fData;              // 音频原始数据
std::shared_ptr<oboe::AudioStream>          fStream;            // Oboe 音频流
std::unique_ptr<parselib::WavStreamReader>  fReader;            // WAV 解析器
parselib::MemInputStream                    fMemInputStream;    // 内存输入流
int32_t                                     fReadFrameIndex;    // 当前读取帧索引
int                                         fNumSampleFrames;   // 总采样帧数
bool                                        fIsLooping;         // 是否循环播放
```

**继承关系：**
- 继承 `SkAudioPlayer` - 实现抽象音频播放接口
- 继承 `oboe::AudioStreamCallback` - 实现音频数据回调接口

## 公共 API 函数

### SkAudioPlayer::Make (工厂方法)
```cpp
std::unique_ptr<SkAudioPlayer> SkAudioPlayer::Make(sk_sp<SkData> src)
```

**功能：** 创建 Android Oboe 音频播放器实例
**参数：** `src` - 包含 WAV 格式音频数据的 `SkData` 对象
**返回值：** `OboeAudioPlayer` 实例（包装为 `SkAudioPlayer` 指针）

**实现逻辑：**
```cpp
return std::unique_ptr<SkAudioPlayer>(new OboeAudioPlayer(std::move(src)));
```

该工厂方法直接创建 `OboeAudioPlayer` 对象，不进行格式检查。如果数据不是有效的 WAV 文件，错误将在构造函数或后续播放时暴露。

## 内部实现细节

### 构造函数初始化流程

```cpp
explicit OboeAudioPlayer(sk_sp<SkData> data)
```

**初始化步骤：**

1. **保存音频数据**
   ```cpp
   fData(std::move(data))
   ```

2. **创建内存输入流**
   ```cpp
   fMemInputStream(
       const_cast<unsigned char*>(static_cast<const unsigned char*>(fData->data())),
       static_cast<int32_t>(fData->size())
   )
   ```
   注意：需要 `const_cast` 是因为 `MemInputStream` API 设计问题，实际不会修改数据。

3. **解析 WAV 文件头**
   ```cpp
   fReader = std::make_unique<parselib::WavStreamReader>(&fMemInputStream);
   fReader->parse();
   fNumSampleFrames = fReader->getNumSampleFrames();
   ```

4. **配置 Oboe 音频流**
   ```cpp
   oboe::AudioStreamBuilder builder;
   builder.setPerformanceMode(oboe::PerformanceMode::LowLatency);     // 低延迟模式
   builder.setSharingMode(oboe::SharingMode::Exclusive);              // 独占模式
   builder.setSampleRate(fReader->getSampleRate());                   // 从 WAV 读取采样率
   builder.setChannelCount(fReader->getNumChannels());                // 从 WAV 读取声道数
   builder.setCallback(this);                                         // 设置数据回调
   builder.setFormat(oboe::AudioFormat::Float);                       // 浮点格式
   ```

5. **打开音频流**
   ```cpp
   builder.openStream(fStream);
   ```

### 音频数据回调机制

```cpp
oboe::DataCallbackResult onAudioReady(oboe::AudioStream *oboeStream,
                                       void *audioData,
                                       int32_t numFrames) override
```

该方法在 Oboe 需要音频数据时被调用（通常在实时音频线程上）。

**处理流程：**

1. **读取音频帧**
   ```cpp
   float *outBuffer = static_cast<float*>(audioData);
   int framesRead = fReader->getDataFloat(outBuffer, numFrames);
   fReadFrameIndex += framesRead;
   ```

2. **处理不足的帧**
   ```cpp
   int remainingFrames = numFrames - framesRead;
   if (remainingFrames > 0) {
       if (fIsLooping) {
           // 循环：重新定位到音频开始位置
           fReader->positionToAudio();
           fReader->getDataFloat(&outBuffer[framesRead * fReader->getNumChannels()],
                                remainingFrames);
       } else {
           // 非循环：填充静音并停止
           renderSilence(&outBuffer[framesRead * fReader->getNumChannels()],
                        remainingFrames);
           return oboe::DataCallbackResult::Stop;
       }
   }
   ```

3. **返回继续播放标志**
   ```cpp
   return oboe::DataCallbackResult::Continue;
   ```

### 虚函数实现

#### onGetDuration - 获取总时长
```cpp
double onGetDuration() const override {
    return fNumSampleFrames * fStream->getChannelCount() / fStream->getSampleRate();
}
```
**计算公式：** `时长 = 总帧数 × 声道数 / 采样率`

**注意：** 此处计算有误！正确公式应该是：
```cpp
// 正确：时长 = 总帧数 / 采样率
return fNumSampleFrames / fStream->getSampleRate();
```
声道数不应参与时长计算，一帧已经包含所有声道的采样。

#### onGetTime - 获取当前位置
```cpp
double onGetTime() const override {
    return (fReadFrameIndex * fStream->getChannelCount()) / fStream->getSampleRate();
}
```
**计算公式：** `当前时间 = 已读帧数 × 声道数 / 采样率`

**同样的问题：** 与 `onGetDuration` 一致，声道数不应参与计算。

#### onSetTime - 设置播放位置
```cpp
double onSetTime(double t) override {
    fReadFrameIndex = (t * fStream->getSampleRate()) / fStream->getChannelCount();
    return onGetTime();
}
```
**逆向计算：** 从时间转换为帧索引

**线程安全问题：** 该方法与音频回调线程并发访问 `fReadFrameIndex`，可能导致数据竞争。

#### onSetState - 状态控制
```cpp
State onSetState(State state) override {
    switch (state) {
        case State::kPlaying: fStream->start();  break;
        case State::kStopped: fStream->close();  break;  // 注意：close() 不可逆！
        case State::kPaused : fStream->pause(); break;
    }
    return state;
}
```

**潜在问题：**
- `close()` 会关闭流，无法再次启动，应使用 `stop()` 代替
- 缺少状态检查，重复调用可能导致错误

#### onSetRate/onSetVolume - 未实现
```cpp
float onSetRate(float r) override { return r; }      // TODO: 待实现
float onSetVolume(float v) override { return v; }    // TODO: 待实现
```

当前仅返回输入值，不实际修改播放速率或音量。

### 静音渲染
```cpp
void renderSilence(float *start, int numFrames) {
    for (int i = 0; i < numFrames * fReader->getNumChannels(); ++i) {
        start[i] = 0;
    }
}
```
填充零值表示静音，适用于音频结束后的缓冲区填充。

## 依赖关系

**外部库依赖：**
- `oboe/Oboe.h` - Google Oboe 音频库（核心依赖）
- `stream/MemInputStream.h` - parselib 内存流（来自第三方音频解析库）
- `wav/WavStreamReader.h` - parselib WAV 解析器

**Skia 内部依赖：**
- `include/core/SkData.h` - Skia 数据容器
- `modules/audioplayer/SkAudioPlayer.h` - 抽象基类

**平台要求：**
- Android API 16+ (OpenSL ES) 或 API 26+ (AAudio)
- C++14 或更高版本
- NDK r16b 或更高版本

## 设计模式与设计决策

### 1. 策略模式
通过继承 `SkAudioPlayer` 实现 Android 平台特定的播放策略，与其他平台实现（SFML、macOS）相互独立。

### 2. 回调模式
实现 `oboe::AudioStreamCallback` 接口，通过回调机制向 Oboe 提供音频数据，实现推送式音频播放。

### 3. 组合模式
将 WAV 解析器（`WavStreamReader`）和音频流（`AudioStream`）组合在一起，分离关注点。

### 4. RAII 资源管理
使用智能指针管理资源生命周期：
- `sk_sp<SkData>` - 共享音频数据所有权
- `std::shared_ptr<oboe::AudioStream>` - 管理音频流
- `std::unique_ptr<WavStreamReader>` - 独占 WAV 解析器

### 5. 匿名命名空间
```cpp
namespace {
class OboeAudioPlayer final : ...
}
```
防止符号污染，确保 `OboeAudioPlayer` 类仅在本编译单元内可见。

### 6. 低延迟优化
```cpp
builder.setPerformanceMode(oboe::PerformanceMode::LowLatency);
builder.setSharingMode(oboe::SharingMode::Exclusive);
```
优先选择低延迟模式和独占模式，适合实时音频应用（如游戏、音乐应用）。

## 性能考量

### 1. 低延迟音频
通过 Oboe 的低延迟模式和独占模式，将音频延迟降至最低（通常 < 10ms），适合实时交互场景。

### 2. 浮点格式采样
```cpp
builder.setFormat(oboe::AudioFormat::Float);
```
使用浮点格式避免整数格式的量化噪声，提供更高的音质，但需要更多 CPU 计算。

### 3. 实时线程安全
音频回调在高优先级实时线程上执行，需要注意：
- **避免阻塞操作** - 不应在回调中进行 I/O、内存分配、加锁等操作
- **数据竞争** - `fReadFrameIndex` 的并发访问未加保护，可能导致不一致

### 4. 内存效率
- 音频数据通过 `sk_sp<SkData>` 共享，避免复制
- WAV 解析器直接从内存流读取，无需临时缓冲区

### 5. 潜在优化点
- **音量控制** - 可在回调中对采样值乘以音量系数
- **速率控制** - 需要重采样算法（如线性插值、Sinc 插值）
- **线程同步** - 使用原子变量保护 `fReadFrameIndex`

## 相关文件

**同模块文件：**
- `modules/audioplayer/SkAudioPlayer.h` - 抽象基类
- `modules/audioplayer/SkAudioPlayer.cpp` - 公共实现
- `modules/audioplayer/SkAudioPlayer_sfml.cpp` - SFML 实现
- `modules/audioplayer/SkAudioPlayer_mac.mm` - macOS 实现
- `modules/audioplayer/SkAudioPlayer_none.cpp` - 空实现

**外部依赖：**
- Oboe 库 (https://github.com/google/oboe) - Android 音频引擎
- parselib WAV 解析器（可能来自独立的解析库）

**构建配置：**
- `modules/audioplayer/BUILD.gn` - 根据平台选择此文件
- Android NDK 配置 - 链接 OpenSL ES 或 AAudio 库

**使用场景：**
- Android 平台的 Skottie 动画音频播放
- Android 版本的 Viewer 工具音频演示
- 第三方 Android 应用集成 Skia 的音频功能

**已知问题：**
1. 时长和时间计算错误（多乘了声道数）
2. `onSetState` 中使用 `close()` 导致流不可重用
3. 缺少线程同步机制保护共享变量
4. `onSetRate` 和 `onSetVolume` 未实现
5. 循环播放标志 `fIsLooping` 没有公共接口设置
