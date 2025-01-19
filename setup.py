from setuptools import setup
from mypyc.build import mypycify

setup(
    name="ClashKing",
    ext_modules=mypycify(["bot"]),
    zip_safe=False,
)