import xmltodict
import json
import yaml
import unittest
import unidecode
import sys
import os
import re
from jsonschema import validate
import markdown
import logging
import datetime
from termcolor import colored
import unidecode
import markdown

VERBOSE = False

def setVerbose():
    global VERBOSE
    VERBOSE = True

###
### Path
###
paths_template_list = """
        "${PATH_PREFIX}/${table}s": {
            "summary": "Path used to manage the list of ${table}s.",
            "description": "The REST endpoint/path used to list and create zero or more `${TABLE}`.  This path contains a `GET` and `POST` operation to perform the list and create tasks, respectively.",

            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "$ref": "#/components/schemas/${TABLE}"
                                    }
                                }
                            }
                        },
                        "description": "Successful response - returns an array of `${TABLE}` entities."
                    }
                },
                "operationId": "get${TABLE}s",
                "summary": "List All ${TABLE}s",
                "description": "Gets a list of all `${TABLE}` entities."
            }
"""
paths_template_create = """
            "post": {
                "requestBody": {
                    "description": "A new `${TABLE}` to be created.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/${TABLE}"
                            }
                        }
                    },
                    "required": true
                },
                "responses": {
                    "201": {
                        "description": "Successful response."
                    }
                },
                "operationId": "create${TABLE}",
                "summary": "Create a ${TABLE}",
                "description": "Creates a new instance of a `${TABLE}`."
            }

"""
paths_template_read = """

        "${PATH_PREFIX}/${table}s/{${table}Id}": {
            "summary": "Path used to manage a single ${TABLE}.",
            "description": "The REST endpoint/path used to get, update, and delete single instances of an `${TABLE}`.  This path contains `GET`, `PUT`, and `DELETE` operations used to perform the get, update, and delete tasks, respectively.",

            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/${TABLE}"
                                }
                            }
                        },
                        "description": "Successful response - returns a single `${TABLE}`."
                    }
                },
                "operationId": "get${TABLE}",
                "summary": "Get a ${TABLE}",
                "description": "Gets the details of a single instance of a `${TABLE}`."
            }

"""
paths_template_update = """
            "put": {
                "requestBody": {
                    "description": "Updated `${TABLE}` information.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/${TABLE}"
                            }
                        }
                    },
                    "required": true
                },
                "responses": {
                    "202": {
                        "description": "Successful response."
                    }
                },
                "operationId": "update${TABLE}",
                "summary": "Update a ${TABLE}",
                "description": "Updates an existing `${TABLE}`."
            },
            "delete": {
                "responses": {
                    "204": {
                        "description": "Successful response."
                    }
                },
                "operationId": "delete${TABLE}",
                "summary": "Delete a ${TABLE}",
                "description": "Deletes an existing `${TABLE}`."
            }
"""
paths_template_parameters = """            
            "parameters": [
                {
                    "name": "${table}Id",
                    "description": "A unique identifier for a `${TABLE}`.",
                    "schema": {
                        "type": "string"
                    },
                    "in": "path",
                    "required": true
                }
            ]

"""


def paths_table(table: str, path_prefix: str = "", paths_template=""):
    l_paths_template = paths_template.replace("${PATH_PREFIX}", path_prefix)
    l_paths_template = l_paths_template.replace("${TABLE}", table)
    l_paths_template = l_paths_template.replace("${table}", table.lower())
    return l_paths_template


def create_path(entities):
    f_paths_template = ""
    sep = ""
    for entity in entities:
        if ("PATH" in entities[entity]):
            if ("read-only" in entities[entity]["PATH_OPERATION"].lower()):
                l_paths_template = paths_template_list + " } ," + paths_template_read + "," + paths_template_parameters + " }"
            else:
                l_paths_template = paths_template_list + " ," + paths_template_create + " } ," + paths_template_read + "," + paths_template_update + "," + paths_template_parameters + " }"

            path   = entities[entity]["PATH"]
            prefix = entities[entity]["PATH_PREFIX"]
            f_paths_template = f_paths_template + sep + paths_table(path, path_prefix=prefix, paths_template=l_paths_template)
            sep = ", "
    return f_paths_template


###
### Print
###


def print_green(text):
    print(colored(text, "green"))
    logging.debug(text)


def print_red(text):
    print(colored(text, "red"))
    logging.debug(text)


def print_verbose(text):
    global VERBOSE
    if (VERBOSE):
        print(colored(text, "magenta"))
    logging.debug(text)


def print_error(text):
    print(colored(text, "cyan"))
    logging.error(text)


def print_yellow(text):
    print(colored(text, "yellow"))
    logging.debug(text)


def print_grey(text):
    print(colored(text, "grey"))
    logging.debug(text)


def print_blue(text):
    print(colored(text, "blue"))
    logging.debug(text)

###
### Util
###

def find_between(content, start, end):
    found = re.search(start + '([\s\S]*?)' + end, content)
    if (found is None): return None
    found = found.group(1)
    found = re.sub(start, "", found)
    found = re.sub(end, "", found)
    return found


def remove_between(content, start, end):
    found = re.sub(start + '([\s\S]*?)' + end, "", content)
    return found


