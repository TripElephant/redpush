from setuptools import setup

setup(
    name='redpush',
    version='0.1',
    py_modules=['cli'],
    include_package_data=True,
    install_requires=[
        'click',
    ],
    entry_points='''
        [console_scripts]
        redpush=cli:cli
    ''',
)