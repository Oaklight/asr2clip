# 语音活动检测

语音活动检测（VAD）可在您停止说话时自动触发转录。

## 启用 VAD

```bash
asr2clip --vad
```

启用 VAD 后，转录在以下情况触发：

1. 检测到语音（音频高于阈值）
2. 随后是静音（音频低于阈值持续指定时长）

## 自适应阈值

默认情况下，VAD 使用自适应阈值，实时根据环境噪音调整：

```bash
# 使用 --vad 时默认启用自适应
asr2clip --vad

# 禁用自适应阈值（使用固定值）
asr2clip --vad --no_adaptive
```

## 校准

测量环境噪音以设置合适的阈值：

```bash
asr2clip --calibrate
```

这会录制一小段环境噪音并建议一个阈值。

## 自定义设置

```bash
# 自定义静音阈值和时长
asr2clip --vad --silence_threshold 0.005 --silence_duration 2.0
```

## VAD 选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--vad` | — | 启用语音活动检测 |
| `--adaptive` | 开启（使用 `--vad` 时） | 自适应阈值调整 |
| `--no_adaptive` | — | 禁用自适应阈值 |
| `--silence_threshold` | 0.01 | 静音 RMS 阈值 |
| `--silence_duration` | 1.5 秒 | 触发转录的静音时长 |
| `--calibrate` | — | 从环境噪音校准阈值 |
