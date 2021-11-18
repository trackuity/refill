from setuptools import setup


install_requires = ["pyparsing", "typing_extensions", "babel"]
extras_require = {
    "pptx": ["python-pptx"],
}

setup(
    name="hydrofile",
    version="0.1",
    description="Machinery for hydrating template files",
    license="Apache Software License (ASF)",
    url="https://github.com/trackuity/hydrofile",
    py_modules=["hydrofile"],
    install_requires=install_requires,
    extras_require={
        "all": list(set(sum(extras_require.values(), []))),
        **extras_require,
    },
)
