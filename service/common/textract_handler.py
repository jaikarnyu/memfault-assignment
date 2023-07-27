import webbrowser, os
import json
import boto3
import io
from io import BytesIO
import sys
from pprint import pprint
import fitz
from PIL import Image
import pandas as pd
import re
from collections import defaultdict


class TextractHandler(object):
    def __init__(self, logger, config):
        self.config = config
        self.logger = logger
        self.client = boto3.client(
            "textract",
            aws_access_key_id=config.AWS_ACCESS_KEY,
            aws_secret_access_key=config.AWS_SECRET_KEY,
            region_name=config.AWS_REGION,
        )

    @staticmethod
    def get_rows_columns_map(table_result, blocks_map):
        rows = {}
        for relationship in table_result["Relationships"]:
            if relationship["Type"] == "CHILD":
                for child_id in relationship["Ids"]:
                    cell = blocks_map[child_id]
                    if cell["BlockType"] == "CELL":
                        row_index = cell["RowIndex"]
                        col_index = cell["ColumnIndex"]
                        if row_index not in rows:
                            # create new row
                            rows[row_index] = {}

                        # get the text value
                        rows[row_index][col_index] = TextractHandler.get_text(
                            cell, blocks_map
                        )
        return rows

    @staticmethod
    def get_text(result, blocks_map):
        text = ""
        if "Relationships" in result:
            for relationship in result["Relationships"]:
                if relationship["Type"] == "CHILD":
                    for child_id in relationship["Ids"]:
                        word = blocks_map[child_id]
                        if word["BlockType"] == "WORD":
                            text += word["Text"] + " "
                        if word["BlockType"] == "SELECTION_ELEMENT":
                            if word["SelectionStatus"] == "SELECTED":
                                text += "X "
        return text

    @staticmethod
    def get_kv_relationship(key_map, value_map, block_map):
        kvs = defaultdict(list)
        for block_id, key_block in key_map.items():
            value_block = TextractHandler.find_value_block(key_block, value_map)
            key = TextractHandler.get_text(key_block, block_map)
            val = TextractHandler.get_text(value_block, block_map)
            kvs[key].append(val)
        return kvs

    @staticmethod
    def find_value_block(key_block, value_map):
        for relationship in key_block["Relationships"]:
            if relationship["Type"] == "VALUE":
                for value_id in relationship["Ids"]:
                    value_block = value_map[value_id]
        return value_block

    @staticmethod
    def print_kvs(kvs):
        for key, value in kvs.items():
            print(key, ":", value)

    @staticmethod
    def search_value(kvs, search_key):
        for key, value in kvs.items():
            if re.search(search_key, key, re.IGNORECASE):
                return value

    def extract_key_values(self, blocks):
        kvs = {}
        key_map = {}
        value_map = {}
        block_map = {}
        for page in blocks:
            for block in page:
                block_id = block["Id"]
                block_map[block_id] = block
                if block["BlockType"] == "KEY_VALUE_SET":
                    if "KEY" in block["EntityTypes"]:
                        key_map[block_id] = block
                    else:
                        value_map[block_id] = block
        new_kvs = TextractHandler.get_kv_relationship(key_map, value_map, block_map)
        kvs.update(new_kvs)
        return kvs

    def extract_tables(self, blocks, column_names=[]):

        blocks_map = {}
        table_blocks = []
        df = pd.DataFrame()
        dfs = []
        for page in blocks:
            for block in page:
                blocks_map[block["Id"]] = block
                if block["BlockType"] == "TABLE":
                    table_blocks.append(block)

        if len(table_blocks) <= 0:
            self.logger.info("NO Table FOUND")

        self.logger.info("Generating dataframe")

        for index, table in enumerate(table_blocks):
            rows = TextractHandler.get_rows_columns_map(table, blocks_map)
            csv = ""
            for row_index, cols in rows.items():
                for col_index, text in cols.items():
                    csv += "{}".format(text.strip().lower()) + ":::"
                csv += "\n"

            valid_table = False
            if len(column_names) == 0:
                valid_table = True
            else:
                for col in column_names:
                    if col in csv:
                        valid_table = True
                        break

            if valid_table:
                print("valid table found")
                new_df = pd.read_csv(io.StringIO(csv), delimiter=":::")
                dfs.append(new_df)

        return dfs

    @staticmethod
    def get_document_bytes(file):
        doc = fitz.Document(file)
        bytes = []
        for i in range(len(doc)):
            imgs = doc.get_page_images(i)
            for img in imgs:
                xref = img[0]
                image = doc.extract_image(xref)
                image_bytes = image["image"]
                bytes.append(image_bytes)
        return bytes

    def analyse_document(self, file):
        bytes = TextractHandler.get_document_bytes(file)
        blocks = []
        # process using image bytes
        if type(bytes) == list:
            for each in bytes:
                response = self.client.analyze_document(
                    Document={"Bytes": each}, FeatureTypes=["TABLES", "FORMS"]
                )
                blocks.append(response["Blocks"])
        else:
            response = self.client.analyze_document(
                Document={"Bytes": bytes}, FeatureTypes=["TABLES", "FORMS"]
            )
            blocks.append(response["Blocks"])
        # Get the text blocks
        return blocks

    def extract_raw_text(self, blocks):
        text = ""
        for page in blocks:
            for block in page:
                if block["BlockType"] == "LINE":
                    text += block["Text"] + " "
        return text

    def extract_data_from_file(self, file, column_names=[]):
        try:
            blocks = self.analyse_document(file)
            dfs = self.extract_tables(blocks, column_names)
            kvs = self.extract_key_values(blocks)
            if len(kvs.keys()) > 0:
                kv_df = pd.json_normalize(kvs)
                dfs.append(kv_df)
            text = self.extract_raw_text(blocks)
            return text, dfs
        except Exception as e:
            self.logger.error("Textract : Error while extracting image data from file")
            self.logger.error(e)
            return None, None
