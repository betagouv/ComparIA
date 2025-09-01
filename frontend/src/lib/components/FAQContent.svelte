<script lang="ts">
  import { Accordion, AccordionGroup, Tabs } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'

  const tabs = [
    {
      id: 'usage',
      label: m['faq.usage.title'](),
      qs: (['1', '2', '3', '4', '5', '6'] as const).map((q) => ({
        title: m[`faq.usage.questions.${q}.title`](),
        desc: m[`faq.usage.questions.${q}.desc`]()
      }))
    },
    {
      id: 'models',
      label: m['faq.models.title'](),
      qs: (['1', '2', '3', '4', '5'] as const).map((q) => ({
        title: m[`faq.models.questions.${q}.title`](),
        desc: m[`faq.models.questions.${q}.desc`]()
      }))
    },
    {
      id: 'datasets',
      label: m['faq.datasets.title'](),
      qs: (['1', '2', '3'] as const).map((q) => ({
        title: m[`faq.datasets.questions.${q}.title`](),
        desc: m[`faq.datasets.questions.${q}.desc`]()
      }))
    },
    {
      id: 'ecology',
      label: m['faq.ecology.title'](),
      qs: (['1', '2', '3'] as const).map((q) => ({
        title: m[`faq.ecology.questions.${q}.title`](),
        desc: m[`faq.ecology.questions.${q}.desc`]()
      }))
    },
    {
      id: 'i18n',
      label: m['faq.i18n.title'](),
      qs: (['1', '2'] as const).map((q) => ({
        title: m[`faq.i18n.questions.${q}.title`](),
        desc: m[`faq.i18n.questions.${q}.desc`]()
      }))
    }
  ]
</script>

<Tabs {tabs} noBorders label="Foire aux questions">
  {#snippet tab({ id })}
    {#each tabs as tab (tab.id)}
      {#if id === tab.id}
        <AccordionGroup>
          {#each tab.qs as q, i (`${tab.id}-${i}`)}
            <Accordion id={`${tab.id}-${i}`} label={q.title}>
              {@html sanitize(q.desc)}
            </Accordion>
          {/each}
        </AccordionGroup>
      {/if}
    {/each}
  {/snippet}
</Tabs>
