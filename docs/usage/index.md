# 使用指南

asr2clip 提供多种录音模式以适应不同使用场景。

## 录音模式

- **[基本用法](basic.md)** — 单次录音和文件转录
- **[持续录音模式](continuous-mode.md)** — 自动分段的长时间录音
- **[语音活动检测](vad.md)** — 停止说话时自动转录
- **[本地 ASR 服务器](local-asr.md)** — 基于 sherpa-onnx 的离线转录

## 命令行参考

```
用法: asr2clip [-h] [-v] [-c FILE] [-q] [-i FILE] [-o FILE] [--test]
               [--list_devices] [--device DEV] [-e] [--generate_config]
               [--print_config] [--vad] [--interval SEC] [--adaptive]
               [--calibrate] [--silence_threshold RMS]
               [--silence_duration SEC] [--no_adaptive]
```

| 选项 | 说明 |
|------|------|
| `-h, --help` | 显示帮助信息 |
| `-v, --version` | 显示版本号 |
| `-c FILE` | 配置文件路径 |
| `-q, --quiet` | 安静模式 — 仅输出转录结果和错误 |
| `-i FILE` | 转录音频文件而非录音 |
| `-o FILE` | 将转录结果追加到文件 |
| `--test` | 测试 API 配置并退出 |
| `--list_devices` | 列出可用的音频输入设备 |
| `--device DEV` | 音频输入设备（名称或索引） |
| `-e, --edit` | 在编辑器中打开配置文件 |
| `--generate_config` | 创建配置文件 |
| `--print_config` | 打印配置模板到 stdout |
| `--vad` | 持续录音，启用语音活动检测 |
| `--interval SEC` | 持续录音，固定间隔转录 |
| `--adaptive` | 自适应阈值（使用 `--vad` 时默认启用） |
| `--calibrate` | 从环境噪音校准静音阈值 |
| `--silence_threshold RMS` | 静音阈值 |
| `--silence_duration SEC` | 触发转录的静音时长 |
| `--no_adaptive` | 禁用自适应阈值 |
