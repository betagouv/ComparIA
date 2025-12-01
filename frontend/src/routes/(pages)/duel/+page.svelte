<script lang="ts">
  import { Accordion, AccordionGroup, Icon, Link } from '$components/dsfr'

  const publicCards = [
    {
      desc: 'Pour découvrir concrètement les coulisses de l’IA.',
      title: 'Collèges et Lycées',
      icon: 'school-line',
      variant: 'text-yellow'
    },
    {
      desc: 'Pour enrichir les discussions sur l’innovation et le développement durable.',
      title: 'Universités',
      icon: 'university',
      variant: 'text-red'
    },
    {
      desc: 'Pour débattre d’un sujet de société en s’appuyant sur un exemple vécu.',
      title: 'Associations, Médiation numérique',
      icon: 'association',
      variant: 'text-green'
    },
    {
      desc: 'Pour réfléchir à un usage plus responsable des outils numériques.',
      title: 'Entreprises',
      icon: 'building-4-line',
      variant: 'text-primary'
    }
  ]

  const workshopSteps = [
    {
      desc: 'Présentation rapide de l’IA générative et de la plateforme compar:IA pour que tout le monde parte du même point, même sans connaissance préalable.',
      duration: '(10min)',
      title: 'Introduction'
    },
    {
      desc: 'Les participants posent la même question à deux modèles d’IA anonymes : un « grand » et un « petit » modèle.',
      duration: '(10-15min)',
      title: 'Le duel'
    },
    {
      desc: 'Moment d’échange pour réfléchir à la pertinence des réponses au regard des besoins des utilisateurs.',
      duration: '(10min)',
      title: 'Comparaison et vote'
    },
    {
      desc: 'Choc pédagogique et découverte des caractéristiques techniques des modèles : « meilleure réponse » ne rime pas toujours avec « sobriété environnementale » !',
      duration: '(10min)',
      title: 'Révélation des modèles'
    },
    {
      desc: 'Temps collectif pour réfléchir aux arbitrages entre usage et impact environnemental.',
      duration: '(10-15min)',
      title: 'Débat final'
    },
    {
      desc: 'Partage de quelques gestes simples pour réduire l’impact lié à l’usage de l’IA.',
      duration: '(5min)',
      title: 'Conclusion et ouverture'
    }
  ]

  const faq = [
    {
      desc: 'Nous avons déjà animé des sessions avec seulement 5 participants, mais aussi devant 300 personnes. Bien sûr, plus le groupe est grand, moins chacun a l’occasion de s’exprimer individuellement. Cela dit, l’atelier reste très flexible : tout dépend de la capacité du facilitateur à gérer le public. Avec un petit groupe, l’expérience est plus personnalisée ; avec un grand nombre de participants, l’énergie et la dynamique sont particulièrement intéressantes.',
      title: "Combien de personnes peuvent participer à une session des Duels de l'IA ?"
    },
    {
      desc: 'Pas du tout ! Le guide facilitateur est conçu pour permettre à toute personne intéressée d’animer un duel. Il fournit les éléments clés pour comprendre le sujet, les enjeux et les outils nécessaires au bon déroulement de l’exercice. Bien sûr, avoir déjà expérimenté un peu avec des modèles de langage peut aider, mais ce n’est en aucun cas indispensable.',
      title: "Faut-il être expert du sujet pour faciliter un Duel de l'IA ?"
    },
    {
      desc: 'Les sessions les plus courtes que nous avons menées ont duré 20 à 30 minutes, mais cela limite un peu l’interactivité. Idéalement, un bon duel prend environ 45 minutes. Et si l’on dispose d’1h30, c’est encore mieux : cela permet d’enchaîner plusieurs duels et d’entrer plus en profondeur dans les discussions.',
      title: 'Combien de temps dure une session des Duels ?'
    }
  ]
</script>

