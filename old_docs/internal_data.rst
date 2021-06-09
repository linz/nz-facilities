.. _internal_data:


Internal Data
================================

The information below describes the data model for building outlines for internal LINZ purposes.

Data Model
--------------------------------

To assist you in understanding these datasets, the structure and details of the data fields is described in tables below. The relationship between tables and directly related datasets is provided in a data model diagram. No attempt has been made to indicate cardinality, however, the arrows drawn between datasets point from the dataset containing the unique record, to the dataset that may contain one or more references to that record (i.e. primary key -> foreign key). 

Primary keys in tables are shown by a field name with bold font.

This data model has been designed to manage building data with multiple representations, allowing for future enhancements in building data management. Not all of this data is currently available and data capture for these new fields will occur over time.

.. figure:: _static/nz-buildings-pgtap-db.png
   :width: 100%
   :alt: buildings database diagram


Schema: {{ schema_gen_buildings["name"] }}
----------------------------------------------------

Description: {{ schema_gen_buildings["comment"] }}


{% for item in schema_tab_buildings  %}
.. _table-name-{{item.table_nam}}:

Table: {{ item.table_nam }}
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
	
Description: {{ item.table_comment }}

		{% for table in item.table_columns %}{%  for column in table %}{{ column }}{% endfor %}
		{% endfor %}
	      
		

{% endfor %}



Schema: {{ schema_gen_buildings_common["name"] }}
-------------------------------------------------------

Description: {{ schema_gen_buildings_common["comment"] }}


{% for item in schema_tab_buildings_common  %}
.. _table-name-{{item.table_nam}}:

Table: {{ item.table_nam }}
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Description: {{ item.table_comment }}

		{% for table in item.table_columns %}{%  for column in table %}{{ column }}{% endfor %}
		{% endfor %}
	      
		

{% endfor %}


Schema: {{ schema_gen_buildings_bulk_load["name"] }}
-------------------------------------------------------

Description: {{ schema_gen_buildings_bulk_load["comment"] }}


{% for item in schema_tab_buildings_bulk_load  %}
.. _table-name-{{item.table_nam}}:

Table: {{ item.table_nam }}
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
	
Description: {{ item.table_comment }}

		{% for table in item.table_columns %}{%  for column in table %}{{ column }}{% endfor %}
		{% endfor %}
	      
		

{% endfor %}


Schema: {{ schema_gen_buildings_reference["name"] }}
-------------------------------------------------------

Description: {{ schema_gen_buildings_reference["comment"] }}


{% for item in schema_tab_buildings_reference  %}
.. _table-name-{{item.table_nam}}:

Table: {{ item.table_nam }}
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
	
Description: {{ item.table_comment }}

		{% for table in item.table_columns %}{%  for column in table %}{{ column }}{% endfor %}
		{% endfor %}
	      
		

{% endfor %}
