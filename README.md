
# SQL Architect to OpenAPI 

This tool converts an SQL Architect project into an OpenAPI 3.0.2 Data Model & CRUD Operations 

[Download SQL Architect](http://www.bestofbi.com/page/architect)

## Create your Data Model :

See below how to Model with SQL Architect for OpenAPI:

![img.png](img.png)

## Generate your API: 

    python.exe .\sql_architect_to_openapi.py .\API_Data_Model_Sample

## View your API: 

[View your APIs once generated in Swagger Editor : ](https://editor.swagger.io/)

![img_1.png](img_1.png)

[View your APIs once generated in Apicur Studio](https://studio.apicur.io/)

![img_2.png](img_2.png)

## Next Steps:

Use OpenAPI Code Generation Tools like Swagger Editor or PostMan to generate server stubs or client SDK.

## How to Model for OpenAPI:

The content of the Data Model in SQL Architect will be used as follow:



    Table:
        Logical Name  = API Object Type
        Physical Name = Examples    
        Remarks       = Description 
        Primary Key   = Not Used (complex)  
        Ignore : if the Physical name contain "ignore", the object will not be generated

        Attribute:
            Logical Name  = API Property Name
            Physical Name = Examples
            Remarks       = Description
            Allow Nulls   = Required / Optional if Ticked
            Type          = String, Integer, Time, Boolean
            Default Value = Pattern 

        Relation:
            Name        = If name contains ignore or color is grey, the relation will nor refer to sub-object attribute
            Description = PK Label + FK Label
            Cardinalite = <NOT IMPLEMENTED>

        Special Attributes
            Name          = _PATH (Generates a CRUD list of operations for this object)
                            _PATH Physical Name : Used as PATH Name
                            _PATH Default value : Used as Path Name Prefix
                            _PATH Remarks : if contains read-only => only get - otherwise get / put / post / delete

    The "OpenAPI" object is used to define the API additional detail in attributes:
        "title"           : Physical Name used as API Title
        "description"     : Physical Name + Remarks used as API Description
        "version"         : Physical Name used as API Version
        "contacts"        : Remarks in JSON Format used as API Contacts
        "license"         : Remarks in JSON Format used as API License
        "tags"            : Remarks in JSON Format used as API tags
        "servers"         : Remarks in JSON Format used as API Servers
        "security"        : Remarks in JSON Format used as API Security
        "securitySchemes" : Remarks in JSON Format used as API SecuritySchemes
