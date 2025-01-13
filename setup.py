from setuptools import setup, find_packages

setup(
    name="asr2clip",
    version="0.3.5",
    author="Oaklight",
    author_email="oaklight@gmx.com",
    description="A real-time speech-to-text clipboard tool.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Oaklight/asr2clip",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.24.4",
        "openai>=1.59.6",
        "pyperclip>=1.9.0",
        "PyYAML>=6.0.2",
        "requests>=2.32.3",
        "scipy>=1.10.1",
        "sounddevice>=0.5.1",
        "pydub>=0.25.1",
        "ffmpeg>=1.4",
    ],
    entry_points={
        "console_scripts": [
            "asr2clip=asr2clip.asr2clip:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
    ],
    license="GNU Affero General Public License v3",
    python_requires=">=3.8",
)
