<script lang="ts">
  import { page } from '$app/state'
  import { Button, Input, Link, Modal, Tabs } from '$components/dsfr'
  import SeoHead from '$components/SEOHead.svelte'
  import ThemeSelector from '$components/ThemeSelector.svelte'
  import { getAuthContext, logout } from '$lib/auth.svelte'
  import { getComparisonsContext } from '$lib/chatService.svelte'
  import { legalPageLinks, resetConsent } from '$lib/consent'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'

  const auth = getAuthContext()
  const comparisons = getComparisonsContext()
  const tabs = [
    { id: 'account', label: m['auth.settings.tabAccount']() },
    { id: 'about', label: m['auth.settings.tabAbout']() }
  ] as const

  let exporting = $state(false)
  let exportError = $state('')
  let eraseEmail = $state('')
  let erasing = $state(false)
  let eraseError = $state('')

  const eraseMatches = $derived(
    !!auth.user && eraseEmail.trim().toLowerCase() === auth.user.email.toLowerCase()
  )

  function download(data: unknown) {
    const content = JSON.stringify(data, null, 2)
    const url = URL.createObjectURL(new Blob([content], { type: 'application/json;charset=utf-8' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `comparia-donnees-${new Date().toISOString().slice(0, 10)}.json`
    document.body.append(anchor)
    anchor.click()
    anchor.remove()
    setTimeout(() => URL.revokeObjectURL(url), 0)
  }

  async function exportData() {
    exporting = true
    exportError = ''
    try {
      download(await api.request('/auth/me/export'))
    } catch {
      exportError = m['auth.settings.export.failed']()
    } finally {
      exporting = false
    }
  }

  async function eraseAccount() {
    if (!eraseMatches) {
      eraseError = m['auth.settings.erase.mismatch']()
      return
    }

    erasing = true
    eraseError = ''
    try {
      await api.request('/auth/me', {
        method: 'DELETE',
        body: JSON.stringify({ email: eraseEmail.trim() })
      })
      auth.user = null
      resetConsent()
      window.location.href = '/'
    } catch {
      eraseError = m['auth.settings.erase.failed']()
    } finally {
      erasing = false
    }
  }
</script>

<SeoHead title={m['seo.titles.settings']()} />

<header class="bg-very-light-primary px-4 py-4 shadow-sm">
  <div class="fr-container max-w-[1000px]">
    <h1 class="fr-h5 mb-0!">{m['auth.settings.title']()}</h1>
    <p class="fr-text--sm text-grey mb-0!">{m['auth.settings.subtitle']()}</p>
  </div>
</header>

<div class="py-6 lg:py-8">
  <div class="fr-container max-w-[1000px]">
    <Tabs {tabs} label={m['auth.settings.tabsLabel']()} noBorders kind="nav">
      {#snippet tab(tab)}
        {#if tab.id === 'account'}
          <div class="fr-grid-row fr-grid-row--gutters">
            <section class="fr-col-12 fr-col-lg-6" aria-labelledby="account-title">
              <h2 id="account-title" class="fr-h4">{m['auth.settings.account.title']()}</h2>

              {#if auth.user}
                <Input
                  id="account-email"
                  type="email"
                  value={auth.user.email}
                  label={m['auth.settings.account.email']()}
                  disabled
                />
                <div class="gap-3 flex flex-wrap">
                  <Button
                    variant="secondary"
                    text={m['auth.settings.logout']()}
                    icon="logout-box-r-line"
                    onclick={() => logout(auth, comparisons)}
                  />
                  <Button
                    variant="tertiary"
                    text={m['auth.settings.erase.action']()}
                    class="text-error!"
                    aria-controls="account-erasure-modal"
                    data-fr-opened="false"
                  />
                </div>
              {:else}
                <p>{m['auth.settings.account.signInPrompt']()}</p>
              {/if}
            </section>

            <section class="fr-col-12 fr-col-lg-6" aria-labelledby="display-title">
              <h2 id="display-title" class="fr-h4">{m['auth.settings.display.title']()}</h2>
              <ThemeSelector variant="select" />
            </section>
          </div>

          {#if auth.user}
            <section class="fr-mt-8v" aria-labelledby="export-title">
              <h2 id="export-title" class="fr-h4">{m['auth.settings.export.title']()}</h2>
              <p class="fr-text--sm text-grey max-w-[800px]">
                {m['auth.settings.export.desc']()}
              </p>
              <Button
                variant="secondary"
                text={exporting
                  ? m['auth.settings.export.pending']()
                  : m['auth.settings.export.action']()}
                disabled={exporting}
                onclick={exportData}
              />
              {#if exportError}
                <p class="fr-error-text" role="alert">{exportError}</p>
              {/if}
            </section>
          {/if}
        {:else}
          <section aria-labelledby="links-title">
            <h2 id="links-title" class="fr-h4">{m['auth.settings.links.title']()}</h2>
            <p class="fr-text--sm text-grey max-w-[800px]">
              {@html sanitize(
                m['footer.license.mention']({
                  linkProps: externalLinkProps({
                    href: 'https://github.com/etalab/licence-ouverte/blob/master/LO.md',
                    title: m['footer.license.linkTitle']()
                  })
                })
              )}
            </p>
            <ul class="fr-raw-list gap-3 flex flex-col items-start">
              {#each legalPageLinks(page.data.informationalPages, 'settings') as link (link.href)}
                <li><Link href={link.href} text={link.label} /></li>
              {/each}
              <li>
                <Link
                  href="https://github.com/betagouv/ComparIA"
                  text={m['footer.links.sources']()}
                />
              </li>
            </ul>
          </section>
        {/if}
      {/snippet}
    </Tabs>
  </div>
</div>

<Modal
  id="account-erasure-modal"
  titleId="account-erasure-title"
  sizeClass="fr-col-12 fr-col-md-8 fr-col-lg-5"
>
  <h2 id="account-erasure-title" class="fr-modal__title">{m['auth.settings.erase.title']()}</h2>
  <p>{m['auth.settings.erase.intro']()}</p>
  <ul>
    <li>{m['auth.settings.erase.effectAccount']()}</li>
    <li>{m['auth.settings.erase.effectComparisons']()}</li>
    <li>{m['auth.settings.erase.effectContent']()}</li>
    <li>{m['auth.settings.erase.effectConsent']()}</li>
  </ul>
  {#if auth.user}
    <Input
      id="account-erasure-email"
      type="email"
      bind:value={eraseEmail}
      label={m['auth.settings.erase.confirmLabel']()}
      help={m['auth.settings.erase.confirmHelp']({ email: auth.user.email })}
      error={eraseError}
      autocomplete="email"
    />
  {/if}
  <div class="fr-btns-group fr-btns-group--inline-reverse fr-btns-group--inline-lg">
    <Button
      text={erasing ? m['auth.settings.erase.pending']() : m['auth.settings.erase.action']()}
      disabled={erasing || !eraseMatches}
      onclick={eraseAccount}
    />
    <Button variant="secondary" text={m['words.cancel']()} aria-controls="account-erasure-modal" />
  </div>
</Modal>
