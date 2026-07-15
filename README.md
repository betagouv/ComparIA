<h1 align="center">Open Source LLM Arena</h1>

<p align="center">
  <strong>Collect human preference datasets for less-resourced languages and specific sectors,<br>
  while raising awareness about model diversity, bias, and environmental impact.</strong><br><br>
  <em>Built by the French government, now growing into new languages and sectors.</em>
</p>

<p align="center">
  <a href="https://comparia.beta.gouv.fr/">🇫🇷 French platform</a>&nbsp;&nbsp;·&nbsp;&nbsp;
  <a href="https://ai-arenaen.dk/">🇩🇰 Danish platform</a>
</p>

<p align="center">
  <img src="https://github.com/simonaszilinskas/fourre-tout/blob/main/Frame%2014254.png?raw=true" alt="Supported by DINUM, Ministry of Culture, ALT-EDIC, Denmark, and recognised as a Digital Public Good" />
</p>

---

## How does it work?

<div align="center">
  <a href="https://comparia.beta.gouv.fr/"
     aria-label="Click to visit the hosted platform"
     title="Demo video of the comparator">
    <video
      src="https://github.com/user-attachments/assets/06ce8c3d-aec1-48d6-ab64-a75a08020796"
      width="800"
      autoplay
      loop
      muted
      playsinline
    />
  </a>
</div>

---

## 🇫🇷 The French use case

<table>
<tr>
<td width="55%" valign="top">

