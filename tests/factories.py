# Copyright 2016, 2019 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Test Factory to make fake objects for testing
"""
from datetime import date, datetime

import factory
from factory.fuzzy import FuzzyChoice, FuzzyDate
from service.models.files import Files
from service.common.enum_handler import *


class FilesFactory(factory.Factory):
    """Creates fake Files that you don't have to feed"""

    class Meta:  # pylint: disable=too-few-public-methods
        """Maps factory to data model"""

        model = Files

    webbot_id = -2
    name = FuzzyChoice(["file1.txt", "file2.pdf", "file3.py"])
    s3_path = "rsgrs"
    file_type = "application/pdf"
    source = FuzzyChoice([e.value for e in FileSource])
    labels = {"label": "value"}
    created_date = datetime.utcnow()
    modified_date = datetime.utcnow()
    active = True
    status = FuzzyChoice([e.value for e in FileStatus])
    allow_questions = factory.Faker("boolean")
    extra_info = {"extra": "info"}
    public = factory.Faker("boolean")
