<script lang="ts">
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Badge } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { ConversationTranscript } from '../../components'
  import { label, modelName } from '../../filters'
  import type { PageProps } from './$types'

  let { data }: PageProps = $props()

  const conversation = $derived(data.conversation)
  const dateFormatter = new Intl.DateTimeFormat(getLocale(), {
    dateStyle: 'long',
    timeStyle: 'short'
  })
  const backHref = $derived(resolve(`/admin/activite/conversations${page.url.search}`))
</script>

<div class="mb-4">
  <a href={backHref} class="fr-link fr-icon-arrow-left-line fr-link--icon-left">
    {m['admin.activity.conversation.back']()}
  </a>
</div>

<div class="gap-8 xl:grid-cols-[1fr_20rem] grid grid-cols-1">
  <section aria-label={m['admin.activity.conversation.title']()}>
    {#key conversation.id}
      <ConversationTranscript {conversation} />
    {/key}
  </section>

  <aside class="gap-6 flex flex-col">
    <section class="p-4 rounded-lg cg-border">
      <h2 class="fr-h6 mb-3!">{m['admin.activity.conversation.details']()}</h2>
      <dl class="gap-2 m-0! fr-text--sm flex flex-col">
        <div>
          <dt class="text-grey">{m['admin.activity.conversations.cols.date']()}</dt>
          <dd class="m-0!">{dateFormatter.format(new Date(conversation.created_at))}</dd>
        </div>
        <div>
          <dt class="text-grey">{m['admin.activity.conversations.cols.models']()}</dt>
          <dd class="m-0!">
            {m['admin.activity.conversation.versus']({
              a: modelName(conversation, 'a'),
              b: modelName(conversation, 'b')
            })}
          </dd>
        </div>
        <div>
          <dt class="text-grey">{m['admin.activity.conversation.mode']()}</dt>
          <dd class="m-0!">{label('modes', conversation.mode)}</dd>
        </div>
        {#if conversation.cohorts}
          <div>
            <dt class="text-grey">{m['admin.activity.conversation.cohort']()}</dt>
            <dd class="m-0!">{conversation.cohorts}</dd>
          </div>
        {/if}
        <div>
          <dt class="text-grey">{m['admin.activity.conversation.revealed']()}</dt>
          <dd class="m-0!">
            {conversation.revealed
              ? m['admin.activity.conversation.yes']()
              : m['admin.activity.conversation.no']()}
          </dd>
        </div>
      </dl>
      {#if conversation.archived || conversation.error}
        <div class="mt-3 gap-1 flex flex-wrap">
          {#if conversation.archived}
            <Badge
              size="sm"
              variant="yellow"
              text={m['admin.activity.conversation.archived']({
                reason: conversation.archived_reason ?? '?'
              })}
              noTooltip
            />
          {/if}
          {#if conversation.error}
            <Badge
              size="sm"
              variant="red"
              text={m['admin.activity.conversation.error']({
                code: conversation.error.code ?? conversation.error.message
              })}
              noTooltip
            />
          {/if}
        </div>
      {/if}
    </section>

    <section class="p-4 rounded-lg cg-border">
      <h2 class="fr-h6 mb-3!">{m['admin.activity.conversation.analysis']()}</h2>
      {#if !conversation.llm_analyzed}
        <p class="fr-text--sm mb-0! text-grey">{m['admin.activity.conversation.notAnalyzed']()}</p>
      {:else}
        <dl class="gap-2 m-0! fr-text--sm flex flex-col">
          {#if conversation.short_summary}
            <div>
              <dt class="text-grey">{m['admin.activity.conversation.summary']()}</dt>
              <dd class="m-0!">
                {#if conversation.contains_pii}
                  <details>
                    <summary class="cursor-pointer"
                      >{m['admin.activity.conversation.show']()}</summary
                    >
                    {conversation.short_summary}
                  </details>
                {:else}
                  {conversation.short_summary}
                {/if}
              </dd>
            </div>
          {/if}
          {#if conversation.categories.length}
            <div>
              <dt class="text-grey">{m['admin.activity.conversation.categories']()}</dt>
              <dd class="m-0!">{conversation.categories.join(', ')}</dd>
            </div>
          {/if}
          {#if conversation.keywords.length}
            <div>
              <dt class="text-grey">{m['admin.activity.conversation.keywords']()}</dt>
              <dd class="m-0!">{conversation.keywords.join(', ')}</dd>
            </div>
          {/if}
          {#if conversation.languages.length}
            <div>
              <dt class="text-grey">{m['admin.activity.conversation.languages']()}</dt>
              <dd class="m-0!">{conversation.languages.join(', ')}</dd>
            </div>
          {/if}
        </dl>
        {#if conversation.contains_pii || conversation.contains_spam}
          <div class="mt-3 gap-1 flex flex-wrap">
            {#if conversation.contains_pii}
              <Badge size="sm" variant="yellow" text={label('flags', 'pii')} noTooltip />
            {/if}
            {#if conversation.contains_spam}
              <Badge size="sm" variant="yellow" text={label('flags', 'spam')} noTooltip />
            {/if}
          </div>
        {/if}
      {/if}
    </section>

    {#if conversation.system_msg_a || conversation.system_msg_b}
      <details class="p-4 rounded-lg cg-border">
        <summary class="fr-text--sm font-bold cursor-pointer">
          {m['admin.activity.conversation.systemPrompts']()}
        </summary>
        {#each [['a', conversation.system_msg_a], ['b', conversation.system_msg_b]] as const as [side, prompt] (side)}
          {#if prompt}
            <p class="fr-text--xs mt-3! mb-1! font-bold">{modelName(conversation, side)}</p>
            <p class="fr-text--xs mb-0! whitespace-pre-wrap">{prompt}</p>
          {/if}
        {/each}
      </details>
    {/if}
  </aside>
</div>
