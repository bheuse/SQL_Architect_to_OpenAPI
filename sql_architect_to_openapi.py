import xmltodict
import dicttoxml
import json
import copy
import yaml
import unittest
import sys
import os
import re
from jsonschema import validate
import logging
import datetime
from termcolor import colored
import unidecode
import markdown
import re, platform, socket, sys, shutil, errno, getopt, glob
import ftplib
from collections import OrderedDict

timestamp = datetime.datetime.now().strftime("%y%m%d-%H%M%S")
logFile   = "."+os.sep+"db_schema_to_openapi.log"
logging.basicConfig(filename=logFile, filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)


###
### FTP
###
def ftp_push_file(filename):
    if (isinstance(filename, str)):
        filename = [filename]
    if (isinstance(filename, list)):
        ftp = ftplib.FTP("ftpupload.net")
        try:
            ftp.login("epiz_30239961", "oqEwtTaACCaANF")
            ftp.cwd("htdocs")
            # remote_files = ftp.nlst()
            # print(remote_files)
            for file in filename:
                Term.print_blue("FTP Push : " + file)
                ftp.storbinary('STOR ' + file.replace("\\" , "/"), open(file, 'rb'))
                Term.print_green("FTP Push : " + file)
            ftp.close()
        except Exception as e:
            Term.print_error("FTP Upload Failed for : "+str(filename),str(e))
            ftp.close()

###
### Print
###

VERBOSE = False


class Term:

    @staticmethod
    def setVerbose():
        global VERBOSE
        VERBOSE = True

    @staticmethod
    def print_green(text):
        print(colored(text, "green"))
        logging.debug(text)

    @staticmethod
    def print_red(text):
        print(colored(text, "red"))
        logging.debug(text)

    @staticmethod
    def print_verbose(text):
        global VERBOSE
        if (VERBOSE):
            print(colored(text, "magenta"))
        logging.debug(text)

    @staticmethod
    def print_error(text, exception : str = None):
        print(colored(text, "cyan"))
        logging.error(text)
        if (exception):
            print(colored(exception, "red"))
            logging.error(exception)

    @staticmethod
    def print_yellow(text):
        print(colored(text, "yellow"))
        logging.debug(text)

    @staticmethod
    def print_grey(text):
        print(colored(text, "grey"))
        logging.debug(text)

    @staticmethod
    def print_blue(text):
        print(colored(text, "blue"))
        logging.debug(text)


###
### Directories and Files
###

class FileSystem:

    @staticmethod
    def saveFileContent(content, file_name: str):
        with open(file_name, "w") as file:
            content = file.write(content)
            file.close()
        return content

    @staticmethod
    def get_basename(filename):
        """ Without Parent Directory  """
        return os.path.basename(filename)

    @staticmethod
    def get_nakedname(filename):
        """ Without Parent Directory & Extension """
        return os.path.basename(filename).replace(FileSystem.get_extension(filename), "")

    @staticmethod
    def get_strippedname(filename):
        """ Without Extension """
        return filename.replace(FileSystem.get_extension(filename), "")

    @staticmethod
    def get_completename(directory: str, filename: str):
        """ Without Full Directory """
        if (os.path.dirname(filename) == ""):
            if (directory.endswith(os.path.sep)):
                return directory + filename
            else:
                return directory + os.path.sep + filename
        else:
            return filename

    @staticmethod
    def get_extension(filename):
        """ Get Extension """
        return os.path.splitext(os.path.basename(filename))[1]

    @staticmethod
    def is_ext(filename, ext):
        """ Check Extension """
        return FileSystem.get_extension(filename) == ext

    @staticmethod
    def is_FileExist(filename):
        try:
            return os.path.exists(filename)
        except:
            return False

    @staticmethod
    def is_DirExist(filename):
        try:
            return os.path.isdir(filename)
        except:
            return False

    @staticmethod
    def remove_extension(filename):
        return filename.replace(get_extension(filename), "")

    @staticmethod
    def safeListFiles(dir: str = ".", file_ext: str = "", keepExt = False) -> list:
        myList = list()
        for f in glob.glob(dir+os.sep+"*"+file_ext):
            f = f.replace(dir+os.sep, "")
            if (keepExt is False):
                f = remove_extension(f)
            myList.append(f)
        return myList

###
### Path
###

paths_template_list_create_prefix  = """
        "${PATH_PREFIX}/${PATH}s": {
            "summary": "Path used to manage the list of ${table}s.",
            "description": "The REST endpoint/path used to list and create zero or more `${TABLE}`.  This path contains a `GET` and `POST` operation to perform the list and create tasks, respectively."
"""
paths_template_list = """
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
paths_template_read_write_prefix = """

        "${PATH_PREFIX}/${PATH}s/{${PATH}Id}": {
            "summary": "Path used to manage a single ${TABLE}.",
            "description": "The REST endpoint/path used to get, update, and delete single instances of an `${TABLE}`.  This path contains `GET`, `PUT`, and `DELETE` operations used to perform the get, update, and delete tasks, respectively."
"""

paths_template_get = """
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
                "description": "Gets the details of a single instance of a `${TABLE}`.",
                "parameters" : [
                     { "in"        : "path" ,
                       "name"     : "${PATH}Id" , 
                       "required" : true,
                        "description": "A unique identifier for a `${TABLE}`.",
                        "schema": {
                            "type": "string"
                        }
                    }
                  ]
            }

"""
paths_template_put = """
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
            }
"""
paths_template_patch = """
            "patch": {
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
            }
"""
paths_template_delete = """
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
                {
                    "name": "${PATH}Id",
                    "description": "A unique identifier for a `${TABLE}`.",
                    "schema": {
                        "type": "string"
                    },
                    "in": "path",
                    "required": true
                }
