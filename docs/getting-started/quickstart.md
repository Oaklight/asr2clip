# 快速开始

## 1. 安装

```bash
pip install asr2clip
```

## 2. 配置

创建并编辑配置文件：

```bash
asr2clip --edit
```

这会在默认编辑器中打开配置文件。填入 ASR API 凭据：

```yaml
api_base_url: "https://api.openai.com/v1/"
api_key: "YOUR_API_KEY"
model_name: "whisper-1"
```

## 3. 测试

验证配置：

```bash
asr2clip --test
```

这将检查剪贴板支持、音频设备功能和 API 连接。

## 4. 录音和转录

```bash
# 单次录音（按 Ctrl+C 停止）
asr2clip

# 持续录音，语音活动检测
asr2clip --vad

# 转录音频文件
asr2clip -i audio.mp3
```

转录结果会自动复制到剪贴板。
