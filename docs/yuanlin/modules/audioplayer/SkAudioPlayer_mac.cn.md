# SkAudioPlayer_mac

> 源文件: modules/audioplayer/SkAudioPlayer_mac.mm

## 概述

`SkAudioPlayer_mac.mm` 是 `SkAudioPlayer` 基于 Apple AVFoundation 框架的原生实现，支持 macOS 和 iOS 平台。该实现使用 Objective-C++ 语言（`.mm` 扩展名）调用 Cocoa 框架的 `AVAudioPlayer` 类，提供高质量、低延迟的音频播放功能。

`AVAudioPlayer` 是 Apple 提供的高级音频播放 API，自动处理音频格式解码、缓冲管理、音频会话配置等细节。相比其他平台实现，该实现代码简洁（85 行），功能完整，且充分利用了 Apple 平台的音频基础设施。

**核心特性：**
- 支持多种音频格式（AAC, MP3, WAV, AIFF, CAF 等 iOS/macOS 原生支持的格式）
- 完整的播放控制（播放、暂停、停止、时间跳转）
- 变速播放（不改变音高）
- 音量控制（0.0 - 1.0）
- 自动内存管理（通过 ARC 或手动引用计数）

## 架构位置

该文件位于 Skia 音频播放模块的平台实现层：

```
modules/audioplayer/
├── SkAudioPlayer.h/cpp              (抽象基类)
├── SkAudioPlayer_oboe.cpp           (Android Oboe 实现)
├── SkAudioPlayer_sfml.cpp           (SFML 跨平台实现)
├── SkAudioPlayer_mac.mm             (macOS/iOS 实现) ← 当前文件
└── SkAudioPlayer_none.cpp           (空实现)
```

**依赖关系图：**
```
SkAudioPlayer_Mac
├── SkAudioPlayer           (继承抽象基类)
├── AVAudioPlayer           (AVFoundation 音频播放器)
├── NSData                  (Foundation 数据容器)
└── sk_sp<SkData>           (Skia 数据容器)
```

该实现作为 Apple 平台和 Skia 跨平台代码之间的桥梁，将 Objective-C API 适配到 C++ 接口。

## 主要类与结构体

### SkAudioPlayer_Mac 类

继承自 `SkAudioPlayer` 的 Apple 平台实现类。

**成员变量：**
```cpp
AVAudioPlayer*  fPlayer;     // AVFoundation 音频播放器对象
sk_sp<SkData>   fData;       // Skia 数据容器（保持数据有效）
```

**关键设计点：**
- `fPlayer` 是 Objective-C 对象指针，需要手动管理引用计数（在非 ARC 环境）
- `fData` 持有音频数据的所有权，因为 `NSData` 使用 `initWithBytesNoCopy:freeWhenDone:NO` 不复制数据

### AVAudioPlayer (Apple 框架类)

AVFoundation 提供的高级音频播放类，主要属性和方法：

**属性：**
```objc
@property(readonly) NSTimeInterval duration;       // 总时长（秒）
@property NSTimeInterval currentTime;              // 当前播放位置（秒）
@property float volume;                            // 音量 (0.0 - 1.0)
@property float rate;                              // 播放速率 (0.5 - 2.0)
@property BOOL enableRate;                         // 启用速率控制
```

**方法：**
```objc
- (instancetype)initWithData:(NSData *)data error:(NSError **)outError;
- (BOOL)prepareToPlay;       // 预加载缓冲区
- (BOOL)play;                // 开始播放
- (void)pause;               // 暂停播放
- (void)stop;                // 停止播放（重置到开头）
```

## 公共 API 函数

### SkAudioPlayer::Make (工厂方法)
```cpp
std::unique_ptr<SkAudioPlayer> SkAudioPlayer::Make(sk_sp<SkData> src)
```

**功能：** 创建 Apple 平台音频播放器实例
**参数：** `src` - 包含音频数据的 `SkData` 对象
**返回值：** 成功返回播放器实例，失败返回 `nullptr`

**实现逻辑：**

1. **创建 NSData 包装器**
   ```objc
   NSData* data = [[NSData alloc] initWithBytesNoCopy:const_cast<void*>(src->data())
                                               length:src->size()
                                         freeWhenDone:NO];
   ```
   - `initWithBytesNoCopy` - 不复制数据，仅保存指针
   - `freeWhenDone:NO` - 不负责释放内存（由 `fData` 管理）
   - `const_cast` - Apple API 不接受 const 指针，但实际不会修改数据

2. **创建 AVAudioPlayer**
   ```objc
   AVAudioPlayer* player = [[AVAudioPlayer alloc] initWithData:data error:nil];
   ```
   - 自动检测音频格式并初始化解码器
   - `error:nil` - 忽略错误详情，通过返回值判断成功/失败

3. **释放 NSData**
   ```objc
   [data release];
   ```
   - `AVAudioPlayer` 已经保存了数据引用，临时包装器可以释放

