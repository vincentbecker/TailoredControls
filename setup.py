from distutils.core import setup
from Cython.Build import cythonize

setup(name="DynamicUIs", ext_modules=cythonize("*.pyx"))
