import xmltodict
import json
import yaml
import unidecode
import sys
import os
import re

"""
The content of the Data Model in DB Schema will be used as in ReadMe File

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
tables   = {}  # From the Schema
links    = {}  # From the Schema
entities = {}  # To OpenAPI Objects

def log():
    # print("entities  : " + str(entities))
    # print("links     : " + str(links))
    # print("tables    : " + str(tables))
    return


# Util
def clean_name(name: str) -> str:
    return unidecode.unidecode(name.strip()).replace(" ", "_").replace("\\", "_").replace("'", "_").replace("/", "-").replace("_fk", "")


def saveFileContent(content, file_name: str):
    with open(file_name, "w") as file:
        content = file.write(content)
        file.close()
    return content


def find_table(table_name):
    for table in entities.keys():
        if (entities[table]["NAME"] == table_name):
            return entities[table]
    return None


def find_table_contenues(table_contenante) -> list:
    lks = []
    for link in links:
        if (links[link]["TableContenante"] == table_contenante):
            lks.append(links[link])
    return lks


def handle_table(table):
    # @name, @spec, comment,
    # Not used : options, pre_script, post_script
    # Not usable : @prior,
    data_type = {}
    name = clean_name(table["@name"])
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


def handle_attribute(data_type, att, entity_name):
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
        data_type["PATH"]           = clean_name(entity_name)
        data_type["PATH_PREFIX"]    = att["defo"]     if ("defo" in att)    else "/"+clean_name(entity_name).lower()
        data_type["PATH_OPERATION"] = att["comment"]  if ("comment" in att) else "READ-WRITE"
        return data_type, name

    property = {}
    property["description"]    = att["comment"]  if ("comment" in att) else "No Description for " + att["@name"]
    if ("@defo" in att): property["pattern"] = att["@defo"]

    property["example"] = re.sub(".*xample:" , "" , property["description"])

    if (not(("mandatory" in att) and (att["mandatory"] != "y"))):
        # Required property
        if "required" not in data_type : data_type["required"] = list()
        data_type["required"].append(name)

    property["type"] = "INVALID"
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
        print("Unsupported Attribute Type : " + att["@type"])
    data_type["properties"][name] = property
    return data_type, name


def handle_link(data_type, relation, entity_name):
    # "@name"       : "fk_ue_restrictions_service",
    # "@to_schema"  : "NEF_MarketPlace_DataModel",
    # "@to_table"   : "Service",
    # "@type"       : "Identifying",
    # "comment"     : "Service Owner"
    global entities, links, tables
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


def collect_entities_links():
    global entities, links, tables
    for table in tables:
        # print(table)
        data_type, entity_name = handle_table(table)
        if "column" in table:
            if isinstance(table["column"], list):
                for col in table["column"]:
                    data_type, att_name = handle_attribute(data_type, col, entity_name)
            else:
                data_type, att_name = handle_attribute(data_type, table["column"], entity_name)
        data_type["RELATIONS"] = {}
        if "fk" in table:
            if isinstance(table["fk"], list):
                for rel in table["fk"]:
                    data_type, att_name = handle_link(data_type, rel, entity_name)
            else:
                data_type, att_name = handle_link(data_type, table["fk"], entity_name)
        if ("ignore" in data_type["example"]) :
            continue
        entities[entity_name] = data_type


def handle_links():
    for link in links:
        property = dict()
        property["description"] = links[link]["Description"]
        if (links[link]["Cardinality"] == "OneToOne") :
            property["$ref"] = "#/components/schemas/" + links[link]["TableContenue"]
        else:
            property["type"] = "array"
            property["items"] = {}
            property["items"]["$ref"] = "#/components/schemas/" + links[link]["TableContenue"]
        table = find_table(links[link]["TableContenante"])
        table["properties"][links[link]["TableContenue"]] = property


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
    global entities, links, tables

    # Reading dbschema file
    myFile = open(data_model + ".dbs", "r")
    dbschema = myFile.read()
    myFile.close()
    dict_schema  = xmltodict.parse(dbschema)
    saveFileContent(json.dumps(dict_schema, indent=3), data_model + ".json")

    # Collecting Table & Links
    tables   = dict_schema["project"]["schema"]["table"]
    collect_entities_links()

    # Handle Relationships between entities
    handle_links()

    # Create API Operations
    paths_to_create = json.loads("{" + create_path() + "}")

    # What did we get ?
    log()


    # API Information Properties
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

    if "OpenAPI" in entities:
        if ("title" in entities["OpenAPI"]["properties"]):
            open_api_yaml["info"]["title"]       = entities["OpenAPI"]["properties"]["title"]["description"]

        if ("version" in entities["OpenAPI"]["properties"]):
            open_api_yaml["info"]["version"]     = entities["OpenAPI"]["properties"]["version"]["description"]

        if ("description" in entities["OpenAPI"]["properties"]):
            open_api_yaml["info"]["description"] = entities["OpenAPI"]["properties"]["description"]["description"]

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

        if ("externalDocs" in entities["OpenAPI"]["properties"]):
            externalDocs = json.loads(entities["OpenAPI"]["properties"]["externalDocs"]["description"])
            open_api_yaml["info"]["externalDocs"] = externalDocs

        if ("terms" in entities["OpenAPI"]["properties"]):
            terms = json.loads(entities["OpenAPI"]["properties"]["externalDocs"]["terms"])
            open_api_yaml["info"]["terms"] = terms

        del entities["OpenAPI"]

    # Clean-up before generation
    for entity in entities:
        del entities[entity]["TABLE"]
        del entities[entity]["RELATIONS"]
        del entities[entity]["NAME"]
        del entities[entity]["prepend"]
        del entities[entity]["append"]
        del entities[entity]["options"]
        if ("PATH_OPERATION" in entities[entity]):  del entities[entity]["PATH_OPERATION"]
        if ("PATH_PREFIX"    in entities[entity]):  del entities[entity]["PATH_PREFIX"]
        if ("PATH"           in entities[entity]):  del entities[entity]["PATH"]

    # Add Paths
    open_api_yaml["paths"] = paths_to_create
    if "components" in open_api_yaml:
        open_api_yaml["components"]["schemas"] = entities
    else:
        open_api_yaml["components"] = {"schemas": entities}

    # Done - Save
    yaml_text = yaml.safe_dump(open_api_yaml, indent=3, default_flow_style=False)
    yaml_file = data_model+".yaml"
    saveFileContent(yaml_text, yaml_file)
    # print(yaml_text)

if __name__ == '__main__':
    data_model = default_data_model
    if (len(sys.argv) == 2):
        data_model = sys.argv[1]
    print("Reading : "+data_model+".dbs")
    lets_do_it(data_model)
    print("Ready   : "+data_model+".yaml")
