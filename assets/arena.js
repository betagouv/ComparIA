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
}


