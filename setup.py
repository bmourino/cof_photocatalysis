#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

import json

from setuptools import find_packages, setup

if __name__ == '__main__':
    # Provide static information in setup.json
    # such that it can be discovered automatically
    with open('setup.json', 'r') as info:
        kwargs = json.load(info)

    setup(packages=find_packages(), **kwargs)
