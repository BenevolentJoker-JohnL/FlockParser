"""
FlockParser - Document RAG Intelligence with Distributed Processing
A system that distributes document RAG across heterogeneous GPU/CPU clusters
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements from requirements.txt
requirements = []
with open('requirements.txt', 'r') as f:
    for line in f:
        line = line.strip()
        # Skip comments, empty lines, and optional dependencies
        if line and not line.startswith('#') and not line.startswith('ocrmypdf'):
            requirements.append(line)

setup(
    name="flockparser",
    version="1.0.3",
    author="BenevolentJoker (John L.)",
    author_email="benevolentjoker@gmail.com",
    description="Document RAG Intelligence with Distributed Processing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BenevolentJoker-JohnL/FlockParser",
    project_urls={
        "Bug Tracker": "https://github.com/BenevolentJoker-JohnL/FlockParser/issues",
        "Documentation": "https://github.com/BenevolentJoker-JohnL/FlockParser#readme",
        "Source Code": "https://github.com/BenevolentJoker-JohnL/FlockParser",
        "Demo Video": "https://youtu.be/M-HjXkWYRLM",
    },
    packages=find_packages(exclude=['tests', 'tests.*', 'testpdfs', 'converted_files', 'knowledge_base']),
    py_modules=[
        'flockparsecli',
        'flock_ai_api',
        'flock_webui',
        'flock_mcp_server',
        'gpu_controller',
        'intelligent_gpu_router',
        'gpu_router_daemon',
        'adaptive_parallelism',
        'vram_monitor',
        'benchmark_comparison',
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: General",
        "Topic :: System :: Distributed Computing",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-timeout>=2.1.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
        ],
        'ocr': [
            'ocrmypdf>=15.4.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'flockparse=flockparsecli:main',
            'flockparse-api=flock_ai_api:main',
            'flockparse-webui=flock_webui:main',
            'flockparse-mcp=flock_mcp_server:main',
        ],
    },
    include_package_data=True,
    package_data={
        '': ['*.md', 'LICENSE', 'requirements.txt', '.env.example'],
    },
    keywords=[
        'rag',
        'retrieval-augmented-generation',
        'distributed-systems',
        'document-processing',
        'gpu-acceleration',
        'ollama',
        'chromadb',
        'pdf-processing',
        'ocr',
        'ai',
        'machine-learning',
        'nlp',
    ],
    zip_safe=False,
)
