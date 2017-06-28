from setuptools import setup, find_packages

long_description = ""

setup(
    name='piper_lxd',
    version='0.11',
    description='Piper CI LXD Runner',
    long_description=long_description,
    packages=find_packages(),
    package_dir={'piper_lxd': 'piper_lxd'},
    author='Martin Franc',
    author_email='francma6@fit.cvut.cz',
    keywords='lxd,ci,runner',
    license='Public Domain',
    url='https://github.com/francma/piper-ci-lxd-runner',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: Public Domain',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries',
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
          'piper-lxd = piper_lxd.run:main'
        ]
    },
    install_requires=[
        'ws4py',
        'requests',
        'pylxd',
        'pyyaml',
        'pykwalify',
    ],
    extras_require={
        'dev': [
            'mypy',
            'tox',
            'coveralls',
            'pytest>=3',
            'pytest-timeout',
            'pytest-cov',
        ],
    },
)
