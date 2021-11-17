from setuptools import setup

install_requires = ["pyparsing", "typing_extensions", "babel"]
setup(
    name="hydrofile",
    version="0.1",
    description="Machinery for hydrating template files",
    license="Apache Software License (ASF)",
    url="https://github.com/trackuity/hydrofile",
    py_modules=["hydrofile"],
    install_requires=install_requires,
)
