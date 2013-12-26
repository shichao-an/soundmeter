from setuptools import setup, find_packages
from soundmeter import __version__


requires = ['pyaudio', 'pydub', 'argparse']

setup(
    name='soundmeter',
    version=__version__,
    description="Simple real-time sound meter.",
    long_description=open('README.rst').read(),
    keywords='soundmeter',
    author='Shichao An',
    author_email='shichao.an@nyu.edu',
    url='https://github.com/shichao-an/soundmeter',
    license='BSD',
    install_requires=requires,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'soundmeter = soundmeter.meter:main',
        ],
    },
    classifiers=[
        "Environment :: Console",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
    ],
)