<main>
  <section class="fr-container--fluid bg-very-light-grey py-15">
    <div class="fr-container">
      <div class="grid gap-10 md:grid-cols-2 lg:px-20">
        <div class="my-auto md:max-w-[415px]">
          <h1 class="fr-h2 mb-3!">
            Vous souhaitez <span class="text-primary">sensibiliser votre public</span> à l’impact environnemental
            de l’IA générative ?
          </h1>
          <p class="mb-7! md:text-lg">
            Organisez un <strong>Duel de l’IA</strong> dans votre établissement, association ou entreprise
            en devenant facilitateur
          </p>

          <Link
            button
            href="https://comparia.getgrist.com/forms/h2i36mSYhJsAyb5r4Bee5c/29"
            text="Recevoir le kit facilitateur"
            size="lg"
            class="w-full!"
          />
        </div>

        <div class="my-auto">
          <img src="/duel/workshop.jpg" class="fr-responsive-img rounded-xl shadow-md" />
        </div>
      </div>
    </div>
  </section>

  <section class="fr-container--fluid bg-light-grey py-15">
    <div class="fr-container">
      <div class="grid gap-10 md:grid-cols-2 lg:px-20">
        <h2 class="fr-h4 my-auto! leading-[1.875]! md:max-w-[460px]">
          Les <span class="text-primary">Duels de l’IA</span> : un format d’<span
            class="text-primary">atelier</span
          >
          ouvert à tout public, pour découvrir les coulisses des IA génératives et réfléchir à leur
          <span class="text-primary">impact environnemental</span>.
        </h2>

        <ul class="m-0! my-auto p-0! md:ms-auto!">
          {#each ['Durée : 45min à 1h30', 'Format présentiel ou en ligne', 'Accès à compar:IA et des supports fournis', 'Atelier clé en main, accessible et interactif'] as text}
            <li class="list-none p-0! not-last:mb-4 md:text-lg">
              <Icon icon="checkbox-line" class="text-primary" />
              {text}
            </li>
          {/each}
        </ul>
      </div>
    </div>
  </section>

  <section class="fr-container--fluid bg-very-light-grey py-15">
    <div class="fr-container">
      <div class="lg:px-10">
        <div class="mb-6 text-center">
          <h2 class="fr-h3 mb-3!">Pour quels publics ?</h2>
          <p class="text-grey mb-0!">
            Cet atelier est ouvert à tous, quel que soit le niveau de connaissance initial.
          </p>
        </div>

        <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {#each publicCards as card}
            <div class="cg-border bg-white p-4 md:px-7 md:py-6">
              <Icon icon={card.icon} class={card.variant} size="lg" block />
              <h3 class="my-3! text-lg! md:mt-5!">{card.title}</h3>
              <p class="text-grey text-sm!">{card.desc}</p>
            </div>
          {/each}
        </div>
      </div>
    </div>
  </section>

  <section class="fr-container--fluid bg-light-grey py-13">
    <div class="fr-container">
      <div class="lg:px-10">
        <div class="mb-11 text-center">
          <h2 class="fr-h3 text-primary! mb-3!">Déroulé type d’un atelier</h2>
          <p class="text-grey mb-0!">Durée approximative : 60 minutes</p>
        </div>

        <div class="grid gap-x-15 gap-y-10 md:grid-cols-2 md:gap-y-20 lg:grid-cols-3">
          {#each workshopSteps as step, i}
            <div class="flex items-start gap-2">
              <div class="mt-1 flex items-end gap-1">
                <div class="bg-primary h-[11px] w-[11px] rounded-full"></div>
                <span class="text-primary text-[40px] font-bold">{i + 1}</span>
              </div>
              <div>
                <h3 class="fr-h6 mb-1!">{step.title}</h3>
                <p class="mb-0!"><em>{step.duration}</em></p>
                <p class="text-grey mb-0! leading-[1.7]!">{step.desc}</p>
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  </section>

  <section class="fr-container--fluid bg-very-light-grey py-18">
    <div class="fr-container">
      <div class="grid gap-10 md:grid-cols-2 lg:px-12">
        <div class="my-auto md:max-w-[440px]">
          <h2 class="mb-6!">Le guide facilitateur</h2>

          <ul class="m-0! mb-13! p-0!">
            {#each ['Guide détaillé avec tout le déroulé expliqué', 'Diapositives prêtes à projeter', 'FAQ et glossaire pour répondre facilement aux questions', 'Exension Chrome pour avoir toutes ces informations à portée de main'] as text}
              <li class="list-none p-0! not-last:mb-3 md:text-lg">
                <Icon icon="checkbox-line" class="text-primary" />
                {text}
              </li>
            {/each}
          </ul>

          <Link
            button
            href="https://comparia.getgrist.com/forms/h2i36mSYhJsAyb5r4Bee5c/29"
            text="Recevoir le kit facilitateur"
            size="lg"
          />
        </div>

        <div class="my-auto">
          <img src="/duel/extension.png" class="fr-responsive-img rounded-xl shadow-md" />
        </div>
      </div>
    </div>
  </section>

  <section class="fr-container--fluid bg-white py-15">
    <div class="fr-container">
      <div class="lg:px-24">
        <h2 class="fr-h3 mb-8! text-center lg:mb-10!">Foire aux questions</h2>

        <AccordionGroup>
          {#each faq as q, i}
            <Accordion id={`faq-${i}`} label={q.title}>
              {q.desc}
            </Accordion>
          {/each}
        </AccordionGroup>

        <div class="mt-8 text-center lg:mt-11">
          <Link
            button
            size="lg"
            href="mailto:simonas.zilinskas@beta.gouv.fr"
            text="Nous contacter pour en savoir plus"
          />
        </div>
      </div>
    </div>
  </section>
</main>