4. **创建 C++ 对象**
   ```cpp
   if (player) {
       return std::unique_ptr<SkAudioPlayer>(new SkAudioPlayer_Mac(player, std::move(src)));
   }
   return nullptr;
   ```

## 内部实现细节

### 构造函数
```cpp
SkAudioPlayer_Mac(AVAudioPlayer* player, sk_sp<SkData> data)
    : fPlayer(player)
    , fData(std::move(data))
{
    fPlayer.enableRate = YES;       // 启用速率控制
    [fPlayer prepareToPlay];        // 预加载音频缓冲区
}
```

**初始化步骤：**
1. 保存 `AVAudioPlayer` 对象指针
2. 转移 `SkData` 所有权（通过 `std::move`）
3. 启用速率控制功能（默认禁用）
4. 调用 `prepareToPlay` 预加载解码器和缓冲区，减少播放延迟

### 析构函数
```cpp
~SkAudioPlayer_Mac() override {
 //   [fPlayer release];  // 已注释
}
```

**内存管理问题：**
- 注释的 `[fPlayer release]` 表明代码可能在 ARC 和非 ARC 环境之间转换过
- 如果使用 ARC（Automatic Reference Counting），编译器自动管理引用计数
- 如果不使用 ARC，注释的代码会导致内存泄漏

**修正建议：**
```cpp
~SkAudioPlayer_Mac() override {
#if !__has_feature(objc_arc)
    [fPlayer release];
#endif
}
```

### 虚函数实现

#### onGetDuration - 获取总时长
```cpp
double onGetDuration() const override {
    return [fPlayer duration];
}
```
直接返回 `AVAudioPlayer` 的 `duration` 属性（`NSTimeInterval` 即 `double` 类型）。

#### onGetTime - 获取当前位置
```cpp
double onGetTime() const override {
    return fPlayer.currentTime;
}
```
使用 Objective-C 点语法访问 `currentTime` 属性。

#### onSetTime - 设置播放位置
```cpp
double onSetTime(double t) override {
    bool wasPlaying = this->isPlaying();
    if (wasPlaying) {
        [fPlayer pause];
    }
    fPlayer.currentTime = t;
    if (wasPlaying) {
        [fPlayer play];
    }
    return fPlayer.currentTime;
}
```

**特殊处理：**
- 如果正在播放，需要先暂停再设置时间，最后恢复播放
- 这是因为 `AVAudioPlayer` 在播放状态下修改 `currentTime` 可能导致音频故障
- 返回实际设置的时间（可能因格式限制略有偏差）

#### onSetState - 状态控制
```cpp
State onSetState(State state) override {
    switch (state) {
        case State::kPlaying: [fPlayer play];  break;
        case State::kStopped: [fPlayer stop];  break;
        case State::kPaused:  [fPlayer pause]; break;
    }
    return state;
}
```

**状态映射：**
- `kPlaying` → `play` - 开始或恢复播放
- `kStopped` → `stop` - 停止并重置到开头
- `kPaused` → `pause` - 暂停（保持当前位置）

**与 SFML 的区别：** `stop` 会重置播放位置，而 SFML 的实现一致。

#### onSetRate - 设置播放速率
```cpp
float onSetRate(float r) override {
    fPlayer.rate = r;
    return r;
}
```

**速率范围：**
- Apple 官方支持 `0.5` - `2.0` 范围
- 超出范围可能被钳制或导致错误
- 需要在构造函数中设置 `enableRate = YES` 才能生效

**音高保持：** `AVAudioPlayer` 的 `rate` 属性会保持音高，不会产生"花栗鼠效应"（与 SFML 的 `setPitch` 不同）。

#### onSetVolume - 设置音量
```cpp
float onSetVolume(float v) override {
    fPlayer.volume = v;
    return v;
}
```

**音量范围：** `0.0` - `1.0`，与 `SkAudioPlayer` 接口完全一致，无需转换。

## 依赖关系

**Apple 框架依赖：**
- `<AVFoundation/AVFoundation.h>` (macOS) - 音视频处理框架
- `<UIKit/UIKit.h>` (iOS，未明确包含但可能隐式依赖) - iOS 用户界面框架

**Skia 内部依赖：**
- `include/core/SkData.h` - 数据容器
- `modules/audioplayer/SkAudioPlayer.h` - 抽象基类

**系统依赖：**
- CoreAudio 框架（AVFoundation 底层依赖）
- AudioToolbox 框架（音频格式解码器）

**平台宏定义：**
```cpp
#if defined(SK_BUILD_FOR_MAC) || defined(SK_BUILD_FOR_IOS)
```
该文件仅在 macOS 或 iOS 平台编译。

## 设计模式与设计决策

### 1. 适配器模式
将 Objective-C 的 `AVAudioPlayer` API 适配到 C++ 的 `SkAudioPlayer` 接口：
```cpp
double onGetTime() const override {
    return fPlayer.currentTime;    // ObjC 属性 → C++ 方法
}
```

