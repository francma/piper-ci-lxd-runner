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
          'piper_lxd = piper_lxd.run:run'
        ]
    },
    setup_requires=[
        'pytest-runner',
    ],
    install_requires=[
        'ws4py',
        'click',
        'flask',
        'uwsgi',
        'flask_uwsgi_websocket',
        'gevent',
        'requests',
        'pylxd',
    ],
    tests_require=[
        'pytest',
        'portalocker',
    ],
)
