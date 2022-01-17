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
from termcolor     import colored
import util as ut

timestamp = datetime.datetime.now().strftime("%y%m%d-%H%M%S")
logFile   = "."+os.sep+"db_schema_to_openapi.log"
logging.basicConfig(filename=logFile, filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)


"""
The content of the Data Model in DB Schema will be used as in ReadMe File
"""

default_data_model = "API_Data_Model_Sample"


# Objects of Interest
links    = {}  # From the Schema
entities = {}  # To OpenAPI Objects



def lets_do_openapi_yaml(data_model : str):
    ut.print_yellow("> lets_do_openapi")
    global entities, links

    # Create API Operations
    paths_to_create = json.loads("{" + ut.create_path(entities) + "}")

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
    ut.print_verbose(yaml_text)
    yaml_file = data_model+".yaml"
    ut.saveFileContent(yaml_text, yaml_file)


baseURI = "https://amdocs.com/schemas/nef/"
schemas = {}


def lets_do_json_schema(data_model : str):
    ut.print_yellow("> lets_do_json")
    json_directory = data_model + "_json"
    if (not os.path.isdir(json_directory)):
        os.mkdir(json_directory)
    for entity in entities:
        is_root = False
        json_object = {}
        json_schema = {}
        object_desc = entities[entity]
        ut.print_yellow("["+entity+"]")
        ut.print_verbose(json.dumps(entities[entity], indent=3))
        ut.print_verbose(" - description : " + str(object_desc["description"]))
        ut.print_verbose(" - type        : " + str(object_desc["type"]))
        ut.print_verbose(" - example     : " + str(object_desc["example"]))
        ut.print_verbose(" - " + str(object_desc))

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
            ut.print_verbose(" #> [" + str(object_desc["properties"][property]) + "]")
            ut.print_verbose(json.dumps(object_desc["properties"][property], indent=3))
            property_desc = object_desc["properties"][property]
            ut.print_verbose(" #>> " + str(property_desc))
            prop_schema = {}
            if ("$ref" in property_desc):
                # Sub-object
                ut.print_verbose("   #>> object        : " + str(property_desc["$ref"]))
                item = re.sub("#/components/schemas/" , "" , str(property_desc["$ref"]))
                prop_schema["$ref"]  = "" + item + "_schema.json"
                prop_schema["$ref"]  = "#/$defs/" + item + ""
                json_schema["properties"][item] = prop_schema
            elif ("items" in property_desc):
                # Array of Sub-objects
                ut.print_verbose("   #>> Array objects : " + str(property_desc["items"]["$ref"]))
                item = re.sub("#/components/schemas/", "", str(property_desc["items"]["$ref"]))
                prop_schema["type"] = "array"
                prop_schema["items"] = {"$ref" : "" + item + "_schema.json"}
                prop_schema["items"] = {"$ref" : "#/$defs/" + item + ""}
                json_schema["properties"][item+"s"] = prop_schema
            else:
                desc = property_desc["description"]
                found = ut.find_between(desc, "<schema>", "</schema>")
                desc_schema = {}
                if (found):
                    desc = ut.remove_between(desc, "<schema>", "</schema>")
                    desc_schema = ut.decode_prop_schema(property, found, desc)

                json_object[property_desc["name"]] = property_desc["example"]
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

                ut.print_verbose("   #>> name        : " + str(property_desc["name"]))
                ut.print_verbose("   #>> description : " + str(property_desc["description"]))
                ut.print_verbose("   #>> type        : " + str(property_desc["type"]))
                ut.print_verbose("   #>> format      : " + str(property_desc["format"]))
                ut.print_verbose("   #>> example     : " + str(property_desc["example"]))
                ut.print_verbose("   #>> pattern     : " + str(property_desc["pattern"]))
                ut.print_verbose("   #>> format      : " + str(property_desc["format"]))
                ut.print_verbose("   #>> mandatory   : " + str(property_desc["mandatory"]))
                if (property_desc["mandatory"]):
                    json_schema["required"].append(property_desc["name"])
                json_schema["properties"][property_desc["name"]] = prop_schema
        ut.print_verbose("Sample Object: "+str(json_object))
        json_schema["examples"]    = [json_object]
        schemas[entity] = json_schema

        # Add $defs Sub-Objects Schemas
        for link in links:
            cardinality     = links[link]["Cardinality"]
            TableContenue   = links[link]["TableContenue"]
            TableContenante = links[link]["TableContenante"]
            Name            = links[link]["Name"]
            Descr           = links[link]["Description"]
            # TableContenante = find_table(links[link]["TableContenante"])
            if (entity == TableContenante) and ("Optional" not in str(cardinality)):
                json_schema["required"].append(TableContenue)
            if (entity == TableContenante) and (str(cardinality)  in ["1", "3"]):
                json_schema["required"].append(TableContenue)

        if (is_root) :
            ut.saveFileContent(json.dumps(json_object, indent=3), json_directory + os.sep + entity + ".json")
            ut.saveFileContent(json.dumps(json_schema, indent=3), json_directory + os.sep + entity + "_schema.json")

    # Add $defs Sub-Objects Schemas
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
            ut.saveFileContent(json.dumps(schemas[schema], indent=3), json_directory + os.sep + schema + "_schema.json")
    ut.print_yellow("< lets_do_json")


if __name__ == '__main__':
    the_data_model = default_data_model
    if (len(sys.argv) == 2):
        the_data_model = sys.argv[1]
    ut.print_blue("Reading : "+the_data_model+".dbs")
    dbschema = DbSchema()
    dbschema.read_dbschema(the_data_model)

    lets_do_openapi_yaml(the_data_model)
    lets_do_json_schema(the_data_model)
    ut.print_blue("Ready   : "+the_data_model+".yaml")
