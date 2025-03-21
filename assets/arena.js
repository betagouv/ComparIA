function() {

  function makeSecondHeaderSticky(firstHeaderId, secondHeaderId) {
 
    const firstHeader = document.getElementById(firstHeaderId);
    const secondHeader = document.getElementById(secondHeaderId);
  
    if (!firstHeader || !secondHeader) {
      console.error("The headers are not found. This is a failure.");
      return;
    }
  
    let firstHeaderHeight = firstHeader.offsetHeight;
    let secondHeaderHeight = secondHeader.offsetHeight;
  
    function recalculateHeights() {
      firstHeaderHeight = firstHeader.offsetHeight;
      secondHeaderHeight = secondHeader.offsetHeight;
    }

    function handleScroll() {
      const scrollY = window.scrollY;
  
      if (scrollY >= firstHeaderHeight) {
        if (secondHeader.style.position !== 'fixed') {
          secondHeader.style.position = 'fixed';
          secondHeader.style.top = '0px';
          firstHeader.style.paddingBottom = `${secondHeaderHeight}px`; // Expand first header
        }
      } else {
        if (secondHeader.style.position !== 'relative') {
          secondHeader.style.position = 'relative';
          secondHeader.style.top = '';
          firstHeader.style.paddingBottom = '';
        }
      }
    }
  
    function handleResize() {
      recalculateHeights();
      handleScroll(); // Re-evaluate scroll position after resize
    }

    window.addEventListener('scroll', handleScroll); // Extra initial calculation
    window.addEventListener('resize', handleResize);

    recalculateHeights();
    handleScroll();
  }
  
  makeSecondHeaderSticky('main-header', 'second-header'); 
  
  function adjustFooter() {
    const footer = document.getElementById('send-area');
    const modeScreen = document.getElementById('mode-screen');
    const chatArea = document.getElementById('chat-area');

    const footerHeight = footer.offsetHeight;
    // Add bottom padding to the chatArea equal to footer height so it's not hidden
    chatArea.style.paddingBottom = `${footerHeight}px`;
    modeScreen.style.paddingBottom = `${footerHeight}px`;
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
}


