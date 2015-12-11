#!/usr/bin/env python

import os
import sys


script = os.path.join(os.path.dirname(__file__), 'src/content/test/gpu/run_gpu_test.py')
os.execv(sys.executable, [sys.executable, script] + sys.argv[1:])