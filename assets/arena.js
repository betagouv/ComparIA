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

  /**
   * Docs Integration
   * Manages document selection from Docs and displays selected documents
   */
  
  // Check for Docs documents in session storage and update UI
  function checkDocsDocuments() {
    const docsDocuments = sessionStorage.getItem('docs_documents');
    const docsDocumentsInfo = document.getElementById('docs-documents-info');
    
    if (docsDocumentsInfo) {
      if (docsDocuments) {
        try {
          const documents = JSON.parse(docsDocuments);
          if (documents.length > 0) {
            // Store document IDs in cookie for backend access
            const documentIds = documents.map(d => d.id);
            // URL encode the JSON to ensure it's properly transmitted
            const encodedIds = encodeURIComponent(JSON.stringify(documentIds));
            document.cookie = `selected_docs=${encodedIds}; SameSite=Strict; Path=/; Max-Age=3600`;
            
            // Show selected documents info as a clean list
            const documentList = documents.map(d => `
              <div class="docs-document-item" style="display: flex; align-items: center; justify-content: space-between; padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 0.5rem; background: #f9f9f9;">
                <span style="font-size: 0.9rem;">${d.title}</span>
                <button class="docs-remove-btn" onclick="removeDocsDocument('${d.id}')" style="background: none; border: none; color: #666; cursor: pointer; font-size: 1.2rem; padding: 0.25rem;" title="Supprimer ce document">×</button>
              </div>
            `).join('');
            
            docsDocumentsInfo.innerHTML = `
              <div style="margin-bottom: 1rem;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
                  <span style="font-weight: 500; color: #666; font-size: 0.9rem;">${documents.length} document(s) sélectionné(s)</span>
                  <button class="fr-btn fr-btn--tertiary-no-outline fr-btn--sm" onclick="clearDocsSelection();" style="font-size: 0.8rem;">
                    Tout effacer
                  </button>
                </div>
                ${documentList}
              </div>
            `;
            docsDocumentsInfo.style.display = 'block';
            docsDocumentsInfo.style.visibility = 'visible';
          } else {
            // Clear cookie if no documents selected
            document.cookie = 'selected_docs=; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Strict; Path=/';
            docsDocumentsInfo.innerHTML = '';
            docsDocumentsInfo.style.display = 'none';
          }
        } catch (e) {
          console.error('Error parsing docs documents:', e);
        }
      } else {
        // No documents in session storage, hide the info
        docsDocumentsInfo.innerHTML = '';
        docsDocumentsInfo.style.display = 'none';
      }
    }
  }
  
  // Clear all selected documents
  function clearDocsSelection() {
    sessionStorage.removeItem('docs_documents');
    document.cookie = 'selected_docs=; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Strict; Path=/';
    location.reload();
  }
  
  // Remove a specific document from selection
  function removeDocsDocument(documentId) {
    const docsDocuments = sessionStorage.getItem('docs_documents');
    if (docsDocuments) {
      try {
        const documents = JSON.parse(docsDocuments);
        const updatedDocuments = documents.filter(d => d.id !== documentId);
        
        if (updatedDocuments.length > 0) {
          sessionStorage.setItem('docs_documents', JSON.stringify(updatedDocuments));
        } else {
          sessionStorage.removeItem('docs_documents');
          // Also clear the cookie when no documents remain
          document.cookie = 'selected_docs=; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Strict; Path=/';
        }
        
        checkDocsDocuments(); // Refresh the display
      } catch (e) {
        console.error('Error removing document:', e);
      }
    }
  }
  
  // Make functions globally available
  window.clearDocsSelection = clearDocsSelection;
  window.removeDocsDocument = removeDocsDocument;

  // Check on page load
  checkDocsDocuments();
  
  // Also check when the mode screen becomes visible
  const observer = new MutationObserver(checkDocsDocuments);
  const modeScreen = document.getElementById('mode-screen');
  if (modeScreen) {
    observer.observe(modeScreen, { attributes: true, attributeFilter: ['style'] });
  }

  // Add Docs integration button to the interface
  function addDocsButton() {
    // Wait for the selections div to be available
    const selectionsDiv = document.querySelector('.selections');
    if (selectionsDiv && !document.querySelector('.docs-btn')) {
      const docsButton = document.createElement('button');
      docsButton.className = 'mode-selection-btn fr-py-1w fr-py-md-0 fr-mb-md-0 fr-mb-1w fr-mr-3v svelte-6bard9 docs-btn';
      docsButton.setAttribute('data-fr-opened', 'false');
      docsButton.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="svelte-6bard9">
          <path d="M9 2.003V2H19.998C20.55 2 21 2.455 21 2.992V21.008C21 21.556 20.555 22 19.993 22H4.007C3.451 22 3 21.545 3 21.008V2.992C3 2.444 3.445 2 4.007 2H7V2.003C7.001 2.003 7.002 2.003 7.003 2.003H9ZM7 4H5V20H19V4H17V6H7V4ZM9 4V6H15V4H9Z" fill="#6A6AF4"/>
        </svg>
        <span class="label svelte-6bard9">ajouter un document depuis Docs</span>
      `;
      
      // Add click handler to navigate to docs
      docsButton.addEventListener('click', function() {
        window.location.href = '/docs/documents';
      });
      
      selectionsDiv.appendChild(docsButton);
    }
  }

  // Try to add the button immediately
  addDocsButton();
  
  // Also try after a delay in case the component loads later
  setTimeout(addDocsButton, 1000);
  setTimeout(addDocsButton, 2000);
  
  // Use a mutation observer to watch for when the component loads
  const componentObserver = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
      if (mutation.addedNodes.length > 0) {
        addDocsButton();
      }
    });
  });
  
  componentObserver.observe(document.body, {
    childList: true,
    subtree: true
  });
}


