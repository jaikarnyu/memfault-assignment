# Copyright 2016, 2019 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this files except in compliance with the License.
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
Files Store Service

Paths:
------
GET /files - Returns a list all of the Files
GET /files/{id} - Returns the Files with a given id number
POST /files - creates a new Files record in the database
PUT /files/{id} - updates a Files record in the database
DELETE /files/{id} - deletes a Files record in the database
"""
from flask import jsonify, request, url_for, abort
from service.models.files import (
    Files,
    DataValidationError,
)
from service.common.enum_handler import *
from service.common import status  # HTTP Status Codes
from .. import app, textract_handler  # Import Flask application
import service.config as conf
import os
from service.common.s3_handler import S3Handler
from flask_restx import Api, Resource, fields, reqparse, inputs, Namespace
from flask import send_file
from werkzeug.datastructures import FileStorage
import mimetypes
from datetime import datetime
import traceback
import uuid


API = Api(
    app,
    version="1.0.0",
    title="Files service",
    description="Files server for webbot",
    default="Files",
    default_label="Files-Operations",
    doc="/",
    prefix="/api",
)


# Initialize S3 Handler
s3_handler = S3Handler()


"""
flask-restx model for service.models.files.Files
"""
FILES_MODEL = API.model(
    "Files",
    {
        "id": fields.Integer(
            readOnly=True,
            required=False,
            description="The unique id assigned internally by service",
        ),
        "name": fields.String(required=True, description="The name of the files"),
        "webbot_id": fields.Integer(
            required=True, description="The webbot id of the files"
        ),
        "s3_path": fields.String(
            required=False, description="The s3_path of the files", default=""
        ),
        "labels": fields.Raw(
            required=False, description="The labels of the files", default={}
        ),
        "created_date": fields.DateTime(
            required=False,
            description="The created at of the files",
        ),
        "modified_date": fields.DateTime(
            required=False,
            description="The updated at of the files",
        ),
        "status": fields.String(
            required=False,
            description="The status of the files",
            default=FileStatus.CREATED.value,
            choices=file_status_choices,
        ),
        "file_type": fields.String(
            required=False, description="The file type of the files", default=""
        ),
        "source": fields.String(
            required=False,
            description="The source of the files",
            choices=file_source_choices,
            default=FileSource.KNOWLEDGE.value,
        ),
        "allow_questions": fields.Boolean(
            required=False, description="The allow questions of the files", default=True
        ),
        "extra_info": fields.Raw(
            required=False, description="The extra info of the files", default={}
        ),
        "active": fields.Boolean(
            required=False, description="The active status of the files", default=True
        ),
        "public": fields.Boolean(
            required=False, description="The public status of the files", default=False
        ),
        "source_url": fields.Url(
            required=False, description="The source url of the files", default=None
        ),
    },
)

CREATE_FILES_MODEL = API.model(
    "Create Files",
    {
        "name": fields.String(required=True, description="The name of the files"),
        "webbot_id": fields.Integer(
            required=True, description="The webbot id of the files"
        ),
        "s3_path": fields.String(
            required=False, description="The s3_path of the files", default=""
        ),
        "source": fields.String(
            required=False,
            description="The source of the files",
            choices=file_source_choices,
            default=FileSource.KNOWLEDGE.value,
        ),
        "source_url": fields.Url(
            required=False, description="The source url of the files", default=None
        ),
        "public": fields.Boolean(
            required=False, description="The public status of the files", default=False
        ),
        "allow_questions": fields.Boolean(
            required=False, description="The allow questions of the files", default=True
        ),
        "extra_info": fields.Raw(
            required=False, description="The extra info of the files", default={}
        ),
        "active": fields.Boolean(
            required=False, description="The active status of the files", default=True
        ),
        "labels": fields.Raw(
            required=False, description="The labels of the files", default={}
        ),
    },
)

UPDATE_FILES_MODEL = API.model(
    "Update Files",
    {
        "name": fields.String(required=False, description="The name of the files"),
        "source": fields.String(
            required=False,
            description="The source of the files",
            choices=file_source_choices,
            default=FileSource.KNOWLEDGE.value,
        ),
        "source_url": fields.Url(
            required=False, description="The source url of the files", default=None
        ),
        "public": fields.Boolean(
            required=False, description="The public status of the files", default=False
        ),
        "allow_questions": fields.Boolean(
            required=False, description="The allow questions of the files", default=True
        ),
        "extra_info": fields.Raw(
            required=False, description="The extra info of the files", default={}
        ),
        "active": fields.Boolean(
            required=False, description="The active status of the files", default=True
        ),
        "labels": fields.Raw(
            required=False, description="The labels of the files", default={}
        ),
    },
)

"""
Query Parsers
"""

FILES_QUERY_PARSER = reqparse.RequestParser()
FILES_QUERY_PARSER.add_argument(
    "webbot_id", type=int, required=False, help="Filter by webbot id"
)
FILES_QUERY_PARSER.add_argument(
    "name", type=str, required=False, help="Filter by files name"
)
FILES_QUERY_PARSER.add_argument(
    "file_status",
    type=str,
    required=False,
    help="Filter by files status",
    choices=file_status_choices,
)

FILES_QUERY_PARSER.add_argument(
    "source", type=str, required=False, help="Filter by files source"
)

FILES_QUERY_PARSER.add_argument(
    "public", type=inputs.boolean, required=False, help="Filter by files public status"
)

FILES_QUERY_PARSER.add_argument(
    "active", type=inputs.boolean, required=False, help="Filter by files active status"
)


UPLOAD_FILE_PARSER = reqparse.RequestParser()
UPLOAD_FILE_PARSER.add_argument(
    "files[]",
    type=FileStorage,
    location="files",
    required=True,
    help="Files to upload",
)


######################################################################
# GET HEALTH CHECK
######################################################################
@app.route("/healthcheck")
def healthcheck():
    """Let them know our heart is still beating"""
    return jsonify(status=200, message="Healthy"), status.HTTP_200_OK


######################################################################


"""
Flask-RESTX resource for service.models.files.Files

