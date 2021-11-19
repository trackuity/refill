from setuptools import setup


install_requires = ["pyparsing", "typing_extensions", "babel"]
extras_require = {
    "pptx": ["python-pptx"],
}

setup(
    name="refill",
    version="0.1",
    description="Reimagined filling of document templates with data",
    license="Apache License, Version 2.0",
    url="https://github.com/trackuity/refill",
    py_modules=["refill"],
    install_requires=install_requires,
    extras_require={
        "all": list(set(sum(extras_require.values(), []))),
        **extras_require,
    },
)
