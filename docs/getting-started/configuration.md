# 配置

## 配置文件格式

asr2clip 使用 YAML 配置文件：

```yaml
api_base_url: "https://api.openai.com/v1/"  # ASR API 端点
api_key: "YOUR_API_KEY"                     # API 密钥
model_name: "whisper-1"                     # 模型名称
# quiet: false                              # 可选：禁用日志
# audio_device: "pulse"                     # 可选：音频输入设备
```

## 配置文件位置

配置文件按以下顺序搜索：

1. `./asr2clip.conf` — 当前目录
2. `~/.config/asr2clip/config.yaml` — XDG 配置（推荐）
3. `~/.config/asr2clip.conf` — 旧版
4. `~/.asr2clip.conf` — 旧版

## 管理配置

```bash
asr2clip --edit            # 在编辑器中打开配置（不存在则创建）
asr2clip --generate_config # 在 ~/.config/asr2clip/config.yaml 生成配置
asr2clip --print_config    # 打印配置模板到 stdout
asr2clip -c /path/to/file  # 使用指定的配置文件
```

## 支持的后端

### OpenAI Whisper

```yaml
api_base_url: "https://api.openai.com/v1/"
api_key: "sk-..."
model_name: "whisper-1"
```

### 硅基流动

```yaml
api_base_url: "https://api.siliconflow.cn/v1/"
api_key: "YOUR_KEY"
model_name: "FunAudioLLM/SenseVoiceSmall"
```

### Xinference（自托管）

```yaml
api_base_url: "http://localhost:9997/v1/"
api_key: "not-used"
model_name: "SenseVoiceSmall"
```

### 本地 ASR 服务器

```yaml
api_base_url: "http://localhost:8000/v1/"
api_key: "not-used"
model_name: "sensevoice-small"    # 必须匹配服务器 models.yaml 中的模型名称
```

本地服务器通过模型注册表（`models.yaml`）支持多种模型。详情请参阅[本地 ASR 服务器](../usage/local-asr.md)了解安装说明和模型管理。

## 音频设备选择

```bash
asr2clip --list_devices    # 列出所有音频输入设备
asr2clip --device pulse    # 按名称选择设备
asr2clip --device 12       # 按索引选择设备
```

或在配置文件中设置：

```yaml
audio_device: "pulse"  # 或设备索引
```
