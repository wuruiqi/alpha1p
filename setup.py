#!/usr/bin/env python

#!/usr/bin/env python
# coding=utf-8
from setuptools import setup, find_packages

from importlib.machinery import SourceFileLoader

version = SourceFileLoader('alpha1p.version',
                           'alpha1p/version.py').load_module()

# with open('README.md', 'r') as fdesc:
#     long_description = fdesc.read()

setup(
    name = "alpha1p",
    version = version.version,
    # packages=['alpha1p'],
    packages = find_packages(),
    # packages = find_packages('alpha1p'),
    # package_dir = {'':'alpha1p'},
    # package_data={'': ['Datas/*']},

    include_package_data=True,
    # platforms="any",
	install_requires = ['numpy>=1.18.1', 'pandas>=1.0.1', 'numba>=0.48.0', 'pyusb>=1.0.2', 'pyserial>=3.4'],
    # metadata for upload to PyPI
    author = "wuruiqi",
    author_email = "woshiwuruiqi@163.com",
    description = "Alpha 1 Pro driver",
    # long_description=long_description,
    # long_description_content_type='text/markdown',
    license = "GNU General Public License v3.0",
    keywords = ["Alpha 1", "ubteach"],
    url="https://github.com/wuruiqi/alpha1p",   # project home page, if any

    # could also include long_description, download_url, classifiers, etc.
    classifiers=[           # 程序的所属分类列表
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",      
        "Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator",  
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],


    zip_safe=False
)