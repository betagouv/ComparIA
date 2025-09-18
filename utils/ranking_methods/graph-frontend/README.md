# SPDX-FileCopyrightText: 2023 Lena Jaskov <<https://observablehq.com/@yaslena>
# SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
# SPDX-License-Identifier: MIT

# Note importante
Ce code a été modifié pour le projet ComparIA, une licence MIT a été rajouté par l'autrice, voir: https://observablehq.com/@yaslena/dynamic-network-graph.

Note importante: il faut dans le dossier `files` inclure le fichier `/data/comparIA_graph.json` produit par le notebook `notebooks/graph.ipynb`. Un chemin direct peut être rajouté.  

# Dynamic Network Graph

View this notebook in your browser by running a web server in this folder. For
example:

~~~sh
npx http-server
~~~

Or, use the [Observable Runtime](https://github.com/observablehq/runtime) to
import this module directly into your application. To npm install:

~~~sh
npm install @observablehq/runtime@5
npm install https://api.observablehq.com/@yaslena/dynamic-network-graph@462.tgz?v=3
~~~

Then, import your notebook and the runtime as:

~~~js
import {Runtime, Inspector} from "@observablehq/runtime";
import define from "@yaslena/dynamic-network-graph";
~~~

To log the value of the cell named “foo”:

~~~js
const runtime = new Runtime();
const main = runtime.module(define);
main.value("foo").then(value => console.log(value));
~~~
