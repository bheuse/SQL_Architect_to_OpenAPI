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
import glob
import markdown
import platform, socket, shutil, errno, getopt
from jsonpath_ng import jsonpath, parse

timestamp = datetime.datetime.now().strftime("%y%m%d-%H%M%S")
logFile   = "."+os.sep+"sql_architect_to_openapi.log"
logging.basicConfig(filename=logFile, filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)


###
### Print
###

VERBOSE = False


class Term:

    @staticmethod
    def flatten(pDict : dict, sep: str = ":") -> dict:
        newDict = {}
        for key, value in pDict.items():
            if type(value) == dict:
                fDict = {sep.join([key, _key]): _value for _key, _value in Term.flatten(value, sep).items()}
                newDict.update(fDict)
            elif type(value) == list:
                i = 0
                for el in value:
                    if type(el) == dict:
                        fDict = {sep.join([key, str(i), _key]): _value for _key, _value in Term.flatten(el, sep).items()}
                        newDict.update(fDict)
                    else:
                        # fDict = { key + str(i) , str(el)}
                        # newDict.update(fDict)
                        newDict[key + sep + str(i)] = str(el)
                        pass
                    i = i + 1
            else:
                newDict[key] = value
        return newDict

    @staticmethod
    def setVerbose(verbose : bool = True):
        global VERBOSE
        VERBOSE = verbose

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

    @staticmethod
    def print_flat(tree_dict):
        flat_dict = Term.flatten(tree_dict, ":")
        for key in flat_dict.keys() :
            print(colored(key, "blue") + " : " + colored(flat_dict[key], "yellow"))

    @staticmethod
    def json_load(text : str ) -> dict:
        try:
            return json.loads(text)
        except Exception as ex :
            Term.print_error("Error with decoding JSON :")
            Term.print_error(text)
            Term.print_error(str(ex))
            raise ex

    @staticmethod
    def yaml_load(text : str ) -> dict:
        try:
            return yaml.safe_load(text)
        except Exception as ex :
            Term.print_error("Error with decoding YAML :")
            Term.print_error(text)
            Term.print_error(str(ex))
            raise ex

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
        return filename.replace(FileSystem.get_extension(filename), "")

    @staticmethod
    def safeListFiles(dir: str = ".", file_ext: str = "", keepExt = False) -> list:
        myList = list()
        for f in glob.glob(dir+os.sep+"*"+file_ext):
            f = f.replace(dir+os.sep, "")
            if (keepExt is False):
                f = FileSystem.remove_extension(f)
            myList.append(f)
        return myList

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
### Path
###


def get_parameters(text, prefix) -> str :
    found = find_between(text.strip(), "<"+prefix+">", "</"+prefix+">")
    if (found): return found
    return None


paths_template_list_create_prefix  = """
        "${PATH_PREFIX}/${PATH}s": {
            "summary": "Path used to manage the list of ${table}s.",
            "description": "The REST endpoint/path used to list and create zero or more `${TABLE}`.  This path contains a `GET` and `POST` operation to perform the list and create tasks, respectively."
"""


def paths_template_list(parameters : str = None) -> str:
    if ((parameters) and (parameters.strip() == "")): parameters = None
    if (not parameters):
        parameters = ""
    else:
        parameters = "\"parameters\" : [  " + parameters + " ] , "

    paths_template_list = """
                "get": {
                    "operationId": "get${TABLE}s",
                    "summary": "List All ${TABLE}s",
                    "description": "Gets a list of all `${TABLE}` entities.",
                    """ + parameters + """
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
                    }
                }
    """
    return paths_template_list


body_content = """
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/${TABLE}"
                                }
                            }
                        },
                        "required": true
"""

def paths_template_create(parameters : str = None) -> str:
    if ((parameters) and (parameters.strip() == "")): parameters = None
    if (not parameters):
        parameters = ""
    else:
        parameters = "\"parameters\" : [  " + parameters + " ] , "
    paths_template_create = """
                "post": {
                    "operationId": "create${TABLE}",
                    "summary": "Create a ${TABLE}",
                    "description": "Creates a new instance of a `${TABLE}`.",
                    """ + parameters + """
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
                        "202": {
                            "description": "Successful response.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/${TABLE}"
                                    }
                                  }
                            }
                        }
                    }
                }
    """
    return paths_template_create


paths_template_read_write_prefix = """

        "${PATH_PREFIX}/${PATH}s/{${PATH}Id}": {
            "summary": "Path used to manage a single ${TABLE}.",
            "description": "The REST endpoint/path used to get, update, and delete single instances of an `${TABLE}`.  This path contains `GET`, `PUT`, and `DELETE` operations used to perform the get, update, and delete tasks, respectively."
"""


def paths_template_get(parameters : str = None) -> str:
    if ((parameters) and (parameters.strip() == "")): parameters = None
    if (not parameters):
        parameters = ""
    else:
        parameters = "\"parameters\" : [  " + parameters + " ] , "
    paths_template_get = """
                "get": {
                    "operationId": "get${TABLE}",
                    "summary": "Get a ${TABLE}",
                    "description": "Gets the details of a single instance of a `${TABLE}`.",
                    """ + parameters + """
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
                    }
                }
    """
    return paths_template_get


