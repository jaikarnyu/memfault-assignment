# Copyright 2016, 2021 John J. Rofrano. All Rights Reserved.
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
Test cases for Files Model

Test cases can be run with:
    nosetests
    coverage report -m

While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_models.py:TestFilesModel

"""
import os
import logging
import unittest
from datetime import date
from werkzeug.exceptions import NotFound
from service.models.files import Files, DataValidationError, db
from service import app
from tests.factories import FilesFactory
from flask import Flask
from service import config
from service.common.enum_handler import *

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/testdb"
)


######################################################################
# FILES   M O D E L   T E S T   C A S E S
######################################################################
"""
    Files Mode : 

    id = db.Column(db.Integer, primary_key=True)
    webbot_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(63), nullable=False)
    s3_path = db.Column(db.String(256), nullable=False, default="")
    file_type = db.Column(db.String(256), nullable=False, default=FileType.TEXT.value)
    source = db.Column(db.String(256), nullable=False, default=Source.KNOWLEDGE.value)
    labels = db.Column(mutable_json_type(dbtype=JSONB, nested=True))
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    modified_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    active = db.Column(db.Boolean, nullable=False, default=True)
    status = db.Column(db.Enum(FileStatus), nullable=False, default=FileStatus.INACTIVE)
    allow_questions = db.Column(db.Boolean, nullable=False, default=True)
    extra_info = db.Column(mutable_json_type(dbtype=JSONB, nested=True))
    """


# pylint: disable=too-many-public-methods
class TestFilesModel(unittest.TestCase):
    """Test Cases for Files Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Files.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Files).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_create_a_files(self):
        """It should Create a files and assert that it exists"""

        files = FilesFactory()
        self.assertTrue(files != None)
        self.assertEqual(files.id, None)
        self.assertEqual(files.webbot_id, -2)
        files.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertTrue(files.id != None)
        db_files = Files.find(files.id)
        self.assertEqual(files.id, db_files.id)

    def test_add_a_files(self):
        """It should Create a files and add it to the database"""
        files = FilesFactory()
        self.assertTrue(files != None)
        self.assertEqual(files.id, None)
        files.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertTrue(files.id != None)
        db_files = Files.find(files.id)
        # Assert that the fields saved are correct
        self.assertEqual(files.id, db_files.id)
        self.assertEqual(files.created_date, db_files.created_date)
        self.assertEqual(files.modified_date, db_files.modified_date)
        self.assertEqual(files.active, db_files.active)
        self.assertEqual(files.webbot_id, db_files.webbot_id)
        self.assertEqual(files.name, db_files.name)
        self.assertEqual(files.s3_path, db_files.s3_path)
        self.assertEqual(files.file_type, db_files.file_type)
        self.assertEqual(files.source, db_files.source)
        self.assertEqual(files.labels, db_files.labels)
        self.assertEqual(files.status, db_files.status)
        self.assertEqual(files.allow_questions, db_files.allow_questions)
        self.assertEqual(files.extra_info, db_files.extra_info)

    def test_update_a_files(self):
        """It should Update a files and add it to the database"""
        files = FilesFactory()
        self.assertTrue(files != None)
        files.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertTrue(files.id != None)
        files = Files.find(files.id)

        # Update the files
        files.name = "Updated Files"
        files.update()
        files = Files.find(files.id)
        self.assertEqual(files.name, "Updated Files")

    def test_delete_a_files(self):
        """It should Delete a files and add it to the database"""
        files = FilesFactory()
        self.assertTrue(files != None)
        files.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertTrue(files.id != None)
        files = Files.find(files.id)
        files.delete()
        files = Files.find(files.id)
        self.assertEqual(files.active, False)

    def test_serialize_a_files(self):
        """It should Serialize a files and add it to the database"""
        files = FilesFactory()
        self.assertTrue(files != None)
        files.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertTrue(files.id != None)
        files = Files.find(files.id)
        data = files.serialize()
        self.assertNotEqual(data, None)
        self.assertIn("id", data)
        self.assertEqual(data["id"], files.id)
        self.assertIn("webbot_id", data)
        self.assertEqual(data["webbot_id"], files.webbot_id)
        self.assertIn("name", data)
        self.assertEqual(data["name"], files.name)
        self.assertIn("s3_path", data)
        self.assertEqual(data["s3_path"], files.s3_path)
        self.assertIn("file_type", data)
        self.assertEqual(data["file_type"], files.file_type)
        self.assertIn("source", data)
        self.assertEqual(data["source"], files.source)
        self.assertIn("labels", data)
        self.assertEqual(data["labels"], files.labels)
        self.assertIn("created_date", data)
        self.assertEqual(data["created_date"], files.created_date.isoformat())
        self.assertIn("modified_date", data)
        self.assertEqual(data["modified_date"], files.modified_date.isoformat())
        self.assertIn("active", data)
        self.assertEqual(data["active"], files.active)
        self.assertIn("status", data)
        self.assertEqual(data["status"], files.status)
        self.assertIn("allow_questions", data)
        self.assertEqual(data["allow_questions"], files.allow_questions)
        self.assertIn("extra_info", data)
        self.assertEqual(data["extra_info"], files.extra_info)

    def test_deserialize_a_files(self):
        """It should Deserialize a files and add it to the database"""
        files = FilesFactory()
        self.assertTrue(files != None)
        files.create()
        data = files.serialize()
        self.assertNotEqual(data, None)
        files = Files()
        files.deserialize(data)
        self.assertNotEqual(files, None)
        self.assertEqual(files.id, None)
        self.assertEqual(files.webbot_id, data["webbot_id"])
        self.assertEqual(files.name, data["name"])
        self.assertEqual(files.s3_path, data["s3_path"])
        self.assertEqual(files.file_type, data["file_type"])
        self.assertEqual(files.source, data["source"])
        self.assertEqual(files.labels, data["labels"])
        self.assertEqual(files.active, data["active"])
        self.assertEqual(files.status, data["status"])
        self.assertEqual(files.allow_questions, data["allow_questions"])
        self.assertEqual(files.extra_info, data["extra_info"])

    def test_deserialize_bad_data(self):
        """It should fail deserializing bad data"""
        files = Files()
        self.assertRaises(DataValidationError, files.deserialize, "data")
        self.assertRaises(DataValidationError, files.deserialize, None)
        self.assertRaises(DataValidationError, files.deserialize, 123)
        self.assertRaises(DataValidationError, files.deserialize, [])
        self.assertRaises(DataValidationError, files.deserialize, {})

    def test_find_all_files(self):
        """Find a files by ID"""
        FilesFactory.reset_sequence(0)
        files = [FilesFactory(), FilesFactory(), FilesFactory()]
        created_files = [file.create() for file in files]
        db_files = Files.all()
        self.assertEqual(db_files.count(), len(files))

    def test_find_by_webbot_id(self):
        """Find a files by webbot_id"""
        FilesFactory.reset_sequence(0)
        files = [FilesFactory(), FilesFactory(), FilesFactory()]
        for file in files:
            file.create()
        db_files = Files.find_by_webbot_id(-2)
        self.assertEqual(len(files), db_files.count())

    def test_find_by_name(self):
        """Find a files by name"""
        FilesFactory.reset_sequence(0)
        file = FilesFactory()
        file.name = "Test"
        file.create()
        db_file = Files.find_by_name("Test")[0]
        self.assertEqual(db_file, file)

    def test_find_by_status(self):
        """Find a files by status"""
        FilesFactory.reset_sequence(0)
        file = FilesFactory()
        file.status = "Test"
        file.create()
        db_file = Files.find_by_status("Test")[0]
        self.assertEqual(db_file, file)

    def test_deserialize_missing_data(self):
        """It should not deserialize a Files with missing data"""
        data = {"id": 1, "name": "Test"}
        files = Files()
        self.assertRaises(DataValidationError, files.deserialize, data)

    def test_find_or_404_found(self):
        """Find or return 404 not found"""
        files = FilesFactory()
        files.create()
        db_files = Files.find_or_404(files.id)
        self.assertNotEqual(files, None)
        self.assertEqual(files.id, db_files.id)

    def test_find_or_404_not_found(self):
        """It should return 404 not found"""
        self.assertRaises(NotFound, Files.find_or_404, 0)
