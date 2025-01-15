from setuptools import setup, find_packages
import sys

# Define package requirements based on Python version
install_requires = [
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "websockets>=12.0",
    "aiohttp>=3.9.3",
    "tweepy>=4.14.0",
    "textblob>=0.17.1",
    "python-dotenv>=1.0.1",
    "httpx>=0.26.0",
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.5",
]

# Add version-specific requirements
if sys.version_info >= (3, 13):
    install_requires.extend([
        "numpy>=1.26.4",
        "scipy>=1.12.0",
        "scikit-learn>=1.4.0",
        "pandas>=2.2.0",
    ])
else:
    install_requires.extend([
        "numpy>=1.24.3",
        "scipy>=1.11.3",
        "scikit-learn>=1.3.0",
        "pandas>=2.1.0",
    ])

setup(
    name="trading-assistant",
    version="0.1",
    packages=find_packages(),
    python_requires='>=3.13',
    install_requires=install_requires,
    classifiers=[
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3 :: Only',
        'Development Status :: 4 - Beta',
    ],
) 