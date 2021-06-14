.. _published_data:


Published Data
================================

The data described below represents facilities data openly available on the LINZ Data Service (LDS):
https://data.linz.govt.nz/layer/105568

Schema: {{ schema_gen_facilities_lds["name"] }}
--------------------------------------------------------

Description: {{ schema_gen_facilities_lds["comment"] }}


{% for item in schema_tab_facilities_lds  %}
.. _table-name-{{item.table_nam}}:

Table: {{ item.table_nam }}
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Description: {{ item.table_comment }}

		{% for table in item.table_columns %}{%  for column in table %}{{ column }}{% endfor %}
		{% endfor %}



{% endfor %}
