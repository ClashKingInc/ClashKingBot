from mypyc.build import mypycify
from setuptools import setup

setup(
    name='ClashKing',
    ext_modules=mypycify(['bot']),
    zip_safe=False,
)
