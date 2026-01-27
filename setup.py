from setuptools import setup, find_packages

# Read long description from README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="vttkit",
    version="0.4.0",
    author="VTTKit Contributors",
    description="Complete VTT (WebVTT) processing toolkit with YouTube support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vttkit/vttkit",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "yt-dlp>=2023.0.0",
        "faster-whisper>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    include_package_data=True,
    keywords="vtt webvtt subtitles captions youtube live-stream hls m3u8",
    project_urls={
        "Bug Reports": "https://github.com/vttkit/vttkit/issues",
        "Source": "https://github.com/vttkit/vttkit",
        "Documentation": "https://github.com/vttkit/vttkit#readme",
    },
)
