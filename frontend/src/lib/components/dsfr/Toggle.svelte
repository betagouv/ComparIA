<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import type { SvelteHTMLElements } from 'svelte/elements'

  type ToggleProps = {
    id: string
    value: boolean
    label: string
    help?: string
    hideCheckLabel?: boolean
    checkedLabel?: string
    uncheckedLabel?: string
    variant?: 'primary' | 'secondary'
    inline?: boolean
    groupClass?: string
    checkLabelClass?: string
  }

  let {
    id,
    value = $bindable(),
    label,
    help,
    hideCheckLabel = false,
    checkedLabel = m['words.activated'](),
    uncheckedLabel = m['words.deactivated'](),
    variant = 'secondary',
    inline = true,
    checkLabelClass,
    groupClass,
    ...props
  }: ToggleProps & SvelteHTMLElements['label'] = $props()
</script>

<div class={['fr-toggle', `toggle-${variant}`, { 'l-toggle-block': !inline }, groupClass]}>
  <input
    type="checkbox"
    class="fr-toggle__input"
    {id}
    bind:checked={value}
    aria-describedby="toggle-hint-{id}"
  />
  {#if !inline}
    <div aria-hidden="true" class={['fr-label w-full', props.class]}>{label}</div>
  {/if}
  <label
    {...props}
    for={id}
    data-fr-checked-label={checkedLabel}
    data-fr-unchecked-label={uncheckedLabel}
    class={['fr-toggle__label', ...(!inline ? ['max-w-[2.5rem]!'] : [props.class])]}
  >
    <div class={['block', { 'sr-only': !inline }]}>{label}</div>
  </label>
  {#if !hideCheckLabel}
    <div
      aria-hidden="true"
      class={[
        'w-full text-end text-sm text-[#3A3A3A]',
        { 'ms-2 w-auto! text-start leading-[1.5rem]': !inline },
        checkLabelClass
      ]}
    >
      {value ? checkedLabel : uncheckedLabel}
    </div>
  {/if}
  {#if help}
    <p class="fr-hint-text mt-1!" id="toggle-hint-{id}">{help}</p>
  {/if}
</div>

<style lang="postcss">
  .fr-toggle {
    label::before {
      content: '' !important;
    }
    &:not(.l-toggle-block) {
      label::before {
        position: absolute;
        right: 0;
        margin-right: 0 !important;
      }
      label::after {
        left: unset;
        right: 1rem;
      }
    }

    &.l-toggle-block label {
      position: relative;
    }

    /* Override only light theme blue to purple */
    :root[data-fr-theme='light'] & {
      --border-action-high-blue-france: var(--blue-france-main-525);
      --text-active-blue-france: var(--blue-france-main-525);

      input[type='checkbox']:checked ~ .fr-toggle__label::after {
        --data-uri-svg: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%236a6af4' d='m10 15.17 9.2-9.2 1.4 1.42L10 18l-6.36-6.36 1.4-1.42z'/%3E%3C/svg%3E");
      }
      label::before {
        --data-uri-svg: url("data:image/svg+xml;charset=utf-8,%3Csvg width='40' stroke='%236a6af4' height='24' fill='transparent' xmlns='http://www.w3.org/2000/svg'%3E%3Crect x='.5' y='.5' width='39' height='23' rx='11.5'/%3E%3C/svg%3E");
      }
      input[type='checkbox']:checked ~ .fr-toggle__label::before {
        --data-uri-svg: url("data:image/svg+xml;charset=utf-8,%3Csvg width='40' stroke='%236a6af4' height='24' fill='%23000091' xmlns='http://www.w3.org/2000/svg'%3E%3Crect fill='%236a6af4' x='.5' y='.5' width='39' height='23' rx='11.5'/%3E%3C/svg%3E");
      }
    }
    /* To avoid flickering at page load */
    @media (prefers-color-scheme: light) {
      :root[data-fr-theme='system'] & {
        --border-action-high-blue-france: var(--blue-france-main-525);
        --text-active-blue-france: var(--blue-france-main-525);

        input[type='checkbox']:checked ~ .fr-toggle__label::after {
          --data-uri-svg: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%236a6af4' d='m10 15.17 9.2-9.2 1.4 1.42L10 18l-6.36-6.36 1.4-1.42z'/%3E%3C/svg%3E");
        }
        label::before {
          --data-uri-svg: url("data:image/svg+xml;charset=utf-8,%3Csvg width='40' stroke='%236a6af4' height='24' fill='transparent' xmlns='http://www.w3.org/2000/svg'%3E%3Crect x='.5' y='.5' width='39' height='23' rx='11.5'/%3E%3C/svg%3E");
        }
        input[type='checkbox']:checked ~ .fr-toggle__label::before {
          --data-uri-svg: url("data:image/svg+xml;charset=utf-8,%3Csvg width='40' stroke='%236a6af4' height='24' fill='%23000091' xmlns='http://www.w3.org/2000/svg'%3E%3Crect fill='%236a6af4' x='.5' y='.5' width='39' height='23' rx='11.5'/%3E%3C/svg%3E");
        }
      }
    }

    &.toggle-secondary {
      --border-action-high-blue-france: var(--grey-200-850);
      --text-active-blue-france: var(--grey-200-850);

      input[type='checkbox']:checked ~ .fr-toggle__label::after {
        --data-uri-svg: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%233a3a3a' d='m10 15.17 9.2-9.2 1.4 1.42L10 18l-6.36-6.36 1.4-1.42z'/%3E%3C/svg%3E");
      }
      label::before {
        --data-uri-svg: url("data:image/svg+xml;charset=utf-8,%3Csvg width='40' stroke='%233a3a3a' height='24' fill='transparent' xmlns='http://www.w3.org/2000/svg'%3E%3Crect x='.5' y='.5' width='39' height='23' rx='11.5'/%3E%3C/svg%3E");
      }
      input[type='checkbox']:checked ~ .fr-toggle__label::before {
        --data-uri-svg: url("data:image/svg+xml;charset=utf-8,%3Csvg width='40' stroke='%233a3a3a' height='24' fill='%23000091' xmlns='http://www.w3.org/2000/svg'%3E%3Crect fill='%23DDDDDD' x='.5' y='.5' width='39' height='23' rx='11.5'/%3E%3C/svg%3E");
      }
    }
  }

  :root[data-fr-theme='dark'] {
    .fr-toggle.toggle-secondary {
      input[type='checkbox']:checked ~ .fr-toggle__label::after {
        --data-uri-svg: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%23cecece' d='m10 15.17 9.2-9.2 1.4 1.42L10 18l-6.36-6.36 1.4-1.42z'/%3E%3C/svg%3E");
      }
      label::before {
        --data-uri-svg: url("data:image/svg+xml;charset=utf-8,%3Csvg width='40' stroke='%23cecece' height='24' fill='transparent' xmlns='http://www.w3.org/2000/svg'%3E%3Crect x='.5' y='.5' width='39' height='23' rx='11.5'/%3E%3C/svg%3E");
      }
      input[type='checkbox']:checked ~ .fr-toggle__label::before {
        --data-uri-svg: url("data:image/svg+xml;charset=utf-8,%3Csvg width='40' stroke='%23cecece' height='24' fill='%23000091' xmlns='http://www.w3.org/2000/svg'%3E%3Crect fill='%23353535' x='.5' y='.5' width='39' height='23' rx='11.5'/%3E%3C/svg%3E");
      }
    }
  }
</style>
