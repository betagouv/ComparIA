// DSFR drives its modals from the global it installs on window.
function dsfrModal(id: string) {
  const element = document.getElementById(id)
  // @ts-expect-error - DSFR is globally available
  return element ? window.dsfr(element).modal : undefined
}

export const discloseModal = (id: string) => dsfrModal(id)?.disclose()

export const closeModal = (id: string) => dsfrModal(id)?.conceal()