"""


def paths_table(path : str, table: str, path_prefix: str = "", paths_template=""):
    l_paths_template = paths_template.replace("${PATH_PREFIX}", path_prefix)
    l_paths_template = l_paths_template.replace("${TABLE}", table)
    l_paths_template = l_paths_template.replace("${PATH}", path)
    l_paths_template = l_paths_template.replace("${table}", table.lower())
    return l_paths_template


def create_path(entities):
    f_paths_template = ""
    sep = ""
    for entity in entities:
        if ("PATH" in entities[entity]):
            if ("PATH_PARAMETERS" in entities[entity]) :
                path_parameters = "\"parameters\": [" + paths_template_parameters + "," + entities[entity]["PATH_PARAMETERS"] + "]"
                small_params    = " , \"parameters\": [" + entities[entity]["PATH_PARAMETERS"] + "]"
            else:
                path_parameters = "\"parameters\": ["  + paths_template_parameters + "]"
                small_params = ""
            if ("list-read-only" in entities[entity]["PATH_OPERATION"].lower()):
                l_paths_template = paths_template_list_create_prefix + "," + paths_template_list + small_params + " } ,"
                l_paths_template = l_paths_template + paths_template_read_write_prefix + "," + paths_template_get + "," + path_parameters + " }"
            elif ("list-create-patch" in entities[entity]["PATH_OPERATION"].lower()):
                l_paths_template = paths_template_list_create_prefix + "," + paths_template_list + "," + paths_template_create  + small_params + " } ,"
                l_paths_template = l_paths_template + paths_template_read_write_prefix + "," + paths_template_get + "," + paths_template_patch + "," + path_parameters + " }"
            elif ("list-create" in entities[entity]["PATH_OPERATION"].lower()):
                l_paths_template = paths_template_list_create_prefix + "," + paths_template_list + "," + paths_template_create + small_params + " } ,"
                l_paths_template = l_paths_template + paths_template_read_write_prefix + "," + paths_template_get + "," + path_parameters + " }"
            elif ("read-only" in entities[entity]["PATH_OPERATION"].lower()):
                l_paths_template = paths_template_list_create_prefix + "," + paths_template_list +  small_params + " } ,"
                l_paths_template = l_paths_template + paths_template_read_write_prefix + "," + paths_template_get + "," + path_parameters + " }"
            elif ("read-create" in entities[entity]["PATH_OPERATION"].lower()):
                l_paths_template = paths_template_list_create_prefix + "," + paths_template_list + "," + paths_template_create + small_params + " } ,"
                l_paths_template = l_paths_template + paths_template_read_write_prefix + "," + paths_template_get + "," + paths_template_patch + "," + path_parameters + " }"
            else:  # "read-create"
                l_paths_template = paths_template_list_create_prefix + "," + paths_template_list + "," + paths_template_create + small_params + " } ,"
                l_paths_template = l_paths_template + paths_template_read_write_prefix + "," + paths_template_get + "," + paths_template_put + "," + paths_template_delete + "," + path_parameters + " }"

            path   = entities[entity]["PATH"]
            prefix = entities[entity]["PATH_PREFIX"]
            f_paths_template = f_paths_template + sep + paths_table(path, entity, path_prefix=prefix, paths_template=l_paths_template)
            sep = ", "
    Term.print_verbose(f_paths_template)
    return f_paths_template


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


###
### Schema Methods
###

def decode_prop_schema(prop: str, schema: str, description: str = None) -> dict:
    schema = schema.strip()
    print(schema)
    if schema.startswith("{"):  # JSON
        desc_schema = json.loads(schema)
    elif schema.startswith("\""):  # JSON
        desc_schema = json.loads("{" + schema + "}")
    else:  # YAML
        desc_schema = yaml.loads(schema)
    if ("validationScript" not in desc_schema):
        desc_schema["validationScript"] = ""
        Term.print_error("Warning : property [" + str(prop) + "] validationScript defaulted to : [" + str(
            desc_schema["validationScript"]) + "]")
    if ("possibleValues" not in desc_schema):
        desc_schema["possibleValues"] = ["default_value", "value1", "value2"]
        Term.print_error("Warning : property [" + str(prop) + "] possibleValues defaulted to : [" + str(
            desc_schema["possibleValues"]) + "]")
    if ("defaultValue" not in desc_schema):
        desc_schema["defaultValue"] = "default_value"
        Term.print_error("Warning : property [" + str(prop) + "] defaultValue defaulted to : [" + str(
            desc_schema["defaultValue"]) + "]")
    if ("applicableTo" not in desc_schema):
        desc_schema["applicableTo"] = ""
        Term.print_error("Warning : property [" + str(prop) + "] pplicableTo defaulted to : [" + str(
            desc_schema["applicableTo"]) + "]")
    if ("minCardinality" not in desc_schema):
        desc_schema["minCardinality"] = 1
        Term.print_error("Warning : property [" + str(prop) + "] minCardinality defaulted to : [" + str(
            desc_schema["minCardinality"]) + "]")
    if ("maxCardinality" not in desc_schema):
        desc_schema["maxCardinality"] = 1
        Term.print_error("Warning : property [" + str(prop) + "] maxCardinality defaulted to : [" + str(
            desc_schema["maxCardinality"]) + "]")
    if ("validFor" not in desc_schema):
        desc_schema["validFor"] = ""
        Term.print_error(
            "Warning : property [" + str(prop) + "] validFor defaulted to : [" + str(desc_schema["validFor"]) + "]")
    if ("format" not in desc_schema):
        desc_schema["format"] = ""
        Term.print_error("Warning : property [" + str(prop) + "] format defaulted to : [" + str(desc_schema["format"]) + "]")
    if ("example" not in desc_schema):
        desc_schema["example"] = ""
        Term.print_error(
            "Warning : property [" + str(prop) + "] example defaulted to : [" + str(desc_schema["example"]) + "]")
    if ("description" not in desc_schema):
        if (description):
            desc_schema["description"] = description
        else:
            desc_schema["description"] = "No Description"
            Term.print_error("Warning : property [" + str(prop) + "] description defaulted to : [" + str(
                desc_schema["description"]) + "]")
    if ("markdownDescription" not in desc_schema):
        desc_schema["markdownDescription"] = desc_schema["description"]
        Term.print_error("Warning : property [" + str(prop) + "] markdownDescription defaulted to : [" + str(
            desc_schema["markdownDescription"]) + "]")
    if ("valueSpecification" not in desc_schema):
        desc_schema["valueSpecification"] = ""
        Term.print_error("Warning : property [" + str(prop) + "] valueSpecification defaulted to : [" + str(
            desc_schema["valueSpecification"]) + "]")
    return desc_schema


def clean_name(name: str) -> str:
    return unidecode.unidecode(name.strip()).replace(" ", "_").replace("\\", "_").replace("'", "_").replace("/", "-").replace("_fk", "")


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

"""
The content of the Data Model in SQL Architect will be used as ReadMe File