def paths_template_put(parameters : str = None) -> str:
    if ((parameters) and (parameters.strip() == "")): parameters = None
    if (not parameters):
        parameters = ""
    else:
        parameters = "\"parameters\" : [  " + parameters + " ] , "
    paths_template_put = """
                "put": {
                    "operationId": "update${TABLE}",
                    "summary": "Update a ${TABLE}",
                    "description": "Updates an existing `${TABLE}`.",
                    """ + parameters + """
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
                    }
                }
    """
    return paths_template_put


"""
                                "schema": {
                                    "$ref": "#/components/schemas/${TABLE}"
                                }
"""

def paths_template_patch(parameters : str = None) -> str:
    if ((parameters) and (parameters.strip() == "")): parameters = None
    if (not parameters):
        parameters = ""
    else:
        parameters = "\"parameters\" : [  " + parameters + " ] , "
    paths_template_patch = """
                "patch": {
                    "operationId": "update${TABLE}",
                    "summary": "Update a ${TABLE}",
                    "description": "Updates an existing `${TABLE}`.",
                    """ + parameters + """
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
                            "description": "Successful response.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/${TABLE}"
                                     }
                                  }
                            }
                        }
                    }
                }
    """
    return paths_template_patch


def paths_template_delete(parameters : str = None) -> str:
    if ((parameters) and (parameters.strip() == "")): parameters = None
    if (not parameters):
        parameters = ""
    else:
        parameters = "\"parameters\" : [  " + parameters + " ] , "
    paths_template_delete = """
                "delete": {
                    "operationId": "delete${TABLE}",
                    "summary": "Delete a ${TABLE}",
                    "description": "Deletes an existing `${TABLE}`.",
                    """ + parameters + """
                    "responses": {
                        "204": {
                            "description": "Successful response."
                        }
                    }
                }
    """
    return paths_template_delete


def paths_template_parameters() -> str:

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
    return paths_template_parameters


def paths_table(path : str, table: str, path_prefix: str = "", p_paths_template=""):
    l_paths_template = p_paths_template.replace("${PATH_PREFIX}", path_prefix)
    l_paths_template = l_paths_template.replace("${TABLE}", table)
    l_paths_template = l_paths_template.replace("${PATH}", path)
    l_paths_template = l_paths_template.replace("${table}", table.lower())
    return l_paths_template


def create_path(entities):
    global schema_parameters
    f_paths_template = ""
    sep = ""
    for entity in entities:
        if ("PATH" in entities[entity]):
            path_par = None
            path_parameters = None
            list_par = None
            get_par = None
            create_par = None
            patch_par = None
            put_par = None
            del_par = None
            schema_par = None
            if ("PATH_PARAMETERS" in entities[entity]) :
                path_par   = get_parameters(entities[entity]["PATH_PARAMETERS"], "path_parameters")
                list_par   = get_parameters(entities[entity]["PATH_PARAMETERS"], "list_parameters")
                get_par    = get_parameters(entities[entity]["PATH_PARAMETERS"], "get_parameters")
                create_par = get_parameters(entities[entity]["PATH_PARAMETERS"], "post_parameters")
                patch_par  = get_parameters(entities[entity]["PATH_PARAMETERS"], "patch_parameters")
                put_par    = get_parameters(entities[entity]["PATH_PARAMETERS"], "put_parameters")
                del_par    = get_parameters(entities[entity]["PATH_PARAMETERS"], "delete_parameters")
                schema_par = get_parameters(entities[entity]["PATH_PARAMETERS"], "schema_parameters")

            if (schema_par and schema_par.strip() != "") :
                schema_params = Term.json_load(schema_par)
                for param in schema_params:
                    schema_parameters[param] = schema_params[param]
            if (not path_par or path_par.strip() == "") :
                path_par = ""
                path_parameters = "\"parameters\": [" + paths_template_parameters() + "]"
            else:
                path_parameters = "\"parameters\": [" + paths_template_parameters() + "," + path_par + "]"
                path_par = " , \"parameters\": [" + path_par + "]"

            if ("list-read-only" in entities[entity]["PATH_OPERATION"].lower()):
                l_paths_template = paths_template_list_create_prefix + "," + paths_template_list(list_par) + path_par + " } ,"
                l_paths_template = l_paths_template + paths_template_read_write_prefix + "," + path_parameters + "," + paths_template_get(get_par)  + " } "
            elif ("list-create-patch" in entities[entity]["PATH_OPERATION"].lower()):
                l_paths_template = paths_template_list_create_prefix + "," + paths_template_list(list_par) + "," + paths_template_create(create_par)  + path_par + " } ,"
                l_paths_template = l_paths_template + paths_template_read_write_prefix + "," + path_parameters + "," + paths_template_get(get_par) + "," + paths_template_patch(patch_par) + " } "
            elif ("list-create" in entities[entity]["PATH_OPERATION"].lower()):
                l_paths_template = paths_template_list_create_prefix + "," + paths_template_list(list_par) + "," + paths_template_create(create_par) + path_par + " } ,"
                l_paths_template = l_paths_template + paths_template_read_write_prefix + "," + path_parameters + "," + paths_template_get(get_par)   + " } "
            elif ("read-only" in entities[entity]["PATH_OPERATION"].lower()):
                l_paths_template = paths_template_list_create_prefix + "," + paths_template_list(list_par) + path_par + " } ,"
                l_paths_template = l_paths_template + paths_template_read_write_prefix + "," + path_parameters + "," + paths_template_get(get_par)  + " }"
            elif ("read-create" in entities[entity]["PATH_OPERATION"].lower()):
                l_paths_template = paths_template_list_create_prefix + "," + paths_template_list(list_par) + "," + paths_template_create(create_par) + path_par + " } ,"
                l_paths_template = l_paths_template + paths_template_read_write_prefix + "," + path_parameters + "," + paths_template_get(get_par) + "," + paths_template_patch(patch_par) + " } "
            else:  # "read-create"
                l_paths_template = paths_template_list_create_prefix + "," + paths_template_list(list_par) + "," + paths_template_create(create_par) + path_par + " } ,"
                l_paths_template = l_paths_template + paths_template_read_write_prefix + "," + path_parameters + "," + paths_template_get(get_par) + "," + paths_template_put(put_par) + "," + paths_template_delete(del_par) + " } "

            path   = entities[entity]["PATH"]
            prefix = entities[entity]["PATH_PREFIX"]
            f_paths_template = f_paths_template + sep + paths_table(path, entity, path_prefix=prefix, p_paths_template=l_paths_template)
            sep = ", "
    Term.print_verbose(f_paths_template)
    return f_paths_template