### 2. 桥接模式
该类作为 Objective-C 和 C++ 之间的桥梁，使用 Objective-C++ 语言特性。

### 3. RAII + 引用计数混合
- C++ 侧使用 `unique_ptr` 和 `sk_sp` 管理生命周期
- Objective-C 侧使用引用计数（`retain`/`release`）或 ARC

### 4. 零拷贝设计
```objc
initWithBytesNoCopy:freeWhenDone:NO
```
避免复制音频数据，通过共享内存提高性能。

### 5. 委托所有权
`fData` 持有数据所有权，`NSData` 和 `AVAudioPlayer` 仅持有指针，确保数据在播放器生命周期内有效。

### 6. 条件编译适配
```cpp
#ifdef SK_BUILD_FOR_MAC
#include <AVFoundation/AVFoundation.h>
#endif

#ifdef SK_BUILD_FOR_IOS
// ???
#endif
```
预留 iOS 特殊处理逻辑（当前未实现）。

## 性能考量

### 1. 低延迟播放
- `prepareToPlay` 预加载缓冲区，减少播放启动延迟（通常 < 5ms）
- AVFoundation 使用 CoreAudio 的低延迟路径

### 2. 零拷贝内存管理
音频数据在 `SkData`、`NSData`、`AVAudioPlayer` 之间共享，避免多次复制：
```
SkData (原始内存)
  ↓ (指针共享)
NSData (临时包装)
  ↓ (指针共享)
AVAudioPlayer (解码器)
```

### 3. 硬件加速解码
Apple 平台的音频解码器可能使用硬件加速（如 AAC 硬件解码）。

### 4. 音频会话管理
`AVAudioPlayer` 自动管理音频会话，处理：
- 与其他应用的音频混音
- 硬件音频路由（扬声器/耳机切换）
- 电话打断处理

### 5. 变速播放开销
`rate` 属性使用时间拉伸算法保持音高，需要额外的 DSP 处理：
- `rate = 1.0` - 无额外开销
- `rate ≠ 1.0` - 需要实时重采样和时间拉伸

### 6. 潜在优化
- **预加载** - 在应用启动时预加载常用音效
- **缓存播放器** - 复用播放器实例避免重复创建
- **音频会话配置** - 根据应用类型配置音频会话（游戏/音乐/通话）

## 相关文件

**同模块文件：**
- `modules/audioplayer/SkAudioPlayer.h` - 抽象基类
- `modules/audioplayer/SkAudioPlayer.cpp` - 公共实现
- `modules/audioplayer/SkAudioPlayer_oboe.cpp` - Android 实现
- `modules/audioplayer/SkAudioPlayer_sfml.cpp` - SFML 实现
- `modules/audioplayer/SkAudioPlayer_none.cpp` - 空实现

**Apple 官方文档：**
- AVAudioPlayer 类参考: https://developer.apple.com/documentation/avfoundation/avaudioplayer
- AVFoundation 编程指南: https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/AVFoundationPG/
- Audio Session 编程指南: https://developer.apple.com/library/archive/documentation/Audio/Conceptual/AudioSessionProgrammingGuide/

**构建配置：**
- `modules/audioplayer/BUILD.gn` - 根据 `SK_BUILD_FOR_MAC` 或 `SK_BUILD_FOR_IOS` 选择此文件
- 需要链接 AVFoundation 框架：`-framework AVFoundation`

**使用场景：**
- **macOS 桌面应用** - 推荐使用（原生 API，性能最佳）
- **iOS 应用** - 理论支持，但代码中 iOS 部分未完成（注释 `// ???`）
- **Skottie 动画** - 在 Apple 平台播放动画背景音乐
- **Viewer 工具** - macOS 版本的音频演示

**已知问题：**
1. **内存管理** - 析构函数中的 `[fPlayer release]` 被注释，可能导致泄漏
2. **iOS 支持不完整** - iOS 分支代码未实现
3. **错误处理** - `initWithData:error:` 传入 `nil` 忽略错误详情
4. **线程安全** - 未明确说明是否线程安全（AVAudioPlayer 本身不是线程安全的）
5. **速率范围** - 未验证输入范围，超出 0.5-2.0 可能导致未定义行为

**改进建议：**
```cpp
// 1. 修复内存管理
~SkAudioPlayer_Mac() override {
#if !__has_feature(objc_arc)
    [fPlayer release];
#endif
}

// 2. 添加错误处理
NSError* error = nil;
AVAudioPlayer* player = [[AVAudioPlayer alloc] initWithData:data error:&error];
if (!player) {
    NSLog(@"Failed to create audio player: %@", error);
    return nullptr;
}

// 3. 钳制速率范围
float onSetRate(float r) override {
    r = std::clamp(r, 0.5f, 2.0f);
    fPlayer.rate = r;
    return r;
}
```
