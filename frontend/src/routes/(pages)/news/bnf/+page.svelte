<script lang="ts">
  import { Badge, Icon, Link } from '$components/dsfr'
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'

  const talks = [
    {
      title: 'Ouverture de la journée',
      desc: 'Isabelle Nyffenegger, Thibault Grouas et Lucie Termignon, du Ministère de la Culture',
      youtubeSrc: 'https://www.youtube.com/embed/wnKNu_eW7Cc'
    },
    {
      title: 'Alignement des modèles sur les usages francophones',
      desc: 'Anastasia Stasenko, de Pleias',
      youtubeSrc: 'https://www.youtube.com/embed/3ayf__MTFzA'
    },
    {
      title: "Comment rendre l'IA compatible avec la démocratie ?",
      desc: 'David Mas de Make.org et Benjamin Piwowarski du CNRS.',
      youtubeSrc: 'https://www.youtube.com/embed/jdALqhnRmCk'
    },
    {
      title: "L'évaluation de l'impact environnemental des IA génératives",
      desc: 'Samuel Rincé, de GenAI Impact.',
      youtubeSrc: 'https://www.youtube.com/embed/i7IAJUzjk0c'
    },
    {
      title: "Enjeux d'éducation et de formation à l'IA générative",
      desc: 'Marie Bancal et Françoise Tort, de Pix.',
      youtubeSrc: 'https://www.youtube.com/embed/1oMLenKEhgk'
    },
    {
      title: "Vers un futur durable pour l'IA francophone",
      desc: 'Sasha Luccioni, de Hugging Face.',
      youtubeSrc: 'https://www.youtube.com/embed/kktVcBSkIIY'
    }
  ] as const

  const workshops = [
    {
      title: 'La bataille de l’IA',
      desc: 'Margaux Levisalles de Latitudes',
      time: '11h à 11h45'
    },
    {
      title: 'La boîte noire de l’IA',
      desc: 'Loup Cellard de Datactivist',
      time: '13h à 13h45'
    },
    {
      title: 'Les modules apprenants Modulix',
      desc: 'Romain Pennec de PIX',
      time: '14h à 14h45'
    },
    {
      title: '15h à 15h45',
      desc: "Atelier Café IA : dialogue constructif sur l'IA",
      time: 'Jean Cattan du Conseil national du numérique'
    },
    {
      title:
        'Retour sur la consultation citoyenne « Quelles sont vos idées pour mettre l’IA au service de l’intérêt général ? »',
      desc: 'Victor Laymand de Make.org',
      time: '15h45 à 16h30'
    }
  ] as const

  const speakers = [
    {
      name: 'Marie Bancal',
      desc: 'Directrice adjointe de Pix',
      img: '/news/bnf/marie-bancal.jpg',
      logos: [
        {
          src: '/orgs/pix.svg',
          invert: false,
          alt: 'Pix',
          width: 100
        }
      ]
    },
    {
      name: 'Mathilde Bras',
      desc: "Co-Responsable de l'Atelier numérique",
      img: '/news/bnf/mathilde-bras.jpg',
      logos: [
        { src: '/orgs/ateliernumerique.png', invert: true, alt: '', width: 100 },
        { src: '/orgs/minicult.svg', invert: false, alt: 'Ministère de la Culture', width: 110 }
      ]
    },
    {
      name: 'Margaux Levisalles',
      desc: 'Co-fondatrice de Latitudes',
      img: '/news/bnf/margaux-levisalles.jpg',
      logos: [
        {
          src: '/orgs/latitudes.png',
          invert: true,
          alt: 'Latitudes',
          width: 150
        }
      ]
    },
    {
      name: 'Jean Cattan',
      desc: 'Secrétaire général du Conseil national du numérique',
      img: '/news/bnf/jean-cattan.jpg',
      logos: [
        {
          src: '/orgs/cnnum.png',
          invert: true,
          alt: 'Conseil national du numérique',
          width: 100
        }
      ]
    },
    {
      name: 'Loup Cellard',
      desc: 'Chercheur chez Datactivist',
      img: '/news/bnf/loup-cellard.jpg',
      logos: [
        {
          src: '/orgs/datactivist.png',
          invert: true,
          alt: 'Datactivist',
          width: 150
        }
      ]
    },
    {
      name: 'Romain Delassus',
      desc: 'Chef du service du numérique du Ministère de la Culture',
      img: '/news/bnf/romain-delassus.jpg',
      logos: [
        {
          src: '/orgs/minicult.svg',
          invert: false,
          alt: 'Ministère de la Culture',
          width: 110
        }
      ]
    },
    {
      name: 'Victor Laymand',
      desc: 'Directeur des études chez make.org',
      img: '/news/bnf/victor-laymand.jpg',
      logos: [
        {
          src: '/orgs/make-org.svg',
          invert: false,
          alt: 'Make.org',
          width: 100
        }
      ]
    },
    {
      name: 'Sasha Luccioni',
      desc: 'AI & Climate Lead chez Hugging Face',
      img: '/news/bnf/sasha-luccioni.jpg',
      logos: [
        {
          src: '/orgs/huggingface-full.svg',
          invert: false,
          alt: 'Hugging Face',
          width: 160
        }
      ]
    },
    {
      name: 'David Mas',
      desc: 'Chief AI Officer chez Make.org',
      img: '/news/bnf/david-mas.jpg',
      logos: [
        {
          src: '/orgs/make-org.svg',
          invert: false,
          alt: 'Make.org',
          width: 100
        }
      ]
    },
    {
      name: 'Benjamin Piwowarski',
      desc: 'Directeur de recherche au CNRS',
      img: '/news/bnf/benjamin-piwowarski.jpg',
      logos: [
        {
          src: '/orgs/cnrs.svg',
          invert: false,
          alt: 'CNRS',
          width: 110
        }
      ]
    },
    {
      name: 'Samuel Rincé',
      desc: 'Président et cofondateur de GenAI Impact',
      img: '/news/bnf/samuel-rince.jpg',
      logos: [
        {
          src: '/orgs/genai.png',
          invert: true,
          alt: 'Gen AI',
          width: 130
        }
      ]
    },
    {
      name: 'Anastasia Stasenko',
      desc: 'Cofondatrice de Pleias',
      img: '/news/bnf/anastasia-stasenko.jpg',
      logos: [
        {
          src: '/orgs/pleias.png',
          invert: false,
          alt: 'Pleias',
          width: 130
        }
      ]
    },
    {
      name: 'Lucie Termignon',
      desc: 'Cheffe de produit de compar:IA',
      img: '/news/bnf/lucie-termignon.jpg',
      logos: [
        {
          src: '/orgs/comparia.svg',
          invert: false,
          alt: 'Comparia',
          width: 80
        },
        { src: '/orgs/minicult.svg', invert: false, alt: 'Ministère de la Culture', width: 110 }
      ]
    },
    {
      name: 'Françoise Tort',
      desc: 'Conceptrice de défis pédagogiques chez Pix',
      img: '/news/bnf/francoise-tort.jpg',
      logos: [
        {
          src: '/orgs/pix.svg',
          invert: false,
          alt: 'Pix',
          width: 100
        }
      ]
    }
  ] as const
