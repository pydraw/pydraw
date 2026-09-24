from pathlib import Path

import setuptools

long_description = Path(__file__).with_name("README_pypi.md").read_text(encoding="utf-8")

setuptools.setup(
    name="pydraw",
    version="3.0a1",
    author="Noah Coetsee",
    author_email="noah@noahcoetsee.me",
    description="A package designed to make graphics with Python simple and easy!",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pydraw/pydraw",
    packages=setuptools.find_packages(exclude=("tests", "tests.*")),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    license='MIT',
    install_requires=[
        'pillow',
        # 'PyObjC',
        # 'pygobject',
    ],
    python_requires='>=3.8',
)
