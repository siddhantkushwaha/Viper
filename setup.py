import pathlib
import setuptools
from distutils.core import setup

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

setup(
    name='viper-python',
    packages=['viper'],
    version='0.1.2',
    license='MIT',
    description='Common utility functions.',
    author='Siddhant Kushwaha',
    author_email='k16.siddhant@gmail.com',
    url='https://github.com/siddhantkushwaha/viper',
    download_url='https://github.com/siddhantkushwaha/viper/archive/0.1.2.tar.gz',
    keywords=['DOWNLOAD', 'PARALLEL', 'CONCURRENT'],
    install_requires=[
        'requests',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    include_package_data=True
)