The content of the Data Model in DB Schema will be used as in ReadMe File

See ReadMe File

"""

default_data_model = "API_Data_Model_Sample"

# Objects of Interest
entities = {}   # To OpenAPI Objects
links    = {}   # To OpenAPI Objects

"""
                                Architect                              DbSchema
Entity:
    entity["name"]              = Logical Name
    entity["type"]              = "object"
    entity["description"]       = table["remarks"]
    entity["example"]           = table["@physicalName"]
    entity["NAME"]              = Logical Name
    entity["TABLE"]             = table["@id"]                         N/A
    entity["RELATIONS"]         = {}
    entity["properties"]        = {}
    entity["PATH_PREFIX"]       = 
    entity["PATH"]              =
    entity["PATH_OPERATION"]    =  "read-only"
    Not Generated               = if ("ignore" in data_type["example"]) => Not Generated

Property:

    this_property["name"]        = name
    this_property["type"]        = "INVALID"
    this_property["description"] = att["@name"]
    this_property["example"]     = att["@name"]
    this_property["mandatory"]   = "n"
    this_property["pattern"]     = att["@defaultValue"]
    this_property["type"]        = "string"
    this_property["format"]      = ""

Link:

     cardinality     = links[link]["Cardinalite"]       OneToOne (3), ZeroToOne (2) , OneToMany (1), ZeroToMany (0) 
     TableContenue   = links[link]["TableContenue"]
     TableContenante = links[link]["TableContenante"]
     Name            = links[link]["Name"]
     Descr           = links[link]["Description"]

