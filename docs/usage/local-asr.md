# 本地 ASR 服务器

asr2clip 包含一个可选的本地 ASR 服务器，基于 [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) 实现完全离线的语音识别。

## 安装

使用 `local_asr` 可选依赖安装：

```bash
pip install "asr2clip[local_asr]"
```

## 下载模型

首次使用前，预下载默认的 SenseVoice 模型：

```bash
asr2clip --download-model
```

模型默认存储在 `~/.local/share/asr2clip/models/` 目录下。可通过 `--model-dir` 参数或 `ASR2CLIP_MODEL_DIR` 环境变量覆盖。

## 启动服务器

可以通过两种方式启动服务器：

```bash
# 使用专用命令
asr2clip-serve

# 或使用 --serve 标志
asr2clip --serve
```

服务器默认在 `http://localhost:8000` 启动，提供 OpenAI 兼容的 `/v1/audio/transcriptions` 端点。

### 服务器选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--host` | `127.0.0.1` | 服务器绑定地址 |
| `--port` | `8000` | 服务器绑定端口 |
| `--model-dir` | 自动 | ASR 模型目录路径 |
| `--num-threads` | `4` | 推理线程数 |
| `--config` | 自动 | `models.yaml` 配置文件路径 |

```bash
# 在自定义地址和端口启动
asr2clip --serve --host 0.0.0.0 --port 9000

# 使用指定模型目录
asr2clip --serve --model-dir /path/to/models

# 使用自定义 models.yaml 配置
asr2clip-serve --config /path/to/models.yaml
```

## 模型注册表

服务器使用基于 YAML 的模型注册表（`models.yaml`）管理可用模型。首次运行时会在 `~/.local/share/asr2clip/models.yaml` 自动创建包含默认 SenseVoice 条目的注册表。

### 注册表格式

```yaml
default_model: sensevoice-small
num_threads: 4

models:
  sensevoice-small:
    type: sense_voice
    dir: sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17
    files:
      model: model.int8.onnx
      tokens: tokens.txt
    options:
      use_itn: true
      language: ""          # 空字符串 = 自动检测
    download:
      url: "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2"
      archive_subdir: sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17
```

### 支持的模型类型

| 类型 | sherpa-onnx 工厂方法 | 必需文件 |
|------|---------------------|----------|
| `sense_voice` | `from_sense_voice` | `model`, `tokens` |
| `whisper` | `from_whisper` | `encoder`, `decoder`, `tokens` |
| `paraformer` | `from_paraformer` | `paraformer`, `tokens` |
| `transducer` | `from_transducer` | `encoder`, `decoder`, `joiner`, `tokens` |

### 添加模型

将 sherpa-onnx 模型文件下载到 `~/.local/share/asr2clip/models/<model-dir>/`，然后在 `models.yaml` 中添加条目：

```yaml
models:
  # ... 已有模型 ...
  whisper-large-v3:
    type: whisper
    dir: sherpa-onnx-whisper-large-v3
    files:
      encoder: encoder.int8.onnx
      decoder: decoder.int8.onnx
      tokens: tokens.txt
    options:
      language: en
```

模型按需懒加载——仅默认模型在启动时加载。

## 配置

将 asr2clip 指向本地服务器：

```yaml
api_base_url: "http://localhost:8000/v1/"
api_key: "not-used"
model_name: "sensevoice-small"
```

## API 端点

### POST `/v1/audio/transcriptions`

OpenAI 兼容的转录端点。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `file` | file | 必需 | 待转录的音频文件 |
| `model` | string | 必需 | 模型名称（必须在模型注册表中注册） |
| `response_format` | string | `"json"` | `"json"`、`"text"` 或 `"verbose_json"` |
| `language` | string | `null` | 语言提示（ISO-639-1，如 `"en"`、`"zh"`） |
| `prompt` | string | `null` | 提示文本（取决于模型） |
| `temperature` | float | `0.0` | 解码温度（取决于模型） |
| `stream` | bool | `false` | 启用 SSE 流式响应 |

**响应格式：**

=== "json（默认）"

    ```json
    {"text": "转录文本"}
    ```

=== "text"

    ```
    转录文本
    ```

=== "verbose_json"

    ```json
    {
      "task": "transcribe",
      "language": "auto",
      "duration": 2.5,
      "text": "转录文本",
      "segments": [{"id": 0, "start": 0.0, "end": 2.5, "text": "转录文本"}]
    }
    ```

**流式响应（SSE）：**

当 `stream=true` 时，响应为 `text/event-stream`，包含以下事件：

```
data: {"type": "transcript.text.delta", "delta": "转录文本"}

data: {"type": "transcript.text.done", "text": "转录文本", "duration": 2.5, "language": "auto"}

data: [DONE]
```

### GET `/v1/models`

列出所有已注册的模型。

### GET `/health`

健康检查——返回 `{"status": "ok"}` 或 `{"status": "loading"}`。

## 使用方式

```bash
# 在一个终端启动服务器
asr2clip --serve

# 在另一个终端使用本地服务器
asr2clip -c local_config.yaml

# 或直接转录文件
asr2clip -c local_config.yaml -i recording.mp3

# 使用 curl 测试
curl http://localhost:8000/v1/audio/transcriptions \
  -F file=@audio.wav \
  -F model=sensevoice-small

# 流式响应
curl http://localhost:8000/v1/audio/transcriptions \
  -F file=@audio.wav \
  -F model=sensevoice-small \
  -F stream=true
```

## 特性

- **完全离线** — 无需互联网连接
- **OpenAI 兼容 API** — 可作为云端 ASR 服务的直接替代
- **多模型支持** — 通过 `models.yaml` 注册和切换模型
- **模型参数路由** — `model` 字段选择使用哪个引擎
- **语言支持** — 每次请求的语言提示，使用 LRU 缓存的识别器
- **SSE 流式传输** — 面向实时客户端的流式转录响应
- **懒加载模型** — 非默认模型在首次请求时加载
- **自动下载模型** — 配置了下载 URL 的模型在首次使用时自动获取
- **集成 CLI** — 使用 `asr2clip --serve` 启动服务器，无需单独命令
