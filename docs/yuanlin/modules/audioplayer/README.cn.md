# audioplayer - 音频播放器模块

## 概述

`modules/audioplayer` 是 Skia 的跨平台音频播放器模块,提供了统一的音频播放抽象接口。该模块主要服务于 Skia 的动画模块 (如 skottie),用于在 Lottie 动画中播放同步的音频轨道。

`SkAudioPlayer` 是一个抽象基类,定义了音频播放器的标准操作接口:播放/暂停/停止控制、时间定位 (seek)、音量调节和播放速率控制。通过静态工厂方法 `Make(sk_sp<SkData>)` 创建平台相关的播放器实例,调用者无需关心底层实现细节。

模块支持三个播放状态 (`State` 枚举): `kPlaying`(播放中)、`kPaused`(暂停)和 `kStopped`(停止)。时间接口提供绝对时间 (`time()`, 单位秒) 和归一化时间 (`normalizedTime()`, 0到1) 两种访问方式。所有 setter 方法都返回实际设置的值,以应对底层平台的限制。

平台实现方面,模块提供了四种后端:macOS 使用 AVFoundation (`SkAudioPlayer_mac.mm`)、Android 使用 Oboe 音频库 (`SkAudioPlayer_oboe.cpp`)、桌面平台使用 SFML 音频 (`SkAudioPlayer_sfml.cpp`),以及一个空实现 (`SkAudioPlayer_none.cpp`) 作为不支持音频的平台的后备方案。

## 架构图

```
+----------------------------------+
|        SkAudioPlayer (抽象基类)   |
|  +-- Make(SkData) [工厂方法]     |
|  +-- play() / pause() / stop()  |
|  +-- setTime() / time()         |
|  +-- setVolume() / volume()     |
|  +-- setRate() / rate()         |
|  +-- State: Playing/Paused/     |
|             Stopped             |
+----------------------------------+
     |          |          |          |
     v          v          v          v
+--------+ +--------+ +--------+ +--------+
| macOS  | | Android| | SFML   | | None   |
| AVFound| | Oboe   | | 桌面   | | (空)   |
| ation  | |        | |        | |        |
| (.mm)  | | (.cpp) | | (.cpp) | | (.cpp) |
+--------+ +--------+ +--------+ +--------+
```

## 目录结构

```
modules/audioplayer/
+-- BUILD.gn                  # GN 构建配置
+-- BUILD.bazel               # Bazel 构建配置
+-- SkAudioPlayer.h           # 公共接口头文件
+-- SkAudioPlayer.cpp         # 基类实现 (状态管理/参数校验)
+-- SkAudioPlayer_mac.mm      # macOS AVFoundation 后端
+-- SkAudioPlayer_oboe.cpp    # Android Oboe 后端
+-- SkAudioPlayer_sfml.cpp    # SFML 跨平台后端
+-- SkAudioPlayer_none.cpp    # 空实现后端
```

## 关键类与函数

| 类/函数 | 文件 | 说明 |
|---------|------|------|
| `SkAudioPlayer` | `SkAudioPlayer.h` | 抽象基类,定义音频播放的完整接口 |
| `SkAudioPlayer::Make()` | `SkAudioPlayer.h` | 静态工厂方法,从 SkData 创建播放器 |
| `SkAudioPlayer::State` | `SkAudioPlayer.h` | 状态枚举: kPlaying/kStopped/kPaused |
| `duration()` | `SkAudioPlayer.h` | 获取音频总时长 (秒) |
| `time()` / `setTime()` | `SkAudioPlayer.h` | 获取/设置播放时间 (秒) |
| `normalizedTime()` | `SkAudioPlayer.h` | 获取归一化时间 (0.0 - 1.0) |
| `volume()` / `setVolume()` | `SkAudioPlayer.h` | 获取/设置音量 (0.0 - 1.0) |
| `rate()` / `setRate()` | `SkAudioPlayer.h` | 获取/设置播放速率 (1.0 = 正常) |
| `play()` / `pause()` / `stop()` | `SkAudioPlayer.h` | 便捷的状态控制方法 |
| `isPlaying()` / `isPaused()` / `isStopped()` | `SkAudioPlayer.h` | 状态查询方法 |

## 依赖关系

- **Skia Core**: `SkData` 用于传递音频数据
- **平台依赖**:
  - macOS: AVFoundation 框架
  - Android: Oboe 音频库
  - 桌面: SFML (Simple and Fast Multimedia Library)
- **被依赖**: `modules/skottie` (Lottie 动画音频轨道)、`modules/skresources` (ExternalTrackAsset)

## 设计模式分析

1. **工厂方法 (Factory Method)**: `SkAudioPlayer::Make()` 根据编译平台自动选择并创建对应的播放器实现,对调用者隐藏平台差异。

2. **模板方法 (Template Method)**: 基类 `SkAudioPlayer.cpp` 实现了参数校验和状态管理的通用逻辑 (如时间范围裁剪、NaN 检查、值变化检测),而 `onSetTime()`/`onSetState()`/`onSetRate()`/`onSetVolume()` 等虚方法由平台子类实现。

3. **空对象模式 (Null Object)**: `SkAudioPlayer_none.cpp` 提供一个什么都不做的实现,确保在不支持音频的平台上不会崩溃。

## 数据流

```
sk_sp<SkData> (音频数据)
       |
       v
SkAudioPlayer::Make(data)
  --> 创建平台特定的播放器实例
       |
       v
setState(kPlaying) --> onSetState() --> 平台音频 API 开始播放
       |
       v
setTime(t) --> 参数校验 (0 <= t <= duration)
  --> onSetTime(t) --> 平台 seek 操作
       |
       v
setVolume(v) --> 参数校验 (0 <= v <= 1, 非 NaN)
  --> onSetVolume(v) --> 平台音量设置
```

## 相关文档与参考

- Skia Lottie 动画: `modules/skottie/`
- 资源管理 (ExternalTrackAsset): `modules/skresources/include/SkResources.h`
- Oboe 音频库: https://github.com/google/oboe
- SFML 音频: https://www.sfml-dev.org/
