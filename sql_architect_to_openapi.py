import xmltodict
import json
import yaml
import unidecode
import sys

"""
The content of the Data Model in SQL Architect will be used as follow:

See ReadMe File

"""

default_data_model = "API_Data_Model_Sample"

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

# Objects of Interest
project = {}
entities = {}
links = {}
tables = {}
relations = {}


def log():
    # print("project : " + str(project))
    # print("entities : " + str(entities))
    # print("links : " + str(links))
    # print("tables : " + str(tables))
    # print("relations : " + str(relations))
    return

# Util
def clean_name(name: str) -> str:
    return unidecode.unidecode(name.strip()).replace(" ", "_").replace("\\", "_").replace("'", "_").replace("/", "-").replace("_fk", "")


def saveFileContent(content, file_name: str):
    with open(file_name, "w") as file:
        content = file.write(content)
        file.close()
    return content


def find_table_name(table_id):
    for table in entities.keys():
        if (entities[table]["TABLE"] == table_id):
            return entities[table]["NAME"]
    return None


def find_table(table_name):
    for table in entities.keys():
        if (entities[table]["NAME"] == table_name):
            return entities[table]
    return None


def collect_links():
    global entities, links, tables, relations, project
    for relation in relations:
        link = dict()
        if ("ignore" in relation["@name"]) :
            continue  # Ignore Grey Links or starting with ignore
        link["TableContenante"] = relation["@pk-table-ref"]   # find_table_name(relation["@pk-table-ref"])
        link["TableContenue"]   = relation["@fk-table-ref"]   # find_table_name(relation["@fk-table-ref"])
        link["Cardinalite"]     = relation["@fkCardinality"]
        link["Name"]            = clean_name(relation["@name"])
        link["Description"]     = "No Description"
        ignore = False
        for tlink in project["play-pen"]["table-link"]:
            if (tlink["@rLineColor"] == "0x999999"):
                ignore = True  # Ignore Grey Links
                continue
            if (tlink["@relationship-ref"] == relation["@id"]):
                link["Description"] = clean_name(tlink["@pkLabelText"]) + " " + clean_name(tlink["@fkLabelText"])
                if (link["Description"] == " "): link["Description"] = link["Name"]
            if (ignore is False) :
                links[relation["@id"]] = link


def find_table_contenues(table_contenante) -> list:
    lks = []
    for link in links:
        if (links[link]["TableContenante"] == table_contenante):
            lks.append(links[link])
    return lks


def handle_object(table):
    data_type = {}
    name = clean_name(table["@name"])
    # data_type["required"] = []
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


def handle_attribute(data_type, att):
    this_property = {}
    name = clean_name(att["@name"])
    if (name == "_PATH"):
        data_type["PATH"]        = att["@physicalName"]
        data_type["PATH_PREFIX"] = att["@defaultValue"]
        data_type["PATH_OPERATION"] = "READ-WRITE"
        if (att["remarks"] is not None):
            data_type["PATH_OPERATION"] = att["remarks"]
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
        pass
        # this_property["required"]     = False
    else:
        if (name != "_PATH"):
            if "required" not in data_type : data_type["required"] = list()
            data_type["required"].append(name)
            # this_property["required"]     = True
    this_property["pattern"] = att["@defaultValue"]
    if (att["@type"] == "12"): this_property["type"]   = "string"
    if (att["@type"] == "4"):  this_property["type"]   = "integer"
    if (att["@type"] == "92"): this_property["type"]   = "string"
    if (att["@type"] == "92"): this_property["format"] = "date-time"
    if (att["@type"] == "16"): this_property["type"]   = "boolean"
    if (this_property["type"] == "INVALID"):
        print("Unsupported Attribute Type : " + att["@type"])
    if (name != "_PATH"):
        data_type["properties"][name] = this_property
    return data_type, name


def collect_tables():
    global entities, links, tables, relations, project
    for table in tables:
        data_type, entity_name = handle_object(table)
        for folder in table["folder"]:
            if "column" not in folder: continue
            column = folder["column"]
            if isinstance(column, list):
                for col in column:
                    data_type, att_name = handle_attribute(data_type, col)
            else:
                data_type, att_name = handle_attribute(data_type, column)
        if ("ignore" in data_type["example"]) :
            continue
        entities[entity_name] = data_type


def paths_table(table: str, path_prefix: str = "", paths_template=""):
    l_paths_template = paths_template.replace("${PATH_PREFIX}", path_prefix)
    l_paths_template = l_paths_template.replace("${TABLE}", table)
    l_paths_template = l_paths_template.replace("${table}", table.lower())
    return l_paths_template


def create_path():
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


def lets_do_it(data_model : str):
    global entities, links, tables, relations, project

    # Reading architect file
    myFile = open(data_model + ".architect", "r")
    architect = myFile.read()
    myFile.close()
    obj = xmltodict.parse(architect)
    saveFileContent(json.dumps(obj, indent=3), data_model + ".json")

    # Collecting architect entities
    project   = obj["architect-project"]
    database  = project["target-database"]
    tables    = database["table"]
    relations = database["relationships"]["relationship"]

    collect_links()

    collect_tables()

    log()

    for entity in entities:
        LINK_TABLE_CONT = find_table_contenues(entities[entity]["TABLE"])
        for rel in LINK_TABLE_CONT:
            rel["TableContenanteID"] = rel["TableContenante"]
            rel["TableContenueID"]   = rel["TableContenue"]
            rel["TableContenante"]   = find_table_name(rel["TableContenante"])
            rel["TableContenue"]     = find_table_name(rel["TableContenue"])
            entities[entity]["RELATIONS"][rel["Name"]] = rel
            this_property = dict()
            this_property["description"] = rel["Description"]
            this_property["$ref"] = "#/components/schemas/" + rel["TableContenue"]
            entities[entity]["properties"][rel["TableContenue"]] = this_property

    paths_to_create = json.loads("{" + create_path() + "}")

    open_api_yaml = dict()
    open_api_yaml["openapi"] = "3.0.2"
    open_api_yaml["info"] = {}
    open_api_yaml["info"]["title"] = "Business Data Model"
    open_api_yaml["info"]["version"] = "1.0.0"
    open_api_yaml["info"]["description"] = "Business Data Model. This is generated, modify source SQL Architect data model instead."
    open_api_yaml["info"]["contact"] = {}
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

    for entity in entities:
        del entities[entity]["TABLE"]
        del entities[entity]["RELATIONS"]
        del entities[entity]["NAME"]
        if ("PATH_OPERATION" in entities[entity]):  del entities[entity]["PATH_OPERATION"]
        if ("PATH_PREFIX" in entities[entity]):     del entities[entity]["PATH_PREFIX"]
        if ("PATH"  in entities[entity]):           del entities[entity]["PATH"]

    open_api_yaml["paths"] = paths_to_create
    if "components" in open_api_yaml:
        open_api_yaml["components"]["schemas"] = entities
    else:
        open_api_yaml["components"] = {"schemas": entities}

    yaml_text = yaml.safe_dump(open_api_yaml, indent=3, default_flow_style=False)
    # print(yaml_text)
    yaml_file = data_model+".yaml"
    saveFileContent(yaml_text, yaml_file)

if __name__ == '__main__':
    data_model = default_data_model
    if (len(sys.argv) == 2):
        data_model = sys.argv[1]
    print("Reading : "+data_model+".architect")
    lets_do_it(data_model)
    print("Ready   : "+data_model+".yaml")
