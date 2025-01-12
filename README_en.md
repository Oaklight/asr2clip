# asr2clip -- Speech-to-Text Clipboard Tool

[中文](README.md)

This tool is designed to recognize speech in real-time, convert it to text, and automatically copy the text to the system clipboard. The tool leverages API services for speech recognition and uses Python libraries for audio capture and clipboard management.

## Prerequisites

Before you begin, ensure you have the following ready:

- **Python 3.8 or higher**: The tool is written in Python, so you'll need Python installed on your system.
- **API Key**: You will need an API key from a speech recognition service (e.g., **OpenAI/Whisper** API or a compatible ASR API, such as **FunAudioLLM/SenseVoiceSmall** at [siliconflow](https://siliconflow.cn/) or [xinference](https://inference.readthedocs.io/en/latest/)). Make sure you have the necessary credentials.

## Installation

1. **Clone the repository** (if applicable):

```bash
git clone https://github.com/Oaklight/asr2clip.git
cd asr2clip
```

2. **Install the required Python packages**:

```bash
pip install -r requirements.txt
```

3. **Set up your API key**:
   - Create a `config.yaml` file in the root directory of the project. A sample file [`config.example.yaml`](config.example.yaml) is provided.
   - Add your API key to the `config.yaml` file:

```yaml
asr_model:
  api_key: "your_api_key_here"
  api_base_url: "https://api.openai.com/v1" # If you need to customize the API URL
  model_name: "whisper-1" # Default model name
```

4. **Note for Linux users**:
If you are using `pyperclip` on Linux, make sure to install `xclip` or `xsel`. You can install them using the following commands:

```bash
sudo apt-get install xsel # Basic clipboard functionality
sudo apt-get install xclip # More advanced functionality
```

## Usage

1. **Run the tool**:

```bash
python asr2clip.py
```

Alternatively, if you have made the script executable (`chmod +x asr2clip.py`), you can run it directly:

```bash
./asr2clip.py
```

2. **Start speaking**:
   - The tool will start capturing audio from your microphone.
   - It will send the audio to the API for speech recognition.
   - The recognized text will be automatically copied to your system clipboard.

3. **Stop the tool**:
   - Press `Ctrl+C` to stop the tool.

## Configuration

You can customize the tool by modifying the `config.yaml` file. For example, you can change the API endpoint, audio sampling rate, or other parameters depending on the API service you are using.

## Example

```bash
$ ./asr2clip.py --duration 5
Recording for 5 seconds...
Recording complete.
Transcribing audio...
Transcribed Text:
-----------------
1,2,3,3,2,1. This is the English test.
The transcribed text has been copied to the clipboard.
```

## Troubleshooting

- **Audio not captured**: Ensure your microphone is properly connected and configured.
- **API errors**: Check your API key and ensure you have sufficient credits or permissions.
- **Clipboard issues**: Ensure `pyperclip` is correctly installed and compatible with your operating system. Linux users need to install `xclip` or `xsel`.

## Contributing

If you would like to contribute to this project, please fork the repository and submit a pull request. We welcome any improvements or new features!

## License

This project is licensed under the GNU Affero General Public License v3.0. See the `LICENSE` file for more details.