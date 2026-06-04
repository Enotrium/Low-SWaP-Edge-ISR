"""
Weaponized SNN FPGA Accelerator — Python Package Setup
Targets low-SWaP defense autonomous systems on XC7Z020 (PYNQ-Z2).
"""
from setuptools import setup, find_packages

setup(
    name="snn-fpga-accelerator",
    version="2.0.0",
    author="Defense Autonomous Systems Research",
    description="Event-Driven SNN FPGA Accelerator hardened for defense autonomous systems",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Enotrium/Low-SWaP-Edge-ISR",
    packages=find_packages(where="software/python"),
    package_dir={"": "software/python"},
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.21.0",
        "pyyaml>=5.4.0",
        "scipy>=1.7.0",
        "matplotlib>=3.5.0",
    ],
    extras_require={
        "zynq": ["pynq>=2.7.0"],
        "test": ["pytest>=7.0.0"],
        "all": ["pynq>=2.7.0", "pytest>=7.0.0"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Defense",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)