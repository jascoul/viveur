from setuptools import setup, find_packages

setup(
    name='viveur',
    version='0.0.0dev',
    author='Jasper Op de Coul',
    author_email='opdecoul@ubib.eur.nl',
    url='http://eur.nl/ul',
    description="Erasmus University VIVO Configuration",
    classifiers=["Development Status :: 5 - Production/Stable",
                 "Programming Language :: Python",
                 "License :: OSI Approved :: BSD License",
                 "Topic :: Software Development :: Libraries :: Python Modules",
                 "Environment :: Web Environment"],
    packages=find_packages(),
    include_package_data = True,
    zip_safe=False,
    license='BSD',
    entry_points= {
    'console_scripts': [
       'metis_dumper = viveur.tools:metis_dumper',
       'vivo_ingester = viveur.tools:vivo_ingester',
       'drop_vivo_tables = viveur.tools:drop_vivo_tables'
      ],
    },
    install_requires=[
        'cx_Oracle',
        'sqlalchemy',
        'lxml',
        'jnius'
    ],
)


