# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

from perf_insights import function_handle

class ModuleToLoadTests(unittest.TestCase):

  def testExactlyOneHrefOrFilename(self):
    with self.assertRaises(Exception):
      function_handle.ModuleToLoad()

    with self.assertRaises(Exception):
      function_handle.ModuleToLoad('foo', 'foo')

  def testRepr(self):
    mtl0 = function_handle.ModuleToLoad(href='/foo')
    mtl1 = function_handle.ModuleToLoad(filename='foo.html')

    self.assertEquals(str(mtl0), 'ModuleToLoad(href="/foo")')
    self.assertEquals(str(mtl1), 'ModuleToLoad(filename="foo.html")')

  def testAsDict(self):
    mtl0 = function_handle.ModuleToLoad(href='/foo')
    mtl1 = function_handle.ModuleToLoad(filename='foo.html')

    self.assertEquals(mtl0.AsDict(), {
        'href': '/foo'
    })

    self.assertEquals(mtl1.AsDict(), {
        'filename': 'foo.html'
    })

  def testFromDict(self):
    module_dict0 = {
        'href': '/foo'
    }

    module_dict1 = {
        'filename': 'foo.html'
    }

    mtl0 = function_handle.ModuleToLoad.FromDict(module_dict0)
    mtl1 = function_handle.ModuleToLoad.FromDict(module_dict1)

    self.assertEquals(mtl0.href, '/foo')
    self.assertIsNone(mtl0.filename)
    self.assertEquals(mtl1.filename, 'foo.html')
    self.assertIsNone(mtl1.href)


class FunctionHandleTests(unittest.TestCase):

  def testRepr(self):
    module = function_handle.ModuleToLoad(href='/foo')
    handle = function_handle.FunctionHandle([module], 'Bar')

    self.assertEquals(
        str(handle),
        'FunctionHandle(modules_to_load=[ModuleToLoad(href="/foo")], '
        'function_name="Bar")')

  def testAsDict(self):
    module = function_handle.ModuleToLoad(href='/foo')
    handle = function_handle.FunctionHandle([module], 'Bar')

    self.assertEquals(
        handle.AsDict(), {
            'modules_to_load' : [{'href': '/foo'}],
            'function_name': 'Bar'
        })

  def testFromDict(self):
    handle_dict = {
        'modules_to_load': [{'href': '/foo'}],
        'function_name': 'Bar'
    }

    handle = function_handle.FunctionHandle.FromDict(handle_dict)
    self.assertEquals(len(handle.modules_to_load), 1)
    self.assertEquals(handle.modules_to_load[0].href, '/foo')
    self.assertEquals(handle.function_name, 'Bar')
