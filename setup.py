from setuptools import setup

setup(
    name='redpush',
    version='0.1',
    py_modules=['cli'],
    include_package_data=True,
    packages=['redpush'],
    install_requires=[
        'click',
        'requests',
        'ruamel.yaml'
    ],
    entry_points='''
        [console_scripts]
        redpush=redpush.cli:cli
    ''',
)