###
### Schema Methods
###

def decode_prop_schema(prop: str, schema: str, description: str = None, key : str = "schema") -> dict:
    """ Decode for JSON Schema in <schema> </schema>
    - schema is the text to be decoded
    - prop is used to refer to the related property in error messages
    - description will be used as default is not in schema
    """
    desc_schema = dict()
    if (find_between(schema, "<"+key+">", "</"+key+">")):
        schema = find_between(schema, "<"+key+">", "</"+key+">")
        schema = schema.strip()
        if schema.startswith("{"):  # JSON
            desc_schema = Term.json_load(schema)
        elif schema.startswith("\""):  # JSON
            desc_schema = Term.json_load("{" + schema + "}")
        elif (schema == ""):  # JSON
            desc_schema = dict()
        else:  # YAML
            try:
                desc_schema = Term.yaml_load(schema)
            except Exception as e:
                Term.print_error(schema, str(e))
                desc_schema = dict()
    else:
        desc_schema = dict()
    if ("validationScript" not in desc_schema):
        desc_schema["validationScript"] = ""
        Term.print_error("Warning : property [" + str(prop) + "] validationScript defaulted to : [" + str(desc_schema["validationScript"]) + "]")
    if ("possibleValues" not in desc_schema):
        desc_schema["possibleValues"] = ["default_value", "value1", "value2"]
        Term.print_error("Warning : property [" + str(prop) + "] possibleValues defaulted to : [" + str(desc_schema["possibleValues"]) + "]")
    if ("defaultValue" not in desc_schema):
        desc_schema["defaultValue"] = "default_value"
        Term.print_error("Warning : property [" + str(prop) + "] defaultValue defaulted to : [" + str(desc_schema["defaultValue"]) + "]")
    if ("applicableTo" not in desc_schema):
        desc_schema["applicableTo"] = ""
        Term.print_error("Warning : property [" + str(prop) + "] applicableTo defaulted to : [" + str(desc_schema["applicableTo"]) + "]")
    if ("minCardinality" not in desc_schema):
        desc_schema["minCardinality"] = 1
        Term.print_error("Warning : property [" + str(prop) + "] minCardinality defaulted to : [" + str(desc_schema["minCardinality"]) + "]")
    if ("maxCardinality" not in desc_schema):
        desc_schema["maxCardinality"] = 1
        Term.print_error("Warning : property [" + str(prop) + "] maxCardinality defaulted to : [" + str(desc_schema["maxCardinality"]) + "]")
    if ("validFor" not in desc_schema):
        desc_schema["validFor"] = ""
        Term.print_error("Warning : property [" + str(prop) + "] validFor defaulted to : [" + str(desc_schema["validFor"]) + "]")
    if ("format" not in desc_schema):
        desc_schema["format"] = ""
        Term.print_error("Warning : property [" + str(prop) + "] format defaulted to : [" + str(desc_schema["format"]) + "]")
    if ("example" not in desc_schema):
        desc_schema["example"] = ""
        Term.print_error("Warning : property [" + str(prop) + "] example defaulted to : [" + str(desc_schema["example"]) + "]")
    if ("description" not in desc_schema):
        if (description):
            desc_schema["description"] = description
        else:
            desc_schema["description"] = "No Description"
            Term.print_error("Warning : property [" + str(prop) + "] description defaulted to : [" + str(desc_schema["description"]) + "]")
    if ("markdownDescription" not in desc_schema):
        desc_schema["markdownDescription"] = desc_schema["description"]
        Term.print_error("Warning : property [" + str(prop) + "] markdownDescription defaulted to : [" + str(desc_schema["markdownDescription"]) + "]")
    if ("valueSpecification" not in desc_schema):
        desc_schema["valueSpecification"] = ""
        Term.print_error("Warning : property [" + str(prop) + "] valueSpecification defaulted to : [" + str(desc_schema["valueSpecification"]) + "]")
    return desc_schema


