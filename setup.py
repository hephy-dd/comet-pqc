from setuptools import setup, find_packages

setup(
    name='comet-pqc',
    version='0.25.4',
    author="Bernhard Arnold",
    author_email="bernhard.arnold@oeaw.ac.at",
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'comet @ https://github.com/hephy-dd/comet/archive/0.11.2.zip#egg=comet-0.11.2',
        'analysis-pqc @ https://github.com/hephy-dd/analysis-pqc/archive/0.1.2.zip#egg=analysis-pqc-0.1.2',
        'qutie>=1.5.2',
        'pyyaml',
        'jsonschema'
    ],
    package_data={
        'comet_pqc': [
            'assets/config/chuck/*.yaml',
            'assets/config/sample/*.yaml',
            'assets/config/sequence/*.yaml',
            'assets/schema/chuck.yaml',
            'assets/schema/sample.yaml',
            'assets/schema/sequence.yaml',
        ],
    },
    entry_points={
        'console_scripts': [
            'comet-pqc = comet_pqc.__main__:main',
        ],
    },
    test_suite='tests',
    license="GPLv3",
)
