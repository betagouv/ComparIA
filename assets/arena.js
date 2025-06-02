function() {

  function makeSecondHeaderSticky(firstHeaderId, secondHeaderId) {

    function handleScroll() {
      // // Ugly fix bc this script should be active only when second header gets rendered
      let firstHeader = document.getElementById(firstHeaderId);
      let secondHeader = document.getElementById(secondHeaderId);

      if (!firstHeader || !secondHeader) {
        return;
      }

      const scrollY = window.scrollY;

      const secondHeaderHeight = secondHeader.offsetHeight;
      const firstHeaderHeight = firstHeader.offsetHeight;

      if (scrollY >= firstHeaderHeight) {
        if (secondHeader.style.position !== 'fixed') {
          secondHeader.style.position = 'fixed';
          secondHeader.style.top = '0px';
          secondHeader.style.zIndex = "850";
          firstHeader.style.marginBottom = `${secondHeaderHeight}px`; // Expand first header
        }
      } else {
        if (secondHeader.style.position !== 'relative') {
          secondHeader.style.position = 'relative';
          secondHeader.style.top = '';
          secondHeader.style.zIndex = "750";
          firstHeader.style.marginBottom = '';
        }
      }
    }

    function handleResize() {
      handleScroll(); //re-evaluate scroll position after resize.
    }

    window.addEventListener('scroll', handleScroll);
    window.addEventListener('resize', handleResize);

    handleScroll();
  }

  makeSecondHeaderSticky('main-header', 'second-header');

  function adjustFooter() {
    const footer = document.getElementById('send-area');
    const chatArea = document.getElementById('chat-area');

    const footerHeight = footer.offsetHeight;
    // Add bottom padding to the chatArea equal to footer height so it's not hidden
    chatArea.style.paddingBottom = `${footerHeight}px`;
  }
  window.addEventListener('load', adjustFooter);
  window.addEventListener('resize', adjustFooter);
  window.addEventListener('click', adjustFooter);
  adjustFooter();

  console.log("Git commit: __GIT_COMMIT__");


  if (typeof Sentry !== "undefined") {
    Sentry.onLoad(function () {
      Sentry.init({
        integrations: [
          // If you use a bundle with tracing enabled, add the BrowserTracing integration
          Sentry.browserTracingIntegration(),
          // If you use a bundle with session replay enabled, add the Replay integration
          Sentry.replayIntegration(),
        ],

        replaysSessionSampleRate: 0.1,
        replaysOnErrorSampleRate: 1.0,
        dsn: "__SENTRY_FRONT_DSN__",
        environment: "__SENTRY_ENV__",

        tracesSampleRate: 0.2
      });
    });
    Sentry.onLoad(function () {
      // Your code to execute when Sentry is loaded
    });
  } else {
    console.log("Not loading front-end Sentry.");
  }

  // Disable landscape mode because it's unusable in chatbot view for now
  screen.orientation.lock("portrait");

  // Check for Docs documents in session storage
  function checkDocsDocuments() {
    const docsDocuments = sessionStorage.getItem('docs_documents');
    const docsStatus = document.getElementById('docs-status');
    const docsDocumentsInfo = document.getElementById('docs-documents-info');
    
    if (docsDocuments && docsStatus && docsDocumentsInfo) {
      try {
        const documents = JSON.parse(docsDocuments);
        if (documents.length > 0) {
          // Store document IDs in cookie for backend access
          const documentIds = documents.map(d => d.id);
          document.cookie = `selected_docs=${JSON.stringify(documentIds)}; SameSite=Strict; Path=/; Max-Age=3600`;
          
          // Hide the connect button
          docsStatus.style.display = 'none';
          
          // Show selected documents info
          const docTitles = documents.map(d => d.title).join(', ');
          docsDocumentsInfo.innerHTML = `
            <div class="fr-callout fr-callout--green-emeraude">
              <h3 class="fr-callout__title">Documents Docs sélectionnés</h3>
              <p class="fr-callout__text">
                ${documents.length} document(s): ${docTitles.length > 100 ? docTitles.substring(0, 100) + '...' : docTitles}
              </p>
              <a href="/docs/documents" class="fr-btn fr-btn--tertiary-no-outline fr-btn--sm">
                Modifier la sélection
              </a>
              <button class="fr-btn fr-btn--tertiary-no-outline fr-btn--sm" onclick="clearDocsSelection();">
                Effacer la sélection
              </button>
            </div>
          `;
          docsDocumentsInfo.style.display = 'block';
        } else {
          // Clear cookie and show the original button if no documents selected
          document.cookie = 'selected_docs=; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Strict; Path=/';
          docsStatus.style.display = 'block';
          docsDocumentsInfo.style.display = 'none';
        }
      } catch (e) {
        console.error('Error parsing docs documents:', e);
      }
    }
  }
  
  // Function to clear docs selection
  function clearDocsSelection() {
    sessionStorage.removeItem('docs_documents');
    document.cookie = 'selected_docs=; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Strict; Path=/';
    location.reload();
  }
  
  // Make clearDocsSelection globally available
  window.clearDocsSelection = clearDocsSelection;

  // Check on page load
  checkDocsDocuments();
  
  // Also check when the mode screen becomes visible
  const observer = new MutationObserver(checkDocsDocuments);
  const modeScreen = document.getElementById('mode-screen');
  if (modeScreen) {
    observer.observe(modeScreen, { attributes: true, attributeFilter: ['style'] });
  }
}


