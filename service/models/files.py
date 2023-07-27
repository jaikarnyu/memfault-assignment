# Copyright 2016, 2021 John Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Models for File Demo Service

All of the models are stored in this module

Models
------
File - A File used in the File Store

Attributes:
-----------
name (string) - the name of the File
category (string) - the category the File belongs to (i.e., dog, cat)
available (boolean) - True for Files that are available for adoption

"""
import logging
from enum import Enum
from datetime import date, datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy_json import mutable_json_type
from sqlalchemy_utils import URLType
from service.common.enum_handler import *
import sqlalchemy_utils

logger = logging.getLogger("flask.app")

# Create the SQLAlchemy object to be initialized later in init_db()
db = SQLAlchemy()


def init_db(app):
    """Initialize the SQLAlchemy app"""
    Files.init_db(app)


class DataValidationError(Exception):
    """Used for an data validation errors when deserializing"""


class Files(db.Model):
    """
    Class that represents a File

    This version uses a relational database for persistence which is hidden
    from us by SQLAlchemy's object relational mappings (ORM)
    """

    ##################################################
    # Table Schema
    ##################################################
    id = db.Column(db.Integer, primary_key=True)
    webbot_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(), nullable=False)
    s3_path = db.Column(db.String(), nullable=False, default="")
    file_type = db.Column(db.String(), nullable=False, default="")
    source = db.Column(
        db.String(), nullable=False, default=FileSource.KNOWLEDGE.value
    )
    source_url = db.Column(URLType, nullable=True, default=None)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())
    modified_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())
    active = db.Column(db.Boolean, nullable=False, default=True)
    status = db.Column(db.String(), nullable=False, default=FileStatus.CREATED.value)
    allow_questions = db.Column(db.Boolean, nullable=False, default=True)
    public = db.Column(db.Boolean, nullable=True, default=False)
    labels = db.Column(
        mutable_json_type(dbtype=JSONB, nested=True), nullable=True, default={}
    )
    extra_info = db.Column(
        mutable_json_type(dbtype=JSONB, nested=True), nullable=True, default={}
    )

    ##################################################
    # INSTANCE METHODS
    ##################################################

    def __repr__(self):
        return f"<File {self.name} id=[{self.id}]>"

    def create(self):
        """
        Creates a File to the database
        """
        logger.info("Creating %s", self.name)
        # id must be none to generate next primary key
        self.id = None  # pylint: disable=invalid-name
        self.created_date = datetime.utcnow()
        self.modified_date = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def update(self):
        """
        Updates a File to the database
        """
        logger.info("Saving %s", self.name)
        if not self.id:
            raise DataValidationError("Update called with empty ID field")
        self.modified_date = datetime.utcnow()
        db.session.commit()

    def delete(self):
        """Removes a File from the data store"""
        logger.info("Deleting %s", self.name)
        self.active = False
        self.modified_date = datetime.utcnow()
        db.session.commit()

    def serialize(self):
        """Serializes a File into a dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "labels": self.labels,
            "webbot_id": self.webbot_id,
            "s3_path": self.s3_path,
            "file_type": self.file_type,
            "created_date": self.created_date.isoformat(),
            "modified_date": self.modified_date.isoformat(),
            "active": self.active,
            "status": self.status,
            "allow_questions": self.allow_questions,
            "extra_info": self.extra_info,
            "source": self.source,
            "source_url": self.source_url,
            "public": self.public,
            "file_id": self.id,
        }

    def deserialize(self, data: dict):
        """
        Deserializes a File from a dictionary
        Args:
            data (dict): A dictionary containing the File data
        """
        try:
            self.name = data["name"]
            self.labels = data.get("labels", {})
            self.webbot_id = int(data["webbot_id"])
            self.s3_path = data.get("s3_path", "")
            self.file_type = data.get("file_type", "")
            self.source = data.get("source", FileSource.KNOWLEDGE.value)
            self.active = data.get("active", True)
            self.status = data.get("status", FileStatus.CREATED.value)
            self.allow_questions = data.get("allow_questions", True)
            self.extra_info = data.get("extra_info", {})
            self.source_url = data.get("source_url", None)
            self.public = data.get("public", False)
        except AttributeError as error:
            raise DataValidationError("Invalid attribute: " + error.args[0]) from error
        except KeyError as error:
            raise DataValidationError(
                "Invalid File: missing " + error.args[0]
            ) from error
        except TypeError as error:
            raise DataValidationError(
                "Invalid File: body of request contained bad or no data " + str(error)
            ) from error
        except ValueError as error:
            raise DataValidationError(
                "Invalid Webbot: body of request contained bad or no data " + str(error)
            ) from error
        return self

    ##################################################
    # CLASS METHODS
    ##################################################

    @classmethod
    def init_db(cls, app: Flask):
        """Initializes the database session

        :param app: the Flask app
        :type data: Flask

        """
        logger.info("Initializing database")
        # This is where we initialize SQLAlchemy from the Flask app
        # db.init_app(app)
        app.app_context().push()
        db.create_all()  # make our sqlalchemy tables

    @classmethod
    def all(cls) -> list:
        """Returns all of the Files in the database"""
        logger.info("Processing all Files")
        return cls.query.filter(cls.active == True)

    @classmethod
    def find(cls, file_id: int):
        """Finds a File by it's ID

        :param file_id: the id of the File to find
        :type file_id: int

        :return: an instance with the file_id, or None if not found
        :rtype: File

        """
        logger.info("Processing lookup for id %s ...", file_id)
        return cls.query.get(file_id)

    @classmethod
    def find_or_404(cls, file_id: int):
        """Find a File by it's id

        :param file_id: the id of the File to find
        :type file_id: int

        :return: an instance with the file_id, or 404_NOT_FOUND if not found
        :rtype: File

        """
        logger.info("Processing lookup or 404 for id %s ...", file_id)
        return cls.query.get_or_404(file_id)

    @classmethod
    def find_by_name(cls, name: str) -> list:
        """Returns all Files with the given name

        :param name: the name of the Files you want to match
        :type name: str

        :return: a collection of Files with that name
        :rtype: list

        """
        logger.info("Processing name query for %s ...", name)
        return cls.query.filter(cls.name == name and cls.active == True)

    @classmethod
    def find_by_webbot_id(cls, webbot_id: int) -> list:
        """Returns all of the Files of a user

        :param webbot_id: webbot_id of the Files you want to match
        :type webbot_id: int

        :return: a collection of Files in that category
        :rtype: list

        """
        logger.info("Processing webbot id query for %s ...", webbot_id)
        return cls.query.filter(cls.webbot_id == webbot_id and cls.active == True)

    @classmethod
    def find_by_status(cls, status) -> list:
        """Returns all Files by their status

        :param status : FileStatus Enum
        :type FileStatus: Enum

        :return: a collection of Files that are available
        :rtype: list

        """
        logger.info("Processing status query for %s ...", status)
        return cls.query.filter(cls.status == status)
