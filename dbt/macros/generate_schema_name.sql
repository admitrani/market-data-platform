{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if target.name == "ci" -%}
        {{ target.schema }}
    {%- elif custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
