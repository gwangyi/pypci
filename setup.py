from setuptools import setup

setup(
    name="pypci",
    description="cffi-based libpci wrapper for python",
    license="MIT",
    version="0.1",
    author='gwangyi',
    maintainer='gwangyi',
    author_email='gwangyi.kr@gmail.com',
    packages=['pypci'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3',
    ],
    setup_requires=['cffi>=1.0.0', 'pycparserlibc', 'cffi_ext'],
    cffi_modules=['build.py:ffi_builder'],
    install_requires=['cffi>=1.0.0'],
    dependency_links=[
        'git+https://github.com/gwangyi/pycparserlibc#egg=pycparserlibc-0',
        'git+https://github.com/gwangyi/cffi_ext#egg=cffi_ext-0'
    ]
)
