.. change::
    :tags: removed, commands

    Removed deprecated ``--head_only`` option to the ``alembic current``
    command

.. change::
    :tags: removed, operations

    Removed legacy parameter names from operations, these have been emitting
    warnings since version 0.8.  In the case that legacy version files have not
    yet been updated, these can be modified directly in order to maintain
    compatibility:

    * :meth:`.Operations.drop_constraint` - "type" (use "type_") and "name"
      (use "constraint_name")

    * :meth:`.Operations.create_primary_key` - "cols" (use "columns") and
      "name" (use "constraint_name")

    * :meth:`.Operations.create_unique_constraint` - "name" (use
      "constraint_name"), "source" (use "table_name") and "local_cols" (use
      "columns")

    * :meth:`.Operations.batch_create_unique_constraint` - "name" (use
      "constraint_name")

    * :meth:`.Operations.create_foreign_key` - "name" (use "constraint_name"),
      "source" (use "source_table"), "referent" (use "referent_table")

    * :meth:`.Operations.batch_create_foreign_key` - "name" (use
      "constraint_name"), "referent" (use "referent_table")

    * :meth:`.Operations.create_check_constraint` - "name" (use
      "constraint_name"), "source" (use "table_name")

    * :meth:`.Operations.batch_create_check_constraint` - "name" (use
      "constraint_name")

    * :meth:`.Operations.create_index` - "name" (use "index_name")

    * :meth:`.Operations.drop_index` - "name" (use "index_name"), "tablename"
      (use "table_name")

    * :meth:`.Operations.batch_drop_index` - "name" (use "index_name"),

    * :meth:`.Operations.create_table` - "name" (use "table_name")

    * :meth:`.Operations.drop_table` - "name" (use "table_name")

    * :meth:`.Operations.alter_column` - "name" (use "new_column_name")


