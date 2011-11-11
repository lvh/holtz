from setuptools import setup

setup(name='txyoga',
      version='0',
      description='Static preprocessor for the web',
      url='https://github.com/lvh/holtz',

      author='Laurens Van Houtven',
      author_email='_@lvh.cc',

      packages=['holtz'],

      requires=['twisted'],

      license='ISC',
      classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Twisted",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Topic :: Internet :: WWW/HTTP",
        ])
