# 基本用法

## 单次录音

录音直到按 Ctrl+C，然后转录并复制到剪贴板：

```bash
asr2clip
```

## 文件转录

转录已有的音频文件：

```bash
asr2clip -i recording.mp3
```

支持 MP3、WAV、FLAC、OGG 以及 ffmpeg 支持的其他格式。

## 保存到文件

将转录结果追加到文件：

```bash
asr2clip -o transcript.txt
```

## 安静模式

仅输出转录结果和错误信息：

```bash
asr2clip -q
```

## 示例

```bash
# 录音并转录
asr2clip

# 转录文件并保存输出
asr2clip -i lecture.mp3 -o notes.txt

# 使用指定音频设备，安静模式
asr2clip --device pulse -q
```