def decode_prop_schema(prop: str, schema: str, description: str = None) -> dict:
    schema = schema.strip()
    if schema.startswith("{"):  # JSON
        desc_schema = json.loads(schema)
    elif schema.startswith("\""):  # JSON
        desc_schema = json.loads("{" + schema + "}")
    else:  # YAML
        desc_schema = yaml.loads(schema)
    if ("validationScript" not in desc_schema):
        desc_schema["validationScript"] = ""
        print_error("Warning : property [" + str(prop) + "] validationScript defaulted to : [" + str(
            desc_schema["validationScript"]) + "]")
    if ("possibleValues" not in desc_schema):
        desc_schema["possibleValues"] = ["default_value", "value1", "value2"]
        print_error("Warning : property [" + str(prop) + "] possibleValues defaulted to : [" + str(
            desc_schema["possibleValues"]) + "]")
    if ("defaultValue" not in desc_schema):
        desc_schema["defaultValue"] = "default_value"
        print_error("Warning : property [" + str(prop) + "] defaultValue defaulted to : [" + str(
            desc_schema["defaultValue"]) + "]")
    if ("applicableTo" not in desc_schema):
        desc_schema["applicableTo"] = ""
        print_error("Warning : property [" + str(prop) + "] pplicableTo defaulted to : [" + str(
            desc_schema["applicableTo"]) + "]")
    if ("minCardinality" not in desc_schema):
        desc_schema["minCardinality"] = 1
        print_error("Warning : property [" + str(prop) + "] minCardinality defaulted to : [" + str(
            desc_schema["minCardinality"]) + "]")
    if ("maxCardinality" not in desc_schema):
        desc_schema["maxCardinality"] = 1
        print_error("Warning : property [" + str(prop) + "] maxCardinality defaulted to : [" + str(
            desc_schema["maxCardinality"]) + "]")
    if ("validFor" not in desc_schema):
        desc_schema["validFor"] = ""
        print_error(
            "Warning : property [" + str(prop) + "] validFor defaulted to : [" + str(desc_schema["validFor"]) + "]")
    if ("format" not in desc_schema):
        desc_schema["format"] = ""
        print_error("Warning : property [" + str(prop) + "] format defaulted to : [" + str(desc_schema["format"]) + "]")
    if ("example" not in desc_schema):
        desc_schema["example"] = ""
        print_error(
            "Warning : property [" + str(prop) + "] example defaulted to : [" + str(desc_schema["example"]) + "]")
    if ("description" not in desc_schema):
        if (description):
            desc_schema["description"] = description
        else:
            desc_schema["description"] = "No Description"
            print_error("Warning : property [" + str(prop) + "] description defaulted to : [" + str(
                desc_schema["description"]) + "]")
    if ("markdownDescription" not in desc_schema):
        desc_schema["markdownDescription"] = desc_schema["description"]
        print_error("Warning : property [" + str(prop) + "] markdownDescription defaulted to : [" + str(
            desc_schema["markdownDescription"]) + "]")
    if ("valueSpecification" not in desc_schema):
        desc_schema["valueSpecification"] = ""
        print_error("Warning : property [" + str(prop) + "] valueSpecification defaulted to : [" + str(
            desc_schema["valueSpecification"]) + "]")
    return desc_schema

###
### Schema Methods
###

def clean_name(name: str) -> str:
    return unidecode.unidecode(name.strip()).replace(" ", "_").replace("\\", "_").replace("'", "_").replace("/","-").replace("_fk", "")


def find_entity(entities, entity_name):
    for entity in entities.keys():
        if (("NAME" in entities[entity]) and (entities[entity]["NAME"] == entity_name)):
            return entities[entity]
        if (("name" in entities[entity]) and (entities[entity]["name"] == entity_name)):
            return entities[entity]
    return None


def find_table_contenues(links, table_contenante) -> list:
    lks = []
    for link in links:
        if (links[link]["TableContenante"] == table_contenante):
            lks.append(links[link])
    return lks

###
### Directories and Files
###

def saveFileContent(content, file_name: str):
    with open(file_name, "w") as file:
        content = file.write(content)
        file.close()
    return content

def get_basename(filename):
    return os.path.basename(filename)
    """ Without Parent Directory  """

def get_nakedname(filename):
    """ Without Parent Directory & Extension """
    return os.path.basename(filename).replace(get_extension(filename), "")

def get_strippedname(filename):
    """ Without Extension """
    return filename.replace(get_extension(filename), "")

def get_completename(directory: str, filename: str):
    """ Without Full Directory """
    if (os.path.dirname(filename) == ""):
        if (directory.endswith(os.path.sep)): return directory + filename
        else: return directory + os.path.sep + filename
    else:
        return filename

def get_extension(filename):
    """ Get Extension """
    return os.path.splitext(os.path.basename(filename))[1]

def is_ext(filename, ext):
    """ Check Extension """
    return get_extension(filename) == ext

def is_FileExist(filename):
    try:
        return os.path.exists(filename)
    except:
        return False

def is_DirExist(filename):
    try:
        return os.path.isdir(filename)
    except:
        return False








