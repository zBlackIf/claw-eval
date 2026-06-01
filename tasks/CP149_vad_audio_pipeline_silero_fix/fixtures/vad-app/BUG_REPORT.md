# VAD 语音打断功能 - Bug 报告

## 现象

用户反馈: "我说话了，语音概率根本没有变化，一直是0%"

## 期望行为

TTS 在播放的过程中，当检测到麦克风有人说话（概率超过阈值），就暂停 TTS 播放。

## 技术栈

- Electron 30 + Vue 3 + TypeScript
- Silero VAD v4 模型 (ONNX Runtime Web)
- Web Audio API (AudioContext, AnalyserNode)

## 音频管线

```
Microphone (48kHz) → MediaStreamSource → AnalyserNode → getFloatTimeDomainData
  → resample to 16kHz → SileroVADService.process() → probability (0-1)
  → threshold comparison → triggerVoice / triggerSilence
```

## 初步诊断

诊断脚本测试发现:
- Silero 模型加载成功 (sileroReady=true)
- 但 AnalyserNode 读取的音频振幅极低: vadMaxAmp=0.0003~0.0009
- 即使大声说话，概率也只有 4.72%

## 相关代码

- `src/composables/live-vad/VADController.ts` - 音频采集和 VAD 控制
- `src/composables/live-vad/SileroVADService.ts` - Silero VAD 推理
- `src/composables/live-vad/types.ts` - 配置和类型定义
