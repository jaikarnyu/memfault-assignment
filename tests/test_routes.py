# Copyright 2016, 2022 John J. Rofrano. All Rights Reserved.
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
Files API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestFilesService
"""

import os
import logging
from unittest import TestCase


# from unittest.mock import MagicMock, patch
from urllib.parse import quote_plus
from service import app
from service.common import status
from service.models.files import db, init_db, Files, DataValidationError
from tests.factories import FilesFactory
from service import config as conf
from service.common.enum_handler import *

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/api/files"


######################################################################
#  T E S T   W E B B O T   S E R V I C E
######################################################################
class TestFilesService(TestCase):
    """Files Server Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Files).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    def _create_files(self, count):
        """Factory method to create files in bulk"""
        files = []
        for _ in range(count):
            test_files = FilesFactory()
            app.logger.info(test_files.serialize())
            response = self.client.post(BASE_URL, json=test_files.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test files",
            )
            new_files = response.get_json()
            test_files.id = new_files["id"]
            files.append(test_files)
        return files

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/healthcheck")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["status"], 200)
        self.assertEqual(data["message"], "Healthy")

    def test_get_files_list(self):
        """It should Get a list of Files"""
        self._create_files(5)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 5)

    def test_get_files(self):
        """It should Get a single Files"""
        # get the id of a files
        test_files = self._create_files(1)[0]
        response = self.client.get(f"{BASE_URL}/{test_files.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        logging.debug("Response data = %s", data)
        self.assertEqual(data["name"], test_files.name)
        self.assertEqual(data["webbot_id"], test_files.webbot_id)

    def test_get_files_not_found(self):
        """It should not Get a Files thats not found"""
        response = self.client.get(f"{BASE_URL}/0")
        logging.debug(response.get_json())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        logging.debug("Response data = %s", data)
        self.assertIn("was not found", data["message"])

    def test_create_files(self):
        """It should Create a new Files"""
        test_files = FilesFactory()
        logging.debug(test_files)
        logging.debug("Test Files: %s", test_files.serialize())
        response = self.client.post(BASE_URL, json=test_files.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check the data is correct
        new_files = response.get_json()
        self.assertEqual(new_files["name"], test_files.name)
        self.assertEqual(new_files["webbot_id"], test_files.webbot_id)

        # Check that the location header was correct
        location = BASE_URL + "/" + str(new_files["id"])
        response = self.client.get(location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_files = response.get_json()
        self.assertEqual(new_files["name"], test_files.name)
        self.assertEqual(new_files["webbot_id"], test_files.webbot_id)

    def test_update_files(self):
        """It should Update an existing Files"""
        # create a files to update
        test_files = FilesFactory()
        response = self.client.post(BASE_URL, json=test_files.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # update the files
        new_files = response.get_json()
        logging.debug(new_files)
        new_files["webbot_id"] = 2
        response = self.client.put(f"{BASE_URL}/{new_files['id']}", json=new_files)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_files = response.get_json()
        self.assertEqual(updated_files["webbot_id"], 2)

    def test_delete_files(self):
        """It should Delete a Files"""
        test_files = self._create_files(1)[0]
        response = self.client.delete(f"{BASE_URL}/{test_files.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(response.data), 0)
        # make sure they are deleted
        response = self.client.get(f"{BASE_URL}/{test_files.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_query_files_list_by_webbot_id(self):
        """It should Query Files by webbot_id"""
        files = self._create_files(10)
        test_webbot_id = files[0].webbot_id
        user_files = [files for files in files if files.webbot_id == test_webbot_id]
        response = self.client.get(
            BASE_URL,
            query_string="webbot_id={webbot_id}".format(webbot_id=test_webbot_id),
        )
        logging.debug("Response: %s", response.get_json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), len(user_files))
        # check the data just to be sure
        for files in data:
            self.assertEqual(files["webbot_id"], test_webbot_id)

    ######################################################################
    #  T E S T   S A D   P A T H S
    ######################################################################

    def test_create_files_no_data(self):
        """It should not Create a Files with missing data"""
        response = self.client.post(BASE_URL, json={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_files_no_content_type(self):
        """It should not Create a Files with no content type"""
        response = self.client.post(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_files_bad_webbot_id(self):
        """It should not Create a Files with bad available data"""
        test_files = FilesFactory()
        logging.debug(test_files)
        # change available to a string
        test_files.webbot_id = "true"
        response = self.client.post(BASE_URL, json=test_files.serialize())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_file_resource(self):
        """Test UploadFile resource"""
        webbot_id = 1
        with open("tests/test_data/SETUP01.pdf", "rb") as file:
            data = {"files[]": file}
            response = self.client.post(
                "/api/files/upload/{0}".format(webbot_id),
                data=data,
                content_type="multipart/form-data",
            )
            app.logger.info("Response: %s", response.status_code)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["file_count"], 1)
            self.assertEqual(response.json["results"][0]['table_count'], 0)
            self.assertEqual(response.json["message"], "Upload Success")

    def test_upload_file_resource_no_file(self):
        """Test UploadFile resource"""
        webbot_id = 1
        response = self.client.post(
            "/api/files/upload/{0}".format(webbot_id),
            data={},
            content_type="multipart/form-data",
        )
        app.logger.info("Response: %s", response.status_code)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["message"], "No files to upload")

    def test_download_file_resource(self):
        """Test DownloadFile resource"""
        webbot_id = 1
        with open("tests/test_data/test_file.txt", "rb") as file:
            data = {"files[]": file}
            response = self.client.post(
                "/api/files/upload/{0}".format(webbot_id),
                data=data,
                content_type="multipart/form-data",
            )
            app.logger.info("Response: %s", response.status_code)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["file_count"], 1)
            self.assertEqual(response.json["message"], "Upload Success")
            results = response.json["results"]

        file_id = results[0]["file_id"]
        filename = results[0]["filename"]
        response = self.client.get(
            "/api/files/download/{0}/{1}".format(webbot_id, file_id),
            content_type="multipart/form-data",
        )
        app.logger.info("Response: %s", response.status_code)
        self.assertEqual(response.status_code, 200)
        # check if file exists in download folder
        local_file_path = conf.DOWNLOADS_PATH.format(webbot_id=webbot_id)
        file_path = os.path.join(local_file_path, filename)
        self.assertTrue(os.path.exists(file_path))

    ######################################################################
    #  T E S T   M O C K S
    ######################################################################

    # @patch('service.routes.Files.find_by_name')
    # def test_bad_request(self, bad_request_mock):
    #     """It should return a Bad Request error from Find By Name"""
    #     bad_request_mock.side_effect = DataValidationError()
    #     response = self.client.get(BASE_URL, query_string='name=fido')
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # @patch('service.routes.Files.find_by_name')
    # def test_mock_search_data(self, files_find_mock):
    #     """It should showing how to mock data"""
    #     files_find_mock.return_value = [MagicMock(serialize=lambda: {'name': 'fido'})]
    #     response = self.client.get(BASE_URL, query_string='name=fido')
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