def check_as_parameter(desc, desc_schema):
    """ Check if this desc_schema property should be set as a global schema parameter and create it if necessary
    - description will be used as default is not in schema
    """
    global schema_parameters
    if ("asParameter" in desc_schema):
        param_desc = dict()
        param_desc["name"] = desc_schema["name"]
        if ("path" in desc_schema["asParameter"].lower())  :
            param_desc["in"] = "path"
        else:
            param_desc["in"] = "query"
        param_desc["description"] = desc["description"]
        if (("required" in desc_schema["asParameter"].lower()) or ("mandatory" in desc_schema["asParameter"].lower())) :
            param_desc["required"] = True
        else:
            param_desc["required"] = False
        param_desc["schema"] = dict()
        param_desc["schema"]["type"]   = desc_schema["type"]
        if not ((desc_schema["format"] == "") or (desc_schema["format"] == "free")):
            param_desc["schema"]["format"] = desc_schema["format"]
        # param_desc["schema"]["minimum"] =
        # param_desc["schema"]["maximum"] =
        param_desc["schema"]["default"] = desc_schema["defaultValue"]
        if (desc_schema["possibleValues"] and desc_schema["possibleValues"].__len__() >=1):
            param_desc["schema"]["enum"]    = desc_schema["possibleValues"]
        # param = { desc_schema["name"]+"Param" : param_desc }
        # schema_parameters.append(param)
        schema_parameters[desc_schema["name"]+"Param"] = param_desc
        return param_desc
    else:
        return None

"""
limitParam:       # Can be referenced as '#/components/parameters/limitParam'
      name: limit
      in: query
      description: Maximum number of items to return.
      required: false
      schema:
        type: integer
        format: int32
        minimum: 1
        maximum: 100
        default: 20
"""

def clean_name(name: str) -> str:
    return unidecode.unidecode(name.strip()).replace(" ", "_").replace("\\", "_").replace("'", "_").replace("/", "-").replace("_fk", "")


def find_entity(entities, entity_name):
    """ Return Entity by Name """
    for entity in entities.keys():
        if (("NAME" in entities[entity]) and (entities[entity]["NAME"] == entity_name)):
            return entities[entity]
        if (("name" in entities[entity]) and (entities[entity]["name"] == entity_name)):
            return entities[entity]
    return None


def find_table_contained(links, table_containing) -> list:
    """ Return Contained Tables for a specified Containing Table """
    lks = []
    for link in links:
        if (links[link]["TableContenante"] == table_containing):
            lks.append(links[link])
    return lks

"""
The content of the Data Model in SQL Architect will be used as ReadMe File

The content of the Data Model in DB Schema will be used as in ReadMe File

See ReadMe File

"""

default_data_model = "API_Data_Model_Sample"

# Objects of Interest
entities   = {}   # To OpenAPI Objects
links      = {}   # To OpenAPI Objects
schema_parameters = {}   # To OpenAPI Objects

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

