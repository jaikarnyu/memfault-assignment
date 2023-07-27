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
Package: service
Package for the application models and service routes
This module creates and configures the Flask app and sets up the logging
and SQL database
"""
import sys
from flask import Flask, jsonify
from service import config
from service.common import log_handlers, status
from service.models.files import Files, DataValidationError, db
import logging
import traceback
from flask_migrate import Migrate
import sqlalchemy_utils
from service.common.textract_handler import TextractHandler


# Create Flask application
app = Flask(__name__)
app.config.from_object(config)
app.config["SQLALCHEMY_POOL_RECYCLE"] = 3600

textract_handler = TextractHandler(app.logger, config)


# Dependencies require we import the routes AFTER the Flask app is created
# pylint: disable=wrong-import-position, wrong-import-order, cyclic-import
from service.routes import files  # noqa: F401, E402
from service.common import error_handlers, cli_commands  # noqa: F401, E402

# Set up logging for production
log_handlers.init_logging(app, "knowledge_service.log")

app.logger.setLevel(logging.DEBUG)


app.logger.info(70 * "*")
app.logger.info("  W E B B O T  S E R V I C E  ".center(70, "*"))
app.logger.info(70 * "*")


try:
    db.init_app(app)
    Files.init_db(app)  # make our sqlalchemy tables
except Exception as error:  # pylint: disable=broad-except
    app.logger.critical("%s: Cannot continue", error)
    # gunicorn requires exit code 4 to stop spawning workers when they die
    sys.exit(4)

migrate = Migrate(app, db)
app.logger.info("Service initialized!")


@app.errorhandler(status.HTTP_400_BAD_REQUEST)
@app.errorhandler(status.HTTP_404_NOT_FOUND)
@app.errorhandler(status.HTTP_405_METHOD_NOT_ALLOWED)
@app.errorhandler(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
def bad_request_error(error):
    """Creates a generic bad request error."""
    app.logger.warning("Bad Request: %s", error)
    print(traceback.format_exc())
    return (
        jsonify(
            status=status.HTTP_400_BAD_REQUEST,
            error="BadRequestError",
            message=str(error),
            traceback=traceback.format_exc(),
        ),
        status.HTTP_400_BAD_REQUEST,
    )


@app.errorhandler(DataValidationError)
def request_validation_error(error):
    """Creates a request validation error."""
    app.logger.warning("ValidationError: %s", error)
    return (
        jsonify(
            status=status.HTTP_400_BAD_REQUEST,
            error="ValidationError",
            message=str(error),
        ),
        status.HTTP_400_BAD_REQUEST,
    )


@app.errorhandler(Exception)
def generic_error(error):
    """Creates a generic error."""
    app.logger.warning("Exception: %s", error)
    return (
        jsonify(
            status=status.HTTP_400_BAD_REQUEST,
            error="ValidationError",
            message=str(error),
            traceback=traceback.format_exc(),
        ),
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
