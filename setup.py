import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="connectduino",
    version="0.0.1",
    author="Sean DeBellis",
    author_email="sdebellis462@gmail.com",
    description="A package with tools to collect data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SMDeBellis/connectduino",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: OS Independent",
    ),
)
