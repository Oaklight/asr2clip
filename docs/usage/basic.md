# 基本用法

## 单次录音

录音直到按 Ctrl+C，然后转录并复制到剪贴板：

```bash
asr2clip
```

按一次 **Ctrl+C** 停止录音并触发转录。按两次 **Ctrl+C** 强制立即退出。

## 文件转录

转录已有的音频文件：

```bash
asr2clip -i recording.mp3
```

支持 MP3、WAV、FLAC、OGG 以及 ffmpeg 支持的其他格式。

## 保存到文件

将转录结果追加到文件（带时间戳）：

```bash
asr2clip -o transcript.txt
```

## 安静模式

仅输出转录结果和错误信息：

```bash
asr2clip -q
```

## 自动重试

如果 API 请求超时，asr2clip 会自动重试最多 3 次，每次间隔 2 秒。

## 示例

```bash
# 录音并转录
asr2clip

# 转录文件并保存输出
asr2clip -i lecture.mp3 -o notes.txt

# 使用指定音频设备，安静模式
asr2clip --device pulse -q

# 录音并保存到文件
asr2clip -o ~/notes.txt
```
