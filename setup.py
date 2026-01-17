from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ""

setup(
    name="codeplug-converter",
    version="0.1.0",
    author="Aram Dermenjyan",
    author_email="",
    description="Convert radio configuration files to various formats",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/CodeplugConverter",  # Update with actual URL
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Communications :: Ham Radio",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        # No required dependencies - uses stdlib only
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
        ],
        "uart": [
            "pyserial>=3.5",  # For future UART programming support
        ],
    },
    entry_points={
        "console_scripts": [
            "codeplug-converter=codeplug_converter.__main__:main",
        ],
    },
)
