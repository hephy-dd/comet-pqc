from setuptools import setup, find_packages

setup(
    name='comet-pqc',
    version='0.2.0',
    author="Bernhard Arnold",
    author_email="bernhard.arnold@oeaw.ac.at",
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'comet @ https://github.com/hephy-dd/comet/archive/0.9.0.zip#egg=comet-0.9.0',
        'pyyaml',
        'jsonschema'
    ],
    package_data={},
    entry_points={
        'console_scripts': [
            'comet-pqc = comet_pqc.__main__:main',
        ],
    },
    test_suite='tests',
    license="GPLv3",
)