</script>

<SeoHead title={m['seo.titles.news']()} />

<main>
  <section class="fr-container--fluid bg-very-light-grey pt-8 pb-16 md:pt-16">
    <div class="fr-container gap-16 md:grid-cols-2 grid items-center">
      <div class="mx-auto max-w-[470px]">
        <img
          class="mb-4"
          src="/iasummit.png"
          alt="Sommet pour l'action sur l'IA"
          title="Sommet pour l'action sur l'IA"
        />
        <h1>
          Journée compar:<span class="text-primary">IA</span>
        </h1>
        <p class="mb-8!">
          Revivez les interventions de notre journée dédiée aux enjeux éthiques, culturels et
          environnementaux des systèmes d'IA conversationnelle.
        </p>
        <Link
          button
          href="https://www.youtube.com/playlist?list=PLtRFEzn7EZGIadxkQgxgDdJ0te-U-iRzx"
          text="Visionner les interventions de la journée"
          size="lg"
          class="w-full!"
        />
      </div>
      <div>
        <img
          src="/news/bnf/cover.jpg"
          alt="Conférence d'Anastasia Stasenko dans un amphithéâtre de la BNF, présentant une diapositive qui analyse le jeu de données compar:IA"
          title="Conférence d'Anastasia Stasenko présentant une diapositive qui analyse le jeu de données compar:IA"
          class="fr-responsive-img rounded-xl"
        />
      </div>
    </div>
  </section>

  <section class="bg-light-grey py-15">
    <div class="fr-container">
      <h3 class="text-center">Les conférences</h3>

      <div class="gap-8 md:grid-cols-2 grid">
        {#each talks as talk, i (i)}
          <div class="cg-border bg-white p-6">
            <iframe
              width="100%"
              src={talk.youtubeSrc}
              title="YouTube video player"
              frameborder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              referrerpolicy="strict-origin-when-cross-origin"
              allowfullscreen
              class="aspect-video"
            ></iframe>

            <h4 class="mt-4!">{talk.title}</h4>
            <p class="text-grey">{talk.desc}</p>
          </div>
        {/each}
      </div>
    </div>

    <div class="fr-container pt-15">
      <h3 class="my-12! text-center">Les ateliers</h3>

      <div class="gap-6 grid grid-cols-3">
        {#each workshops as workshop, i (i)}
          <div class="cg-border bg-white p-6">
            <div class="mb-4 flex items-center">
              <p class="mb-0! text-sm! text-grey inline-flex">
                <Icon icon="time-line" size="sm" class="me-1" />
                {workshop.time}
              </p>
              <Badge variant="yellow" text="Atelier" size="sm" class="ms-auto" />
            </div>

            <h6 class="mb-3!">{workshop.title}</h6>
            <p class="text-sm! text-grey">{workshop.desc}</p>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <section class="py-15">
    <h3 class="text-center">Les intervenant·es</h3>
    <div class="fr-container gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 grid">
      {#each speakers as speaker (speaker.name)}
        <div class="cg-border bg-light-grey p-7 flex flex-col">
          <img class="rounded-lg w-full" src={speaker.img} alt="" />
          <h6 class="my-2!">{speaker.name}</h6>
          <p class="text-sm! text-grey">{speaker.desc}</p>

          <div class="gap-2 mt-auto flex flex-wrap">
            {#each speaker.logos as logo, i (`${speaker.name}-${i}`)}
              <img
                src={logo.src}
                width={logo.width ?? 100}
                alt={logo.alt}
                title={logo.alt}
                class={logo.invert ? 'dark:invert' : ''}
              />
            {/each}
          </div>
        </div>
      {/each}
    </div>
  </section>

  <section class="bg-light-grey flex flex-col items-center">
    <div class="fr-container md:w-1/2!">
      <h4 class="mt-12! text-center">À propos de la journée compar:IA</h4>
      <p class="text-center">
        La journée compar:IA s'est tenue le 7 février 2025 à la Bnf François-Mitterrand. L'évènement
        a réuni plus de 300 participant·es en présentiel et une centaine de personnes ont suivi la
        journée en direct.
      </p>
      <p class="text-center">
        L'objectif était d'échanger sur les enjeux éthiques, culturels et environnementaux liés à
        l'IA conversationnelle.
      </p>
      <p class="mb-8! text-center">
        Un grand merci à tou·tes les participant·es et aux partenaires de l'évènement !
      </p>
    </div>

    <div
      class="fr-container mb-12! gap-6 flex max-w-full flex-wrap justify-center *:max-h-[100px] *:object-contain"
    >
      <img src="/orgs/minicult.svg" alt="Ministère de la Culture" title="Ministère de la Culture" />
      <img
        src="/orgs/ateliernumerique.png"
        alt="Atelier numérique"
        title="Atelier numérique"
        class="dark:invert"
      />
      <img
        src="/iasummit.png"
        alt="Sommet de l'IA"
        title="Sommet pour l'action sur l'IA"
        class="dark:invert"
      />
      <img src="/orgs/betagouv.svg" alt="beta.gouv.fr" title="beta.gouv.fr" class="dark:invert" />
      <img src="/orgs/bnf.svg" class="max-w-[100px] dark:invert" alt="BNF" title="BNF" />
    </div>
  </section>
</main>
