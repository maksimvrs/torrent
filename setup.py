from setuptools import setup

setup(
    name='torrent',
    version='1.0.0',
    packages=['cli', 'gui'],
    install_requires=[
        'Click==7.0',
        'bitstring==3.1.5',
        'aiohttp==3.4.4',
        'setuptools==39.0.1',
        'PyQt5==5.12.1',
    ],
)
