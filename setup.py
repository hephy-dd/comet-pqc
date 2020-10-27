from setuptools import setup, find_packages

setup(
    name='comet-pqc',
    version='0.26.0',
    author="Bernhard Arnold",
    author_email="bernhard.arnold@oeaw.ac.at",
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'comet @ git+https://github.com/hephy-dd/comet.git@0.12.0',
        'analysis-pqc @ git+https://github.com/hephy-dd/analysis-pqc.git@0.1.2',
        'qutie>=1.6.0',
        'pyyaml',
        'jsonschema'
    ],
    package_data={
        'comet_pqc': [
            'assets/config/chuck/*.yaml',
            'assets/config/sample/*.yaml',
            'assets/config/sequence/*.yaml',
            'assets/icons/*.svg',
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
