<script lang="ts">
  function showSnackbar(message: string) {
    snackbarMessage = message
    snackbarVisible = true

    setTimeout(() => {
      snackbarVisible = false
    }, 2000)
  }

  function closeSnackbar() {
    snackbarVisible = false
  }
</script>

<div id="snackbar">
  <div class="checkmark">
    <svg width="16" height="15" viewBox="0 0 16 15" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        fill-rule="evenodd"
        clip-rule="evenodd"
        d="M8.25477 13.7224C4.91029 13.7224 2.19922 11.0114 2.19922 7.66688C2.19922 4.3224 4.91029 1.61133 8.25477 1.61133C11.5993 1.61133 14.3103 4.3224 14.3103 7.66688C14.3103 11.0114 11.5993 13.7224 8.25477 13.7224ZM7.65104 10.0891L11.9323 5.80722L11.0761 4.95097L7.65104 8.3766L5.93792 6.66348L5.08166 7.51973L7.65104 10.0891Z"
        fill="white"
      />
    </svg>
  </div>
  <span class="message"></span><span class="close" on:click={closeSnackbar}
    ><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="12" height="12">
      <path
        d="m12 10.6 4.95-4.96 1.4 1.4L13.42 12l4.96 4.95-1.4 1.4L12 13.42l-4.95 4.96-1.4-1.4L10.58 12 5.63 7.05l1.4-1.4z"
      />
    </svg></span
  >
</div>
