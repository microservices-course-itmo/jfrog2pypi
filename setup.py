"""
The build/compilations setup
"""
from setuptools import setup

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()
    f.close()

def get_version(filename="jfrog2pypi.py"):
    version = ''
    with open(filename, encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith("__version__"):
            version = line.split('"')[1]
            break
    f.close()
    return version
    

setup(
    name='jfrog2pypi',
    version=get_version(),
    url='https://github.com/microservices-course-itmo/jfrog2pypi.git',
    author='SkymeFactor',
    author_email='sergei.51351@gmail.com',
    license='MIT',
    description='Jfrog Artifactory python modules loader',
    py_modules=["jfrog2pypi"],
    include_package_data=True,
    python_requires='>=3.6',
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Content Management System",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Version Control",
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    install_requires=[
    	"requests",
    	"bs4",
    	"dohq-artifactory",
    	"protobuf"
    ],
    keywords=["jfrog", "pypi", "jfrog2pypi", "artifactory", "parse"],
)