"""


class DbSchema:

    def __init__(self):
        self.tables   = dict()

    def log(self):
        global entities, links
        Term.print_verbose("tables    : " + str(self.tables))
        Term.print_verbose("entities  : " + str(entities))
        Term.print_verbose("links     : " + str(links))
        return

    def handle_table(self, table):
        # @name, @spec, comment,
        # Not used : options, pre_script, post_script
        # Not usable : @prior,
        data_type = {}
        name = clean_name(table["@name"])
        data_type["name"] = "name"
        data_type["type"] = "object"
        data_type["description"] = table["comment"] if ("comment"     in table) else "No Description for " + table["@name"]
        data_type["options"] = table["options"]     if ("options"     in table) else ""
        data_type["append"]  = table["post_script"] if ("post_script" in table) else ""
        data_type["prepend"] = table["pre_script"]  if ("pre_script"  in table) else ""
        data_type["example"] = table["@spec"]       if ("@spec"       in table) else ""
        data_type["properties"] = {}
        data_type["NAME"]       = name
        data_type["TABLE"]      = table["@name"]
        data_type["RELATIONS"]  = {}
        return data_type, name

    def handle_attribute(self, data_type, att, entity_name):
        # "@name"   : "Name"    => Property Name
        # "@type"   : "varchar" => Type
        # "@length" : "255"     => Not Used
        # "@jt"     : "12",     => Type Related Information ?
        # "@mandatory" : "y"    => Required
        # "@to do"     : "1"    => Not Used
        # "comment"    :        => Description
        # "@defo"      : [default] => Example

        name = clean_name(att["@name"])

        if (name == "_PATH"):
            data_type["PATH"]            = clean_name(entity_name)
            data_type["PATH_PREFIX"]     = att["defo"]     if ("defo" in att)    else "/"+clean_name(entity_name).lower()
            if ("comment" in att) :
                desc  = att["comment"]
                found = find_between(desc, "<parameters>", "</parameters>")
                if (found):
                    desc = remove_between(desc, "<parameters>", "</parameters>")
                    data_type["PATH_PARAMETERS"] = found
                data_type["PATH_OPERATION"]  = desc
            else:
                data_type["PATH_OPERATION"] = "READ-WRITE"

            return data_type, name

        property = dict()
        property["name"]        = name
        property["pattern"]     = None
        property["description"] = None
        property["example"]     = None
        property["mandatory"]   = False
        property["type"]        = "INVALID"
        property["format"]      = ""

        property["description"]    = att["comment"]  if ("comment" in att) else "No Description for " + att["@name"]
        if ("@defo" in att): property["pattern"] = att["@defo"]

        property["example"] = re.sub(".*xample:" , "" , property["description"])

        if (("@mandatory" in att) and (att["@mandatory"] == "y")):
            # Required property
            if "required" not in data_type : data_type["required"] = list()
            data_type["required"].append(name)
            property["mandatory"] = True

        if (att["@type"] == "text")     : property["type"]   = "string"
        if (att["@type"] == "varchar")  : property["type"]   = "string"
        if (att["@type"] == "boolean")  : property["type"]   = "boolean"
        if (att["@type"] == "integer")  : property["type"]   = "integer"
        if (att["@type"] == "numeric")  : property["type"]   = "number"
        if (att["@type"] == "decimal")  : property["type"]   = "number"
        if (att["@type"] == "int")      : property["type"]   = "integer"
        if (att["@type"] == "datetime") : property["type"]   = "string"
        if (att["@type"] == "datetime") : property["format"] = "date-time "
        if (att["@type"] == "date")     : property["type"]   = "string"
        if (att["@type"] == "date")     : property["format"] = "date"
        if (property["type"] == "INVALID"):
            property["type"]  = att["@type"]
            Term.print_error("Unsupported Attribute Type : " + att["@type"])
        data_type["properties"][name] = property
        return data_type, name

    def handle_link(self, data_type, relation, entity_name):
        # "@name"       : "fk_ue_restrictions_service",
        # "@to_schema"  : "NEF_MarketPlace_DataModel",
        # "@to_table"   : "Service",
        # "@type"       : "Identifying",
        # "comment"     : "Service Owner"
        global entities, links
        link = dict()
        if ("ignore" in relation["@name"]) :
            # Ignore  Links with ignore
            return data_type, relation["@name"]
        else:
            name = relation["@name"]
            ignore = False
        link["TableContenante"] = relation["@to_table"]
        link["TableContenue"]   = entity_name
        link["Name"]            = clean_name(relation["@name"])
        if "comment" in relation :
            link["Description"] = relation["comment"]
        else:
            link["Description"] = "No Description"
        #  Identifying / NonIdentifyingMandatory / OneToOne  / ManyToMany
        link["Cardinality"] = relation["@type"]

        links[link["Name"]] = link
        data_type["RELATIONS"][link["Name"]] = link

        return data_type, name

    def collect_entities_links(self):
        global entities, links
        for table in self.tables:
            Term.print_verbose(table)
            data_type, entity_name = self.handle_table(table)
            if "column" in table:
                if isinstance(table["column"], list):
                    for col in table["column"]:
                        data_type, att_name = self.handle_attribute(data_type, col, entity_name)
                else:
                    data_type, att_name = self.handle_attribute(data_type, table["column"], entity_name)
            data_type["RELATIONS"] = {}
            if "fk" in table:
                if isinstance(table["fk"], list):
                    for rel in table["fk"]:
                        data_type, att_name = self.handle_link(data_type, rel, entity_name)
                else:
                    data_type, att_name = self.handle_link(data_type, table["fk"], entity_name)
            if ("ignore" in data_type["example"]) :
                continue
            entities[entity_name] = data_type

    def handle_links(self):
        for link in links:
            property = dict()
            property["description"] = links[link]["Description"]
            if (links[link]["Cardinality"] == "OneToOne") :
                property["$ref"] = "#/components/schemas/" + links[link]["TableContenue"]
            else:
                property["type"] = "array"
                property["items"] = {}
                property["items"]["$ref"] = "#/components/schemas/" + links[link]["TableContenue"]
            table = find_entity(entities, links[link]["TableContenante"])
            table["properties"][links[link]["TableContenue"]] = property

    def read_dbschema(self, data_model : str):
        Term.print_yellow("> read_dbschema")
        global entities, links

        # Reading dbschema file
        myFile = open(data_model + ".dbs", "r")
        dbschemaContent = myFile.read()
        myFile.close()
        dict_schema = xmltodict.parse(dbschemaContent)

        # Save to JSON Format
        FileSystem.saveFileContent(json.dumps(dict_schema, indent=3), data_model + ".json")

        # Collecting Table & Links
        self.tables = dict_schema["project"]["schema"]["table"]
        self.collect_entities_links()

        # Handle Relationships between entities
        self.handle_links()

        # What did we get ?
        self.log()

        Term.print_yellow("< read_dbschema")
        return entities, links


class Architect:

    def __init__(self):
        self.architect = None
        self.tables    = dict()  # From SQL Architect
        self.relations = dict()  # From SQL Architect

    def log(self):
        global entities, links
        Term.print_verbose("tables    : " + str(self.tables))
        Term.print_verbose("relations : " + str(self.relations))
        Term.print_verbose("entities  : " + str(entities))
        Term.print_verbose("links     : " + str(links))
        return

    def find_table_name(self, table_id):
        global entities, links
        for table in entities.keys():
            if (entities[table]["TABLE"] == table_id):
                return entities[table]["NAME"]
        return None

    def collect_links(self):
        global entities, links
        if isinstance(self.relations, dict) :
            self.relations = [ self.relations ]
        for relation in self.relations:
            link = dict()
            if ("ignore" in relation["@name"]) :
                continue  # Ignore Grey Links or starting with ignore
            link["TableContenante"] = relation["@pk-table-ref"]   # find_table_name(relation["@pk-table-ref"])
            link["TableContenue"]   = relation["@fk-table-ref"]   # find_table_name(relation["@fk-table-ref"])
            if   (relation["@fkCardinality"] == "3") :  link["Cardinalite"]     = "ZeroToOne"
            elif (relation["@fkCardinality"] == "7") :  link["Cardinalite"]     = "OneToMore"
            elif (relation["@fkCardinality"] == "6") :  link["Cardinalite"]     = "ZeroToMore"
            if   (relation["@pkCardinality"] == "3") :  link["Cardinalite"]     = "ZeroToOne"
            elif (relation["@pkCardinality"] == "7") :  link["Cardinalite"]     = "OneToMore"
            elif (relation["@pkCardinality"] == "6") :  link["Cardinalite"]     = "ZeroToMore"
            elif (relation["@pkCardinality"] == "2") :  link["Cardinalite"]     = "OneToOne"
            link["Name"]            = clean_name(relation["@name"])
            link["Description"]     = "No Description"
            ignore = False
            for tlink in self.architect["architect-project"]["play-pen"]["table-link"]:
                if (tlink["@rLineColor"] == "0x999999"):
                    ignore = True  # Ignore Grey Links
                    continue
                if (tlink["@relationship-ref"] == relation["@id"]):
                    link["Description"] = clean_name(tlink["@pkLabelText"]) + " " + clean_name(tlink["@fkLabelText"])
                    if (link["Description"] == " "): link["Description"] = link["Name"]
                if (ignore is False) :
                    links[relation["@id"]] = link

    def handle_object(self, table):
        data_type = {}
        name = clean_name(table["@name"])
        data_type["name"] = "name"
        data_type["type"] = "object"
        if (table["remarks"]):
            data_type["description"] = table["remarks"]
        else:
            data_type["description"] = "No Description for " + table["@name"]
        data_type["example"]    = table["@physicalName"]
        data_type["properties"] = {}
        data_type["NAME"]       = name
        data_type["TABLE"]      = table["@id"]
        data_type["RELATIONS"]  = {}
        return data_type, name

    def handle_attribute(self, data_type, att):
        this_property = {}
        name = clean_name(att["@name"])
        this_property["name"] = name
        if (name == "_PATH"):
            data_type["PATH"]        = att["@physicalName"]
            data_type["PATH_PREFIX"] = att["@defaultValue"]
            data_type["PATH_OPERATION"] = "READ-WRITE"
            if (att["remarks"] is not None):
                desc  = att["remarks"]
                found = find_between(desc, "<parameters>", "</parameters>")
                if (found):
                    desc = remove_between(desc, "<parameters>", "</parameters>")
                    data_type["PATH_PARAMETERS"] = found
                data_type["PATH_OPERATION"]  = desc

        this_property["type"] = "INVALID"
        if (att["remarks"] is None):
            this_property["description"] = "No Description for " + att["@name"]
        else:
            this_property["description"] = att["remarks"]
        if (att["@physicalName"] is None):
            this_property["example"] = "No example for " + att["@name"]
        else:
            this_property["example"] = att["@physicalName"]
        if (att["@nullable"] == "1"):
            this_property["mandatory"] = "n"
        else:
            if (name != "_PATH"):
                if "required" not in data_type : data_type["required"] = list()
                data_type["required"].append(name)
                this_property["mandatory"] = "y"
        this_property["pattern"] = att["@defaultValue"]
        this_property["type"]   = "string"
        this_property["format"] = ""
        if (att["@type"] == "12"): this_property["type"]   = "string"
        if (att["@type"] == "4"):  this_property["type"]   = "integer"
        if (att["@type"] == "92"): this_property["type"]   = "string"
        if (att["@type"] == "92"): this_property["format"] = "date-time"
        if (att["@type"] == "16"): this_property["type"]   = "boolean"
        if (this_property["type"] == "INVALID"):
            Term.print_error("Unsupported Attribute Type : " + att["@type"])
        if (name != "_PATH"):
            data_type["properties"][name] = this_property
        return data_type, name

    def collect_tables(self):
        global entities, links
        for table in self.tables:
            data_type, entity_name = self.handle_object(table)
            for folder in table["folder"]:
                if "column" not in folder: continue
                column = folder["column"]
                if isinstance(column, list):
                    for col in column:
                        data_type, att_name = self.handle_attribute(data_type, col)
                else:
                    data_type, att_name = self.handle_attribute(data_type, column)
            if ("ignore" in data_type["example"]) :
                continue
            entities[entity_name] = data_type

    def read_architect(self, data_model : str):
        Term.print_yellow("> read_architect")
        global entities, links

        # Reading architect file
        myFile = open(data_model + ".architect", "r")
        architectSchema = myFile.read()
        myFile.close()
        self.architect = xmltodict.parse(architectSchema)

        # Save to JSON Format
        FileSystem.saveFileContent(json.dumps(self.architect, indent=3), data_model + ".json")

        # Collecting architect entities
        self.tables    = self.architect["architect-project"]["target-database"]["table"]
        self.relations = self.architect["architect-project"]["target-database"]["relationships"]["relationship"]
        self.collect_links()
        self.collect_tables()

        # Replacing Table IDs by Names
        for entity in entities:
            LINK_TABLE_CONT = find_table_contenues(links, entities[entity]["TABLE"])
            for rel in LINK_TABLE_CONT:
                if (not self.find_table_name(rel["TableContenue"])):
                    continue
                rel["TableContenanteID"] = rel["TableContenante"]
                rel["TableContenueID"]   = rel["TableContenue"]
                rel["TableContenante"]   = self.find_table_name(rel["TableContenante"])
                rel["TableContenue"]     = self.find_table_name(rel["TableContenue"])
                entities[entity]["RELATIONS"][rel["Name"]] = rel
                this_property = dict()
                this_property["description"] = rel["Description"]
                this_property["$ref"] = "#/components/schemas/" + rel["TableContenue"]
                entities[entity]["properties"][rel["TableContenue"]] = this_property

        # What did we get ?
        self.log()

        Term.print_yellow("< read_architect")
        return entities, links


def lets_do_dbschema(data_model : str):
    Term.print_yellow("> lets_do_dbschema")
    data_model = re.sub(".*\\" + os.sep , "", data_model)
    xml =       "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>"
    xml = xml + "   <project name=\""+data_model+"\" id=\"Project-2cc\" database=\""+"LogicalDesign"+"\" >"
    xml = xml + "       <schema name=\""+data_model+"\" >"
    x, y = 0, 0
    for entity in entities:
        x, y = x + 25, y + 25
        # entity : type, description, example
        xml = xml + "<table name=\""+entity+"\" prior=\"Entity\" spec=\"\" >"
        xml = xml + "<comment><![CDATA["+entities[entity]["description"]+"]]></comment>\n"
        xml = xml + "<options><![CDATA[" + entities[entity]["example"] + "]]></options>\n"
        xml = xml + "<pre_script><![CDATA[" + entities[entity]["example"] + "]]></pre_script>\n"
        xml = xml + "<post_script><![CDATA[" + entities[entity]["example"] + "]]></post_script>\n"
        # property: type, description, example, pattern
        for property in entities[entity]["properties"]:
            prop = entities[entity]["properties"][property]
            add = ""
            if ("required" in entities[entity]) and (property in entities[entity]["required"]):
                add = " mandatory=\"y\" "
            type = "type=\"varchar\""
            if "type" in prop:
                if (prop["type"] == "integer"):
                    type = "type=\"integer\""
                elif (prop["type"] == "string"):
                    type = "type=\"varchar\""
                elif (prop["type"] == "boolean"):
                    type = "type=\"boolean\""
            xml = xml + "<column name=\"" + property + "\" "+type+" length=\"255\" "+add+"jt=\"12\" todo=\"1\">\n"
            if "pattern" in prop:
                xml = xml + "<defo> <![CDATA["+prop["pattern"]+"]]> </defo>\n"
            if "description" in prop:
                xml = xml + "<comment> <![CDATA["+prop["description"]+"]]> </comment>\n"
            if "example" in prop:
                xml = xml + "<options><![CDATA[" + prop["example"] + "]]></options>\n"
            xml = xml + "</column>\n"
        # Links
        for lk in links :
            link = links[lk]
            # link: TableContenante, TableContenue, Cardinalite, Name, Description
            if (link["TableContenue"] != entity): continue
            xml = xml + "<fk name=\""+link["Name"]+"\" to_schema=\""+data_model+"\" to_table=\""+link["TableContenante"]+"\" type=\"Identifying\" >\n"
            xml = xml + "<comment><![CDATA[" + link["Description"] + "]]></comment></fk>\n"
        xml = xml + "</table>\n"
    xml = xml + "       </schema>"
    xml = xml + "<layout name=\"Default Layout\" id=\"Layout-686\" show_relation=\"columns\" >\n"
    for entity in entities:
        xml = xml + "<entity schema=\"NEF_Business_Model\" name=\""+entity+"\"  color=\"3986C1\" x=\""+str(x)+"\" y=\""+str(y)+"\"/>\n"
    xml = xml + "   </layout>\n"
    xml = xml + "</project>\n"
    dbs_file = data_model + ".dbs"
    FileSystem.saveFileContent(xml, dbs_file)
    Term.print_yellow("< lets_do_dbschema")
    return xml


def lets_do_openapi_yaml(data_model : str):
    Term.print_yellow("> lets_do_openapi Yaml API")
    global entities, links

    # Create API Operations
    paths = create_path(entities)
    print(paths)
    paths_to_create = json.loads("{" + paths + "}")

    open_api_yaml = dict()
    open_api_yaml["openapi"] = "3.0.2"
    open_api_yaml["info"] = dict()
    open_api_yaml["info"]["title"]       = "Business Data Model"
    open_api_yaml["info"]["version"]     = "1.0.0"
    open_api_yaml["info"]["description"] = "Business Data Model. This is generated, modify source SQL Architect data model instead."
    open_api_yaml["info"]["contact"]     = {}
    open_api_yaml["info"]["contact"]["name"]  = "Bernard Heuse"
    open_api_yaml["info"]["contact"]["url"]   = "https://www.gadseca.org/"
    open_api_yaml["info"]["contact"]["email"] = "bheuse@gmail.com"

    if "OpenAPI" in entities :
        if ("title" in entities["OpenAPI"]["properties"]):
            open_api_yaml["info"]["title"]       = entities["OpenAPI"]["properties"]["title"]["example"]

        if ("version" in entities["OpenAPI"]["properties"]):
            open_api_yaml["info"]["version"]     = entities["OpenAPI"]["properties"]["version"]["example"]

        if ("description" in entities["OpenAPI"]["properties"]):
            open_api_yaml["info"]["description"] = entities["OpenAPI"]["properties"]["description"]["example"] + " " + entities["OpenAPI"]["properties"]["description"]["description"]

        if ("contact" in entities["OpenAPI"]["properties"]):
            contacts = json.loads(entities["OpenAPI"]["properties"]["contact"]["description"])
            open_api_yaml["info"]["contact"] = contacts

        if ("security" in entities["OpenAPI"]["properties"]):
            security = json.loads(entities["OpenAPI"]["properties"]["security"]["description"])
            open_api_yaml["security"] = security

        if ("license" in entities["OpenAPI"]["properties"]):
            license = json.loads(entities["OpenAPI"]["properties"]["license"]["description"])
            open_api_yaml["info"]["license"] = license

        if ("tags" in entities["OpenAPI"]["properties"]):
            tags = json.loads(entities["OpenAPI"]["properties"]["tags"]["description"])
            open_api_yaml["tags"] = tags

        if ("servers" in entities["OpenAPI"]["properties"]):
            servers = json.loads(entities["OpenAPI"]["properties"]["servers"]["description"])
            open_api_yaml["servers"] = servers

        if ("securitySchemes" in entities["OpenAPI"]["properties"]):
            securitySchemes = json.loads(entities["OpenAPI"]["properties"]["securitySchemes"]["description"])
            open_api_yaml["components"] = dict()
            open_api_yaml["components"]["securitySchemes"] = securitySchemes

        del entities["OpenAPI"]

    # Clean-up before generation
    entities_yaml = copy.deepcopy(entities)
    for entity in entities_yaml:
        if ("TABLE" in entities_yaml[entity])     : del entities_yaml[entity]["TABLE"]
        if ("RELATIONS" in entities_yaml[entity]) : del entities_yaml[entity]["RELATIONS"]
        if ("NAME" in entities_yaml[entity])      : del entities_yaml[entity]["NAME"]
        if ("prepend" in entities_yaml[entity])   : del entities_yaml[entity]["prepend"]
        if ("append" in entities_yaml[entity])    : del entities_yaml[entity]["append"]
        if ("options" in entities_yaml[entity])   : del entities_yaml[entity]["options"]
        if ("PATH_OPERATION" in entities_yaml[entity]):  del entities_yaml[entity]["PATH_OPERATION"]
        if ("PATH_PARAMETERS" in entities_yaml[entity]): del entities_yaml[entity]["PATH_PARAMETERS"]
        if ("PATH_PREFIX" in entities_yaml[entity]):     del entities_yaml[entity]["PATH_PREFIX"]
        if ("PATH"  in entities_yaml[entity]):           del entities_yaml[entity]["PATH"]
        if ("_ROOT" in entities_yaml[entity]):           del entities_yaml[entity]["_ROOT"]
        if ("name" in entities_yaml[entity]) :           del entities_yaml[entity]["name"]
        if ("mandatory" in entities_yaml[entity]) :      del entities_yaml[entity]["mandatory"]
        if ("properties" in entities_yaml[entity]) :
            if ("name" in entities_yaml[entity]["properties"]):           del entities_yaml[entity]["properties"]["name"]
            if ("mandatory" in entities_yaml[entity]["properties"]):      del entities_yaml[entity]["properties"]["mandatory"]
            if ("_ROOT" in entities_yaml[entity]["properties"]):          del entities_yaml[entity]["properties"]["_ROOT"]
            for prop in entities_yaml[entity]["properties"] :
                if ("name" in entities_yaml[entity]["properties"][prop]):           del entities_yaml[entity]["properties"][prop]["name"]
                if ("mandatory" in entities_yaml[entity]["properties"][prop]):      del entities_yaml[entity]["properties"][prop]["mandatory"]
                desc = entities_yaml[entity]["properties"][prop]["description"]
                found = find_between(desc, "<schema>", "</schema>")
                if (found):
                    desc = remove_between(desc, "<schema>", "</schema>")
                    try:
                        desc_schema = decode_prop_schema(property, found, desc)
                    except Exception as e:
                        Term.print_error(found,str(e))
                entities_yaml[entity]["properties"][prop]["description"]  = desc.strip()


    # Add Paths
    open_api_yaml["paths"] = paths_to_create
    if "components" in open_api_yaml:
        open_api_yaml["components"]["schemas"] = entities_yaml
    else:
        open_api_yaml["components"] = {"schemas": entities_yaml}

    # Re-Order
    open_api = dict()
    if "openapi"      in open_api_yaml : open_api["openapi"]      = open_api_yaml["openapi"]
    if "info"         in open_api_yaml : open_api["info"]         = open_api_yaml["info"]
    if "externalDocs" in open_api_yaml : open_api["externalDocs"] = open_api_yaml["externalDocs"]
    if "servers"      in open_api_yaml : open_api["servers"]      = open_api_yaml["servers"]
    if "security"     in open_api_yaml : open_api["security"]     = open_api_yaml["security"]
    if "paths"        in open_api_yaml : open_api["paths"]        = open_api_yaml["paths"]
    if "components"   in open_api_yaml : open_api["components"]   = open_api_yaml["components"]

    print()
    # Done - Save
    yaml_text = yaml.safe_dump(open_api, indent=2, default_flow_style=False, sort_keys=False)
    Term.print_verbose(yaml_text)
    yaml_file = data_model+".yaml"
    FileSystem.saveFileContent(yaml_text, yaml_file)
    yaml_file = data_model.replace("_DataModel", "")+".yaml"
    FileSystem.saveFileContent(yaml_text, yaml_file)

    xml_text = dicttoxml.dicttoxml(open_api_yaml, attr_type=False).decode("utf-8")
    Term.print_verbose(xml_text)
    xml_file = data_model + ".xml"
    FileSystem.saveFileContent(xml_text, xml_file)

    Term.print_yellow("< lets_do_openapi")


baseURI  = "https://amdocs.com/schemas/nef/"
schemas  = {}


def lets_do_json_schema(data_model : str):
    Term.print_yellow("> lets_do_json Schema")

    entities_json = copy.deepcopy(entities)
    # Clean-up before generation
    for entity in entities_json:
        if ("TABLE" in entities_json[entity])     : del entities_json[entity]["TABLE"]
        if ("RELATIONS" in entities_json[entity]) : del entities_json[entity]["RELATIONS"]
        if ("NAME" in entities_json[entity])    : del entities_json[entity]["NAME"]
        if ("prepend" in entities_json[entity]) : del entities_json[entity]["prepend"]
        if ("append" in entities_json[entity])  : del entities_json[entity]["append"]
        if ("options" in entities_json[entity]) : del entities_json[entity]["options"]
        if ("PATH_OPERATION" in entities_json[entity]):  del entities_json[entity]["PATH_OPERATION"]
        if ("PATH_PARAMETERS" in entities_json[entity]): del entities_json[entity]["PATH_PARAMETERS"]
        if ("PATH_PREFIX" in entities_json[entity]):     del entities_json[entity]["PATH_PREFIX"]
        if ("PATH"  in entities_json[entity]):           del entities_json[entity]["PATH"]
        # if ("name" in entities_json[entity]) :           del entities_json[entity]["name"]
        # if ("mandatory" in entities_json[entity]) :      del entities_json[entity]["mandatory"]
        for prop in entities_json[entity]["properties"] :
            # if ("name" in entities_json[entity]["properties"][prop]):           del entities_json[entity]["properties"][prop]["name"]
            # if ("mandatory" in entities_json[entity]["properties"][prop]):      del entities_json[entity]["properties"][prop]["mandatory"]
            continue


    json_directory = data_model + "_json"
    if (not os.path.isdir(json_directory)):
        os.mkdir(json_directory)
    for entity in entities_json:
        is_root = False
        json_object = {}
        json_schema = {}
        object_desc = entities_json[entity]
        Term.print_yellow("["+entity+"]")
        Term.print_verbose(json.dumps(entities_json[entity], indent=3))
        Term.print_verbose(" - description : " + str(object_desc["description"]))
        Term.print_verbose(" - type        : " + str(object_desc["type"]))
        Term.print_verbose(" - example     : " + str(object_desc["example"]))
        Term.print_verbose(" - " + str(object_desc))

        json_schema["$schema"]     = "http://json-schema.org/draft-07/schema"
        json_schema["$id"]         = baseURI+entity+".json"
        json_schema["type"]        = "object"
        json_schema["title"]       = "Schema for " + entity
        json_schema["description"] = object_desc["description"]
        json_schema["default"]     = {}
        json_schema["examples"]    = []
        json_schema["required"]    = []
        json_schema["properties"]  = {}
        json_schema["additionalProperties"] = True

        for property in object_desc["properties"]:
            if (property == "_ROOT"):
                is_root = True
            Term.print_verbose(" #> [" + str(object_desc["properties"][property]) + "]")
            Term.print_verbose(json.dumps(object_desc["properties"][property], indent=3))
            property_desc = object_desc["properties"][property]
            Term.print_verbose(" #>> " + str(property_desc))
            prop_schema = {}
            if ("$ref" in property_desc):
                # Sub-object
                Term.print_verbose("   #>> object        : " + str(property_desc["$ref"]))
                item = re.sub("#/components/schemas/" , "" , str(property_desc["$ref"]))
                prop_schema["$ref"]  = "" + item + "_schema.json"
                prop_schema["$ref"]  = "#/$defs/" + item + ""
                json_schema["properties"][item] = prop_schema
            elif ("items" in property_desc):
                # Array of Sub-objects
                Term.print_verbose("   #>> Array objects : " + str(property_desc["items"]["$ref"]))
                item = re.sub("#/components/schemas/", "", str(property_desc["items"]["$ref"]))
                prop_schema["type"] = "array"
                prop_schema["items"] = {"$ref" : "" + item + "_schema.json"}
                prop_schema["items"] = {"$ref" : "#/$defs/" + item + ""}
                json_schema["properties"][item+"s"] = prop_schema
            else:
                desc = property_desc["description"]
                found = find_between(desc, "<schema>", "</schema>")
                desc_schema = {}
                if (found):
                    Term.print_verbose(found)
                    desc = remove_between(desc, "<schema>", "</schema>")
                    desc_schema = decode_prop_schema(property, found, desc)

                json_object[property_desc["name"]] = property_desc["example"] if ("example" in property_desc) else "No Example"
                prop_schema["$id"]          = "#/properties/" + property_desc["name"]
                prop_schema["type"]         = property_desc["type"]
                prop_schema["title"]        = property_desc["name"]
                prop_schema["description"]  = desc.strip()
                prop_schema["default"]      = ""
                # prop_schema["examples"]     = [property_desc["example"]]

                prop_schema["validationScript"] = desc_schema["validationScript"] if ("validationScript" in desc_schema) else ""
                prop_schema["possibleValues"]   = desc_schema["possibleValues"]   if ("possibleValues"   in desc_schema) else ["default_value", "value1" , "value2"]
                prop_schema["defaultValue"]     = desc_schema["defaultValue"]     if ("defaultValue"     in desc_schema) else "default_value"
                prop_schema["applicableTo"]     = desc_schema["applicableTo"]     if ("applicableTo"     in desc_schema) else ""
                prop_schema["minCardinality"]   = desc_schema["minCardinality"]   if ("minCardinality"   in desc_schema) else 1
                prop_schema["maxCardinality"]   = desc_schema["maxCardinality"]   if ("maxCardinality"   in desc_schema) else 1
                prop_schema["validFor"]         = desc_schema["validFor"]         if ("validFor"         in desc_schema) else ""
                prop_schema["format"]           = desc_schema["format"]           if ("format"           in desc_schema) else ""
                prop_schema["example"]          = desc_schema["example"]          if ("example"          in desc_schema) else ""
                prop_schema["description"]      = desc_schema["description"]      if ("description"      in desc_schema) else desc
                prop_schema["markdownDescription"] = desc_schema["markdownDescription"] if ("markdownDescription"  in desc_schema) else ""
                prop_schema["valueSpecification"]  = desc_schema["valueSpecification"]  if ("valueSpecification"   in desc_schema) else {}

                Term.print_verbose("   #>> name        : " + str(property_desc["name"]))
                Term.print_verbose("   #>> description : " + str(property_desc["description"]))
                Term.print_verbose("   #>> type        : " + str(property_desc["type"]))
                Term.print_verbose("   #>> format      : " + str(property_desc["format"]))
                Term.print_verbose("   #>> example     : " + str(property_desc["example"]))
                Term.print_verbose("   #>> pattern     : " + str(property_desc["pattern"]))
                Term.print_verbose("   #>> format      : " + str(property_desc["format"]))
                Term.print_verbose("   #>> mandatory   : " + str(property_desc["mandatory"]))
                if (property_desc["mandatory"]):
                    json_schema["required"].append(property_desc["name"])
                json_schema["properties"][property_desc["name"]] = prop_schema
        Term.print_verbose("Sample Object: "+str(json_object))
        json_schema["examples"]    = [json_object]
        schemas[entity] = json_schema

        # Add $defs Sub-Objects Schemas
        for link in links:
            cardinality     = links[link]["Cardinalite"]
            TableContenue   = links[link]["TableContenue"]
            TableContenante = links[link]["TableContenante"]
            Name            = links[link]["Name"]
            Descr           = links[link]["Description"]
            Term.print_verbose(TableContenante + " Contains [" + cardinality + "] " + TableContenue)
            if (entity == TableContenante) and ("Optional" not in str(cardinality)):
                json_schema["required"].append(TableContenue)
            if (entity == TableContenante) and (str(cardinality)  in ["1", "3"]):
                json_schema["required"].append(TableContenue)

        if (is_root) :
            FileSystem.saveFileContent(json.dumps(json_object, indent=3), json_directory + os.sep + entity + ".json")
            FileSystem.saveFileContent(json.dumps(json_schema, indent=3), json_directory + os.sep + entity + "_schema.json")

    # Add $defs Sub-Objects Schemas
    schema_file = None
    for schema in schemas:
        if "properties" not in schemas[schema]: continue
        if "_ROOT" in schemas[schema]["properties"] :
            # del schemas[schema]["properties"]["_ROOT"]
            schemas[schema]["$defs"] = {}
            for schema2 in schemas:
                if "properties" not in schemas[schema]: continue
                if "_ROOT" in schemas[schema2]["properties"] : continue
                del schemas[schema2]["$schema"]
                del schemas[schema2]["$id"]
                schemas[schema]["$defs"][schema2] = schemas[schema2]
            schema_file = json_directory + os.sep + schema + "_schema.json"
            FileSystem.saveFileContent(json.dumps(schemas[schema], indent=3), json_directory + os.sep + schema + "_schema.json")
    Term.print_yellow("< lets_do_json")
    if (schema_file) :
        Term.print_blue("Ready   : "+schema_file)


class Test(unittest.TestCase):

    def setUp(self) -> None:
        Term.setVerbose()
        Term.print_red("> Setup")
        Term.print_red("< Setup")

    def testValidateSchema(self):
        Term.print_green("> testValidateSchema")
        schema = {
            "items": {
                "anyOf": [
                    {"type": "string", "maxLength": 2},
                    {"type": "integer", "minimum": 5}
                ]
            }
        }
        instance = [{}, 3, "foo"]
        validate(instance={"name": "Eggs", "price": 34.99}, schema=schema)
        instance = ["fo", 3]
        validate(instance=instance, schema=schema)
        Term.print_green("< testValidateSchema")


if __name__ == '__main__':
    the_data_model = default_data_model
    if (len(sys.argv) == 2):
        the_data_model = sys.argv[1]

    if FileSystem.is_FileExist(the_data_model+".architect"):
        Term.print_blue("Reading : "+the_data_model+".architect")
        architect = Architect()
        architect.read_architect(the_data_model)
    elif FileSystem.is_FileExist(the_data_model+".dbs"):
        Term.print_blue("Reading : "+the_data_model+".dbs")
        dbschema = DbSchema()
        dbschema.read_dbschema(the_data_model)
    else:
        Term.print_error("Model not found : "+the_data_model)
        exit(2)

    lets_do_json_schema(the_data_model)
    lets_do_openapi_yaml(the_data_model)
    Term.print_blue("Ready   : "+the_data_model+".yaml")
    # ftp_push_file(the_data_model+".yaml")
    # Term.print_blue("FTP Pushed : "+the_data_model+".yaml")
