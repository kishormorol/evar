Original path: pydantic/json_schema.py
Snapshot commit: 22b6bcecdd2be748ff2567e4e83a853be84554e2
Original lines: 1555-1665

            json_schema['additionalProperties'] = False
        elif schema.get('extra_behavior') == 'allow':
            json_schema['additionalProperties'] = allow_additional_props

        if cls is not None:
            # `_update_class_schema()` will not override
            # `additionalProperties` if already present:
            self._update_class_schema(json_schema, cls, config)
        elif 'additionalProperties' not in json_schema:
            extra = schema.get('config', {}).get('extra_fields_behavior')
            if extra == 'forbid':
                json_schema['additionalProperties'] = False
            elif extra == 'allow':
                json_schema['additionalProperties'] = allow_additional_props

        return json_schema

    @staticmethod
    def _name_required_computed_fields(
        computed_fields: list[ComputedField],
    ) -> list[tuple[str, bool, core_schema.ComputedField]]:
        return [
            (field['property_name'], field.get('serialization_exclude_if') is None, field) for field in computed_fields
        ]

    def _named_required_fields_schema(
        self, named_required_fields: Sequence[tuple[str, bool, CoreSchemaField]]
    ) -> JsonSchemaValue:
        properties: dict[str, JsonSchemaValue] = {}
        required_fields: list[str] = []
        for name, required, field in named_required_fields:
            if self.by_alias:
                name = self._get_alias_name(field, name)
            try:
                field_json_schema = self.generate_inner(field).copy()
            except PydanticOmit:
                continue
            if 'title' not in field_json_schema and self.field_title_should_be_set(field):
                title = self.get_title_from_name(name)
                field_json_schema['title'] = title
            field_json_schema = self.handle_ref_overrides(field_json_schema)
            properties[name] = field_json_schema
            if required:
                required_fields.append(name)

        json_schema = {'type': 'object', 'properties': properties}
        if required_fields:
            json_schema['required'] = required_fields
        return json_schema

    def _get_alias_name(self, field: CoreSchemaField, name: str) -> str:
        if field['type'] == 'computed-field':
            alias: Any = field.get('alias', name)
        elif self.mode == 'validation':
            alias = name if not self._config.validate_by_alias else field.get('validation_alias', name)
        else:
            alias = field.get('serialization_alias', name)
        if isinstance(alias, str):
            name = alias
        elif isinstance(alias, list):
            alias = cast('list[str] | str', alias)
            for path in alias:
                if isinstance(path, list) and len(path) == 1 and isinstance(path[0], str):
                    # Use the first valid single-item string path; the code that constructs the alias array
                    # should ensure the first such item is what belongs in the JSON schema
                    name = path[0]
                    break
        else:
            assert_never(alias)
        return name

    def typed_dict_field_schema(self, schema: core_schema.TypedDictField) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a typed dict field.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self.generate_inner(schema['schema'])

    def dataclass_field_schema(self, schema: core_schema.DataclassField) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a dataclass field.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self.generate_inner(schema['schema'])

    def model_field_schema(self, schema: core_schema.ModelField) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a model field.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self.generate_inner(schema['schema'])

    def computed_field_schema(self, schema: core_schema.ComputedField) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a computed field.

        Args:
            schema: The core schema.

        Returns:
