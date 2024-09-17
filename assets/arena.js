function() {
        
    const footer = document.getElementById('send-area');
    const modeScreen = document.getElementById('mode-screen');
    const chatArea = document.getElementById('chat-area');
  
    function adjustFooter() {
      const footerHeight = footer.offsetHeight;
      // Add bottom padding to the chatArea equal to footer height so it's not hidden
      chatArea.style.paddingBottom = `${footerHeight}px`;
      modeScreen.style.paddingBottom = `${footerHeight}px`;
    }
    // Adjust footer on page load, resize and initially
    window.addEventListener('load', adjustFooter);
    window.addEventListener('resize', adjustFooter);
    adjustFooter();

}

