# JFrog2PyPI
![PyPI](https://img.shields.io/pypi/v/jfrog2pypi) [![GitHub](https://img.shields.io/github/license/microservices-course-itmo/jfrog2pypi?color=silver)](https://github.com/microservices-course-itmo/jfrog2pypi/blob/main/LICENSE)
***
## Description

### Substantiation
Free version of JFrog Artifactory doesn't have a default API to allow to use it within python projects in any other way than just direct downloading by the full path. It certainly blocks our development process as far as we want to have some sort of version-control and automatic search.
### Solution
Trying to solve this problem, jfrog2pypi module was written. Currently it minifies the interaction with artifactory down to a few lines of code. Module provides versioning, automatic search and collision-solving mechanisms. Default parameters are pretty similar to those that are being passed to `pip`, others are listed below.
> ***Note:*** If non-whl module is being loaded, there is no guarantee that all dependencies will be satisfied.
Though, this package was specifically designed to work with python-compiled protobuf files and their dependencies are also not guaranteed.
---
## User Guide
### Installing
You have two options to install this package:

1. Use ```python -m pip install jfrog2pypi```
2. Directly include `jfrog2pypi.py` file into your project and install dependencies by yourself

Doesn't change anything, though the first way is more preferable and comfortable.

### Loading your package
Default loading procedure should look like in the following snippet:
```python
from jfrog2pypi import ArtifactoryParser

module = ArtifactoryParser().get_module(
	req_module = '<module name>==1.0.0',
	url = 'http://<artifactory url>:<port>/artifactory/<repository name>',
	tags= ['<service name>', 'pb2.py'],
	login = 'login',
	password= 'password',
	searcher='dohq'
)

if not module == None:
    print('Module has been successfully loaded')
else:
    print('Something went wrong')
```
### Detailed explanation
Let's break down the method parameters:
1. `req_module`: contains module name and a version determining expression (optional) supports any number of expressions, delimited by one of ['=', '>', '<'] signs.
2. `url`: http link to the artifactory repository. If you really sure, you can even pass a PyPI-repo link (See the point 6).
3. `tags`: options to resolve possible collisions within a given repository. Anything that can help to distinguish your package from others with identical names will be useful.

> ***Note:*** In case if you want to load a module that has `.whl` extension instead of `.py`, you may use such tags as 'cp38' or 'none-any.whl', etc. 

4. `login`: basic auth login.
5. `password`: basic auth password. (See the [Notion](https://www.notion.so/ded97d649cc840ccbf1972568627a218) for more).
6. `searcher`: defines the way you are going to parse the repository structure. It currently supports two possible options: 'dohq' and 'html'. 

> ***Note:*** 'html' searcher is way too slow and I really recommend you to use 'dohq' due to the fact that it uses open-source python implementation of artifactory API.

If everything went OK, the `module` now will contain the real module and you can refer to any of it's internal properties by `module.property`. Otherwise `module` will be equal to `None` and logger will print possible causes of the error.
***
## Contribution
MIT License does not restrict your rights to use and modify this software, so please feel free to participate. There are lots of ways to improve it's performance and usability.

In case of detected bugs you can eather email me or open an issue on github.

**SkymeFactor, <sergey.51351@gmail.com>**