"""


class Architect:

    def __init__(self):
        self.architect = None
        self.tables    = dict()  # From SQL Architect
        self.relations = dict()  # From SQL Architect

    def find_table_name(self, table_id):
        global entities, links
        for table in entities.keys():
            if (entities[table]["TABLE"] == table_id):
                return entities[table]["NAME"]
        return None

    def collect_links(self):
        """ Scan for all Links / Relationships  and their Attributes in the Architect Data Model """
        global entities, links
        if isinstance(self.relations, dict) :
            self.relations = [self.relations]
        for relation in self.relations:
            link = dict()
            if ("ignore" in relation["@name"]) :
                # Ignore starting with ignore (or Grey Links)
                Term.print_verbose("Relation Ignored (ignore in name) : "+clean_name(relation["@name"]))
                continue
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
                    # Ignore Grey Links (or starting with ignore)
                    Term.print_verbose("Relation Ignored (grey color) : " + clean_name(relation["@name"]))
                    ignore = True
                    continue
                if (tlink["@relationship-ref"] == relation["@id"]):
                    link["Description"] = clean_name(tlink["@pkLabelText"]) + " " + clean_name(tlink["@fkLabelText"])
                    if (link["Description"] == " "): link["Description"] = link["Name"]
                if (ignore is False) :
                    links[relation["@id"]] = link


    def handle_object(self, table):
        """ Extract Data from Architect Table for Object Descriptors """
        obj_desc = {}
        name = clean_name(table["@name"])
        obj_desc["name"] = "name"
        obj_desc["type"] = "object"
        if (table["remarks"]):
            obj_desc["description"] = table["remarks"]
        else:
            obj_desc["description"] = "No Description for " + table["@name"]
        obj_desc["example"]    = table["@physicalName"]
        obj_desc["properties"] = {}
        obj_desc["NAME"]       = name
        obj_desc["TABLE"]      = table["@id"]
        obj_desc["RELATIONS"]  = {}
        return obj_desc, name

    def handle_attribute(self, obj_desc, att):
        """ Extract Data from Architect Table Attribute for Object Property Descriptors """
        obj_property = {}
        name = clean_name(att["@name"])
        obj_property["name"] = name
        if (name == "_PATH"):
            obj_desc["PATH"]        = att["@physicalName"]
            obj_desc["PATH_PREFIX"] = att["@defaultValue"]
            obj_desc["PATH_OPERATION"] = "READ-WRITE"
            if (att["remarks"] is not None):
                desc  = att["remarks"]
                found = find_between(desc, "<parameters>", "</parameters>")
                if (found):
                    desc = remove_between(desc, "<parameters>", "</parameters>")
                    obj_desc["PATH_PARAMETERS"] = found
                obj_desc["PATH_OPERATION"]  = desc

        obj_property["type"] = "INVALID"
        if (att["remarks"] is None):
            obj_property["description"] = "No Description for " + att["@name"]
        else:
            obj_property["description"] = att["remarks"]

        desc_schema = decode_prop_schema(name, obj_property["description"], key="schema")

        if (att["@physicalName"] is None):
            obj_property["example"] = "No example for " + att["@name"]
        else:
            obj_property["example"] = att["@physicalName"]
        if ((att["@nullable"] == "1") or (name == "_PATH") or (name == "_ROOT") or (desc_schema["minCardinality"] == 0)) :
            obj_property["mandatory"] = "n"
        else:
            if "required" not in obj_desc : obj_desc["required"] = list()
            obj_desc["required"].append(name)
            obj_property["mandatory"] = "y"
        obj_property["pattern"] = att["@defaultValue"]
        obj_property["type"]   = "string"
        obj_property["format"] = ""
        if (att["@type"] == "12"): obj_property["type"]   = "string"   # VARCHAR
        if (att["@type"] == "4"):  obj_property["type"]   = "integer"
        if (att["@type"] == "-5"): obj_property["type"]   = "integer"  # BIGINT
        if (att["@type"] == "92"): obj_property["type"]   = "string"
        if (att["@type"] == "92"): obj_property["format"] = "date-time"
        if (att["@type"] == "16"): obj_property["type"]   = "boolean"  # BOOLEAN
        if (desc_schema["maxCardinality"] > 1):
            # Array
            obj_property["items"] = dict()
            obj_property["items"]["type"]   = obj_property["type"]
            obj_property["items"]["format"] = obj_property["format"]
            obj_property["type"] = "array"
            obj_property["minItems"] = desc_schema["minCardinality"]
            obj_property["maxItems"] = desc_schema["maxCardinality"]

        if (obj_property["type"] == "INVALID"):
            Term.print_error("Unsupported Attribute Type : " + att["@type"])
        if (name != "_PATH"):
            obj_desc["properties"][name] = obj_property
        return obj_desc, name

    def collect_tables(self):
        """ Scan for all Tables and their Attributes in the Architect Data Model """
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
                Term.print_verbose("Table Ignored (ignore in example/physicalName) : " + clean_name(entity_name))
                continue
            entities[entity_name] = data_type

    def read_architect(self, data_model : str):
        """ Read and Scan Architect Data Model """
        Term.print_yellow("> read_architect")
        global entities, links

        # Reading architect file
        myFile = open(data_model + ".architect", "r")
        architectSchema = myFile.read()
        myFile.close()
        self.architect = xmltodict.parse(architectSchema)

        # Save to JSON Format
        # FileSystem.saveFileContent(json.dumps(self.architect, indent=3), data_model + ".json")
        Term.print_verbose("architect : \n" + json.dumps(self.architect, indent=3))

        # Collecting architect entities
        self.tables    = self.architect["architect-project"]["target-database"]["table"]
        self.relations = self.architect["architect-project"]["target-database"]["relationships"]["relationship"]
        self.collect_links()
        self.collect_tables()

        # Replacing Table IDs by Names & Creating Sub-Relationships
        for entity in entities:
            for rel in find_table_contained(links, entities[entity]["TABLE"]):
                if (not self.find_table_name(rel["TableContenue"])):
                    continue
                rel["TableContenanteID"] = rel["TableContenante"]
                rel["TableContenueID"]   = rel["TableContenue"]
                rel["TableContenante"]   = self.find_table_name(rel["TableContenante"])
                rel["TableContenue"]     = self.find_table_name(rel["TableContenue"])
                entities[entity]["RELATIONS"][rel["Name"]] = rel
                this_property = dict()
                this_property["description"] = rel["Description"]
                if (rel["Cardinalite"] == "OneToOne") or (rel["Cardinalite"] == "ZeroToOne") :
                    this_property["$ref"] = "#/components/schemas/" + rel["TableContenue"]
                else:
                    this_property["type"] = "array"
                    this_property["items"] = {}
                    this_property["items"]["$ref"] = "#/components/schemas/" + rel["TableContenue"]
                entities[entity]["properties"][rel["TableContenue"]] = this_property

        # What did we get ?
        Term.print_verbose("tables    : " + str(self.tables))
        Term.print_verbose("relations : " + str(self.relations))
        Term.print_verbose("entities  : " + str(entities))
        Term.print_verbose("links     : " + str(links))

        Term.print_yellow("< read_architect")
        return entities, links

"""
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
"""


def lets_do_openapi_yaml(data_model : str):
    """ Created Openapi Yaml from Data Model """
    Term.print_yellow("> lets_do_openapi Yaml API")
    global entities, links, schema_parameters

    # Create API Operations
    paths = create_path(entities)
    paths_to_create = Term.json_load("{" + paths + "}")

    # Info Data
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
            contacts = Term.json_load(entities["OpenAPI"]["properties"]["contact"]["description"])
            open_api_yaml["info"]["contact"] = contacts

        if ("security" in entities["OpenAPI"]["properties"]):
            security = Term.json_load(entities["OpenAPI"]["properties"]["security"]["description"])
            open_api_yaml["security"] = security

        if ("license" in entities["OpenAPI"]["properties"]):
            license = Term.json_load(entities["OpenAPI"]["properties"]["license"]["description"])
            open_api_yaml["info"]["license"] = license

        if ("tags" in entities["OpenAPI"]["properties"]):
            tags = Term.json_load(entities["OpenAPI"]["properties"]["tags"]["description"])
            open_api_yaml["tags"] = tags

        if ("servers" in entities["OpenAPI"]["properties"]):
            servers = Term.json_load(entities["OpenAPI"]["properties"]["servers"]["description"])
            open_api_yaml["servers"] = servers

        if ("securitySchemes" in entities["OpenAPI"]["properties"]):
            securitySchemes = Term.json_load(entities["OpenAPI"]["properties"]["securitySchemes"]["description"])
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
                        desc_schema = decode_prop_schema(property, found, description=desc)
                        check_as_parameter(entities_yaml[entity]["properties"][prop], desc_schema)
                    except Exception as e:
                        Term.print_error(found, str(e))
                entities_yaml[entity]["properties"][prop]["description"]  = desc.strip()

    # Add Paths
    open_api_yaml["paths"] = paths_to_create
    if "components" in open_api_yaml:
        open_api_yaml["components"]["schemas"] = entities_yaml
    else:
        open_api_yaml["components"] = {"schemas": entities_yaml}

    # Add Parameters
    if "components" in open_api_yaml:
        open_api_yaml["components"]["parameters"] = schema_parameters
    else:
        open_api_yaml["components"] = {"parameters": schema_parameters}

    # Re-Order
    open_api = dict()
    if "openapi"      in open_api_yaml : open_api["openapi"]      = open_api_yaml["openapi"]
    if "info"         in open_api_yaml : open_api["info"]         = open_api_yaml["info"]
    if "externalDocs" in open_api_yaml : open_api["externalDocs"] = open_api_yaml["externalDocs"]
    if "servers"      in open_api_yaml : open_api["servers"]      = open_api_yaml["servers"]
    if "security"     in open_api_yaml : open_api["security"]     = open_api_yaml["security"]
    if "paths"        in open_api_yaml : open_api["paths"]        = open_api_yaml["paths"]
    if "components"   in open_api_yaml : open_api["components"]   = open_api_yaml["components"]

    # Some Custom for NEF_Configuration_Service
    if ("NEF_Configuration_Service" in data_model) :
        for path in open_api["paths"] :
            for op in open_api["paths"][path]:
                if (op == "get") :
                    del open_api["paths"][path][op]["responses"]["200"]["content"]["application/json"]["schema"]
                if (op == "post"):
                    open_api["paths"][path][op]["requestBody"]["content"]["application/json"]["schema"]["$ref"] = "#/components/schemas/Configuration"
                    # open_api["paths"][path][op]["responses"]["202"]["content"]["application/json"]["schema"]
                if (op == "patch"):
                    del open_api["paths"][path][op]["requestBody"]
                    # del open_api["paths"][path][op]["requestBody"]["content"]["application/json"]["schema"]
                    # del open_api["paths"][path][op]["responses"]["202"]["content"]["application/json"]["schema"]

    Term.print_yellow("< lets_do_openapi")
    Term.print_verbose(open_api)

    # Done - Save
    yaml_text = yaml.safe_dump(open_api, indent=2, default_flow_style=False, sort_keys=False)
    Term.print_verbose(yaml_text)
    FileSystem.saveFileContent(yaml_text, data_model+".yaml")
    Term.print_blue("Ready   : " + data_model + ".yaml")

baseURI  = "https://amdocs.com/schemas/nef/"
schemas  = {}

def lets_do_json_schema(data_model : str):
    Term.print_yellow("> lets_do_json Schema")
    ex_objets = {}

    entities_json = copy.deepcopy(entities)
    # Clean-up before generation
    for entity in entities_json:
        if ("TABLE" in entities_json[entity])     : del entities_json[entity]["TABLE"]
        if ("RELATIONS" in entities_json[entity]) : del entities_json[entity]["RELATIONS"]
        if ("NAME" in entities_json[entity])      : del entities_json[entity]["NAME"]
        if ("prepend" in entities_json[entity])   : del entities_json[entity]["prepend"]
        if ("append" in entities_json[entity])    : del entities_json[entity]["append"]
        if ("options" in entities_json[entity])   : del entities_json[entity]["options"]
        if ("PATH_OPERATION" in entities_json[entity]):  del entities_json[entity]["PATH_OPERATION"]
        if ("PATH_PARAMETERS" in entities_json[entity]): del entities_json[entity]["PATH_PARAMETERS"]
        if ("PATH_PREFIX" in entities_json[entity]):     del entities_json[entity]["PATH_PREFIX"]
        if ("PATH"  in entities_json[entity]):           del entities_json[entity]["PATH"]
        # if ("name" in entities_json[entity]) :           del entities_json[entity]["name"]
        # if ("mandatory" in entities_json[entity]) :      del entities_json[entity]["mandatory"]
        Term.print_verbose("> " + entity)
        for prop in entities_json[entity]["properties"] :
            Term.print_verbose(" - " + prop)
            # if ("name" in entities_json[entity]["properties"][prop]):           del entities_json[entity]["properties"][prop]["name"]
            # if ("mandatory" in entities_json[entity]["properties"][prop]):      del entities_json[entity]["properties"][prop]["mandatory"]
            continue

    for entity in entities_json:
        Term.print_yellow("["+entity+"]")
        Term.print_verbose(json.dumps(entities_json[entity], indent=3))
        Term.print_verbose(" - description : " + str(entities_json[entity]["description"]))
        Term.print_verbose(" - type        : " + str(entities_json[entity]["type"]))
        Term.print_verbose(" - example     : " + str(entities_json[entity]["example"]))
        Term.print_verbose(" - " + str(entities_json[entity]))

        is_root = False
        json_object = {}
        json_schema = {}
        object_desc = entities_json[entity]

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

        for new_property in object_desc["properties"]:
            if (new_property == "_ROOT"):
                is_root = True
            Term.print_verbose(" #> [" + str(object_desc["properties"][new_property]) + "]")
            Term.print_verbose(json.dumps(object_desc["properties"][new_property], indent=3))
            property_desc = object_desc["properties"][new_property]
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
                if ("$ref" in property_desc["items"]):
                    # Array of Sub-objects
                    Term.print_verbose("   #>> Array objects : " + str(property_desc["items"]["$ref"]))
                    item = re.sub("#/components/schemas/", "", str(property_desc["items"]["$ref"]))
                    prop_schema["type"] = "array"
                    prop_schema["items"] = {"$ref" : "" + item + "_schema.json"}
                    prop_schema["items"] = {"$ref" : "#/$defs/" + item + ""}
                    # json_schema["properties"][item+"s"] = prop_schema
                    json_schema["properties"][item] = prop_schema
                else:
                    # Array of Basic Types
                    Term.print_verbose("   #>> Array Types : " + str(property_desc["items"]["type"]))
                    prop_schema["type"] = "array"
                    prop_schema["items"] = {"type" : property_desc["items"]["type"] , "format" : property_desc["items"]["format"] }
            else:
                # Value Property
                desc = property_desc["description"]
                found = find_between(desc, "<schema>", "</schema>")
                desc_schema = {}
                if (found):
                    Term.print_verbose(found)
                    desc = remove_between(desc, "<schema>", "</schema>")
                    desc_schema = decode_prop_schema(new_property, found, desc)

                if (property_desc["name"] != "_ROOT"):
                    json_object[property_desc["name"]] = property_desc["example"] if ("example" in property_desc) else "noExample"
                prop_schema["$id"]          = "#/properties/" + property_desc["name"]
                prop_schema["type"]         = property_desc["type"]
                prop_schema["title"]        = property_desc["name"]
                prop_schema["description"]  = desc.strip()
                prop_schema["default"]      = ""
                prop_schema["examples"]     = [property_desc["example"] ,  property_desc["pattern"]]

                prop_schema["validationScript"] = desc_schema["validationScript"] if ("validationScript" in desc_schema) else ""
                prop_schema["possibleValues"]   = desc_schema["possibleValues"]   if ("possibleValues"   in desc_schema) else ["default_value", "value1" , "value2"]
                prop_schema["defaultValue"]     = desc_schema["defaultValue"]     if ("defaultValue"     in desc_schema) else "default_value"
                prop_schema["applicableTo"]     = desc_schema["applicableTo"]     if ("applicableTo"     in desc_schema) else ""
                prop_schema["minCardinality"]   = desc_schema["minCardinality"]   if ("minCardinality"   in desc_schema) else 1
                prop_schema["maxCardinality"]   = desc_schema["maxCardinality"]   if ("maxCardinality"   in desc_schema) else 1
                prop_schema["validFor"]         = desc_schema["validFor"]         if ("validFor"         in desc_schema) else ""
                prop_schema["format"]           = desc_schema["format"]           if ("format"           in desc_schema) else ""
                prop_schema["examples"]         = desc_schema["examples"]         if ("examples"         in desc_schema) else prop_schema["examples"]
                prop_schema["description"]      = desc_schema["description"]      if ("description"      in desc_schema) else desc
                prop_schema["markdownDescription"] = desc_schema["markdownDescription"] if ("markdownDescription"  in desc_schema) else ""
                prop_schema["valueSpecification"]  = desc_schema["valueSpecification"]  if ("valueSpecification"   in desc_schema) else {}
                if (property_desc["name"] != "_ROOT"):
                    json_object[property_desc["name"]] = prop_schema["defaultValue"]

                Term.print_verbose("   #>> name        : " + str(property_desc["name"]))
                Term.print_verbose("   #>> description : " + str(property_desc["description"]))
                Term.print_verbose("   #>> type        : " + str(property_desc["type"]))
                Term.print_verbose("   #>> format      : " + str(property_desc["format"]))
                Term.print_verbose("   #>> example     : " + str(property_desc["example"]))
                Term.print_verbose("   #>> pattern     : " + str(property_desc["pattern"]))
                Term.print_verbose("   #>> format      : " + str(property_desc["format"]))
                Term.print_verbose("   #>> mandatory   : " + str(property_desc["mandatory"]))
                if (property_desc["mandatory"] and property_desc["mandatory"] == "y"):
                    json_schema["required"].append(property_desc["name"])
                json_schema["properties"][property_desc["name"]] = prop_schema
        Term.print_verbose("Sample Object: "+str(json_object))
        json_schema["examples"]    = [json_object]
        ex_objets[entity] = json_object
        schemas[entity] = json_schema

        # Add $defs Sub-Objects Schemas
        for link in links:
            cardinality     = links[link]["Cardinalite"]
            TableContenue   = links[link]["TableContenue"]
            TableContenante = links[link]["TableContenante"]
            Name            = links[link]["Name"]
            Descr           = links[link]["Description"]
            Term.print_verbose(TableContenante + " Contains [" + cardinality + "] " + TableContenue)
            # if (entity == TableContenante) and ("Optional" not in str(cardinality)):
            #     json_schema["required"].append(TableContenue)
            if (entity == TableContenante) and (str(cardinality)  in ["1", "3", "OneToMore" , "OneToOne"]):
                json_schema["required"].append(TableContenue)

        if (is_root) :
            # json_directory = data_model + "_json"
            # if (not os.path.isdir(json_directory)):
            #    os.mkdir(json_directory)

            # FileSystem.saveFileContent(json.dumps(json_object, indent=3), json_directory + os.sep + entity + ".json")
            # FileSystem.saveFileContent(json.dumps(json_schema, indent=3), json_directory + os.sep + entity + "_schema.json")
            # FileSystem.saveFileContent(json.dumps(json_schema, indent=3),   data_model + "_Schema.json")
            pass

    # Add $defs Sub-Objects Schemas
    schema_file = None
    for schema in schemas:
        if "properties" not in schemas[schema]: continue
        if "_ROOT" in schemas[schema]["properties"] :
            # del schemas[schema]["properties"]["_ROOT"]
            schemas[schema]["$defs"] = {}
            for schema2 in schemas:
                if "properties" not in schemas[schema]: continue
                if "_ROOT" in schemas[schema2]["properties"] :
                    del schemas[schema2]["properties"]["_ROOT"]
                    continue
                del schemas[schema2]["$schema"]
                del schemas[schema2]["$id"]
                schemas[schema]["$defs"][schema2] = schemas[schema2]
            # schema_file = data_model + "_" + schema + "_Schema.json"
            schema_file = data_model + "_Schema.json"
            FileSystem.saveFileContent(json.dumps(schemas[schema], indent=3), schema_file)

    Term.print_yellow("< lets_do_json")
    Term.print_verbose(json.dumps(ex_objets, indent=3))
    if (schema_file) :
        Term.print_blue("Ready   : "+schema_file)
    else:
        Term.print_error("No _ROOT Entry")


def lets_do_it(the_data_model, what : str = "openapi + schema"):
    if FileSystem.is_FileExist(the_data_model+".architect"):
        Term.print_blue("Reading : "+the_data_model+".architect")
        architect = Architect()
        architect.read_architect(the_data_model)
    elif FileSystem.is_FileExist(the_data_model+".dbs"):
        Term.print_error("Disabled : "+the_data_model+".dbs")
        # Term.print_blue("Reading : "+the_data_model+".dbs")
        # dbschema = DbSchema()
        # dbschema.read_dbschema(the_data_model)
    else:
        Term.print_error("Model not found : "+the_data_model)
        return

    if ("schema" in what.lower()) :
        lets_do_json_schema(the_data_model)
    if (("openapi" in what.lower()) or ("yaml" in what.lower())) :
        lets_do_openapi_yaml(the_data_model)


class Test(unittest.TestCase):

    def setUp(self) -> None:
        Term.print_red("> Setup")
        Term.setVerbose()
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

    def testGenerateNEFConfigurationSchema(self):
        Term.setVerbose(False)
        lets_do_it("Nef"+os.sep+"NEF_Configuration", "schema")

    def testGenerateNEFConfigurationService(self):
        Term.setVerbose(False)
        lets_do_it("Nef"+os.sep+"NEF_Configuration_Service", "openapi")

    def testGenerateNEFMarketPlaceDataService(self):
        Term.setVerbose(False)
        lets_do_it("Nef"+os.sep+"NEF_MarketPlace_DataModel", "openapi")

    def testGenerateNEFCatalogDataService(self):
        Term.setVerbose(False)
        lets_do_it("Nef"+os.sep+"NEF_Catalog_DataModel", "openapi + schema")

if __name__ == '__main__':
    the_data_model = default_data_model
    what = "openapi , yaml"
    if (len(sys.argv) >= 2):
        the_data_model = sys.argv[1]
    if (len(sys.argv) >= 3):
        what = sys.argv[2]
    lets_do_it(the_data_model, what)
