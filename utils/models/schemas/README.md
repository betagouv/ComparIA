# LLM data specifications

We use some JSON files to specify organisations, LLMs, licenses and architectures information.
All of those are then used to build differents files needed by the backend and frontends with `utils/models/build_models.py`.

To help you add new data, all the data specifications files are linked to a JSON Schema with vscode.

## Data generation

To generate all needed files:

```bash
make models-build
```

To clean data specifications (reorder properties, remove defaults):

```bash
make models-maintenance
```

To generate this doc and JSON schemas in `utils/models/schemas`:

```bash
make models-doc
```

## Data specifications

### Organisations and LLMs

File: ['utils/models/models.json'](./models.json)

#### Organisation

Properties:
{orga_attrs}

<details>
<summary>Raw individual organisation definition to fill:</summary>

```json
{orga}
```

</details>

#### LLM

LLM definitions are specified in the `"models"`'s organisation property.

Properties:
{llm_attrs}

<details>
<summary>Raw individual LLM definition to fill:</summary>

```json
{llm}
```

</details>

### Licenses

File: ['utils/models/licenses.json'](./licenses.json)

Properties:
{license_attrs}

<details>
<summary>Raw individual license definition to fill:</summary>

```json
{license}
```

</details>

### Architectures

File: ['utils/models/archs.json'](./archs.json)

Properties:
{arch_attrs}

<details>
<summary>Raw individual architecture definition to fill:</summary>

```json
{arch}
```

</details>
