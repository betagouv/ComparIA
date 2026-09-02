<div align="center">
<img src="docs/assets/logo-comparia-symbole.svg" alt="compar:IA logo" width="120">

# compar:IA

### An open-source LLM arena for your organisation, sector, or language.

Collect human votes, compare models through real use, and publish open datasets for any language or sector.

<br>

[![License](https://img.shields.io/github/license/betagouv/ComparIA?color=blue)](./LICENSE)
[![Hugging Face datasets](https://img.shields.io/badge/Hugging%20Face-datasets-yellow?logo=huggingface&logoColor=white)](https://huggingface.co/ministere-culture)
[![Paper](https://img.shields.io/badge/arXiv-2602.06669-b31b1b?logo=arxiv&logoColor=white)](https://arxiv.org/abs/2602.06669)
[![DPG Badge](https://img.shields.io/badge/Verified-DPG-3333AB?logo=data:image/svg%2bxml;base64,PHN2ZyB3aWR0aD0iMzEiIGhlaWdodD0iMzMiIHZpZXdCb3g9IjAgMCAzMSAzMyIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTE0LjIwMDggMjEuMzY3OEwxMC4xNzM2IDE4LjAxMjRMMTEuNTIxOSAxNi40MDAzTDEzLjk5MjggMTguNDU5TDE5LjYyNjkgMTIuMjExMUwyMS4xOTA5IDEzLjYxNkwxNC4yMDA4IDIxLjM2NzhaTTI0LjYyNDEgOS4zNTEyN0wyNC44MDcxIDMuMDcyOTdMMTguODgxIDUuMTg2NjJMMTUuMzMxNCAtMi4zMzA4MmUtMDVMMTEuNzgyMSA1LjE4NjYyTDUuODU2MDEgMy4wNzI5N0w2LjAzOTA2IDkuMzUxMjdMMCAxMS4xMTc3TDMuODQ1MjEgMTYuMDg5NUwwIDIxLjA2MTJMNi4wMzkwNiAyMi44Mjc3TDUuODU2MDEgMjkuMTA2TDExLjc4MjEgMjYuOTkyM0wxNS4zMzE0IDMyLjE3OUwxOC44ODEgMjYuOTkyM0wyNC44MDcxIDI5LjEwNkwyNC42MjQxIDIyLjgyNzdMMzAuNjYzMSAyMS4wNjEyTDI2LjgxNzYgMTYuMDg5NUwzMC42NjMxIDExLjExNzdMMjQuNjI0MSA5LjM1MTI3WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cg==)](https://www.digitalpublicgoods.net/r/comparia)

**[Try the arena](https://comparia.beta.gouv.fr)** · **[Leaderboard](https://comparia.beta.gouv.fr/ranking)** · **[Walkthrough](#walkthrough-video)** · **[Datasets](https://huggingface.co/ministere-culture)** · **[Deploy your own](#deploy-your-own)** · **[Roadmap](#roadmap)** · **[Contribute](#contribute)**

</div>

---

## What is compar:IA?

compar:IA is an LLM arena. Enter a prompt and two anonymous models respond. Vote for the answer you prefer or skip the vote; the model names are revealed only afterwards. The French public arena is free and does not require an account.

The [model catalogue](https://comparia.beta.gouv.fr/modeles) lists each model's origin and technical characteristics. Where enough technical data is available, compar:IA also shows an EcoLogits estimate of its energy use.

<div align="center">
  <img width="7164" height="2269" alt="Frame 15928" src="https://github.com/user-attachments/assets/629853f5-fbc3-461a-8357-1f5073d58aa0" />
</div>

## Walkthrough video

https://github.com/user-attachments/assets/cf23a010-0ce8-4c96-a603-b087bef3271b

## What can you use it for?

- Raise awareness about differences between models, including bias, openness, and energy consumption.
- Rank models through real-world use rather than laboratory benchmarks, for a specific use case and language.
- Publish open datasets of prompts, votes, and reactions for research, training, and fine-tuning.

## Leaderboard and open data

The [public leaderboard](https://comparia.beta.gouv.fr/ranking) converts blind votes into Bradley-Terry scores with 95% confidence intervals. It measures the preferences collected in the arena, not objective model quality. The [methodology](https://huggingface.co/blog/comparIA/publication-du-premier-classement), calculations, and source data are public.

The [`comparia-fr-arena` dataset](https://huggingface.co/datasets/ministere-culture/comparia-fr-arena) is published under the Etalab Open Licence 2.0 and CC BY 4.0.

## Project history

- **Oct 2024:** The French government launched [comparia.beta.gouv.fr](https://comparia.beta.gouv.fr), a public LLM arena.
- **Mar 2025:** The arena reached 50,000 votes, and the first dataset was published on Hugging Face.
- **Nov 2025:** The first public leaderboard was released, and compar:IA was [recognized as a Digital Public Good](https://www.digitalpublicgoods.net/r/comparia). A second instance, Denmark's [AI-arenaen](https://ai-arenaen.dk), also went live.
- **Jun 2026:** The project passed 700,000 conversations and 250,000 votes ([about 89% in French](https://arxiv.org/abs/2602.06669)), with more than 130 models tested and several datasets published.
- **Sept 2026:** compar:IA 2.0 was released with message history, personal leaderboards, and an admin panel. Companies, sectors, and language communities can now deploy their own instance.

## Active instances

| Instance | Region | Live | Datasets |
| --- | :---: | --- | --- |
| **compar:IA**, French Government | 🇫🇷 | [comparia.beta.gouv.fr](https://comparia.beta.gouv.fr) | [Hugging Face](https://huggingface.co/datasets/ministere-culture/comparia-fr-arena), [data.gouv.fr](https://www.data.gouv.fr/datasets/compar-ia), [Mozilla](https://mozilladatacollective.com/datasets/cmklbq9qt006mnw077t9lqh89) |
| **AI-arenaen**, Denmark | 🇩🇰 | [ai-arenaen.dk](https://ai-arenaen.dk) | *Coming soon* |
| **Yours?** | 🌍 | [Deploy one](#deploy-your-own) | Your own |

## Deploy your own

Host compar:IA with your own models, language, datasets, and leaderboard.

**Self-host with Docker:** Run the platform on a single server with automatic HTTPS from Caddy. Follow the [self-hosting guide](./docs/self-hosting.md), then configure your models, languages and branding in the [admin panel](./docs/admin.md).

**Local development:**

```bash
cp .env.example .env   # configure your environment variables
make install           # install all dependencies
source .env

make dev-backend       # backend  -> http://localhost:8008
make dev-frontend      # frontend -> http://localhost:5173
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full setup: instances, Docker, the database, testing, and translations.

## Roadmap

**In progress**

- Agentic tool use
- OIDC SSO
- Improved style control

<details>
<summary><b>Done</b></summary>

- [Authentication](https://github.com/betagouv/ComparIA/milestone/11) *(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)*
- Style control, [#532](https://github.com/betagouv/ComparIA/pull/532) *(🇫🇷 Ministry of Culture)*
- Prompt moderation, [#542](https://github.com/betagouv/ComparIA/pull/542) *(🇫🇷 Ministry of Culture)*
- [Improved model cards](https://github.com/betagouv/ComparIA/milestone/14) *(🇫🇷 Ministry of Culture)*
- Live use-case mapping *(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)*
- Message history *(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)*
- Socio-demographic data collection *(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)*
- [Back-office management](https://github.com/betagouv/ComparIA/milestone/17) *(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)*
- New voting system *(🇪🇺 ALT-EDIC, 🇫🇷 Ministry of Culture)*
- Web search *(🇪🇺 ALT-EDIC)*
- Separation of all platforms into separate instances *(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)*
- Ranking consolidation and internationalization *(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)*
- Language / platform-specific model support *(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)*
- Gradio to FastAPI migration *(🇫🇷 Ministry of Culture, 🇫🇷 DINUM, 🇪🇺 ALT-EDIC)*
- [EcoLogits update](https://github.com/betagouv/ComparIA/pull/253) *(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)*
- Dataset publishing pipeline v1 *(🇫🇷 DINUM, 🇫🇷 Ministry of Culture)*
- Leaderboard v1 *(🇫🇷 DINUM, 🇫🇷 Ministry of Culture, with 🇫🇷 PEReN)*
- Archived models *(🇫🇷 DINUM, 🇫🇷 Ministry of Culture)*
- Blog section *(🇫🇷 DINUM, 🇫🇷 Ministry of Culture)*
- Internationalization foundations *(🇫🇷 DINUM, 🇫🇷 Ministry of Culture)*
- compar:IA v1 *(🇫🇷 DINUM, 🇫🇷 Ministry of Culture)*

</details>

## Contribute

compar:IA is a digital common. You can support it by running an instance, funding the work, contributing code or translations, or sharing research and ideas.

- **Run an instance:** Each deployment can produce an open dataset and benchmark for its language, sector, or organisation.
- **Fund the project:** compar:IA is funded by ALT-EDIC, DINUM, and the French Ministry of Culture. New partners and funders help cover infrastructure, add languages, and keep the project independent. Contact [contact@comparia.beta.gouv.fr](mailto:contact@comparia.beta.gouv.fr).
- **Contribute code or translations:** Bug fixes, features, translations, and documentation can be submitted through a [pull request](https://github.com/betagouv/ComparIA/pulls).
- **Share ideas or report issues:** Start or join a thread in [GitHub Discussions](https://github.com/betagouv/ComparIA/discussions).
- **Research and partnerships:** For academic work, media enquiries, partnerships, or other forms of support, [get in touch](mailto:contact@comparia.beta.gouv.fr).

## Built by

**DINUM**, the **French Ministry of Culture**, and **ALT-EDIC** 🇪🇺, with **AI-arenaen** (Denmark), **PIX**, **PEReN**, and other contributors.

---

<div align="center">

Read the paper: **[compar:IA: The French Government's LLM arena](https://arxiv.org/abs/2602.06669)**

</div>
