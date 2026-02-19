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
- `name`: str  *Organisation's name*  
- `icon_path`: str (optional) *An icon name from https://lobehub.com/fr/icons or a filename (e.g. 'ai2.svg') from `frontend/static/orgs/ai/`*  
- `proprietary_license_desc`: str (optional) *Description of the optional organisation's proprietary license*  
- `proprietary_reuse`: bool  *Whether LLMs can be reused/redistributed according to this proprietary license*  
- `proprietary_commercial_use`: bool (optional) *Whether commercial use is permitted with this proprietary license*  
- `proprietary_reuse_specificities`: str (optional) *Additional reuse restrictions/notes*  
- `proprietary_commercial_use_specificities`: str (optional) *Additional commercial use restrictions/notes*  
- `models`: list (optional) *list of this organisation's LLMs*

<details>
<summary>Raw individual organisation definition to fill:</summary>

```json
{
  "name": "",
  "icon_path": "",
  "proprietary_license_desc": "",
  "proprietary_reuse": false,
  "proprietary_commercial_use": null,
  "proprietary_reuse_specificities": "",
  "proprietary_commercial_use_specificities": "",
  "models": []
}
```

</details>

#### LLM

LLM definitions are specified in the `"models"`'s organisation property.

Properties:
- `new`: bool  *Whether this is a newly added LLM*  
- `status`: `'archived'` | `'missing_data'` | `'disabled'` | `'enabled'` (optional) *This LLM data status*  
- `id`: str  *Unique LLM identifier (you can choose it or use HF one)*  
- `simple_name`: str  *Human-readable LLM name*  
- `license`: str  *License identifier (maps to `licenses.json` ids)*  
- `fully_open_source`: bool  *Whether LLM weights are fully open/public*  
- `release_date`: str  *LLM release date in MM/YYYY format*  
- `arch`: str  *LLM architecture (maps to `archs.json` ids). Use `maybe-*` if information is not confirmed*  
- `params`: int | float  *Total parameters in billions*  
- `active_params`: int | float (optional) *Active parameters in billions (only for MoE LLMs)*  
- `reasoning`: bool | `'hybrid'` (optional) *Extended thinking capability*  
- `quantization`: `'q4'` | `'q8'` (optional) *Quantization scheme applied (q4, q8, or None for full precision)*  
- `url`: str (optional) *LLM homepage or documentation URL*  
- `endpoint`: Endpoint (optional) *API access configuration (None for unavailable LLMs)*  
- `pricey`: bool  *Whether LLM has high API costs (triggers stricter rate limits)*  
- `specific_portals`: list (optional) *Custom allow list of country portals on which the LLM is available*  
- `desc`: str  *Detailed LLM description*  
- `size_desc`: str  *Detailed description of LLM size*  
- `fyi`: str  *Additional notes for users*

<details>
<summary>Raw individual LLM definition to fill:</summary>

```json
{
  "new": true,
  "status": "enabled",
  "id": "",
  "simple_name": "",
  "license": "",
  "fully_open_source": false,
  "release_date": "MM/YYYY",
  "arch": "",
  "params": null,
  "active_params": null,
  "reasoning": false,
  "quantization": null,
  "url": null,
  "endpoint": {
    "api_type": "openai",
    "api_base": null,
    "api_version": null,
    "vertex_ai_location": null
  },
  "pricey": false,
  "specific_portals": null,
  "desc": "",
  "size_desc": "",
  "fyi": ""
}
```

</details>

### Licenses

File: ['utils/models/licenses.json'](./licenses.json)

Properties:
- `license`: str  *Human-readable License name (e.g. 'Apache 2.0' or 'MIT')*  
- `license_desc`: str  *Description of the license*  
- `distribution`: `'api-only'` | `'open-weights'` | `'fully-open-source'` (optional) *How the LLM is distributed*  
- `reuse`: bool  *Whether the LLM can be reused/redistributed*  
- `commercial_use`: bool (optional) *Whether commercial use is permitted (None = unknown)*  
- `reuse_specificities`: str (optional) *Additional reuse restrictions/notes*  
- `commercial_use_specificities`: str (optional) *Additional commercial use restrictions/notes*

<details>
<summary>Raw individual license definition to fill:</summary>

```json
{
  "license": "",
  "license_desc": "",
  "distribution": "api-only|open-weights|fully-open-source",
  "reuse": false,
  "commercial_use": null,
  "reuse_specificities": "",
  "commercial_use_specificities": ""
}
```

</details>

### Architectures

File: ['utils/models/archs.json'](./archs.json)

Properties:
- `id`: str  *Architecture identifier (e.g. 'dense', 'moe')*  
- `name`: str  *Human-readable architecture name*  
- `title`: str  *Human-readable architecture complete title ('Architecture {name}')*  
- `desc`: str  *Detailed description of the architecture*

<details>
<summary>Raw individual architecture definition to fill:</summary>

```json
{
  "id": "",
  "name": "",
  "title": "",
  "desc": ""
}
```

</details>
