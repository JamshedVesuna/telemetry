# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from telemetry.page import page as page_module
from telemetry import story

class StartupPagesRecordPage(page_module.Page):
  def __init__(self, url, page_set):
    super(StartupPagesRecordPage, self).__init__(url=url, page_set=page_set)
    self.archive_data_file = 'data/url.json'


class Url{0}PageSet(story.StorySet):
  def __init__(self):
    super(Url{0}PageSet, self).__init__(
        archive_data_file='data/url{0}_page.json')

    urls_list = ['{1}']

    for url in urls_list:
      self.AddStory(StartupPagesRecordPage(url, self))