"""


@API.route("/files/<int:file_id>")
@API.param("file_id", "The Files identifier")
@API.response(404, "File not found")
class FilesResource(Resource):
    @API.doc("get_files")
    @API.marshal_with(FILES_MODEL)
    @API.response(400, "Files not found")
    def get(self, file_id):
        """Returns a single Files"""
        app.logger.info("Request for files with id: %s", file_id)
        files = Files.find(file_id)
        if not files:
            abort(
                status.HTTP_404_NOT_FOUND,
                "Files with id '{}' was not found.".format(file_id),
            )
        return files.serialize(), status.HTTP_200_OK

    @API.doc("update_files")
    @API.expect(UPDATE_FILES_MODEL)
    @API.response(400, "The posted Files data was not valid")
    @API.response(404, "Files not found")
    @API.marshal_with(FILES_MODEL, code=200)
    def put(self, file_id):
        """Updates a Files"""
        app.logger.info("Request to update files with id: %s", file_id)
        check_content_type("application/json")
        files = Files.find(file_id)
        if not files:
            abort(
                status.HTTP_404_NOT_FOUND,
                "Files with id '{}' was not found.".format(file_id),
            )
        data = request.get_json()
        files.deserialize(data)
        files.id = file_id
        files.update()
        return files.serialize(), status.HTTP_200_OK

    @API.doc("delete_files")
    @API.response(204, "Files deleted")
    def delete(self, file_id):
        """Deletes a Files"""
        app.logger.info("Request to delete files with id: %s", file_id)
        files = Files.find(file_id)
        if files:
            files.delete()
        return "", status.HTTP_204_NO_CONTENT


@API.route("/files")
class FilesCollection(Resource):
    """Handles all interactions with collections of Files"""

    @API.doc("list_files")
    @API.expect(FILES_QUERY_PARSER)
    @API.marshal_list_with(FILES_MODEL)
    def get(self):
        """Returns all of the Files"""
        app.logger.debug("Request for files list")
        files = []
        query_args = request.args
        if len(query_args) > 0:
            files = Files.query.filter_by(**query_args)
        else:
            files = Files.all()

        results = [file.serialize() for file in files]
        app.logger.debug("Returning %d files", len(results))
        return results, status.HTTP_200_OK

    @API.doc("create_files")
    @API.expect(CREATE_FILES_MODEL)
    @API.response(400, "The posted Files data was not valid")
    @API.response(201, "Files created successfully")
    @API.marshal_with(FILES_MODEL, code=201)
    def post(self):
        """Creates a Files"""
        app.logger.info("Request to create a files")
        check_content_type("application/json")
        files = Files()
        data = request.get_json()
        files.deserialize(data)
        files.create()
        app.logger.info("Files with new id [%s] saved!", files.id)
        return files.serialize(), status.HTTP_201_CREATED


######################################################################
# UPLOAD A FILE
######################################################################


@API.doc("upload_file")
@API.route("/files/upload/<int:webbot_id>", methods=["POST"])
@API.param("webbot_id", "The webbot id of the files")
class UploadFile(Resource):
    """_upload_file_

    This endpoint will upload a file to webbot_id
    """

    @API.doc("upload_file")
    @API.expect(UPLOAD_FILE_PARSER)
    @API.response(400, "The posted Files data was not valid")
    @API.response(200, "File uploaded successfully")
    def post(self, webbot_id):
        """
        This endpoint will upload a file to webbot_id

        :param webbot_id: webbot_id of the webbot
        :type webbot_id: int
        :return: file name
        """

        app.logger.info("Uploading file for webbot {0}".format(webbot_id))

        local_file_path = conf.LOCAL_FILE_PATH.format(webbot_id=webbot_id)

        # Make directory if not exists
        if not os.path.isdir(local_file_path):
            os.mkdir(local_file_path)

        if request.method == "POST":

            if "files[]" not in request.files:
                app.logger.info("No file part")
                return (
                    {"message": "No files to upload"},
                    status.HTTP_400_BAD_REQUEST,
                )

            app.logger.info(request.files.getlist("files[]"))
            files = request.files.getlist("files[]")
            app.logger.info("Files found {0}".format(len(files)))
            files_meta = []
            for file in files:
                if file:
                    table_file_ids = []
                    text_file_id = None
                    file_meta = Files()
                    file_meta.name = file.filename
                    file_meta.status = FileStatus.UPLOADING.value
                    file_meta.webbot_id = webbot_id
                    file_meta.file_type = mimetypes.guess_type(file.filename)[0]
                    file_meta.create()
                    try:

                        if "/" in file.filename:
                            file.filename = file.filename.split("/")[-1]
                        file_path = os.path.join(local_file_path, file.filename)
                        file.save(file_path)

                        s3_handler.upload_files(
                            file_path,
                            bucket=conf.AWS_S3_BUCKET,
                            prefix=conf.AWS_S3_PREFIX.format(webbot_id=webbot_id),
                        )
                        file_meta.s3_path = (
                            conf.AWS_S3_PREFIX.format(webbot_id=webbot_id)
                            + file.filename
                        )
                        file_meta.status = FileStatus.UPLOAD_SUCCESS.value
                        app.logger.info("File uploaded {0}".format(file.filename))
                        file_meta.update()

                        # text, dfs = textract_handler.extract_data_from_file(file_path)
                        text = None
                        dfs = None
                        if dfs:
                            count = 1
                            for df in dfs:
                                file_name = (
                                    "file_{file_id}_table_".format(file_id=file_meta.id)
                                    + str(count)
                                    + ".csv"
                                )
                                local_path = os.path.join(local_file_path, file_name)
                                df.to_csv(local_path, sep='\t', encoding='utf-8')
                                s3_handler.upload_files(
                                    local_path,
                                    bucket=conf.AWS_S3_BUCKET,
                                    prefix=conf.AWS_S3_PREFIX.format(
                                        webbot_id=webbot_id
                                    ),
                                )
                                file = Files()
                                file.name = file_name
                                file.status = FileStatus.UPLOAD_SUCCESS.value
                                file.webbot_id = webbot_id
                                file.file_type = "application/pickle"
                                file.s3_path = (
                                    conf.AWS_S3_PREFIX.format(webbot_id=webbot_id)
                                    + file_name
                                )
                                file.create()
                                table_file_ids.append(file.id)
                                count += 1
                        if text:
                            file_name = "file_{file_id}_text.txt".format(
                                file_id=file_meta.id
                            )
                            local_path = os.path.join(local_file_path, file_name)
                            with open(local_path, "w") as f:
                                f.write(text)
                            s3_handler.upload_files(
                                local_path,
                                bucket=conf.AWS_S3_BUCKET,
                                prefix=conf.AWS_S3_PREFIX.format(webbot_id=webbot_id),
                            )
                            file = Files()
                            file.name = file_name
                            file.status = FileStatus.UPLOAD_SUCCESS.value
                            file.webbot_id = webbot_id
                            file.file_type = "text/plain"
                            file.s3_path = (
                                conf.AWS_S3_PREFIX.format(webbot_id=webbot_id)
                                + file_name
                            )
                            file.create()
                            text_file_id = file.id

                    except Exception as e:
                        app.logger.error(
                            "Error uploading file {0}".format(file.filename)
                        )
                        app.logger.error(str(e))
                        app.logger.error(traceback.format_exc())
                        file_meta.status = FileStatus.UPLOAD_FAILED.value
                        file_meta.update()

                    files_meta.append(
                        {
                            "file_id": file_meta.id,
                            "filename": file_meta.name,
                            "status": file_meta.status,
                            "tables": table_file_ids,
                            "text_file_id": text_file_id,
                            "table_count": len(table_file_ids),
                        }
                    )

            app.logger.info("Files successfully uploaded")
            return (
                {
                    "file_count": len(files),
                    "results": files_meta,
                    "message": "Upload Success",
                },
                status.HTTP_200_OK,
            )


######################################################################
# DOWNLOAD A FILE
######################################################################


@API.route("/files/download/<int:webbot_id>/<int:file_id>")
@API.param("webbot_id", "The webbot id of the files")
@API.param("file_id", "The file id of the files")
class DownloadFile(Resource):
    @API.doc("download_file")
    @API.response(200, "File uploaded successfully")
    def get(self, webbot_id, file_id):
        """
        This endpoint will download a file from webbot_id

        :param webbot_id: webbot_id to download file from
        :type webbot_id: int
        :param file_id: file_id to download
        :type file_id: int

        :return: file
        """

        app.logger.info("Downloading file for webbot {0}".format(webbot_id))

        # Get file name
        file = Files.find(file_id)
        filename = file.name
        s3_path = file.s3_path
        local_file_path = conf.DOWNLOADS_PATH.format(webbot_id=webbot_id)
        if not os.path.exists(local_file_path):
            os.makedirs(local_file_path)

        local_file_path = local_file_path + filename

        # Download file from s3
        s3_handler.download_files(
            bucket=conf.AWS_S3_BUCKET, s3_path=s3_path, local_path=local_file_path
        )

        return send_file(local_file_path, as_attachment=True, download_name=filename)


######################################################################
#  U T I L I T Y   F U N C T I O N S
######################################################################


def check_content_type(content_type):
    """Checks that the media type is correct"""
    if "Content-Type" not in request.headers:
        app.logger.error("No Content-Type specified.")
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}",
        )

    if request.headers["Content-Type"] == content_type:
        return

    app.logger.error("Invalid Content-Type: %s", request.headers["Content-Type"])
    abort(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        f"Content-Type must be {content_type}",
    )
