# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

version = '0.1'

setup(name='powerlinex-segment-weechat-remote',
      version=version,
      description='Powerline eXtenstion for Weechat',
      long_description=open('README.rst').read(),
      keywords='weechat powerline powerlinex',
      author='Jason Kölker',
      author_email='jason@koelker.net',
      url='https://github.com/jkoelker/powerlinex-segment-weechat-remote',
      license='MIT',
      packages=find_packages(),
      namespace_packages=['powerlinex']
      )
