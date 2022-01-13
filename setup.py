from setuptools import find_packages, setup


install_requires = ["pyparsing>=3.0", "typing_extensions", "babel", "dataclass_utils"]
extras_require = {
    "pptx": ["python-pptx"],
}

setup(
    name="refill",
    version="0.3",
    description="Reimagined filling of document templates",
    license="Apache License, Version 2.0",
    url="https://github.com/trackuity/refill",
    packages=find_packages(exclude=("tests",)),
    python_requires=">=3.7",
    install_requires=install_requires,
    extras_require={
        "all": list(set(sum(extras_require.values(), []))),
        **extras_require,
    },
)