Launched in October 2024 by [DINUM](https://www.numerique.gouv.fr/dinum/) and the French [Ministry of Culture](https://www.culture.gouv.fr/) to address the lack of French-language preference data for LLM training nd evaluation.

Since launch: **700,000+ prompts**, **250,000+ preference votes**, 450,000+ visitors. One of the largest non-English human preference datasets available. All data published openly on Hugging Face:[comparIA/comparia-fr-arena](https://huggingface.co/datasets/comparIA/comparia-fr-arena)

We published a [pre-print](https://huggingface.co/papers/2602.06669) to dive deep into the project's strategy in France.

</td>
<td width="45%" valign="top">

<img src="https://comparia.beta.gouv.fr/news/jt-france2.jpeg" alt="Compar:IA featured on France 2 news, being used in a classroom" width="100%" />

<sub><em>Compar:IA on the France 2 evening news, used in the classroom to teach students about AI models, bias, and environmental impact.</em></sub>

</td>
</tr>
</table>

---

## For whom?

<table>
<tr>
<td width="33%" valign="top">

### 🌍 Languages

Most LLMs underperform outside English. Compar:IA collects the preference data needed to close this gap.

Already live in **French and Danish**, and planning launches in Sweden, Estonia and Lithuania.

</td>
<td width="33%" valign="top">

### 🏛️ Sectors

Generic benchmarks miss domain-specific needs. A sector arena reveals which models handle specialised language best.

_Healthcare, legal, education, public admin, agriculture..._

</td>
<td width="33%" valign="top">

### 🏢 Organisations

Run your own arena, evaluate models on your real-world tasks, and contribute data back to the commons.

_Governments, universities, hospitals, companies, NGOs..._

</td>
</tr>
</table>

---

## Benefits

<table>
<tr>
<td width="33%" align="center">

### 💡 Raise awareness

Teach citizens and professionals about model diversity, bias, and environmental cost. Already used in schools and training sessions.

<img src="https://comparia.beta.gouv.fr/news/duel.jpg" alt="Blind comparison between two models" width="100%" />

</td>
<td width="33%" align="center">

### 📊 Generate rare datasets

Produce instruction and preference data in less-ressourced languages.

<img src="https://comparia.beta.gouv.fr/datasets/bunka-analyse.png" alt="Dataset analysis visualization" width="100%" />

</td>
<td width="33%" align="center">

### 🔁 Downstream reuse

Data feeds into new model training, leaderboards, use case mappings, and other research topics.

<img src="https://comparia.beta.gouv.fr/news/analyse-bunka.png" alt="Downstream data analysis" width="100%" />

</td>
</tr>
</table>

---

## Interested in an arena for your language, sector, or organisation?

The platform is fully open source, self-hostable, and customizable: choose your models, translate the interface, adapt prompt suggestions, add your logo. We can host it for you or help you set it up yourself.

Whatever your situation, **reach out first** and we'll figure out the best path together.

📬 **[contact@comparia.beta.gouv.fr](mailto:contact@comparia.beta.gouv.fr)**

---

## Contribute, we need you 🤝

Compar:IA is a digital common. Whether you can offer funding, code, translations, or simply ideas, there is a place for you.

**💰 Financially.** Compar:IA has been funded by DINUM and the French Ministry of Culture, with European support from ALT-EDIC. We are actively looking for new partners and funders to sustain the infrastructure, expand to new languages, and keep the project independent. **[contact@comparia.beta.gouv.fr](mailto:contact@comparia.beta.gouv.fr)**

**💻 In code.** The entire platform is open source and we welcome contributions of all sizes: bug fixes, new features, translations, documentation. Come build with us. **[GitHub repository](https://github.com/betagouv/ComparIA)**

**💬 In discussions.** Share your ideas, flag issues, or just ask questions on GitHub Discussions. We want to hear from you. **[GitHub Discussions](https://github.com/betagouv/ComparIA/discussions)**

**Any other way.** Partnerships, academic collaborations, media coverage, spreading the word: every contribution matters. Reach out and let's talk. **[Contact us](mailto:contact@comparia.beta.gouv.fr)**

---

## Roadmap

### 🟢 In Progress
- [Authentication](https://github.com/betagouv/ComparIA/milestone/11)  _(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)_
- Style control https://github.com/betagouv/ComparIA/pull/532 _(🇫🇷 Ministry of Culture)_
- Prompt moderation https://github.com/betagouv/ComparIA/pull/542 _(🇫🇷 Ministry of Culture)_
- [Improved model cards](https://github.com/betagouv/ComparIA/milestone/14) _(🇫🇷 Ministry of Culture)_

### 🔮 Up Next

- Live use-case mapping _(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)_
- Message history _(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)_
- Socio-demographic data collection _(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)_
- [Back-office management](https://github.com/betagouv/ComparIA/milestone/17)  _(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)_

### ⛵ Shipped
- New voting system _(🇪🇺 ALT-EDIC, 🇫🇷 Ministry of Culture)_
- Web search _(🇪🇺 ALT-EDIC)_
- Separation of all platforms into separate instances _(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)_
- Ranking consolidation and internationalization _(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)_
- Language/platform-specific model support _(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)_
- Gradio → FastAPI migration _(🇫🇷 Ministry of Culture, 🇫🇷 DINUM, 🇪🇺 ALT-EDIC)_
- [EcoLogits update](https://github.com/betagouv/ComparIA/pull/253) _(🇪🇺 ALT-EDIC, 🇫🇷 DINUM)_
- Dataset publishing pipeline v1 _(🇫🇷 DINUM, 🇫🇷 Ministry of Culture)_
- Leaderboard v1 _(🇫🇷 DINUM, 🇫🇷 Ministry of Culture, in collaboration with 🇫🇷 PEReN)_
- Archived models _(🇫🇷 DINUM, 🇫🇷 Ministry of Culture)_
- Blog section _(🇫🇷 DINUM, 🇫🇷 Ministry of Culture)_
- Internationalization foundations _(🇫🇷 DINUM, 🇫🇷 Ministry of Culture)_
- compar:IA v1 _(🇫🇷 DINUM, 🇫🇷 Ministry of Culture)_

---

👉 **[Full technical roadmap on GitHub](https://github.com/orgs/betagouv/projects/160)**

---

## Getting started

The platform is fully open source and self-hostable.

**Self-host with Docker** (single server, automatic HTTPS via Caddy): see **[DOCKER_INSTALL.md](devops/standalone_docker_install/DOCKER_INSTALL.md)**

**Local development (basic):**

```bash
cp .env.example .env       # Configure environment variables
make install               # Install all dependencies
source .env
make dev-backend           # Backend on http://localhost:8008
make dev-frontend          # Frontend on http://localhost:5173
```

For the full setup guide (instances, KeePass, Docker, testing, models, i18n, architecture), see **[CONTRIBUTING.md](CONTRIBUTING.md)**.

<a href="https://digitalpublicgoods.net/r/comparia" target="_blank" rel="noopener noreferrer"><img src="https://github.com/DPGAlliance/dpg-resources/blob/main/docs/assets/dpg-badge.png?raw=true" width="100" alt="Digital Public Goods Badge"></a>
